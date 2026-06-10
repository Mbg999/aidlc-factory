from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "aidlc-scripts"
sys.path.insert(0, str(SCRIPTS))

import factory_skill_sync as mod
import skill_utils as su


def _make_skill_dir(base: Path, name: str, content: str = "") -> Path:
    d = base / name
    d.mkdir(parents=True, exist_ok=True)
    (d / "SKILL.md").write_text(
        content or f"---\nname: {name}\ndescription: test\n---\n",
        encoding="utf-8",
    )
    return d


# ── _parse_node_version ─────────────────────────────────────────

class TestParseNodeVersion:
    def test_full_semver(self):
        assert mod._parse_node_version("v22.6.0") == (22, 6, 0)

    def test_no_v_prefix(self):
        assert mod._parse_node_version("22.6.0") == (22, 6, 0)

    def test_with_whitespace(self):
        assert mod._parse_node_version("  v22.6.0\n") == (22, 6, 0)

    def test_pads_missing_parts(self):
        assert mod._parse_node_version("v22") == (22, 0, 0)
        assert mod._parse_node_version("v22.6") == (22, 6, 0)

    def test_non_numeric_returns_none(self):
        assert mod._parse_node_version("v22.x.y") is None

    def test_empty_string_returns_none(self):
        assert mod._parse_node_version("") is None


# ── _resolve_npx ────────────────────────────────────────────────

class TestResolveNpx:
    def test_file_not_found_returns_none(self):
        with patch("factory_skill_sync.subprocess.run", side_effect=FileNotFoundError):
            assert mod._resolve_npx() is None

    def test_timeout_returns_none(self):
        with patch(
            "factory_skill_sync.subprocess.run",
            side_effect=subprocess.TimeoutExpired("node", 10),
        ):
            assert mod._resolve_npx() is None

    def test_all_attempts_fail_returns_none(self):
        """node, fnm, and volta all fail — returns None."""
        results = [
            MagicMock(returncode=1, stdout="", stderr=""),
            MagicMock(returncode=1, stdout="", stderr=""),
            MagicMock(returncode=1, stdout="", stderr=""),
        ]
        with patch("factory_skill_sync.subprocess.run", side_effect=results), \
             patch("pathlib.Path.home", return_value=Path("/tmp/no-nvm")):
            assert mod._resolve_npx() is None

    def test_node_too_old_continues_to_next(self):
        """node returns old version — fnm succeeds."""
        old_node = MagicMock(returncode=0, stdout="v18.17.0\n")
        good_node = MagicMock(returncode=0, stdout="v22.6.0\n")
        with patch("factory_skill_sync.subprocess.run", side_effect=[old_node, good_node]), \
             patch("pathlib.Path.home", return_value=Path("/tmp/no-nvm")):
            resolved = mod._resolve_npx()
        assert resolved is not None
        prefix, label, _nvm_bin = resolved
        assert prefix == ["fnm", "exec", "--using=22", "--", "npx"]
        assert "fnm" in label

    def test_returns_system_node_when_meets_min(self):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "v22.6.0\n"
        with patch("factory_skill_sync.subprocess.run", return_value=result):
            resolved = mod._resolve_npx()
        assert resolved is not None
        prefix, label, _nvm_bin = resolved
        assert prefix == ["node"]
        assert "22.6.0" in label

    def test_returns_none_when_version_too_old(self):
        result = MagicMock()
        result.returncode = 0
        result.stdout = "v18.17.0\n"
        with patch("factory_skill_sync.subprocess.run", return_value=result):
            assert mod._resolve_npx() is None

    def test_second_attempt_succeeds_after_first_fails(self):
        results = [
            MagicMock(returncode=1, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="v22.6.0\n"),
        ]
        with patch("factory_skill_sync.subprocess.run", side_effect=results), \
             patch("pathlib.Path.home", return_value=Path("/tmp/no-nvm")):
            resolved = mod._resolve_npx()
        assert resolved is not None
        prefix, _label, _nvm_bin = resolved
        assert prefix == ["fnm", "exec", "--using=22", "--", "npx"]


