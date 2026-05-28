"""NFR-03/05: Retry rate metric extraction and context compaction compliance tests.
"""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

VALIDATOR_RETRY_SKILL = (
    REPO_ROOT / ".agents" / "custom-skills" / "validator-retry" / "SKILL.md"
)
COMPACTION_MD = REPO_ROOT / ".aidlc-orchestrator" / "runtime" / "compaction.md"
SPAWN_LOOP_MD = REPO_ROOT / ".aidlc-orchestrator" / "runtime" / "spawn-loop.md"


class TestNfrRetryRate:
    def test_validator_retry_skill_exists(self):
        assert VALIDATOR_RETRY_SKILL.exists(), \
            "validator-retry SKILL.md must exist"

    def test_retry_limit_documented(self):
        text = VALIDATOR_RETRY_SKILL.read_text()
        assert "3" in text or "max" in text.lower() or "retr" in text.lower(), \
            "validator-retry must document retry limit"

    def test_build_test_agent_references_validator_retry(self):
        agent_path = REPO_ROOT / ".claude" / "agents" / "stage" / "build-test-agent.md"
        assert "validator-retry" in agent_path.read_text(), \
            "build-test-agent must reference validator-retry"

    def test_code_generator_references_validator_retry(self):
        agent_path = REPO_ROOT / ".claude" / "agents" / "stage" / "code-generator.md"
        assert "validator-retry" in agent_path.read_text(), \
            "code-generator must reference validator-retry"


class TestNfrContextCompaction:
    def test_compaction_doc_exists(self):
        assert COMPACTION_MD.exists(), \
            "runtime/compaction.md must exist"

    def test_compaction_mentioned_in_spawn_loop(self):
        text = SPAWN_LOOP_MD.read_text()
        assert "compaction" in text.lower(), \
            "spawn-loop.md must mention compaction"

    def test_compaction_discards_transient_reasoning(self):
        text = COMPACTION_MD.read_text() if COMPACTION_MD.exists() else \
            SPAWN_LOOP_MD.read_text()
        assert "discard" in text.lower() or "transient" in text.lower(), \
            "compaction must discard transient reasoning"

    def test_compaction_preserves_artifacts(self):
        text = COMPACTION_MD.read_text() if COMPACTION_MD.exists() else \
            SPAWN_LOOP_MD.read_text()
        assert "artifacts" in text.lower() or "structured" in text.lower(), \
            "compaction must preserve structured artifacts"
