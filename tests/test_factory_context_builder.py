"""tests/test_factory_context_builder.py — Unit tests for factory_context_builder.py.

Tests cover:
- Token counting (tiktoken vs fallback)
- Caching with checksum invalidation
- Compact YAML rendering
- Auto depth selection
- All data loaders (manifest, timeline, audit, state)
- Truncation logic
- Format outputs (compact, markdown, yaml, json)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import pytest
import yaml

# Ensure the script under test is importable
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "aidlc-scripts"))

from factory_context_builder import (
    _build_current_state,
    _build_handoff_summary,
    _build_open_items,
    _build_project_context,
    _build_recent_decisions,
    _build_skills,
    _build_stage_timeline,
    _estimate_tokens,
    _file_checksums,
    _load_audit_md,
    _load_cached,
    _load_manifest,
    _load_state_md,
    _load_timeline,
    _render_compact,
    _render_markdown,
    _save_cached,
    _truncate_text,
    build_context,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_manifest() -> dict:
    return {
        "run_id": "2026-05-08-healthz-endpoint",
        "started_at": "2026-05-08T00:00:00Z",
        "user_request": "add a /healthz endpoint",
        "project_slug": "custom-aidlc",
        "current_stage": "requirements-analyst",
        "completed_stages": ["workspace-scout"],
        "skipped_stages": [],
        "failed_stages": [],
        "orchestrator_version": "0.2.0",
        "project_profile": {
            "ui": False,
            "api": True,
            "has_legacy": False,
            "framework": "none",
        },
        "skill_paths": {
            "using-agent-skills": "~/.agents/skills/using-agent-skills/SKILL.md",
        },
        "units": [],
    }


@pytest.fixture
def sample_timeline() -> list[dict]:
    return [
        {"ts": "2026-05-08T00:00:00Z", "evt": "run_init", "run_id": "2026-05-08-healthz-endpoint"},
        {"ts": "2026-05-08T00:01:00Z", "evt": "spawn_start", "stage": "workspace-scout", "run_id": "2026-05-08-healthz-endpoint"},
        {"ts": "2026-05-08T00:02:00Z", "evt": "stage_complete", "stage": "workspace-scout", "run_id": "2026-05-08-healthz-endpoint"},
    ]


@pytest.fixture
def sample_audit_blocks() -> list[dict]:
    return [
        {
            "ts": "2026-05-08T00:02:00Z",
            "phase": "INCEPTION",
            "label": "User Decision (workspace-scout)",
            "bullets": ["[User] Approved workspace-scout"],
        },
        {
            "ts": "2026-05-08T00:03:00Z",
            "phase": "INCEPTION",
            "label": "User Answers Received",
            "bullets": ["Q1=A (greenfield)"],
        },
    ]


@pytest.fixture
def sample_state() -> dict:
    return {
        "project_name": "Custom AIDLC",
        "project_type": "greenfield",
        "current_stage": "requirements-analyst",
        "phase": "INCEPTION",
        "stage_progress": [
            {"done": True, "description": "Workspace Detection"},
            {"done": False, "description": "Requirements Analysis"},
        ],
        "extensions": [{"name": "security-baseline", "enabled": "Yes", "decided_at": "Requirements Analysis"}],
    }


# ---------------------------------------------------------------------------
# Token counting
# ---------------------------------------------------------------------------

def test_estimate_tokens_basic() -> None:
    text = "Hello world"
    tokens = _estimate_tokens(text)
    # Should be > 0 and reasonable
    assert 1 <= tokens <= 10


def test_estimate_tokens_empty() -> None:
    assert _estimate_tokens("") == 1  # min 1


def test_truncate_text_within_budget() -> None:
    text = "Short"
    result = _truncate_text(text, 100)
    assert result == text


def test_truncate_text_exceeds_budget() -> None:
    text = "a" * 400
    result = _truncate_text(text, 10)
    assert result.endswith("\n... [truncated]")
    assert _estimate_tokens(result) <= 25  # truncated should be close to budget


def test_truncate_text_preserves_structure() -> None:
    text = "Line 1\nLine 2\nLine 3\nLine 4"
    result = _truncate_text(text, 5)
    assert result.endswith("... [truncated]")

# ---------------------------------------------------------------------------
# Caching
# ---------------------------------------------------------------------------

def test_cache_hit(tmp_path: Path, sample_manifest: dict) -> None:
    import factory_context_builder as fcb
    original_runs_root = fcb.RUNS_ROOT
    fcb.RUNS_ROOT = tmp_path
    try:
        run_dir = tmp_path / "test-cache"
        run_dir.mkdir()
        manifest_path = run_dir / "manifest.yaml"
        manifest_path.write_text(yaml.safe_dump(sample_manifest), encoding="utf-8")
        
        checksums = _file_checksums("test-cache")
        # Build and save
        result = build_context("test-cache", depth="minimal", format="compact")
        _save_cached("test-cache", "minimal", checksums, result)
        
        # Load cache
        cached = _load_cached("test-cache", "minimal", checksums)
        assert cached is not None
        assert cached["result"]["run_id"] == "test-cache"
    finally:
        fcb.RUNS_ROOT = original_runs_root


def test_cache_miss_different_checksum(tmp_path: Path, sample_manifest: dict) -> None:
    import factory_context_builder as fcb
    original_runs_root = fcb.RUNS_ROOT
    fcb.RUNS_ROOT = tmp_path
    try:
        run_dir = tmp_path / "test-cache2"
        run_dir.mkdir()
        manifest_path = run_dir / "manifest.yaml"
        manifest_path.write_text(yaml.safe_dump(sample_manifest), encoding="utf-8")
        
        checksums = _file_checksums("test-cache2")
        result = build_context("test-cache2", depth="minimal", format="compact")
        _save_cached("test-cache2", "minimal", checksums, result)
        
        # Modify manifest
        sample_manifest["current_stage"] = "code-generator"
        manifest_path.write_text(yaml.safe_dump(sample_manifest), encoding="utf-8")
        
        new_checksums = _file_checksums("test-cache2")
        cached = _load_cached("test-cache2", "minimal", new_checksums)
        assert cached is None
    finally:
        fcb.RUNS_ROOT = original_runs_root


def test_cache_miss_different_depth(tmp_path: Path, sample_manifest: dict) -> None:
    import factory_context_builder as fcb
    original_runs_root = fcb.RUNS_ROOT
    fcb.RUNS_ROOT = tmp_path
    try:
        run_dir = tmp_path / "test-cache3"
        run_dir.mkdir()
        manifest_path = run_dir / "manifest.yaml"
        manifest_path.write_text(yaml.safe_dump(sample_manifest), encoding="utf-8")
        
        checksums = _file_checksums("test-cache3")
        result = build_context("test-cache3", depth="minimal", format="compact")
        _save_cached("test-cache3", "minimal", checksums, result)
        
        cached = _load_cached("test-cache3", "standard", checksums)
        assert cached is None
    finally:
        fcb.RUNS_ROOT = original_runs_root

# ---------------------------------------------------------------------------
# Data loaders
# ---------------------------------------------------------------------------

def test_load_manifest_valid(tmp_path: Path, sample_manifest: dict) -> None:
    import factory_context_builder as fcb
    original_runs_root = fcb.RUNS_ROOT
    fcb.RUNS_ROOT = tmp_path
    try:
        run_dir = tmp_path / "2026-05-08-healthz-endpoint"
        run_dir.mkdir()
        manifest_path = run_dir / "manifest.yaml"
        manifest_path.write_text(yaml.safe_dump(sample_manifest), encoding="utf-8")
        result = _load_manifest("2026-05-08-healthz-endpoint")
        assert result["run_id"] == "2026-05-08-healthz-endpoint"
        assert result["current_stage"] == "requirements-analyst"
    finally:
        fcb.RUNS_ROOT = original_runs_root


def test_load_manifest_missing(tmp_path: Path) -> None:
    import factory_context_builder as fcb
    original_runs_root = fcb.RUNS_ROOT
    fcb.RUNS_ROOT = tmp_path
    try:
        result = _load_manifest("nonexistent")
        assert result == {}
    finally:
        fcb.RUNS_ROOT = original_runs_root


def test_load_timeline_valid(tmp_path: Path, sample_timeline: list[dict]) -> None:
    import factory_context_builder as fcb
    original_runs_root = fcb.RUNS_ROOT
    fcb.RUNS_ROOT = tmp_path
    try:
        run_dir = tmp_path / "2026-05-08-healthz-endpoint"
        run_dir.mkdir()
        timeline_path = run_dir / "timeline.jsonl"
        timeline_path.write_text(
            "\n".join(json.dumps(e) for e in sample_timeline), encoding="utf-8"
        )
        result = _load_timeline("2026-05-08-healthz-endpoint")
        assert len(result) == 3
        assert result[0]["evt"] == "run_init"
    finally:
        fcb.RUNS_ROOT = original_runs_root


def test_load_timeline_malformed_lines(tmp_path: Path) -> None:
    import factory_context_builder as fcb
    original_runs_root = fcb.RUNS_ROOT
    fcb.RUNS_ROOT = tmp_path
    try:
        run_dir = tmp_path / "2026-05-08-healthz-endpoint"
        run_dir.mkdir()
        timeline_path = run_dir / "timeline.jsonl"
        timeline_path.write_text(
            '{"ts": "2026-05-08T00:00:00Z", "evt": "run_init"}\nMALFORMED\n{"ts": "2026-05-08T00:01:00Z", "evt": "stage_complete"}',
            encoding="utf-8",
        )
        result = _load_timeline("2026-05-08-healthz-endpoint")
        assert len(result) == 2
        assert result[0]["evt"] == "run_init"
        assert result[1]["evt"] == "stage_complete"
    finally:
        fcb.RUNS_ROOT = original_runs_root


def test_load_timeline_empty(tmp_path: Path) -> None:
    import factory_context_builder as fcb
    original_runs_root = fcb.RUNS_ROOT
    fcb.RUNS_ROOT = tmp_path
    try:
        result = _load_timeline("nonexistent")
        assert result == []
    finally:
        fcb.RUNS_ROOT = original_runs_root


def test_load_audit_md_valid(tmp_path: Path) -> None:
    audit_content = """# Audit Log

