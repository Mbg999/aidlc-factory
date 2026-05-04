#!/usr/bin/env python3
"""Memory subagent for AIDLC.

Provides persistent, cross-session, multi-developer memory accessible
via the standard subagent manager interface.

Actions (passed via context["action"]):
  remember   – Store a memory entry
  recall     – Query memory entries
  context    – Get a preformatted context string for LLM injection
  forget     – Delete a specific entry by ID
  compact    – Remove expired entries
  share      – Promote a private entry to shared
  profile    – Get or update developer profile
  list_devs  – List all known developers

Required context keys:
  developer_id  – Who is operating (required for all actions)
  action        – One of the above

Example:
  run({"developer_id": "miguel", "action": "remember",
       "content": "API uses FastAPI + Pydantic v2", "tags": ["arch"]})
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

# Allow running both as a subagent (subprocess) and imported directly
try:
    from memory import MemoryStore, MemoryEntry, MemoryType
    from memory.types import Scope
except ImportError:
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from memory import MemoryStore, MemoryEntry, MemoryType
    from memory.types import Scope

AGENT_ID = "memory"

# Default memory root: repo-level .aidlc-memory
REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_MEMORY_ROOT = REPO_ROOT / ".aidlc-memory"


def _get_store(ctx: dict) -> MemoryStore:
    """Resolve the memory store from context.

    Supports optional Engram backend via context keys or env vars:
      ctx["memory_backend"] = "engram"  (or env AIDLC_MEMORY_BACKEND)
      ctx["engram_url"]     = "http://127.0.0.1:7437"  (or env AIDLC_ENGRAM_URL)
      ctx["engram_project"] = "my-project"  (or env AIDLC_ENGRAM_PROJECT)
    """
    import os

    memory_root = ctx.get("memory_root") or str(DEFAULT_MEMORY_ROOT)

    backend = (ctx.get("memory_backend") or os.environ.get("AIDLC_MEMORY_BACKEND", "")).lower()
    if backend == "engram":
        engram_url = ctx.get("engram_url") or os.environ.get("AIDLC_ENGRAM_URL", "http://127.0.0.1:7437")
        engram_project = ctx.get("engram_project") or os.environ.get("AIDLC_ENGRAM_PROJECT", "aidlc")
        return MemoryStore.with_engram(
            memory_root,
            engram_url=engram_url,
            project=engram_project,
        )

    return MemoryStore(memory_root)


def run(context: dict | None = None) -> dict[str, Any]:
    ctx = context or {}
    dev_id = ctx.get("developer_id", "").strip()
    action = ctx.get("action", "").strip()

    if not dev_id:
        return {"agent_id": AGENT_ID, "status": "error", "error": "developer_id is required"}

    if not action:
        return {"agent_id": AGENT_ID, "status": "error", "error": "action is required"}

    store = _get_store(ctx)

    try:
        if action == "remember":
            return _action_remember(store, dev_id, ctx)
        elif action == "recall":
            return _action_recall(store, dev_id, ctx)
        elif action == "context":
            return _action_context(store, dev_id, ctx)
        elif action == "forget":
            return _action_forget(store, dev_id, ctx)
        elif action == "compact":
            return _action_compact(store, dev_id, ctx)
        elif action == "share":
            return _action_share(store, dev_id, ctx)
        elif action == "profile":
            return _action_profile(store, dev_id, ctx)
        elif action == "list_devs":
            return _action_list_devs(store)
        else:
            return {"agent_id": AGENT_ID, "status": "error", "error": f"unknown action: {action}"}
    except Exception as e:
        return {"agent_id": AGENT_ID, "status": "error", "error": str(e)}


# ------------------------------------------------------------------
# Action handlers
# ------------------------------------------------------------------

def _action_remember(store: MemoryStore, dev_id: str, ctx: dict) -> dict:
    content = ctx.get("content", "")
    if not content:
        return {"agent_id": AGENT_ID, "status": "error", "error": "content is required for remember"}

    mt = MemoryType(ctx["memory_type"]) if ctx.get("memory_type") else MemoryType.SEMANTIC
    sc = Scope(ctx["scope"]) if ctx.get("scope") else Scope.PRIVATE

    entry = store.remember(
        developer_id=dev_id,
        content=content,
        memory_type=mt,
        scope=sc,
        tags=ctx.get("tags", []),
        metadata=ctx.get("metadata", {}),
        session_id=ctx.get("session_id", ""),
        ttl_hours=ctx.get("ttl_hours"),
    )
    return {"agent_id": AGENT_ID, "status": "ok", "entry_id": entry.id, "entry": entry.to_dict()}


def _action_recall(store: MemoryStore, dev_id: str, ctx: dict) -> dict:
    mt = MemoryType(ctx["memory_type"]) if ctx.get("memory_type") else None
    entries = store.recall(
        developer_id=dev_id,
        tags=ctx.get("tags"),
        memory_type=mt,
        query=ctx.get("query"),
        limit=ctx.get("limit", 50),
        include_shared=ctx.get("include_shared", True),
        include_expired=ctx.get("include_expired", False),
    )
    return {
        "agent_id": AGENT_ID,
        "status": "ok",
        "count": len(entries),
        "entries": [e.to_dict() for e in entries],
    }


def _action_context(store: MemoryStore, dev_id: str, ctx: dict) -> dict:
    text = store.recall_context(
        developer_id=dev_id,
        tags=ctx.get("tags"),
        limit=ctx.get("limit", 20),
    )
    return {"agent_id": AGENT_ID, "status": "ok", "context_text": text}


def _action_forget(store: MemoryStore, dev_id: str, ctx: dict) -> dict:
    entry_id = ctx.get("entry_id", "")
    if not entry_id:
        return {"agent_id": AGENT_ID, "status": "error", "error": "entry_id required"}
    removed = store.forget(dev_id, entry_id)
    return {"agent_id": AGENT_ID, "status": "ok", "removed": removed}


def _action_compact(store: MemoryStore, dev_id: str, ctx: dict) -> dict:
    count = store.compact(dev_id)
    return {"agent_id": AGENT_ID, "status": "ok", "removed_count": count}


def _action_share(store: MemoryStore, dev_id: str, ctx: dict) -> dict:
    entry_id = ctx.get("entry_id", "")
    if not entry_id:
        return {"agent_id": AGENT_ID, "status": "error", "error": "entry_id required"}
    shared = store.share(dev_id, entry_id)
    return {"agent_id": AGENT_ID, "status": "ok", "shared": shared}


def _action_profile(store: MemoryStore, dev_id: str, ctx: dict) -> dict:
    updates = ctx.get("profile_updates")
    if updates and isinstance(updates, dict):
        profile = store.update_profile(dev_id, updates)
    else:
        profile = store.get_profile(dev_id)
    return {"agent_id": AGENT_ID, "status": "ok", "profile": profile}


def _action_list_devs(store: MemoryStore) -> dict:
    devs = store.list_developers()
    return {"agent_id": AGENT_ID, "status": "ok", "developers": devs}


if __name__ == "__main__":
    import sys

    ctx: dict = {}
    if len(sys.argv) > 1:
        try:
            ctx = json.loads(sys.argv[1])
        except Exception:
            ctx = {"action": sys.argv[1]}
    print(json.dumps(run(ctx), ensure_ascii=False, indent=2))
