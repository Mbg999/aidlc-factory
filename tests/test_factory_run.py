from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
RUN_PY = SCRIPTS / "factory_run.py"


def test_init_and_status(env_setup, run_id):
    result = subprocess.run(
        [sys.executable, str(RUN_PY), "init", run_id, "--user-request", "test request"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert result.returncode == 0
    assert "initialized" in result.stdout

    result2 = subprocess.run(
        [sys.executable, str(RUN_PY), "status", run_id],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert result2.returncode == 0
    assert run_id in result2.stdout


def test_init_force(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(RUN_PY), "init", run_id, "--user-request", "first"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    # Without --force, should fail
    result = subprocess.run(
        [sys.executable, str(RUN_PY), "init", run_id, "--user-request", "second"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert result.returncode == 2

    # With --force, should succeed
    result2 = subprocess.run(
        [sys.executable, str(RUN_PY), "init", run_id, "--user-request", "third", "--force"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert result2.returncode == 0


def test_complete_stage_and_resume(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(RUN_PY), "init", run_id, "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )

    # Complete first stage
    result = subprocess.run(
        [sys.executable, str(RUN_PY), "complete-stage", run_id, "workspace-scout",
         "--next-stage", "reverse-engineer"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert result.returncode == 0
    assert "complete" in result.stdout

    # Resume should suggest reverse-engineer
    result2 = subprocess.run(
        [sys.executable, str(RUN_PY), "resume", run_id],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    data = json.loads(result2.stdout)
    assert data["completed_count"] == 1
    assert data["next_stage_suggestion"] == "reverse-engineer"


def test_complete_stage_idempotent(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(RUN_PY), "init", run_id, "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )
    subprocess.run(
        [sys.executable, str(RUN_PY), "complete-stage", run_id, "workspace-scout"],
        capture_output=True, env={**__import__("os").environ},
    )
    result = subprocess.run(
        [sys.executable, str(RUN_PY), "complete-stage", run_id, "workspace-scout"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert "idempotent" in result.stdout


def test_fail_stage(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(RUN_PY), "init", run_id, "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )
    result = subprocess.run(
        [sys.executable, str(RUN_PY), "fail-stage", run_id, "workspace-scout",
         "--reason", "syntax error"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert result.returncode == 0
    assert "syntax error" in result.stdout

    result2 = subprocess.run(
        [sys.executable, str(RUN_PY), "status", run_id, "--json"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    data = json.loads(result2.stdout)
    assert len(data["failed_stages"]) == 1
    assert data["failed_stages"][0]["stage"] == "workspace-scout"


def test_next_stage_ordering(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(RUN_PY), "init", run_id, "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )

    stages = ["workspace-scout", "reverse-engineer", "requirements-analyst"]
    for s in stages:
        subprocess.run(
            [sys.executable, str(RUN_PY), "complete-stage", run_id, s],
            capture_output=True, env={**__import__("os").environ},
        )

    result = subprocess.run(
        [sys.executable, str(RUN_PY), "resume", run_id],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    data = json.loads(result.stdout)
    assert data["completed_count"] == 3
    assert data["next_stage_suggestion"] == "story-writer"


def test_emit_event(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(RUN_PY), "init", run_id, "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )
    result = subprocess.run(
        [sys.executable, str(RUN_PY), "emit", run_id, "--evt", "spawn_start", "--stage", "code-gen"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["evt"] == "spawn_start"


def test_replay(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(RUN_PY), "init", run_id, "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )
    for s in ["workspace-scout", "reverse-engineer", "requirements-analyst"]:
        subprocess.run(
            [sys.executable, str(RUN_PY), "complete-stage", run_id, s],
            capture_output=True, env={**__import__("os").environ},
        )

    result = subprocess.run(
        [sys.executable, str(RUN_PY), "replay", run_id, "--from", "workspace-scout"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    data = json.loads(result.stdout)
    assert data["replayed_from"] == "workspace-scout"
    assert len(data["rolled_back"]) == 3


def test_tail_empty_timeline(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(RUN_PY), "init", run_id, "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )
    result = subprocess.run(
        [sys.executable, str(RUN_PY), "tail", run_id],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert result.returncode == 0


def test_set_field(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(RUN_PY), "init", run_id, "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )
    result = subprocess.run(
        [sys.executable, str(RUN_PY), "set", run_id, "--field", "project_profile.ui=true"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert result.returncode == 0

    result2 = subprocess.run(
        [sys.executable, str(RUN_PY), "status", run_id, "--json"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    data = json.loads(result2.stdout)
    assert data["project_profile"]["ui"] is True
