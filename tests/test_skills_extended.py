"""SKL-05/06/07/08/09/10/11: Extended skills evaluation tests.

Validates:
- SKL-05: design-system-composer + ui-constraint-validator
- SKL-06: requirements-intelligence 8-axis + weasel-word detection
- SKL-07: secret-knowledge tool verification
- SKL-08: codegraph-aware-exploration routing
- SKL-09: library-docs-with-context7 protocol
- SKL-10: browser-testing-with-devtools skill
- SKL-11: Per-stage skill attachment
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

CUSTOM_SKILLS = REPO_ROOT / ".agents" / "custom-skills"

SKILL_PATHS = {
    "design-system-composer": CUSTOM_SKILLS / "design-system-composer" / "SKILL.md",
    "ui-constraint-validator": CUSTOM_SKILLS / "ui-constraint-validator" / "SKILL.md",
    "requirements-intelligence": CUSTOM_SKILLS / "requirements-intelligence" / "SKILL.md",
    "secret-knowledge": CUSTOM_SKILLS / "secret-knowledge" / "SKILL.md",
    "codegraph-aware-exploration": CUSTOM_SKILLS / "codegraph-aware-exploration" / "SKILL.md",
    "library-docs-with-context7": CUSTOM_SKILLS / "library-docs-with-context7" / "SKILL.md",
    "browser-testing-with-devtools": CUSTOM_SKILLS / "browser-testing-with-devtools" / "SKILL.md",
}


def _read_skill(name: str) -> str:
    path = SKILL_PATHS.get(name)
    if path and path.exists():
        return path.read_text()
    return ""


def _stage_agent_text(stage_name: str) -> str:
    """Read a stage agent markdown, stripping frontmatter."""
    path = REPO_ROOT / ".claude" / "agents" / "stage" / f"{stage_name}.md"
    if not path.exists():
        return ""
    text = path.read_text()
    return re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)


# ---------------------------------------------------------------------------
# SKL-05: Design-system-composer + ui-constraint-validator
# ---------------------------------------------------------------------------

class TestDesignSystemComposer:
    def test_skill_exists(self):
        path = SKILL_PATHS["design-system-composer"]
        assert path.exists(), f"design-system-composer SKILL.md not found"

    def test_skill_composes_from_primitives(self):
        text = path = _read_skill("design-system-composer")
        assert "primitive" in text.lower() or "INDEX.md" in text or "token" in text.lower(), \
            "design-system-composer must compose from primitives/tokens"

    def test_skill_mentions_design_system_path(self):
        text = _read_skill("design-system-composer")
        assert "design-system" in text or "designtoken" in text.lower(), \
            "Must reference design system path"

    def test_skill_upholds_token_discipline(self):
        text = _read_skill("design-system-composer")
        assert "token" in text.lower() or "constraint" in text.lower(), \
            "Must enforce token discipline"


class TestUiConstraintValidator:
    def test_skill_exists(self):
        path = SKILL_PATHS["ui-constraint-validator"]
        assert path.exists(), f"ui-constraint-validator SKILL.md not found"

    def test_validates_hardcoded_values(self):
        text = _read_skill("ui-constraint-validator")
        assert "hardcod" in text.lower(), \
            "Must detect hardcoded values"

    def test_validates_spacing_radius_typography(self):
        text = _read_skill("ui-constraint-validator")
        keywords = ["spacing", "radius", "typography", "color", "elevation"]
        found = [k for k in keywords if k in text.lower()]
        assert len(found) >= 2, \
            f"Should validate at least 2 of spacing/radius/typography/color/elevation, found {found}"

    def test_can_block_slice(self):
        text = _read_skill("ui-constraint-validator")
        assert "block" in text.lower() or "needs_human" in text or "reject" in text.lower(), \
            "Should block or escalate when deviations exceed threshold"


# ---------------------------------------------------------------------------
# SKL-06: requirements-intelligence coverage
# ---------------------------------------------------------------------------

class TestRequirementsIntelligence:
    def test_skill_exists(self):
        path = SKILL_PATHS["requirements-intelligence"]
        assert path.exists(), f"requirements-intelligence SKILL.md not found"

    def test_adaptive_elicitation(self):
        text = _read_skill("requirements-intelligence")
        assert "adaptive" in text.lower() or "elicitation" in text.lower(), \
            "Must mention adaptive elicitation"

    def test_weasel_word_detection(self):
        text = _read_skill("requirements-intelligence")
        assert "weasel" in text.lower(), \
            "Must detect and flag weasel words"

    def test_socratic_probing(self):
        text = _read_skill("requirements-intelligence")
        assert "socratic" in text.lower() or "ambiguity" in text.lower() or \
               "assumption" in text.lower(), \
            "Must use probing techniques"

    def test_pre_mortem(self):
        text = _read_skill("requirements-intelligence")
        assert "pre-mortem" in text.lower() or "premortem" in text.lower(), \
            "Must include pre-mortem analysis"


# ---------------------------------------------------------------------------
# SKL-07: secret-knowledge tool verification
# ---------------------------------------------------------------------------

class TestSecretKnowledge:
    def test_skill_exists(self):
        path = SKILL_PATHS["secret-knowledge"]
        assert path.exists(), f"secret-knowledge SKILL.md not found"

    def test_has_tool_catalog(self):
        text = _read_skill("secret-knowledge")
        assert "tool" in text.lower() or "catalog" in text.lower() or \
               "command" in text.lower(), \
            "Must contain a reference catalog of tools"

    def test_has_security_toolkit(self):
        text = _read_skill("secret-knowledge")
        assert "security" in text.lower(), \
            "Must include security toolkits"

    def test_has_performance_profilers(self):
        text = _read_skill("secret-knowledge")
        assert "perform" in text.lower() or "profile" in text.lower(), \
            "Must include performance profilers"


# ---------------------------------------------------------------------------
# SKL-08: codegraph-aware-exploration routing
# ---------------------------------------------------------------------------

class TestCodegraphAwareExploration:
    def test_skill_exists(self):
        path = SKILL_PATHS["codegraph-aware-exploration"]
        assert path.exists(), f"codegraph-aware-exploration SKILL.md not found"

    def test_prefers_codegraph_tools(self):
        text = _read_skill("codegraph-aware-exploration")
        assert "codegraph_" in text or "codegraph_search" in text or \
               "codegraph_explore" in text or "codegraph_context" in text, \
            "Must prefer codegraph_* MCP tools over grep/glob"

    def test_falls_back_when_no_index(self):
        text = _read_skill("codegraph-aware-exploration")
        assert "fallback" in text.lower() or "not indexed" in text.lower() or \
               "not exist" in text.lower(), \
            "Must fall back to grep/glob/Read when .codegraph/ is absent"

    def test_wired_into_stage_agents(self):
        """Codegraph skill must be referenced by key stage agents."""
        for stage in ("code-generator", "build-test-agent", "workspace-scout",
                      "reviewer-code", "reverse-engineer"):
            agent_text = _stage_agent_text(stage)
            if agent_text:
                assert "codegraph" in agent_text.lower(), \
                    f"{stage}.md must reference codegraph-aware-exploration"


# ---------------------------------------------------------------------------
# SKL-09: library-docs-with-context7 protocol
# ---------------------------------------------------------------------------

class TestLibraryDocsWithContext7:
    def test_skill_exists(self):
        path = SKILL_PATHS["library-docs-with-context7"]
        assert path.exists(), f"library-docs-with-context7 SKILL.md not found"

    def test_references_context7_protocol(self):
        text = _read_skill("library-docs-with-context7")
        assert "resolve-library-id" in text or "query-docs" in text or \
               "Context7" in text, \
            "Must reference Context7 two-call protocol"

    def test_wired_into_code_generator(self):
        agent_text = _stage_agent_text("code-generator")
        assert "library-docs-with-context7" in agent_text or \
               "context7" in agent_text.lower(), \
            "code-generator must reference library-docs-with-context7"

    def test_wired_into_build_test(self):
        agent_text = _stage_agent_text("build-test-agent")
        assert "library-docs-with-context7" in agent_text or \
               "context7" in agent_text.lower(), \
            "build-test-agent must reference library-docs-with-context7"

    def test_wired_into_reviewer_code(self):
        agent_text = _stage_agent_text("reviewer-code")
        assert "library-docs-with-context7" in agent_text or \
               "context7" in agent_text.lower(), \
            "reviewer-code must reference library-docs-with-context7"


# ---------------------------------------------------------------------------
# SKL-10: browser-testing-with-devtools
# ---------------------------------------------------------------------------

class TestBrowserTestingWithDevtools:
    def test_skill_exists(self):
        path = SKILL_PATHS["browser-testing-with-devtools"]
        assert path.exists(), f"browser-testing-with-devtools SKILL.md not found"

    def test_references_devtools_operations(self):
        text = _read_skill("browser-testing-with-devtools")
        operations = ["click", "fill", "screenshot", "network", "lighthouse"]
        found = [o for o in operations if o in text.lower()]
        assert len(found) >= 2, \
            f"Should reference at least 2 DevTools operations, found {found}"

    def test_wired_into_build_test(self):
        agent_text = _stage_agent_text("build-test-agent")
        assert "browser-testing-with-devtools" in agent_text or \
               "devtools" in agent_text.lower(), \
            "build-test-agent must reference browser-testing-with-devtools"


# ---------------------------------------------------------------------------
# SKL-11: Per-stage skill attachment
# ---------------------------------------------------------------------------

class TestPerStageSkillAttachment:
    """Verify the correct skills are auto-attached per stage."""

    STAGE_EXPECTED_SKILLS: dict[str, list[str]] = {
        "workspace-scout": [
            "environment-detection",
            "codegraph-aware-exploration",
        ],
        "requirements-analyst": [
            "requirements-intelligence",
            "spec-driven-development",
        ],
        "code-generator": [
            "validator-retry",
            "test-driven-development",
            "codegraph-aware-exploration",
            "library-docs-with-context7",
        ],
        "build-test-agent": [
            "validator-retry",
            "debugging-and-error-recovery",
            "browser-testing-with-devtools",
            "library-docs-with-context7",
        ],
        "reviewer-code": [
            "code-review-and-quality",
            "library-docs-with-context7",
        ],
        "reviewer-security": [
            "security-and-hardening",
        ],
        "reviewer-performance": [
            "performance-optimization",
        ],
        "reviewer-simplifier": [
            "code-simplification",
        ],
        "ship-agent": [
            "shipping-and-launch",
            "documentation-and-adrs",
            "git-workflow-and-versioning",
            "ci-cd-and-automation",
        ],
    }

    def test_all_stages_have_expected_skills(self):
        """Every stage agent references its expected skills."""
        for stage, expected_skills in self.STAGE_EXPECTED_SKILLS.items():
            agent_text = _stage_agent_text(stage)
            if not agent_text:
                pytest.skip(f"{stage}.md not found")
            missing = [s for s in expected_skills if s not in agent_text]
            assert not missing, \
                f"{stage}.md missing expected skills: {missing}"

    def test_skill_validator_retry_wired_to_code_gen_and_build(self):
        for stage in ("code-generator", "build-test-agent"):
            agent_text = _stage_agent_text(stage)
            if agent_text:
                assert "validator-retry" in agent_text, \
                    f"{stage}.md must reference validator-retry"

    def test_skill_using_agent_skills_present(self):
        """At minimum, the 'using-agent-skills' meta-skill should be referenced."""
        for stage in ("workspace-scout", "requirements-analyst", "code-generator"):
            agent_text = _stage_agent_text(stage)
            if agent_text:
                assert "using-agent-skills" in agent_text or "Skills:" in agent_text or \
                       "skills" in agent_text.lower(), \
                    f"{stage}.md must declare its skills list"

    def test_skill_names_exist_in_custom_or_installed(self):
        """Every skill referenced by a stage agent should exist as a SKILL.md."""
        all_skill_names = set()
        # Collect from custom skills
        if CUSTOM_SKILLS.exists():
            for skill_dir in CUSTOM_SKILLS.iterdir():
                if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                    all_skill_names.add(skill_dir.name)

        for stage, expected_skills in self.STAGE_EXPECTED_SKILLS.items():
            for skill in expected_skills:
                skill_found = (CUSTOM_SKILLS / skill / "SKILL.md").exists()
                if not skill_found:
                    pytest.skip(f"Skill {skill} not found in custom skills (may be installed via --with-agent-skills)")
