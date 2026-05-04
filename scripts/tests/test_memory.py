"""Tests for the AIDLC persistent memory system.

Covers: store CRUD, developer isolation, concurrent writes, TTL expiry,
shared/private scoping, memory agent subagent interface, and compaction.
"""
from __future__ import annotations

import json
import runpy
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

# Ensure subagents package is importable
SUBAGENTS_DIR = Path(__file__).resolve().parents[1] / "subagents"
sys.path.insert(0, str(SUBAGENTS_DIR))

from memory import MemoryStore, MemoryEntry, MemoryType
from memory.types import Scope

MEMORY_AGENT_PATH = SUBAGENTS_DIR / "memory_agent.py"


# =====================================================================
# Core store tests
# =====================================================================

class TestMemoryStore:
    def test_remember_and_recall(self, tmp_path):
        store = MemoryStore(tmp_path / "mem")
        store.remember("alice", "FastAPI is used for the API layer", tags=["arch", "api"])
        store.remember("alice", "Postgres is the primary DB", tags=["arch", "db"])

        results = store.recall("alice")
        assert len(results) == 2
        contents = {e.content for e in results}
        assert "FastAPI is used for the API layer" in contents

    def test_recall_by_tags(self, tmp_path):
        store = MemoryStore(tmp_path / "mem")
        store.remember("bob", "Uses React 18", tags=["frontend"])
        store.remember("bob", "Uses FastAPI", tags=["backend"])

        results = store.recall("bob", tags=["frontend"])
        assert len(results) == 1
        assert results[0].content == "Uses React 18"

    def test_recall_by_query(self, tmp_path):
        store = MemoryStore(tmp_path / "mem")
        store.remember("carol", "The auth system uses JWT tokens", tags=["auth"])
        store.remember("carol", "Deploy to AWS ECS", tags=["infra"])

        results = store.recall("carol", query="JWT")
        assert len(results) == 1
        assert "JWT" in results[0].content

    def test_recall_by_memory_type(self, tmp_path):
        store = MemoryStore(tmp_path / "mem")
        store.remember("dan", "Sprint started", memory_type=MemoryType.EPISODIC, tags=["sprint"])
        store.remember("dan", "Architecture uses CQRS", memory_type=MemoryType.SEMANTIC, tags=["arch"])

        results = store.recall("dan", memory_type=MemoryType.EPISODIC)
        assert len(results) == 1
        assert results[0].memory_type == MemoryType.EPISODIC

    def test_episodic_append_only(self, tmp_path):
        store = MemoryStore(tmp_path / "mem")
        for i in range(5):
            store.remember("eve", f"Event {i}", memory_type=MemoryType.EPISODIC, tags=["log"])

        ep_file = tmp_path / "mem" / "developers" / "eve" / "episodic.jsonl"
        assert ep_file.exists()
        lines = ep_file.read_text().strip().splitlines()
        assert len(lines) == 5

    def test_forget(self, tmp_path):
        store = MemoryStore(tmp_path / "mem")
        entry = store.remember("frank", "Temporary note", tags=["temp"])
        assert store.forget("frank", entry.id)
        results = store.recall("frank")
        assert len(results) == 0

    def test_forget_nonexistent(self, tmp_path):
        store = MemoryStore(tmp_path / "mem")
        assert not store.forget("ghost", "nonexistent-id")

    def test_ttl_expiry(self, tmp_path):
        store = MemoryStore(tmp_path / "mem")
        entry = store.remember("grace", "Ephemeral", tags=["tmp"], ttl_hours=0.0001)
        # Force expiry by waiting briefly (TTL is ~0.36 seconds)
        time.sleep(0.5)
        results = store.recall("grace", include_expired=False)
        assert len(results) == 0

        # With include_expired=True
        results_all = store.recall("grace", include_expired=True)
        assert len(results_all) == 1

    def test_compact(self, tmp_path):
        store = MemoryStore(tmp_path / "mem")
        store.remember("hank", "Keep me", tags=["keep"])
        store.remember("hank", "Expire me", tags=["tmp"], ttl_hours=0.0001)
        time.sleep(0.5)
        removed = store.compact("hank")
        assert removed == 1
        results = store.recall("hank")
        assert len(results) == 1
        assert results[0].content == "Keep me"

    def test_recall_context_string(self, tmp_path):
        store = MemoryStore(tmp_path / "mem")
        store.remember("ivan", "API runs on port 8080", tags=["api"])
        ctx = store.recall_context("ivan")
        assert "ivan" in ctx
        assert "8080" in ctx
        assert "[semantic]" in ctx

    def test_recall_context_empty(self, tmp_path):
        store = MemoryStore(tmp_path / "mem")
        ctx = store.recall_context("nobody")
        assert ctx == ""


