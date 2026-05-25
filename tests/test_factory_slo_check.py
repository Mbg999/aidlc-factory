"""Tests for aidlc-scripts/factory_slo_check.py."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
SLO_PY = SCRIPTS / "factory_slo_check.py"


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SLO_PY), "--repo-root", str(repo), *args],
        capture_output=True, text=True,
    )


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    (tmp_path / "aidlc-docs" / "quality").mkdir(parents=True)
    (tmp_path / "aidlc-scripts").mkdir(parents=True)
    return tmp_path


def _write_slos(repo: Path, slos: list[dict]) -> None:
    import yaml
    yaml_block = "```yaml\n" + yaml.safe_dump({"slos": slos}) + "```\n"
    (repo / "aidlc-docs/quality/slos.md").write_text(f"# SLOs\n\n{yaml_block}")


def _write_report(repo: Path, stages: dict, runs_count: int = 5) -> Path:
    p = repo / "report.json"
    p.write_text(json.dumps({"runs_count": runs_count, "stages": stages}))
    return p


def test_all_slos_met_exit_0(fake_repo: Path):
    _write_slos(fake_repo, [
        {"stage": "requirements-analyst", "metric": "evidence_fail_rate",
         "comparator": "<", "threshold": 0.05, "severity": "block"},
    ])
    report = _write_report(fake_repo, {
        "requirements-analyst": {"evidence_fail_rate": 0.02},
    })
    result = _run(fake_repo, "--quality-report", str(report))
    assert result.returncode == 0
    assert "within bounds" in result.stdout


def test_block_breach_exits_2(fake_repo: Path):
    _write_slos(fake_repo, [
        {"stage": "requirements-analyst", "metric": "evidence_fail_rate",
         "comparator": "<", "threshold": 0.05, "severity": "block"},
    ])
    report = _write_report(fake_repo, {
        "requirements-analyst": {"evidence_fail_rate": 0.10},
    })
    result = _run(fake_repo, "--quality-report", str(report))
    assert result.returncode == 2
    assert "BLOCK" in result.stdout
    assert "unacknowledged" in result.stdout.lower()


def test_warn_breach_exits_1(fake_repo: Path):
    _write_slos(fake_repo, [
        {"stage": "requirements-analyst", "metric": "redflag_rate",
         "comparator": "<", "threshold": 0.20, "severity": "warn"},
    ])
    report = _write_report(fake_repo, {
        "requirements-analyst": {"redflag_rate": 0.30},
    })
    result = _run(fake_repo, "--quality-report", str(report))
    assert result.returncode == 1


def test_acknowledged_breach_clears_block(fake_repo: Path):
    import yaml
    _write_slos(fake_repo, [
        {"stage": "requirements-analyst", "metric": "evidence_fail_rate",
         "comparator": "<", "threshold": 0.05, "severity": "block"},
    ])
    # Write the ack
    acks_yaml = "```yaml\n" + yaml.safe_dump({"acks": [{
        "stage": "requirements-analyst",
        "metric": "evidence_fail_rate",
        "observed": 0.10,
        "threshold": 0.05,
        "acknowledged_at": "2026-05-15",
        "acknowledged_by": "test",
        "rationale": "known issue, fix landing soon",
    }]}) + "```\n"
    (fake_repo / "aidlc-docs/quality/slo-acks.md").write_text(f"# acks\n\n{acks_yaml}")

    report = _write_report(fake_repo, {
        "requirements-analyst": {"evidence_fail_rate": 0.10},
    })
    result = _run(fake_repo, "--quality-report", str(report))
    assert result.returncode == 0
    assert "Acknowledged" in result.stdout


def test_wildcard_stage_applies_to_all(fake_repo: Path):
    _write_slos(fake_repo, [
        {"stage": "*", "metric": "redflag_rate",
         "comparator": "<", "threshold": 0.30, "severity": "warn"},
    ])
    report = _write_report(fake_repo, {
        "requirements-analyst": {"redflag_rate": 0.40},
        "workflow-planner": {"redflag_rate": 0.05},
    })
    result = _run(fake_repo, "--quality-report", str(report))
    assert result.returncode == 1  # warn
    assert "requirements-analyst" in result.stdout


def test_expired_ack_no_longer_clears_breach(fake_repo: Path):
    import yaml
    _write_slos(fake_repo, [
        {"stage": "ship-agent", "metric": "failed_rate",
         "comparator": "<", "threshold": 0.05, "severity": "block"},
    ])
    acks_yaml = "```yaml\n" + yaml.safe_dump({"acks": [{
        "stage": "ship-agent", "metric": "failed_rate",
        "observed": 0.10, "threshold": 0.05,
        "acknowledged_at": "2020-01-01",
        "expires_at": "2020-12-31",  # long expired
    }]}) + "```\n"
    (fake_repo / "aidlc-docs/quality/slo-acks.md").write_text(acks_yaml)

    report = _write_report(fake_repo, {"ship-agent": {"failed_rate": 0.10}})
    result = _run(fake_repo, "--quality-report", str(report))
    assert result.returncode == 2


def test_missing_slos_file_exits_3(tmp_path: Path):
    result = _run(tmp_path, "--quality-report", os.devnull)
    assert result.returncode == 3


def test_json_output_includes_breaches(fake_repo: Path):
    _write_slos(fake_repo, [
        {"stage": "requirements-analyst", "metric": "evidence_fail_rate",
         "comparator": "<", "threshold": 0.05, "severity": "block"},
    ])
    report = _write_report(fake_repo, {
        "requirements-analyst": {"evidence_fail_rate": 0.10},
    })
    result = _run(fake_repo, "--quality-report", str(report), "--json")
    assert result.returncode == 2
    data = json.loads(result.stdout)
    assert len(data["breaches"]) == 1
    assert data["breaches"][0]["severity"] == "block"


def test_real_repo_slos_parse():
    """The shipped slos.md must be parseable."""
    repo = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, str(SLO_PY), "--repo-root", str(repo), "--auto", "--json"],
        capture_output=True, text=True,
    )
    # Empty runs are OK (no breaches), as is "no breaches"
    assert result.returncode in (0, 1, 2), result.stderr
    if result.returncode != 3:
        data = json.loads(result.stdout)
        assert data["slos_evaluated"] >= 5