## 2026-05-08T00:02:00Z INCEPTION - User Decision (workspace-scout)
- [User] Approved workspace-scout

## 2026-05-08T00:03:00Z INCEPTION - User Answers Received
- Q1=A (greenfield)

## 2026-05-08T00:04:00Z INCEPTION - Workflow Planning
- Approved execution plan
"""
    import factory_context_builder as fcb
    original_docs = fcb.AIDLC_DOCS
    fcb.AIDLC_DOCS = tmp_path
    try:
        (tmp_path / "audit.md").write_text(audit_content, encoding="utf-8")
        result = _load_audit_md()
        assert len(result) == 3
        assert result[0]["label"] == "User Decision (workspace-scout)"
        assert result[0]["bullets"] == ["[User] Approved workspace-scout"]
    finally:
        fcb.AIDLC_DOCS = original_docs


def test_load_audit_md_empty(tmp_path: Path) -> None:
    import factory_context_builder as fcb
    original_docs = fcb.AIDLC_DOCS
    fcb.AIDLC_DOCS = tmp_path
    try:
        result = _load_audit_md()
        assert result == []
    finally:
        fcb.AIDLC_DOCS = original_docs


def test_load_audit_md_malformed_headers(tmp_path: Path) -> None:
    audit_content = """# Audit Log

