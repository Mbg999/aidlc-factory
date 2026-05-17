from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"
sys.path.insert(0, str(SCRIPTS))

from skill_utils import (
    discover_skills,
    find_workspace_dirs,
    parse_frontmatter,
    sha256_file,
    ver_in_range,
)

REPO_ROOT = Path(__file__).resolve().parent.parent


# ── sha256_file ───────────────────────────────────────────────────────────────

class TestSha256File:
    def test_known_hash(self, tmp_path):
        f = tmp_path / "f.txt"
        f.write_bytes(b"hello")
        assert sha256_file(f) == hashlib.sha256(b"hello").hexdigest()

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_bytes(b"")
        assert sha256_file(f) == hashlib.sha256(b"").hexdigest()

    def test_two_identical_files_same_hash(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_bytes(b"data")
        b.write_bytes(b"data")
        assert sha256_file(a) == sha256_file(b)

    def test_two_different_files_different_hash(self, tmp_path):
        a = tmp_path / "a.txt"
        b = tmp_path / "b.txt"
        a.write_bytes(b"aaa")
        b.write_bytes(b"bbb")
        assert sha256_file(a) != sha256_file(b)


# ── parse_frontmatter ─────────────────────────────────────────────────────────

class TestParseFrontmatter:
    def _skill(self, tmp_path, content: str) -> Path:
        p = tmp_path / "SKILL.md"
        p.write_text(content, encoding="utf-8")
        return p

    def test_simple_fields(self, tmp_path):
        p = self._skill(tmp_path, "---\nname: my-skill\ndescription: does stuff\n---\nbody")
        fm = parse_frontmatter(p)
        assert fm["name"] == "my-skill"
        assert fm["description"] == "does stuff"

    def test_no_frontmatter_returns_empty(self, tmp_path):
        p = self._skill(tmp_path, "# No frontmatter\njust body")
        assert parse_frontmatter(p) == {}

    def test_unclosed_frontmatter_returns_empty(self, tmp_path):
        p = self._skill(tmp_path, "---\nname: foo\n")
        assert parse_frontmatter(p) == {}

    def test_nested_applies_to(self, tmp_path):
        content = "---\nname: nextjs-skill\napplies_to:\n  framework: next\n  version: '>=14.0.0'\n---\n"
        p = self._skill(tmp_path, content)
        fm = parse_frontmatter(p)
        assert fm["name"] == "nextjs-skill"
        assert isinstance(fm["applies_to"], dict)
        assert fm["applies_to"]["framework"] == "next"
        assert fm["applies_to"]["version"] == ">=14.0.0"

    def test_quoted_values_stripped(self, tmp_path):
        p = self._skill(tmp_path, '---\nname: "quoted-skill"\n---\n')
        assert parse_frontmatter(p)["name"] == "quoted-skill"

    def test_comments_ignored(self, tmp_path):
        p = self._skill(tmp_path, "---\n# comment\nname: x\n---\n")
        assert parse_frontmatter(p)["name"] == "x"

    def test_missing_file_returns_empty(self, tmp_path):
        assert parse_frontmatter(tmp_path / "nonexistent.md") == {}

    def test_empty_file_returns_empty(self, tmp_path):
        p = self._skill(tmp_path, "")
        assert parse_frontmatter(p) == {}


# ── ver_in_range ──────────────────────────────────────────────────────────────

class TestVerInRange:
    def test_gte_inside(self):
        assert ver_in_range("15.0.0", ">=14.0.0") is True

    def test_gte_equal(self):
        assert ver_in_range("14.0.0", ">=14.0.0") is True

    def test_gte_below(self):
        assert ver_in_range("13.9.9", ">=14.0.0") is False

    def test_lt_inside(self):
        assert ver_in_range("14.5.0", "<15.0.0") is True

    def test_lt_equal_boundary(self):
        assert ver_in_range("15.0.0", "<15.0.0") is False

    def test_compound_range_inside(self):
        assert ver_in_range("14.2.0", ">=14.0.0 <15.0.0") is True

    def test_compound_range_above(self):
        assert ver_in_range("15.0.1", ">=14.0.0 <15.0.0") is False

    def test_compound_range_below(self):
        assert ver_in_range("13.0.0", ">=14.0.0 <15.0.0") is False

    def test_caret_same_major_inside(self):
        assert ver_in_range("14.2.0", "^14.0.0") is True

    def test_caret_different_major(self):
        assert ver_in_range("15.0.0", "^14.0.0") is False

    def test_tilde_same_minor_inside(self):
        assert ver_in_range("14.1.5", "~14.1.0") is True

    def test_tilde_different_minor(self):
        assert ver_in_range("14.2.0", "~14.1.0") is False

    def test_exact_match(self):
        assert ver_in_range("14.0.0", "==14.0.0") is True

    def test_exact_no_match(self):
        assert ver_in_range("14.0.1", "==14.0.0") is False

    def test_unparseable_version_returns_false(self):
        assert ver_in_range("not-a-version", ">=14.0.0") is False

    def test_empty_range_returns_true(self):
        # no constraints → always covered
        assert ver_in_range("99.0.0", "") is True


# ── discover_skills ───────────────────────────────────────────────────────────

class TestDiscoverSkills:
    def _make_skill(self, base: Path, name: str, content: str = "") -> None:
        d = base / name
        d.mkdir(parents=True, exist_ok=True)
        (d / "SKILL.md").write_text(
            content or f"---\nname: {name}\ndescription: test\n---\n"
        )

    def test_finds_custom_skills(self, tmp_path):
        cs = tmp_path / ".agents" / "custom-skills"
        self._make_skill(cs, "my-skill")
        skills = discover_skills(tmp_path)
        assert any(s.name == "my-skill" for s in skills)

    def test_finds_framework_skills(self, tmp_path):
        fs = tmp_path / ".agents" / "skills"
        self._make_skill(fs, "nextjs")
        skills = discover_skills(tmp_path)
        assert any(s.name == "nextjs" for s in skills)

    def test_custom_skill_takes_priority_over_framework(self, tmp_path):
        cs = tmp_path / ".agents" / "custom-skills"
        fs = tmp_path / ".agents" / "skills"
        self._make_skill(cs, "overlap", "---\nname: overlap\ndescription: custom\n---\n")
        self._make_skill(fs, "overlap", "---\nname: overlap\ndescription: framework\n---\n")
        skills = discover_skills(tmp_path)
        matches = [s for s in skills if s.name == "overlap"]
        assert len(matches) == 1
        assert "custom" in str(matches[0].path)

    def test_only_filter(self, tmp_path):
        cs = tmp_path / ".agents" / "custom-skills"
        self._make_skill(cs, "skill-a")
        self._make_skill(cs, "skill-b")
        skills = discover_skills(tmp_path, only="skill-a")
        assert len(skills) == 1
        assert skills[0].name == "skill-a"

    def test_only_filter_no_match_returns_empty(self, tmp_path):
        cs = tmp_path / ".agents" / "custom-skills"
        self._make_skill(cs, "skill-a")
        assert discover_skills(tmp_path, only="does-not-exist") == []

    def test_skips_dirs_without_skill_md(self, tmp_path):
        cs = tmp_path / ".agents" / "custom-skills"
        (cs / "no-skill-md").mkdir(parents=True)
        # Patch home so global ~/.agents/skills doesn't leak into the result
        import skill_utils as su
        with patch.object(su.Path, "home", return_value=tmp_path):
            skills = discover_skills(tmp_path)
        assert skills == []

    def test_applies_to_populated(self, tmp_path):
        cs = tmp_path / ".agents" / "custom-skills"
        content = "---\nname: react-skill\napplies_to:\n  framework: react\n  version: '>=18.0.0'\n---\n"
        self._make_skill(cs, "react-skill", content)
        skills = discover_skills(tmp_path)
        assert skills[0].framework == "react"
        assert skills[0].version_range == ">=18.0.0"
        assert skills[0].has_applies_to is True

    def test_no_applies_to(self, tmp_path):
        cs = tmp_path / ".agents" / "custom-skills"
        self._make_skill(cs, "universal")
        skill = discover_skills(tmp_path)[0]
        assert skill.has_applies_to is False
        assert skill.framework == ""


# ── find_workspace_dirs ───────────────────────────────────────────────────────

class TestFindWorkspaceDirs:
    def test_root_always_included(self, tmp_path):
        result = find_workspace_dirs(tmp_path)
        assert tmp_path in result

    def test_detects_package_json(self, tmp_path):
        (tmp_path / "package.json").write_text("{}")
        result = find_workspace_dirs(tmp_path)
        assert tmp_path in result

    def test_detects_sub_package(self, tmp_path):
        sub = tmp_path / "backend"
        sub.mkdir()
        (sub / "package.json").write_text("{}")
        result = find_workspace_dirs(tmp_path)
        assert sub in result

    def test_detects_pyproject_toml(self, tmp_path):
        sub = tmp_path / "services" / "api"
        sub.mkdir(parents=True)
        (sub / "pyproject.toml").write_text("")
        result = find_workspace_dirs(tmp_path)
        assert sub in result

    def test_excludes_node_modules(self, tmp_path):
        nm = tmp_path / "node_modules" / "some-pkg"
        nm.mkdir(parents=True)
        (nm / "package.json").write_text("{}")
        result = find_workspace_dirs(tmp_path)
        assert nm not in result

    def test_excludes_dot_git(self, tmp_path):
        git = tmp_path / ".git"
        git.mkdir()
        (git / "package.json").write_text("{}")
        result = find_workspace_dirs(tmp_path)
        assert git not in result

    def test_max_depth_respected(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "d" / "e"
        deep.mkdir(parents=True)
        (deep / "package.json").write_text("{}")
        result = find_workspace_dirs(tmp_path, max_depth=4)
        assert deep not in result

    def test_max_depth_at_boundary_included(self, tmp_path):
        at_depth = tmp_path / "a" / "b" / "c" / "d"
        at_depth.mkdir(parents=True)
        (at_depth / "package.json").write_text("{}")
        result = find_workspace_dirs(tmp_path, max_depth=4)
        assert at_depth in result

    def test_no_manifest_only_root(self, tmp_path):
        sub = tmp_path / "subdir"
        sub.mkdir()
        result = find_workspace_dirs(tmp_path)
        assert result == [tmp_path]
