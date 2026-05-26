from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "aidlc-scripts"
sys.path.insert(0, str(SCRIPTS))
import factory_stitch_mcp as mod
sys.path.pop(0)


class TestConstants:
    def test_package_name(self):
        assert mod.STITCH_MCP_PACKAGE == "@_davideast/stitch-mcp"

    def test_node_min_major(self):
        assert isinstance(mod.NODE_MIN_MAJOR, int)
        assert mod.NODE_MIN_MAJOR >= 16

    def test_proxy_command_shape(self):
        assert "npx" in mod.STITCH_MCP_PROXY_CMD
        assert mod.STITCH_MCP_PACKAGE in " ".join(mod.STITCH_MCP_PROXY_CMD)

    def test_config_entry_has_command_and_args(self):
        entry = mod.STITCH_MCP_CONFIG_ENTRY["stitch"]
        assert entry["command"] == "npx"
        assert mod.STITCH_MCP_PACKAGE in " ".join(entry["args"])

    def test_opencode_entry_shape(self):
        entry = mod.STITCH_MCP_OPENCODE_ENTRY
        assert entry["type"] == "local"
        assert isinstance(entry["command"], list)
        assert entry["enabled"] is True

    def test_tools_list_nonempty(self):
        assert len(mod.STITCH_MCP_TOOLS) > 0
        assert "get_screen_code" in mod.STITCH_MCP_TOOLS


class TestCheckNode:
    @patch("factory_stitch_mcp.subprocess.run")
    def test_node_ok(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="v20.11.0\n", returncode=0
        )
        ok, version = mod._check_node(min_major=18)
        assert ok is True
        assert "v20.11.0" in version

    @patch("factory_stitch_mcp.subprocess.run")
    def test_node_too_old(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="v16.14.0\n", returncode=0
        )
        ok, version = mod._check_node(min_major=18)
        assert ok is False
        assert "v16.14.0" in version

    @patch("factory_stitch_mcp.subprocess.run")
    def test_node_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        ok, version = mod._check_node()
        assert ok is False
        assert version == "not found"

    @patch("factory_stitch_mcp.subprocess.run")
    def test_node_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("node", 10)
        ok, _ = mod._check_node()
        assert ok is False


class TestCheckNpx:
    @patch("factory_stitch_mcp.shutil.which")
    def test_npx_found(self, mock_which):
        mock_which.return_value = "npx"
        assert mod._check_npx() is True

    @patch("factory_stitch_mcp.shutil.which")
    def test_npx_not_found(self, mock_which):
        mock_which.return_value = None
        assert mod._check_npx() is False


class TestDoctor:
    @patch("factory_stitch_mcp._check_node", return_value=(True, "v20.11.0"))
    @patch("factory_stitch_mcp._check_npx", return_value=True)
    @patch("factory_stitch_mcp.STITCH_MCP_DOCTOR_CMD", ["echo", "ok"])
    @patch("factory_stitch_mcp.subprocess.run")
    def test_ok(self, mock_run, *_):
        mock_run.return_value = MagicMock(
            returncode=0, stdout="All good\n", stderr=""
        )
        result = mod.doctor()
        assert result["overall"] == "ok"
        assert result["node"]["ok"] is True
        assert result["stitch_mcp_package"]["ok"] is True

    @patch("factory_stitch_mcp._check_node", return_value=(True, "v20.11.0"))
    @patch("factory_stitch_mcp._check_npx", return_value=True)
    @patch("factory_stitch_mcp.STITCH_MCP_DOCTOR_CMD", ["echo", "fail"])
    @patch("factory_stitch_mcp.subprocess.run")
    def test_degraded(self, mock_run, *_):
        mock_run.return_value = MagicMock(
            returncode=1, stdout="", stderr="Something broke"
        )
        result = mod.doctor()
        assert result["overall"] == "degraded"
        assert result["stitch_mcp_package"]["ok"] is False

    @patch("factory_stitch_mcp._check_node", return_value=(False, "v16.14.0"))
    def test_unavailable_when_node_too_old(self, _):
        result = mod.doctor()
        assert result["overall"] == "unavailable"
        assert result["stitch_mcp_package"]["ok"] is False

    @patch("factory_stitch_mcp._check_node", return_value=(True, "v20.11.0"))
    @patch("factory_stitch_mcp._check_npx", return_value=False)
    def test_unavailable_when_npx_missing(self, *_):
        result = mod.doctor()
        assert result["overall"] == "unavailable"

    @patch("factory_stitch_mcp._check_node", return_value=(True, "v20.11.0"))
    @patch("factory_stitch_mcp._check_npx", return_value=True)
    @patch("factory_stitch_mcp.subprocess.run")
    def test_degraded_on_timeout(self, mock_run, *_):
        mock_run.side_effect = subprocess.TimeoutExpired("stitch-mcp", 30)
        result = mod.doctor()
        assert result["overall"] == "degraded"


class TestProxyConfig:
    def test_returns_dict(self):
        result = mod.proxy_config()
        assert isinstance(result, dict)
        assert result["package"] == mod.STITCH_MCP_PACKAGE

    def test_has_command(self):
        result = mod.proxy_config()
        assert "command" in result
        assert result["command"] == "npx"

    def test_has_env(self):
        result = mod.proxy_config()
        assert "env" in result
        assert "GOOGLE_CLOUD_PROJECT" in result["env"]

    def test_has_description(self):
        result = mod.proxy_config()
        assert isinstance(result["description"], str)
        assert len(result["description"]) > 10


class TestConfig:
    def test_default_format_json(self):
        result = mod.config()
        parsed = json.loads(result)
        assert "stitch" in parsed

    def test_opencode_format(self):
        result = mod.config(format="opencode")
        parsed = json.loads(result)
        assert parsed["type"] == "local"
        assert isinstance(parsed["command"], list)

    def test_cursor_format(self):
        result = mod.config(format="cursor")
        parsed = json.loads(result)
        assert "command" in parsed
        assert "args" in parsed

    def test_vscode_format(self):
        result = mod.config(format="vscode")
        parsed = json.loads(result)
        assert parsed["type"] == "stdio"

    def test_all_formats_are_valid_json(self):
        for fmt in ("json", "opencode", "cursor", "vscode"):
            result = mod.config(format=fmt)
            parsed = json.loads(result)
            assert isinstance(parsed, dict), f"Failed for format={fmt}"


class TestCli:
    def test_doctor_help(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "factory_stitch_mcp.py"), "doctor", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "doctor" in result.stdout
        assert "--json" in result.stdout

    def test_proxy_config_help(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "factory_stitch_mcp.py"), "proxy-config", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0

    def test_config_help(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "factory_stitch_mcp.py"), "config", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0

    def test_config_json(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "factory_stitch_mcp.py"), "config", "--format", "json"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        parsed = json.loads(result.stdout)
        assert "stitch" in parsed

    def test_proxy_config_output(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "factory_stitch_mcp.py"), "proxy-config"],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0
        parsed = json.loads(result.stdout)
        assert parsed["package"] == "@_davideast/stitch-mcp"

    def test_missing_command_exits_nonzero(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "factory_stitch_mcp.py")],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0
