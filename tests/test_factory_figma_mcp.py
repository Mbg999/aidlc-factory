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
import factory_figma_mcp as mod
sys.path.pop(0)


class TestConstants:
    def test_remote_url(self):
        assert mod.FIGMA_MCP_REMOTE_URL == "https://mcp.figma.com/mcp"

    def test_community_package(self):
        assert mod.FIGMA_MCP_COMMUNITY_PACKAGE == "figma-mcp"

    def test_node_min_major(self):
        assert isinstance(mod.NODE_MIN_MAJOR, int)
        assert mod.NODE_MIN_MAJOR >= 16

    def test_remote_config_entry_has_type_http(self):
        entry = mod.FIGMA_MCP_REMOTE_CONFIG_ENTRY["figma"]
        assert entry["type"] == "http"
        assert "url" in entry

    def test_community_config_entry_has_command(self):
        entry = mod.FIGMA_MCP_COMMUNITY_CONFIG_ENTRY["figma"]
        assert "command" in entry
        assert entry["command"] == "npx"

    def test_tools_list_nonempty(self):
        assert len(mod.FIGMA_MCP_TOOLS) > 0
        assert "get_design_context" in mod.FIGMA_MCP_TOOLS

    def test_opencode_remote_entry_shape(self):
        entry = mod.FIGMA_MCP_OPENCODE_REMOTE_ENTRY
        assert entry["type"] == "http"
        assert entry["enabled"] is True

    def test_opencode_community_entry_shape(self):
        entry = mod.FIGMA_MCP_OPENCODE_COMMUNITY_ENTRY
        assert entry["type"] == "local"
        assert isinstance(entry["command"], list)
        assert "FIGMA_API_KEY" in entry["environment"]


class TestCheckNode:
    @patch("factory_figma_mcp.subprocess.run")
    def test_node_ok(self, mock_run):
        mock_run.return_value = MagicMock(stdout="v20.11.0\n", returncode=0)
        ok, version = mod._check_node(min_major=18)
        assert ok is True
        assert "v20.11.0" in version

    @patch("factory_figma_mcp.subprocess.run")
    def test_node_too_old(self, mock_run):
        mock_run.return_value = MagicMock(stdout="v16.14.0\n", returncode=0)
        ok, _ = mod._check_node(min_major=18)
        assert ok is False

    @patch("factory_figma_mcp.subprocess.run")
    def test_node_not_found(self, mock_run):
        mock_run.side_effect = FileNotFoundError()
        ok, version = mod._check_node()
        assert ok is False
        assert version == "not found"

    @patch("factory_figma_mcp.subprocess.run")
    def test_node_timeout(self, mock_run):
        mock_run.side_effect = subprocess.TimeoutExpired("node", 10)
        ok, _ = mod._check_node()
        assert ok is False


class TestCheckNpx:
    @patch("factory_figma_mcp.shutil.which")
    def test_npx_found(self, mock_which):
        mock_which.return_value = "/usr/local/bin/npx"
        assert mod._check_npx() is True

    @patch("factory_figma_mcp.shutil.which")
    def test_npx_not_found(self, mock_which):
        mock_which.return_value = None
        assert mod._check_npx() is False


class TestDoctor:
    @patch("factory_figma_mcp._check_node", return_value=(True, "v20.11.0"))
    @patch("factory_figma_mcp._check_npx", return_value=True)
    @patch("factory_figma_mcp.shutil.which", return_value="/usr/bin/curl")
    @patch("factory_figma_mcp.subprocess.run")
    def test_remote_mode_ok(self, mock_run, *_):
        mock_run.return_value = MagicMock(stdout="200\n", returncode=0)
        result = mod.doctor(mode="remote")
        assert result["overall"] == "ok"
        assert result["endpoint"]["ok"] is True

    @patch("factory_figma_mcp._check_node", return_value=(True, "v20.11.0"))
    @patch("factory_figma_mcp._check_npx", return_value=True)
    @patch("factory_figma_mcp.shutil.which", return_value="/usr/bin/curl")
    @patch("factory_figma_mcp.subprocess.run")
    def test_remote_mode_405_is_degraded(self, mock_run, *_):
        mock_run.return_value = MagicMock(stdout="405\n", returncode=0)
        result = mod.doctor(mode="remote")
        assert result["overall"] == "degraded"
        assert result["endpoint"]["ok"] is False

    @patch("factory_figma_mcp._check_node", return_value=(True, "v20.11.0"))
    @patch("factory_figma_mcp._check_npx", return_value=True)
    @patch("factory_figma_mcp.subprocess.run")
    def test_community_mode_ok(self, mock_run, *_):
        mock_run.return_value = MagicMock(stdout="0.1.4\n", returncode=0)
        result = mod.doctor(mode="community")
        assert result["overall"] == "ok"
        assert result["package"]["ok"] is True

    @patch("factory_figma_mcp._check_node", return_value=(True, "v20.11.0"))
    @patch("factory_figma_mcp._check_npx", return_value=True)
    @patch("factory_figma_mcp.subprocess.run")
    def test_community_mode_degraded(self, mock_run, *_):
        mock_run.return_value = MagicMock(stdout="", stderr="error", returncode=1)
        result = mod.doctor(mode="community")
        assert result["overall"] == "degraded"
        assert result["package"]["ok"] is False

    @patch("factory_figma_mcp._check_node", return_value=(False, "v16.14.0"))
    def test_unavailable_when_node_too_old(self, _):
        result = mod.doctor()
        assert result["overall"] == "unavailable"

    @patch("factory_figma_mcp._check_node", return_value=(True, "v20.11.0"))
    @patch("factory_figma_mcp._check_npx", return_value=True)
    @patch("factory_figma_mcp.shutil.which", return_value=None)
    def test_remote_mode_no_curl_is_degraded(self, *_):
        result = mod.doctor(mode="remote")
        assert result["overall"] == "degraded"
        assert "curl" in result["endpoint"]["message"]

    @patch("factory_figma_mcp._check_node", return_value=(True, "v20.11.0"))
    @patch("factory_figma_mcp._check_npx", return_value=True)
    @patch("factory_figma_mcp.subprocess.run")
    def test_auto_mode_tries_remote_then_community(self, mock_run, *_):
        mock_run.return_value = MagicMock(stdout="200\n", returncode=0)
        result = mod.doctor(mode="auto")
        assert result["overall"] == "ok"

    @patch("factory_figma_mcp._check_node", return_value=(True, "v20.11.0"))
    @patch("factory_figma_mcp._check_npx", return_value=True)
    @patch("factory_figma_mcp.shutil.which", return_value="/usr/bin/curl")
    @patch("factory_figma_mcp.subprocess.run")
    def test_auto_mode_fallback_to_community(self, mock_run, *_):
        mock_run.return_value = MagicMock(stdout="500\n", returncode=0)
        result = mod.doctor(mode="remote")
        assert result["overall"] == "degraded"


