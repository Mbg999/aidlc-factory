"""Local file-backed memory backend.

Wraps the existing MemoryStore logic as a backend implementation so it
can be used interchangeably with Engram or other backends.
"""
from __future__ import annotations

from typing import Any

from ..backend import MemoryBackend
from ..types import MemoryEntry, MemoryType, Scope


class LocalBackend(MemoryBackend):
    """Delegates to the file-based MemoryStore internals.

    This backend is always available (no external dependencies).
    It receives the MemoryStore instance at construction time and
    calls its private helpers directly.
    """

    def __init__(self, store: "MemoryStore") -> None:  # noqa: F821 — forward ref
        self._store = store

    def save(self, developer_id: str, entry: MemoryEntry) -> MemoryEntry:
        if entry.scope == Scope.SHARED:
            self._store._write_shared(entry)
        else:
            self._store._write_private(entry)
        return entry

    def search(
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
        from datetime import datetime, timezone

        candidates: list[MemoryEntry] = []
        candidates.extend(self._store._read_all_private(developer_id))
        if include_shared:
            candidates.extend(self._store._read_all_shared())

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

    def delete(self, developer_id: str, entry_id: str) -> bool:
        return self._store.forget(developer_id, entry_id)

    def get_profile(self, developer_id: str) -> dict[str, Any]:
        return self._store.get_profile(developer_id)

    def update_profile(self, developer_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        return self._store.update_profile(developer_id, updates)

    def list_developers(self) -> list[str]:
        return self._store.list_developers()

    def compact(self, developer_id: str) -> int:
        return self._store.compact(developer_id)

    def share(self, developer_id: str, entry_id: str) -> bool:
        return self._store.share(developer_id, entry_id)
