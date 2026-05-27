from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
RUN_PY = SCRIPTS / "factory_run.py"


def test_generate_run_id_default_slug():
    result = subprocess.run(
        [sys.executable, str(RUN_PY), "generate-run-id"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    rid = result.stdout.strip()
    assert rid.endswith("-run"), f"expected default slug '-run', got {rid!r}"
    assert "T" in rid and "Z" in rid, f"expected ISO-like ts, got {rid!r}"


def test_generate_run_id_custom_slug():
    result = subprocess.run(
        [sys.executable, str(RUN_PY), "generate-run-id", "--slug", "my-feature"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    rid = result.stdout.strip()
    assert rid.endswith("-my-feature"), f"expected slug '-my-feature', got {rid!r}"
    # Verify it matches _RUN_ID_RE
    assert re.match(r"^[a-zA-Z0-9_.-]+$", rid), f"run_id {rid!r} fails validation"


def test_generate_run_id_slug_with_spaces():
    """Spaces in slug should be replaced with hyphens."""
    result = subprocess.run(
        [sys.executable, str(RUN_PY), "generate-run-id", "--slug", "my feature"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    rid = result.stdout.strip()
    assert rid.endswith("-my-feature"), f"expected slug '-my-feature', got {rid!r}"


def test_generate_run_id_format():
    """Verify the timestamp portion matches YYYY-MM-DDTHH-MM-SSZ."""
    result = subprocess.run(
        [sys.executable, str(RUN_PY), "generate-run-id", "--slug", "x"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    rid = result.stdout.strip()
    ts_part = rid.removesuffix("-x")
    # Basic shape: 4-2-2 T 2-2-2 Z
    parts = ts_part.split("T")
    assert len(parts) == 2, f"expected dateTtime, got {ts_part!r}"
    date_part, time_part = parts
    assert time_part.endswith("Z"), f"expected Z suffix, got {time_part!r}"
    time_stripped = time_part[:-1]  # remove Z
    assert len(time_stripped.split("-")) == 3, f"expected HH-MM-SS, got {time_stripped!r}"
    assert len(date_part.split("-")) == 3, f"expected YYYY-MM-DD, got {date_part!r}"


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


# ── --next-cmd (B3 substitution helper) ───────────────────────────────────────

import importlib.util as _ilu
_spec = _ilu.spec_from_file_location("factory_run_mod", RUN_PY)
_factory_run_mod = _ilu.module_from_spec(_spec)
_spec.loader.exec_module(_factory_run_mod)


def test_next_command_empty_manifest():
    assert _factory_run_mod._next_command("r1", {"completed_stages": []}) is None


def test_next_command_after_phase0():
    m = {"completed_stages": ["workspace-scout", "requirements-analyst"]}
    assert _factory_run_mod._next_command("r1", m) == "/factory-plan r1"


def test_next_command_after_phase1():
    m = {"completed_stages": ["workspace-scout", "requirements-analyst", "workflow-planner"]}
    assert _factory_run_mod._next_command("r1", m) == "/factory-build r1"


def test_next_command_after_build():
    m = {"completed_stages": ["workspace-scout", "requirements-analyst", "workflow-planner",
                              "code-generator", "build-test-agent"]}
    assert _factory_run_mod._next_command("r1", m) == "/factory-review r1"


def test_next_command_after_review():
    m = {"completed_stages": ["workspace-scout", "requirements-analyst", "workflow-planner",
                              "code-generator", "build-test-agent",
                              "reviewer-code", "reviewer-simplifier"]}
    assert _factory_run_mod._next_command("r1", m) == "/factory-ship r1"


def test_next_command_after_ship_returns_none():
    m = {"completed_stages": ["workspace-scout", "requirements-analyst", "workflow-planner",
                              "code-generator", "build-test-agent",
                              "reviewer-code", "ship-agent"]}
    assert _factory_run_mod._next_command("r1", m) is None


def test_next_command_cli_with_real_manifest(env_setup, run_id):
    subprocess.run(
        [sys.executable, str(RUN_PY), "init", run_id, "--user-request", "test"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    subprocess.run(
        [sys.executable, str(RUN_PY), "complete-stage", run_id, "workspace-scout"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    subprocess.run(
        [sys.executable, str(RUN_PY), "complete-stage", run_id, "requirements-analyst"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    result = subprocess.run(
        [sys.executable, str(RUN_PY), "status", run_id, "--next-cmd"],
        capture_output=True, text=True, env={**__import__("os").environ},
    )
    assert result.returncode == 0
    assert result.stdout.strip() == f"/factory-plan {run_id}"
    # Critical: literal run_id present, no `<run-id>` placeholder leaking
    assert "<run-id>" not in result.stdout


# ── _flock / _acquire_lock / _release_lock (Bug B regression) ────────────────

import threading


class TestFlock:
    def test_acquire_release_no_error(self, tmp_path):
        """Basic acquire + release should not raise on any platform."""
        lockfile = tmp_path / "test.lock"
        lf = lockfile.open("a")
        _factory_run_mod._acquire_lock(lf)
        _factory_run_mod._release_lock(lf)
        lf.close()

    def test_context_manager_acquires_and_releases(self, tmp_path):
        """The _flock CM should acquire on enter and release on exit."""
        path = tmp_path / "target.txt"
        with _factory_run_mod._flock(path):
            path.write_text("locked write")
        assert path.read_text() == "locked write"

    def test_mutual_exclusion(self, tmp_path):
        """Two concurrent writers under _flock must not interleave writes."""
        path = tmp_path / "shared.txt"
        barrier = threading.Barrier(2, timeout=10)
        results: list[str] = []

        def writer(letter: str, count: int):
            barrier.wait()
            for _ in range(count):
                with _factory_run_mod._flock(path):
                    content = path.read_text() if path.exists() else ""
                    path.write_text(content + letter)

        t1 = threading.Thread(target=writer, args=("A", 50))
        t2 = threading.Thread(target=writer, args=("B", 50))
        t1.start()
        t2.start()
        t1.join()
        t2.join()

        text = path.read_text()
        assert len(text) == 100
        assert text.count("A") == 50
        assert text.count("B") == 50

    def test_dedupe_prevents_duplicate_blocks(self, tmp_path):
        """_append_audit_block should not write the same phase+label twice."""
        saved_docs = _factory_run_mod.AIDLC_DOCS
        _factory_run_mod.AIDLC_DOCS = tmp_path / "aidlc-docs"
        try:
            audit = _factory_run_mod.AIDLC_DOCS / "audit.md"
            first = _factory_run_mod._append_audit_block(
                "2026-05-25T10:00:00", "INCEPTION - Planning", "ComplexityGov", ["skip=story-writer"],
            )
            assert first is True
            assert audit.exists()
            second = _factory_run_mod._append_audit_block(
                "2026-05-25T10:00:00", "INCEPTION - Planning", "ComplexityGov", ["skip=story-writer"],
            )
            assert second is False
        finally:
            _factory_run_mod.AIDLC_DOCS = saved_docs

    def test_chronology_violation_dies(self, tmp_path):
        """An older timestamp after a newer one should trigger _die (sys.exit)."""
        saved_docs = _factory_run_mod.AIDLC_DOCS
        _factory_run_mod.AIDLC_DOCS = tmp_path / "aidlc-docs"
        try:
            _factory_run_mod._append_audit_block(
                "2026-05-25T10:01:00", "INCEPTION - Build", "CodeGen", ["feat: done"],
            )
            with pytest.raises(SystemExit):
                _factory_run_mod._append_audit_block(
                    "2026-05-25T10:00:00", "INCEPTION - Build", "CodeGen", ["cannot go back"],
                )
        finally:
            _factory_run_mod.AIDLC_DOCS = saved_docs

    # ── import-failure fallback paths ──────────────────────────────────────

    def test_fcntl_unavailable_falls_through(self, tmp_path):
        """When fcntl is removed from sys.modules, _acquire_lock should
        fall through to msvcrt (or no-op on macOS) without raising."""
        lockfile = tmp_path / "test.lock"
        lf = lockfile.open("a")
        saved = sys.modules.pop("fcntl", None)
        try:
            _factory_run_mod._acquire_lock(lf)
            _factory_run_mod._release_lock(lf)
        finally:
            if saved is not None:
                sys.modules["fcntl"] = saved
        lf.close()

    def test_both_fcntl_and_msvcrt_unavailable_falls_through(self, tmp_path):
        """When both locking modules are absent, the no-op path must not
        raise. This is the WASM / exotic-platform safety net."""
        lockfile = tmp_path / "test.lock"
        lf = lockfile.open("a")
        saved_fcntl = sys.modules.pop("fcntl", None)
        saved_msvcrt = sys.modules.pop("msvcrt", None)
        try:
            _factory_run_mod._acquire_lock(lf)
            _factory_run_mod._release_lock(lf)
        finally:
            if saved_fcntl is not None:
                sys.modules["fcntl"] = saved_fcntl
            if saved_msvcrt is not None:
                sys.modules["msvcrt"] = saved_msvcrt
        lf.close()

    def test_append_audit_block_still_works_without_fcntl(self, tmp_path):
        """The end-to-end audit write must work even when fcntl is absent."""
        saved_docs = _factory_run_mod.AIDLC_DOCS
        _factory_run_mod.AIDLC_DOCS = tmp_path / "aidlc-docs"
        saved_fcntl = sys.modules.pop("fcntl", None)
        try:
            result = _factory_run_mod._append_audit_block(
                "2026-05-25T10:00:00",
                "INCEPTION - Planning",
                "ComplexityGov",
                ["skip=story-writer"],
            )
            assert result is True
        finally:
            if saved_fcntl is not None:
                sys.modules["fcntl"] = saved_fcntl
            _factory_run_mod.AIDLC_DOCS = saved_docs
