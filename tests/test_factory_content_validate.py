"""Tests for aidlc-scripts/factory_content_validate.py."""

from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
VALIDATE_PY = SCRIPTS / "factory_content_validate.py"


def _run(args: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATE_PY), *args],
        capture_output=True,
        text=True,
    )


@pytest.fixture
def fake_run(tmp_path: Path) -> Path:
    """A minimal fake run directory with .aidlc-orchestrator anchor."""
    (tmp_path / ".aidlc-orchestrator" / "runs" / "r1" / "handoffs").mkdir(parents=True)
    (tmp_path / "aidlc-docs" / "inception" / "requirements").mkdir(parents=True)
    return tmp_path


_COVERAGE_BY_DEPTH = {
    "minimal": "[CoverageMap]\n| Axis | Required at | Question IDs | Status |\n|---|---|---|---|\n| Purpose | all | Q1 | covered |\n| Needs | all | Q2 | covered |\n| Expectations | all | Q3 | covered |\n| Acceptance | all | Q4 | covered |",
    "standard": "[CoverageMap]\n| Axis | Required at | Question IDs | Status |\n|---|---|---|---|\n| Purpose | all | Q1 | covered |\n| Needs | all | Q2 | covered |\n| Limits | standard+ | Q3 | covered |\n| Expectations | all | Q4 | covered |\n| Context | standard+ | Q5 | covered |\n| Acceptance | all | Q6 | covered |",
    "comprehensive": "[CoverageMap]\n| Axis | Required at | Question IDs | Status |\n|---|---|---|---|\n| Purpose | all | Q1 | covered |\n| Needs | all | Q2 | covered |\n| Limits | standard+ | Q3 | covered |\n| Expectations | all | Q4 | covered |\n| Context | standard+ | Q5 | covered |\n| Risks | comprehensive | Q6 | covered |\n| Acceptance | all | Q7 | covered |\n| Unknowns | comprehensive | Q8 | covered |",
}


def _write_pass1_handoff(
    repo: Path,
    *,
    depth: str = "standard",
    questions_path: str = "aidlc-docs/inception/requirements/r1-requirement-verification-questions.md",
    audit_entries: list[str] | None = None,
) -> Path:
    p = repo / ".aidlc-orchestrator/runs/r1/handoffs/requirements-analyst.output.yaml"
    p.write_text(yaml.safe_dump({
        "status": "needs_human",
        "needs_user_input": True,
        "depth": depth,
        "questions_artifact_path": questions_path,
        "artifacts": [
            {"path": questions_path, "kind": "questions"},
        ],
        "audit_entries": audit_entries if audit_entries is not None else [
            "[SkillRead] requirements-analysis.md L1: \"PRIORITY: P1\"",
            "[SignalScore] {clarity: Vague, risk: low}",
            _COVERAGE_BY_DEPTH[depth],
        ],
        "skill_compliance": [
            {"skill": "using-agent-skills", "status": "PASS", "evidence": "ok"},
            {"skill": "idea-refine", "status": "PASS", "evidence": "ok"},
            {"skill": "spec-driven-development", "status": "PASS", "evidence": "ok"},
            {"skill": "requirements-intelligence", "status": "PASS", "evidence": "ok"},
        ],
    }))
    return p


def _good_standard_questions() -> str:
    """A correctly-tagged questions file covering the standard-depth axes."""
    return textwrap.dedent("""
        # Requirements Verification Questions

        <!-- axis: Purpose -->
        ## Question 1
        Why this?

        A) Reason A
        B) Reason B
        X) Other (please describe after [Answer]: tag below)

        [Answer]:

        <!-- axis: Needs -->
        ## Question 2
        What does it do?

        A) Thing 1
        B) Thing 2
        X) Other (please describe after [Answer]: tag below)

        [Answer]:

        <!-- axis: Limits -->
        ## Question 3
        Out of scope?

        A) X is out
        B) Y is out
        X) Other (please describe after [Answer]: tag below)

        [Answer]:

        <!-- axis: Expectations -->
        ## Question 4
        How fast?

        A) <100ms
        B) <1s
        X) Other (please describe after [Answer]: tag below)

        [Answer]:

        <!-- axis: Context -->
        ## Question 5
        Stack constraint?

        A) Node
        B) Python
        X) Other (please describe after [Answer]: tag below)

        [Answer]:

        <!-- axis: Acceptance -->
        ## Question 6
        Demo?

        A) Two tabs send/receive
        B) Reload preserves history
        X) Other (please describe after [Answer]: tag below)

        [Answer]:
    """).strip()