# ── _run_npx ────────────────────────────────────────────────────

class TestRunNpx:
    def test_runs_with_correct_args(self):
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = "skills_installed"
        proc.stderr = ""
        with patch("factory_skill_sync.subprocess.run", return_value=proc) as mock_run:
            result = mod._run_npx(
                ["node"], ["-y", "--path", "/tmp/project", "--tech", "react,nextjs"],
                project_dir=Path("/tmp/project"), timeout=180,
            )
        assert result is not None
        assert result.stdout == "skills_installed"
        mock_run.assert_called_once_with(
            ["node", "npx", "-y", mod.PACKAGE_NAME, "-y", "--path", "/tmp/project", "--tech", "react,nextjs"],
            cwd="/tmp/project", capture_output=True, text=True, timeout=180,
        )

    def test_without_project_dir(self):
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = ""
        proc.stderr = ""
        with patch("factory_skill_sync.subprocess.run", return_value=proc) as mock_run:
            result = mod._run_npx(["node"], ["--list-tech"])
        assert result is not None
        mock_run.assert_called_once_with(
            ["node", "npx", "-y", mod.PACKAGE_NAME, "--list-tech"],
            cwd=None, capture_output=True, text=True, timeout=180,
        )

    def test_file_not_found_returns_none(self):
        with patch("factory_skill_sync.subprocess.run", side_effect=FileNotFoundError):
            result = mod._run_npx(["node"], [], timeout=30)
        assert result is None

    def test_timeout_returns_none(self):
        with patch(
            "factory_skill_sync.subprocess.run",
            side_effect=subprocess.TimeoutExpired("npx", 30),
        ):
            result = mod._run_npx(["node"], [], timeout=30)
        assert result is None

    def test_oserror_returns_none(self):
        with patch("factory_skill_sync.subprocess.run", side_effect=OSError("denied")):
            result = mod._run_npx(["node"], [], timeout=30)
        assert result is None


# ── _collect_installed_skills ───────────────────────────────────

class TestCollectInstalledSkills:
    def test_empty_when_skills_dir_missing(self, tmp_path):
        result = mod._collect_installed_skills(tmp_path)
        assert result == []

    def test_returns_valid_skill_dirs(self, tmp_path):
        skills_dir = tmp_path / ".agents" / "skills"
        _make_skill_dir(skills_dir, "react")
        _make_skill_dir(skills_dir, "nextjs")
        result = mod._collect_installed_skills(tmp_path)
        assert len(result) == 2
        names = {d.name for d in result}
        assert names == {"react", "nextjs"}

    def test_skips_dirs_without_skill_md(self, tmp_path):
        skills_dir = tmp_path / ".agents" / "skills"
        _make_skill_dir(skills_dir, "valid")
        (skills_dir / "no-skill-dir").mkdir()
        result = mod._collect_installed_skills(tmp_path)
        assert len(result) == 1
        assert result[0].name == "valid"

    def test_only_returns_dirs(self, tmp_path):
        skills_dir = tmp_path / ".agents" / "skills"
        skills_dir.mkdir(parents=True)
        (skills_dir / "file.txt").write_text("not a dir")
        result = mod._collect_installed_skills(tmp_path)
        assert result == []


# ── cmd_sync ────────────────────────────────────────────────────

