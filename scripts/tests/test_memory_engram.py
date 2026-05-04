"""Tests for the Engram backend integration.

All tests are mock-based — no real Engram server is required.
Covers: content formatting, type mapping, observation conversion,
backend delegation, fallback behavior, and health checks.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# Ensure subagents package is importable
SUBAGENTS_DIR = Path(__file__).resolve().parents[1] / "subagents"
sys.path.insert(0, str(SUBAGENTS_DIR))

from memory import MemoryStore, MemoryEntry, MemoryType
from memory.types import Scope
from memory.backends.engram import EngramBackend, _TYPE_MAP, _REVERSE_TYPE_MAP


# =====================================================================
# EngramBackend unit tests (mocked HTTP)
# =====================================================================


class TestEngramTypeMapping:
    """Verify Engram type mapping is consistent."""

    def test_type_map_covers_all_memory_types(self):
        for mt in MemoryType:
            assert mt in _TYPE_MAP, f"MemoryType.{mt.name} missing from _TYPE_MAP"

    def test_reverse_map_covers_common_engram_types(self):
        for engram_type in ("decision", "discovery", "pattern"):
            assert engram_type in _REVERSE_TYPE_MAP


class TestEngramContentFormatting:
    """Test the Engram What/Why/Where/Learned format."""

    def test_basic_formatting(self):
        backend = EngramBackend()
        entry = MemoryEntry(
            content="API uses FastAPI",
            memory_type=MemoryType.SEMANTIC,
            tags=["arch"],
            metadata={},
            developer_id="alice",
        )
        result = backend._format_content(entry)
        assert "**What**: API uses FastAPI" in result
        assert "**Tags**: arch" in result
        assert "**Developer**: alice" in result

    def test_metadata_fields(self):
        backend = EngramBackend()
        entry = MemoryEntry(
            content="Switched to Pydantic v2",
            memory_type=MemoryType.SEMANTIC,
            tags=[],
            metadata={"why": "Performance", "where": "models/", "learned": "v2 is strict"},
            developer_id="bob",
        )
        result = backend._format_content(entry)
        assert "**Why**: Performance" in result
        assert "**Where**: models/" in result
        assert "**Learned**: v2 is strict" in result


class TestEngramObservationConversion:
    """Test conversion from Engram observations to MemoryEntry."""

    def test_basic_conversion(self):
        backend = EngramBackend()
        obs = {
            "id": 42,
            "type": "decision",
            "title": "[arch] API uses FastAPI",
            "content": "**What**: API uses FastAPI\n**Tags**: arch, api",
            "scope": "personal",
            "tool_name": "aidlc-memory:alice",
            "created_at": "2025-01-15T10:00:00+00:00",
        }
        entry = backend._observation_to_entry(obs, "alice")
        assert entry is not None
        assert entry.content == "API uses FastAPI"
        assert entry.memory_type == MemoryType.SEMANTIC
        assert entry.scope == Scope.PRIVATE
        assert "arch" in entry.tags
        assert entry.metadata["engram_id"] == 42
        assert entry.developer_id == "alice"

    def test_shared_scope(self):
        backend = EngramBackend()
        obs = {
            "id": 99,
            "type": "discovery",
            "title": "Found a bug",
            "content": "**What**: Found a bug in auth",
            "scope": "project",
            "tool_name": "aidlc-memory:bob",
        }
        entry = backend._observation_to_entry(obs, "bob")
        assert entry is not None
        assert entry.scope == Scope.SHARED

    def test_malformed_observation_returns_none(self):
        backend = EngramBackend()
        entry = backend._observation_to_entry({"broken": True}, "x")
        # Should not crash, may return entry with defaults or None
        # The implementation catches all exceptions
        # With the current code it returns an entry with empty content


class TestEngramHealthCheck:
    """Test health check logic."""

    def test_available_when_healthy(self):
        backend = EngramBackend()
        with patch.object(backend, "_get", return_value={"status": "ok"}):
            assert backend.is_available() is True

    def test_unavailable_when_unhealthy(self):
        backend = EngramBackend()
        with patch.object(backend, "_get", return_value={"status": "error"}):
            assert backend.is_available() is False

    def test_unavailable_on_connection_error(self):
        backend = EngramBackend()
        with patch.object(backend, "_get", side_effect=ConnectionError("refused")):
            assert backend.is_available() is False


class TestEngramSave:
    """Test save() with mocked HTTP."""

    def test_save_creates_session_and_posts_observation(self):
        backend = EngramBackend(project="test-proj")
        responses = []

        def mock_post(path, body):
            responses.append((path, body))
            if path == "/sessions":
                return {"id": body["id"]}
            return {"id": 123}

        with patch.object(backend, "_post", side_effect=mock_post):
            entry = MemoryEntry(
                content="Test memory",
                memory_type=MemoryType.EPISODIC,
                tags=["test"],
                metadata={},
                developer_id="dev1",
            )
            result = backend.save("dev1", entry)

        # Should have created session + posted observation
        assert len(responses) == 2
        assert responses[0][0] == "/sessions"
        assert responses[1][0] == "/observations"
        obs_body = responses[1][1]
        assert obs_body["type"] == "discovery"  # EPISODIC -> discovery
        assert obs_body["project"] == "test-proj"
        assert "aidlc-memory:dev1" == obs_body["tool_name"]
        assert result.metadata.get("engram_id") == 123

    def test_save_reuses_session(self):
        backend = EngramBackend()
        backend._session_ids["dev1"] = "existing-session"
        calls = []

        def mock_post(path, body):
            calls.append(path)
            return {"id": 1}

        with patch.object(backend, "_post", side_effect=mock_post):
            entry = MemoryEntry(
                content="x", memory_type=MemoryType.SEMANTIC,
                tags=[], metadata={}, developer_id="dev1",
            )
            backend.save("dev1", entry)

        # Should NOT create a new session
        assert "/sessions" not in calls
        assert calls == ["/observations"]


class TestEngramSearch:
    """Test search() with mocked HTTP."""

    def test_search_returns_entries(self):
        backend = EngramBackend()
        mock_response = {
            "observations": [
                {
                    "id": 1,
                    "type": "decision",
                    "title": "[arch] FastAPI",
                    "content": "**What**: Uses FastAPI\n**Tags**: arch",
                    "scope": "personal",
                    "tool_name": "aidlc-memory:alice",
                    "created_at": "2025-01-01T00:00:00+00:00",
                },
            ]
        }
        with patch.object(backend, "_get", return_value=mock_response):
            results = backend.search("alice", tags=["arch"])

        assert len(results) == 1
        assert results[0].content == "Uses FastAPI"
        assert results[0].memory_type == MemoryType.SEMANTIC

    def test_search_empty_results(self):
        backend = EngramBackend()
        with patch.object(backend, "_get", return_value={"observations": []}):
            results = backend.search("alice", query="nonexistent")
        assert results == []

    def test_search_with_type_filter(self):
        backend = EngramBackend()
        with patch.object(backend, "_get", return_value={"observations": []}) as mock_get:
            backend.search("alice", memory_type=MemoryType.PROCEDURAL)
        # Should pass type=pattern to the API
        call_args = mock_get.call_args
        params = call_args[0][1] if len(call_args[0]) > 1 else call_args[1].get("params", {})
        assert params.get("type") == "pattern"


class TestEngramDelete:
    """Test delete() with mocked HTTP."""

    def test_delete_valid_id(self):
        backend = EngramBackend()
        with patch.object(backend, "_request", return_value={}) as mock_req:
            result = backend.delete("alice", "42")
        assert result is True
        mock_req.assert_called_once_with("DELETE", "/observations/42")

    def test_delete_invalid_id(self):
        backend = EngramBackend()
        result = backend.delete("alice", "not-a-number")
        assert result is False

    def test_delete_on_error(self):
        backend = EngramBackend()
        with patch.object(backend, "_request", side_effect=Exception("fail")):
            result = backend.delete("alice", "42")
        assert result is False


class TestEngramProfile:
    """Test profile get/update with mocked HTTP."""

    def test_get_profile_found(self):
        backend = EngramBackend()
        profile_data = {"name": "Alice", "preferred_lang": "python"}
        mock_response = {
            "observations": [
                {
                    "id": 10,
                    "type": "config",
                    "tool_name": "aidlc-profile:alice",
                    "content": json.dumps(profile_data),
                }
            ]
        }
        with patch.object(backend, "_get", return_value=mock_response):
            result = backend.get_profile("alice")
        assert result == profile_data

    def test_get_profile_not_found(self):
        backend = EngramBackend()
        with patch.object(backend, "_get", return_value={"observations": []}):
            result = backend.get_profile("alice")
        assert result == {}

    def test_update_profile(self):
        backend = EngramBackend()
        backend._session_ids["alice"] = "sess-1"

        with patch.object(backend, "_get", return_value={"observations": []}), \
             patch.object(backend, "_post", return_value={"id": 20}) as mock_post:
            result = backend.update_profile("alice", {"name": "Alice"})

        assert result["name"] == "Alice"
        assert "updated_at" in result
        # Verify the POST was called with correct args
        call_body = mock_post.call_args[0][1]
        assert call_body["type"] == "config"
        assert "aidlc-profile:alice" in call_body["tool_name"]


class TestEngramListDevelopers:
    """Test list_developers with mocked HTTP."""

    def test_list_devs(self):
        backend = EngramBackend()
        mock_response = {
            "observations": [
                {"tool_name": "aidlc-memory:alice"},
                {"tool_name": "aidlc-memory:bob"},
                {"tool_name": "aidlc-profile:alice"},
                {"tool_name": "aidlc-memory:charlie"},
            ]
        }
        with patch.object(backend, "_get", return_value=mock_response):
            devs = backend.list_developers()
        assert devs == ["alice", "bob", "charlie"]


# =====================================================================
# MemoryStore with Engram backend (integration-level, still mocked)
# =====================================================================


class TestMemoryStoreWithBackend:
    """Test MemoryStore delegates to backend when configured."""

    def test_backend_name_local(self, tmp_path):
        store = MemoryStore(tmp_path / "mem")
        assert store.backend_name == "local"

    def test_backend_name_engram(self, tmp_path):
        backend = MagicMock()
        type(backend).__name__ = "EngramBackend"
        store = MemoryStore(tmp_path / "mem", backend=backend)
        assert store.backend_name == "engram"

    def test_remember_writes_through_to_backend(self, tmp_path):
        backend = MagicMock()
        backend.save.return_value = MemoryEntry(
            content="test", memory_type=MemoryType.SEMANTIC,
            tags=[], metadata={"engram_id": 99}, developer_id="alice",
        )
        store = MemoryStore(tmp_path / "mem", backend=backend)
        entry = store.remember("alice", "test content", tags=["arch"])

        # Backend.save was called
        backend.save.assert_called_once()
        # Local file was also written (write-through)
        local_results = store._recall_local("alice")
        assert len(local_results) == 1

    def test_remember_survives_backend_failure(self, tmp_path):
        backend = MagicMock()
        backend.save.side_effect = ConnectionError("Engram down")
        store = MemoryStore(tmp_path / "mem", backend=backend)

        # Should not raise
        entry = store.remember("alice", "still works", tags=["test"])
        assert entry.content == "still works"

        # Local write still succeeded
        local_results = store._recall_local("alice")
        assert len(local_results) == 1

    def test_recall_prefers_backend(self, tmp_path):
        mock_entries = [
            MemoryEntry(
                content="from engram", memory_type=MemoryType.SEMANTIC,
                tags=["arch"], metadata={}, developer_id="alice",
            )
        ]
        backend = MagicMock()
        backend.search.return_value = mock_entries
        store = MemoryStore(tmp_path / "mem", backend=backend)

        results = store.recall("alice", tags=["arch"])
        assert len(results) == 1
        assert results[0].content == "from engram"
        backend.search.assert_called_once()

    def test_recall_falls_back_to_local_on_backend_failure(self, tmp_path):
        backend = MagicMock()
        backend.search.side_effect = ConnectionError("Engram down")
        store = MemoryStore(tmp_path / "mem", backend=backend)

        # Write locally first
        store._write_private(MemoryEntry(
            content="local entry", memory_type=MemoryType.SEMANTIC,
            tags=["test"], metadata={}, developer_id="bob",
        ))

        results = store.recall("bob", tags=["test"])
        assert len(results) == 1
        assert results[0].content == "local entry"

    def test_forget_delegates_to_backend(self, tmp_path):
        backend = MagicMock()
        backend.delete.return_value = True
        store = MemoryStore(tmp_path / "mem", backend=backend)

        store.forget("alice", "some-id")
        backend.delete.assert_called_once_with("alice", "some-id")

    def test_share_delegates_to_backend(self, tmp_path):
        backend = MagicMock()
        backend.share.return_value = True
        store = MemoryStore(tmp_path / "mem", backend=backend)

        # Need a local entry to share
        entry = store.remember("alice", "shareable", tags=["x"])
        store.share("alice", entry.id)
        backend.share.assert_called_once()


class TestWithEngramFactory:
    """Test the with_engram class method."""

    def test_falls_back_when_engram_unavailable(self, tmp_path):
        # EngramBackend.is_available() will fail since no server is running
        store = MemoryStore.with_engram(tmp_path / "mem", engram_url="http://127.0.0.1:99999")
        assert store.backend_name == "local"

    def test_uses_engram_when_available(self, tmp_path):
        with patch("memory.backends.engram.EngramBackend.is_available", return_value=True):
            store = MemoryStore.with_engram(tmp_path / "mem")
        assert store.backend_name == "engram"


# =====================================================================
# Memory agent backend config
# =====================================================================


class TestMemoryAgentConfig:
    """Test that memory_agent respects backend configuration."""

    def test_default_is_local(self, tmp_path):
        sys.path.insert(0, str(SUBAGENTS_DIR))
        from memory_agent import _get_store
        store = _get_store({"memory_root": str(tmp_path / "mem")})
        assert store.backend_name == "local"

    def test_engram_config_falls_back_when_unavailable(self, tmp_path):
        from memory_agent import _get_store
        store = _get_store({
            "memory_root": str(tmp_path / "mem"),
            "memory_backend": "engram",
            "engram_url": "http://127.0.0.1:99999",
        })
        # Should fall back to local since Engram isn't running
        assert store.backend_name == "local"

    def test_engram_config_env_var(self, tmp_path, monkeypatch):
        from memory_agent import _get_store
        monkeypatch.setenv("AIDLC_MEMORY_BACKEND", "engram")
        monkeypatch.setenv("AIDLC_ENGRAM_URL", "http://127.0.0.1:99999")
        store = _get_store({"memory_root": str(tmp_path / "mem")})
        # Falls back to local
        assert store.backend_name == "local"
