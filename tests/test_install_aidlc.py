from __future__ import annotations

import json
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

    def test_codex_accepted(self):
        assert install_aidlc.parse_tools_string("codex,claude") == ["codex", "claude"]

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

    def test_factory_custom_skills_in_scripts(self):
        assert "factory_custom_skills.py" in install_aidlc.ORCHESTRATOR_FACTORY_SCRIPTS

    def test_factory_skill_drift_in_scripts(self):
        assert "factory_skill_drift.py" in install_aidlc.ORCHESTRATOR_FACTORY_SCRIPTS

    def test_skill_sources_in_root_configs(self):
        assert "skill-sources.yaml" in install_aidlc.ORCHESTRATOR_ROOT_CONFIGS

    def test_skill_sources_yaml_exists_in_repo(self):
        assert (REPO_ROOT / "skill-sources.yaml").exists()

    def test_factory_custom_skills_source_exists(self):
        assert (REPO_ROOT / "aidlc-scripts" / "factory_custom_skills.py").exists()

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
            "--tool", "claude", "--yes", "--no-venv",
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
            "--tool", "claude", "--yes", "--no-venv",
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
            "--tool", "claude", "--yes", "--no-venv", "--force",
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
        [sys.executable, str(INSTALL_PY), "--skip-preflight", *args],
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
            "--tool", "claude", "--yes", "--no-venv",
            "--dest", str(tmp_path),
        )
        assert r.returncode == 0
        assert "Skipped Python venv setup" in r.stdout
        assert not (tmp_path / ".venv").exists()

    def test_dry_run_announces_venv_creation(self, tmp_path: Path):
        _stub_skills(tmp_path)
        r = _run_cli(
            "--tool", "claude", "--yes", "--dry-run",
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
            "--tool", "claude", "--yes", "--no-venv",
            "--dry-run",
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
            "--tool", "claude", "--yes", "--no-venv",
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

    def test_engram_mcp_tools_has_cursor(self):
        assert "cursor" in install_aidlc.ENGRAM_MCP_TOOLS

    def test_engram_mcp_tools_has_copilot(self):
        assert "copilot" in install_aidlc.ENGRAM_MCP_TOOLS

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
        install_aidlc.install_engram(["cursor"], project_dir, dry_run=False)
        install_aidlc.install_engram(["cursor"], project_dir, dry_run=False)
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
            "--tool", "claude", "--yes", "--no-venv",
            "--dry-run",
            "--dest", str(tmp_path),
        )
        assert r.returncode == 0, r.stderr
        assert "Engram" in r.stdout or "engram" in r.stdout.lower()

    def test_cli_with_engram_writes_project_config(self, tmp_path: Path):
        import json
        _stub_skills(tmp_path)
        r = _run_cli(
            "--tool", "cursor", "--yes", "--no-venv",
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
            "--tool", "cursor", "--yes", "--no-venv",
            "--dest", str(tmp_path),
        )
        assert r.returncode == 0, r.stderr
        mcp_path = tmp_path / ".mcp.json"
        assert mcp_path.exists(), ".mcp.json not written for cursor"
        config = json.loads(mcp_path.read_text())
        assert "engram" in config.get("mcpServers", {})


# ---------- _apply_mcp_config ----------

