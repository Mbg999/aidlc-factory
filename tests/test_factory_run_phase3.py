from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
RUN_PY = SCRIPTS / "factory_run.py"


def test_init_sets_orchestrator_version(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(RUN_PY), "init", run_id, "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )
    result = subprocess.run(
        [sys.executable, str(RUN_PY), "status", run_id, "--json"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    data = json.loads(result.stdout)
    assert "orchestrator_version" in data
    assert data["orchestrator_version"] != ""


def test_resume_version_warning(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(RUN_PY), "init", run_id, "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )
    # Set a different version to trigger warning
    subprocess.run(
        [sys.executable, str(RUN_PY), "set", run_id, "--field",
         "orchestrator_version=0.1.0"],
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
    assert "version_warning" in data
    assert "0.1.0" in data["version_warning"]
