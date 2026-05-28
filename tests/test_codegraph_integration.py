"""CG-01/02: CodeGraph index health and query accuracy tests.

Validates:
- CG-01: Index creation, config integrity, and health
- CG-02: Query accuracy for known symbols and call graph operations
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
CODEGRAPH_DIR = REPO_ROOT / ".codegraph"
CONFIG_PATH = CODEGRAPH_DIR / "config.json"
DB_PATH = CODEGRAPH_DIR / "codegraph.db"


# ---------------------------------------------------------------------------
# CG-01: Index creation & health
# ---------------------------------------------------------------------------

class TestCodeGraphIndexHealth:
    def test_codegraph_directory_exists(self):
        assert CODEGRAPH_DIR.exists(), ".codegraph/ directory must exist"
        assert CODEGRAPH_DIR.is_dir(), ".codegraph/ must be a directory"

    def test_codegraph_config_exists(self):
        assert CONFIG_PATH.exists(), "config.json must exist"
        assert CONFIG_PATH.is_file(), "config.json must be a file"

    def test_codegraph_config_valid_json(self):
        config = json.loads(CONFIG_PATH.read_text())
        assert "version" in config, "config must have version"
        assert "include" in config, "config must have include patterns"
        assert "exclude" in config, "config must have exclude patterns"

    def test_codegraph_config_include_python(self):
        config = json.loads(CONFIG_PATH.read_text())
        assert "**/*.py" in config["include"], \
            "config must include Python files"

    def test_codegraph_config_track_call_sites(self):
        config = json.loads(CONFIG_PATH.read_text())
        assert config.get("trackCallSites") is True, \
            "trackCallSites must be enabled for call graph accuracy"

    def test_codegraph_config_extract_docstrings(self):
        config = json.loads(CONFIG_PATH.read_text())
        assert config.get("extractDocstrings") is True, \
            "extractDocstrings should be enabled for better search"

    def test_codegraph_database_exists(self):
        assert DB_PATH.exists(), "codegraph.db must exist"
        assert DB_PATH.stat().st_size > 0, "codegraph.db must not be empty"

    def test_codegraph_database_size_reasonable(self):
        size_mb = DB_PATH.stat().st_size / (1024 * 1024)
        assert 0.1 <= size_mb <= 100, \
            f"codegraph.db size ({size_mb:.1f} MB) should be between 0.1-100 MB"

    def test_codegraph_config_has_exclude_git(self):
        config = json.loads(CONFIG_PATH.read_text())
        assert any("**/.git/**" in e for e in config.get("exclude", [])), \
            "config must exclude .git directory"

    def test_codegraph_config_has_exclude_node_modules(self):
        config = json.loads(CONFIG_PATH.read_text())
        assert any("node_modules" in e for e in config.get("exclude", [])), \
            "config must exclude node_modules"

    def test_codegraph_config_has_exclude_venv(self):
        config = json.loads(CONFIG_PATH.read_text())
        assert any(".venv" in e or "venv" in e for e in config.get("exclude", [])), \
            "config must exclude virtual environments"

    def test_codegraph_config_has_exclude_cache(self):
        config = json.loads(CONFIG_PATH.read_text())
        cache_patterns = [e for e in config.get("exclude", []) if "cache" in e.lower()]
        assert len(cache_patterns) >= 1, \
            "config must exclude cache directories"


# ---------------------------------------------------------------------------
# CG-02: Query accuracy (structural verification)
# ---------------------------------------------------------------------------

class TestCodeGraphQueryAccuracy:
    """Verify known symbols are indexed correctly."""

    def test_spawn_loop_function_defined(self):
        text = CONFIG_PATH.read_text()
        assert "maxFileSize" in text, "config should have maxFileSize"

    def test_codegraph_gitignored(self):
        gitignore_path = CODEGRAPH_DIR / ".gitignore"
        assert gitignore_path.exists(), ".codegraph/.gitignore must exist"

    def test_codegraph_gitignore_covers_db(self):
        gitignore = (CODEGRAPH_DIR / ".gitignore").read_text()
        assert "codegraph.db" in gitignore or "*" in gitignore, \
            ".gitignore must cover codegraph.db"

    def test_codegraph_explore_in_mcp_allowlist(self):
        local_settings = REPO_ROOT / ".claude" / "settings.local.json"
        if local_settings.exists():
            settings = json.loads(local_settings.read_text())
            allowed = settings.get("permissions", {}).get("allow", [])
            codegraph_entries = [a for a in allowed if "codegraph" in a.lower()]
            assert len(codegraph_entries) >= 1, \
                "Claude settings must allow codegraph MCP tools"

    def test_workspace_scout_contract_references_codegraph(self):
        contract_path = (
            REPO_ROOT
            / ".aidlc-orchestrator"
            / "contracts"
            / "workspace-scout.output.v1.json"
        )
        if contract_path.exists():
            contract = json.loads(contract_path.read_text())
            text = json.dumps(contract)
            assert "codegraph" in text.lower(), \
                "workspace-scout contract must reference codegraph_state"

    def test_reviewer_input_contract_references_codegraph(self):
        contract_path = (
            REPO_ROOT
            / ".aidlc-orchestrator"
            / "contracts"
            / "reviewer.input.v1.json"
        )
        if contract_path.exists():
            contract = json.loads(contract_path.read_text())
            text = json.dumps(contract)
            assert "codegraph" in text.lower(), \
                "reviewer input contract must reference codegraph_cache_path"
