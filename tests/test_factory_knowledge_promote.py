"""Tests for aidlc-scripts/factory_knowledge_promote.py."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
KP_PY = SCRIPTS / "factory_knowledge_promote.py"


def _run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(KP_PY), *args],
        capture_output=True, text=True,
    )


def _write_obs(path: Path, observations: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(o) for o in observations))


def test_three_similar_observations_across_three_projects_get_promoted(tmp_path: Path):
    obs = tmp_path / "obs.jsonl"
    _write_obs(obs, [
        {"sync_id": "obs-1", "project": "alpha", "kind": "pattern",
         "title": "Use environment variables for database credentials",
         "body": "Storing database credentials in environment variables is "
                 "safer than committing them to source control."},
        {"sync_id": "obs-2", "project": "beta", "kind": "pattern",
         "title": "Database credentials belong in environment variables",
         "body": "Never commit credentials to source. Environment variables "
                 "are the standard way to inject secrets at runtime."},
        {"sync_id": "obs-3", "project": "gamma", "kind": "pattern",
         "title": "Environment variables for credentials",
         "body": "Store database credentials in environment variables rather "
                 "than in source code or config files."},
    ])
    result = _run("--observations", str(obs), "--similarity-threshold", "0.4")
    assert result.returncode == 0
    promos = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
    assert len(promos) == 1
    p = promos[0]
    assert p["topic_key"].startswith("aidlc/_shared/pattern/")
    assert set(p["projects_observed_in"]) == {"alpha", "beta", "gamma"}
    assert p["member_count"] == 3


def test_two_projects_not_promoted(tmp_path: Path):
    obs = tmp_path / "obs.jsonl"
    _write_obs(obs, [
        {"sync_id": "x", "project": "alpha", "kind": "pattern",
         "title": "Pattern A", "body": "Some text about pattern A"},
        {"sync_id": "y", "project": "beta", "kind": "pattern",
         "title": "Pattern A", "body": "Some text about pattern A"},
    ])
    result = _run("--observations", str(obs), "--similarity-threshold", "0.5")
    assert result.returncode == 0
    promos = [l for l in result.stdout.splitlines() if l.strip()]
    assert promos == []


def test_dissimilar_observations_not_clustered(tmp_path: Path):
    obs = tmp_path / "obs.jsonl"
    _write_obs(obs, [
        {"sync_id": "1", "project": "alpha", "kind": "pattern",
         "title": "Cats", "body": "Cats are mammals."},
        {"sync_id": "2", "project": "beta", "kind": "pattern",
         "title": "Database migrations", "body": "Always backup before migrating."},
        {"sync_id": "3", "project": "gamma", "kind": "pattern",
         "title": "Whales", "body": "Whales are aquatic mammals."},
    ])
    result = _run("--observations", str(obs), "--similarity-threshold", "0.8")
    assert result.returncode == 0
    promos = [l for l in result.stdout.splitlines() if l.strip()]
    assert promos == []  # too dissimilar


def test_different_kinds_not_clustered(tmp_path: Path):
    """Same title across kinds (pattern vs decision) should NOT cluster."""
    obs = tmp_path / "obs.jsonl"
    _write_obs(obs, [
        {"sync_id": "1", "project": "alpha", "kind": "pattern",
         "title": "Use Postgres", "body": "Postgres is the right choice."},
        {"sync_id": "2", "project": "beta", "kind": "decision",
         "title": "Use Postgres", "body": "Postgres is the right choice."},
        {"sync_id": "3", "project": "gamma", "kind": "lesson",
         "title": "Use Postgres", "body": "Postgres is the right choice."},
    ])
    result = _run("--observations", str(obs), "--similarity-threshold", "0.3")
    promos = [l for l in result.stdout.splitlines() if l.strip()]
    assert promos == []  # different kinds — no cluster


def test_min_projects_flag_respected(tmp_path: Path):
    """With --min-projects=2, two projects is enough."""
    obs = tmp_path / "obs.jsonl"
    _write_obs(obs, [
        {"sync_id": "1", "project": "alpha", "kind": "lesson",
         "title": "Always log requests", "body": "Log every incoming request."},
        {"sync_id": "2", "project": "beta", "kind": "lesson",
         "title": "Log every request", "body": "Logging incoming requests "
                                              "is essential for debugging."},
    ])
    result = _run("--observations", str(obs), "--similarity-threshold", "0.3",
                  "--min-projects", "2")
    assert result.returncode == 0
    promos = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
    assert len(promos) == 1


def test_provenance_tracked(tmp_path: Path):
    obs = tmp_path / "obs.jsonl"
    items = [
        {"sync_id": f"obs-{i}", "project": f"p-{i}", "kind": "pattern",
         "title": "Database connection pooling",
         "body": "Use connection pooling for the database to avoid creating "
                 "a new connection per request."}
        for i in range(3)
    ]
    _write_obs(obs, items)
    result = _run("--observations", str(obs), "--similarity-threshold", "0.5")
    assert result.returncode == 0
    promos = [json.loads(l) for l in result.stdout.splitlines() if l.strip()]
    assert len(promos) == 1
    p = promos[0]
    sync_ids = {pr["sync_id"] for pr in p["provenance"]}
    assert sync_ids == {"obs-0", "obs-1", "obs-2"}


def test_dry_run_does_not_write(tmp_path: Path):
    obs = tmp_path / "obs.jsonl"
    items = [
        {"sync_id": f"obs-{i}", "project": f"p-{i}", "kind": "pattern",
         "title": "Use HTTPS everywhere",
         "body": "Always use HTTPS for production traffic."}
        for i in range(3)
    ]
    _write_obs(obs, items)
    out = tmp_path / "promotions.jsonl"
    result = _run("--observations", str(obs), "--similarity-threshold", "0.4",
                  "--dry-run", "--out", str(out))
    assert result.returncode == 0
    assert "dry-run" in result.stdout
    assert not out.exists()


def test_out_flag_writes_to_file(tmp_path: Path):
    obs = tmp_path / "obs.jsonl"
    items = [
        {"sync_id": f"o{i}", "project": f"p{i}", "kind": "pattern",
         "title": "Cache responses",
         "body": "Use Redis or Memcached to cache common responses."}
        for i in range(3)
    ]
    _write_obs(obs, items)
    out = tmp_path / "promotions.jsonl"
    result = _run("--observations", str(obs), "--similarity-threshold", "0.4",
                  "--out", str(out))
    assert result.returncode == 0
    assert out.exists()


def test_missing_field_exits_2(tmp_path: Path):
    obs = tmp_path / "obs.jsonl"
    obs.write_text(json.dumps({"sync_id": "x"}))  # missing project/kind/title/body
    result = _run("--observations", str(obs))
    assert result.returncode == 2


def test_missing_file_exits_2():
    result = _run("--observations", "/nonexistent.jsonl")
    assert result.returncode == 2