# =====================================================================
# Developer isolation
# =====================================================================

class TestDeveloperIsolation:
    def test_private_entries_isolated(self, tmp_path):
        store = MemoryStore(tmp_path / "mem")
        store.remember("alice", "Alice's secret", tags=["private"])
        store.remember("bob", "Bob's secret", tags=["private"])

        alice_results = store.recall("alice", include_shared=False)
        bob_results = store.recall("bob", include_shared=False)
        assert len(alice_results) == 1
        assert alice_results[0].content == "Alice's secret"
        assert len(bob_results) == 1
        assert bob_results[0].content == "Bob's secret"

    def test_shared_entries_visible_to_all(self, tmp_path):
        store = MemoryStore(tmp_path / "mem")
        store.remember("alice", "Shared architecture decision",
                       scope=Scope.SHARED, tags=["arch"])

        alice_r = store.recall("alice", include_shared=True)
        bob_r = store.recall("bob", include_shared=True)
        assert any("Shared architecture" in e.content for e in alice_r)
        assert any("Shared architecture" in e.content for e in bob_r)

    def test_share_promotion(self, tmp_path):
        store = MemoryStore(tmp_path / "mem")
        entry = store.remember("carol", "Was private, now sharing", tags=["upgrade"])
        assert store.share("carol", entry.id)

        # Carol's private should no longer have it
        private_only = store.recall("carol", include_shared=False)
        assert not any(e.id == entry.id for e in private_only)

        # But shared should
        dan_results = store.recall("dan", include_shared=True)
        assert any("now sharing" in e.content for e in dan_results)

    def test_list_developers(self, tmp_path):
        store = MemoryStore(tmp_path / "mem")
        store.remember("alice", "note")
        store.remember("bob", "note")
        store.remember("carol", "note")
        devs = store.list_developers()
        assert devs == ["alice", "bob", "carol"]

    def test_profile_crud(self, tmp_path):
        store = MemoryStore(tmp_path / "mem")
        assert store.get_profile("alice") == {}
        store.update_profile("alice", {"editor": "vscode", "lang": "es"})
        profile = store.get_profile("alice")
        assert profile["editor"] == "vscode"
        assert profile["lang"] == "es"
        assert "updated_at" in profile

        store.update_profile("alice", {"lang": "en"})
        profile2 = store.get_profile("alice")
        assert profile2["lang"] == "en"
        assert profile2["editor"] == "vscode"  # preserved


# =====================================================================
# Concurrency
# =====================================================================

class TestConcurrency:
    def test_concurrent_writes_same_developer(self, tmp_path):
        """Multiple threads writing to the same developer's memory simultaneously."""
        store = MemoryStore(tmp_path / "mem")
        n = 30

        def _write(i: int):
            store.remember("shared-dev", f"Concurrent entry {i}",
                           memory_type=MemoryType.EPISODIC, tags=["concurrent"])
            return i

        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(_write, i) for i in range(n)]
            results = [f.result() for f in as_completed(futures)]

        assert len(results) == n
        entries = store.recall("shared-dev", memory_type=MemoryType.EPISODIC, limit=100)
        assert len(entries) == n

    def test_concurrent_writes_different_developers(self, tmp_path):
        """Multiple developers writing simultaneously — no interference."""
        store = MemoryStore(tmp_path / "mem")
        devs = [f"dev-{i}" for i in range(10)]

        def _write(dev_id: str):
            for j in range(5):
                store.remember(dev_id, f"Note {j} from {dev_id}", tags=["multi"])
            return dev_id

        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = [pool.submit(_write, d) for d in devs]
            [f.result() for f in as_completed(futures)]

        for d in devs:
            entries = store.recall(d, include_shared=False, limit=100)
            assert len(entries) == 5, f"{d} should have 5 entries, got {len(entries)}"

    def test_concurrent_read_write(self, tmp_path):
        """Reads and writes happening concurrently don't corrupt data."""
        store = MemoryStore(tmp_path / "mem")
        # Seed some data
        for i in range(10):
            store.remember("rw-dev", f"Seed {i}", tags=["seed"])

        errors = []

        def _writer(i: int):
            try:
                store.remember("rw-dev", f"Write {i}", tags=["concurrent"])
            except Exception as e:
                errors.append(e)

        def _reader():
            try:
                store.recall("rw-dev", limit=100)
            except Exception as e:
                errors.append(e)

        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = []
            for i in range(20):
                futs.append(pool.submit(_writer, i))
                futs.append(pool.submit(_reader))
            [f.result() for f in as_completed(futs)]

        assert not errors, f"Concurrent errors: {errors}"


