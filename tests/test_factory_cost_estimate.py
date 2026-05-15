"""Tests for aidlc-scripts/factory_cost_estimate.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
COST_PY = SCRIPTS / "factory_cost_estimate.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(COST_PY), *args],
        capture_output=True, text=True,
    )


@pytest.fixture
def fake_repo_with_run(tmp_path: Path) -> tuple[Path, Path]:
    (tmp_path / ".aidlc-orchestrator" / "runs" / "r1" / "handoffs").mkdir(parents=True)
    repo, run_dir = tmp_path, tmp_path / ".aidlc-orchestrator/runs/r1"
    (run_dir / "manifest.yaml").write_text(yaml.safe_dump({
        "run_id": "r1",
        "current_stage": "workflow-planner",
        "project_profile": {"ui": True, "api": True, "has_legacy": False},
    }))
    (run_dir / "handoffs" / "workflow-planner.output.yaml").write_text(yaml.safe_dump({
        "status": "needs_human",
        "unit_count": 3,
        "task_count": 12,
    }))
    return (repo, run_dir)


def test_estimate_returns_markdown_with_total(fake_repo_with_run):
    repo, run_dir = fake_repo_with_run
    result = _run("--repo-root", str(repo), "--run-dir", str(run_dir))
    assert result.returncode == 0
    assert "Pre-flight cost estimate" in result.stdout
    assert "Total:" in result.stdout
    # Should show 3 units
    assert "Units: **3**" in result.stdout


def test_per_unit_stages_scale_with_unit_count(fake_repo_with_run):
    repo, run_dir = fake_repo_with_run
    result_1 = _run("--repo-root", str(repo), "--run-dir", str(run_dir),
                    "--unit-count", "1", "--json")
    result_5 = _run("--repo-root", str(repo), "--run-dir", str(run_dir),
                    "--unit-count", "5", "--json")
    p1 = json.loads(result_1.stdout)
    p5 = json.loads(result_5.stdout)
    # code-generator should scale 5x
    codegen_1 = next(r for r in p1["rows"] if r["stage"] == "code-generator")
    codegen_5 = next(r for r in p5["rows"] if r["stage"] == "code-generator")
    assert codegen_5["tokens"] == codegen_1["tokens"] * 5
    assert codegen_5["multiplier"] == 5


def test_reverse_engineer_skipped_when_no_legacy(fake_repo_with_run):
    repo, run_dir = fake_repo_with_run
    result = _run("--repo-root", str(repo), "--run-dir", str(run_dir), "--json")
    proj = json.loads(result.stdout)
    stages = {r["stage"] for r in proj["rows"]}
    assert "reverse-engineer" not in stages


def test_reverse_engineer_included_for_brownfield(tmp_path: Path):
    (tmp_path / ".aidlc-orchestrator" / "runs" / "r1" / "handoffs").mkdir(parents=True)
    run_dir = tmp_path / ".aidlc-orchestrator/runs/r1"
    (run_dir / "manifest.yaml").write_text(yaml.safe_dump({
        "run_id": "r1",
        "project_profile": {"ui": True, "api": True, "has_legacy": True},
    }))
    result = _run("--repo-root", str(tmp_path), "--run-dir", str(run_dir), "--json")
    proj = json.loads(result.stdout)
    stages = {r["stage"] for r in proj["rows"]}
    assert "reverse-engineer" in stages


def test_ceiling_blocks_overrun(fake_repo_with_run):
    repo, run_dir = fake_repo_with_run
    # Set ceiling far below realistic total
    result = _run("--repo-root", str(repo), "--run-dir", str(run_dir),
                  "--ceiling-tokens", "1000")
    assert result.returncode == 1


def test_historical_samples_used_when_available(tmp_path: Path):
    """If past runs have cost.tokens_in/out in handoffs, use them."""
    repo = tmp_path
    runs_root = repo / ".aidlc-orchestrator" / "runs"
    runs_root.mkdir(parents=True)

    # Seed 3 historical runs with workspace-scout cost data
    for i in range(3):
        rd = runs_root / f"hist-{i}"
        (rd / "handoffs").mkdir(parents=True)
        (rd / "handoffs" / "workspace-scout.output.yaml").write_text(yaml.safe_dump({
            "status": "complete",
            "cost": {"tokens_in": 10_000, "tokens_out": 5_000, "wall_clock_min": 2.0},
        }))
        (rd / "manifest.yaml").write_text(yaml.safe_dump({"run_id": f"hist-{i}"}))

    # New run
    new_run = runs_root / "new"
    (new_run / "handoffs").mkdir(parents=True)
    (new_run / "manifest.yaml").write_text(yaml.safe_dump({
        "run_id": "new", "project_profile": {"ui": True},
    }))

    result = _run("--repo-root", str(repo), "--run-dir", str(new_run), "--json")
    proj = json.loads(result.stdout)
    ws = next(r for r in proj["rows"] if r["stage"] == "workspace-scout")
    assert ws["tokens"] == 15_000  # tokens_in + tokens_out
    assert ws["confidence"] == "high"
    assert "3 historical samples" in ws["source"]


def test_out_flag_writes_to_file(fake_repo_with_run, tmp_path: Path):
    repo, run_dir = fake_repo_with_run
    out = tmp_path / "estimate.md"
    result = _run("--repo-root", str(repo), "--run-dir", str(run_dir),
                  "--out", str(out))
    assert result.returncode == 0
    assert "Total:" in out.read_text()


def test_no_args_works_with_defaults(tmp_path: Path):
    """Run without --run-dir or --manifest — uses defaults for everything."""
    (tmp_path / ".aidlc-orchestrator").mkdir(parents=True)
    result = _run("--repo-root", str(tmp_path), "--json", "--unit-count", "1")
    assert result.returncode == 0
    proj = json.loads(result.stdout)
    assert proj["unit_count"] == 1
    assert proj["total_tokens"] > 0