class TestApplyMCPConfig:
    def test_adds_stitch_and_figma_when_opted_in(self, tmp_path: Path):
        cfg = tmp_path / ".mcp.json"
        cfg.write_text(json.dumps({
            "mcpServers": {
                "context7": {"command": "npx", "args": ["-y", "context7"]},
            }
        }))
        install_aidlc._apply_mcp_config(cfg, tool="claude", with_stitch=True, with_figma=True, dry_run=False)
        data = json.loads(cfg.read_text())
        assert "stitch" in data["mcpServers"]
        assert "figma" in data["mcpServers"]
        assert "context7" in data["mcpServers"]

    def test_adds_only_stitch_when_only_stitch_opted(self, tmp_path: Path):
        cfg = tmp_path / ".mcp.json"
        cfg.write_text(json.dumps({"mcpServers": {}}))
        install_aidlc._apply_mcp_config(cfg, tool="claude", with_stitch=True, with_figma=False, dry_run=False)
        data = json.loads(cfg.read_text())
        assert "stitch" in data["mcpServers"]
        assert "figma" not in data["mcpServers"]

    def test_adds_only_figma_when_only_figma_opted(self, tmp_path: Path):
        cfg = tmp_path / ".mcp.json"
        cfg.write_text(json.dumps({"mcpServers": {}}))
        install_aidlc._apply_mcp_config(cfg, tool="claude", with_stitch=False, with_figma=True, dry_run=False)
        data = json.loads(cfg.read_text())
        assert "figma" in data["mcpServers"]
        assert "stitch" not in data["mcpServers"]

    def test_adds_nothing_when_both_skipped(self, tmp_path: Path):
        cfg = tmp_path / ".mcp.json"
        cfg.write_text(json.dumps({"mcpServers": {}}))
        install_aidlc._apply_mcp_config(cfg, tool="claude", with_stitch=False, with_figma=False, dry_run=False)
        data = json.loads(cfg.read_text())
        assert "stitch" not in data["mcpServers"]
        assert "figma" not in data["mcpServers"]

    def test_adds_opencode_format_correctly(self, tmp_path: Path):
        cfg = tmp_path / "opencode.json"
        cfg.write_text(json.dumps({"mcp": {}}))
        install_aidlc._apply_mcp_config(cfg, tool="opencode", with_stitch=False, with_figma=True, dry_run=False)
        data = json.loads(cfg.read_text())
        assert "figma" in data["mcp"]
        assert data["mcp"]["figma"]["enabled"] is True

    def test_adds_vscode_format_correctly(self, tmp_path: Path):
        cfg = tmp_path / ".vscode" / "mcp.json"
        cfg.parent.mkdir(parents=True)
        cfg.write_text(json.dumps({"servers": {}}))
        install_aidlc._apply_mcp_config(cfg, tool="copilot", with_stitch=True, with_figma=False, dry_run=False)
        data = json.loads(cfg.read_text())
        assert "stitch" in data["servers"]

    def test_dry_run_does_not_modify(self, tmp_path: Path):
        cfg = tmp_path / ".mcp.json"
        original = {"mcpServers": {}}
        cfg.write_text(json.dumps(original))
        install_aidlc._apply_mcp_config(cfg, tool="claude", with_stitch=True, with_figma=True, dry_run=True)
        data = json.loads(cfg.read_text())
        assert data == original

    def test_noop_when_file_missing(self, tmp_path: Path):
        cfg = tmp_path / "nope.json"
        install_aidlc._apply_mcp_config(cfg, tool="claude", with_stitch=False, with_figma=False, dry_run=False)

    def test_noop_when_invalid_json(self, tmp_path: Path):
        cfg = tmp_path / ".mcp.json"
        cfg.write_text("{invalid")
        install_aidlc._apply_mcp_config(cfg, tool="claude", with_stitch=False, with_figma=False, dry_run=False)

    def test_preserves_config_when_no_servers_key(self, tmp_path: Path):
        cfg = tmp_path / ".mcp.json"
        cfg.write_text(json.dumps({"version": 1}))
        install_aidlc._apply_mcp_config(cfg, tool="claude", with_stitch=True, with_figma=True, dry_run=False)
        data = json.loads(cfg.read_text())
        assert data == {"version": 1}


# ---------- _venv_python (cross-platform venv executable detection) ----------

class TestVenvPythonDetection:
    def test_unix_bin_python(self, tmp_path: Path):
        venv = tmp_path / ".venv"
        py = venv / "bin" / "python"
        py.parent.mkdir(parents=True)
        py.touch()
        assert install_aidlc._venv_python(venv) == py

    def test_unix_bin_python3(self, tmp_path: Path):
        venv = tmp_path / ".venv"
        py = venv / "bin" / "python3"
        py.parent.mkdir(parents=True)
        py.touch()
        assert install_aidlc._venv_python(venv) == py

    def test_windows_scripts_python_exe(self, tmp_path: Path):
        venv = tmp_path / ".venv"
        py = venv / "Scripts" / "python.exe"
        py.parent.mkdir(parents=True)
        py.touch()
        assert install_aidlc._venv_python(venv) == py

    def test_windows_scripts_python3_exe(self, tmp_path: Path):
        venv = tmp_path / ".venv"
        py = venv / "Scripts" / "python3.exe"
        py.parent.mkdir(parents=True)
        py.touch()
        assert install_aidlc._venv_python(venv) == py

    def test_returns_none_when_not_found(self, tmp_path: Path):
        venv = tmp_path / ".venv"
        venv.mkdir()
        assert install_aidlc._venv_python(venv) is None

    def test_unix_preferred_over_windows(self, tmp_path: Path):
        """bin/python takes precedence over Scripts/python.exe."""
        venv = tmp_path / ".venv"
        unix_py = venv / "bin" / "python"
        win_py = venv / "Scripts" / "python.exe"
        for p in (unix_py, win_py):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.touch()
        assert install_aidlc._venv_python(venv) == unix_py

    def test_bin_python3_preferred_over_scripts(self, tmp_path: Path):
        """bin/python3 takes precedence over Scripts/python.exe."""
        venv = tmp_path / ".venv"
        unix_py3 = venv / "bin" / "python3"
        win_py = venv / "Scripts" / "python.exe"
        for p in (unix_py3, win_py):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.touch()
        assert install_aidlc._venv_python(venv) == unix_py3


