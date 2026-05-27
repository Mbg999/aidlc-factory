from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import shutil
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "aidlc-scripts"
sys.path.insert(0, str(SCRIPTS))


def _symlink_or_copy(target: Path, source: Path):
    """Symlink target→source, falling back to copy2/copytree on Windows."""
    try:
        target.symlink_to(source)
    except (OSError, NotImplementedError, PermissionError):
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)

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


# ── (consolidation helpers removed — no symlinks created) ─────────

# ── _resolve_node ─────────────────────────────────────────────────────────────

class TestResolveNode:
    def test_node_not_found_returns_none(self):
        with patch("factory_skill_sync.subprocess.run", side_effect=FileNotFoundError):
            assert mod._resolve_node() is None

    def test_timeout_returns_none(self):
        with patch("factory_skill_sync.subprocess.run",
                   side_effect=subprocess.TimeoutExpired("node", 10)):
            assert mod._resolve_node() is None

    def test_nonzero_exit_returns_none(self):
        result = MagicMock()
        result.returncode = 1
        with patch("factory_skill_sync.subprocess.run", return_value=result):
            assert mod._resolve_node() is None

    def test_returns_system_node_when_meets_min(self):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "v22.6.0\n"
        with patch("factory_skill_sync.subprocess.run", return_value=result):
            resolved = mod._resolve_node()
        assert resolved is not None
        prefix, label = resolved
        assert prefix == ["node"]
        assert "22.6.0" in label

    def test_returns_none_when_version_too_old(self):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "v18.17.0\n"
        with patch("factory_skill_sync.subprocess.run", return_value=result):
            assert mod._resolve_node() is None


# ── clone_autoskills ────────────────────────────────────────────────────────────

class TestCloneAutoskills:
    def test_dry_run_prints_and_returns_dest(self, tmp_path, capsys):
        dest = tmp_path / "autoskills"
        result = mod.clone_autoskills(dest, dry_run=True)
        assert result == dest
        out = capsys.readouterr().out
        assert "[DRY-RUN]" in out
        assert not dest.exists()

    def test_existing_git_dir_pulls(self, tmp_path):
        dest = tmp_path / "autoskills"
        dest.mkdir()
        (dest / ".git").mkdir()
        with patch("factory_skill_sync.subprocess.run") as mock_run:
            mod.clone_autoskills(dest, dry_run=False)
            calls = [c.args for c in mock_run.call_args_list]
            assert any("pull" in str(a) for a in calls)

    def test_clone_runs_git_clone(self, tmp_path):
        dest = tmp_path / "autoskills"
        with patch("factory_skill_sync.subprocess.run") as mock_run:
            mod.clone_autoskills(dest, dry_run=False)
            args = mock_run.call_args[0][0]
            assert args[0] == "git"
            assert "--depth" in args
            assert "1" in args
            assert "--single-branch" in args
            assert "--no-tags" in args
            assert mod.AUTOSKILLS_REPO in args


# ── _build_autoskills ───────────────────────────────────────────────────────────

