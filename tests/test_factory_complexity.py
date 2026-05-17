from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "aidlc-scripts"
COMPLEXITY_PY = SCRIPTS / "factory_complexity.py"

sys.path.insert(0, str(SCRIPTS))
import factory_complexity as mod


# ── _resolve_tier ─────────────────────────────────────────────────────────────

class TestResolveTier:
    def test_single_file_trivial_is_small(self):
        tier, _ = mod._resolve_tier("Single File", "Trivial")
        assert tier == "SMALL"

    def test_single_component_simple_is_small(self):
        tier, _ = mod._resolve_tier("Single Component", "Simple")
        assert tier == "SMALL"

    def test_multiple_components_is_medium(self):
        tier, _ = mod._resolve_tier("Multiple Components", "Trivial")
        assert tier == "MEDIUM"

    def test_moderate_complexity_is_medium(self):
        tier, _ = mod._resolve_tier("Single File", "Moderate")
        assert tier == "MEDIUM"

    def test_system_wide_is_large(self):
        tier, _ = mod._resolve_tier("System-wide", "Simple")
        assert tier == "LARGE"

    def test_cross_system_is_large(self):
        tier, _ = mod._resolve_tier("Cross-system", "Trivial")
        assert tier == "LARGE"

    def test_complex_complexity_is_large(self):
        tier, _ = mod._resolve_tier("Single File", "Complex")
        assert tier == "LARGE"

    def test_tiebreak_higher_wins_large_vs_medium(self):
        # scope=Multiple Components→MEDIUM, complexity=Complex→LARGE → LARGE
        tier, _ = mod._resolve_tier("Multiple Components", "Complex")
        assert tier == "LARGE"

    def test_tiebreak_higher_wins_medium_vs_small(self):
        # scope=Single File→SMALL, complexity=Moderate→MEDIUM → MEDIUM
        tier, _ = mod._resolve_tier("Single File", "Moderate")
        assert tier == "MEDIUM"

    def test_none_scope_defaults_to_medium(self):
        # None scope → MEDIUM default, Simple → SMALL; tie-break takes higher → MEDIUM
        tier, _ = mod._resolve_tier(None, "Simple")
        assert tier == "MEDIUM"

    def test_unknown_scope_defaults_to_medium(self):
        tier, _ = mod._resolve_tier("Galaxy-wide", "Trivial")
        assert tier == "MEDIUM"

    def test_unknown_complexity_defaults_to_medium(self):
        tier, _ = mod._resolve_tier("Single File", "Insane")
        assert tier == "MEDIUM"

    def test_both_none_returns_medium(self):
        tier, _ = mod._resolve_tier(None, None)
        assert tier == "MEDIUM"

    def test_rationale_is_non_empty(self):
        _, rationale = mod._resolve_tier("System-wide", "Complex")
        assert len(rationale) > 0


# ── routing table ─────────────────────────────────────────────────────────────

class TestRoutingTable:
    def test_small_reviewer_pool(self):
        assert mod._ROUTING["SMALL"]["reviewer_pool"] == ["reviewer-code"]

    def test_small_skips_story_and_decomposer(self):
        assert "story-writer" in mod._ROUTING["SMALL"]["skip_stages"]
        assert "unit-decomposer" in mod._ROUTING["SMALL"]["skip_stages"]

    def test_large_has_all_reviewers(self):
        pool = mod._ROUTING["LARGE"]["reviewer_pool"]
        assert "reviewer-security" in pool
        assert "reviewer-performance" in pool

    def test_token_caps_increase_by_tier(self):
        assert mod._ROUTING["SMALL"]["tokens_max"] < mod._ROUTING["MEDIUM"]["tokens_max"]
        assert mod._ROUTING["MEDIUM"]["tokens_max"] < mod._ROUTING["LARGE"]["tokens_max"]


# ── cmd_assess via CLI ────────────────────────────────────────────────────────

