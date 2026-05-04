"""Example Code Reviewer subagent.

This is intentionally minimal: real implementations should run linters, security
scanners, and produce structured reports. The `run(context)` function below is
the only required entrypoint used by `manager.py`.
"""
from __future__ import annotations

def run(context: dict | None = None) -> dict:
    context = context or {}
    notes = []
    if isinstance(context, dict) and context.get("sample"):
        notes.append("Received sample payload")
    # Minimal mock checks
    notes.append("Lint: OK")
    notes.append("Security: OK")

    return {"agent_id": "code-reviewer", "status": "ok", "notes": notes}
