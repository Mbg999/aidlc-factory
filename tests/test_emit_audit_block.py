"""TDD coverage for `factory_run.py emit_audit_block` (TODO Phase 1).

The helper compiles the substep-6 canonical sequence (timeline emit + dedupe-
guarded audit.md append) into a single atomic call. Every assertion below
captures a guarantee the inline restatements in orchestrator.md used to make.
"""
from __future__ import annotations

import json
import multiprocessing
import os
import re
import subprocess
import sys
import time
from pathlib import Path

import pytest


SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
RUN_PY = SCRIPTS / "factory_run.py"

ENV = lambda: {**os.environ}


def _init(run_id: str):
    return subprocess.run(
        [sys.executable, str(RUN_PY), "init", run_id, "--user-request", "test"],
        capture_output=True, text=True, env=ENV(),
    )


def _emit_audit_block(*args):
    return subprocess.run(
        [sys.executable, str(RUN_PY), "emit_audit_block", *args],
        capture_output=True, text=True, env=ENV(),
    )


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


def test_emit_audit_block_writes_timeline_and_audit(env_setup, run_id):
    _init(run_id)
    r = _emit_audit_block(
        run_id,
        "--evt", "user_decision",
        "--stage", "workflow-planner",
        "--phase", "INCEPTION",
        "--label", "User Decision (workflow-planner)",
        "--field", "decision=approve",
        "--bullet", "[User] Approved execution plan",
        "--bullet", "[User] Free-text note: looks good",
    )
    assert r.returncode == 0, r.stderr

    # 1. Timeline event was emitted with the canonical evt
    timeline = env_setup / ".aidlc-orchestrator" / "runs" / run_id / "timeline.jsonl"
    events = [json.loads(line) for line in timeline.read_text().splitlines() if line.strip()]
    user_events = [e for e in events if e["evt"] == "user_decision"]
    assert len(user_events) == 1
    assert user_events[0]["stage"] == "workflow-planner"
    assert user_events[0]["decision"] == "approve"
    ts_emitted = user_events[0]["ts"]

    # 2. audit.md was appended with header grounded to timeline ts
    audit = env_setup / "aidlc-docs" / "audit.md"
    text = audit.read_text()
    assert f"## {ts_emitted} INCEPTION - User Decision (workflow-planner)" in text
    assert "- [User] Approved execution plan" in text
    assert "- [User] Free-text note: looks good" in text

    # 3. The ts is printed to stdout so callers can capture it
    assert ts_emitted in r.stdout


def test_emit_audit_block_creates_audit_md_with_header_if_missing(env_setup, run_id):
    _init(run_id)
    audit = env_setup / "aidlc-docs" / "audit.md"
    assert not audit.exists() or "audit" not in audit.read_text().lower()  # may not exist yet
    r = _emit_audit_block(
        run_id, "--evt", "orchestrator_note",
        "--phase", "INCEPTION", "--label", "Note",
        "--field", "summary=first",
        "--bullet", "first bullet",
    )
    assert r.returncode == 0
    text = audit.read_text()
    assert text.startswith("# Audit Log") or text.startswith("## ")  # header acceptable


# ---------------------------------------------------------------------------
# Dedupe guard
# ---------------------------------------------------------------------------