# ---------- _is_windows ----------

class TestIsWindows:
    def test_returns_bool(self):
        assert isinstance(install_aidlc._is_windows(), bool)

    def test_true_when_platform_is_windows(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "win32")
        monkeypatch.setattr(install_aidlc._platform, "system", lambda: "Windows")
        assert install_aidlc._is_windows() is True

    def test_true_when_msys(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "msys")
        monkeypatch.setattr(install_aidlc._platform, "system", lambda: "MSYS_NT-10.0-19045")
        assert install_aidlc._is_windows() is True

    def test_true_when_mingw(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "win32")
        monkeypatch.setattr(install_aidlc._platform, "system", lambda: "MINGW64_NT-10.0-19045")
        assert install_aidlc._is_windows() is True

    def test_true_when_cygwin(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "cygwin")
        monkeypatch.setattr(install_aidlc._platform, "system", lambda: "CYGWIN_NT-10.0-19045")
        assert install_aidlc._is_windows() is True

    def test_false_on_macos(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "darwin")
        monkeypatch.setattr(install_aidlc._platform, "system", lambda: "Darwin")
        assert install_aidlc._is_windows() is False

    def test_false_on_linux(self, monkeypatch):
        monkeypatch.setattr("sys.platform", "linux")
        monkeypatch.setattr(install_aidlc._platform, "system", lambda: "Linux")
        assert install_aidlc._is_windows() is False


# ---------- update_gitignore — force preserves existing content ----------

class TestUpdateGitignoreForcePreservesContent:
    def test_force_does_not_overwrite_existing_lines(self, tmp_path: Path):
        gi = tmp_path / ".gitignore"
        gi.write_text("*.pyc\n__pycache__/\n")
        install_aidlc.update_gitignore(
            tmp_path, [".aidlc-orchestrator/runs/"], "# AIDLC", dry_run=False, force=True,
        )
        text = gi.read_text()
        assert "*.pyc" in text
        assert "__pycache__/" in text
        assert ".aidlc-orchestrator/runs/" in text

    def test_new_file_has_no_leading_blank_line(self, tmp_path: Path):
        gi = tmp_path / ".gitignore"
        install_aidlc.update_gitignore(
            tmp_path, [".aidlc-orchestrator/runs/"], "# AIDLC", dry_run=False,
        )
        text = gi.read_text()
        assert not text.startswith("\n"), "new .gitignore must not start with a blank line"
        assert ".aidlc-orchestrator/runs/" in text

    def test_force_new_file_no_leading_blank_line(self, tmp_path: Path):
        gi = tmp_path / ".gitignore"
        install_aidlc.update_gitignore(
            tmp_path, [".aidlc-orchestrator/runs/"], "# AIDLC", dry_run=False, force=True,
        )
        text = gi.read_text()
        assert not text.startswith("\n")
        assert ".aidlc-orchestrator/runs/" in text

    def test_force_existing_file_has_separator_blank_line(self, tmp_path: Path):
        """A blank line should separate existing content from the new AIDLC block."""
        gi = tmp_path / ".gitignore"
        gi.write_text("*.log\n")
        install_aidlc.update_gitignore(
            tmp_path, [".aidlc-orchestrator/runs/"], "# AIDLC", dry_run=False, force=True,
        )
        text = gi.read_text()
        assert "\n\n" in text, "expected blank separator line between sections"


# ---------- Windows python_cmds ----------

