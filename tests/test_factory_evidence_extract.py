"""Tests for aidlc-scripts/factory_evidence_extract.py."""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
EXTRACT_PY = SCRIPTS / "factory_evidence_extract.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(EXTRACT_PY), *args],
        capture_output=True,
        text=True,
    )


SAMPLE_AUDIT = textwrap.dedent("""\
    # Audit Log

    ## Summary
    - Current Phase: INCEPTION

    ## Entries

    ## 2026-05-13T09:54:02+00:00 INCEPTION - WORKSPACE SCOUT START
    - [Orchestrator] spawned with tokens_max=50000, wall_clock_max_min=10
    - [WorkspaceScout] User request: 'a pokedex web app'
    - [WorkspaceScout] [Depth] Determined 'standard' depth
    - [Skill] Executed: using-agent-skills — PASS

    ## 2026-05-13T09:55:31+00:00 INCEPTION - WORKSPACE SCOUT COMPLETE
    - [Orchestrator] tokens used: 60000, wall_min: 1.5
    - [CostGov] Estimated workspace-scout cost

    ## 2026-05-13T09:56:20+00:00 INCEPTION - REQUIREMENTS ANALYST START (PASS 1)
    - [SkillRead] requirements-analysis.md L1: "PRIORITY: P1"
    - [SignalScore] {clarity: Vague, risk: low}
    - [CoverageMap]
      | Axis | Required at | Question IDs | Status |
      | Purpose | all | Q1 | covered |
""")


@pytest.fixture
def sample_audit_file(tmp_path: Path) -> Path:
    """Write the sample audit.md to a temp file under aidlc-docs/."""
    docs = tmp_path / "aidlc-docs"
    docs.mkdir()
    p = docs / "audit.md"
    p.write_text(SAMPLE_AUDIT)
    return p


# -------------------- happy path --------------------


def test_extract_emits_jsonl_rows(sample_audit_file: Path):
    result = _run(str(sample_audit_file), "--run-id", "test-run")
    assert result.returncode == 0
    lines = [l for l in result.stdout.splitlines() if l.strip()]
    assert len(lines) >= 7  # 4 in section 1 + 2 in section 2 + 2 in section 3

    rows = [json.loads(l) for l in lines]
    # Check first row
    r0 = rows[0]
    assert r0["run_id"] == "test-run"
    assert r0["phase"] == "INCEPTION"
    assert r0["stage"] == "workspace-scout"
    assert r0["state"] == "START"
    assert r0["timestamp"] == "2026-05-13T09:54:02+00:00"
    assert r0["prefix"] == "Orchestrator"
    assert r0["payload"].startswith("spawned with")


def test_multi_bracket_line_emits_all_tags(sample_audit_file: Path):
    result = _run(str(sample_audit_file), "--run-id", "test-run")
    rows = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
    multi = [r for r in rows if r["payload"].startswith("Determined 'standard'")]
    assert len(multi) == 1
    assert multi[0]["tags"] == ["WorkspaceScout", "Depth"]
    assert multi[0]["prefix"] == "WorkspaceScout"


def test_pass1_state_parsed(sample_audit_file: Path):
    result = _run(str(sample_audit_file), "--run-id", "test-run")
    rows = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
    pass1 = [r for r in rows if r["stage"] == "requirements-analyst"]
    assert pass1, "no requirements-analyst rows found"
    # State could be "PASS 1" or "(PASS 1)" after normalisation
    states = {r["state"] for r in pass1}
    assert any("PASS 1" in s or "START" in s for s in states), states


def test_skill_read_row_extracted(sample_audit_file: Path):
    result = _run(str(sample_audit_file), "--run-id", "test-run")
    rows = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
    skillread = [r for r in rows if r["prefix"] == "SkillRead"]
    assert len(skillread) == 1
    assert "requirements-analysis.md" in skillread[0]["payload"]


def test_coverage_map_row_extracted(sample_audit_file: Path):
    result = _run(str(sample_audit_file), "--run-id", "test-run")
    rows = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
    cov = [r for r in rows if r["prefix"] == "CoverageMap"]
    assert len(cov) == 1


# -------------------- run-id inference --------------------


def test_run_id_auto_from_runs_directory(tmp_path: Path):
    """audit.md inside `.aidlc-orchestrator/runs/<run-id>/aidlc-docs/audit.md` → run-id from path."""
    target = tmp_path / ".aidlc-orchestrator" / "runs" / "2026-05-14-my-run" / "aidlc-docs"
    target.mkdir(parents=True)
    audit = target / "audit.md"
    audit.write_text(SAMPLE_AUDIT)

    result = _run(str(audit))
    rows = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
    assert rows[0]["run_id"] == "2026-05-14-my-run"


def test_run_dir_flag_works(tmp_path: Path):
    """--run-dir <dir> looks for <dir>/aidlc-docs/audit.md."""
    docs = tmp_path / "aidlc-docs"
    docs.mkdir()
    (docs / "audit.md").write_text(SAMPLE_AUDIT)

    result = _run("--run-dir", str(tmp_path), "--run-id", "manual")
    assert result.returncode == 0
    rows = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
    assert rows[0]["run_id"] == "manual"


# -------------------- error paths --------------------


def test_missing_file_exits_2():
    result = _run("/nonexistent/audit.md")
    assert result.returncode == 2


def test_audit_with_no_section_headers_exits_1(tmp_path: Path):
    audit = tmp_path / "audit.md"
    audit.write_text("# Audit Log\n\nNothing structured here.\n")
    result = _run(str(audit), "--run-id", "x")
    assert result.returncode == 1


def test_no_source_exits_2():
    result = _run()
    assert result.returncode == 2


# -------------------- output options --------------------


def test_out_flag_writes_to_file(sample_audit_file: Path, tmp_path: Path):
    out = tmp_path / "out.jsonl"
    result = _run(str(sample_audit_file), "--run-id", "r1", "--out", str(out))
    assert result.returncode == 0
    text = out.read_text()
    rows = [json.loads(l) for l in text.splitlines() if l.strip()]
    assert len(rows) >= 7


def test_pretty_flag_produces_valid_json_objects(sample_audit_file: Path):
    result = _run(str(sample_audit_file), "--run-id", "r1", "--pretty")
    assert result.returncode == 0
    # Output should contain `"run_id": "r1"` indented (pretty)
    assert "  \"run_id\": \"r1\"" in result.stdout


# -------------------- real-data smoke test --------------------


def test_real_pruebaaidlcv2_audit_if_present():
    """If pruebaaidlcv2/aidlc-docs/audit.md exists, parse it and confirm rows.

    This is a soft integration check — skipped if the target audit doesn't exist."""
    p = Path("/Users/miguel.belmonte/Desktop/pruebaaidlcv2/aidlc-docs/audit.md")
    if not p.exists():
        pytest.skip("pruebaaidlcv2 audit not present")

    result = _run(str(p))
    assert result.returncode == 0
    rows = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
    assert len(rows) >= 5
    # Should contain at least one WorkspaceScout row
    assert any(r["prefix"] == "WorkspaceScout" or r["stage"] == "workspace-scout"
               for r in rows)
