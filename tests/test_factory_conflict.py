from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
CONFLICT_PY = SCRIPTS / "factory_conflict.py"


def _run(args, env_setup, text=True):
    return subprocess.run(
        [sys.executable, str(CONFLICT_PY)] + args,
        capture_output=True, text=text, env={**__import__("os").environ},
    )


def test_acquire_and_release(env_setup, run_id):
    # First create run via init
    subprocess.run(
        [sys.executable, str(SCRIPTS / "factory_run.py"), "init", run_id,
         "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )

    r = _run(["acquire", run_id, "code-gen:auth", "--mode", "write", "src/auth/**"], env_setup)
    assert r.returncode == 0
    assert "GRANTED" in r.stderr

    r = _run(["list", run_id], env_setup)
    assert "code-gen:auth" in r.stdout

    r = _run(["release", run_id, "code-gen:auth"], env_setup)
    assert "RELEASED" in r.stdout


def test_acquire_conflict(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(SCRIPTS / "factory_run.py"), "init", run_id,
         "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )

    _run(["acquire", run_id, "code-gen:auth", "src/auth/**"], env_setup)
    # Second holder wants overlapping glob
    r = _run(["acquire", run_id, "code-gen:users", "src/auth/users.py"], env_setup)
    assert r.returncode == 1
    assert "CONFLICT" in r.stderr


def test_read_lock_no_conflict(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(SCRIPTS / "factory_run.py"), "init", run_id,
         "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )

    _run(["acquire", run_id, "reader1", "--mode", "read", "src/auth/**"], env_setup)
    # Another reader should not conflict
    r = _run(["acquire", run_id, "reader2", "--mode", "read", "src/auth/users.py"], env_setup)
    assert r.returncode == 0


def test_ttl_expiry(env_setup, run_id):
    """Lock with TTL should auto-release when stale."""
    subprocess.run(
        [sys.executable, str(SCRIPTS / "factory_run.py"), "init", run_id,
         "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )

    # Acquire with 0 TTL (immediately expired)
    r = _run(["acquire", run_id, "code-gen:auth", "src/auth/**", "--ttl-minutes", "0"], env_setup)
    assert r.returncode == 0

    # List should show it
    r = _run(["list", run_id, "--json"], env_setup)
    locks = json.loads(r.stdout)
    assert len(locks) == 1
    assert locks[0]["ttl_minutes"] == 0

    # Stale release should clean it
    r = _run(["release", run_id, "--stale", "--older-than", "0"], env_setup)
    assert r.returncode == 0
    r = _run(["list", run_id], env_setup)
    assert "no active locks" in r.stdout


def test_patterns_overlap():
    """Test the internal patterns_overlap function via check-wave."""
    # Unit test the function directly
    import importlib.util
    spec = importlib.util.spec_from_file_location("factory_conflict", CONFLICT_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    assert mod.patterns_overlap("src/auth/**", "src/auth/users.py") is True
    assert mod.patterns_overlap("src/auth/**", "src/billing/main.py") is False
    assert mod.patterns_overlap("src/**", "src/auth/users.py") is True
    assert mod.patterns_overlap("src/auth/login.py", "src/auth/login.py") is True
    assert mod.patterns_overlap("**/config.py", "src/config.py") is True


def test_merge_locks_on_reacquire(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(SCRIPTS / "factory_run.py"), "init", run_id,
         "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )

    _run(["acquire", run_id, "code-gen:auth", "src/auth/**"], env_setup)
    # Re-acquire with additional glob
    _run(["acquire", run_id, "code-gen:auth", "src/shared/**"], env_setup)

    r = _run(["list", run_id, "--json"], env_setup)
    locks = json.loads(r.stdout)
    assert len(locks) == 1
    assert len(locks[0]["globs"]) == 2


def test_check_wave(env_setup, run_id):
    """Test check-wave with a synthetic manifest and handoff files."""
    subprocess.run(
        [sys.executable, str(SCRIPTS / "factory_run.py"), "init", run_id,
         "--user-request", "test"],
        capture_output=True, env={**__import__("os").environ},
    )

    aidlc_root = Path(__import__("os").environ["AIDLC_ROOT"])
    runs_dir = aidlc_root / ".aidlc-orchestrator" / "runs" / run_id

    # Inject synthetic manifest with waves
    import yaml
    manifest_path = runs_dir / "manifest.yaml"
    manifest = yaml.safe_load(manifest_path.read_text())
    manifest["unit_waves"] = [["unit-a", "unit-b"]]
    manifest_path.write_text(yaml.safe_dump(manifest))

    # Inject handoff files with locks_required
    handoffs = runs_dir / "handoffs"
    handoffs.mkdir(parents=True, exist_ok=True)
    for unit, globs in [("unit-a", ["src/auth/**"]), ("unit-b", ["src/auth/users.py"])]:
        inp = {"locks_required": globs}
        (handoffs / f"code-generator.{unit}.input.yaml").write_text(
            yaml.safe_dump(inp))

    r = _run(["check-wave", run_id, "--wave-idx", "0"], env_setup)
    data = json.loads(r.stdout)
    assert data["safe"] is False
    assert len(data["collisions"]) == 1


def test_acquire_run_lock_with_fcntl():
    """_acquire_run_lock works with fcntl available."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("factory_conflict", CONFLICT_PY)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    import tempfile
    lock_path = Path(tempfile.mktemp(suffix=".lock"))
    try:
        # Should not raise with fcntl available on macOS/Linux
        mod._acquire_run_lock(lock_path)
    except Exception as e:
        pytest.fail(f"_acquire_run_lock raised: {e}")
    finally:
        lock_path.unlink(missing_ok=True)


def test_acquire_run_lock_no_fcntl_fallback_noop():
    """_acquire_run_lock does not crash when neither fcntl nor msvcrt exist."""
    import importlib.util
    import builtins

    original_import = builtins.__import__

    def _no_fcntl_import(name, *args, **kwargs):
        if name in ("fcntl", "msvcrt"):
            raise ImportError(f"no {name} (simulated)")
        return original_import(name, *args, **kwargs)

    spec = importlib.util.spec_from_file_location("factory_conflict_lockless", CONFLICT_PY)
    mod = importlib.util.module_from_spec(spec)
    with patch.object(builtins, "__import__", _no_fcntl_import):
        spec.loader.exec_module(mod)

    import tempfile
    lock_path = Path(tempfile.mktemp(suffix=".lock"))
    try:
        # Should return without doing anything (no-op fallback)
        mod._acquire_run_lock(lock_path)
    except Exception as e:
        pytest.fail(f"_acquire_run_lock raised with no lock modules: {e}")
    finally:
        lock_path.unlink(missing_ok=True)
