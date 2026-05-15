"""Tests for aidlc-scripts/factory_features.py."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
FEATURES_PY = SCRIPTS / "factory_features.py"


def _run(*args: str, env: dict | None = None) -> subprocess.CompletedProcess[str]:
    full_env = None if env is None else {**dict(__import__("os").environ), **env}
    return subprocess.run(
        [sys.executable, str(FEATURES_PY), *args],
        capture_output=True, text=True, env=full_env,
    )


@pytest.fixture
def fake_repo(tmp_path: Path) -> Path:
    budgets = tmp_path / ".aidlc-orchestrator" / "budgets"
    budgets.mkdir(parents=True)
    return tmp_path


def _write_budget(repo: Path, features: dict) -> None:
    (repo / ".aidlc-orchestrator/budgets/default.yaml").write_text(
        yaml.safe_dump({"per_stage": {}, "features": features})
    )


def test_default_is_false_when_flag_missing(fake_repo: Path):
    _write_budget(fake_repo, {})  # empty features
    result = _run("--repo-root", str(fake_repo), "get", "content_validator_strict")
    assert result.returncode == 0
    assert result.stdout.strip() == "false"


def test_explicit_true_returns_true(fake_repo: Path):
    _write_budget(fake_repo, {"content_validator_strict": True})
    result = _run("--repo-root", str(fake_repo), "get", "content_validator_strict")
    assert result.returncode == 0
    assert result.stdout.strip() == "true"


def test_is_set_exits_0_when_true(fake_repo: Path):
    _write_budget(fake_repo, {"content_validator_strict": True})
    result = _run("--repo-root", str(fake_repo), "is-set", "content_validator_strict")
    assert result.returncode == 0


def test_is_set_exits_1_when_false(fake_repo: Path):
    _write_budget(fake_repo, {"content_validator_strict": False})
    result = _run("--repo-root", str(fake_repo), "is-set", "content_validator_strict")
    assert result.returncode == 1


def test_env_override_wins_over_yaml(fake_repo: Path):
    _write_budget(fake_repo, {"content_validator_strict": False})
    result = _run("--repo-root", str(fake_repo), "get", "content_validator_strict",
                  env={"AIDLC_FEATURE_CONTENT_VALIDATOR_STRICT": "true"})
    assert result.stdout.strip() == "true"


def test_unknown_flag_exits_2(fake_repo: Path):
    _write_budget(fake_repo, {})
    result = _run("--repo-root", str(fake_repo), "get", "this-flag-does-not-exist")
    assert result.returncode == 2


def test_list_prints_all_known_flags(fake_repo: Path):
    _write_budget(fake_repo, {"content_validator_strict": True})
    result = _run("--repo-root", str(fake_repo), "list")
    assert result.returncode == 0
    # All 4 known flags should appear in output
    for flag in ["content_validator_strict", "slo_blocking",
                 "knowledge_promotion", "shared_corpus_injection"]:
        assert flag in result.stdout
    assert "content_validator_strict=true" in result.stdout


def test_truthy_yaml_values_accepted(fake_repo: Path):
    """YAML can give us 'yes', 1, 'on' etc. — all should be true."""
    for truthy in [True, "true", "yes", "on", 1]:
        (fake_repo / ".aidlc-orchestrator/budgets/default.yaml").write_text(
            f"per_stage: {{}}\nfeatures:\n  knowledge_promotion: {truthy}\n"
        )
        result = _run("--repo-root", str(fake_repo), "get", "knowledge_promotion")
        assert result.stdout.strip() == "true", f"{truthy!r} should be true"


def test_no_subcommand_exits_2():
    result = _run()
    assert result.returncode == 2
