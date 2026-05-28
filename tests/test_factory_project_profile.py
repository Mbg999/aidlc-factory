#!/usr/bin/env python3
"""Tests for factory_project_profile.py — project profile classification & DS bootstrap."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

try:
    import yaml
except ImportError:
    pytest.skip("pyyaml not installed", allow_module_level=True)

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "aidlc-scripts"
sys.path.insert(0, str(SCRIPTS))
import factory_project_profile as mod
sys.path.pop(0)


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def tmp_repo(tmp_path: Path) -> Path:
    """Minimal repo root with aidlc-scripts symlinked (or copied) so subcalls work."""
    # We don't copy the whole repo — tests that need subcalls will use REPO_ROOT directly.
    return tmp_path


def _write_ws_yaml(path: Path, workspace_state: dict) -> None:
    """Write a minimal workspace-scout output YAML."""
    data = {"workspace_state": workspace_state}
    path.write_text(yaml.safe_dump(data), encoding="utf-8")


# ── classify ─────────────────────────────────────────────────────────────────


class TestClassify:
    def test_ui_true_react(self, tmp_repo: Path):
        ws = {
            "programming_languages": ["TypeScript"],
            "project_structure": "SPA frontend React",
            "tech_stack": [
                {"package": "react", "version": "18.2.0", "ecosystem": "npm"},
                {"package": "react-dom", "version": "18.2.0", "ecosystem": "npm"},
            ],
        }
        out = tmp_repo / "ws.yaml"
        _write_ws_yaml(out, ws)
        profile = mod.classify(out, user_request="")
        assert profile["ui"] is True
        assert profile["framework"] == "react"

    def test_ui_false_react_native_only(self, tmp_repo: Path):
        ws = {
            "programming_languages": ["JavaScript"],
            "project_structure": "mobile app",
            "tech_stack": [
                {"package": "react-native", "version": "0.72.0", "ecosystem": "npm"},
                {"package": "react", "version": "18.2.0", "ecosystem": "npm"},
            ],
        }
        out = tmp_repo / "ws.yaml"
        _write_ws_yaml(out, ws)
        profile = mod.classify(out, user_request="")
        assert profile["ui"] is False

    def test_ui_false_no_frontend(self, tmp_repo: Path):
        ws = {
            "programming_languages": ["Python"],
            "project_structure": "microservice",
            "tech_stack": [
                {"package": "fastapi", "version": "0.100.0", "ecosystem": "pip"},
            ],
        }
        out = tmp_repo / "ws.yaml"
        _write_ws_yaml(out, ws)
        profile = mod.classify(out, user_request="")
        assert profile["ui"] is False
        assert profile["api"] is True

    def test_detect_api_from_request(self, tmp_repo: Path):
        ws = {
            "programming_languages": ["TypeScript"],
            "project_structure": "library",
            "tech_stack": [],
        }
        out = tmp_repo / "ws.yaml"
        _write_ws_yaml(out, ws)
        profile = mod.classify(out, user_request="add a REST endpoint for auth")
        assert profile["api"] is True

    def test_detect_legacy_from_request(self, tmp_repo: Path):
        ws = {
            "programming_languages": ["Java"],
            "project_structure": "monolith",
            "tech_stack": [],
        }
        out = tmp_repo / "ws.yaml"
        _write_ws_yaml(out, ws)
        profile = mod.classify(out, user_request="refactor the legacy auth module")
        assert profile["has_legacy"] is True

    def test_detect_legacy_from_workspace(self, tmp_repo: Path):
        ws = {
            "programming_languages": ["Java"],
            "project_structure": "monolith",
            "reverse_engineering_artifacts_present": True,
            "tech_stack": [],
        }
        out = tmp_repo / "ws.yaml"
        _write_ws_yaml(out, ws)
        profile = mod.classify(out, user_request="add new feature")
        assert profile["has_legacy"] is True

    def test_figma_data_propagated(self, tmp_repo: Path):
        ws = {
            "has_figma_data": True,
            "figma_paths": ["figma/raw-data.json"],
            "programming_languages": ["TypeScript"],
            "project_structure": "SPA frontend React",
            "tech_stack": [
                {"package": "react", "version": "18.2.0", "ecosystem": "npm"},
            ],
        }
        out = tmp_repo / "ws.yaml"
        _write_ws_yaml(out, ws)
        profile = mod.classify(out, user_request="")
        assert profile["has_figma_data"] is True

    def test_stitch_data_propagated(self, tmp_repo: Path):
        ws = {
            "has_stitch_data": True,
            "stitch_paths": ["stitch/export.html"],
            "programming_languages": ["TypeScript"],
            "project_structure": "SPA frontend React",
            "tech_stack": [
                {"package": "react", "version": "18.2.0", "ecosystem": "npm"},
            ],
        }
        out = tmp_repo / "ws.yaml"
        _write_ws_yaml(out, ws)
        profile = mod.classify(out, user_request="")
        assert profile["has_stitch_data"] is True


# ── bootstrap ──────────────────────────────────────────────────────────────


class TestBootstrap:
    def test_skip_when_exists(self, tmp_repo: Path):
        (tmp_repo / "design-system").mkdir()
        result = mod.bootstrap(tmp_repo)
        assert result["action"] == "skip"

    def test_error_when_script_missing(self, tmp_repo: Path):
        # factory_ds_bootstrap.py won't exist under tmp_repo/aidlc-scripts
        with patch.object(mod, "_SCRIPT_DIR", tmp_repo / "aidlc-scripts"):
            result = mod.bootstrap(tmp_repo)
            assert result["action"] == "error"

    @patch("factory_project_profile._run")
    def test_calls_init_when_missing(self, mock_run, tmp_repo: Path):
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        result = mod.bootstrap(tmp_repo, force=False, dry_run=False)
        assert result["action"] == "bootstrap"
        cmd = mock_run.call_args[0][0]
        assert "init" in cmd


# ── reverse_engineer_ui ────────────────────────────────────────────────────


class TestReverseEngineerUI:
    def test_skip_when_no_css(self, tmp_repo: Path):
        result = mod.reverse_engineer_ui(tmp_repo, dry_run=False)
        assert result["action"] == "skip"

    def test_dry_run_extracts_tokens(self, tmp_repo: Path):
        css = tmp_repo / "src" / "styles.css"
        css.parent.mkdir(parents=True)
        css.write_text("""
            .btn { padding: 16px; border-radius: 8px; color: #2563EB; font-size: 14px; }
        """)
        result = mod.reverse_engineer_ui(tmp_repo, dry_run=True)
        assert result["action"] == "dry-run"
        assert "tokens" in result
        # Should have extracted at least padding (16), radius (8), color (#2563EB), font-size (14)
        tokens = result["tokens"]
        assert len(tokens["spacing"]) > 0
        assert len(tokens["radius"]) > 0
        assert len(tokens["color"]) > 0
        assert len(tokens["typography"]) > 0

    def test_extracts_from_styled_components_file(self, tmp_repo: Path):
        tsx = tmp_repo / "src" / "Button.styled.ts"
        tsx.parent.mkdir(parents=True)
        tsx.write_text("""
            import styled from 'styled-components';
            export const Btn = styled.button`
                padding: 12px 24px;
                border-radius: 6px;
                color: #EF4444;
                font-size: 16px;
            `;
        """)
        result = mod.reverse_engineer_ui(tmp_repo, dry_run=True)
        assert result["action"] == "dry-run"
        tokens = result["tokens"]
        assert len(tokens["spacing"]) > 0
        assert len(tokens["color"]) > 0


# ── set_manifest ─────────────────────────────────────────────────────────────


class TestSetManifest:
    @patch("factory_project_profile._run")
    def test_persists_all_fields(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="updated", stderr="")
        profile = {
            "ui": True,
            "api": False,
            "has_legacy": False,
            "framework": "react",
            "design_system_path": "design-system/",
            "has_figma_data": True,
            "has_stitch_data": False,
        }
        result = mod.set_manifest("test-run-001", profile)
        assert result["action"] == "set-manifest"
        assert result["returncode"] == 0
        cmd = mock_run.call_args[0][0]
        # cmd[0] is sys.executable; factory_run.py appears later in the list
        cmd_str = " ".join(str(c) for c in cmd)
        assert "factory_run.py" in cmd_str
        assert "set" in cmd
        assert "test-run-001" in cmd


# ── run_pipeline (integration-ish) ─────────────────────────────────────────


class TestRunPipeline:
    @patch("factory_project_profile.classify")
    @patch("factory_project_profile.bootstrap")
    @patch("factory_project_profile.snap_figma")
    @patch("factory_project_profile.snap_stitch")
    @patch("factory_project_profile.reverse_engineer_ui")
    @patch("factory_project_profile.set_manifest")
    def test_full_pipeline_ui_no_external_data_brownfield(
        self, mock_set, mock_re, mock_stitch, mock_figma, mock_boot, mock_cls, tmp_repo: Path
    ):
        mock_cls.return_value = {
            "ui": True, "api": False, "has_legacy": False,
            "framework": "react", "design_system_path": "",
            "has_figma_data": False, "has_stitch_data": False,
        }
        mock_boot.return_value = {"action": "bootstrap", "returncode": 0}
        mock_figma.return_value = {"action": "skip"}
        mock_stitch.return_value = {"action": "skip"}
        mock_re.return_value = {"action": "reverse-engineer"}
        mock_set.return_value = {"action": "set-manifest", "returncode": 0}

        ws_out = tmp_repo / "ws.yaml"
        ws_out.write_text("workspace_state:\n  project_type: brownfield\n")

        result = mod.run_pipeline("run-001", ws_out, tmp_repo)
        # The log line is "[Bootstrap] design-system/ missing — running init"
        assert any("[Bootstrap] design-system/ missing" in line for line in result["logs"])
        assert any("[ReverseEngineer] brownfield UI without figma/stitch" in line for line in result["logs"])
        assert result["profile"]["ui"] is True
        mock_boot.assert_called_once()
        mock_re.assert_called_once()
        mock_set.assert_called_once()

    @patch("factory_project_profile.classify")
    @patch("factory_project_profile.bootstrap")
    @patch("factory_project_profile.snap_figma")
    @patch("factory_project_profile.snap_stitch")
    @patch("factory_project_profile.reverse_engineer_ui")
    @patch("factory_project_profile.set_manifest")
    def test_full_pipeline_ui_with_figma(
        self, mock_set, mock_re, mock_stitch, mock_figma, mock_boot, mock_cls, tmp_repo: Path
    ):
        mock_cls.return_value = {
            "ui": True, "api": False, "has_legacy": False,
            "framework": "react", "design_system_path": "design-system/",
            "has_figma_data": True, "has_stitch_data": False,
        }
        mock_boot.return_value = {"action": "skip"}
        mock_figma.return_value = {"action": "snap-and-import", "snapped_path": "figma/snapped.json"}
        mock_stitch.return_value = {"action": "skip"}
        mock_re.return_value = {"action": "skip"}
        mock_set.return_value = {"action": "set-manifest", "returncode": 0}

        ws_out = tmp_repo / "ws.yaml"
        ws_out.write_text("workspace_state:\n  project_type: brownfield\n")

        result = mod.run_pipeline("run-002", ws_out, tmp_repo)
        # Log line is "[Figma] has_figma_data=true — snapping"
        assert any("[Figma] has_figma_data=true" in line for line in result["logs"])
        assert "figma/snapped.json" == result["profile"].get("figma_snapped_path")
        mock_figma.assert_called_once()
        mock_re.assert_not_called()

    @patch("factory_project_profile.classify")
    @patch("factory_project_profile.bootstrap")
    @patch("factory_project_profile.snap_figma")
    @patch("factory_project_profile.snap_stitch")
    @patch("factory_project_profile.reverse_engineer_ui")
    @patch("factory_project_profile.set_manifest")
    def test_full_pipeline_no_ui_skips_all(
        self, mock_set, mock_re, mock_stitch, mock_figma, mock_boot, mock_cls, tmp_repo: Path
    ):
        mock_cls.return_value = {
            "ui": False, "api": True, "has_legacy": False,
            "framework": "none", "design_system_path": "",
            "has_figma_data": False, "has_stitch_data": False,
        }
        mock_boot.return_value = {"action": "skip"}
        mock_figma.return_value = {"action": "skip"}
        mock_stitch.return_value = {"action": "skip"}
        mock_re.return_value = {"action": "skip"}
        mock_set.return_value = {"action": "set-manifest", "returncode": 0}

        ws_out = tmp_repo / "ws.yaml"
        ws_out.write_text("workspace_state:\n  project_type: greenfield\n")

        result = mod.run_pipeline("run-003", ws_out, tmp_repo)
        assert "[Bootstrap] ui=false — skipping" in result["logs"]
        mock_boot.assert_not_called()
        mock_figma.assert_not_called()
        mock_stitch.assert_not_called()
        mock_re.assert_not_called()


# ── CLI smoke tests ────────────────────────────────────────────────────────


class TestCli:
    def test_classify_help(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "factory_project_profile.py"), "classify", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "--workspace-output" in result.stdout

    def test_run_help(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "factory_project_profile.py"), "run", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "--workspace-output" in result.stdout

    def test_reverse_engineer_ui_help(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "factory_project_profile.py"), "reverse-engineer-ui", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0

    def test_missing_command_exits_nonzero(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "factory_project_profile.py")],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
