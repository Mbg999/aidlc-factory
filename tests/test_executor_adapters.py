"""EXE-02/03: Executor adapter tests.

Validates:
- EXE-02: Stage registry correctly discovers adapters and reports contract coverage
- EXE-03: All adapters implement the StageExecutor interface contract
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent

STAGE_REGISTRY_SCRIPT = REPO_ROOT / "aidlc-scripts" / "factory_stage_registry.py"
STAGE_DIR = REPO_ROOT / ".claude" / "agents" / "stage"


class TestStageRegistry:
    def test_registry_script_exists(self):
        assert STAGE_REGISTRY_SCRIPT.exists(), \
            "factory_stage_registry.py must exist"

    def _registry(self) -> dict:
        return subprocess_run(
            [sys.executable, str(STAGE_REGISTRY_SCRIPT), "--repo-root",
             str(REPO_ROOT), "json"],
        )

    def test_registry_script_runs(self):
        result = self._registry()
        assert result["returncode"] == 0, \
            f"registry script failed: {result['stderr']}"

    def test_registry_returns_valid_json(self):
        result = self._registry()
        registry = json.loads(result["stdout"])
        assert isinstance(registry, list), "registry must return a list"

    def test_registry_has_all_stages(self):
        result = self._registry()
        registry = json.loads(result["stdout"])
        stage_files = {p.stem for p in STAGE_DIR.glob("*.md")}
        registered_names = {r["name"] for r in registry}
        missing = stage_files - registered_names
        assert not missing, \
            f"Registry missing stages: {missing}"

    def test_every_stage_has_phase(self):
        result = self._registry()
        registry = json.loads(result["stdout"])
        for r in registry:
            assert r["phase"] is not None, \
                f"{r['name']} missing phase assignment"

    def test_every_stage_has_commands(self):
        result = self._registry()
        registry = json.loads(result["stdout"])
        for r in registry:
            assert len(r["commands"]) >= 1, \
                f"{r['name']} must route to at least one command"

    def test_every_stage_has_execution_mode(self):
        result = self._registry()
        registry = json.loads(result["stdout"])
        valid_modes = {"full-spawn", "post-execution"}
        for r in registry:
            assert r["execution_mode"] in valid_modes, \
                f"{r['name']}: invalid execution_mode '{r['execution_mode']}'"

    def test_every_stage_has_input_contract(self):
        result = self._registry()
        registry = json.loads(result["stdout"])
        for r in registry:
            assert r["input_contract_present"], \
                f"{r['name']}: input contract '{r['input_contract']}' not found"

    def test_every_stage_has_output_contract(self):
        result = self._registry()
        registry = json.loads(result["stdout"])
        for r in registry:
            assert r["output_contract_present"], \
                f"{r['name']}: output contract '{r['output_contract']}' not found"

    def test_every_stage_has_model(self):
        result = self._registry()
        registry = json.loads(result["stdout"])
        for r in registry:
            assert r["model"] is not None, \
                f"{r['name']} missing model assignment"

    def test_registry_stage_count_matches(self):
        result = self._registry()
        registry = json.loads(result["stdout"])
        assert len(registry) == 14, \
            f"Expected 14 stages, found {len(registry)}"


def subprocess_run(args: list[str]) -> dict:
    import subprocess
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        timeout=30,
    )
    return {
        "returncode": proc.returncode,
        "stdout": proc.stdout,
        "stderr": proc.stderr,
    }
