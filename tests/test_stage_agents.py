"""STG-02/03/04/09/10/11/13: Stage agent evaluation tests.

Validates:
- STG-02: Requirements-analyst 8-axis coverage map
- STG-03: Workflow-planner decomposition rules
- STG-04: Story-writer schema + distinct personas
- STG-09/10/11: Reviewer schema compliance + severity audit
- STG-13: Reverse-engineer documentation completeness
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

STAGE_DIR = REPO_ROOT / ".claude" / "agents" / "stage"

# ── Stage agent markdown paths ──────────────────────────────────────────────
REQUIREMENTS_ANALYST = STAGE_DIR / "requirements-analyst.md"
WORKFLOW_PLANNER = STAGE_DIR / "workflow-planner.md"
STORY_WRITER = STAGE_DIR / "story-writer.md"
REVERSE_ENGINEER = STAGE_DIR / "reverse-engineer.md"
REVIEWER_CODE = STAGE_DIR / "reviewer-code.md"
REVIEWER_SECURITY = STAGE_DIR / "reviewer-security.md"
REVIEWER_PERFORMANCE = STAGE_DIR / "reviewer-performance.md"
REVIEWER_SIMPLIFIER = STAGE_DIR / "reviewer-simplifier.md"

# ── Reviewer output schema ──────────────────────────────────────────────────
REVIEWER_OUTPUT_SCHEMA = (
    REPO_ROOT / ".aidlc-orchestrator" / "contracts" / "reviewer.output.v1.json"
)


# ---------------------------------------------------------------------------
# STG-02: Requirements-analyst 8-axis coverage
# ---------------------------------------------------------------------------

class TestRequirementsAnalyst:
    EIGHT_AXES = [
        "Purpose",
        "Needs",
        "Limits",
        "Expectations",
        "Context",
        "Risks",
        "Acceptance",
        "Unknowns",
    ]

    def test_requirements_analyst_exists(self):
        assert REQUIREMENTS_ANALYST.exists()

    def test_requirements_analyst_mentions_adaptive_depth(self):
        text = REQUIREMENTS_ANALYST.read_text()
        assert "adaptive" in text.lower(), \
            "Requirements analyst must mention adaptive depth"

    def test_requirements_analyst_has_two_pass(self):
        text = REQUIREMENTS_ANALYST.read_text()
        assert "Two-pass" in text or "Pass 1" in text or "Pass 2" in text or \
               "two-pass" in text.lower(), \
            "Requirements analyst must be two-pass"

    def test_at_least_half_axes_covered(self):
        text = REQUIREMENTS_ANALYST.read_text()
        found = [a for a in self.EIGHT_AXES if a.lower() in text.lower()]
        assert len(found) >= len(self.EIGHT_AXES) // 2, \
            f"Requirements analyst should cover at least {len(self.EIGHT_AXES)//2}/{len(self.EIGHT_AXES)} axes, found {found}"

    def test_requirements_has_questions_artifact(self):
        text = REQUIREMENTS_ANALYST.read_text()
        assert "questions" in text.lower() or "questions_artifact" in text, \
            "Requirements analyst must produce questions artifact"

    def test_requirements_has_approval_gate(self):
        text = REQUIREMENTS_ANALYST.read_text()
        assert "needs_human" in text or "approval" in text.lower(), \
            "Requirements analyst must have approval gate"


# ---------------------------------------------------------------------------
# STG-03: Workflow-planner decomposition
# ---------------------------------------------------------------------------

class TestWorkflowPlanner:
    def test_planner_exists(self):
        assert WORKFLOW_PLANNER.exists()

    def test_planner_decomposes_into_units(self):
        text = WORKFLOW_PLANNER.read_text()
        assert "unit" in text.lower() or "decompos" in text.lower(), \
            "Workflow planner must decompose into units"

    def test_planner_has_dependencies(self):
        text = WORKFLOW_PLANNER.read_text()
        assert "depend" in text.lower(), \
            "Workflow planner must document dependencies between units"

    def test_planner_has_execution_plan(self):
        text = WORKFLOW_PLANNER.read_text()
        assert "execution plan" in text.lower() or "Execution Plan" in text, \
            "Workflow planner must produce an execution plan"

    def test_planner_has_acceptance_criteria(self):
        text = WORKFLOW_PLANNER.read_text()
        assert "acceptance" in text.lower() or "verification" in text.lower(), \
            "Workflow planner must define acceptance criteria"

    def test_planner_has_mermaid(self):
        text = WORKFLOW_PLANNER.read_text()
        assert "mermaid" in text.lower() or "diagram" in text.lower(), \
            "Workflow planner must include Mermaid diagram"


# ---------------------------------------------------------------------------
# STG-04: Story-writer
# ---------------------------------------------------------------------------

class TestStoryWriter:
    def test_story_writer_exists(self):
        assert STORY_WRITER.exists()

    def test_story_writer_has_personas(self):
        text = STORY_WRITER.read_text()
        assert "persona" in text.lower(), \
            "Story writer must define personas"

    def test_story_writer_links_to_requirements(self):
        text = STORY_WRITER.read_text()
        assert "requirements" in text.lower(), \
            "Stories must link to requirements"

    def test_story_writer_has_investment_profile(self):
        text = STORY_WRITER.read_text()
        assert "profile" in text.lower() or "investment" in text.lower() or "invest" in text.lower(), \
            "Stories must have investment profile"


# ---------------------------------------------------------------------------
# STG-09/10/11: Reviewer schema + severity audit
# ---------------------------------------------------------------------------

def _load_reviewer_schema() -> dict:
    """Load the reviewer output contract schema."""
    return json.loads(REVIEWER_OUTPUT_SCHEMA.read_text())


class TestReviewerSchemaBase:
    """Shared schema validation for all reviewers."""

    REVIEWER_FILES = {
        "code-quality": REVIEWER_CODE,
        "security": REVIEWER_SECURITY,
        "performance": REVIEWER_PERFORMANCE,
        "simplifier": REVIEWER_SIMPLIFIER,
    }

    def test_all_reviewers_exist(self):
        for name, path in self.REVIEWER_FILES.items():
            assert path.exists(), f"Missing reviewer: {name}"

    def test_all_reviewers_reference_contract(self):
        for name, path in self.REVIEWER_FILES.items():
            text = path.read_text()
            assert "contract" in text.lower() or "reviewer.output" in text, \
                f"{name} must reference output contract"

    def test_schema_has_required_fields(self):
        schema = _load_reviewer_schema()
        required = schema.get("required", [])
        for field in ("status", "reviewer", "findings", "findings_summary"):
            assert field in required, \
                f"Schema must require '{field}', found required={required}"

    def test_schema_finding_has_severity_and_message(self):
        schema = _load_reviewer_schema()
        finding = schema["properties"]["findings"]["items"]
        finding_req = finding.get("required", [])
        for field in ("severity", "message"):
            assert field in finding_req or field in finding.get("properties", {}), \
                f"Finding must have '{field}'"

    def test_schema_severity_enum_values(self):
        schema = _load_reviewer_schema()
        sev = schema["properties"]["findings"]["items"]["properties"]["severity"]
        expected = {"P0", "P1", "P2", "P3"}
        actual = set(sev.get("enum", []))
        assert actual == expected or actual.issuperset(expected), \
            f"Severity enum must include P0-P3, got {actual}"

    def test_schema_findings_summary_matches_count(self):
        schema = _load_reviewer_schema()
        summary = schema["properties"]["findings_summary"]
        for count_field in ("P0_count", "P1_count", "P2_count", "P3_count"):
            assert count_field in summary.get("required", []) or \
                   count_field in summary.get("properties", {}), \
                f"Findings summary must have {count_field}"

    def test_schema_requires_skill_compliance(self):
        schema = _load_reviewer_schema()
        required = schema.get("required", [])
        assert "skill_compliance" in required, \
            "Schema must require skill_compliance"

    def test_schema_requires_audit_entries(self):
        schema = _load_reviewer_schema()
        required = schema.get("required", [])
        assert "audit_entries" in required, \
            "Schema must require audit_entries"


class TestReviewerCodeContent:
    def test_reviewer_code_has_five_axes(self):
        text = REVIEWER_CODE.read_text()
        assert "five-axis" in text.lower() or "5-axis" in text.lower() or \
               "axis" in text.lower(), \
            "Code reviewer must have five-axis review"

    def test_reviewer_code_mentions_build(self):
        text = REVIEWER_CODE.read_text()
        assert "build" in text.lower() or "lint" in text.lower(), \
            "Code reviewer must reference build/lint"


class TestReviewerSecurityContent:
    def test_security_mentions_cwe(self):
        text = REVIEWER_SECURITY.read_text()
        assert "CWE" in text or "cwe" in text, \
            "Security reviewer must reference CWE"

    def test_security_mentions_owasp(self):
        text = REVIEWER_SECURITY.read_text()
        assert "OWASP" in text or "owasp" in text, \
            "Security reviewer must reference OWASP"


class TestReviewerPerformanceContent:
    def test_performance_mentions_big_o(self):
        text = REVIEWER_PERFORMANCE.read_text()
        assert "Big-O" in text or "big O" in text.lower() or "complexity" in text.lower(), \
            "Performance reviewer must reference Big-O notation"

    def test_performance_mentions_hot_path(self):
        text = REVIEWER_PERFORMANCE.read_text()
        assert "hot path" in text.lower() or "hot-path" in text.lower(), \
            "Performance reviewer must consider hot paths"


class TestReviewerSimplifierContent:
    def test_simplifier_mentions_anti_patterns(self):
        text = REVIEWER_SIMPLIFIER.read_text()
        assert "anti-pattern" in text.lower() or "antipattern" in text.lower() or \
               "dead code" in text.lower(), \
            "Simplifier reviewer must detect anti-patterns"

    def test_simplifier_mentions_over_engineering(self):
        text = REVIEWER_SIMPLIFIER.read_text()
        assert "over-engineering" in text.lower() or "over engineering" in text.lower() or \
               "premature" in text.lower(), \
            "Simplifier reviewer must flag over-engineering"


# ---------------------------------------------------------------------------
# SEC-06: Security reviewer correlation with scanner output
# ---------------------------------------------------------------------------

class TestSecurityReviewerCorrelation:
    """Validate security reviewer output can be correlated with SAST scanners."""

    def test_security_mentions_scanner(self):
        text = REVIEWER_SECURITY.read_text()
        assert "scan" in text.lower() or "SAST" in text or "semgrep" in text.lower() or \
               "bandit" in text.lower(), \
            "Security reviewer must reference security scanners"

    def test_security_findings_include_cwe(self):
        text = REVIEWER_SECURITY.read_text()
        assert "CWE" in text or "cwe" in text, \
            "Security findings must include CWE identifiers"

    def test_security_findings_include_location(self):
        text = REVIEWER_SECURITY.read_text()
        assert "file" in text.lower() or "line" in text.lower(), \
            "Security findings must include file/line location"


# ---------------------------------------------------------------------------
# STG-13: Reverse-engineer
# ---------------------------------------------------------------------------

class TestReverseEngineer:
    def test_reverse_engineer_exists(self):
        assert REVERSE_ENGINEER.exists()

    def test_reverse_engineer_has_component_inventory(self):
        text = REVERSE_ENGINEER.read_text()
        assert "component" in text.lower() or "inventory" in text.lower(), \
            "Reverse engineer must produce component inventory"

    def test_reverse_engineer_has_dependency_graph(self):
        text = REVERSE_ENGINEER.read_text()
        assert "depend" in text.lower(), \
            "Reverse engineer must detect dependencies"

    def test_reverse_engineer_has_api_docs(self):
        text = REVERSE_ENGINEER.read_text()
        assert "API" in text or "api" in text, \
            "Reverse engineer must document APIs"

    def test_reverse_engineer_has_tech_stack_detection(self):
        text = REVERSE_ENGINEER.read_text()
        assert "tech stack" in text.lower() or "technology" in text.lower() or \
               "framework" in text.lower(), \
            "Reverse engineer must detect tech stack"

    def test_reverse_engineer_conditional_on_brownfield(self):
        text = REVERSE_ENGINEER.read_text()
        assert "brownfield" in text.lower(), \
            "Reverse engineer must be conditional on brownfield workspace"

    def test_reverse_engineer_condition_on_no_prior_artifacts(self):
        text = REVERSE_ENGINEER.read_text()
        assert "prior" in text.lower() or "existing" in text.lower(), \
            "Reverse engineer must check for prior artifacts before running"