# -------------------- happy path --------------------


def test_happy_path_standard_depth(fake_run):
    handoff = _write_pass1_handoff(fake_run)
    qpath = fake_run / "aidlc-docs/inception/requirements/r1-requirement-verification-questions.md"
    qpath.write_text(_good_standard_questions())

    result = _run(["--mode", "strict", "requirements", str(handoff)])
    assert result.returncode == 0, result.stderr
    assert "PASS" in result.stdout


def test_happy_path_coverage_map_claims_match(fake_run):
    audit = [
        "[CoverageMap]",
        "| Axis | Required at | Question IDs | Status |",
        "|---|---|---|---|",
        "| Purpose | all | Q1 | covered |",
        "| Needs | all | Q2 | covered |",
        "| Limits | standard+ | Q3 | covered |",
        "| Expectations | all | Q4 | covered |",
        "| Context | standard+ | Q5 | covered |",
        "| Acceptance | all | Q6 | covered |",
    ]
    handoff = _write_pass1_handoff(fake_run, audit_entries=audit)
    qpath = fake_run / "aidlc-docs/inception/requirements/r1-requirement-verification-questions.md"
    qpath.write_text(_good_standard_questions())

    result = _run(["--mode", "strict", "requirements", str(handoff)])
    assert result.returncode == 0, result.stderr


# -------------------- failure modes --------------------


def test_missing_axis_tag_fails_strict(fake_run):
    handoff = _write_pass1_handoff(fake_run)
    qpath = fake_run / "aidlc-docs/inception/requirements/r1-requirement-verification-questions.md"
    # Strip ALL axis tags
    bad = _good_standard_questions().replace("<!-- axis:", "<!-- removed:")
    qpath.write_text(bad)

    result = _run(["--mode", "strict", "requirements", str(handoff)])
    assert result.returncode == 1
    assert "no `<!-- axis:" in result.stderr or "have no" in result.stderr


def test_missing_axis_tag_warns_in_warn_mode(fake_run):
    handoff = _write_pass1_handoff(fake_run)
    qpath = fake_run / "aidlc-docs/inception/requirements/r1-requirement-verification-questions.md"
    bad = _good_standard_questions().replace("<!-- axis:", "<!-- removed:")
    qpath.write_text(bad)

    result = _run(["--mode", "warn", "requirements", str(handoff)])
    assert result.returncode == 0  # warn does not exit non-zero
    assert "WARN" in result.stdout


def test_missing_answer_tag(fake_run):
    handoff = _write_pass1_handoff(fake_run)
    qpath = fake_run / "aidlc-docs/inception/requirements/r1-requirement-verification-questions.md"
    bad = _good_standard_questions().replace("[Answer]:", "[Removed]:")
    qpath.write_text(bad)

    result = _run(["--mode", "strict", "requirements", str(handoff)])
    assert result.returncode == 1
    assert "missing [Answer]: tag" in result.stderr


def test_missing_other_option(fake_run):
    handoff = _write_pass1_handoff(fake_run)
    qpath = fake_run / "aidlc-docs/inception/requirements/r1-requirement-verification-questions.md"
    bad = _good_standard_questions().replace("X) Other", "X) Banana")
    qpath.write_text(bad)

    result = _run(["--mode", "strict", "requirements", str(handoff)])
    assert result.returncode == 1
    assert "missing 'X) Other' option" in result.stderr


