"""Tests for aidlc-scripts/factory_lint_rules.py."""

from __future__ import annotations

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
LINT_PY = SCRIPTS / "factory_lint_rules.py"


def _run(repo_root: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(LINT_PY), "--repo-root", str(repo_root), *extra],
        capture_output=True,
        text=True,
    )


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    """Minimal AIDLC repo skeleton for linter tests."""
    (tmp_path / ".aidlc-orchestrator" / "contracts").mkdir(parents=True)
    (tmp_path / ".claude" / "agents" / "stage").mkdir(parents=True)
    (tmp_path / "aidlc-rules" / "aws-aidlc-rule-details" / "inception").mkdir(parents=True)
    return tmp_path


def _write_stage(repo: Path, name: str, skills_block: str) -> None:
    (repo / ".claude/agents/stage" / f"{name}.md").write_text(
        f"---\nname: {name}\n---\n\n# {name}\n\n{skills_block}\n"
    )


def _write_contract(repo: Path, name: str, min_items: int, description: str = "") -> None:
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "$id": f"{name}.output.v1",
        "type": "object",
        "required": ["status", "skill_compliance"],
        "properties": {
            "status": {"type": "string"},
            "skill_compliance": {
                "type": "array",
                "minItems": min_items,
                "description": description,
                "items": {"type": "object"},
            },
        },
    }
    (repo / ".aidlc-orchestrator/contracts" / f"{name}.output.v1.json").write_text(
        json.dumps(schema, indent=2)
    )


def _write_rule_file(repo: Path, phase: str, fname: str, skills: list[str]) -> None:
    block = "## Agent Skills (MANDATORY)\n\n"
    for s in skills:
        block += f"- `{s}/SKILL.md` — description\n"
    (repo / "aidlc-rules/aws-aidlc-rule-details" / phase).mkdir(parents=True, exist_ok=True)
    (repo / "aidlc-rules/aws-aidlc-rule-details" / phase / fname).write_text(
        f"# {fname}\n\n{block}\n"
    )


# -------------------- happy path --------------------


def test_clean_repo_passes(fake_repo: Path):
    _write_stage(
        fake_repo, "workspace-scout",
        "**Skills:** `using-agent-skills`, `spec-driven-development`."
    )
    _write_contract(fake_repo, "workspace-scout", min_items=2,
                    description="using-agent-skills, spec-driven-development")
    _write_rule_file(fake_repo, "inception", "workspace-detection.md",
                     ["spec-driven-development"])

    result = _run(fake_repo)
    assert result.returncode == 0, result.stderr
    assert "clean" in result.stdout


def test_conditional_skill_does_not_count_toward_min_items(fake_repo: Path):
    """Conditional skills (marked *) should not be required by minItems."""
    _write_stage(
        fake_repo, "workspace-scout",
        "**Skills:** `using-agent-skills`, `spec-driven-development`, `optional-skill*`."
    )
    # minItems=2 because only 2 are unconditional
    _write_contract(fake_repo, "workspace-scout", min_items=2)
    _write_rule_file(fake_repo, "inception", "workspace-detection.md",
                     ["spec-driven-development"])

    result = _run(fake_repo)
    assert result.returncode == 0, result.stderr


# -------------------- drift detection --------------------


def test_min_items_too_low(fake_repo: Path):
    _write_stage(
        fake_repo, "workspace-scout",
        "**Skills:** `a`, `b`, `c`."
    )
    _write_contract(fake_repo, "workspace-scout", min_items=2)  # but 3 declared

    result = _run(fake_repo)
    assert result.returncode == 1
    assert "minItems=2" in result.stderr
    assert "3 unconditional skills" in result.stderr


def test_unconditional_skill_missing_from_rule_file(fake_repo: Path):
    _write_stage(
        fake_repo, "workspace-scout",
        "**Skills:** `using-agent-skills`, `idea-refine`, `new-skill`."
    )
    _write_contract(fake_repo, "workspace-scout", min_items=3)
    _write_rule_file(fake_repo, "inception", "workspace-detection.md",
                     ["idea-refine"])  # missing new-skill

    result = _run(fake_repo)
    assert result.returncode == 1
    assert "new-skill" in result.stderr
    assert "absent from rule file" in result.stderr


def test_conditional_skill_missing_from_rule_file_is_only_warning(fake_repo: Path):
    _write_stage(
        fake_repo, "workspace-scout",
        "**Skills:** `using-agent-skills`, `idea-refine`, `conditional-skill*`."
    )
    _write_contract(fake_repo, "workspace-scout", min_items=2)
    _write_rule_file(fake_repo, "inception", "workspace-detection.md",
                     ["idea-refine"])  # missing conditional-skill

    result = _run(fake_repo)
    assert result.returncode == 0  # warning, not error
    assert "conditional-skill" in result.stderr
    assert "OK for context-gated" in result.stderr


def test_using_agent_skills_excluded_from_rule_file_check(fake_repo: Path):
    """`using-agent-skills` is meta-protocol and may be omitted from rule files."""
    _write_stage(
        fake_repo, "workspace-scout",
        "**Skills:** `using-agent-skills`, `idea-refine`."
    )
    _write_contract(fake_repo, "workspace-scout", min_items=2)
    _write_rule_file(fake_repo, "inception", "workspace-detection.md",
                     ["idea-refine"])  # using-agent-skills omitted — should be fine

    result = _run(fake_repo)
    assert result.returncode == 0, result.stderr


# -------------------- edge cases --------------------


def test_repo_without_aidlc_orchestrator_dir_exits_2(tmp_path: Path):
    (tmp_path / "somefile").write_text("x")
    result = _run(tmp_path)
    assert result.returncode == 2


def test_repo_with_no_stage_agents_warns(fake_repo: Path):
    # No stage agents at all
    result = _run(fake_repo)
    # No stages → no errors, just an info note
    assert result.returncode == 1  # because empty list returns an error
    assert "no stage agents found" in result.stderr


def test_inline_and_bulleted_skill_styles_both_work(fake_repo: Path):
    """Inline `**Skills:**` and bulleted `**Skills required for this stage:**` both parse."""
    # Inline style
    _write_stage(
        fake_repo, "stage-a",
        "**Skills:** `using-agent-skills`, `s1`, `s2`."
    )
    _write_contract(fake_repo, "stage-a", min_items=3)

    # Bulleted style
    _write_stage(
        fake_repo, "stage-b",
        "**Skills required for this stage:**\n"
        "- `using-agent-skills` — meta-protocol\n"
        "- `s1` — first\n"
        "- `s2` — second\n"
    )
    _write_contract(fake_repo, "stage-b", min_items=3)

    result = _run(fake_repo)
    assert result.returncode == 0, result.stderr


def test_quiet_flag_suppresses_success_message(fake_repo: Path):
    _write_stage(fake_repo, "stage-a", "**Skills:** `s1`.")
    _write_contract(fake_repo, "stage-a", min_items=1)

    result = _run(fake_repo, "--quiet")
    assert result.returncode == 0
    assert "clean" not in result.stdout


# -------------------- self-test: lint the real repo --------------------


def test_real_repo_is_clean():
    """The actual aidlc-workflows repo (this repo) must lint clean.

    This is the dogfooding check — any future drift in the real repo
    fails this test.
    """
    repo_root = Path(__file__).resolve().parent.parent
    result = subprocess.run(
        [sys.executable, str(LINT_PY), "--repo-root", str(repo_root), "--quiet"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        pytest.fail(f"real repo has drift:\n{result.stderr}")
