from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
BUDGET_PY = SCRIPTS / "factory_budget.py"


def test_init(env_setup, run_id):
    result = subprocess.run(
        [sys.executable, str(BUDGET_PY), "init", run_id],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert result.returncode == 0
    assert "initialized" in result.stdout

    # Status should show the initialized budget
    result2 = subprocess.run(
        [sys.executable, str(BUDGET_PY), "status", run_id],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert result2.returncode == 0
    assert run_id in result2.stdout


def test_check_ok(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(BUDGET_PY), "init", run_id],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    result = subprocess.run(
        [sys.executable, str(BUDGET_PY), "check", run_id, "workspace-scout"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert data["decision"] == "ok"


def test_check_halt_on_exhausted_wall_clock(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(BUDGET_PY), "init", run_id],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    # Deduct enough wall time to exhaust budget
    subprocess.run(
        [sys.executable, str(BUDGET_PY), "deduct", run_id, "workspace-scout",
         "--wall-min", "250"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    result = subprocess.run(
        [sys.executable, str(BUDGET_PY), "check", run_id, "workspace-scout"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    data = json.loads(result.stdout)
    assert data["decision"] == "halt"
    assert data["reason"] == "wall_clock_exhausted"


def test_check_halt_on_exhausted_estimate(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(BUDGET_PY), "init", run_id],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    # Deduct close to max tokens
    subprocess.run(
        [sys.executable, str(BUDGET_PY), "deduct", run_id, "workspace-scout",
         "--tokens-in", "4900000"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    result = subprocess.run(
        [sys.executable, str(BUDGET_PY), "check", run_id, "code-generator"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    data = json.loads(result.stdout)
    # code-generator est 500K, remaining < that, and it's not optional
    assert data["decision"] == "halt"
    assert data["reason"] == "estimated_tokens_exceed_remaining"


def test_deduct_tracking(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(BUDGET_PY), "init", run_id],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    result = subprocess.run(
        [sys.executable, str(BUDGET_PY), "deduct", run_id, "workspace-scout",
         "--tokens-in", "10000", "--tokens-out", "20000", "--wall-min", "3.5"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert result.returncode == 0
    assert "30,000 tokens" in result.stdout
    assert "3.5m" in result.stdout

    # Verify via status
    result2 = subprocess.run(
        [sys.executable, str(BUDGET_PY), "status", run_id],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert result2.returncode == 0
    assert "30000" in result2.stdout or "30,000" in result2.stdout


def test_deduct_negative_rejected(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(BUDGET_PY), "init", run_id],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    result = subprocess.run(
        [sys.executable, str(BUDGET_PY), "deduct", run_id, "workspace-scout",
         "--tokens-in", "-100"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert result.returncode == 2
    assert "negative" in result.stderr


def test_skip_optional_stage(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(BUDGET_PY), "init", run_id],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    # Deduct so remaining is under threshold%
    subprocess.run(
        [sys.executable, str(BUDGET_PY), "deduct", run_id, "workspace-scout",
         "--tokens-in", "4000000"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    result = subprocess.run(
        [sys.executable, str(BUDGET_PY), "check", run_id, "unit-decomposer"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    # unit-decomposer is optional, under threshold → skip
    data = json.loads(result.stdout)
    assert data["decision"] == "skip"
