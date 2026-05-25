from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "aidlc-scripts"
sys.path.insert(0, str(SCRIPTS))

import factory_skill_sync as mod
import skill_utils as su


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_skill_dir(base: Path, name: str, content: str = "") -> Path:
    d = base / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        content or f"---\nname: {name}\ndescription: test\n---\n",
        encoding="utf-8",
    )
    return d


# ── _remove ───────────────────────────────────────────────────────────────────

class TestRemove:
    def test_removes_real_directory(self, tmp_path):
        d = tmp_path / "skill"
        d.mkdir()
        (d / "SKILL.md").write_text("content")
        mod._remove(d)
        assert not d.exists()

    def test_removes_symlink_to_directory(self, tmp_path):
        real = tmp_path / "real-skill"
        real.mkdir()
        (real / "SKILL.md").write_text("content")
        link = tmp_path / "link-skill"
        link.symlink_to(real)
        mod._remove(link)
        assert not link.exists()
        assert real.exists()  # target untouched

    def test_removes_symlink_does_not_touch_target(self, tmp_path):
        real = tmp_path / "shared"
        real.mkdir()
        (real / "SKILL.md").write_text("shared content")
        link = tmp_path / "alias"
        link.symlink_to(real)
        mod._remove(link)
        assert (real / "SKILL.md").read_text() == "shared content"

    def test_noop_on_nonexistent(self, tmp_path):
        mod._remove(tmp_path / "does-not-exist")  # must not raise


# ── _copy_skill ────────────────────────────────────────────────────────────────

class TestCopySkill:
    def test_copies_real_directory(self, tmp_path):
        src = tmp_path / "src" / "react"
        src.mkdir(parents=True)
        (src / "SKILL.md").write_text("react content")
        dest = tmp_path / "dest" / "react"
        mod._copy_skill(src, dest)
        assert (dest / "SKILL.md").read_text() == "react content"

    def test_copies_through_symlink(self, tmp_path):
        real = tmp_path / "real" / "angular"
        real.mkdir(parents=True)
        (real / "SKILL.md").write_text("angular content")
        link = tmp_path / "link" / "angular"
        link.parent.mkdir()
        link.symlink_to(real)
        dest = tmp_path / "dest" / "angular"
        mod._copy_skill(link, dest)
        assert (dest / "SKILL.md").read_text() == "angular content"

    def test_copy_preserves_subdirs(self, tmp_path):
        src = tmp_path / "src" / "vue"
        (src / "sub").mkdir(parents=True)
        (src / "SKILL.md").write_text("main")
        (src / "sub" / "extra.md").write_text("extra")
        dest = tmp_path / "dest" / "vue"
        mod._copy_skill(src, dest)
        assert (dest / "sub" / "extra.md").read_text() == "extra"


# ── _check_node ───────────────────────────────────────────────────────────────