def test_coverage_map_claim_without_matching_tag(fake_run):
    audit = [
        "[CoverageMap]",
        "| Axis | Required at | Question IDs | Status |",
        "|---|---|---|---|",
        "| Risks | comprehensive | Q9 | covered |",  # claim Risks but no Risks question
    ]
    handoff = _write_pass1_handoff(fake_run, audit_entries=audit)
    qpath = fake_run / "aidlc-docs/inception/requirements/r1-requirement-verification-questions.md"
    qpath.write_text(_good_standard_questions())

    result = _run(["--mode", "strict", "requirements", str(handoff)])
    assert result.returncode == 1
    assert "Risks" in result.stderr
    assert "no questions are tagged" in result.stderr


def test_minimal_depth_doesnt_require_limits(fake_run):
    """At minimal depth, Limits axis is NOT required — questions file without it should pass."""
    handoff = _write_pass1_handoff(fake_run, depth="minimal")
    qpath = fake_run / "aidlc-docs/inception/requirements/r1-requirement-verification-questions.md"
    # minimal-friendly: Purpose, Needs, Expectations, Acceptance only
    minimal_questions = textwrap.dedent("""
        # Q

        <!-- axis: Purpose -->
        ## Question 1
        Why?
        A) A
        B) B
        X) Other (please describe after [Answer]: tag below)
        [Answer]:

        <!-- axis: Needs -->
        ## Question 2
        What?
        A) A
        B) B
        X) Other (please describe after [Answer]: tag below)
        [Answer]:

        <!-- axis: Expectations -->
        ## Question 3
        How fast?
        A) Fast
        B) Slow
        X) Other (please describe after [Answer]: tag below)
        [Answer]:

        <!-- axis: Acceptance -->
        ## Question 4
        Done when?
        A) X
        B) Y
        X) Other (please describe after [Answer]: tag below)
        [Answer]:
    """).strip()
    qpath.write_text(minimal_questions)

    result = _run(["--mode", "strict", "requirements", str(handoff)])
    assert result.returncode == 0, result.stderr


def test_multi_axis_tag_counts_for_all(fake_run):
    """An assumption-mining question tagged for multiple axes covers all of them."""
    handoff = _write_pass1_handoff(fake_run, depth="standard")
    qpath = fake_run / "aidlc-docs/inception/requirements/r1-requirement-verification-questions.md"
    multi_tag = textwrap.dedent("""
        # Q

        <!-- axis: Purpose -->
        ## Question 1
        Why?
        A) A
        B) B
        X) Other (please describe after [Answer]: tag below)
        [Answer]:

        <!-- axis: Needs, Limits, Context, Expectations -->
        ## Question 2
        Assumption-mining covers many axes.
        A) Correct
        B) Some wrong
        X) Other (please describe after [Answer]: tag below)
        [Answer]:

        <!-- axis: Acceptance -->
        ## Question 3
        Demo?
        A) A
        B) B
        X) Other (please describe after [Answer]: tag below)
        [Answer]:
    """).strip()
    qpath.write_text(multi_tag)

    result = _run(["--mode", "strict", "requirements", str(handoff)])
    assert result.returncode == 0, result.stderr


def test_trivial_skip_path(fake_run):
    """Trivial + Clear + Single File: questions file can be omitted entirely."""
    p = fake_run / ".aidlc-orchestrator/runs/r1/handoffs/requirements-analyst.output.yaml"
    p.write_text(yaml.safe_dump({
        "status": "complete",
        "depth": "minimal",
        "request_classification": {
            "clarity": "Clear",
            "complexity": "Trivial",
            "scope": "Single File",
            "type": "Bug Fix",
        },
        "artifacts": [
            {"path": "aidlc-docs/inception/requirements/r1-requirements.md", "kind": "spec"},
        ],
        "audit_entries": ["[Skip] Trivial+Clear+SingleFile per requirements-analyst rule"],
        "skill_compliance": [
            {"skill": "using-agent-skills", "status": "PASS", "evidence": "ok"},
            {"skill": "idea-refine", "status": "PASS", "evidence": "ok"},
            {"skill": "spec-driven-development", "status": "PASS", "evidence": "ok"},
            {"skill": "requirements-intelligence", "status": "N/A",
             "evidence": "Trivial+Clear+SingleFile skip path per questioning-policy.md"},
        ],
    }))
    # Write a minimal valid requirements.md so the spec check passes
    req = fake_run / "aidlc-docs/inception/requirements/r1-requirements.md"
    req.write_text("# Requirements\n\n" + "Intent: fix a typo in the readme.\n" * 50)

    result = _run(["--mode", "strict", "requirements", str(p)])
    assert result.returncode == 0, result.stderr


