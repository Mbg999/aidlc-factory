from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
CACHE_PY = SCRIPTS / "factory_build_cache.py"


def _cache(args, env_setup):
    return subprocess.run(
        [sys.executable, str(CACHE_PY)] + args,
        capture_output=True, text=True, env={**__import__("os").environ},
    )


def test_cache_miss(env_setup, run_id):
    r = _cache(["check", run_id, "unit-a", "--hash", "deadbeef"], env_setup)
    assert r.returncode == 1
    data = json.loads(r.stdout)
    assert data["hit"] is False


def test_cache_save_and_hit(env_setup, run_id):
    _cache(["save", run_id, "unit-a", "--hash", "abc123", "--status", "complete"], env_setup)
    r = _cache(["check", run_id, "unit-a", "--hash", "abc123"], env_setup)
    assert r.returncode == 0
    data = json.loads(r.stdout)
    assert data["hit"] is True
    assert data["result"]["status"] == "complete"


def test_cache_hash_computation(env_setup):
    r = _cache(["hash", "--files", "aidlc-scripts/VERSION"], env_setup)
    data = json.loads(r.stdout)
    assert "hash" in data
    assert len(data["hash"]) == 16
