from __future__ import annotations

import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
BUDGET_PY = SCRIPTS / "factory_budget.py"


def _budget(args, env_setup):
    return subprocess.run(
        [sys.executable, str(BUDGET_PY)] + args,
        capture_output=True, text=True, env={**__import__("os").environ},
    )


def test_trends_no_matching_runs(env_setup):
    r = _budget(["trends", "nonexistent-prefix"], env_setup)
    assert r.returncode != 0
    assert "no runs" in r.stderr or "no runs directory" in r.stderr


def test_trends_with_data(env_setup, run_id):
    # Initialize a run and deduct to create budget data
    _budget(["init", run_id], env_setup)
    _budget(["deduct", run_id, "workspace-scout", "--tokens-in", "10000",
             "--tokens-out", "20000", "--wall-min", "5.0"], env_setup)

    # Now run trends matching this run_id
    r = _budget(["trends", run_id[:8], "--dry-run"], env_setup)
    assert r.returncode == 0
    assert "workspace-scout" in r.stdout
    assert "30,000" in r.stdout  # 10K + 20K