class TestBuildAutoskills:
    def test_cache_hit_skips_build(self, tmp_path):
        autoskills_dir = tmp_path / "autoskills"
        pkg = autoskills_dir / mod.AUTOSKILLS_PKG_DIR
        pkg.mkdir(parents=True)
        ts = pkg / "main.ts"
        ts.write_text("// code")
        entry = pkg / mod.AUTOSKILLS_ENTRY
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_text("built")
        # Make entry newer than source
        now = time.time()
        os.utime(str(ts), (now - 100, now - 100))
        os.utime(str(entry), (now, now))
        with patch("factory_skill_sync.subprocess.run") as mock_run:
            mod._build_autoskills(autoskills_dir, dry_run=False)
            mock_run.assert_not_called()

    def test_build_runs_install_and_build(self, tmp_path):
        autoskills_dir = tmp_path / "autoskills"
        pkg = autoskills_dir / mod.AUTOSKILLS_PKG_DIR
        pkg.mkdir(parents=True)
        ts = pkg / "main.ts"
        ts.write_text("// code")
        entry = pkg / mod.AUTOSKILLS_ENTRY
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_text("built")
        # Make source newer than entry to force a rebuild
        now = time.time()
        os.utime(str(entry), (now - 100, now - 100))
        os.utime(str(ts), (now, now))
        with patch("factory_skill_sync.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            mod._build_autoskills(autoskills_dir, dry_run=False)
            calls = [c.args[0] for c in mock_run.call_args_list]
            assert any(c[0] == "npm" and "install" in c for c in calls)
            assert any(c[0] == "npm" and "build" in c for c in calls)

    def test_dry_run_does_not_run(self, tmp_path):
        autoskills_dir = tmp_path / "autoskills"
        with patch("factory_skill_sync.subprocess.run") as mock_run:
            mod._build_autoskills(autoskills_dir, dry_run=True)
            mock_run.assert_not_called()


# ── _run_local_autoskills ─────────────────────────────────────────────────────

class TestRunLocalAutoskills:
    def test_dry_run_returns_empty(self, tmp_path):
        result = mod._run_local_autoskills(
            tmp_path, tmp_path / "autoskills", dry_run=True
        )
        assert result == []

    def test_no_node_returns_empty(self, tmp_path):
        with patch("factory_skill_sync._resolve_node", return_value=None):
            result = mod._run_local_autoskills(
                tmp_path, tmp_path / "autoskills", dry_run=False
            )
        assert result == []

    def test_runs_node_with_entry_and_tech(self, tmp_path):
        autoskills_dir = tmp_path / "autoskills"
        entry = autoskills_dir / mod.AUTOSKILLS_PKG_DIR / mod.AUTOSKILLS_ENTRY
        entry.parent.mkdir(parents=True, exist_ok=True)
        entry.write_text("// built")

        proc_result = MagicMock()
        proc_result.returncode = 0
        proc_result.stdout = ""
        proc_result.stderr = ""

        with patch("factory_skill_sync._resolve_node",
                   return_value=(["node"], "system node v22.6.0")) as _mock_node, \
             patch("factory_skill_sync.subprocess.run", return_value=proc_result) as mock_run:
            mod._run_local_autoskills(
                tmp_path, autoskills_dir, techs=["react", "nextjs"], dry_run=False
            )
            call_args = mock_run.call_args
            args_list = call_args[0][0] if call_args[0] else call_args[1].get("args", [])
            assert str(entry) in args_list
            assert "--path" in args_list
            assert str(tmp_path) in args_list
            assert "--tech" in args_list
            assert "react,nextjs" in args_list


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
        with patch("factory_skill_sync.REPO_ROOT_DEFAULT", tmp_path), \
             patch("factory_skill_sync._resolve_node", return_value=None):
            mod.cmd_select(tmp_path, output_format="json")

        out = capsys.readouterr().out
        data = json.loads(out)
        assert "skill_paths_resolved" in data
        assert "framework_skill_names" in data
        assert isinstance(data["framework_skill_names"], list)
        assert data["skill_count"] >= 2

    def test_custom_skills_come_first(self, tmp_path, capsys):
        self._setup_skills(tmp_path)
        with patch("factory_skill_sync.REPO_ROOT_DEFAULT", tmp_path), \
             patch("factory_skill_sync._resolve_node", return_value=None):
            mod.cmd_select(tmp_path, output_format="json")

        data = json.loads(capsys.readouterr().out)
        paths = data["skill_paths_resolved"]
        custom_idx = next(i for i, p in enumerate(paths) if "custom-skills" in p)
        framework_idx = next(i for i, p in enumerate(paths) if "/skills/" in p and "custom" not in p)
        assert custom_idx < framework_idx

    def test_text_output_one_path_per_line(self, tmp_path, capsys):
        self._setup_skills(tmp_path)
        with patch("factory_skill_sync.REPO_ROOT_DEFAULT", tmp_path), \
             patch("factory_skill_sync._resolve_node", return_value=None):
            mod.cmd_select(tmp_path, output_format="text")

        lines = [l for l in capsys.readouterr().out.splitlines() if l.strip()]
        assert len(lines) >= 2
        for line in lines:
            assert "SKILL.md" in line

    def test_no_skills_returns_empty_list(self, tmp_path, capsys):
        with patch("factory_skill_sync.REPO_ROOT_DEFAULT", tmp_path), \
             patch("factory_skill_sync._resolve_node", return_value=None), \
             patch.object(su.Path, "home", return_value=tmp_path):
            mod.cmd_select(tmp_path, output_format="json")

        data = json.loads(capsys.readouterr().out)
        assert data["skill_paths_resolved"] == []
        assert data["framework_skill_names"] == []
        assert data["skill_count"] == 0


# ── cmd_sync graceful degradation ────────────────────────────────────────────

class TestCmdSyncGracefulDegradation:
    def test_node_missing_exits_0(self, tmp_path, capsys):
        with patch("factory_skill_sync._resolve_node", return_value=None):
            result = mod.cmd_sync(tmp_path)
        assert result == 0

    def test_clone_failure_is_graceful(self, tmp_path, capsys):
        with patch("factory_skill_sync._resolve_node",
                   return_value=(["node"], "system node v22.6.0")), \
             patch("factory_skill_sync.clone_autoskills",
                   side_effect=subprocess.CalledProcessError(1, "git")):
            result = mod.cmd_sync(tmp_path)
        assert result == 0
        out = capsys.readouterr().out
        assert "failed to clone" in out.lower() or "warning" in out.lower()

    def test_techs_passed_to_runner(self, tmp_path, capsys):
        with patch("factory_skill_sync._resolve_node",
                   return_value=(["node"], "system node v22.6.0")), \
             patch("factory_skill_sync.clone_autoskills", return_value=tmp_path / "cache"), \
             patch("factory_skill_sync._run_local_autoskills", return_value=[]) as mock_run:
            result = mod.cmd_sync(tmp_path, techs=["python"])
        assert result == 0
        mock_run.assert_called_once()
        _, kwargs = mock_run.call_args
        assert kwargs.get("techs") == ["python"]


# ── cmd_sync cache cleanup ────────────────────────────────────

class TestCmdSyncCacheCleanup:
    def test_cleans_up_autoskills_cache_after_success(self, tmp_path):
        """cmd_sync should remove .autoskills-cache after successful run."""
        cache_dir = tmp_path / mod.AUTOSKILLS_CACHE_DIR
        cache_dir.mkdir(parents=True)
        (cache_dir / "dummy").write_text("cache artifact")

        with patch("factory_skill_sync._resolve_node",
                   return_value=(["node"], "system node v22.6.0")), \
             patch("factory_skill_sync.clone_autoskills", return_value=cache_dir), \
             patch("factory_skill_sync._run_local_autoskills", return_value=[]):
            mod.cmd_sync(tmp_path)

        assert not cache_dir.exists(), "cache dir was not cleaned up"

    def test_does_not_clean_in_dry_run(self, tmp_path):
        """cmd_sync should NOT remove .autoskills-cache in dry-run mode."""
        cache_dir = tmp_path / mod.AUTOSKILLS_CACHE_DIR
        cache_dir.mkdir(parents=True)

        with patch("factory_skill_sync._resolve_node",
                   return_value=(["node"], "system node v22.6.0")), \
             patch("factory_skill_sync.clone_autoskills", return_value=cache_dir), \
             patch("factory_skill_sync._run_local_autoskills", return_value=[]):
            mod.cmd_sync(tmp_path, dry_run=True)

        assert cache_dir.exists(), "cache dir was removed in dry-run"


# ── CLI argument parsing ──────────────────────────────────────────────────────

class TestCliParsing:
    def test_sync_with_tech(self, tmp_path):
        with patch("factory_skill_sync.cmd_sync", return_value=0) as mock_sync:
            with patch("sys.argv", ["factory_skill_sync.py", "--repo-root", str(tmp_path), "sync", "--tech", "react,nextjs"]):
                with pytest.raises(SystemExit) as exc_info:
                    mod.main()
                assert exc_info.value.code == 0
        assert mock_sync.called
        _, kwargs = mock_sync.call_args
        assert kwargs["techs"] == ["react", "nextjs"]

    def test_sync_without_tech(self, tmp_path):
        with patch("factory_skill_sync.cmd_sync", return_value=0) as mock_sync:
            with patch("sys.argv", ["factory_skill_sync.py", "--repo-root", str(tmp_path), "sync"]):
                with pytest.raises(SystemExit) as exc_info:
                    mod.main()
                assert exc_info.value.code == 0
        assert mock_sync.called
        _, kwargs = mock_sync.call_args
        assert kwargs["techs"] is None