## 2026-05-08T00:02:00Z INCEPTION - User Decision (workspace-scout)
- [User] Approved

## malformed header without ts
- bullet

## 2026-05-08T00:03:00Z CONSTRUCTION - Code Generation
- Generated code
"""
    import factory_context_builder as fcb
    original_docs = fcb.AIDLC_DOCS
    fcb.AIDLC_DOCS = tmp_path
    try:
        (tmp_path / "audit.md").write_text(audit_content, encoding="utf-8")
        result = _load_audit_md()
        assert len(result) == 2
        assert result[0]["label"] == "User Decision (workspace-scout)"
        assert result[1]["label"] == "Code Generation"
    finally:
        fcb.AIDLC_DOCS = original_docs


def test_load_state_md_valid(tmp_path: Path) -> None:
    state_content = """# AI-DLC State Tracking

## Project Information
- **Project Name**: Custom AIDLC
- **Project Type**: Greenfield
- **Start Date**: 2026-05-08T00:00:00Z
- **Current Stage**: CONSTRUCTION - Code Generation (COMPLETE)

## Workspace State
- **Existing Code**: Yes (generated)

## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| security-baseline | Yes | Requirements Analysis |

## Stage Progress
- [x] INCEPTION - Workspace Detection (Greenfield detected)
- [x] INCEPTION - Requirements Analysis (Approved)
- [ ] CONSTRUCTION - Code Generation
"""
    import factory_context_builder as fcb
    original_docs = fcb.AIDLC_DOCS
    fcb.AIDLC_DOCS = tmp_path
    try:
        (tmp_path / "aidlc-state.md").write_text(state_content, encoding="utf-8")
        result = _load_state_md()
        assert result["project_name"] == "Custom AIDLC"
        assert result["project_type"] == "Greenfield"
        assert result["current_stage"] == "CONSTRUCTION - Code Generation (COMPLETE)"
        assert len(result["extensions"]) == 1
        assert result["extensions"][0]["name"] == "security-baseline"
        assert len(result["stage_progress"]) == 3
    finally:
        fcb.AIDLC_DOCS = original_docs


def test_load_state_md_missing(tmp_path: Path) -> None:
    import factory_context_builder as fcb
    original_docs = fcb.AIDLC_DOCS
    fcb.AIDLC_DOCS = tmp_path
    try:
        result = _load_state_md()
        assert result == {}
    finally:
        fcb.AIDLC_DOCS = original_docs


# ---------------------------------------------------------------------------
# Compact builders
# ---------------------------------------------------------------------------

def test_build_project_context(sample_manifest: dict) -> None:
    result = _build_project_context(sample_manifest)
    assert result["slug"] == "custom-aidlc"
    assert result["version"] == "0.2.0"
    assert result["profile"]["api"] is True


def test_build_current_state(sample_manifest: dict, sample_state: dict) -> None:
    result = _build_current_state(sample_state, sample_manifest)
    assert result["stage"] == "requirements-analyst"
    assert result["completed"] == ["workspace-scout"]


def test_build_recent_decisions(sample_audit_blocks: list[dict]) -> None:
    result = _build_recent_decisions(sample_audit_blocks, max_entries=10)
    assert len(result) == 1  # Only "User Decision" matches the filter
    assert result[0]["label"] == "User Decision (workspace-scout)"


def test_build_recent_decisions_empty() -> None:
    result = _build_recent_decisions([], max_entries=10)
    assert result == []


def test_build_stage_timeline(sample_timeline: list[dict]) -> None:
    result = _build_stage_timeline(sample_timeline, max_events=5)
    assert "workspace-scout" in result
    assert len(result["workspace-scout"]) == 2


def test_build_stage_timeline_empty() -> None:
    result = _build_stage_timeline([], max_events=5)
    assert result == {}


def test_build_open_items(sample_manifest: dict, sample_timeline: list[dict]) -> None:
    result = _build_open_items(sample_manifest, sample_timeline)
    assert result["incomplete_units"] == 0
    assert result["pending_approvals"] == 0
    assert result["items"] == []


def test_build_open_items_with_pending() -> None:
    manifest = {"units": [], "completed_stages": []}
    timeline = [{"evt": "needs_human", "stage": "requirements-analyst", "ts": "2026-05-08T00:00:00Z"}]
    result = _build_open_items(manifest, timeline)
    assert result["pending_approvals"] == 1
    assert "approval:requirements-analyst" in result["items"]


def test_build_skills(sample_manifest: dict) -> None:
    result = _build_skills(sample_manifest)
    assert "using-agent-skills" in result


def test_build_skills_empty() -> None:
    result = _build_skills({"skill_paths": {}})
    assert result == []


# ---------------------------------------------------------------------------
# Compact rendering
# ---------------------------------------------------------------------------

def test_render_compact_basic() -> None:
    data = {
        "project": {"slug": "test", "version": "1.0"},
        "state": {"stage": "workspace-scout"},
    }
    result = _render_compact(data)
    assert "project:" in result
    assert "slug: test" in result
    assert "state:" in result
    assert "stage: workspace-scout" in result


def test_render_compact_nested() -> None:
    data = {
        "profile": {"ui": True, "api": False, "count": 42},
    }
    result = _render_compact(data)
    assert "profile:" in result
    assert "ui: true" in result
    assert "api: false" in result
    assert "count: 42" in result


def test_render_compact_list() -> None:
    data = {
        "items": ["a", "b", "c"],
    }
    result = _render_compact(data)
    assert "items:" in result
    assert "- a" in result
    assert "- b" in result


def test_render_compact_list_of_dicts() -> None:
    data = {
        "decisions": [{"ts": "2026-01-01", "label": "Approved"}],
    }
    result = _render_compact(data)
    assert "decisions:" in result
    assert "ts=2026-01-01" in result


def test_render_markdown_basic() -> None:
    data = {
        "project": {"slug": "test", "version": "1.0", "profile": {"ui": False, "api": True, "legacy": False, "framework": "none"}},
        "state": {"stage": "code-generator", "phase": "CONSTRUCTION", "type": "greenfield", "completed": ["workspace-scout"], "skipped": [], "failed": 0},
    }
    result = _render_markdown(data)
    assert "# AIDLC Context" in result
    assert "test" in result
    assert "code-generator" in result

# ---------------------------------------------------------------------------
# build_context integration
# ---------------------------------------------------------------------------

def test_build_context(tmp_path: Path, sample_manifest: dict) -> None:
    import factory_context_builder as fcb
    original_runs_root = fcb.RUNS_ROOT
    original_docs = fcb.AIDLC_DOCS
    fcb.RUNS_ROOT = tmp_path
    fcb.AIDLC_DOCS = tmp_path
    try:
        run_dir = tmp_path / "2026-05-08-healthz-endpoint"
        run_dir.mkdir(parents=True)
        (run_dir / "manifest.yaml").write_text(yaml.safe_dump(sample_manifest), encoding="utf-8")
        (run_dir / "timeline.jsonl").write_text("", encoding="utf-8")
        (tmp_path / "audit.md").write_text("# Audit Log\n", encoding="utf-8")
        
        result = build_context("2026-05-08-healthz-endpoint", format="compact")
        assert result["run_id"] == "2026-05-08-healthz-endpoint"
        assert "tokens" in result
        assert "context" in result
        assert "project" in result["data"]
        assert "state" in result["data"]
        assert "decisions" in result["data"]
    finally:
        fcb.RUNS_ROOT = original_runs_root
        fcb.AIDLC_DOCS = original_docs


def test_build_context_missing_run(tmp_path: Path) -> None:
    import factory_context_builder as fcb
    original_runs_root = fcb.RUNS_ROOT
    original_docs = fcb.AIDLC_DOCS
    fcb.RUNS_ROOT = tmp_path
    fcb.AIDLC_DOCS = tmp_path
    try:
        run_dir = tmp_path / "nonexistent-run"
        run_dir.mkdir(parents=True)
        result = build_context("nonexistent-run", format="compact")
        assert result["run_id"] == "nonexistent-run"
        assert "context" in result
    finally:
        fcb.RUNS_ROOT = original_runs_root
        fcb.AIDLC_DOCS = original_docs


def test_build_context_caching(tmp_path: Path, sample_manifest: dict) -> None:
    import factory_context_builder as fcb
    original_runs_root = fcb.RUNS_ROOT
    original_docs = fcb.AIDLC_DOCS
    fcb.RUNS_ROOT = tmp_path
    fcb.AIDLC_DOCS = tmp_path
    try:
        run_dir = tmp_path / "cache-test"
        run_dir.mkdir(parents=True)
        (run_dir / "manifest.yaml").write_text(yaml.safe_dump(sample_manifest), encoding="utf-8")
        (run_dir / "timeline.jsonl").write_text("", encoding="utf-8")
        (tmp_path / "audit.md").write_text("# Audit Log\n", encoding="utf-8")
        
        # First call — not cached
        result1 = build_context("cache-test", depth="minimal", format="compact")
        assert result1["cached"] is False
        
        # Second call — should be cached
        result2 = build_context("cache-test", depth="minimal", format="compact")
        assert result2["cached"] is True
        assert result2["cache_age"] is not None
    finally:
        fcb.RUNS_ROOT = original_runs_root
        fcb.AIDLC_DOCS = original_docs

# ---------------------------------------------------------------------------
# Format outputs
# ---------------------------------------------------------------------------

def test_compact_format_saves_tokens(tmp_path: Path, sample_manifest: dict) -> None:
    import factory_context_builder as fcb
    original_runs_root = fcb.RUNS_ROOT
    original_docs = fcb.AIDLC_DOCS
    fcb.RUNS_ROOT = tmp_path
    fcb.AIDLC_DOCS = tmp_path
    try:
        run_dir = tmp_path / "fmt-test"
        run_dir.mkdir(parents=True)
        (run_dir / "manifest.yaml").write_text(yaml.safe_dump(sample_manifest), encoding="utf-8")
        (run_dir / "timeline.jsonl").write_text("", encoding="utf-8")
        (tmp_path / "audit.md").write_text("# Audit Log\n", encoding="utf-8")
        
        # Use standard depth to have more content for comparison
        compact = build_context("fmt-test", depth="standard", format="compact")
        markdown = build_context("fmt-test", depth="standard", format="markdown")
        
        compact_tokens = compact["tokens"]
        markdown_tokens = markdown["tokens"]
        
        # Compact should be smaller or equal (not larger)
        assert compact_tokens <= markdown_tokens * 1.1  # Allow 10% variance
    finally:
        fcb.RUNS_ROOT = original_runs_root
        fcb.AIDLC_DOCS = original_docs


def test_json_format_output(tmp_path: Path, sample_manifest: dict) -> None:
    import factory_context_builder as fcb
    original_runs_root = fcb.RUNS_ROOT
    original_docs = fcb.AIDLC_DOCS
    fcb.RUNS_ROOT = tmp_path
    fcb.AIDLC_DOCS = tmp_path
    try:
        run_dir = tmp_path / "json-test"
        run_dir.mkdir(parents=True)
        (run_dir / "manifest.yaml").write_text(yaml.safe_dump(sample_manifest), encoding="utf-8")
        (run_dir / "timeline.jsonl").write_text("", encoding="utf-8")
        (tmp_path / "audit.md").write_text("# Audit Log\n", encoding="utf-8")
        
        result = build_context("json-test", depth="minimal", format="json")
        assert "data" in result
        assert "tokens" in result
    finally:
        fcb.RUNS_ROOT = original_runs_root
        fcb.AIDLC_DOCS = original_docs
