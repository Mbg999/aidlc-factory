from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "aidlc-scripts"
INSTALL_PY = SCRIPTS / "install_aidlc.py"

# Import install_aidlc as a module for pure-function unit tests.
sys.path.insert(0, str(SCRIPTS))
import install_aidlc  # noqa: E402
sys.path.pop(0)


# ---------- parse_tools_string ----------

class TestParseToolsString:
    def test_single(self):
        assert install_aidlc.parse_tools_string("claude") == ["claude"]

    def test_multi(self):
        assert install_aidlc.parse_tools_string("claude,opencode") == ["claude", "opencode"]

    def test_whitespace_stripped(self):
        assert install_aidlc.parse_tools_string(" claude , opencode ") == ["claude", "opencode"]

    def test_dedup_preserves_order(self):
        assert install_aidlc.parse_tools_string("opencode,claude,opencode") == ["opencode", "claude"]

    def test_lowercased(self):
        assert install_aidlc.parse_tools_string("CLAUDE,OpenCode") == ["claude", "opencode"]

    def test_invalid_raises(self):
        with pytest.raises(ValueError, match="bogus"):
            install_aidlc.parse_tools_string("claude,bogus")

    def test_empty_raises(self):
        with pytest.raises(ValueError, match="No tools"):
            install_aidlc.parse_tools_string("")

    def test_only_commas_raises(self):
        with pytest.raises(ValueError, match="No tools"):
            install_aidlc.parse_tools_string(",,,")


# ---------- hallucination prevention stack constants ----------

