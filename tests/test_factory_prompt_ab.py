"""Tests for aidlc-scripts/factory_prompt_ab.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
AB_PY = SCRIPTS / "factory_prompt_ab.py"


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(AB_PY), "--repo-root", str(repo), *args],
        capture_output=True, text=True,
    )


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    stage_dir = tmp_path / ".claude" / "agents" / "stage"
    stage_dir.mkdir(parents=True)
    (stage_dir / "requirements-analyst.md").write_text("# baseline body\n")
    return tmp_path


def test_discover_no_experiments(fake_repo: Path):
    result = _run(fake_repo, "discover", "requirements-analyst")
    assert result.returncode == 0
    assert "No experiment dir" in result.stdout


def test_discover_lists_variants(fake_repo: Path):
    exp = fake_repo / ".claude/agents/stage/requirements-analyst.experiment"
    exp.mkdir()
    (exp / "v2-socratic-first.md").write_text("# variant A\n")
    (exp / "v3-shorter.md").write_text("# variant B\n")

    result = _run(fake_repo, "discover", "requirements-analyst")
    assert result.returncode == 0
    assert "v2-socratic-first" in result.stdout
    assert "v3-shorter" in result.stdout


def test_activate_swaps_and_preserves_baseline(fake_repo: Path):
    exp = fake_repo / ".claude/agents/stage/requirements-analyst.experiment"
    exp.mkdir()
    (exp / "v2.md").write_text("# variant v2 body\n")

    result = _run(fake_repo, "activate", "requirements-analyst", "v2")
    assert result.returncode == 0

    stage_path = fake_repo / ".claude/agents/stage/requirements-analyst.md"
    baseline_path = fake_repo / ".claude/agents/stage/requirements-analyst.baseline.md"
    assert stage_path.read_text() == "# variant v2 body\n"
    assert baseline_path.read_text() == "# baseline body\n"


def test_restore_brings_back_baseline(fake_repo: Path):
    exp = fake_repo / ".claude/agents/stage/requirements-analyst.experiment"
    exp.mkdir()
    (exp / "v2.md").write_text("# variant body\n")

    _run(fake_repo, "activate", "requirements-analyst", "v2")
    result = _run(fake_repo, "restore", "requirements-analyst")
    assert result.returncode == 0

    stage_path = fake_repo / ".claude/agents/stage/requirements-analyst.md"
    assert stage_path.read_text() == "# baseline body\n"
    assert not (fake_repo / ".claude/agents/stage/requirements-analyst.baseline.md").exists()


def test_activate_unknown_variant_exits_2(fake_repo: Path):
    result = _run(fake_repo, "activate", "requirements-analyst", "nonexistent")
    assert result.returncode == 2


def test_compare_two_runs(tmp_path: Path):
    """Build two fake runs and compare requirements-analyst metrics."""
    def _seed_run(run_dir: Path, tokens_in, tokens_out, wall):
        h = run_dir / "handoffs"
        h.mkdir(parents=True)
        (h / "requirements-analyst.output.yaml").write_text(yaml.safe_dump({
            "status": "complete",
            "cost": {"tokens_in": tokens_in, "tokens_out": tokens_out,
                     "wall_clock_min": wall},
            "audit_entries": ["[ReqAnalyst] done"],
        }))

    a = tmp_path / "run-a"
    b = tmp_path / "run-b"
    _seed_run(a, 100_000, 50_000, 8.0)
    _seed_run(b, 60_000, 30_000, 5.0)

    result = _run(tmp_path, "compare", "requirements-analyst", str(a), str(b))
    assert result.returncode == 0
    assert "tokens_total" in result.stdout
    assert "150000" in result.stdout or "150,000" in result.stdout or "150000" in result.stdout.replace(",", "")


def test_compare_warns_when_variant_burns_more_tokens(tmp_path: Path):
    a = tmp_path / "run-a"
    b = tmp_path / "run-b"
    for r, tk in [(a, 100_000), (b, 150_000)]:
        h = r / "handoffs"
        h.mkdir(parents=True)
        (h / "requirements-analyst.output.yaml").write_text(yaml.safe_dump({
            "status": "complete",
            "cost": {"tokens_in": tk, "tokens_out": tk // 2, "wall_clock_min": 5.0},
            "audit_entries": [],  # no rationalizations either side
        }))

    result = _run(tmp_path, "compare", "requirements-analyst", str(a), str(b))
    # B uses ~50% more tokens with no rigor gain → exit 1
    assert result.returncode == 1
    assert "more tokens" in result.stdout


def test_compare_json_output(tmp_path: Path):
    a = tmp_path / "run-a"
    b = tmp_path / "run-b"
    for r in (a, b):
        h = r / "handoffs"
        h.mkdir(parents=True)
        (h / "requirements-analyst.output.yaml").write_text(yaml.safe_dump({
            "status": "complete",
            "cost": {"tokens_in": 1000, "tokens_out": 500, "wall_clock_min": 1.0},
            "audit_entries": [],
        }))

    result = _run(tmp_path, "compare", "requirements-analyst", str(a), str(b), "--json")
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert "A" in data and "B" in data
    assert data["A"]["tokens_total"] == 1500
