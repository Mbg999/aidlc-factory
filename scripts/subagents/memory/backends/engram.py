"""Engram HTTP API backend for the AIDLC memory system.

Maps MemoryBackend operations to Engram's REST API (default http://127.0.0.1:7437).
Developer isolation is achieved via Engram's project-scoped observations plus
a `developer:<id>` convention in the scope/tool_name fields.

Requires: Engram running locally (`engram serve`) or reachable via network.
No pip dependencies — uses only stdlib urllib.

Engram API mapping:
  remember  → POST /observations
  recall    → GET  /search
  forget    → DELETE /observations/{id}
  context   → GET  /context
  profile   → stored as a special observation with type=config, topic_key=developer/<id>/profile
"""
from __future__ import annotations

import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timezone
from typing import Any

from ..backend import MemoryBackend
from ..types import MemoryEntry, MemoryType, Scope

# Engram type mapping
_TYPE_MAP: dict[MemoryType, str] = {
    MemoryType.SEMANTIC: "decision",
    MemoryType.EPISODIC: "discovery",
    MemoryType.PROCEDURAL: "pattern",
}

_REVERSE_TYPE_MAP: dict[str, MemoryType] = {
    "decision": MemoryType.SEMANTIC,
    "architecture": MemoryType.SEMANTIC,
    "config": MemoryType.SEMANTIC,
    "discovery": MemoryType.EPISODIC,
    "bugfix": MemoryType.EPISODIC,
    "learning": MemoryType.EPISODIC,
    "pattern": MemoryType.PROCEDURAL,
    "preference": MemoryType.PROCEDURAL,
}