def test_pass2_blank_requirements_fails(fake_run):
    p = fake_run / ".aidlc-orchestrator/runs/r1/handoffs/requirements-analyst.output.pass2.yaml"
    p.write_text(yaml.safe_dump({
        "status": "complete",
        "depth": "standard",
        "artifacts": [
            {"path": "aidlc-docs/inception/requirements/r1-requirements.md", "kind": "spec"},
        ],
        "audit_entries": ["[whatever]"],
        "skill_compliance": [
            {"skill": "x", "status": "PASS", "evidence": "y"},
        ],
    }))
    req = fake_run / "aidlc-docs/inception/requirements/r1-requirements.md"
    req.write_text("# Requirements\n")  # essentially empty

    result = _run(["--mode", "strict", "requirements", str(p)])
    assert result.returncode == 1
    assert "suspiciously short" in result.stderr


# -------------------- usage errors --------------------


def test_missing_handoff_file_exits_2():
    result = _run(["--mode", "strict", "requirements", "/nonexistent/path/handoff.yaml"])
    assert result.returncode == 2


def test_no_subcommand_exits_2():
    result = _run([])
    assert result.returncode == 2


# ============================================================================
# Phase 1 expansion: plan / code / tests / ship validators
# ============================================================================


def _write_plan_handoff(repo: Path, plan_path: str, units: list[dict] | None = None,
                       mermaid_validated: bool = True) -> Path:
    p = repo / ".aidlc-orchestrator/runs/r1/handoffs/workflow-planner.output.yaml"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump({
        "status": "needs_human",
        "artifacts": [{"path": plan_path, "kind": "plan"}],
        "audit_entries": ["[planner] done"],
        "skill_compliance": [
            {"skill": "using-agent-skills", "status": "PASS", "evidence": "ok"},
            {"skill": "planning-and-task-breakdown", "status": "PASS", "evidence": "ok"},
            {"skill": "requirements-intelligence", "status": "N/A", "evidence": "trivial"},
        ],
        "units": units if units is not None else [{"name": "auth", "description": "x"}],
        "task_count": 5,
        "unit_count": 1,
        "mermaid_validated": mermaid_validated,
    }))
    return p


def _good_plan_md(unit_name: str = "auth") -> str:
    return textwrap.dedent(f"""
        # Execution Plan

        ## Overview
        We plan to build the {unit_name} unit.

        ## Mermaid

        ```mermaid
        graph TD
          A[Start] --> B[Build]
          B --> C[Test]
        ```

        ## Tasks ({unit_name})

        - [ ] T1: implement {unit_name} foo
          Acceptance: foo() returns 42
        - [ ] T2: implement {unit_name} bar
          Acceptance: bar() handles errors
        - [ ] T3: write tests
          Acceptance: 90% coverage

        ## Acceptance criteria table

        | Task | AC |
        |---|---|
        | T1 | foo returns 42 |
    """).strip()


def test_plan_happy_path(fake_run: Path):
    plan_path = "aidlc-docs/inception/plans/r1-execution-plan.md"
    handoff = _write_plan_handoff(fake_run, plan_path)
    (fake_run / "aidlc-docs/inception/plans").mkdir(parents=True, exist_ok=True)
    (fake_run / plan_path).write_text(_good_plan_md())

    result = _run(["--mode", "strict", "plan", str(handoff)])
    assert result.returncode == 0, result.stderr


def test_plan_missing_mermaid_fails_strict(fake_run: Path):
    plan_path = "aidlc-docs/inception/plans/r1-execution-plan.md"
    handoff = _write_plan_handoff(fake_run, plan_path)
    (fake_run / "aidlc-docs/inception/plans").mkdir(parents=True, exist_ok=True)
    no_mermaid = _good_plan_md().replace("```mermaid", "```text")
    (fake_run / plan_path).write_text(no_mermaid)

    result = _run(["--mode", "strict", "plan", str(handoff)])
    assert result.returncode == 1
    assert "Mermaid" in result.stderr or "mermaid" in result.stderr