def _write_handoff(run_dir: Path, scope: str, complexity: str) -> None:
    handoffs = run_dir / "handoffs"
    handoffs.mkdir(parents=True, exist_ok=True)
    (handoffs / "requirements-analyst.output.yaml").write_text(
        f"request_classification:\n  scope: {scope}\n  complexity: {complexity}\n",
        encoding="utf-8",
    )


def _run_cli(*args, env_overrides=None) -> subprocess.CompletedProcess:
    import os
    env = {**os.environ, **(env_overrides or {})}
    return subprocess.run(
        [sys.executable, str(COMPLEXITY_PY), *args],
        capture_output=True, text=True, env=env,
    )


class TestCmdAssess:
    def test_small_tier_output(self, tmp_path):
        run_id = "test-small-run"
        runs_root = tmp_path / ".aidlc-orchestrator" / "runs"
        _write_handoff(runs_root / run_id, "Single File", "Trivial")
        r = _run_cli(run_id, env_overrides={"AIDLC_ROOT": str(tmp_path)})
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert data["tier"] == "SMALL"

    def test_large_tier_output(self, tmp_path):
        run_id = "test-large-run"
        runs_root = tmp_path / ".aidlc-orchestrator" / "runs"
        _write_handoff(runs_root / run_id, "System-wide", "Complex")
        r = _run_cli(run_id, env_overrides={"AIDLC_ROOT": str(tmp_path)})
        assert r.returncode == 0, r.stderr
        data = json.loads(r.stdout)
        assert data["tier"] == "LARGE"
        assert "skip_stages" in data
        assert "reviewer_pool" in data
        assert "tokens_max" in data

    def test_missing_handoff_exits_1(self, tmp_path):
        r = _run_cli("nonexistent-run", env_overrides={"AIDLC_ROOT": str(tmp_path)})
        assert r.returncode == 1

    def test_missing_classification_exits_1(self, tmp_path):
        run_id = "bad-run"
        runs_root = tmp_path / ".aidlc-orchestrator" / "runs"
        handoffs = runs_root / run_id / "handoffs"
        handoffs.mkdir(parents=True, exist_ok=True)
        (handoffs / "requirements-analyst.output.yaml").write_text("status: complete\n")
        r = _run_cli(run_id, env_overrides={"AIDLC_ROOT": str(tmp_path)})
        assert r.returncode == 1

    def test_apply_writes_budget_yaml(self, tmp_path):
        run_id = "apply-run"
        runs_root = tmp_path / ".aidlc-orchestrator" / "runs"
        run_dir = runs_root / run_id
        _write_handoff(run_dir, "Single File", "Trivial")
        budget = run_dir / "budget.yaml"
        budget.write_text("budget: {}\n")
        r = _run_cli(run_id, "--apply", env_overrides={"AIDLC_ROOT": str(tmp_path)})
        assert r.returncode == 0
        import yaml
        state = yaml.safe_load(budget.read_text())
        assert state["complexity_tier"] == "SMALL"
        assert state["budget"]["tokens_max"] == mod._ROUTING["SMALL"]["tokens_max"]

    def test_apply_without_budget_yaml_does_not_crash(self, tmp_path):
        run_id = "no-budget-run"
        runs_root = tmp_path / ".aidlc-orchestrator" / "runs"
        _write_handoff(runs_root / run_id, "Single File", "Simple")
        r = _run_cli(run_id, "--apply", env_overrides={"AIDLC_ROOT": str(tmp_path)})
        assert r.returncode == 0


# ── AIDLC_ROOT env override wiring ───────────────────────────────────────────

class TestAidlcRootOverride:
    def test_env_var_redirects_runs_root(self, tmp_path):
        run_id = "env-test"
        _write_handoff(
            tmp_path / ".aidlc-orchestrator" / "runs" / run_id,
            "Multiple Components", "Moderate",
        )
        r = _run_cli(run_id, env_overrides={"AIDLC_ROOT": str(tmp_path)})
        assert r.returncode == 0
        data = json.loads(r.stdout)
        assert data["tier"] == "MEDIUM"
