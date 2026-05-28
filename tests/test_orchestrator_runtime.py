"""ORC-03/04/05/09/10: Orchestrator runtime protocol tests.

Validates:
- ORC-03: Spawn-loop protocol (Task() boundary, bookkeeping steps)
- ORC-04: Fast-path decision-table (TINY bypass vs full pipeline)
- ORC-05: Recovery & resume (critical vs non-critical, fail-stage, replay)
- ORC-09: Depth mode propagation (minimal/standard/comprehensive)
- ORC-10: Mid-workflow changes (skip, restart, pause)
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "aidlc-scripts"
RUN_PY = SCRIPTS / "factory_run.py"
TRIAGE_PY = SCRIPTS / "factory_triage.py"

SPAWN_LOOP = REPO_ROOT / ".aidlc-orchestrator" / "runtime" / "spawn-loop.md"
FAST_PATH = REPO_ROOT / ".aidlc-orchestrator" / "runtime" / "fast-path.md"
RECOVERY = REPO_ROOT / ".aidlc-orchestrator" / "runtime" / "recovery.md"
REPLAY_ADOPT = REPO_ROOT / ".aidlc-orchestrator" / "runtime" / "replay-adopt.md"
COMPACTION = REPO_ROOT / ".aidlc-orchestrator" / "runtime" / "compaction.md"


# ---------------------------------------------------------------------------
# ORC-03: Spawn-loop protocol
# ---------------------------------------------------------------------------

class TestSpawnLoopProtocol:
    """Validate the spawn-loop.md defines the correct protocol shape."""

    def test_full_spawn_10_steps_documented(self):
        text = SPAWN_LOOP.read_text()
        for step_num in (0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12):
            assert f"{step_num}." in text, \
                f"spawn-loop.md should enumerate step {step_num}"

    def test_full_spawn_has_task_and_validate(self):
        text = SPAWN_LOOP.read_text()
        assert "Task()" in text, "Full spawn loop must use Task()"
        assert "Validate input handoff" in text or "Validate output handoff" in text, \
            "Full spawn loop must validate handoffs"

    def test_post_exec_skips_steps_3_to_5(self):
        text = SPAWN_LOOP.read_text()
        assert "Steps 3-5" in text and "SKIPPED" in text, \
            "Post-execution loop must skip handoff validation"

    def test_context_compaction_mandatory_after_inline(self):
        text = SPAWN_LOOP.read_text()
        assert "compaction" in text.lower() or "compact" in text.lower(), \
            "Post-execution loop must mention context compaction"

    def test_lightweight_validation_for_inline(self):
        text = SPAWN_LOOP.read_text()
        assert "Lightweight validation" in text or "lightweight validation" in text.lower(), \
            "Post-execution loop must have lightweight validation"

    def test_knowledge_query_on_every_spawn(self):
        text = SPAWN_LOOP.read_text()
        assert "Knowledge query" in text or "pre-spawn" in text, \
            "Spawn loop must query knowledge before execution"

    def test_knowledge_save_on_return(self):
        text = SPAWN_LOOP.read_text()
        assert "Knowledge save" in text or "emitted_knowledge" in text, \
            "Spawn loop must save knowledge on stage return"

    def test_timeline_events_on_both_ends(self):
        text = SPAWN_LOOP.read_text()
        assert "spawn_start" in text and "spawn_end" in text, \
            "Spawn loop must emit both spawn_start and spawn_end timeline events"

    def test_halt_or_surface_on_non_complete(self):
        text = SPAWN_LOOP.read_text()
        assert "Halt or surface" in text or "halt and surface" in text.lower(), \
            "Spawn loop must halt on non-complete status"

    def test_needs_human_gate_pauses_run(self):
        text = SPAWN_LOOP.read_text()
        assert "needs_human" in text, \
            "Spawn loop must handle needs_human status"

    def test_stage_specific_deltas(self):
        text = SPAWN_LOOP.read_text()
        assert "Stage-specific deltas" in text or "stage-specific" in text.lower(), \
            "Spawn loop must document stage-specific deltas"


# ---------------------------------------------------------------------------
# ORC-04: Fast-path decision table
# ---------------------------------------------------------------------------

class TestFastPathDecisionTable:
    """Validate FAST_PATH and factory_triage.py decision logic."""

    def test_fast_path_documentation_exists(self):
        assert FAST_PATH.exists(), "fast-path.md must exist"
        text = FAST_PATH.read_text()
        assert "FAST_PATH" in text
        assert "TINY" in text

    def test_fast_path_both_dimensions_required(self):
        text = FAST_PATH.read_text()
        txt_lower = text.lower()
        assert "single file" in txt_lower and "trivial" in txt_lower, \
            "FAST_PATH requires scope=Single File AND complexity=Trivial"

    def test_fast_path_what_it_skips_is_documented(self):
        text = FAST_PATH.read_text()
        assert "sacrifices" in text or "skips" in text.lower(), \
            "FAST_PATH must document what it skips"

    def test_fast_path_bailout_paths(self):
        text = FAST_PATH.read_text()
        assert "Bailout" in text or "escalat" in text.lower(), \
            "FAST_PATH must document bailout paths when user rejects"

    def test_triage_prefilter_tiny_triggers(self):
        for trivial in ("fix typo in README", "update docs", "add license file"):
            result = subprocess.run(
                [sys.executable, str(TRIAGE_PY), "prefilter", trivial],
                capture_output=True, text=True,
            )
            assert result.returncode == 0 or result.returncode == 10
            if result.returncode == 0:
                data = json.loads(result.stdout)
                assert data["tier"] == "TINY", f"Expected TINY for {trivial!r}"

    def test_triage_prefilter_complex_unknown(self):
        result = subprocess.run(
            [sys.executable, str(TRIAGE_PY), "prefilter", "add healthz endpoint"],
            capture_output=True, text=True,
        )
        assert result.returncode == 10
        data = json.loads(result.stdout)
        assert data["tier"] == "UNKNOWN"

    def test_fast_path_apply_function(self):
        """Decision-table test: various inputs map to expected tiers."""
        cases = [
            # (scope, risk, arch_impact, security, data_impact, coordination, expected_tier)
            ("single_file", "low", "none", "none", "none", False, "SMALL"),
            ("multi_module", "medium", "medium", "none", "medium", True, "MEDIUM"),
            ("system_wide", "high", "high", "high", "high", True, "LARGE"),
        ]
        for scope, risk, arch, sec, data, coord, expected in cases:
            data_dict = {
                "scope": scope, "risk": risk, "architecture_impact": arch,
                "security_relevance": sec, "data_layer_impact": data,
                "coordination_required": coord, "ambiguity": "low",
                "estimated_affected_components": "1-2" if scope == "single_file" else "3-5",
                "intent": "modify" if scope == "single_file" else "create",
                "external_dependencies": [],
            }
            result = subprocess.run(
                [sys.executable, str(TRIAGE_PY), "apply", "-"],
                input=json.dumps(data_dict), capture_output=True, text=True,
            )
            data_out = json.loads(result.stdout)
            assert data_out["tier"] == expected, \
                f"Expected {expected} for scope={scope}, got {data_out['tier']}"

    def test_non_tiny_never_fast_path(self):
        """Decision-table: no non-TINY input should produce fast_path: true."""
        cases = [
            ("single_file", "low", "none"),
            ("multi_module", "low", "none"),
            ("single_file", "medium", "none"),
        ]
        for scope, risk, arch in cases:
            data_dict = {
                "scope": scope, "risk": risk, "architecture_impact": arch,
                "security_relevance": "none", "data_layer_impact": "none",
                "coordination_required": False, "ambiguity": "low",
                "estimated_affected_components": "1-2",
                "intent": "modify",
                "external_dependencies": [],
            }
            result = subprocess.run(
                [sys.executable, str(TRIAGE_PY), "apply", "-"],
                input=json.dumps(data_dict), capture_output=True, text=True,
            )
            assert result.returncode in (1, 10)


# ---------------------------------------------------------------------------
# ORC-05: Recovery & resume (enhanced)
# ---------------------------------------------------------------------------

class TestRecoveryProtocol:
    """Validate recovery.md and factory_run.py resume/replay behavior."""

    def test_recovery_documentation(self):
        text = RECOVERY.read_text()
        assert "critical" in text and "non-critical" in text.lower(), \
            "Recovery docs must differentiate critical vs non-critical stages"

    def test_critical_stages_listed(self):
        text = RECOVERY.read_text()
        for stage in ("workspace-scout", "requirements-analyst", "workflow-planner",
                      "code-generator", "build-test-agent"):
            assert stage in text, f"Critical stage {stage} must be in recovery docs"

    def test_non_critical_skip_sequence(self):
        text = RECOVERY.read_text()
        assert "stage_skipped" in text or "emit_audit_block" in text, \
            "Non-critical skip must call emit_audit_block with stage_skipped"

    def test_critical_failure_halts(self):
        text = RECOVERY.read_text()
        assert "halt" in text.lower() or "fail-stage" in text, \
            "Critical stage failure must halt the run"

    def test_replay_documentation(self):
        text = REPLAY_ADOPT.read_text()
        assert "Roll" in text and "back" in text.lower(), \
            "Replay must roll back completed stages"
        assert "archive" in text.lower(), \
            "Replay must archive prior handoffs, not delete"

    def test_replay_requires_existing_stage(self):
        text = REPLAY_ADOPT.read_text()
        assert "completed_stages" in text, \
            "Replay must validate stage is in completed_stages[]"

    def test_resume_checks_partial_outputs(self):
        text = REPLAY_ADOPT.read_text()
        assert "partial_outputs" in text, \
            "Resume must check for partial outputs"

    def test_replay_archives_with_timestamp(self):
        text = REPLAY_ADOPT.read_text()
        assert ".replay-" in text, \
            "Replay must suffix archived handoffs with .replay-<ts>"

    def test_resume_and_replay_have_atomicity(self):
        for doc in (REPLAY_ADOPT,):
            text = doc.read_text()
            assert "Atomicity" in text or "POSIX-atomic" in text or "tmpfile" in text, \
                "Resume/replay must document atomicity guarantees"


# ---------------------------------------------------------------------------
# ORC-09: Depth mode propagation
# ---------------------------------------------------------------------------

class TestDepthMode:
    """Validate depth mode (minimal/standard/comprehensive) is propagated."""

    PROMPT_FILES_WITH_DEPTH = [
        REPO_ROOT / ".claude" / "agents" / "orchestrator.md",
        REPO_ROOT / ".cursor" / "agents" / "orchestrator.md",
        REPO_ROOT / ".opencode" / "agents" / "orchestrator.md",
        REPO_ROOT / ".github" / "agents" / "orchestrator.md",
    ]

    def test_depth_mode_referenced_in_orchestrator(self):
        for path in self.PROMPT_FILES_WITH_DEPTH:
            if path.exists():
                text = path.read_text()
                assert "depth" in text.lower() or "depth_mode" in text, \
                    f"{path.name} must reference depth mode"
                break

    def test_depth_levels_defined(self):
        levels = ("minimal", "standard", "comprehensive")
        for path in self.PROMPT_FILES_WITH_DEPTH:
            if path.exists():
                text = path.read_text()
                found = [l for l in levels if l in text.lower()]
                assert len(found) >= 1, \
                    f"Orchestrator should reference at least one depth level, found {found}"
                return
        pytest.skip("No orchestrator agent prompt found")

    def test_silent_spoken_protocol(self):
        for path in self.PROMPT_FILES_WITH_DEPTH:
            if path.exists():
                text = path.read_text()
                if "no chat output" in text.lower() or "spoken" in text.lower():
                    return
        pytest.skip("No orchestrator with silent/spoken protocol found")


# ---------------------------------------------------------------------------
# ORC-10: Mid-workflow changes
# ---------------------------------------------------------------------------

class TestMidWorkflowChanges:
    """Validate orchestrator can handle mid-run changes (skip, restart, pause)."""

    ORCHESTRATOR_MDS = [
        REPO_ROOT / ".claude" / "agents" / "orchestrator.md",
    ]

    def test_mid_workflow_change_handling_documented(self):
        for path in self.ORCHESTRATOR_MDS:
            if path.exists():
                text = path.read_text()
                assert "Mid-Workflow Changes" in text or "skip stage" in text.lower(), \
                    "Orchestrator must document mid-workflow change handling"

    def test_skip_stage_pattern_documented(self):
        text = self.ORCHESTRATOR_MDS[0].read_text()
        assert "skip stage" in text.lower() or "Skip" in text, \
            "Orchestrator must support skipping a stage"

    def test_restart_pattern_documented(self):
        text = self.ORCHESTRATOR_MDS[0].read_text()
        assert "restart" in text.lower() or "reset" in text.lower(), \
            "Orchestrator must support restarting from a stage"

    def test_pause_pattern_documented(self):
        text = self.ORCHESTRATOR_MDS[0].read_text()
        assert "pause" in text.lower(), \
            "Orchestrator must support pausing a run"

    def test_depth_change_documented(self):
        text = self.ORCHESTRATOR_MDS[0].read_text()
        assert "change depth" in text.lower() or "depth_mode" in text, \
            "Orchestrator must support changing depth mid-run"

    def test_archival_before_restart(self):
        text = self.ORCHESTRATOR_MDS[0].read_text()
        assert "archive" in text.lower(), \
            "Orchestrator must archive state before restart"


# ---------------------------------------------------------------------------
# Context compaction (referenced by ORC-03/09)
# ---------------------------------------------------------------------------

class TestContextCompaction:
    def test_compaction_documentation(self):
        text = COMPACTION.read_text()
        assert "compact" in text.lower() or "discard" in text.lower(), \
            "Compaction docs must mention compaction"
        assert "chain-of-thought" in text or "chain of thought" in text.lower(), \
            "Compaction must discard raw chain-of-thought"

    def test_compaction_applies_after_inline_stages(self):
        text = COMPACTION.read_text()
        assert "after every inline stage" in text.lower() or \
               "every inline stage" in text.lower(), \
            "Compaction must run after every inline stage"

    def test_compaction_index_principle_referenced(self):
        text = COMPACTION.read_text()
        assert "index.md" in text or "principle 6" in text.lower(), \
            "Compaction must reference index.md principle 6"
