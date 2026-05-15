"""Executor conformance tests — `.aidlc-orchestrator/contracts/executor.v1.md`.

Parametrized across every registered adapter. Production adapters must pass
all tests; stub adapters (health_check returns False) skip with a clear
marker so failures don't fire prematurely.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "aidlc-scripts"))

from executors import (
    ClaudeCodeExecutor,
    OpenCodeExecutor,
    SpawnResult,
    StageExecutor,
)


# -------------------- adapter parametrization --------------------


def _claude_factory(repo: Path, spawn_callable=None):
    return ClaudeCodeExecutor(repo, spawn_callable=spawn_callable)


def _opencode_factory(repo: Path, spawn_callable=None):
    # OpenCode stub doesn't accept spawn_callable — that's fine, the
    # conformance suite skips non-production adapters for spawn-path tests.
    return OpenCodeExecutor(repo)


ADAPTER_PARAMS = [
    pytest.param(_claude_factory, "claude-code", "production", id="claude-code"),
    pytest.param(_opencode_factory, "opencode", "stub", id="opencode-stub"),
]


def _skip_if_not_production(status: str):
    if status != "production":
        pytest.skip(f"adapter is a {status}, skipping spawn-path test")


# -------------------- fake spawn fixture --------------------


@pytest.fixture
def minimal_workspace(tmp_path: Path) -> Path:
    """Workspace with the schema needed to validate spawn output."""
    # Copy the requirements-analyst schema into the test workspace.
    contracts_dir = tmp_path / ".aidlc-orchestrator" / "contracts"
    contracts_dir.mkdir(parents=True)
    src = REPO_ROOT / ".aidlc-orchestrator" / "contracts" / "requirements-analyst.output.v1.json"
    (contracts_dir / "requirements-analyst.output.v1.json").write_text(
        src.read_text()
    )
    # Symlink factory_validate so the adapter can invoke it.
    scripts = tmp_path / "aidlc-scripts"
    scripts.mkdir()
    (scripts / "factory_validate.py").symlink_to(REPO_ROOT / "aidlc-scripts" / "factory_validate.py")
    (scripts / "VERSION").write_text("0.2.0\n")

    # Handoffs dir
    (tmp_path / ".aidlc-orchestrator" / "runs" / "r1" / "handoffs").mkdir(parents=True)
    return tmp_path


def _fake_spawn_writes_valid_handoff(*, output_handoff_path: Path, **kwargs):
    """Write a minimal-valid requirements-analyst output handoff."""
    output_handoff_path.write_text(yaml.safe_dump({
        "status": "complete",
        "depth": "minimal",
        "artifacts": [
            {"path": "aidlc-docs/inception/requirements/r1-requirements.md", "kind": "spec"},
        ],
        "audit_entries": ["[Test] fake spawn"],
        "skill_compliance": [
            {"skill": "a", "status": "PASS", "evidence": "x"},
            {"skill": "b", "status": "PASS", "evidence": "x"},
            {"skill": "c", "status": "PASS", "evidence": "x"},
            {"skill": "d", "status": "PASS", "evidence": "x"},
        ],
        "cost": {"tokens_in": 50_000, "tokens_out": 20_000, "wall_clock_min": 5.0},
    }))
    return {"tokens_in": 50_000, "tokens_out": 20_000}


# -------------------- conformance tests --------------------


@pytest.mark.parametrize("factory,adapter_name,status", ADAPTER_PARAMS)
def test_adapter_metadata_present(factory, adapter_name, status, tmp_path):
    """Every adapter must declare name, version, capabilities, target_tools."""
    ad = factory(tmp_path)
    assert ad.name == adapter_name
    assert ad.version
    assert ad.capabilities.max_concurrency >= 1
    assert isinstance(ad.capabilities.target_tools, tuple)
    assert ad.capabilities.target_tools  # at least one target tool


@pytest.mark.parametrize("factory,adapter_name,status", ADAPTER_PARAMS)
def test_spawn_emits_valid_output(factory, adapter_name, status, minimal_workspace):
    _skip_if_not_production(status)

    ad = factory(minimal_workspace, spawn_callable=_fake_spawn_writes_valid_handoff)
    input_p = minimal_workspace / ".aidlc-orchestrator/runs/r1/handoffs/requirements-analyst.input.yaml"
    input_p.write_text("placeholder: input\n")

    result = ad.spawn("requirements-analyst", input_p)
    assert isinstance(result, SpawnResult)
    assert result.status == "complete", result.error
    assert result.output_handoff_path is not None
    assert result.output_handoff_path.exists()


@pytest.mark.parametrize("factory,adapter_name,status", ADAPTER_PARAMS)
def test_spawn_emits_cost_data(factory, adapter_name, status, minimal_workspace):
    _skip_if_not_production(status)

    ad = factory(minimal_workspace, spawn_callable=_fake_spawn_writes_valid_handoff)
    input_p = minimal_workspace / ".aidlc-orchestrator/runs/r1/handoffs/requirements-analyst.input.yaml"
    input_p.write_text("placeholder: input\n")

    result = ad.spawn("requirements-analyst", input_p)
    assert result.tokens_in > 0
    assert result.tokens_out > 0
    assert result.wall_clock_sec >= 0


@pytest.mark.parametrize("factory,adapter_name,status", ADAPTER_PARAMS)
def test_invalid_output_yields_failed(factory, adapter_name, status, minimal_workspace):
    _skip_if_not_production(status)

    def _bad_spawn(*, output_handoff_path: Path, **kwargs):
        # Write something the schema rejects (missing required field 'status')
        output_handoff_path.write_text(yaml.safe_dump({
            "depth": "minimal",
            "artifacts": [],
        }))
        return {}

    ad = factory(minimal_workspace, spawn_callable=_bad_spawn)
    input_p = minimal_workspace / ".aidlc-orchestrator/runs/r1/handoffs/requirements-analyst.input.yaml"
    input_p.write_text("placeholder: input\n")
    result = ad.spawn("requirements-analyst", input_p)
    assert result.status == "failed"
    assert result.error is not None


@pytest.mark.parametrize("factory,adapter_name,status", ADAPTER_PARAMS)
def test_timeout_returns_timeout_status(factory, adapter_name, status, minimal_workspace):
    _skip_if_not_production(status)

    def _timeout_spawn(**kwargs):
        raise TimeoutError("simulated timeout")

    ad = factory(minimal_workspace, spawn_callable=_timeout_spawn)
    input_p = minimal_workspace / ".aidlc-orchestrator/runs/r1/handoffs/requirements-analyst.input.yaml"
    input_p.write_text("placeholder: input\n")
    result = ad.spawn("requirements-analyst", input_p, timeout_sec=1)
    assert result.status == "timeout"


@pytest.mark.parametrize("factory,adapter_name,status", ADAPTER_PARAMS)
def test_exception_in_spawn_yields_failed(factory, adapter_name, status, minimal_workspace):
    _skip_if_not_production(status)

    def _raising_spawn(**kwargs):
        raise RuntimeError("simulated failure")

    ad = factory(minimal_workspace, spawn_callable=_raising_spawn)
    input_p = minimal_workspace / ".aidlc-orchestrator/runs/r1/handoffs/requirements-analyst.input.yaml"
    input_p.write_text("placeholder: input\n")
    result = ad.spawn("requirements-analyst", input_p)
    assert result.status == "failed"
    assert "simulated failure" in (result.error or "")


# -------------------- stub-specific tests --------------------


def test_opencode_stub_spawn_returns_unsupported(minimal_workspace):
    """Calling spawn on the stub returns status=unsupported with a clear error."""
    ad = OpenCodeExecutor(minimal_workspace)
    input_p = minimal_workspace / ".aidlc-orchestrator/runs/r1/handoffs/requirements-analyst.input.yaml"
    input_p.write_text("placeholder: input\n")
    result = ad.spawn("requirements-analyst", input_p)
    assert result.status == "unsupported"
    assert "stub" in (result.error or "").lower() or "NotImplementedError" in (result.error or "")


def test_opencode_health_check_false():
    """Stub MUST advertise itself as unavailable so the orchestrator falls back."""
    ad = OpenCodeExecutor(Path("/tmp"))
    assert ad.health_check() is False


def test_claude_health_check_true():
    ad = ClaudeCodeExecutor(Path("/tmp"))
    assert ad.health_check() is True


# -------------------- registry consistency --------------------


def test_registry_loads_and_matches_adapters():
    """Each adapter in registry.yaml MUST be importable + class names match."""
    reg = yaml.safe_load((REPO_ROOT / "aidlc-scripts/executors/registry.yaml").read_text())
    names = {e["name"] for e in reg["executors"]}
    assert "claude-code" in names
    assert "opencode" in names

    # Instantiate each — should not raise
    for entry in reg["executors"]:
        if entry["name"] == "claude-code":
            assert ClaudeCodeExecutor.name == entry["name"]
        elif entry["name"] == "opencode":
            assert OpenCodeExecutor.name == entry["name"]
