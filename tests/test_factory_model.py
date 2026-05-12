from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
MODEL_PY = SCRIPTS / "factory_model.py"

# Import the module for unit tests
import importlib.util
spec = importlib.util.spec_from_file_location("factory_model", MODEL_PY)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_resolve_workspace_scout(env_setup):
    """workspace-scout should resolve to sonnet."""
    model = mod.resolve("workspace-scout")
    assert model == "sonnet"


def test_resolve_code_generator(env_setup):
    """code-generator should resolve to opus."""
    model = mod.resolve("code-generator")
    assert model == "opus"


def test_resolve_requirements_analyst(env_setup):
    """requirements-analyst should resolve to opus."""
    model = mod.resolve("requirements-analyst")
    assert model == "opus"


def test_resolve_reviewer_wildcard(env_setup):
    """reviewer-* stages should fall back to reviewer-code config (sonnet)."""
    model = mod.resolve("reviewer-security")
    assert model == "sonnet"


def test_resolve_unknown_stage(env_setup):
    """Unknown stage should return default model."""
    model = mod.resolve("nonexistent-stage")
    assert model == mod.DEFAULT_MODEL  # "sonnet"


def test_resolve_env_override(env_setup):
    """Env var AIDLC_MODEL_CODE_GENERATOR should override budget config."""
    os.environ["AIDLC_MODEL_CODE_GENERATOR"] = "haiku"
    try:
        model = mod.resolve("code-generator")
        assert model == "haiku"
    finally:
        os.environ.pop("AIDLC_MODEL_CODE_GENERATOR", None)


def test_cli_resolve(env_setup):
    """CLI should print the model name."""
    result = subprocess.run(
        [sys.executable, str(MODEL_PY), "resolve", "code-generator"],
        capture_output=True, text=True, env={**os.environ},
    )
    assert result.returncode == 0
    assert result.stdout.strip() == "opus"


def test_cli_resolve_unknown(env_setup):
    """CLI with unknown stage should print default."""
    result = subprocess.run(
        [sys.executable, str(MODEL_PY), "resolve", "nonexistent"],
        capture_output=True, text=True, env={**os.environ},
    )
    assert result.returncode == 0
    assert result.stdout.strip() == mod.DEFAULT_MODEL