def test_plan_units_not_referenced(fake_run: Path):
    """Unit declared in handoff but absent from plan text → fail."""
    plan_path = "aidlc-docs/inception/plans/r1-execution-plan.md"
    handoff = _write_plan_handoff(
        fake_run, plan_path,
        units=[{"name": "ghost-unit", "description": "x"}],
    )
    (fake_run / "aidlc-docs/inception/plans").mkdir(parents=True, exist_ok=True)
    # _good_plan_md() uses 'auth', not 'ghost-unit' → mismatch
    (fake_run / plan_path).write_text(_good_plan_md(unit_name="auth"))

    result = _run(["--mode", "strict", "plan", str(handoff)])
    assert result.returncode == 1
    assert "ghost-unit" in result.stderr


def test_plan_no_tasks_fails(fake_run: Path):
    plan_path = "aidlc-docs/inception/plans/r1-execution-plan.md"
    handoff = _write_plan_handoff(fake_run, plan_path)
    (fake_run / "aidlc-docs/inception/plans").mkdir(parents=True, exist_ok=True)
    no_tasks = "# Plan\n```mermaid\ngraph A --> B\n```\nNo tasks here.\n"
    (fake_run / plan_path).write_text(no_tasks)

    result = _run(["--mode", "strict", "plan", str(handoff)])
    assert result.returncode == 1
    assert "task checkboxes" in result.stderr


def test_code_happy_path(fake_run: Path):
    src = fake_run / "src/auth/login.py"
    src.parent.mkdir(parents=True)
    src.write_text("def login(): return True\n")
    test = fake_run / "tests/test_login.py"
    test.parent.mkdir(parents=True, exist_ok=True)
    test.write_text("def test_login(): pass\n")

    p = fake_run / ".aidlc-orchestrator/runs/r1/handoffs/code-generator.output.yaml"
    p.write_text(yaml.safe_dump({
        "status": "complete",
        "artifacts": [
            {"path": "src/auth/login.py", "kind": "source"},
            {"path": "tests/test_login.py", "kind": "test"},
        ],
        "audit_entries": ["[Codegen] done"],
        "skill_compliance": [{"skill": "x", "status": "PASS", "evidence": "ok"}],
        "locks_to_release": ["src/auth/**"],
    }))

    result = _run(["--mode", "strict", "code", str(p)])
    assert result.returncode == 0, result.stderr


def test_code_missing_tests_fails(fake_run: Path):
    src = fake_run / "src/auth/login.py"
    src.parent.mkdir(parents=True)
    src.write_text("def login(): return True\n")

    p = fake_run / ".aidlc-orchestrator/runs/r1/handoffs/code-generator.output.yaml"
    p.write_text(yaml.safe_dump({
        "status": "complete",
        "artifacts": [
            {"path": "src/auth/login.py", "kind": "source"},
        ],
        "audit_entries": ["[Codegen] no tests"],
        "skill_compliance": [{"skill": "x", "status": "PASS", "evidence": "ok"}],
        "locks_to_release": ["src/auth/**"],
    }))

    result = _run(["--mode", "strict", "code", str(p)])
    assert result.returncode == 1
    assert "no test artifacts" in result.stderr


def test_code_missing_source_file_fails(fake_run: Path):
    """Handoff declares a source file that doesn't exist on disk → fail."""
    p = fake_run / ".aidlc-orchestrator/runs/r1/handoffs/code-generator.output.yaml"
    p.write_text(yaml.safe_dump({
        "status": "complete",
        "artifacts": [
            {"path": "src/auth/missing.py", "kind": "source"},
            {"path": "tests/test_x.py", "kind": "test"},
        ],
        "audit_entries": ["[Codegen]"],
        "skill_compliance": [{"skill": "x", "status": "PASS", "evidence": "ok"}],
        "locks_to_release": ["src/auth/**"],
    }))

    result = _run(["--mode", "strict", "code", str(p)])
    assert result.returncode == 1
    assert "missing" in result.stderr