def test_emit_audit_block_dedupes_on_retry(env_setup, run_id, monkeypatch):
    _init(run_id)
    # First call lands the block.
    r1 = _emit_audit_block(
        run_id,
        "--evt", "user_answers_received",
        "--stage", "requirements-analyst",
        "--phase", "INCEPTION",
        "--label", "User Answers Received",
        "--bullet", "[User] Q1=A",
    )
    assert r1.returncode == 0

    # Second call with the SAME ts and label is treated as a retry → no-op.
    # We simulate "same ts" by freezing the clock to the ts emitted in r1.
    audit = env_setup / "aidlc-docs" / "audit.md"
    text_after_first = audit.read_text()
    h2_lines = [ln for ln in text_after_first.splitlines() if ln.startswith("## ")]
    assert len(h2_lines) == 1
    first_ts = h2_lines[0].split()[1]

    # Force a retry by replaying the same ts via the explicit --ts override.
    r2 = _emit_audit_block(
        run_id,
        "--evt", "user_answers_received",
        "--stage", "requirements-analyst",
        "--phase", "INCEPTION",
        "--label", "User Answers Received",
        "--bullet", "[User] Q1=A",
        "--ts", first_ts,
    )
    assert r2.returncode == 0, r2.stderr
    assert "dedupe" in r2.stdout.lower() or "skipped" in r2.stdout.lower()

    # audit.md still has only one section
    text_after_second = audit.read_text()
    h2_lines2 = [ln for ln in text_after_second.splitlines() if ln.startswith("## ")]
    assert len(h2_lines2) == 1


def test_emit_audit_block_appends_when_label_differs(env_setup, run_id):
    _init(run_id)
    r1 = _emit_audit_block(
        run_id, "--evt", "user_decision", "--stage", "workflow-planner",
        "--phase", "INCEPTION", "--label", "User Decision (workflow-planner)",
        "--field", "decision=approve", "--bullet", "[User] approved",
    )
    assert r1.returncode == 0
    r2 = _emit_audit_block(
        run_id, "--evt", "user_decision", "--stage", "code-generator",
        "--phase", "CONSTRUCTION", "--label", "User Decision (code-generator plan)",
        "--field", "decision=approve", "--bullet", "[User] approved plan",
    )
    assert r2.returncode == 0
    audit = (env_setup / "aidlc-docs" / "audit.md").read_text()
    h2_lines = [ln for ln in audit.splitlines() if ln.startswith("## ")]
    assert len(h2_lines) == 2


# ---------------------------------------------------------------------------
# Validation / error paths
# ---------------------------------------------------------------------------


def test_emit_audit_block_rejects_unknown_evt(env_setup, run_id):
    _init(run_id)
    r = _emit_audit_block(
        run_id, "--evt", "bogus_event_name",
        "--phase", "INCEPTION", "--label", "X",
        "--bullet", "y",
    )
    assert r.returncode != 0
    assert "evt" in r.stderr.lower() or "vocabulary" in r.stderr.lower() or "unknown" in r.stderr.lower()
    # Neither audit.md nor timeline should have a new entry
    timeline = env_setup / ".aidlc-orchestrator" / "runs" / run_id / "timeline.jsonl"
    events = [json.loads(line) for line in timeline.read_text().splitlines() if line.strip()]
    assert not any(e.get("evt") == "bogus_event_name" for e in events)


def test_emit_audit_block_rejects_missing_run(env_setup):
    r = _emit_audit_block(
        "no-such-run", "--evt", "orchestrator_note",
        "--phase", "INCEPTION", "--label", "X",
        "--field", "summary=foo", "--bullet", "y",
    )
    assert r.returncode != 0
    assert "not found" in r.stderr.lower() or "manifest" in r.stderr.lower()


def test_emit_audit_block_rejects_invalid_phase(env_setup, run_id):
    _init(run_id)
    r = _emit_audit_block(
        run_id, "--evt", "orchestrator_note",
        "--phase", "MIDDLEWARE", "--label", "X",
        "--field", "summary=foo", "--bullet", "y",
    )
    assert r.returncode != 0
    assert "phase" in r.stderr.lower()


def test_emit_audit_block_requires_at_least_one_bullet(env_setup, run_id):
    _init(run_id)
    r = _emit_audit_block(
        run_id, "--evt", "orchestrator_note",
        "--phase", "INCEPTION", "--label", "X",
        "--field", "summary=foo",
    )
    # Either errors out, OR appends an empty block — pick one. We require error.
    assert r.returncode != 0
    assert "bullet" in r.stderr.lower()


# ---------------------------------------------------------------------------
# Stage-skipped evt requires stage; user_decision requires decision field
# ---------------------------------------------------------------------------