class TestCmdSync:
    def test_node_missing_exits_0(self, tmp_path, capsys):
        with patch("factory_skill_sync._resolve_npx", return_value=None):
            rc = mod.cmd_sync(tmp_path)
        assert rc == 0

    def test_dry_run_displays_correctly(self, tmp_path, capsys):
        with patch(
            "factory_skill_sync._resolve_npx",
            return_value=(["node"], "node (v22.6.0)", None),
        ):
            rc = mod.cmd_sync(tmp_path, dry_run=True)
        assert rc == 0
        out = capsys.readouterr().out
        assert "[DRY-RUN]" in out
        assert str(tmp_path) in out

    def test_dry_run_with_tech(self, tmp_path, capsys):
        with patch(
            "factory_skill_sync._resolve_npx",
            return_value=(["node"], "node (v22.6.0)", None),
        ):
            rc = mod.cmd_sync(tmp_path, dry_run=True, techs=["react", "nextjs"])
        assert rc == 0
        out = capsys.readouterr().out
        assert "react,nextjs" in out

    def test_runner_failure_is_graceful(self, tmp_path, capsys):
        with patch(
            "factory_skill_sync._resolve_npx",
            return_value=(["node"], "node (v22.6.0)", None),
        ), patch("factory_skill_sync._run_npx", return_value=None):
            rc = mod.cmd_sync(tmp_path)
        assert rc == 0
        out = capsys.readouterr().out
        assert "SKIP" in out

    def test_passes_args_to_run_npx(self, tmp_path):
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = ""
        proc.stderr = ""
        with patch(
            "factory_skill_sync._resolve_npx",
            return_value=(["node"], "node (v22.6.0)", None),
        ), patch("factory_skill_sync._run_npx", return_value=proc) as mock_run:
            mod.cmd_sync(tmp_path, techs=["react", "nextjs"])
        mock_run.assert_called_once_with(
            ["node"],
            ["-y", "--path", str(tmp_path), "--tech", "react,nextjs"],
            project_dir=tmp_path, nvm_bin=None,
        )

    def test_no_techs_passed(self, tmp_path):
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = ""
        proc.stderr = ""
        with patch(
            "factory_skill_sync._resolve_npx",
            return_value=(["node"], "node (v22.6.0)", None),
        ), patch("factory_skill_sync._run_npx", return_value=proc) as mock_run:
            mod.cmd_sync(tmp_path)
        mock_run.assert_called_once_with(
            ["node"],
            ["-y", "--path", str(tmp_path)],
            project_dir=tmp_path, nvm_bin=None,
        )

    def test_nonzero_exit_prints_error(self, tmp_path, capsys):
        proc = MagicMock()
        proc.returncode = 1
        proc.stdout = ""
        proc.stderr = "some error\nline2\nline3\nline4\nline5\nline6\n"
        with patch(
            "factory_skill_sync._resolve_npx",
            return_value=(["node"], "node (v22.6.0)", None),
        ), patch("factory_skill_sync._run_npx", return_value=proc):
            rc = mod.cmd_sync(tmp_path)
        assert rc == 0
        out = capsys.readouterr().out
        assert "exited 1" in out

    def test_reports_installed_skill_count(self, tmp_path, capsys):
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = ""
        proc.stderr = ""
        skills_dir = tmp_path / ".agents" / "skills"
        _make_skill_dir(skills_dir, "react")
        _make_skill_dir(skills_dir, "nextjs")
        with patch(
            "factory_skill_sync._resolve_npx",
            return_value=(["node"], "node (v22.6.0)", None),
        ), patch("factory_skill_sync._run_npx", return_value=proc):
            rc = mod.cmd_sync(tmp_path)
        assert rc == 0
        out = capsys.readouterr().out
        assert "2 skill(s)" in out

    def test_no_installed_skills_message(self, tmp_path, capsys):
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = ""
        proc.stderr = ""
        with patch(
            "factory_skill_sync._resolve_npx",
            return_value=(["node"], "node (v22.6.0)", None),
        ), patch("factory_skill_sync._run_npx", return_value=proc):
            rc = mod.cmd_sync(tmp_path)
        assert rc == 0
        out = capsys.readouterr().out
        assert "no matching technologies" in out


# ── cmd_list_tech ───────────────────────────────────────────────

