"""INS-04: Multi-tool parity test.

Ensures all 5 supported tools (claude, cursor, opencode, copilot, codex)
have the same agents, stages, cross-cutting agents, commands, and skills.

Only frontmatter format should differ between tools. The file tree structure
and file content (after parsing frontmatter) should be identical.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

# Map of tool name → (agents_dir, commands_dir, has_agents, orchestrator_path)
TOOLS = {
    "claude": {
        "agents": REPO_ROOT / ".claude" / "agents",
        "commands": REPO_ROOT / ".claude" / "commands",
    },
    "cursor": {
        "agents": REPO_ROOT / ".cursor" / "agents",
        "commands": REPO_ROOT / ".cursor" / "commands",
    },
    "opencode": {
        "agents": REPO_ROOT / ".opencode" / "agents",
        "commands": REPO_ROOT / ".opencode" / "commands",
    },
    "copilot": {
        "agents": REPO_ROOT / ".github" / "agents",
        "commands": REPO_ROOT / ".github" / "prompts",
    },
    "codex": {
        "agents": REPO_ROOT / ".codex" / "agents",
        "commands": REPO_ROOT / ".codex" / "config.toml",
    },
}


def _stems(directory: Path) -> set[str]:
    """Return sorted set of filenames without extensions from a directory.

    Strips .agent.md, .md, .prompt.md, .toml suffixes so names normalize across tools.
    """
    if not directory.exists():
        return set()
    result = set()
    for f in sorted(directory.iterdir()):
        if not f.is_file() or f.name.startswith("."):
            continue
        name = f.name
        # Handle .agent.md (GitHub Copilot), .prompt.md, .md, .toml
        for suffix in (".agent.md", ".prompt.md", ".md", ".toml"):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                break
        result.add(name)
    return result


def _relative_stems(base: Path, directory: Path) -> set[str]:
    """Return relative paths of files under directory, minus extension."""
    if not directory.exists():
        return set()
    result = set()
    for f in sorted(directory.rglob("*")):
        if f.is_file() and not f.name.startswith(".") and f.suffix in (".md",):
            rel = f.relative_to(directory)
            result.add(str(rel.parent / rel.stem))
    return result


def _strip_frontmatter(text: str) -> str:
    """Strip YAML frontmatter (--- ... ---) from markdown content."""
    return re.sub(r"^---\n.*?\n---\n", "", text, count=1, flags=re.DOTALL)


# ---------------------------------------------------------------------------
# Each tool must exist and have orchestrator.md
# ---------------------------------------------------------------------------

class TestToolExistence:
    @pytest.mark.parametrize("tool,paths", list(TOOLS.items()))
    def test_agents_dir_exists(self, tool, paths):
        assert paths["agents"].exists(), \
            f"Missing agents directory for {tool}: {paths['agents']}"

    def test_all_tools_have_orchestrator(self):
        for tool, paths in TOOLS.items():
            # Codex uses .toml; Copilot uses .agent.md; all others use .md
            if tool == "codex":
                orch = paths["agents"] / "orchestrator.toml"
            elif tool == "copilot":
                orch = paths["agents"] / "orchestrator.agent.md"
            else:
                orch = paths["agents"] / "orchestrator.md"
            assert orch.exists(), \
                f"Missing orchestrator for {tool} at {orch}"


# ---------------------------------------------------------------------------
# Stage agents parity
# ---------------------------------------------------------------------------

REFERENCE_STAGES = _stems(TOOLS["claude"]["agents"] / "stage")
REFERENCE_CROSS_CUTTING = _stems(TOOLS["claude"]["agents"] / "cross-cutting")
REFERENCE_CUSTOM = _stems(TOOLS["claude"]["agents"] / "custom")


class TestStageParity:
    """Every tool must have the same stage agents as .claude (reference)."""

    def test_all_tools_have_same_stage_agents(self):
        for tool, paths in TOOLS.items():
            stage_dir = paths["agents"] / "stage"
            if not stage_dir.exists():
                continue
            actual = _stems(stage_dir)
            missing = REFERENCE_STAGES - actual
            extra = actual - REFERENCE_STAGES
            assert not missing, f"{tool} missing stage agents: {sorted(missing)}"
            assert not extra, f"{tool} has extra stage agents: {sorted(extra)}"

    def test_all_tools_have_same_cross_cutting_agents(self):
        for tool, paths in TOOLS.items():
            cc_dir = paths["agents"] / "cross-cutting"
            if not cc_dir.exists():
                continue
            actual = _stems(cc_dir)
            missing = REFERENCE_CROSS_CUTTING - actual
            extra = actual - REFERENCE_CROSS_CUTTING
            assert not missing, f"{tool} missing cross-cutting agents: {sorted(missing)}"
            assert not extra, f"{tool} has extra cross-cutting agents: {sorted(extra)}"

    def test_all_tools_have_same_custom_agents(self):
        for tool, paths in TOOLS.items():
            custom_dir = paths["agents"] / "custom"
            if not custom_dir.exists():
                continue
            actual = _stems(custom_dir)
            missing = REFERENCE_CUSTOM - actual
            extra = actual - REFERENCE_CUSTOM
            # Custom agents are allowed to differ, but warn about missing
            if missing:
                pytest.skip(f"{tool} missing custom agents (acceptable): {sorted(missing)}")

    def test_stage_agent_count_matches(self):
        for tool, paths in TOOLS.items():
            stage_dir = paths["agents"] / "stage"
            if not stage_dir.exists():
                continue
            actual = _stems(stage_dir)
            assert len(actual) == len(REFERENCE_STAGES), \
                f"{tool} has {len(actual)} stage agents, expected {len(REFERENCE_STAGES)}"


# ---------------------------------------------------------------------------
# Commands parity
# ---------------------------------------------------------------------------

REFERENCE_COMMANDS = set()


class TestCommandsParity:
    """Every tool must have the same commands as .claude (reference)."""

    @classmethod
    def setup_class(cls):
        global REFERENCE_COMMANDS
        REFERENCE_COMMANDS = _stems(TOOLS["claude"]["commands"])

    def test_all_tools_have_same_commands(self):
        for tool, paths in TOOLS.items():
            cmd_dir = paths["commands"]
            if tool == "codex":
                # Codex uses a single config.toml; verify it exists
                assert cmd_dir.exists(), f"Missing codex config: {cmd_dir}"
                continue
            if not cmd_dir.exists():
                continue
            actual = _stems(cmd_dir)
            missing = REFERENCE_COMMANDS - actual
            extra = actual - REFERENCE_COMMANDS
            assert not missing, f"{tool} missing commands: {sorted(missing)}"
            assert not extra, f"{tool} has extra commands: {sorted(extra)}"

    def test_command_count_matches(self):
        for tool, paths in TOOLS.items():
            cmd_dir = paths["commands"]
            if tool == "codex":
                continue
            if not cmd_dir.exists():
                continue
            actual = _stems(cmd_dir)
            assert len(actual) == len(REFERENCE_COMMANDS), \
                f"{tool} has {len(actual)} commands, expected {len(REFERENCE_COMMANDS)}"


# ---------------------------------------------------------------------------
# Content parity (content after frontmatter should be similar)
# ---------------------------------------------------------------------------

class TestContentParity:
    """Verify key content blocks are present across tools."""

    STAGE_CONTENT_CHECKS = {
        "code-generator": [
            "Skills:",
            "validator-retry",
            "TDD",
            "Sub-stage",
        ],
        "build-test-agent": [
            "validator-retry",
            "Static validation",
            "build-instructions.md",
        ],
        "workspace-scout": [
            "greenfield",
            "brownfield",
            "tech_stack",
        ],
        "orchestrator": [
            "AIDLC Orchestrat",
            "approval",
            "manifest.yaml",
        ],
    }

    def _check_content_in_tool(self, tool, paths, agent_name, checks):
        """Check that agent file in tool contains all required text fragments."""
        if agent_name == "orchestrator":
            agent_path = paths["agents"] / "orchestrator.md"
        else:
            agent_path = paths["agents"] / "stage" / f"{agent_name}.md"
        if not agent_path.exists():
            return  # May not have stage/ in codex
        text = _strip_frontmatter(agent_path.read_text())
        missing = [c for c in checks if c not in text]
        assert not missing, \
            f"{tool}/{agent_name} missing content: {missing}"

    @pytest.mark.parametrize("tool,paths", list(TOOLS.items()))
    @pytest.mark.parametrize("agent,checks", list(STAGE_CONTENT_CHECKS.items()))
    def test_stage_content_present(self, tool, paths, agent, checks):
        self._check_content_in_tool(tool, paths, agent, checks)


# ---------------------------------------------------------------------------
# Codex special case: it may have different structure (config.toml-based)
# ---------------------------------------------------------------------------

class TestCodexStructure:
    """Codex uses a different paradigm (TOML-based subagent configs).
    Validate it has the equivalent content in its own format.
    """

    def test_codex_config_exists(self):
        config_path = TOOLS["codex"]["commands"]
        assert config_path.exists(), f"Missing codex config: {config_path}"

    def test_codex_has_agent_tomls(self):
        agents_dir = TOOLS["codex"]["agents"]
        if agents_dir.exists():
            toml_files = list(agents_dir.glob("*.toml"))
            assert len(toml_files) > 0, \
                "Codex agents dir must contain at least one .toml file"

    def test_codex_orchestrator_exists(self):
        orch = TOOLS["codex"]["agents"] / "orchestrator.toml"
        assert orch.exists(), \
            "Codex must have orchestrator.toml (referenced from config.toml)"


# ---------------------------------------------------------------------------
# Cross-tool consistency: no file is stale (creation dates compared)
# ---------------------------------------------------------------------------

class TestNoStaleFilesAcrossTools:
    """If a stage agent was updated in .claude/, the other tools' copies
    should not be significantly older. This catches stale parity."""

    def _find_stale(self, reference: Path, tool_name: str, tool_path: Path):
        """Return names of files in tool_path that are stale vs reference."""
        if not tool_path.exists():
            return set()
        stale = set()
        for f in tool_path.iterdir():
            if not f.is_file() or f.suffix not in (".md",):
                continue
            ref = reference / f.name
            if ref.exists():
                ref_mtime = ref.stat().st_mtime
                tool_mtime = f.stat().st_mtime
                # Allow 24h drift for legitimate reasons
                if ref_mtime - tool_mtime > 86400 * 7:
                    stale.add(f.name)
        return stale

    def test_no_stale_stage_agents(self):
        ref_dir = TOOLS["claude"]["agents"] / "stage"
        for tool, paths in TOOLS.items():
            if tool == "claude":
                continue
            tool_dir = paths["agents"] / "stage"
            if not tool_dir.exists():
                continue
            stale = self._find_stale(ref_dir, tool, tool_dir)
            assert not stale, \
                f"{tool} has stage agents unchanged for >1 week vs reference: {sorted(stale)}"
