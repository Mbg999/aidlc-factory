"""E2E tests for AI Architecture Cookbook integration.

Covers Unit 6 tasks T6.1-T6.5 from the execution plan.

T6.1-T6.3 require a running OpenCode session and can't be automated in
Python. This file tests the structural integration points and provides
smoke-test stubs for manual execution.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "aidlc-scripts"
VALIDATE_PY = SCRIPTS / "factory_validate.py"
FEATURES_PY = SCRIPTS / "factory_features.py"

STAGE_DIR = REPO_ROOT.parent / ".opencode" / "agents" / "stage"

COOKBOOK_AGENTS = [
    "workspace-scout",
    "requirements-analyst",
    "code-generator",
    "reviewer-code",
    "reviewer-security",
    "reviewer-performance",
    "ship-agent",
]

# ── Helpers ────────────────────────────────────────────────────────────────────


def _run_validate(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(VALIDATE_PY), *args],
        capture_output=True, text=True,
    )


def _run_features(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(FEATURES_PY), *args],
        capture_output=True, text=True,
    )


def _agent_text(name: str) -> str:
    path = STAGE_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


# ── T6.1: spec triggers Cookbook call (structural) ────────────────────────────


class TestSpecTriggersCookbookCall:
    """T6.1 — Verify workspace-scout and requirements-analyst reference Cookbook."""

    def test_workspace_scout_references_cookbook(self):
        text = _agent_text("workspace-scout")
        assert "ai-architecture-cookbook" in text, \
            "workspace-scout must reference the Cookbook skill"

    def test_workspace_scout_has_fallback(self):
        text = _agent_text("workspace-scout")
        assert "fallback" in text.lower() or "degrad" in text.lower(), \
            "workspace-scout must document fallback behavior for MCP unavailability"

    def test_requirements_analyst_references_cookbook(self):
        text = _agent_text("requirements-analyst")
        assert "ai-architecture-cookbook" in text, \
            "requirements-analyst must reference the Cookbook skill"


# ── T6.2: build uses decision tree (structural) ───────────────────────────────


class TestBuildUsesDecisionTree:
    """T6.2 — Verify code-generator references Cookbook decision tools."""

    def test_code_generator_references_cookbook(self):
        text = _agent_text("code-generator")
        assert "ai-architecture-cookbook" in text, \
            "code-generator must reference the Cookbook skill"

    def test_code_generator_has_decision_tree_reference(self):
        text = _agent_text("code-generator")
        has_decision = "decision_tree" in text or "decision" in text.lower()
        has_checklist = "checklist" in text.lower()
        assert has_decision or has_checklist, \
            "code-generator must reference decision tree or checklist tools"

    def test_code_generator_has_fallback(self):
        text = _agent_text("code-generator")
        assert "fallback" in text.lower() or "degrad" in text.lower(), \
            "code-generator must document fallback behavior"


# ── T6.3: review includes checklist items (structural) ────────────────────────


class TestReviewIncludesChecklistItems:
    """T6.3 — Verify reviewer agents reference Cookbook checklists."""

    def test_reviewer_code_references_cookbook(self):
        text = _agent_text("reviewer-code")
        assert "ai-architecture-cookbook" in text, \
            "reviewer-code must reference the Cookbook skill"

    def test_reviewer_security_references_cookbook(self):
        text = _agent_text("reviewer-security")
        assert "ai-architecture-cookbook" in text, \
            "reviewer-security must reference the Cookbook skill"

    def test_reviewer_performance_references_cookbook(self):
        text = _agent_text("reviewer-performance")
        assert "ai-architecture-cookbook" in text, \
            "reviewer-performance must reference the Cookbook skill"

    def test_ship_agent_references_cookbook(self):
        text = _agent_text("ship-agent")
        assert "ai-architecture-cookbook" in text, \
            "ship-agent must reference the Cookbook skill"


# ── T6.4: Degradation — MCP down, factory still works ─────────────────────────


class TestDegradation:
    """T6.4 — Verify --check-cookbook correctly identifies all three states."""

    def test_healthy_with_mcp_and_yaml(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("AIDLC_ROOT", str(tmp_path))
        cookbook = tmp_path / ".ai-architecture-cookbook"
        (cookbook / "mcp-server" / "dist").mkdir(parents=True)
        (cookbook / "mcp-server" / "dist" / "server.js").write_text("// mock")
        (cookbook / "standards").mkdir(parents=True)
        (cookbook / "standards" / "test.yaml").write_text("key: val")
        result = _run_validate("--check-cookbook")
        assert "unhealthy" not in result.stdout
        assert result.returncode == 0

    def test_degraded_yaml_only(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("AIDLC_ROOT", str(tmp_path))
        cookbook = tmp_path / ".ai-architecture-cookbook"
        (cookbook / "standards").mkdir(parents=True)
        (cookbook / "standards" / "test.yaml").write_text("key: val")
        result = _run_validate("--check-cookbook")
        assert "degraded" in result.stdout.lower()
        assert result.returncode == 0

    def test_unhealthy_nothing_found(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
        monkeypatch.setenv("AIDLC_ROOT", str(tmp_path))
        result = _run_validate("--check-cookbook")
        assert "unhealthy" in result.stdout.lower()
        assert result.returncode == 1

    def test_feature_flag_defaults_to_false(self, tmp_path: Path):
        budgets = tmp_path / ".aidlc-orchestrator" / "budgets"
        budgets.mkdir(parents=True)
        (budgets / "default.yaml").write_text("features:\n")
        result = _run_features("--repo-root", str(tmp_path),
                               "get", "architecture_cookbook_enabled")
        assert result.returncode == 0
        assert result.stdout.strip() == "false"

    def test_feature_flag_can_be_set_true(self, tmp_path: Path):
        budgets = tmp_path / ".aidlc-orchestrator" / "budgets"
        budgets.mkdir(parents=True)
        (budgets / "default.yaml").write_text(
            yaml.safe_dump({"per_stage": {}, "features": {"architecture_cookbook_enabled": True}})
        )
        result = _run_features("--repo-root", str(tmp_path),
                               "is-set", "architecture_cookbook_enabled")
        assert result.returncode == 0


# ── T6.5: Regression (structural check) ───────────────────────────────────────


class TestRegression:
    """T6.5 — Verify existing infrastructure is intact."""

    def test_cookbook_skill_exists(self):
        skill_path = REPO_ROOT.parent / ".agents" / "custom-skills" / "ai-architecture-cookbook" / "SKILL.md"
        assert skill_path.exists(), "Cookbook SKILL.md must exist"
        text = skill_path.read_text(encoding="utf-8")
        assert text.startswith("---"), "SKILL.md must have YAML frontmatter"

    def test_cookbook_contracts_exist(self):
        contracts_dir = REPO_ROOT.parent / ".aidlc-orchestrator" / "contracts" / "cookbook"
        assert contracts_dir.exists(), "Cookbook contracts directory must exist"
        schemas = list(contracts_dir.glob("*.json"))
        assert len(schemas) >= 2, "Expected at least 2 cookbook JSON schemas"

    def test_cookbook_budget_flag_exists(self):
        budget_path = REPO_ROOT.parent / ".aidlc-orchestrator" / "budgets" / "default.yaml"
        assert budget_path.exists()
        text = budget_path.read_text(encoding="utf-8")
        assert "architecture_cookbook_enabled" in text

    def test_all_cookbook_agents_wired(self):
        for agent in COOKBOOK_AGENTS:
            path = STAGE_DIR / f"{agent}.md"
            assert path.exists(), f"Stage agent file must exist: {agent}.md"
            text = path.read_text(encoding="utf-8")
            assert "ai-architecture-cookbook" in text, \
                f"{agent}.md must reference ai-architecture-cookbook skill"


# ── Live E2E smoke-test stubs ─────────────────────────────────────────────────


class TestLiveE2ESmokeStubs:
    """Stubs for manual E2E tests that require a running OpenCode session.

    These tests document the manual verification procedure. They are skipped
    by default because they require a live OpenCode environment.
    """

    @pytest.mark.skip(reason="Requires running OpenCode session")
    def test_factory_spec_with_cookbook(self):
        """T6.1 smoke test:
        1. Create a temp greenfield project with the AIDLC installer
        2. Run: install_aidlc.py --with-architecture-cookbook
        3. Run: /factory-spec "build an API with auth"
        4. Verify: agent output contains a Cookbook pattern recommendation
        """
        ...

    @pytest.mark.skip(reason="Requires running OpenCode session")
    def test_factory_build_with_cookbook(self):
        """T6.2 smoke test:
        1. Run: /factory-build on brownfield project
        2. Verify: code-generator calls get_decision_tree
        3. Verify: recommended pattern appears in generated code
        """
        ...

    @pytest.mark.skip(reason="Requires running OpenCode session")
    def test_factory_review_with_cookbook(self):
        """T6.3 smoke test:
        1. Run: /factory-review on a project
        2. Verify: review report includes get_checklist items
        3. Verify: checklist items include Cookbook standard ID citations
        """
        ...

    @pytest.mark.skip(reason="Requires running OpenCode session")
    def test_degradation_mcp_down(self):
        """T6.4 smoke test:
        1. Start a factory run with Cookbook enabled
        2. Disconnect MCP server mid-run
        3. Verify: all stages fall back to inline YAML — no crashes
        4. Verify: WARNING-level log emitted for each fallback
        """
        ...
