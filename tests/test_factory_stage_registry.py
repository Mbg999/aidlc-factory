"""Tests for aidlc-scripts/factory_stage_registry.py."""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
REGISTRY_PY = SCRIPTS / "factory_stage_registry.py"


def _run(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(REGISTRY_PY), "--repo-root", str(repo), *args],
        capture_output=True, text=True,
    )


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    (tmp_path / ".aidlc-orchestrator" / "contracts").mkdir(parents=True)
    (tmp_path / ".claude" / "agents" / "stage").mkdir(parents=True)
    return tmp_path


def _write_stage(repo: Path, name: str, frontmatter: str = "", body: str = "Hi") -> None:
    fm = f"---\nname: {name}\n{frontmatter}---\n"
    (repo / ".claude/agents/stage" / f"{name}.md").write_text(fm + body)


def _write_contract(repo: Path, name: str) -> None:
    (repo / ".aidlc-orchestrator/contracts" / f"{name}.json").write_text(
        '{"$id": "x"}'
    )


def test_list_shows_inferred_defaults(fake_repo: Path):
    _write_stage(fake_repo, "workspace-scout")
    _write_contract(fake_repo, "workspace-scout.input.v1")
    _write_contract(fake_repo, "workspace-scout.output.v1")

    result = _run(fake_repo, "list")
    assert result.returncode == 0
    assert "workspace-scout" in result.stdout
    assert "P0" in result.stdout  # default phase
    assert "factory-spec" in result.stdout  # default command


def test_explicit_aidlc_stage_block_overrides_defaults(fake_repo: Path):
    fm = textwrap.dedent("""\
        description: a stage
        aidlc_stage:
          phase: 1
          commands: [custom-cmd]
          execution_mode: full-spawn
          requires_skills:
            - skill-a
            - skill-b
    """)
    _write_stage(fake_repo, "my-stage", frontmatter=fm)

    result = _run(fake_repo, "show", "my-stage")
    assert result.returncode == 0
    rec = json.loads(result.stdout)
    assert rec["phase"] == 1
    assert rec["commands"] == ["custom-cmd"]
    assert rec["execution_mode"] == "full-spawn"
    assert rec["requires_skills"] == ["skill-a", "skill-b"]
    assert rec["has_explicit_aidlc_stage_block"] is True


def test_show_unknown_stage_exits_2(fake_repo: Path):
    _write_stage(fake_repo, "workspace-scout")
    result = _run(fake_repo, "show", "nonexistent")
    assert result.returncode == 2


def test_json_emits_array(fake_repo: Path):
    _write_stage(fake_repo, "workspace-scout")
    _write_stage(fake_repo, "requirements-analyst")

    result = _run(fake_repo, "json")
    assert result.returncode == 0
    rec = json.loads(result.stdout)
    assert isinstance(rec, list)
    names = {r["name"] for r in rec}
    assert {"workspace-scout", "requirements-analyst"} <= names


def test_reviewer_uses_shared_contract(fake_repo: Path):
    _write_stage(fake_repo, "reviewer-code")
    _write_contract(fake_repo, "reviewer.input.v1")
    _write_contract(fake_repo, "reviewer.output.v1")

    result = _run(fake_repo, "show", "reviewer-code")
    rec = json.loads(result.stdout)
    assert rec["input_contract"] == "reviewer.input.v1.json"
    assert rec["output_contract"] == "reviewer.output.v1.json"
    assert rec["input_contract_present"] is True
    assert rec["output_contract_present"] is True
    assert rec["execution_mode"] == "full-spawn"


def test_no_stages_exits_2(fake_repo: Path):
    result = _run(fake_repo, "list")
    assert result.returncode == 2


def test_real_repo_lists_all_stages():
    repo = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, str(REGISTRY_PY), "--repo-root", str(repo), "list"],
        capture_output=True, text=True,
    )
    assert result.returncode == 0
    # Sanity: every known stage agent should appear in the output
    for name in ("workspace-scout", "requirements-analyst", "workflow-planner",
                 "code-generator", "build-test-agent", "ship-agent",
                 "reviewer-code", "reviewer-security"):
        assert name in result.stdout, f"{name} missing from registry"