class TestCmdListTech:
    def test_node_missing_exits_0(self, tmp_path, capsys):
        with patch("factory_skill_sync._resolve_npx", return_value=None):
            rc = mod.cmd_list_tech(tmp_path)
        assert rc == 0
        out = capsys.readouterr().out
        assert "SKIP" in out

    def test_dry_run_prints_and_returns(self, tmp_path, capsys):
        with patch(
            "factory_skill_sync._resolve_npx",
            return_value=(["node"], "node (v22.6.0)", None),
        ):
            rc = mod.cmd_list_tech(tmp_path, dry_run=True)
        assert rc == 0
        out = capsys.readouterr().out
        assert "[DRY-RUN]" in out
        assert mod.PACKAGE_NAME in out

    def test_prints_stdout_on_success(self, tmp_path, capsys):
        proc = MagicMock()
        proc.returncode = 0
        proc.stdout = "react\nnextjs\npython\n"
        proc.stderr = ""
        with patch(
            "factory_skill_sync._resolve_npx",
            return_value=(["node"], "node (v22.6.0)", None),
        ), patch("factory_skill_sync.subprocess.run", return_value=proc):
            rc = mod.cmd_list_tech(tmp_path)
        assert rc == 0
        out = capsys.readouterr().out
        assert "react" in out
        assert "nextjs" in out
        assert "python" in out

    def test_nonzero_exit_prints_stderr(self, tmp_path, capsys):
        proc = MagicMock()
        proc.returncode = 1
        proc.stdout = ""
        proc.stderr = "error: something went wrong"
        with patch(
            "factory_skill_sync._resolve_npx",
            return_value=(["node"], "node (v22.6.0)", None),
        ), patch("factory_skill_sync.subprocess.run", return_value=proc):
            rc = mod.cmd_list_tech(tmp_path)
        assert rc == 0
        captured = capsys.readouterr()
        assert "exited 1" in captured.out


# ── cmd_select ──────────────────────────────────────────────────

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
             patch("factory_skill_sync._resolve_npx", return_value=None):
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
             patch("factory_skill_sync._resolve_npx", return_value=None):
            mod.cmd_select(tmp_path, output_format="json")

        data = json.loads(capsys.readouterr().out)
        paths = data["skill_paths_resolved"]
        custom_idx = next(i for i, p in enumerate(paths) if "custom-skills" in p)
        framework_idx = next(i for i, p in enumerate(paths) if "/skills/" in p and "custom" not in p)
        assert custom_idx < framework_idx

    def test_text_output_one_path_per_line(self, tmp_path, capsys):
        self._setup_skills(tmp_path)
        with patch("factory_skill_sync.REPO_ROOT_DEFAULT", tmp_path), \
             patch("factory_skill_sync._resolve_npx", return_value=None):
            mod.cmd_select(tmp_path, output_format="text")

        lines = [l for l in capsys.readouterr().out.splitlines() if l.strip()]
        assert len(lines) >= 2
        for line in lines:
            assert "SKILL.md" in line

    def test_no_skills_returns_empty_list(self, tmp_path, capsys):
        with patch("factory_skill_sync.REPO_ROOT_DEFAULT", tmp_path), \
             patch("factory_skill_sync._resolve_npx", return_value=None), \
             patch.object(su.Path, "home", return_value=tmp_path):
            mod.cmd_select(tmp_path, output_format="json")

        data = json.loads(capsys.readouterr().out)
        assert data["skill_paths_resolved"] == []
        assert data["framework_skill_names"] == []
        assert data["skill_count"] == 0

    def test_warns_when_npx_unavailable(self, tmp_path, capsys):
        self._setup_skills(tmp_path)
        with patch("factory_skill_sync.REPO_ROOT_DEFAULT", tmp_path), \
             patch("factory_skill_sync._resolve_npx", return_value=None):
            mod.cmd_select(tmp_path, output_format="json")

        data = json.loads(capsys.readouterr().out)
        assert len(data["warnings"]) >= 1
        assert "autoskills was SKIPPED" in data["warnings"][0]


