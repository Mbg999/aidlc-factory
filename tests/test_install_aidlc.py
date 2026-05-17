from __future__ import annotations

import subprocess
import sys
from pathlib import Path

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


# ---------- check_workflow_doc_conflicts ----------

class TestCheckWorkflowDocConflicts:
    def test_single_tool_ok(self):
        install_aidlc.check_workflow_doc_conflicts(["claude"])

    def test_claude_plus_opencode_ok(self):
        # Different docs (CLAUDE.md vs AGENTS.md)
        install_aidlc.check_workflow_doc_conflicts(["claude", "opencode"])

    def test_tool_scoped_combo_ok(self):
        # None of these write to a shared top-level doc
        install_aidlc.check_workflow_doc_conflicts(
            ["kiro", "amazonq", "cursor", "cline", "windsurf"]
        )

    def test_opencode_codex_clashes(self):
        with pytest.raises(ValueError, match="AGENTS.md"):
            install_aidlc.check_workflow_doc_conflicts(["opencode", "codex"])

    def test_opencode_other_clashes(self):
        with pytest.raises(ValueError, match="AGENTS.md"):
            install_aidlc.check_workflow_doc_conflicts(["opencode", "other"])

    def test_codex_other_clashes(self):
        with pytest.raises(ValueError, match="AGENTS.md"):
            install_aidlc.check_workflow_doc_conflicts(["codex", "other"])


# ---------- detect_installed_tools ----------

class TestDetectInstalledTools:
    def test_empty_dir(self, tmp_path: Path):
        assert install_aidlc.detect_installed_tools(tmp_path) == set()

    def test_claude_marker(self, tmp_path: Path):
        (tmp_path / "CLAUDE.md").write_text("x")
        assert install_aidlc.detect_installed_tools(tmp_path) == {"claude"}

    def test_opencode_marker(self, tmp_path: Path):
        (tmp_path / ".opencode" / "agents").mkdir(parents=True)
        assert install_aidlc.detect_installed_tools(tmp_path) == {"opencode"}

    def test_codex_marker(self, tmp_path: Path):
        (tmp_path / ".codex" / "agents").mkdir(parents=True)
        assert install_aidlc.detect_installed_tools(tmp_path) == {"codex"}

    def test_copilot_marker(self, tmp_path: Path):
        (tmp_path / ".github").mkdir()
        (tmp_path / ".github" / "copilot-instructions.md").write_text("x")
        assert install_aidlc.detect_installed_tools(tmp_path) == {"copilot"}

    def test_agents_md_alone_is_ambiguous(self, tmp_path: Path):
        # AGENTS.md is shared by opencode/codex/other; without a tool-specific
        # dir we cannot disambiguate, so no tool is detected.
        (tmp_path / "AGENTS.md").write_text("x")
        assert install_aidlc.detect_installed_tools(tmp_path) == set()

    def test_other_never_auto_detected(self, tmp_path: Path):
        # 'other' has no unique marker — should never appear in the set
        (tmp_path / "AGENTS.md").write_text("x")
        (tmp_path / ".aidlc-rule-details").mkdir()
        assert "other" not in install_aidlc.detect_installed_tools(tmp_path)

    def test_multiple_tools(self, tmp_path: Path):
        (tmp_path / "CLAUDE.md").write_text("x")
        (tmp_path / ".opencode" / "agents").mkdir(parents=True)
        (tmp_path / ".kiro" / "steering" / "aws-aidlc-rules").mkdir(parents=True)
        assert install_aidlc.detect_installed_tools(tmp_path) == {"claude", "opencode", "kiro"}


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

    def test_clash_opencode_codex_exits_2(self, tmp_path: Path):
        r = _run_cli("--tool", "opencode,codex", "--yes", "--dry-run", "--dest", str(tmp_path))
        assert r.returncode == 2
        assert "Incompatible" in r.stdout
        assert "AGENTS.md" in r.stdout

    def test_fresh_install_claude(self, tmp_path: Path):
        _stub_skills(tmp_path)
        r = _run_cli(
            "--tool", "claude", "--yes", "--no-orchestrator", "--no-venv",
            "--dest", str(tmp_path),
        )
        assert r.returncode == 0, r.stdout + r.stderr
        assert (tmp_path / "CLAUDE.md").exists()
        assert (tmp_path / ".aidlc-rule-details").exists()

    def test_rerun_skips_existing(self, tmp_path: Path):
        _stub_skills(tmp_path)
        r1 = _run_cli(
            "--tool", "claude", "--yes", "--no-orchestrator", "--no-venv",
            "--dest", str(tmp_path),
        )
        assert r1.returncode == 0
        r2 = _run_cli(
            "--tool", "claude", "--yes", "--no-orchestrator", "--no-venv",
            "--dest", str(tmp_path),
        )
        assert r2.returncode == 0
        assert "Detected existing install for: claude" in r2.stdout
        assert "nothing to do" in r2.stdout

    def test_add_second_tool_merges(self, tmp_path: Path):
        _stub_skills(tmp_path)
        _run_cli("--tool", "claude", "--yes", "--no-orchestrator", "--no-venv", "--dest", str(tmp_path))
        assert (tmp_path / "CLAUDE.md").exists()
        r = _run_cli(
            "--tool", "claude,opencode", "--yes", "--no-orchestrator", "--no-venv",
            "--dest", str(tmp_path),
        )
        assert r.returncode == 0
        assert "Detected existing install for: claude" in r.stdout
        assert (tmp_path / "AGENTS.md").exists()
        # Both workflow docs now coexist
        assert (tmp_path / "CLAUDE.md").exists()

    def test_force_reinstalls(self, tmp_path: Path):
        _stub_skills(tmp_path)
        _run_cli("--tool", "claude", "--yes", "--no-orchestrator", "--no-venv", "--dest", str(tmp_path))
        r = _run_cli(
            "--tool", "claude", "--yes", "--no-orchestrator", "--no-venv", "--force",
            "--dest", str(tmp_path),
        )
        assert r.returncode == 0
        assert "Detected existing install" not in r.stdout
        assert "Installing for Claude Code" in r.stdout


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