# =====================================================================
# Memory agent (subagent interface)
# =====================================================================

class TestMemoryAgent:
    def _run_agent(self, ctx: dict) -> dict:
        mod = runpy.run_path(str(MEMORY_AGENT_PATH))
        return mod["run"](ctx)

    def test_remember_action(self, tmp_path):
        res = self._run_agent({
            "developer_id": "test-dev",
            "action": "remember",
            "content": "Testing the memory agent",
            "tags": ["test"],
            "memory_root": str(tmp_path / "mem"),
        })
        assert res["status"] == "ok"
        assert res["entry_id"]

    def test_recall_action(self, tmp_path):
        root = str(tmp_path / "mem")
        self._run_agent({
            "developer_id": "test-dev",
            "action": "remember",
            "content": "Entry for recall test",
            "tags": ["recall-test"],
            "memory_root": root,
        })
        res = self._run_agent({
            "developer_id": "test-dev",
            "action": "recall",
            "tags": ["recall-test"],
            "memory_root": root,
        })
        assert res["status"] == "ok"
        assert res["count"] == 1

    def test_context_action(self, tmp_path):
        root = str(tmp_path / "mem")
        self._run_agent({
            "developer_id": "ctx-dev",
            "action": "remember",
            "content": "Important context fact",
            "tags": ["ctx"],
            "memory_root": root,
        })
        res = self._run_agent({
            "developer_id": "ctx-dev",
            "action": "context",
            "tags": ["ctx"],
            "memory_root": root,
        })
        assert res["status"] == "ok"
        assert "Important context fact" in res["context_text"]

    def test_forget_action(self, tmp_path):
        root = str(tmp_path / "mem")
        r1 = self._run_agent({
            "developer_id": "f-dev",
            "action": "remember",
            "content": "To be forgotten",
            "memory_root": root,
        })
        r2 = self._run_agent({
            "developer_id": "f-dev",
            "action": "forget",
            "entry_id": r1["entry_id"],
            "memory_root": root,
        })
        assert r2["status"] == "ok"
        assert r2["removed"] is True

    def test_profile_action(self, tmp_path):
        root = str(tmp_path / "mem")
        res = self._run_agent({
            "developer_id": "p-dev",
            "action": "profile",
            "profile_updates": {"editor": "cursor", "team": "platform"},
            "memory_root": root,
        })
        assert res["status"] == "ok"
        assert res["profile"]["editor"] == "cursor"

    def test_list_devs_action(self, tmp_path):
        root = str(tmp_path / "mem")
        for d in ["alpha", "beta"]:
            self._run_agent({
                "developer_id": d,
                "action": "remember",
                "content": f"note from {d}",
                "memory_root": root,
            })
        res = self._run_agent({
            "developer_id": "alpha",
            "action": "list_devs",
            "memory_root": root,
        })
        assert res["status"] == "ok"
        assert "alpha" in res["developers"]
        assert "beta" in res["developers"]

    def test_missing_developer_id(self, tmp_path):
        res = self._run_agent({"action": "remember", "content": "x", "memory_root": str(tmp_path)})
        assert res["status"] == "error"
        assert "developer_id" in res["error"]

    def test_missing_action(self, tmp_path):
        res = self._run_agent({"developer_id": "x", "memory_root": str(tmp_path)})
        assert res["status"] == "error"
        assert "action" in res["error"]

    def test_unknown_action(self, tmp_path):
        res = self._run_agent({
            "developer_id": "x",
            "action": "explode",
            "memory_root": str(tmp_path),
        })
        assert res["status"] == "error"
        assert "unknown action" in res["error"]