class TestWindowsPythonCmds:
    def test_windows_includes_py_launcher(self, monkeypatch):
        monkeypatch.setattr(install_aidlc, "_is_windows", lambda: True)
        called: list[str] = []

        def fake_run(cmd, **kwargs):
            called.append(cmd[0])
            if cmd[0] == "py":
                import types
                r = types.SimpleNamespace(returncode=0)
                return r
            raise FileNotFoundError("not found")

        venv_path = Path("/fake/.venv")
        fake_py = venv_path / "Scripts" / "python.exe"
        monkeypatch.setattr(install_aidlc, "_venv_python", lambda p: fake_py)

        import types
        fake_venv_py = types.SimpleNamespace(returncode=0)

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                types.SimpleNamespace(returncode=0),  # venv creation (py -m venv)
                types.SimpleNamespace(returncode=0),  # pip upgrade
                types.SimpleNamespace(returncode=0),  # pip install -r
            ]
            try:
                install_aidlc.create_venv_and_install_requirements(
                    Path("/fake"), Path("/fake/requirements.txt"), dry_run=False,
                )
            except Exception:
                pass

        first_cmd = mock_run.call_args_list[0][0][0]
        assert first_cmd[0] == "py", f"Expected 'py' as first venv cmd on Windows, got {first_cmd[0]!r}"

    def test_non_windows_starts_with_python3(self, monkeypatch):
        monkeypatch.setattr(install_aidlc, "_is_windows", lambda: False)

        import types
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = [
                types.SimpleNamespace(returncode=0),
                types.SimpleNamespace(returncode=0),
                types.SimpleNamespace(returncode=0),
            ]
            monkeypatch.setattr(install_aidlc, "_venv_python", lambda p: p / "bin" / "python")
            try:
                install_aidlc.create_venv_and_install_requirements(
                    Path("/fake"), Path("/fake/requirements.txt"), dry_run=False,
                )
            except Exception:
                pass

        first_cmd = mock_run.call_args_list[0][0][0]
        assert first_cmd[0] == "python3", (
            f"Expected 'python3' as first venv cmd on non-Windows, got {first_cmd[0]!r}"
        )


# ---------- _probe_version (Windows cmd /c fallback) ----------

class TestProbeVersion:
    """Unit tests for _probe_version() — especially the Windows cmd /c / pwsh fallback."""

    def test_successful_probe(self):
        ok, ver = install_aidlc._probe_version([sys.executable, "--version"])
        assert ok
        assert "Python" in ver

    def test_non_zero_returncode(self, monkeypatch):
        mock = MagicMock()
        mock.returncode = 1
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock)
        ok, ver = install_aidlc._probe_version(["some-cmd", "--version"])
        assert not ok
        assert ver == "not found"

    def test_timeout_expired(self, monkeypatch):
        monkeypatch.setattr(install_aidlc, "_is_windows", lambda: False)

        def _raise(*a, **kw):
            raise subprocess.TimeoutExpired(cmd="some-cmd", timeout=10)
        monkeypatch.setattr("subprocess.run", _raise)
        ok, ver = install_aidlc._probe_version(["some-cmd", "--version"])
        assert not ok
        assert ver == "not found"

    def test_file_not_found_on_unix_no_fallback(self, monkeypatch):
        monkeypatch.setattr(install_aidlc, "_is_windows", lambda: False)

        def _raise(*a, **kw):
            raise FileNotFoundError("not found")
        monkeypatch.setattr("subprocess.run", _raise)
        ok, ver = install_aidlc._probe_version(["npm", "--version"])
        assert not ok
        assert ver == "not found"

    def test_cmd_c_succeeds_first_on_windows(self, monkeypatch):
        """On Windows, cmd /c is tried first — succeed immediately."""
        monkeypatch.setattr(install_aidlc, "_is_windows", lambda: True)

        calls = []

        def _run(cmd, **kw):
            calls.append(cmd)
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = "11.4.2\n"
            return mock

        monkeypatch.setattr("subprocess.run", _run)
        ok, ver = install_aidlc._probe_version(["npm", "--version"])
        assert ok
        assert ver == "11.4.2"
        assert len(calls) == 1
        assert calls[0] == ["cmd", "/c", "npm", "--version"]

    def test_cmd_c_fails_falls_back_to_powershell(self, monkeypatch):
        """When cmd /c fails, PowerShell is tried next."""
        monkeypatch.setattr(install_aidlc, "_is_windows", lambda: True)

        calls = []

        def _run(cmd, **kw):
            calls.append(cmd)
            if len(calls) == 1:
                raise FileNotFoundError("cmd /c not found")
            # Second call is PowerShell — succeed
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = "11.4.2\n"
            return mock

        monkeypatch.setattr("subprocess.run", _run)
        ok, ver = install_aidlc._probe_version(["npm", "--version"])
        assert ok
        assert ver == "11.4.2"
        assert len(calls) == 2
        assert calls[0] == ["cmd", "/c", "npm", "--version"]
        assert "powershell" in calls[1][0].lower()
        assert "npm --version" in " ".join(calls[1])

    def test_cmd_c_and_powershell_fail_falls_back_to_direct(self, monkeypatch):
        """When cmd /c and PowerShell both fail, raw subprocess is tried last."""
        monkeypatch.setattr(install_aidlc, "_is_windows", lambda: True)

        calls = []

        def _run(cmd, **kw):
            calls.append(cmd)
            if len(calls) <= 2:
                raise FileNotFoundError("not found")
            # Third call is raw subprocess — succeed
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = "11.4.2\n"
            return mock

        monkeypatch.setattr("subprocess.run", _run)
        ok, ver = install_aidlc._probe_version(["npm", "--version"])
        assert ok
        assert ver == "11.4.2"
        assert len(calls) == 3
        assert calls[0] == ["cmd", "/c", "npm", "--version"]
        assert "powershell" in calls[1][0].lower()
        assert calls[2] == ["npm", "--version"]

    def test_all_windows_fallbacks_fail(self, monkeypatch):
        monkeypatch.setattr(install_aidlc, "_is_windows", lambda: True)

        def _raise(*a, **kw):
            raise FileNotFoundError("not found")
        monkeypatch.setattr("subprocess.run", _raise)
        ok, ver = install_aidlc._probe_version(["npm", "--version"])
        assert not ok
        assert ver == "not found"

    def test_empty_output_returns_empty_string(self, monkeypatch):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = ""
        mock.stderr = ""
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock)
        ok, ver = install_aidlc._probe_version(["cmd", "--version"])
        assert ok
        assert ver == ""

    def test_returns_first_line_of_multi_line_output(self, monkeypatch):
        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "first line\nsecond line\n"
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock)
        ok, ver = install_aidlc._probe_version(["cmd", "--version"])
        assert ok
        assert ver == "first line"