# ── CLI argument parsing ────────────────────────────────────────

class TestCliParsing:
    def test_sync_with_tech(self, tmp_path):
        with patch("factory_skill_sync.cmd_sync", return_value=0) as mock_sync:
            with patch("sys.argv", [
                "factory_skill_sync.py", "--repo-root", str(tmp_path),
                "sync", "--tech", "react,nextjs",
            ]):
                with pytest.raises(SystemExit) as exc_info:
                    mod.main()
                assert exc_info.value.code == 0
        assert mock_sync.called
        _args, kwargs = mock_sync.call_args
        assert kwargs["techs"] == ["react", "nextjs"]

    def test_sync_without_tech(self, tmp_path):
        with patch("factory_skill_sync.cmd_sync", return_value=0) as mock_sync:
            with patch("sys.argv", [
                "factory_skill_sync.py", "--repo-root", str(tmp_path),
                "sync",
            ]):
                with pytest.raises(SystemExit) as exc_info:
                    mod.main()
                assert exc_info.value.code == 0
        assert mock_sync.called
        _args, kwargs = mock_sync.call_args
        assert kwargs["techs"] is None

    def test_sync_dry_run_flag(self, tmp_path):
        with patch("factory_skill_sync.cmd_sync", return_value=0) as mock_sync:
            with patch("sys.argv", [
                "factory_skill_sync.py", "--repo-root", str(tmp_path),
                "sync", "--dry-run",
            ]):
                with pytest.raises(SystemExit) as exc_info:
                    mod.main()
                assert exc_info.value.code == 0
        _args, kwargs = mock_sync.call_args
        assert kwargs["dry_run"] is True

    def test_select_json_default(self, tmp_path):
        with patch("factory_skill_sync.cmd_select", return_value=0) as mock_select:
            with patch("sys.argv", [
                "factory_skill_sync.py", "--repo-root", str(tmp_path),
                "select",
            ]):
                with pytest.raises(SystemExit) as exc_info:
                    mod.main()
                assert exc_info.value.code == 0
        _args, kwargs = mock_select.call_args
        assert kwargs["output_format"] == "json"

    def test_select_text_output(self, tmp_path):
        with patch("factory_skill_sync.cmd_select", return_value=0) as mock_select:
            with patch("sys.argv", [
                "factory_skill_sync.py", "--repo-root", str(tmp_path),
                "select", "--output", "text",
            ]):
                with pytest.raises(SystemExit) as exc_info:
                    mod.main()
                assert exc_info.value.code == 0
        _args, kwargs = mock_select.call_args
        assert kwargs["output_format"] == "text"

    def test_list_tech(self, tmp_path):
        with patch("factory_skill_sync.cmd_list_tech", return_value=0) as mock_list:
            with patch("sys.argv", [
                "factory_skill_sync.py", "--repo-root", str(tmp_path),
                "list-tech",
            ]):
                with pytest.raises(SystemExit) as exc_info:
                    mod.main()
                assert exc_info.value.code == 0
        assert mock_list.called

    def test_list_tech_dry_run(self, tmp_path):
        with patch("factory_skill_sync.cmd_list_tech", return_value=0) as mock_list:
            with patch("sys.argv", [
                "factory_skill_sync.py", "--repo-root", str(tmp_path),
                "list-tech", "--dry-run",
            ]):
                with pytest.raises(SystemExit) as exc_info:
                    mod.main()
                assert exc_info.value.code == 0
        _args, kwargs = mock_list.call_args
        assert kwargs["dry_run"] is True

    def test_unknown_command_exits_2(self, tmp_path):
        with patch("sys.argv", [
            "factory_skill_sync.py", "--repo-root", str(tmp_path),
            "bogus",
        ]):
            with pytest.raises(SystemExit) as exc_info:
                mod.main()
            assert exc_info.value.code == 2