class TestProxyConfig:
    def test_returns_dict_with_keys(self):
        result = mod.proxy_config()
        assert isinstance(result, dict)
        assert "remote" in result
        assert "community" in result

    def test_remote_has_url(self):
        result = mod.proxy_config()
        assert result["remote"]["url"] == "https://mcp.figma.com/mcp"

    def test_remote_has_auth(self):
        result = mod.proxy_config()
        assert "OAuth" in result["remote"]["auth"]

    def test_community_has_package(self):
        result = mod.proxy_config()
        assert result["community"]["package"] == "figma-mcp"

    def test_community_has_env(self):
        result = mod.proxy_config()
        assert "FIGMA_API_KEY" in result["community"]["env"]

    def test_both_have_descriptions(self):
        result = mod.proxy_config()
        assert isinstance(result["remote"]["description"], str)
        assert isinstance(result["community"]["description"], str)
        assert len(result["remote"]["description"]) > 10
        assert len(result["community"]["description"]) > 10


class TestConfig:
    @pytest.mark.parametrize("fmt", ("json", "opencode", "cursor", "vscode"))
    def test_remote_mode_all_formats_valid_json(self, fmt):
        result = mod.config(format=fmt, mode="remote")
        parsed = json.loads(result)
        assert isinstance(parsed, dict), f"Failed for remote mode format={fmt}"

    @pytest.mark.parametrize("fmt", ("json", "opencode", "cursor", "vscode"))
    def test_community_mode_all_formats_valid_json(self, fmt):
        result = mod.config(format=fmt, mode="community")
        parsed = json.loads(result)
        assert isinstance(parsed, dict), f"Failed for community mode format={fmt}"

    def test_default_remote_json(self):
        result = mod.config()
        parsed = json.loads(result)
        assert "figma" in parsed
        assert parsed["figma"]["type"] == "http"

    def test_remote_opencode(self):
        result = mod.config(format="opencode")
        parsed = json.loads(result)
        assert parsed["type"] == "http"

    def test_remote_vscode_falls_back_to_stdio(self):
        """VS Code doesn't support HTTP transport; should fall back to stdio."""
        result = mod.config(format="vscode", mode="remote")
        parsed = json.loads(result)
        assert parsed["type"] == "stdio"

    def test_community_json(self):
        result = mod.config(mode="community")
        parsed = json.loads(result)
        assert "figma" in parsed
        assert parsed["figma"]["command"] == "npx"

    def test_community_opencode(self):
        result = mod.config(format="opencode", mode="community")
        parsed = json.loads(result)
        assert parsed["type"] == "local"
        assert isinstance(parsed["command"], list)

    def test_community_cursor(self):
        result = mod.config(format="cursor", mode="community")
        parsed = json.loads(result)
        assert "command" in parsed

    def test_remote_cursor(self):
        result = mod.config(format="cursor", mode="remote")
        parsed = json.loads(result)
        assert parsed["type"] == "http"


class TestCli:
    def test_doctor_help(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "factory_figma_mcp.py"), "doctor", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        assert "doctor" in result.stdout
        assert "--json" in result.stdout
        assert "--mode" in result.stdout

    def test_proxy_config_help(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "factory_figma_mcp.py"), "proxy-config", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0

    def test_config_help(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "factory_figma_mcp.py"), "config", "--help"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0

    def test_config_json(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "factory_figma_mcp.py"), "config"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        parsed = json.loads(result.stdout)
        assert "figma" in parsed

    def test_config_community(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "factory_figma_mcp.py"), "config",
             "--mode", "community", "--format", "opencode"],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode == 0
        parsed = json.loads(result.stdout)
        assert parsed["type"] == "local"

    def test_proxy_config_output(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "factory_figma_mcp.py"), "proxy-config"],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0
        parsed = json.loads(result.stdout)
        assert "remote" in parsed
        assert "community" in parsed

    def test_missing_command_exits_nonzero(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "factory_figma_mcp.py")],
            capture_output=True, text=True, timeout=10,
        )
        assert result.returncode != 0

    def test_doctor_remote_json(self):
        result = subprocess.run(
            [sys.executable, str(SCRIPTS / "factory_figma_mcp.py"),
             "doctor", "--mode", "remote", "--json"],
            capture_output=True, text=True, timeout=15,
        )
        assert result.returncode == 0
        parsed = json.loads(result.stdout)
        assert "overall" in parsed
        assert "mode" in parsed
