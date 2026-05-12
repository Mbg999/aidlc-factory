from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
RUN_PY = SCRIPTS / "factory_run.py"


def test_complete_stage_with_reason(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(RUN_PY), "init", run_id, "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )
    result = subprocess.run(
        [sys.executable, str(RUN_PY), "complete-stage", run_id, "workspace-scout",
         "--next-stage", "reverse-engineer", "--reason", "crash_safe"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert result.returncode == 0

    # Check manifest has last_action_reason
    result2 = subprocess.run(
        [sys.executable, str(RUN_PY), "status", run_id, "--json"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    data = json.loads(result2.stdout)
    assert data.get("last_action_reason") == "crash_safe"


def test_resume_with_reconcile(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(RUN_PY), "init", run_id, "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )
    subprocess.run(
        [sys.executable, str(RUN_PY), "complete-stage", run_id, "workspace-scout"],
        capture_output=True, env={**__import__("os").environ},
    )
    result = subprocess.run(
        [sys.executable, str(RUN_PY), "resume", run_id],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    data = json.loads(result.stdout)
    assert "reconcile" in data
    assert "drift" in data["reconcile"]
    # Should not have drift in a clean run
    assert data["reconcile"]["drift"] is False


def test_status_latency_no_events(env_setup, run_id):
    """status --latency on a run with no human events should show minimal output."""
    subprocess.run(
        [sys.executable, str(RUN_PY), "init", run_id, "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )
    result = subprocess.run(
        [sys.executable, str(RUN_PY), "status", run_id, "--latency"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert result.returncode == 0
    assert "Latency" in result.stdout