def test_tests_happy_path(fake_run: Path):
    instructions = fake_run / "aidlc-docs/construction/build-instructions.md"
    instructions.parent.mkdir(parents=True)
    instructions.write_text("# Build instructions\n\nRun `pytest`.\n")
    summary = fake_run / "aidlc-docs/construction/build-and-test-summary.md"
    summary.write_text("# Summary\n\nAll tests passed (42/42).\n")

    p = fake_run / ".aidlc-orchestrator/runs/r1/handoffs/build-test-agent.output.yaml"
    p.write_text(yaml.safe_dump({
        "status": "complete",
        "artifacts": [
            {"path": "aidlc-docs/construction/build-instructions.md", "kind": "doc"},
            {"path": "aidlc-docs/construction/build-and-test-summary.md", "kind": "doc"},
        ],
        "audit_entries": ["[Build] green"],
        "skill_compliance": [{"skill": "x", "status": "PASS", "evidence": "ok"}],
    }))

    result = _run(["--mode", "strict", "tests", str(p)])
    assert result.returncode == 0, result.stderr


def test_tests_summary_without_pass_marker_fails(fake_run: Path):
    instructions = fake_run / "aidlc-docs/construction/build-instructions.md"
    instructions.parent.mkdir(parents=True)
    instructions.write_text("# Build instructions\n")
    summary = fake_run / "aidlc-docs/construction/build-and-test-summary.md"
    summary.write_text("# Summary\n\nResults pending review.\n")  # no pass token

    p = fake_run / ".aidlc-orchestrator/runs/r1/handoffs/build-test-agent.output.yaml"
    p.write_text(yaml.safe_dump({
        "status": "complete",
        "artifacts": [
            {"path": "aidlc-docs/construction/build-instructions.md", "kind": "doc"},
            {"path": "aidlc-docs/construction/build-and-test-summary.md", "kind": "doc"},
        ],
        "audit_entries": ["[Build] x"],
        "skill_compliance": [{"skill": "x", "status": "PASS", "evidence": "ok"}],
    }))

    result = _run(["--mode", "strict", "tests", str(p)])
    assert result.returncode == 1
    assert "pass" in result.stderr.lower()


def test_ship_happy_path(fake_run: Path):
    rn = fake_run / "RELEASE_NOTES.md"
    rn.write_text("# v1.0\nFirst release.\n")
    cl = fake_run / "CHANGELOG.md"
    cl.write_text("# Changelog\n\n## v1.0\n- initial\n")
    adr = fake_run / "aidlc-docs/operations/adrs/r1-0001-pick-postgres.md"
    adr.parent.mkdir(parents=True)
    adr.write_text("# ADR-0001: Pick PostgreSQL\n")

    p = fake_run / ".aidlc-orchestrator/runs/r1/handoffs/ship-agent.output.yaml"
    p.write_text(yaml.safe_dump({
        "status": "complete",
        "artifacts": [
            {"path": "RELEASE_NOTES.md", "kind": "doc"},
            {"path": "CHANGELOG.md", "kind": "doc"},
            {"path": "aidlc-docs/operations/adrs/r1-0001-pick-postgres.md", "kind": "doc"},
        ],
        "audit_entries": ["[Ship] done"],
        "skill_compliance": [{"skill": "x", "status": "PASS", "evidence": "ok"}],
        "version_proposed": "1.0.0",
    }))

    result = _run(["--mode", "strict", "ship", str(p)])
    assert result.returncode == 0, result.stderr


def test_ship_missing_release_notes_fails(fake_run: Path):
    cl = fake_run / "CHANGELOG.md"
    cl.write_text("# Changelog\n")

    p = fake_run / ".aidlc-orchestrator/runs/r1/handoffs/ship-agent.output.yaml"
    p.write_text(yaml.safe_dump({
        "status": "complete",
        "artifacts": [
            {"path": "CHANGELOG.md", "kind": "doc"},  # no RELEASE_NOTES
        ],
        "audit_entries": ["[Ship]"],
        "skill_compliance": [{"skill": "x", "status": "PASS", "evidence": "ok"}],
    }))

    result = _run(["--mode", "strict", "ship", str(p)])
    assert result.returncode == 1
    assert "RELEASE_NOTES" in result.stderr