class TestHallucinationPreventionStack:
    """Piece 3 + Piece 4 scripts must be registered in installer constants."""

    def test_factory_autoskills_in_scripts(self):
        assert "factory_autoskills.py" in install_aidlc.ORCHESTRATOR_FACTORY_SCRIPTS

    def test_factory_skill_drift_in_scripts(self):
        assert "factory_skill_drift.py" in install_aidlc.ORCHESTRATOR_FACTORY_SCRIPTS

    def test_skill_sources_in_root_configs(self):
        assert "skill-sources.yaml" in install_aidlc.ORCHESTRATOR_ROOT_CONFIGS

    def test_skill_sources_yaml_exists_in_repo(self):
        assert (REPO_ROOT / "skill-sources.yaml").exists()

    def test_factory_autoskills_source_exists(self):
        assert (REPO_ROOT / "aidlc-scripts" / "factory_autoskills.py").exists()

    def test_factory_skill_drift_source_exists(self):
        assert (REPO_ROOT / "aidlc-scripts" / "factory_skill_drift.py").exists()

    def test_factory_skill_sync_in_scripts(self):
        assert "factory_skill_sync.py" in install_aidlc.ORCHESTRATOR_FACTORY_SCRIPTS

    def test_skill_utils_in_scripts(self):
        assert "skill_utils.py" in install_aidlc.ORCHESTRATOR_FACTORY_SCRIPTS

    def test_factory_skill_sync_source_exists(self):
        assert (REPO_ROOT / "aidlc-scripts" / "factory_skill_sync.py").exists()

    def test_skill_utils_source_exists(self):
        assert (REPO_ROOT / "aidlc-scripts" / "skill_utils.py").exists()

    def test_validator_retry_skill_exists(self):
        skill_md = REPO_ROOT / ".agents" / "custom-skills" / "validator-retry" / "SKILL.md"
        assert skill_md.exists(), f"validator-retry skill not found at {skill_md}"

    def test_skill_sources_copied_on_orchestrator_install(self, tmp_path: Path):
        """skill-sources.yaml must land in the target root during orchestrator install."""
        _stub_skills(tmp_path)
        r = _run_cli(
            "--tool", "claude", "--yes", "--with-orchestrator", "--no-venv",
            "--dest", str(tmp_path),
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert (tmp_path / "skill-sources.yaml").exists(), (
            "skill-sources.yaml was not installed to target root"
        )

    def test_skill_sources_not_overwritten_without_force(self, tmp_path: Path):
        """Re-install without --force must not overwrite a customised skill-sources.yaml."""
        _stub_skills(tmp_path)
        sentinel = "# user-customised\n"
        (tmp_path / "skill-sources.yaml").write_text(sentinel)
        r = _run_cli(
            "--tool", "claude", "--yes", "--with-orchestrator", "--no-venv",
            "--dest", str(tmp_path),
        )
        assert r.returncode == 0
        assert (tmp_path / "skill-sources.yaml").read_text() == sentinel, (
            "skill-sources.yaml was overwritten without --force"
        )

    def test_skill_sources_overwritten_with_force(self, tmp_path: Path):
        """Re-install with --force must overwrite skill-sources.yaml."""
        _stub_skills(tmp_path)
        (tmp_path / "skill-sources.yaml").write_text("# old content\n")
        r = _run_cli(
            "--tool", "claude", "--yes", "--with-orchestrator", "--no-venv", "--force",
            "--dest", str(tmp_path),
        )
        assert r.returncode == 0
        content = (tmp_path / "skill-sources.yaml").read_text()
        assert content != "# old content\n", "skill-sources.yaml was NOT overwritten with --force"


# ---------- CLI integration (subprocess) ----------

def _stub_skills(target: Path) -> None:
    """Pre-populate .agents/skills/ so the script skips the network clone."""
    stub = target / ".agents" / "skills" / "_stub"
    stub.mkdir(parents=True, exist_ok=True)
    (stub / "SKILL.md").write_text("# stub\n")


def _run_cli(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(INSTALL_PY), *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
    )


class TestCli:
    def test_invalid_tool_exits_2(self, tmp_path: Path):
        r = _run_cli("--tool", "bogus", "--yes", "--dry-run", "--dest", str(tmp_path))
        assert r.returncode == 2
        assert "Unknown tool" in r.stdout



# ---------- update_workflow_doc_pointer (force upgrade) ----------

class TestUpdateWorkflowDocPointer:
    def test_append_when_marker_missing(self, tmp_path: Path):
        doc = tmp_path / "CLAUDE.md"
        doc.write_text("existing content\n")
        install_aidlc.update_workflow_doc_pointer(
            doc, "<!-- MARKER -->", "\n<!-- MARKER -->\n## NEW BLOCK\n", dry_run=False,
        )
        assert "<!-- MARKER -->" in doc.read_text()
        assert "NEW BLOCK" in doc.read_text()

    def test_skip_when_marker_present_no_force(self, tmp_path: Path):
        doc = tmp_path / "CLAUDE.md"
        doc.write_text("before\n<!-- MARKER -->\n## OLD BLOCK\nafter\n")
        install_aidlc.update_workflow_doc_pointer(
            doc, "<!-- MARKER -->", "\n<!-- MARKER -->\n## NEW BLOCK\n", dry_run=False,
        )
        text = doc.read_text()
        assert "OLD BLOCK" in text  # unchanged
        assert "NEW BLOCK" not in text

    def test_replace_when_marker_present_with_force(self, tmp_path: Path):
        doc = tmp_path / "CLAUDE.md"
        doc.write_text("before\n<!-- MARKER -->\n## OLD BLOCK\n## OTHER STUFF\nafter\n")
        install_aidlc.update_workflow_doc_pointer(
            doc, "<!-- MARKER -->", "<!-- MARKER -->\n## NEW BLOCK\n", dry_run=False, force=True,
        )
        text = doc.read_text()
        assert "OLD BLOCK" not in text  # replaced
        assert "NEW BLOCK" in text
        assert "before" in text  # preamble preserved
        # Content after the block is removed (replaced in place)
        assert "after" not in text  # old content after marker is gone

    def test_dry_run_does_not_modify(self, tmp_path: Path):
        doc = tmp_path / "CLAUDE.md"
        doc.write_text("before\n<!-- MARKER -->\n## OLD BLOCK\nafter\n")
        install_aidlc.update_workflow_doc_pointer(
            doc, "<!-- MARKER -->", "<!-- MARKER -->\n## NEW BLOCK\n", dry_run=True, force=True,
        )
        assert "OLD BLOCK" in doc.read_text()  # unchanged
        assert "NEW BLOCK" not in doc.read_text()

    def test_creates_file_when_missing(self, tmp_path: Path):
        doc = tmp_path / "CLAUDE.md"
        assert not doc.exists()
        install_aidlc.update_workflow_doc_pointer(
            doc, "<!-- MARKER -->", "<!-- MARKER -->\n## NEW BLOCK\n", dry_run=False,
        )
        assert doc.exists()
        assert "NEW BLOCK" in doc.read_text()


# ---------- update_gitignore (force upgrade) ----------

class TestUpdateGitignore:
    def test_append_when_marker_missing(self, tmp_path: Path):
        gi = tmp_path / ".gitignore"
        gi.write_text("*.pyc\n")
        install_aidlc.update_gitignore(
            tmp_path, [".aidlc-orchestrator/runs/"], "# header", dry_run=False,
        )
        text = gi.read_text()
        assert ".aidlc-orchestrator/runs/" in text

    def test_skip_when_entries_exist_no_force(self, tmp_path: Path):
        gi = tmp_path / ".gitignore"
        gi.write_text(".aidlc-orchestrator/runs/\n.aidlc-orchestrator/knowledge/\n")
        install_aidlc.update_gitignore(
            tmp_path, [".aidlc-orchestrator/runs/"], "# header", dry_run=False,
        )
        text = gi.read_text()
        assert text.count(".aidlc-orchestrator/runs/") == 1  # no duplicate

    def test_reappends_when_entries_exist_with_force(self, tmp_path: Path):
        gi = tmp_path / ".gitignore"
        gi.write_text(".aidlc-orchestrator/runs/\n")
        install_aidlc.update_gitignore(
            tmp_path, [".aidlc-orchestrator/runs/", ".aidlc-orchestrator/knowledge/"],
            "# header", dry_run=False, force=True,
        )
        text = gi.read_text()
        # With force, entries are re-appended (duplicate entry is acceptable — idempotent at runtime)
        assert text.count(".aidlc-orchestrator/runs/") >= 1
        assert ".aidlc-orchestrator/knowledge/" in text


# ---------- ensure_target_requirements ----------

class TestEnsureTargetRequirements:
    def test_seeds_from_source_when_target_missing(self, tmp_path: Path):
        repo = tmp_path / "repo"
        target = tmp_path / "target"
        repo.mkdir()
        target.mkdir()
        (repo / "requirements.txt").write_text("pyyaml>=6.0\n")
        out = install_aidlc.ensure_target_requirements(repo, target, dry_run=False)
        assert out == target / "requirements.txt"
        assert (target / "requirements.txt").read_text() == "pyyaml>=6.0\n"

    def test_preserves_existing_target(self, tmp_path: Path):
        repo = tmp_path / "repo"
        target = tmp_path / "target"
        repo.mkdir()
        target.mkdir()
        (repo / "requirements.txt").write_text("pyyaml>=6.0\n")
        (target / "requirements.txt").write_text("custom-dep==1.0\n")
        install_aidlc.ensure_target_requirements(repo, target, dry_run=False)
        # Existing target file untouched
        assert (target / "requirements.txt").read_text() == "custom-dep==1.0\n"

    def test_returns_none_when_neither_exists(self, tmp_path: Path):
        repo = tmp_path / "repo"
        target = tmp_path / "target"
        repo.mkdir()
        target.mkdir()
        assert install_aidlc.ensure_target_requirements(repo, target, dry_run=False) is None

    def test_dry_run_does_not_create(self, tmp_path: Path):
        repo = tmp_path / "repo"
        target = tmp_path / "target"
        repo.mkdir()
        target.mkdir()
        (repo / "requirements.txt").write_text("pyyaml>=6.0\n")
        out = install_aidlc.ensure_target_requirements(repo, target, dry_run=True)
        assert out == target / "requirements.txt"
        assert not (target / "requirements.txt").exists()


# ---------- venv CLI behavior ----------

class TestVenvCli:
    def test_no_venv_flag_skips_creation(self, tmp_path: Path):
        _stub_skills(tmp_path)
        r = _run_cli(
            "--tool", "claude", "--yes", "--no-orchestrator", "--no-venv",
            "--dest", str(tmp_path),
        )
        assert r.returncode == 0
        assert "Skipped Python venv setup" in r.stdout
        assert not (tmp_path / ".venv").exists()

    def test_dry_run_announces_venv_creation(self, tmp_path: Path):
        _stub_skills(tmp_path)
        r = _run_cli(
            "--tool", "claude", "--yes", "--no-orchestrator", "--dry-run",
            "--dest", str(tmp_path),
        )
        assert r.returncode == 0
        # dry-run should mention the venv path without actually creating it
        assert "Would create venv" in r.stdout or "[DRY-RUN] Would create venv" in r.stdout
        assert not (tmp_path / ".venv").exists()


# ---------- CodeGraph integration ----------

class TestCodeGraphIntegration:
    """CodeGraph integration files and installer constants."""

    def test_factory_codegraph_in_scripts(self):
        assert "factory_codegraph.py" in install_aidlc.ORCHESTRATOR_FACTORY_SCRIPTS

    def test_factory_codegraph_source_exists(self):
        assert (REPO_ROOT / "aidlc-scripts" / "factory_codegraph.py").exists()

    def test_codegraph_skill_exists(self):
        skill_md = (
            REPO_ROOT / ".agents" / "custom-skills"
            / "codegraph-aware-exploration" / "SKILL.md"
        )
        assert skill_md.exists(), f"codegraph-aware-exploration skill not found at {skill_md}"

    def test_codegraph_skill_has_valid_frontmatter(self):
        skill_md = (
            REPO_ROOT / ".agents" / "custom-skills"
            / "codegraph-aware-exploration" / "SKILL.md"
        )
        text = skill_md.read_text()
        assert text.startswith("---"), "SKILL.md must start with frontmatter"
        assert "name: codegraph-aware-exploration" in text
        assert "description:" in text

    def test_codegraph_gitignore_entry(self):
        assert ".codegraph/" in install_aidlc.ORCHESTRATOR_GITIGNORE_ENTRIES

    def test_workspace_scout_contract_has_codegraph_state(self):
        import json
        contract_path = (
            REPO_ROOT / ".aidlc-orchestrator" / "contracts"
            / "workspace-scout.output.v1.json"
        )
        schema = json.loads(contract_path.read_text())
        ws = schema["properties"]["workspace_state"]["properties"]
        assert "codegraph_state" in ws, "codegraph_state missing from workspace_state schema"
        cg = ws["codegraph_state"]["properties"]
        assert "indexed" in cg
        assert "nodes" in cg
        assert "files" in cg
        assert "backend" in cg

    def test_codegraph_dry_run_flag_accepted(self, tmp_path: Path):
        _stub_skills(tmp_path)
        r = _run_cli(
            "--tool", "claude", "--yes", "--no-orchestrator", "--no-venv",
            "--with-codegraph", "--dry-run",
            "--dest", str(tmp_path),
        )
        assert r.returncode == 0, r.stderr
        # Dry-run should mention codegraph install without actually running npm
        assert "CodeGraph" in r.stdout or "codegraph" in r.stdout.lower()

    def test_orchestrator_md_has_codegraph_section(self):
        orchestrator_md = REPO_ROOT / ".claude" / "agents" / "orchestrator.md"
        text = orchestrator_md.read_text()
        assert "CodeGraph contextualization" in text
        assert "codegraph_context" in text
        assert "MUST NOT" in text  # main-session restriction

    def test_reverse_engineer_loads_codegraph_skill(self):
        re_md = REPO_ROOT / ".claude" / "agents" / "stage" / "reverse-engineer.md"
        text = re_md.read_text()
        assert "codegraph-aware-exploration" in text

    def test_code_generator_has_preflight(self):
        cg_md = REPO_ROOT / ".claude" / "agents" / "stage" / "code-generator.md"
        text = cg_md.read_text()
        assert "Pre-flight" in text
        assert "codegraph_impact" in text
        assert "blast-radius" in text.lower() or "blast_radius" in text

    def test_build_test_agent_has_affected_step(self):
        bt_md = REPO_ROOT / ".claude" / "agents" / "stage" / "build-test-agent.md"
        text = bt_md.read_text()
        assert "Affected test detection" in text
        assert "codegraph affected" in text

    def test_all_reviewers_load_codegraph_skill(self):
        reviewer_dir = REPO_ROOT / ".claude" / "agents" / "stage"
        for name in ("reviewer-code", "reviewer-security", "reviewer-performance", "reviewer-simplifier"):
            md = reviewer_dir / f"{name}.md"
            text = md.read_text()
            assert "codegraph-aware-exploration" in text, (
                f"{name}.md does not load codegraph-aware-exploration"
            )


# ---------- _auto_init_codegraph ----------

class TestAutoInitCodeGraph:
    """Unit tests for _auto_init_codegraph()."""

    def test_skip_when_codegraph_dir_exists(self, tmp_path: Path):
        (tmp_path / ".codegraph").mkdir()
        install_aidlc._auto_init_codegraph(tmp_path, dry_run=False)

    def test_skip_when_node_too_old(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(
            install_aidlc, "_check_node_version",
            lambda m: (False, "v16.0.0"),
        )
        install_aidlc._auto_init_codegraph(tmp_path, dry_run=False)

    def test_skip_when_codegraph_not_on_path(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(
            install_aidlc, "_check_node_version",
            lambda m: (True, "v20.0.0"),
        )

        def _raise(*a, **kw):
            raise FileNotFoundError("codegraph not found")

        monkeypatch.setattr("subprocess.run", _raise)
        install_aidlc._auto_init_codegraph(tmp_path, dry_run=False)

    def test_skip_when_codegraph_returns_nonzero(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(
            install_aidlc, "_check_node_version",
            lambda m: (True, "v20.0.0"),
        )
        mock = MagicMock()
        mock.returncode = 1
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock)
        install_aidlc._auto_init_codegraph(tmp_path, dry_run=False)

    def test_dry_run_does_not_init(self, tmp_path: Path, capsys):
        with (
            patch.object(install_aidlc, "_check_node_version", return_value=(True, "v20.0.0")),
            patch("subprocess.run") as mock_run,
        ):
            mock_version = MagicMock()
            mock_version.returncode = 0
            mock_version.stdout = "1.2.3\n"
            mock_run.return_value = mock_version

            install_aidlc._auto_init_codegraph(tmp_path, dry_run=True)

        captured = capsys.readouterr()
        assert "[DRY-RUN]" in captured.out
        assert "codegraph init -i" in captured.out

    def test_init_success_runs_status(self, tmp_path: Path, capsys):
        with (
            patch.object(install_aidlc, "_check_node_version", return_value=(True, "v20.0.0")),
            patch("subprocess.run") as mock_run,
        ):
            mock_version = MagicMock()
            mock_version.returncode = 0
            mock_version.stdout = "1.2.3\n"

            mock_init = MagicMock()
            mock_init.returncode = 0

            mock_status = MagicMock()
            mock_status.returncode = 0

            mock_run.side_effect = [mock_version, mock_init, mock_status]

            install_aidlc._auto_init_codegraph(tmp_path, dry_run=False)

        captured = capsys.readouterr()
        assert "built successfully" in captured.out
        assert mock_run.call_count == 3

    def test_init_failure_shows_warning(self, tmp_path: Path, capsys):
        with (
            patch.object(install_aidlc, "_check_node_version", return_value=(True, "v20.0.0")),
            patch("subprocess.run") as mock_run,
        ):
            mock_version = MagicMock()
            mock_version.returncode = 0
            mock_version.stdout = "1.2.3\n"

            mock_init = MagicMock()
            mock_init.returncode = 1

            mock_run.side_effect = [mock_version, mock_init]

            install_aidlc._auto_init_codegraph(tmp_path, dry_run=False)

        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "exited with an error" in captured.out
        assert "Run manually" in captured.out

    def test_skip_when_subprocess_times_out(self, tmp_path: Path, monkeypatch):
        monkeypatch.setattr(
            install_aidlc, "_check_node_version",
            lambda m: (True, "v20.0.0"),
        )

        def _raise(*a, **kw):
            raise subprocess.TimeoutExpired(cmd="codegraph", timeout=10)

        monkeypatch.setattr("subprocess.run", _raise)
        install_aidlc._auto_init_codegraph(tmp_path, dry_run=False)

    def test_cli_auto_detect_does_not_crash(self, tmp_path: Path):
        _stub_skills(tmp_path)
        r = _run_cli(
            "--tool", "claude", "--yes", "--no-orchestrator", "--no-venv",
            "--dest", str(tmp_path),
        )
        assert r.returncode == 0, r.stderr


# ---------- Engram integration ----------

class TestEngramIntegration:
    """Engram setup constants and installer."""

    # --- constants ---

    def test_engram_cli_setup_has_claude(self):
        assert "claude" in install_aidlc.ENGRAM_CLI_SETUP

    def test_engram_cli_setup_claude_has_two_commands(self):
        cmds = install_aidlc.ENGRAM_CLI_SETUP["claude"]
        assert len(cmds) == 2
        assert cmds[0] == ["claude", "plugin", "marketplace", "add", "Gentleman-Programming/engram"]
        assert cmds[1] == ["claude", "plugin", "install", "engram"]

    def test_engram_cli_setup_has_opencode(self):
        assert "opencode" in install_aidlc.ENGRAM_CLI_SETUP
        assert install_aidlc.ENGRAM_CLI_SETUP["opencode"] == [["engram", "setup", "opencode"]]

    def test_engram_cli_setup_has_codex(self):
        assert "codex" in install_aidlc.ENGRAM_CLI_SETUP
        assert install_aidlc.ENGRAM_CLI_SETUP["codex"] == [["engram", "setup", "codex"]]

    def test_engram_mcp_tools_has_cursor(self):
        assert "cursor" in install_aidlc.ENGRAM_MCP_TOOLS

    def test_engram_mcp_tools_has_windsurf(self):
        assert "windsurf" in install_aidlc.ENGRAM_MCP_TOOLS

    def test_engram_mcp_entry_shape(self):
        e = install_aidlc.ENGRAM_MCP_ENTRY
        assert e["command"] == "engram"
        assert e["args"] == ["mcp"]

    # --- project config ---

    def test_install_engram_writes_project_config(self, tmp_path: Path):
        import json
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        install_aidlc.install_engram([], project_dir, dry_run=False)
        config = json.loads((project_dir / ".engram" / "project.json").read_text())
        assert config["project_name"] == "my-project"

    def test_install_engram_project_name_matches_folder(self, tmp_path: Path):
        import json
        project_dir = tmp_path / "awesome-repo"
        project_dir.mkdir()
        install_aidlc.install_engram([], project_dir, dry_run=False)
        config = json.loads((project_dir / ".engram" / "project.json").read_text())
        assert config["project_name"] == "awesome-repo"

    def test_install_engram_dry_run_no_files(self, tmp_path: Path):
        project_dir = tmp_path / "my-project"
        project_dir.mkdir()
        install_aidlc.install_engram([], project_dir, dry_run=True)
        assert not (project_dir / ".engram").exists()

    # --- MCP tools ---

    def test_install_engram_mcp_tool_writes_mcp_json(self, tmp_path: Path):
        import json
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        install_aidlc.install_engram(["cursor"], project_dir, dry_run=False)
        mcp_path = project_dir / ".mcp.json"
        assert mcp_path.exists()
        config = json.loads(mcp_path.read_text())
        assert "engram" in config["mcpServers"]
        assert config["mcpServers"]["engram"]["command"] == "engram"
        assert config["mcpServers"]["engram"]["args"] == ["mcp"]

    def test_install_engram_mcp_tool_merges_existing_mcp_json(self, tmp_path: Path):
        import json
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        mcp_path = project_dir / ".mcp.json"
        mcp_path.write_text(json.dumps({"mcpServers": {"other": {"command": "other", "args": []}}}))
        install_aidlc.install_engram(["cursor"], project_dir, dry_run=False)
        config = json.loads(mcp_path.read_text())
        assert "other" in config["mcpServers"]
        assert "engram" in config["mcpServers"]

    def test_install_engram_mcp_tool_no_duplicate(self, tmp_path: Path):
        import json
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        install_aidlc.install_engram(["windsurf"], project_dir, dry_run=False)
        install_aidlc.install_engram(["windsurf"], project_dir, dry_run=False)
        config = json.loads((project_dir / ".mcp.json").read_text())
        assert list(config["mcpServers"].keys()).count("engram") == 1

    def test_install_engram_mcp_dry_run_no_files(self, tmp_path: Path):
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        install_aidlc.install_engram(["cursor"], project_dir, dry_run=True)
        assert not (project_dir / ".mcp.json").exists()

    # --- CLI-native tools ---

    def test_install_engram_cli_tool_runs_commands(self, tmp_path: Path):
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            install_aidlc.install_engram(["opencode"], project_dir, dry_run=False)
        assert mock_run.called
        first_cmd = mock_run.call_args_list[0][0][0]
        assert first_cmd == ["engram", "setup", "opencode"]

    def test_install_engram_cli_tool_dry_run_no_subprocess(self, tmp_path: Path):
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        with patch("subprocess.run") as mock_run:
            install_aidlc.install_engram(["opencode"], project_dir, dry_run=True)
        mock_run.assert_not_called()

    def test_install_engram_cli_tool_dry_run_output(self, tmp_path: Path, capsys):
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        with patch("subprocess.run"):
            install_aidlc.install_engram(["opencode"], project_dir, dry_run=True)
        captured = capsys.readouterr()
        assert "[DRY-RUN]" in captured.out
        assert "engram setup opencode" in captured.out

    def test_install_engram_cli_tool_handles_not_found(self, tmp_path: Path, capsys):
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        with patch("subprocess.run", side_effect=FileNotFoundError("not found")):
            install_aidlc.install_engram(["opencode"], project_dir, dry_run=False)
        captured = capsys.readouterr()
        assert "WARNING" in captured.out
        assert "run manually" in captured.out

    def test_install_engram_cli_tool_handles_timeout(self, tmp_path: Path, capsys):
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="engram", timeout=60)):
            install_aidlc.install_engram(["opencode"], project_dir, dry_run=False)
        captured = capsys.readouterr()
        assert "WARNING" in captured.out

    def test_install_engram_claude_second_command_skipped_on_first_failure(self, tmp_path: Path):
        project_dir = tmp_path / "proj"
        project_dir.mkdir()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            install_aidlc.install_engram(["claude"], project_dir, dry_run=False)
        assert mock_run.call_count == 1, "second command must be skipped when first fails"

    # --- CLI flag ---

    def test_cli_with_engram_dry_run_accepted(self, tmp_path: Path):
        _stub_skills(tmp_path)
        r = _run_cli(
            "--tool", "claude", "--yes", "--no-orchestrator", "--no-venv",
            "--with-engram", "--dry-run",
            "--dest", str(tmp_path),
        )
        assert r.returncode == 0, r.stderr
        assert "Engram" in r.stdout or "engram" in r.stdout.lower()

    def test_cli_with_engram_writes_project_config(self, tmp_path: Path):
        import json
        _stub_skills(tmp_path)
        r = _run_cli(
            "--tool", "cursor", "--yes", "--no-orchestrator", "--no-venv",
            "--with-engram",
            "--dest", str(tmp_path),
        )
        assert r.returncode == 0, r.stderr
        config_path = tmp_path / ".engram" / "project.json"
        assert config_path.exists(), "project config not written"
        config = json.loads(config_path.read_text())
        assert config["project_name"] == tmp_path.name

    def test_cli_with_engram_mcp_tool_writes_mcp_json(self, tmp_path: Path):
        import json
        _stub_skills(tmp_path)
        r = _run_cli(
            "--tool", "cursor", "--yes", "--no-orchestrator", "--no-venv",
            "--with-engram",
            "--dest", str(tmp_path),
        )
        assert r.returncode == 0, r.stderr
        mcp_path = tmp_path / ".mcp.json"
        assert mcp_path.exists(), ".mcp.json not written for cursor"
        config = json.loads(mcp_path.read_text())
        assert "engram" in config.get("mcpServers", {})
