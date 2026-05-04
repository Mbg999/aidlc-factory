"""Core persistent memory store.

File-backed, multi-developer, concurrent-safe.
Supports pluggable backends: local file (default) or Engram HTTP API.
When Engram is configured, writes go to both Engram and local (write-through).
Reads prefer Engram but fall back to local on failure.

Storage layout (local):
  <root>/
    developers/<dev_id>/
      profile.json          # Developer metadata & preferences
      episodic.jsonl        # Append-only event log
      semantic.json         # Key-value knowledge base
    shared/
      semantic.json         # Shared project knowledge
      decisions.jsonl       # Architecture decision records
    _locks/                 # Advisory lock files
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .locking import file_lock
from .types import MemoryEntry, MemoryType, Scope


class MemoryStore:
    """Persistent memory store with developer isolation and concurrent safety.

    Usage (local only):
        store = MemoryStore("/path/to/project/.aidlc-memory")

    Usage (with Engram backend + local fallback):
        store = MemoryStore.with_engram(
            "/path/to/project/.aidlc-memory",
            engram_url="http://127.0.0.1:7437",
            project="my-project",
        )
    """

    def __init__(self, root: str | Path, *, backend: "MemoryBackend | None" = None) -> None:
        self._root = Path(root)
        self._root.mkdir(parents=True, exist_ok=True)
        self._locks = self._root / "_locks"
        self._locks.mkdir(exist_ok=True)
        self._backend = backend

    @classmethod
    def with_engram(
        cls,
        root: str | Path,
        *,
        engram_url: str = "http://127.0.0.1:7437",
        project: str = "aidlc",
        timeout: float = 5.0,
    ) -> "MemoryStore":
        """Create a MemoryStore that uses Engram as primary backend with local fallback.

        If Engram is unreachable at creation time, silently falls back to local-only.
        """
        try:
            from .backends.engram import EngramBackend
            backend = EngramBackend(base_url=engram_url, project=project, timeout=timeout)
            if backend.is_available():
                return cls(root, backend=backend)
        except Exception:
            pass
        return cls(root)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def backend_name(self) -> str:
        """Return the name of the active backend ('local' or 'engram')."""
        if self._backend is not None:
            return type(self._backend).__name__.replace("Backend", "").lower()
        return "local"

    def remember(
        self,
        developer_id: str,
        content: str,
        *,
        memory_type: MemoryType = MemoryType.SEMANTIC,
        scope: Scope = Scope.PRIVATE,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        session_id: str = "",
        ttl_hours: float | None = None,
    ) -> MemoryEntry:
        """Store a new memory entry.

        When an external backend (Engram) is configured, writes go to both
        the backend and local storage (write-through for resilience).
        """
        entry = MemoryEntry(
            content=content,
            memory_type=memory_type,
            scope=scope,
            tags=tags or [],
            metadata=metadata or {},
            developer_id=developer_id,
            session_id=session_id,
            ttl_hours=ttl_hours,
        )

        # Always write locally (ensures offline resilience)
        if scope == Scope.SHARED:
            self._write_shared(entry)
        else:
            self._write_private(entry)

        # Write-through to external backend (best-effort)
        if self._backend is not None:
            try:
                entry = self._backend.save(developer_id, entry)
            except Exception:
                pass  # Local write succeeded; backend failure is non-fatal

        return entry

    def recall(
        self,
        developer_id: str,
        *,
        tags: list[str] | None = None,
        memory_type: MemoryType | None = None,
        query: str | None = None,
        limit: int = 50,
        include_shared: bool = True,
        include_expired: bool = False,
    ) -> list[MemoryEntry]:
        """Retrieve memory entries matching the given filters.

        When an external backend is configured, prefers its results (FTS5 search
        is better than our linear scan). Falls back to local on failure.
        """
        # Try external backend first
        if self._backend is not None:
            try:
                return self._backend.search(
                    developer_id,
                    tags=tags,
                    memory_type=memory_type,
                    query=query,
                    limit=limit,
                    include_shared=include_shared,
                    include_expired=include_expired,
                )
            except Exception:
                pass  # Fall through to local

        return self._recall_local(
            developer_id,
            tags=tags,
            memory_type=memory_type,
            query=query,
            limit=limit,
            include_shared=include_shared,
            include_expired=include_expired,
        )

    def _recall_local(
        self,
        developer_id: str,
        *,
        tags: list[str] | None = None,
        memory_type: MemoryType | None = None,
        query: str | None = None,
        limit: int = 50,
        include_shared: bool = True,
        include_expired: bool = False,
    ) -> list[MemoryEntry]:
        """Local file-based recall with scoring."""
        candidates: list[MemoryEntry] = []
        candidates.extend(self._read_all_private(developer_id))
        if include_shared:
            candidates.extend(self._read_all_shared())

        if not include_expired:
            candidates = [e for e in candidates if not e.is_expired()]
        if memory_type is not None:
            candidates = [e for e in candidates if e.memory_type == memory_type]
        if tags:
            tag_set = set(t.lower() for t in tags)
            candidates = [
                e for e in candidates
                if tag_set & set(t.lower() for t in e.tags)
            ]
        if query:
            q_lower = query.lower()
            candidates = [
                e for e in candidates
                if q_lower in e.content.lower()
                or any(q_lower in t.lower() for t in e.tags)
            ]

        def _score(entry: MemoryEntry) -> float:
            score = 0.0
            if tags:
                tag_set_l = set(t.lower() for t in tags)
                score += len(tag_set_l & set(t.lower() for t in entry.tags)) * 10
            try:
                created = datetime.fromisoformat(entry.created_at)
                age_hours = (datetime.now(timezone.utc) - created).total_seconds() / 3600
                score += max(0, 100 - age_hours)
            except Exception:
                pass
            if query and query.lower() in entry.content.lower():
                score += 20
            return score

        candidates.sort(key=_score, reverse=True)
        return candidates[:limit]

    def recall_context(
        self,
        developer_id: str,
        *,
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> str:
        """Return a preformatted context string suitable for injection into an LLM prompt."""
        entries = self.recall(developer_id, tags=tags, limit=limit)
        if not entries:
            return ""
        lines = [f"## Developer Memory ({developer_id})\n"]
        for e in entries:
            tag_str = ", ".join(e.tags) if e.tags else ""
            prefix = f"[{e.memory_type.value}]"
            if tag_str:
                prefix += f" ({tag_str})"
            lines.append(f"- {prefix} {e.content}")
        return "\n".join(lines)

    def list_developers(self) -> list[str]:
        """Return all known developer IDs."""
        devs_dir = self._root / "developers"
        if not devs_dir.exists():
            return []
        return sorted(
            d.name for d in devs_dir.iterdir()
            if d.is_dir() and not d.name.startswith("_")
        )

    def get_profile(self, developer_id: str) -> dict[str, Any]:
        """Read a developer's profile."""
        path = self._dev_dir(developer_id) / "profile.json"
        lock = self._locks / f"dev-{developer_id}-profile.lock"
        with file_lock(lock, shared=True):
            if path.exists():
                return json.loads(path.read_text(encoding="utf-8"))
        return {}

    def update_profile(self, developer_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        """Merge updates into a developer's profile."""
        path = self._dev_dir(developer_id) / "profile.json"
        lock = self._locks / f"dev-{developer_id}-profile.lock"
        with file_lock(lock):
            existing = {}
            if path.exists():
                existing = json.loads(path.read_text(encoding="utf-8"))
            existing.update(updates)
            existing["updated_at"] = datetime.now(timezone.utc).isoformat()
            path.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding="utf-8")
        return existing

    def forget(self, developer_id: str, entry_id: str) -> bool:
        """Remove a specific memory entry by ID.

        Works for semantic/procedural entries (JSON keyed by id).
        Episodic entries cannot be individually deleted (append-only).
        """
        # Delete from backend too (best-effort)
        if self._backend is not None:
            try:
                self._backend.delete(developer_id, entry_id)
            except Exception:
                pass

        sem_path = self._dev_dir(developer_id) / "semantic.json"
        lock = self._locks / f"dev-{developer_id}-semantic.lock"
        with file_lock(lock):
            if sem_path.exists():
                data: dict = json.loads(sem_path.read_text(encoding="utf-8"))
                if entry_id in data:
                    del data[entry_id]
                    sem_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
                    return True
        return False

    def compact(self, developer_id: str) -> int:
        """Remove expired entries from semantic store. Returns count removed."""
        sem_path = self._dev_dir(developer_id) / "semantic.json"
        lock = self._locks / f"dev-{developer_id}-semantic.lock"
        removed = 0
        with file_lock(lock):
            if sem_path.exists():
                data: dict = json.loads(sem_path.read_text(encoding="utf-8"))
                to_remove = []
                for eid, raw in data.items():
                    try:
                        entry = MemoryEntry.from_dict(raw)
                        if entry.is_expired():
                            to_remove.append(eid)
                    except Exception:
                        continue
                for eid in to_remove:
                    del data[eid]
                    removed += 1
                if removed:
                    sem_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        return removed

    def share(self, developer_id: str, entry_id: str) -> bool:
        """Promote a private entry to shared scope."""
        # Also promote in backend (best-effort)
        if self._backend is not None:
            try:
                self._backend.share(developer_id, entry_id)
            except Exception:
                pass

        sem_path = self._dev_dir(developer_id) / "semantic.json"
        lock = self._locks / f"dev-{developer_id}-semantic.lock"
        entry_dict = None
        with file_lock(lock):
            if sem_path.exists():
                data = json.loads(sem_path.read_text(encoding="utf-8"))
                entry_dict = data.pop(entry_id, None)
                if entry_dict:
                    sem_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        if entry_dict:
            entry = MemoryEntry.from_dict(entry_dict)
            entry.scope = Scope.SHARED
            self._write_shared(entry)
            return True
        return False

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _dev_dir(self, developer_id: str) -> Path:
        d = self._root / "developers" / developer_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _shared_dir(self) -> Path:
        d = self._root / "shared"
        d.mkdir(parents=True, exist_ok=True)
        return d

    def _write_private(self, entry: MemoryEntry) -> None:
        dev = entry.developer_id
        if entry.memory_type == MemoryType.EPISODIC:
            path = self._dev_dir(dev) / "episodic.jsonl"
            lock = self._locks / f"dev-{dev}-episodic.lock"
            with file_lock(lock):
                with open(path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        else:
            path = self._dev_dir(dev) / "semantic.json"
            lock = self._locks / f"dev-{dev}-semantic.lock"
            with file_lock(lock):
                data: dict = {}
                if path.exists():
                    data = json.loads(path.read_text(encoding="utf-8"))
                data[entry.id] = entry.to_dict()
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _write_shared(self, entry: MemoryEntry) -> None:
        if entry.memory_type == MemoryType.EPISODIC:
            path = self._shared_dir() / "decisions.jsonl"
            lock = self._locks / "shared-decisions.lock"
            with file_lock(lock):
                with open(path, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")
        else:
            path = self._shared_dir() / "semantic.json"
            lock = self._locks / "shared-semantic.lock"
            with file_lock(lock):
                data: dict = {}
                if path.exists():
                    data = json.loads(path.read_text(encoding="utf-8"))
                data[entry.id] = entry.to_dict()
                path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _read_all_private(self, developer_id: str) -> list[MemoryEntry]:
        entries: list[MemoryEntry] = []
        dev_dir = self._dev_dir(developer_id)

        # Episodic (JSONL)
        ep_path = dev_dir / "episodic.jsonl"
        lock_ep = self._locks / f"dev-{developer_id}-episodic.lock"
        if ep_path.exists():
            with file_lock(lock_ep, shared=True):
                for line in ep_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line:
                        try:
                            entries.append(MemoryEntry.from_dict(json.loads(line)))
                        except Exception:
                            continue

        # Semantic/procedural (JSON dict)
        sem_path = dev_dir / "semantic.json"
        lock_sem = self._locks / f"dev-{developer_id}-semantic.lock"
        if sem_path.exists():
            with file_lock(lock_sem, shared=True):
                data = json.loads(sem_path.read_text(encoding="utf-8"))
                for raw in data.values():
                    try:
                        entries.append(MemoryEntry.from_dict(raw))
                    except Exception:
                        continue

        return entries

    def _read_all_shared(self) -> list[MemoryEntry]:
        entries: list[MemoryEntry] = []
        shared = self._shared_dir()

        # Decisions JSONL
        dec_path = shared / "decisions.jsonl"
        lock_dec = self._locks / "shared-decisions.lock"
        if dec_path.exists():
            with file_lock(lock_dec, shared=True):
                for line in dec_path.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line:
                        try:
                            entries.append(MemoryEntry.from_dict(json.loads(line)))
                        except Exception:
                            continue

        # Shared semantic
        sem_path = shared / "semantic.json"
        lock_sem = self._locks / "shared-semantic.lock"
        if sem_path.exists():
            with file_lock(lock_sem, shared=True):
                data = json.loads(sem_path.read_text(encoding="utf-8"))
                for raw in data.values():
                    try:
                        entries.append(MemoryEntry.from_dict(raw))
                    except Exception:
                        continue

        return entries