# ---------- _check_node_version (Windows cmd /c fallback) ----------

class TestCheckNodeVersion:
    def test_ok_when_version_sufficient(self, monkeypatch):
        monkeypatch.setattr(install_aidlc, "_is_windows", lambda: False)

        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "v22.0.0\n"
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock)
        ok, ver = install_aidlc._check_node_version(18)
        assert ok
        assert ver == "v22.0.0"

    def test_fail_when_version_too_low(self, monkeypatch):
        monkeypatch.setattr(install_aidlc, "_is_windows", lambda: False)

        mock = MagicMock()
        mock.returncode = 0
        mock.stdout = "v16.0.0\n"
        monkeypatch.setattr("subprocess.run", lambda *a, **kw: mock)
        ok, ver = install_aidlc._check_node_version(18)
        assert not ok
        assert ver == "v16.0.0"

    def test_cmd_c_on_windows(self, monkeypatch):
        """On Windows, _check_node_version uses cmd /c to resolve node.exe."""
        monkeypatch.setattr(install_aidlc, "_is_windows", lambda: True)

        calls = []

        def _run(cmd, **kw):
            calls.append(cmd)
            mock = MagicMock()
            mock.returncode = 0
            mock.stdout = "v22.0.0\n"
            return mock

        monkeypatch.setattr("subprocess.run", _run)
        ok, ver = install_aidlc._check_node_version(18)
        assert ok
        assert ver == "v22.0.0"
        assert len(calls) == 1
        assert calls[0] == ["cmd", "/c", "node", "--version"]

    def test_file_not_found_returns_not_found(self, monkeypatch):
        monkeypatch.setattr(install_aidlc, "_is_windows", lambda: False)

        def _raise(*a, **kw):
            raise FileNotFoundError("not found")
        monkeypatch.setattr("subprocess.run", _raise)
        ok, ver = install_aidlc._check_node_version(18)
        assert not ok
        assert ver == "not found"

    def test_timeout_returns_not_found(self, monkeypatch):
        monkeypatch.setattr(install_aidlc, "_is_windows", lambda: False)

        def _raise(*a, **kw):
            raise subprocess.TimeoutExpired(cmd="node", timeout=10)
        monkeypatch.setattr("subprocess.run", _raise)
        ok, ver = install_aidlc._check_node_version(18)
        assert not ok
        assert ver == "not found"