class EngramBackend(MemoryBackend):
    """Engram HTTP API backend.

    Usage:
        backend = EngramBackend(base_url="http://127.0.0.1:7437", project="my-project")

    Falls back gracefully: if Engram is unreachable, methods raise ConnectionError
    and the MemoryStore can catch + fallback to local.
    """

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:7437",
        project: str = "aidlc",
        timeout: float = 5.0,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._project = project
        self._timeout = timeout
        self._session_ids: dict[str, str] = {}  # developer_id → session_id

    # ------------------------------------------------------------------
    # MemoryBackend interface
    # ------------------------------------------------------------------

    def save(self, developer_id: str, entry: MemoryEntry) -> MemoryEntry:
        session_id = self._ensure_session(developer_id)
        engram_type = _TYPE_MAP.get(entry.memory_type, "discovery")
        scope = "project" if entry.scope == Scope.SHARED else "personal"

        # Build structured content (Engram's What/Why/Where/Learned format)
        content = self._format_content(entry)

        # Build title from first 80 chars of content
        title = entry.content[:80]
        if entry.tags:
            title = f"[{', '.join(entry.tags[:3])}] {title}"
        title = title[:120]

        # Topic key for upsert dedup
        topic_key = None
        if entry.metadata.get("topic_key"):
            topic_key = entry.metadata["topic_key"]
        elif entry.memory_type == MemoryType.SEMANTIC and entry.tags:
            topic_key = f"{entry.tags[0]}/{developer_id}"

        body: dict[str, Any] = {
            "session_id": session_id,
            "type": engram_type,
            "title": title,
            "content": content,
            "project": self._project,
            "scope": scope,
            "tool_name": f"aidlc-memory:{developer_id}",
        }
        if topic_key:
            body["topic_key"] = topic_key

        resp = self._post("/observations", body)

        # Engram returns the observation with an `id` field
        if resp and isinstance(resp, dict):
            engram_id = resp.get("id") or resp.get("observation", {}).get("id")
            if engram_id is not None:
                entry.metadata["engram_id"] = engram_id

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
        # Build Engram search query
        q_parts: list[str] = []
        if query:
            q_parts.append(query)
        if tags:
            q_parts.extend(tags)
        if not q_parts:
            q_parts.append("*")

        params: dict[str, str] = {
            "q": " ".join(q_parts),
            "project": self._project,
            "limit": str(min(limit, 100)),
        }

        if memory_type is not None:
            engram_type = _TYPE_MAP.get(memory_type)
            if engram_type:
                params["type"] = engram_type

        if not include_shared:
            params["scope"] = "personal"

        resp = self._get("/search", params)
        if not resp:
            return []

        # Parse Engram search results into MemoryEntry objects
        observations = resp if isinstance(resp, list) else resp.get("observations", [])
        entries: list[MemoryEntry] = []
        for obs in observations:
            entry = self._observation_to_entry(obs, developer_id)
            if entry:
                entries.append(entry)

        return entries[:limit]

    def delete(self, developer_id: str, entry_id: str) -> bool:
        # entry_id might be our internal ID or an engram observation ID
        try:
            obs_id = int(entry_id)
        except (ValueError, TypeError):
            return False

        try:
            self._request("DELETE", f"/observations/{obs_id}")
            return True
        except Exception:
            return False

    def get_profile(self, developer_id: str) -> dict[str, Any]:
        # Search for the profile observation
        params = {
            "q": f"aidlc-profile {developer_id}",
            "project": self._project,
            "type": "config",
            "scope": "personal",
            "limit": "1",
        }
        resp = self._get("/search", params)
        if not resp:
            return {}
        observations = resp if isinstance(resp, list) else resp.get("observations", [])
        for obs in observations:
            tool = obs.get("tool_name", "")
            if f"aidlc-profile:{developer_id}" in tool:
                try:
                    return json.loads(obs.get("content", "{}"))
                except Exception:
                    return {}
        return {}

    def update_profile(self, developer_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_profile(developer_id)
        existing.update(updates)
        existing["updated_at"] = datetime.now(timezone.utc).isoformat()

        session_id = self._ensure_session(developer_id)
        body = {
            "session_id": session_id,
            "type": "config",
            "title": f"aidlc-profile {developer_id}",
            "content": json.dumps(existing, ensure_ascii=False),
            "project": self._project,
            "scope": "personal",
            "tool_name": f"aidlc-profile:{developer_id}",
            "topic_key": f"developer/{developer_id}/profile",
        }
        self._post("/observations", body)
        return existing

    def list_developers(self) -> list[str]:
        # Search for all aidlc-memory tool observations to find unique developer IDs
        params = {
            "q": "aidlc-memory aidlc-profile",
            "project": self._project,
            "limit": "100",
        }
        resp = self._get("/search", params)
        if not resp:
            return []

        observations = resp if isinstance(resp, list) else resp.get("observations", [])
        devs: set[str] = set()
        for obs in observations:
            tool = obs.get("tool_name", "")
            for prefix in ("aidlc-memory:", "aidlc-profile:"):
                if prefix in tool:
                    dev = tool.split(prefix, 1)[-1]
                    if dev:
                        devs.add(dev)
        return sorted(devs)

    def compact(self, developer_id: str) -> int:
        # Engram handles dedup/compaction via topic_key upsert; no-op here
        return 0

    def share(self, developer_id: str, entry_id: str) -> bool:
        try:
            obs_id = int(entry_id)
        except (ValueError, TypeError):
            return False
        try:
            self._request("PATCH", f"/observations/{obs_id}", {"scope": "project"})
            return True
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Health check
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Check if Engram is running and reachable."""
        try:
            resp = self._get("/health")
            return isinstance(resp, dict) and resp.get("status") == "ok"
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_session(self, developer_id: str) -> str:
        """Get or create an Engram session for this developer."""
        if developer_id in self._session_ids:
            return self._session_ids[developer_id]

        # Create a new session
        session_id = f"aidlc-{developer_id}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')}"
        try:
            self._post("/sessions", {
                "id": session_id,
                "project": self._project,
                "directory": ".",
            })
        except Exception:
            pass  # Session might already exist
        self._session_ids[developer_id] = session_id
        return session_id

    def _format_content(self, entry: MemoryEntry) -> str:
        """Format entry content in Engram's What/Why/Where/Learned structure."""
        parts = [f"**What**: {entry.content}"]
        if entry.metadata.get("why"):
            parts.append(f"**Why**: {entry.metadata['why']}")
        if entry.metadata.get("where"):
            parts.append(f"**Where**: {entry.metadata['where']}")
        if entry.metadata.get("learned"):
            parts.append(f"**Learned**: {entry.metadata['learned']}")
        if entry.tags:
            parts.append(f"**Tags**: {', '.join(entry.tags)}")
        if entry.developer_id:
            parts.append(f"**Developer**: {entry.developer_id}")
        return "\n".join(parts)

    def _observation_to_entry(self, obs: dict, developer_id: str) -> MemoryEntry | None:
        """Convert an Engram observation dict to a MemoryEntry."""
        try:
            content = obs.get("content", "")
            # Extract the "What" line if present
            for line in content.split("\n"):
                if line.startswith("**What**:"):
                    content = line.replace("**What**:", "").strip()
                    break

            engram_type = obs.get("type", "discovery")
            memory_type = _REVERSE_TYPE_MAP.get(engram_type, MemoryType.SEMANTIC)
            scope = Scope.SHARED if obs.get("scope") == "project" else Scope.PRIVATE

            # Extract tags from content
            tags: list[str] = []
            for line in (obs.get("content") or "").split("\n"):
                if line.startswith("**Tags**:"):
                    tags = [t.strip() for t in line.replace("**Tags**:", "").split(",") if t.strip()]
                    break
            # Also extract from title brackets
            title = obs.get("title", "")
            if title.startswith("[") and "]" in title:
                bracket_tags = title[1:title.index("]")]
                tags.extend(t.strip() for t in bracket_tags.split(",") if t.strip())

            # Extract developer from tool_name
            tool_name = obs.get("tool_name", "")
            obs_dev = developer_id
            if "aidlc-memory:" in tool_name:
                obs_dev = tool_name.split("aidlc-memory:", 1)[-1]

            return MemoryEntry(
                content=content,
                memory_type=memory_type,
                scope=scope,
                tags=list(set(tags)),
                metadata={"engram_id": obs.get("id"), "engram_type": engram_type},
                id=str(obs.get("id", "")),
                created_at=obs.get("created_at", datetime.now(timezone.utc).isoformat()),
                developer_id=obs_dev,
            )
        except Exception:
            return None

    # ------------------------------------------------------------------
    # HTTP primitives (stdlib only, no requests dependency)
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict[str, str] | None = None) -> Any:
        return self._request("GET", path, params=params)

    def _post(self, path: str, body: dict) -> Any:
        return self._request("POST", path, body=body)

    def _request(
        self,
        method: str,
        path: str,
        body: dict | None = None,
        params: dict[str, str] | None = None,
    ) -> Any:
        url = f"{self._base}{path}"
        if params:
            url += "?" + urllib.parse.urlencode(params)

        data = None
        if body is not None:
            data = json.dumps(body, ensure_ascii=False).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=data,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                raw = resp.read().decode("utf-8")
                if raw.strip():
                    return json.loads(raw)
                return {}
        except urllib.error.HTTPError as e:
            body_text = ""
            try:
                body_text = e.read().decode("utf-8", errors="replace")
            except Exception:
                pass
            raise ConnectionError(
                f"Engram HTTP {e.code} on {method} {path}: {body_text}"
            ) from e
        except urllib.error.URLError as e:
            raise ConnectionError(f"Engram unreachable at {self._base}: {e}") from e
