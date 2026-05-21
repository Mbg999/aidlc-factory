"""Tests for aidlc-scripts/factory_quality_report.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
QR_PY = SCRIPTS / "factory_quality_report.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(QR_PY), *args],
        capture_output=True, text=True,
    )


@pytest.fixture
def repo_with_runs(tmp_path: Path) -> Path:
    """Seed a repo with 3 completed runs of varied quality."""
    runs = tmp_path / ".aidlc-orchestrator" / "runs"
    runs.mkdir(parents=True)

    # Run 1 — clean
    r1 = runs / "r1" / "handoffs"
    r1.mkdir(parents=True)
    (r1 / "workspace-scout.output.yaml").write_text(yaml.safe_dump({
        "status": "complete",
        "cost": {"tokens_in": 10_000, "tokens_out": 5_000, "wall_clock_min": 2.0},
        "audit_entries": ["[WorkspaceScout] done"],
    }))
    (r1 / "requirements-analyst.output.yaml").write_text(yaml.safe_dump({
        "status": "complete",
        "cost": {"tokens_in": 100_000, "tokens_out": 50_000, "wall_clock_min": 10.0},
        "audit_entries": ["[ReqAnalyst] done"],
    }))

    # Run 2 — requirements-analyst hit needs_human
    r2 = runs / "r2" / "handoffs"
    r2.mkdir(parents=True)
    (r2 / "workspace-scout.output.yaml").write_text(yaml.safe_dump({
        "status": "complete",
        "cost": {"tokens_in": 12_000, "tokens_out": 6_000, "wall_clock_min": 2.5},
        "audit_entries": [],
    }))
    (r2 / "requirements-analyst.output.yaml").write_text(yaml.safe_dump({
        "status": "needs_human",
        "cost": {"tokens_in": 80_000, "tokens_out": 40_000, "wall_clock_min": 8.0},
        "audit_entries": ["[RedFlag] requirements-intelligence: 3 contradictions"],
    }))

    # Run 3 — content validator failed for requirements-analyst
    r3 = runs / "r3" / "handoffs"
    r3.mkdir(parents=True)
    (r3 / "requirements-analyst.output.yaml").write_text(yaml.safe_dump({
        "status": "blocked",
        "cost": {"tokens_in": 90_000, "tokens_out": 45_000, "wall_clock_min": 9.0, "retries_used": 1},
        "audit_entries": ["[ContentValidator] FAIL: 2 axes missing tags"],
    }))

    return tmp_path


def test_aggregates_across_runs(repo_with_runs):
    result = _run("--repo-root", str(repo_with_runs), "--json")
    assert result.returncode == 0
    agg = json.loads(result.stdout)
    assert agg["runs_count"] == 3
    assert "requirements-analyst" in agg["stages"]
    assert "workspace-scout" in agg["stages"]


def test_needs_human_rate_correct(repo_with_runs):
    result = _run("--repo-root", str(repo_with_runs), "--json")
    agg = json.loads(result.stdout)
    ra = agg["stages"]["requirements-analyst"]
    # 1 of 3 runs had needs_human
    assert ra["needs_human_rate"] == pytest.approx(1/3, abs=0.01)


def test_evidence_fail_rate_correct(repo_with_runs):
    result = _run("--repo-root", str(repo_with_runs), "--json")
    agg = json.loads(result.stdout)
    ra = agg["stages"]["requirements-analyst"]
    # 1 of 3 had [ContentValidator] FAIL
    assert ra["evidence_fail_rate"] == pytest.approx(1/3, abs=0.01)


def test_redflag_rate_detected(repo_with_runs):
    result = _run("--repo-root", str(repo_with_runs), "--json")
    agg = json.loads(result.stdout)
    ra = agg["stages"]["requirements-analyst"]
    assert ra["redflag_rate"] == pytest.approx(1/3, abs=0.01)


def test_token_percentiles(repo_with_runs):
    result = _run("--repo-root", str(repo_with_runs), "--json")
    agg = json.loads(result.stdout)
    ra = agg["stages"]["requirements-analyst"]
    # 3 samples: 150k, 120k, 135k → median around 135k
    assert 100_000 < ra["token_p50"] < 200_000
    assert ra["token_p95"] >= ra["token_p50"]


def test_markdown_contains_slo_breach_when_evidence_fails_high(repo_with_runs):
    """1 out of 3 evidence-fails is 33% — above the 5% SLO default."""
    result = _run("--repo-root", str(repo_with_runs))
    assert result.returncode == 0
    assert "SLO breach signals" in result.stdout
    assert "evidence_fail_rate" in result.stdout


def test_out_flag_writes_to_file(repo_with_runs, tmp_path: Path):
    out = tmp_path / "report.md"
    result = _run("--repo-root", str(repo_with_runs), "--out", str(out))
    assert result.returncode == 0
    assert "Quality Report" in out.read_text()


def test_no_runs_exits_1(tmp_path: Path):
    (tmp_path / ".aidlc-orchestrator").mkdir(parents=True)
    result = _run("--repo-root", str(tmp_path))
    assert result.returncode == 1


def test_real_repo_runs_and_produces_output():
    """Smoke test against the real repo (pruebaaidlcv2 may have runs to scan)."""
    repo = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, str(QR_PY), "--repo-root", str(repo), "--json"],
        capture_output=True, text=True,
    )
    # Real repo may or may not have runs — either exit 0 (runs found) or 1 (no runs).
    assert result.returncode in (0, 1)