class TestCheckNode:
    def test_node_not_found_returns_false(self):
        with patch("factory_skill_sync.subprocess.run", side_effect=FileNotFoundError):
            ok, reason = mod._check_node()
            assert ok is False
            assert "not found" in reason.lower()

    def test_node_old_version_returns_false(self):
        result = MagicMock()
        result.stdout = "v18.0.0\n"
        with patch("factory_skill_sync.subprocess.run", return_value=result):
            ok, reason = mod._check_node()
            assert ok is False
            assert "v18" in reason

    def test_node_good_version_returns_true(self):
        result = MagicMock()
        result.stdout = "v22.6.0\n"
        with patch("factory_skill_sync.subprocess.run", return_value=result):
            ok, reason = mod._check_node()
            assert ok is True
            assert reason == ""

    def test_node_newer_version_returns_true(self):
        result = MagicMock()
        result.stdout = "v24.0.0\n"
        with patch("factory_skill_sync.subprocess.run", return_value=result):
            ok, reason = mod._check_node()
            assert ok is True

    def test_timeout_returns_false(self):
        with patch("factory_skill_sync.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("node", 10)):
            ok, reason = mod._check_node()
            assert ok is False


# ── _skill_is_current ─────────────────────────────────────────────────────────

class TestSkillIsCurrent:
    def test_matching_sha_returns_true(self, tmp_path):
        src = _make_skill_dir(tmp_path / "src", "my-skill", "content-abc")
        dest = _make_skill_dir(tmp_path / "dest", "my-skill", "content-abc")
        assert mod._skill_is_current(src, dest) is True

    def test_different_sha_returns_false(self, tmp_path):
        src = _make_skill_dir(tmp_path / "src", "my-skill", "content-abc")
        dest = _make_skill_dir(tmp_path / "dest", "my-skill", "content-xyz")
        assert mod._skill_is_current(src, dest) is False

    def test_dest_missing_returns_false(self, tmp_path):
        src = _make_skill_dir(tmp_path / "src", "my-skill")
        dest = tmp_path / "dest" / "my-skill"
        assert mod._skill_is_current(src, dest) is False

    def test_src_missing_returns_false(self, tmp_path):
        src = tmp_path / "src" / "my-skill"
        dest = _make_skill_dir(tmp_path / "dest", "my-skill")
        assert mod._skill_is_current(src, dest) is False


# ── _consolidate ──────────────────────────────────────────────────────────────

class TestConsolidate:
    def test_installs_new_skill(self, tmp_path):
        src_dir = _make_skill_dir(tmp_path / "ws" / ".agents" / "skills", "react")
        root_skills = tmp_path / ".agents" / "skills"
        all_found = {"react": src_dir}

        installed, skipped = mod._consolidate(all_found, root_skills, tmp_path, dry_run=False)

        assert installed == 1
        assert skipped == 0
        assert (root_skills / "react" / "SKILL.md").exists()

    def test_skips_up_to_date_skill(self, tmp_path):
        content = "---\nname: react\n---\n"
        src_dir = _make_skill_dir(tmp_path / "ws" / ".agents" / "skills", "react", content)
        root_skills = tmp_path / ".agents" / "skills"
        dest_dir = _make_skill_dir(root_skills, "react", content)

        all_found = {"react": src_dir}
        installed, skipped = mod._consolidate(all_found, root_skills, tmp_path, dry_run=False)

        assert installed == 0
        assert skipped == 1

    def test_dry_run_does_not_write(self, tmp_path):
        src_dir = _make_skill_dir(tmp_path / "ws" / ".agents" / "skills", "vue")
        root_skills = tmp_path / ".agents" / "skills"
        all_found = {"vue": src_dir}

        installed, skipped = mod._consolidate(all_found, root_skills, tmp_path, dry_run=True)

        assert installed == 1
        assert not (root_skills / "vue" / "SKILL.md").exists()

    def test_same_root_skill_skipped(self, tmp_path):
        root_skills = tmp_path / ".agents" / "skills"
        src_dir = _make_skill_dir(root_skills, "already-here")
        all_found = {"already-here": src_dir}

        installed, skipped = mod._consolidate(all_found, root_skills, tmp_path, dry_run=False)

        assert installed == 0
        assert skipped == 1

    def test_symlink_src_is_installed_and_removed(self, tmp_path):
        """autoskills CLI may create symlinks; _consolidate must follow and remove them."""
        real = tmp_path / "cache" / "angular"
        real.mkdir(parents=True)
        (real / "SKILL.md").write_text("---\nname: angular\n---\n")
        link = tmp_path / "ws" / ".agents" / "skills" / "angular"
        link.parent.mkdir(parents=True)
        link.symlink_to(real)

        root_skills = tmp_path / ".agents" / "skills"
        installed, skipped = mod._consolidate({"angular": link}, root_skills, tmp_path, dry_run=False)

        assert installed == 1
        assert (root_skills / "angular" / "SKILL.md").exists()
        assert not link.exists()   # symlink removed
        assert real.exists()       # original cache untouched

    def test_symlink_src_up_to_date_is_removed(self, tmp_path):
        """Up-to-date symlink src must be unlinked, not left dangling."""
        content = "---\nname: vue\n---\n"
        real = tmp_path / "cache" / "vue"
        real.mkdir(parents=True)
        (real / "SKILL.md").write_text(content)

        root_skills = tmp_path / ".agents" / "skills"
        _make_skill_dir(root_skills, "vue", content)  # already up-to-date

        link = tmp_path / "ws" / ".agents" / "skills" / "vue"
        link.parent.mkdir(parents=True)
        link.symlink_to(real)

        installed, skipped = mod._consolidate({"vue": link}, root_skills, tmp_path, dry_run=False)

        assert skipped == 1
        assert not link.exists()  # symlink cleaned up even when skipped


# ── _cleanup_workspace_agents ─────────────────────────────────────────────────

class TestCleanupWorkspaceAgents:
    def test_removes_empty_skills_dir(self, tmp_path):
        ws = tmp_path / "backend"
        ws.mkdir()
        skills_dir = ws / ".agents" / "skills"
        skills_dir.mkdir(parents=True)

        mod._cleanup_workspace_agents([ws], tmp_path, dry_run=False)

        assert not skills_dir.exists()

    def test_removes_empty_agents_dir(self, tmp_path):
        ws = tmp_path / "backend"
        ws.mkdir()
        agents_dir = ws / ".agents"
        agents_dir.mkdir()

        mod._cleanup_workspace_agents([ws], tmp_path, dry_run=False)

        assert not agents_dir.exists()

    def test_does_not_remove_non_empty_skills_dir(self, tmp_path):
        ws = tmp_path / "backend"
        ws.mkdir()
        skills_dir = ws / ".agents" / "skills" / "react"
        skills_dir.mkdir(parents=True)
        (skills_dir / "SKILL.md").write_text("content")

        mod._cleanup_workspace_agents([ws], tmp_path, dry_run=False)

        assert (skills_dir / "SKILL.md").exists()

    def test_skips_repo_root_itself(self, tmp_path):
        agents_dir = tmp_path / ".agents"
        agents_dir.mkdir()

        mod._cleanup_workspace_agents([tmp_path], tmp_path, dry_run=False)

        assert agents_dir.exists()

    def test_removes_skills_lock_json(self, tmp_path):
        ws = tmp_path / "frontend"
        ws.mkdir()
        lock = ws / "skills-lock.json"
        lock.write_text("{}")

        mod._cleanup_workspace_agents([ws], tmp_path, dry_run=False)

        assert not lock.exists()

    def test_dry_run_does_not_remove(self, tmp_path):
        ws = tmp_path / "backend"
        ws.mkdir()
        skills_dir = ws / ".agents" / "skills"
        skills_dir.mkdir(parents=True)

        mod._cleanup_workspace_agents([ws], tmp_path, dry_run=True)

        assert skills_dir.exists()

    def test_removes_symlink_skills_dir(self, tmp_path):
        """autoskills may leave ws/.agents/skills as a symlink; must be unlinked."""
        ws = tmp_path / "frontend"
        ws.mkdir()
        real_skills = tmp_path / "shared-skills"
        real_skills.mkdir()
        link = ws / ".agents" / "skills"
        link.parent.mkdir(parents=True)
        link.symlink_to(real_skills)

        mod._cleanup_workspace_agents([ws], tmp_path, dry_run=False)

        assert not link.exists()
        assert real_skills.exists()  # target untouched

    def test_removes_symlink_agents_dir(self, tmp_path):
        ws = tmp_path / "backend"
        ws.mkdir()
        real_agents = tmp_path / "shared-agents"
        real_agents.mkdir()
        link = ws / ".agents"
        link.symlink_to(real_agents)

        mod._cleanup_workspace_agents([ws], tmp_path, dry_run=False)

        assert not link.exists()
        assert real_agents.exists()


# ── cmd_select ────────────────────────────────────────────────────────────────

class TestCmdSelect:
    def _setup_skills(self, tmp_path):
        cs = tmp_path / ".agents" / "custom-skills"
        fs = tmp_path / ".agents" / "skills"
        _make_skill_dir(cs, "my-process-skill")
        _make_skill_dir(fs, "nextjs")
        return tmp_path

    def test_returns_json_by_default(self, tmp_path, capsys):
        self._setup_skills(tmp_path)
        with patch("factory_skill_sync.REPO_ROOT_DEFAULT", tmp_path):
            mod.cmd_select(tmp_path, output_format="json")

        out = capsys.readouterr().out
        data = json.loads(out)
        assert "skill_paths_resolved" in data
        assert data["skill_count"] >= 2

    def test_custom_skills_come_first(self, tmp_path, capsys):
        self._setup_skills(tmp_path)
        with patch("factory_skill_sync.REPO_ROOT_DEFAULT", tmp_path):
            mod.cmd_select(tmp_path, output_format="json")

        data = json.loads(capsys.readouterr().out)
        paths = data["skill_paths_resolved"]
        custom_idx = next(i for i, p in enumerate(paths) if "custom-skills" in p)
        framework_idx = next(i for i, p in enumerate(paths) if "/skills/" in p and "custom" not in p)
        assert custom_idx < framework_idx

    def test_text_output_one_path_per_line(self, tmp_path, capsys):
        self._setup_skills(tmp_path)
        with patch("factory_skill_sync.REPO_ROOT_DEFAULT", tmp_path):
            mod.cmd_select(tmp_path, output_format="text")

        lines = [l for l in capsys.readouterr().out.splitlines() if l.strip()]
        assert len(lines) >= 2
        for line in lines:
            assert "SKILL.md" in line

    def test_no_skills_returns_empty_list(self, tmp_path, capsys):
        with patch("factory_skill_sync.REPO_ROOT_DEFAULT", tmp_path), \
             patch.object(su.Path, "home", return_value=tmp_path):
            mod.cmd_select(tmp_path, output_format="json")

        data = json.loads(capsys.readouterr().out)
        assert data["skill_paths_resolved"] == []
        assert data["skill_count"] == 0


# ── cmd_sync graceful degradation ────────────────────────────────────────────

class TestCmdSyncGracefulDegradation:
    def test_node_missing_exits_0(self, tmp_path, capsys):
        with patch("factory_skill_sync._check_node",
                   return_value=(False, "Node.js not found on PATH")):
            result = mod.cmd_sync(tmp_path)
        assert result == 0
        out = capsys.readouterr().out
        assert "[Sync] SKIPPED" in out
        assert "Node.js not found" in out
        assert "[Sync] WARN" in out
