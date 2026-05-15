"""Tests for aidlc-scripts/factory_knowledge_dashboard.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
DASH_PY = SCRIPTS / "factory_knowledge_dashboard.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(DASH_PY), *args],
        capture_output=True, text=True,
    )


def _write_obs(p: Path, items: list[dict]) -> None:
    p.write_text("\n".join(json.dumps(o) for o in items))


def test_renders_shared_observations(tmp_path: Path):
    obs = tmp_path / "obs.jsonl"
    _write_obs(obs, [
        {"sync_id": "p1", "project": "_shared", "kind": "pattern",
         "topic_key": "aidlc/_shared/pattern/use-env-vars-for-secrets",
         "title": "Use env vars for secrets",
         "body": "Store secrets in environment variables.",
         "tags": ["security", "credentials"],
         "provenance": [
             {"sync_id": "s1", "project": "alpha", "title": "..."},
             {"sync_id": "s2", "project": "beta", "title": "..."},
             {"sync_id": "s3", "project": "gamma", "title": "..."},
         ]},
    ])
    out = tmp_path / "dash.md"
    result = _run("--observations", str(obs), "--out", str(out))
    assert result.returncode == 0, result.stderr
    text = out.read_text()
    assert "Use env vars for secrets" in text
    assert "alpha" in text and "beta" in text and "gamma" in text
    assert "`security`" in text
    assert "`aidlc/_shared/pattern/" in text


def test_filters_out_non_shared(tmp_path: Path):
    obs = tmp_path / "obs.jsonl"
    _write_obs(obs, [
        {"sync_id": "x", "project": "alpha", "kind": "pattern",
         "topic_key": "aidlc/alpha/pattern/foo",
         "title": "Only in alpha", "body": "...", "tags": []},
        {"sync_id": "y", "project": "_shared", "kind": "pattern",
         "topic_key": "aidlc/_shared/pattern/bar",
         "title": "Shared pattern", "body": "...", "tags": []},
    ])
    out = tmp_path / "dash.md"
    result = _run("--observations", str(obs), "--out", str(out))
    text = out.read_text()
    assert "Only in alpha" not in text
    assert "Shared pattern" in text


def test_groups_by_kind(tmp_path: Path):
    obs = tmp_path / "obs.jsonl"
    _write_obs(obs, [
        {"sync_id": "a", "project": "_shared", "kind": "pattern",
         "topic_key": "aidlc/_shared/pattern/x", "title": "P1", "body": "x", "tags": []},
        {"sync_id": "b", "project": "_shared", "kind": "lesson",
         "topic_key": "aidlc/_shared/lesson/y", "title": "L1", "body": "y", "tags": []},
        {"sync_id": "c", "project": "_shared", "kind": "decision",
         "topic_key": "aidlc/_shared/decision/z", "title": "D1", "body": "z", "tags": []},
    ])
    out = tmp_path / "dash.md"
    result = _run("--observations", str(obs), "--out", str(out))
    text = out.read_text()
    assert "## Pattern (1)" in text
    assert "## Lesson (1)" in text
    assert "## Decision (1)" in text


def test_no_shared_exits_1(tmp_path: Path):
    obs = tmp_path / "obs.jsonl"
    _write_obs(obs, [
        {"sync_id": "x", "project": "alpha", "kind": "pattern",
         "topic_key": "aidlc/alpha/pattern/foo",
         "title": "...", "body": "..."},
    ])
    out = tmp_path / "dash.md"
    result = _run("--observations", str(obs), "--out", str(out))
    assert result.returncode == 1
    # File still written though
    assert "No shared observations yet" in out.read_text()


def test_allow_empty_exits_0(tmp_path: Path):
    obs = tmp_path / "obs.jsonl"
    obs.write_text("")
    out = tmp_path / "dash.md"
    result = _run("--observations", str(obs), "--out", str(out), "--allow-empty")
    assert result.returncode == 0


def test_missing_file_exits_2(tmp_path: Path):
    result = _run("--observations", "/nonexistent.jsonl", "--out", str(tmp_path / "x.md"))
    assert result.returncode == 2


def test_default_output_path_in_repo(tmp_path: Path):
    """Without --out, writes to <repo>/aidlc-docs/knowledge/cross-project.md."""
    obs = tmp_path / "obs.jsonl"
    _write_obs(obs, [
        {"sync_id": "x", "project": "_shared", "kind": "pattern",
         "topic_key": "aidlc/_shared/pattern/x",
         "title": "X", "body": "y"},
    ])
    result = _run("--observations", str(obs), "--repo-root", str(tmp_path))
    assert result.returncode == 0
    default_out = tmp_path / "aidlc-docs/knowledge/cross-project.md"
    assert default_out.exists()
    assert "X" in default_out.read_text()
