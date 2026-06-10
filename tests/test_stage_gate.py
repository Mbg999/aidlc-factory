"""Tests for stage_gate.py — Stage Gate Enforcement.

Validates that the stage gate script correctly enforces stage prerequisites.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
STAGE_GATE = REPO_ROOT / "aidlc-scripts" / "stage_gate.py"


def _manifest(run_id: str, **kwargs) -> Path:
    """Create a minimal manifest for testing."""
    run_dir = REPO_ROOT / ".aidlc-orchestrator" / "runs" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "run_id": run_id,
        "completed_stages": [],
        "current_stage": "workspace-scout",
        **kwargs,
    }
    manifest_path = run_dir / "manifest.yaml"
    manifest_path.write_text(yaml.safe_dump(manifest))
    return manifest_path


class TestStageGateCheck:
    def test_workspace_scout_no_prerequisites(self):
        run_id = "test-gate-ws"
        _manifest(run_id, completed_stages=[])
        
        result = subprocess.run(
            [sys.executable, str(STAGE_GATE), "check", run_id, "workspace-scout"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"Expected OK, got: {result.stdout} {result.stderr}"
        assert "OK" in result.stdout

    def test_requirements_analyst_needs_workspace_scout(self):
        run_id = "test-gate-req-missing"
        _manifest(run_id, completed_stages=[])
        
        result = subprocess.run(
            [sys.executable, str(STAGE_GATE), "check", run_id, "requirements-analyst"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1, f"Expected BLOCKED, got: {result.stdout} {result.stderr}"
        assert "BLOCKED" in result.stdout
        assert "workspace-scout" in result.stdout

    def test_requirements_analyst_with_workspace_scout(self):
        run_id = "test-gate-req-ok"
        _manifest(run_id, completed_stages=["workspace-scout"])
        
        result = subprocess.run(
            [sys.executable, str(STAGE_GATE), "check", run_id, "requirements-analyst"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"Expected OK, got: {result.stdout} {result.stderr}"
        assert "OK" in result.stdout

    def test_code_generator_needs_workflow_planner(self):
        run_id = "test-gate-cg-missing"
        _manifest(run_id, completed_stages=["workspace-scout", "requirements-analyst"])
        
        result = subprocess.run(
            [sys.executable, str(STAGE_GATE), "check", run_id, "code-generator"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1, f"Expected BLOCKED, got: {result.stdout} {result.stderr}"
        assert "BLOCKED" in result.stdout
        assert "workflow-planner" in result.stdout

    def test_code_generator_with_workflow_planner(self):
        run_id = "test-gate-cg-ok"
        _manifest(run_id, completed_stages=["workspace-scout", "requirements-analyst", "workflow-planner"])
        
        result = subprocess.run(
            [sys.executable, str(STAGE_GATE), "check", run_id, "code-generator"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"Expected OK, got: {result.stdout} {result.stderr}"
        assert "OK" in result.stdout

    def test_ship_needs_reviewer(self):
        run_id = "test-gate-ship-missing"
        _manifest(run_id, completed_stages=["workspace-scout", "requirements-analyst", "workflow-planner", "code-generator"])
        
        result = subprocess.run(
            [sys.executable, str(STAGE_GATE), "check", run_id, "ship-agent"],
            capture_output=True, text=True,
        )
        assert result.returncode == 1, f"Expected BLOCKED, got: {result.stdout} {result.stderr}"
        assert "BLOCKED" in result.stdout

    def test_ship_with_reviewer(self):
        run_id = "test-gate-ship-ok"
        _manifest(run_id, completed_stages=["workspace-scout", "requirements-analyst", "workflow-planner", "code-generator", "reviewer-code"])
        
        result = subprocess.run(
            [sys.executable, str(STAGE_GATE), "check", run_id, "ship-agent"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"Expected OK, got: {result.stdout} {result.stderr}"
        assert "OK" in result.stdout

    def test_unknown_stage(self):
        run_id = "test-gate-unknown"
        _manifest(run_id, completed_stages=[])
        
        result = subprocess.run(
            [sys.executable, str(STAGE_GATE), "check", run_id, "nonexistent-stage"],
            capture_output=True, text=True,
        )
        assert result.returncode == 2
        assert "unknown stage" in result.stderr

    def test_missing_run(self):
        result = subprocess.run(
            [sys.executable, str(STAGE_GATE), "check", "nonexistent-run-123", "workspace-scout"],
            capture_output=True, text=True,
        )
        assert result.returncode == 2
        assert "manifest not found" in result.stderr


class TestStageGateList:
    def test_list_shows_completion(self):
        run_id = "test-gate-list"
        _manifest(run_id, completed_stages=["workspace-scout", "requirements-analyst"])
        
        result = subprocess.run(
            [sys.executable, str(STAGE_GATE), "list", run_id],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "workspace-scout" in result.stdout
        assert "requirements-analyst" in result.stdout
        assert "COMPLETED" in result.stdout


class TestStageGateNext:
    def test_next_shows_next_stage(self):
        run_id = "test-gate-next"
        _manifest(run_id, completed_stages=["workspace-scout", "requirements-analyst"])
        
        result = subprocess.run(
            [sys.executable, str(STAGE_GATE), "next", run_id],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert "workflow-planner" in result.stdout

    def test_all_mandatory_completed(self):
        run_id = "test-gate-all-done"
        # All MANDATORY stages completed (conditional stages may remain)
        _manifest(run_id, completed_stages=[
            "workspace-scout", "requirements-analyst", "workflow-planner",
            "code-generator", "build-test-agent", "reviewer-code", "ship-agent"
        ])
        
        result = subprocess.run(
            [sys.executable, str(STAGE_GATE), "next", run_id],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        # No mandatory stages should be available
        assert "No mandatory stages" in result.stdout or "Available stages" in result.stdout
