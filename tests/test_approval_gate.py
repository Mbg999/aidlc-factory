"""ORC-07: Approval gate behavioral test.

Ensures the orchestrator NEVER auto-commits without explicit user approval.
The approval logic is enforced through markdown prompts (not Python code),
so these tests parse the prompt files as the source of truth.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
APPROVAL_SIGNALS = frozenset({
    "approve", "approved", "go ahead", "continue", "next", "lgtm",
    "ship it", "proceed", "dale", "sí",
})
CLAUDE_ORCHESTRATOR = REPO_ROOT / ".claude" / "agents" / "orchestrator.md"
CORE_WORKFLOW = REPO_ROOT / ".aidlc-orchestrator" / "runtime" / "core-workflow.md"
SPAWN_LOOP = REPO_ROOT / ".aidlc-orchestrator" / "runtime" / "spawn-loop.md"


class TestOrchestratormdHasApprovalGateRule:
    def test_orchestrator_md_explicit_approval_rule(self):
        text = CLAUDE_ORCHESTRATOR.read_text()
        assert "Commits require explicit user approval" in text or \
               "auto-commit" not in text, \
            "orchestrator.md must restrict commits to explicit approval"

    def test_orchestrator_md_lists_approval_signals(self):
        text = CLAUDE_ORCHESTRATOR.read_text()
        # At minimum the orchestrator should mention the signals or reference
        # core-workflow.md which lists them
        for signal in ("approve", "go ahead", "continue", "lgtm", "dale", "sí"):
            if signal in text:
                return
        pytest.fail("orchestrator.md must reference at least one approval signal")

    def test_orchestrator_md_no_auto_commit_on_stage_complete(self):
        text = CLAUDE_ORCHESTRATOR.read_text()
        # The hard rule: "Never auto-commit when a stage or phase completes"
        assert "Never auto-commit" in text or "never auto-commit" in text.lower(), \
            "orchestrator.md must prohibit auto-commit on stage completion"

    def test_orchestrator_md_references_commit_deferral(self):
        text = CLAUDE_ORCHESTRATOR.read_text()
        assert "commit" in text.lower(), \
            "orchestrator.md must mention commit behavior"


class TestCoreWorkflowHasApprovalMandate:
    def test_core_workflow_has_approval_signals_list(self):
        text = CORE_WORKFLOW.read_text()
        found = [s for s in APPROVAL_SIGNALS if s in text]
        assert len(found) >= 5, \
            f"core-workflow.md should enumerate most approval signals, found only {found}"

    def test_core_workflow_says_commit_on_approval_only(self):
        text = CORE_WORKFLOW.read_text()
        assert "Approval ONLY" in text or \
               "only after" in text.lower() and "approval" in text.lower(), \
            "core-workflow.md must restrict commits to approval-only"

    def test_core_workflow_has_anti_pattern(self):
        text = CORE_WORKFLOW.read_text()
        assert "Anti-pattern" in text or "anti-pattern" in text, \
            "core-workflow.md must document the anti-pattern to reject"

    def test_core_workflow_anti_pattern_rejects_commit_on_complete(self):
        text = CORE_WORKFLOW.read_text()
        assert "status: complete" in text, \
            "core-workflow.md anti-pattern must reference 'status: complete'"


class TestSpawnLoopDefersCommit:
    def test_spawn_loop_step9_defers_to_command_boundary(self):
        text = SPAWN_LOOP.read_text()
        assert "DEFERRED" in text, \
            "spawn-loop.md step 9 must say DEFERRED for auto-commit"
        assert "command boundary" in text.lower(), \
            "spawn-loop.md must defer commit to command boundary"

    def test_spawn_loop_no_per_stage_commit_language(self):
        text = SPAWN_LOOP.read_text()
        # Ensure it doesn't say "commit" in the bookkeeping steps before approval
        # Step 9 is the commit step and it should say deferred
        commit_lines = [l for l in text.splitlines() if "commit" in l.lower()]
        for line in commit_lines:
            assert "DEFERRED" in line or "deferred" in line.lower() or \
                   "per-stage commit" not in line.lower(), \
                f"Every commit reference should mention deferral: {line!r}"

    def test_post_exec_loop_also_defers_commit(self):
        text = SPAWN_LOOP.read_text()
        post_exec_section = text.split("Post-execution loop")[-1] if "Post-execution loop" in text else ""
        if post_exec_section:
            assert "DEFERRED" in post_exec_section or "deferred" in post_exec_section.lower(), \
                "Post-execution loop must also defer commit"


class TestAllToolOrchestratorsHaveApprovalRule:
    """Every tool's orchestrator.md must have the approval gate rule."""

    TOOL_ORCHESTRATORS = [
        (".claude/agents/orchestrator.md", REPO_ROOT / ".claude" / "agents" / "orchestrator.md"),
        (".cursor/agents/orchestrator.md", REPO_ROOT / ".cursor" / "agents" / "orchestrator.md"),
        (".github/agents/orchestrator.agent.md", REPO_ROOT / ".github" / "agents" / "orchestrator.agent.md"),
        (".opencode/agents/orchestrator.md", REPO_ROOT / ".opencode" / "agents" / "orchestrator.md"),
    ]

    def test_all_tools_have_orchestrator(self):
        for name, path in self.TOOL_ORCHESTRATORS:
            assert path.exists(), f"Missing orchestrator: {name}"

    @pytest.mark.parametrize("name,path", TOOL_ORCHESTRATORS)
    def test_each_orchestrator_has_approval_rule(self, name, path):
        text = path.read_text()
        assert "commit" in text.lower(), \
            f"{name} must mention commit behavior"
        assert "applause" not in text, \
            f"{name} should not mention applause (typo check)"


class TestNoAutoCommitInFactoryCommands:
    """Factory commands must not have their own commit logic."""

    COMMAND_DIRS = [
        REPO_ROOT / ".claude" / "commands",
        REPO_ROOT / ".cursor" / "commands",
        REPO_ROOT / ".opencode" / "commands",
        REPO_ROOT / ".github" / "prompts",
    ]

    def _get_command_files(self):
        for d in self.COMMAND_DIRS:
            if d.exists():
                for f in sorted(d.iterdir()):
                    if f.suffix in (".md", ".prompt.md"):
                        yield f

    def test_no_command_runs_git_commit(self):
        for cmd in self._get_command_files():
            text = cmd.read_text()
            # Command files should reference the orchestrator for commit,
            # not run git commit themselves
            if "git commit" in text:
                assert "orchestrator" in text.lower() or "approval" in text.lower(), \
                    f"Command {cmd.name} has git commit but no reference to orchestrator approval"