def test_emit_audit_block_stage_skipped_requires_reason(env_setup, run_id):
    _init(run_id)
    r = _emit_audit_block(
        run_id, "--evt", "stage_skipped", "--stage", "story-writer",
        "--phase", "INCEPTION", "--label", "Story Writer SKIPPED",
        "--bullet", "[Orchestrator] non-critical stage failed",
        # no --field reason= → expect error
    )
    assert r.returncode != 0
    assert "reason" in r.stderr.lower()


def test_emit_audit_block_user_decision_requires_decision_field(env_setup, run_id):
    _init(run_id)
    r = _emit_audit_block(
        run_id, "--evt", "user_decision", "--stage", "workflow-planner",
        "--phase", "INCEPTION", "--label", "User Decision",
        "--bullet", "[User] x",
        # no --field decision= → expect error
    )
    assert r.returncode != 0
    assert "decision" in r.stderr.lower()


# ---------------------------------------------------------------------------
# Header chronology — ts must be ≥ all prior `## ` ts values
# ---------------------------------------------------------------------------


def test_emit_audit_block_header_ts_is_monotonic(env_setup, run_id):
    _init(run_id)
    r1 = _emit_audit_block(
        run_id, "--evt", "user_decision", "--stage", "workflow-planner",
        "--phase", "INCEPTION", "--label", "User Decision (workflow-planner)",
        "--field", "decision=approve", "--bullet", "[User] approved",
    )
    assert r1.returncode == 0
    time.sleep(1)  # ensure ts increments by at least 1 second
    r2 = _emit_audit_block(
        run_id, "--evt", "orchestrator_note",
        "--phase", "INCEPTION", "--label", "Note",
        "--field", "summary=continue", "--bullet", "[Orchestrator] proceeding",
    )
    assert r2.returncode == 0
    audit = (env_setup / "aidlc-docs" / "audit.md").read_text()
    ts_matches = re.findall(r"^## (\S+) ", audit, re.MULTILINE)
    assert len(ts_matches) >= 2
    # ts values must be monotonically non-decreasing
    from datetime import datetime
    parsed = [datetime.fromisoformat(t) for t in ts_matches]
    assert parsed == sorted(parsed)


# ---------------------------------------------------------------------------
# Concurrent writer safety (advisory flock on audit.md)
# ---------------------------------------------------------------------------


def _spawn_emit(run_id, label, aidlc_root):
    """Helper for the concurrent-writes test. Must be top-level for pickling."""
    env = dict(os.environ)
    env["AIDLC_ROOT"] = str(aidlc_root)
    return subprocess.run(
        [sys.executable, str(RUN_PY), "emit_audit_block",
         run_id, "--evt", "orchestrator_note",
         "--phase", "INCEPTION", "--label", label,
         "--field", "summary=parallel",
         "--bullet", f"[Test] {label}"],
        capture_output=True, text=True, env=env,
    ).returncode


def test_emit_audit_block_concurrent_writers_serialize(env_setup, run_id):
    _init(run_id)
    aidlc_root = env_setup
    labels = [f"Parallel-{i}" for i in range(8)]

    with multiprocessing.Pool(processes=8) as pool:
        rcs = pool.starmap(_spawn_emit, [(run_id, lbl, aidlc_root) for lbl in labels])

    assert all(rc == 0 for rc in rcs), f"some concurrent writers failed: {rcs}"

    audit = (env_setup / "aidlc-docs" / "audit.md").read_text()
    # Every label must be present exactly once. No interleaving / corruption.
    for lbl in labels:
        assert audit.count(f"INCEPTION - {lbl}") == 1, \
            f"label {lbl} appeared {audit.count(lbl)} times (expected 1)"
    # File parses as well-formed: every `## ` line has a ts after it
    for ln in audit.splitlines():
        if ln.startswith("## "):
            parts = ln.split()
            assert len(parts) >= 2, f"malformed header: {ln!r}"
            # ts must be parseable
            from datetime import datetime
            datetime.fromisoformat(parts[1])
