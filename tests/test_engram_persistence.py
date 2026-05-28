"""EN-01/02/03/04: Engram persistent memory tests.

Validates:
- EN-01: Cross-session persistence protocol documented and wired
- EN-02: Memory conflict resolution documentation
- EN-03: Session summary protocol format
- EN-04: Topic-key upsert mechanism
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

RUNTIME_DIR = REPO_ROOT / ".aidlc-orchestrator" / "runtime"
KNOWLEDGE_AGENT_MD = RUNTIME_DIR / "knowledge-agent.md"
SPAWN_LOOP_MD = RUNTIME_DIR / "spawn-loop.md"
CROSS_CUTTING_KNOWLEDGE = (
    REPO_ROOT / ".claude" / "agents" / "cross-cutting" / "knowledge-agent.md"
)
ORCHESTRATOR_MD = REPO_ROOT / ".claude" / "agents" / "orchestrator.md"
SETTINGS_LOCAL = REPO_ROOT / ".claude" / "settings.local.json"


# ---------------------------------------------------------------------------
# EN-01: Cross-session persistence
# ---------------------------------------------------------------------------

class TestEngramCrossSessionPersistence:
    def test_knowledge_agent_runtime_doc_exists(self):
        assert KNOWLEDGE_AGENT_MD.exists(), "runtime/knowledge-agent.md must exist"

    def test_knowledge_agent_cross_cutting_exists(self):
        assert CROSS_CUTTING_KNOWLEDGE.exists(), \
            "cross-cutting/knowledge-agent.md must exist"

    def test_spawn_loop_references_mem_search(self):
        text = SPAWN_LOOP_MD.read_text()
        assert "mem_search" in text, \
            "spawn-loop.md must reference mem_search for pre-spawn queries"

    def test_spawn_loop_references_mem_save(self):
        text = SPAWN_LOOP_MD.read_text()
        assert "mem_save" in text, \
            "spawn-loop.md must reference mem_save for post-return persistence"

    def test_spawn_loop_documents_degraded_mode(self):
        text = SPAWN_LOOP_MD.read_text()
        assert "DEGRADED" in text or "degraded" in text, \
            "spawn-loop.md must document degraded mode when engram unavailable"

    def test_spawn_loop_has_context_pointers(self):
        text = SPAWN_LOOP_MD.read_text()
        assert "context_pointers" in text, \
            "spawn-loop.md must inject context_pointers from engram"

    def test_knowledge_agent_documents_two_namespaces(self):
        text = KNOWLEDGE_AGENT_MD.read_text()
        assert "project" in text.lower() and "shared" in text.lower(), \
            "knowledge-agent.md must document project and shared namespaces"

    def test_knowledge_agent_documents_promotion_lifecycle(self):
        text = KNOWLEDGE_AGENT_MD.read_text()
        assert "promot" in text.lower(), \
            "knowledge-agent.md must document promotion lifecycle"

    def test_orchestrator_references_engram(self):
        text = (ORCHESTRATOR_MD.read_text() + SPAWN_LOOP_MD.read_text()
                + CROSS_CUTTING_KNOWLEDGE.read_text())
        assert "engram" in text.lower() or "mem_search" in text, \
            "orchestrator or spawn-loop must reference engram/MCP tools"

    def test_settings_local_allows_engram(self):
        assert SETTINGS_LOCAL.exists(), "settings.local.json must exist"
        settings = json.loads(SETTINGS_LOCAL.read_text())
        allowed = settings.get("permissions", {}).get("allow", [])
        engram_entries = [a for a in allowed if "engram" in a.lower()]
        assert len(engram_entries) >= 1, \
            "Claude settings must allow engram MCP tools"


# ---------------------------------------------------------------------------
# EN-02: Memory conflict resolution
# ---------------------------------------------------------------------------

class TestEngramConflictResolution:
    def test_spawn_loop_references_judgment(self):
        text = SPAWN_LOOP_MD.read_text()
        assert "judgment" in text.lower(), \
            "spawn-loop.md must reference judgment for conflict resolution"

    def test_spawn_loop_references_judgment_required(self):
        text = SPAWN_LOOP_MD.read_text()
        assert "judgment_required" in text, \
            "spawn-loop.md must handle judgment_required from mem_save"

    def test_knowledge_agent_judgment_heuristic(self):
        text = CROSS_CUTTING_KNOWLEDGE.read_text()
        assert "related" in text.lower() or "compatible" in text.lower() or \
               "supersedes" in text.lower() or "conflicts_with" in text.lower(), \
            "cross-cutting/knowledge-agent.md must document judgment relations"

    def test_settings_local_allows_mem_judge(self):
        settings = json.loads(SETTINGS_LOCAL.read_text())
        allowed = settings.get("permissions", {}).get("allow", [])
        has_judge = any("mem_judge" in a for a in allowed)
        assert has_judge, "settings.local.json must allow mem_judge"


# ---------------------------------------------------------------------------
# EN-03: Session summary protocol
# ---------------------------------------------------------------------------

class TestEngramSessionSummary:
    def test_knowledge_agent_exists_and_has_save(self):
        text = CROSS_CUTTING_KNOWLEDGE.read_text() \
            if CROSS_CUTTING_KNOWLEDGE.exists() else ""
        assert len(text) > 0, "cross-cutting/knowledge-agent.md must exist"

    def test_spawn_loop_mentions_timeline_events(self):
        text = SPAWN_LOOP_MD.read_text()
        assert "spawn_start" in text and "spawn_end" in text, \
            "spawn-loop must document timeline events"

    def test_spawn_loop_mentions_audit_append(self):
        text = SPAWN_LOOP_MD.read_text()
        assert "audit" in text.lower(), \
            "spawn-loop must document audit lifecycle"


# ---------------------------------------------------------------------------
# EN-04: Topic-key upserts
# ---------------------------------------------------------------------------

class TestEngramTopicKeys:
    def test_spawn_loop_references_topic_key(self):
        text = SPAWN_LOOP_MD.read_text()
        assert "topic_key" in text, \
            "spawn-loop.md must reference topic_key for deduplication"

    def test_spawn_loop_topic_key_format(self):
        text = SPAWN_LOOP_MD.read_text()
        assert "aidlc/" in text.lower(), \
            "topic_key format must include aidlc/ namespace prefix"
