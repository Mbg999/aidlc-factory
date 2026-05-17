from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "aidlc-scripts"
sys.path.insert(0, str(SCRIPTS))

import factory_autoskills as mod


# ── _parse_yaml_sources ───────────────────────────────────────────────────────

class TestParseYamlSources:
    def test_single_entry(self):
        text = """\
sources:
  - name: my-skill
    url: https://example.com/SKILL.md
    sha256: abc123
"""
        entries = mod._parse_yaml_sources(text)
        assert len(entries) == 1
        assert entries[0]["name"] == "my-skill"
        assert entries[0]["url"] == "https://example.com/SKILL.md"
        assert entries[0]["sha256"] == "abc123"

    def test_multiple_entries(self):
        text = """\
sources:
  - name: skill-a
    url: https://example.com/a.md
    sha256: aaa
  - name: skill-b
    url: https://example.com/b.md
    sha256: bbb
"""
        entries = mod._parse_yaml_sources(text)
        assert len(entries) == 2
        assert entries[0]["name"] == "skill-a"
        assert entries[1]["name"] == "skill-b"

    def test_placeholder_entry(self):
        text = """\
sources:
  - name: _placeholder
    url: ""
    sha256: ""
"""
        entries = mod._parse_yaml_sources(text)
        assert entries[0]["name"] == "_placeholder"

    def test_applies_to_nested(self):
        text = """\
sources:
  - name: react-skill
    url: https://example.com/react.md
    sha256: abc
    applies_to:
      framework: react
      version: ">=18.0.0"
"""
        entries = mod._parse_yaml_sources(text)
        assert entries[0]["applies_to"]["framework"] == "react"
        assert entries[0]["applies_to"]["version"] == ">=18.0.0"

    def test_comments_and_blank_lines_ignored(self):
        text = """\
# header comment

sources:
  # section comment
  - name: x
    url: https://x.com
    sha256: xxx
"""
        entries = mod._parse_yaml_sources(text)
        assert len(entries) == 1

    def test_no_sources_block(self):
        assert mod._parse_yaml_sources("name: foo\n") == []

    def test_empty_text(self):
        assert mod._parse_yaml_sources("") == []


# ── _is_placeholder ───────────────────────────────────────────────────────────

class TestIsPlaceholder:
    def test_underscore_name(self):
        assert mod._is_placeholder({"name": "_example", "url": "https://x.com"}) is True

    def test_empty_url(self):
        assert mod._is_placeholder({"name": "real-skill", "url": ""}) is True

    def test_real_entry(self):
        assert mod._is_placeholder({"name": "real-skill", "url": "https://x.com"}) is False


# ── install_skill ─────────────────────────────────────────────────────────────

class TestInstallSkill:
    def _entry(self, name="test-skill", url="https://example.com/SKILL.md", sha=""):
        return {"name": name, "url": url, "sha256": sha}

    def test_placeholder_skipped(self):
        entry = {"name": "_placeholder", "url": ""}
        result = mod.install_skill(entry)
        assert result["status"] == "skipped"

    def test_empty_url_treated_as_placeholder(self):
        # _is_placeholder catches empty URL before the explicit error branch
        entry = {"name": "x", "url": ""}
        result = mod.install_skill(entry)
        assert result["status"] == "skipped"

    def test_malformed_url_error(self):
        with patch.object(mod, "_download", side_effect=ValueError("invalid URL")):
            result = mod.install_skill(self._entry(url="not-a-url"))
        assert result["status"] == "error"
        assert "download failed" in result["detail"]

    def test_network_error(self):
        import urllib.error
        with patch.object(mod, "_download", side_effect=urllib.error.URLError("timeout")):
            result = mod.install_skill(self._entry())
        assert result["status"] == "error"

    def test_sha_mismatch(self):
        data = b"skill content"
        with patch.object(mod, "_download", return_value=data):
            result = mod.install_skill(self._entry(sha="0" * 64))
        assert result["status"] == "error"
        assert "SHA-256 mismatch" in result["detail"]

    def test_sha_match_writes_file(self, tmp_path):
        data = b"---\nname: test-skill\n---\n"
        actual_sha = hashlib.sha256(data).hexdigest()
        with patch.object(mod, "_download", return_value=data), \
             patch.object(mod, "SKILLS_DIR", tmp_path / ".agents" / "skills"):
            result = mod.install_skill(self._entry(sha=actual_sha))
        assert result["status"] == "ok"
        target = tmp_path / ".agents" / "skills" / "test-skill" / "SKILL.md"
        assert target.exists()
        assert target.read_bytes() == data

    def test_dry_run_does_not_write(self, tmp_path):
        data = b"content"
        actual_sha = hashlib.sha256(data).hexdigest()
        with patch.object(mod, "_download", return_value=data), \
             patch.object(mod, "SKILLS_DIR", tmp_path / ".agents" / "skills"):
            result = mod.install_skill(self._entry(sha=actual_sha), dry_run=True)
        assert result["status"] == "dry-run"
        assert not (tmp_path / ".agents" / "skills" / "test-skill" / "SKILL.md").exists()

    def test_idempotent_same_content_skips_write(self, tmp_path):
        data = b"content"
        actual_sha = hashlib.sha256(data).hexdigest()
        target = tmp_path / ".agents" / "skills" / "test-skill" / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_bytes(data)
        with patch.object(mod, "_download", return_value=data), \
             patch.object(mod, "SKILLS_DIR", tmp_path / ".agents" / "skills"):
            result = mod.install_skill(self._entry(sha=actual_sha))
        assert result["status"] == "unchanged"

    def test_no_sha_records_actual(self, tmp_path):
        data = b"content"
        actual_sha = hashlib.sha256(data).hexdigest()
        with patch.object(mod, "_download", return_value=data), \
             patch.object(mod, "SKILLS_DIR", tmp_path / ".agents" / "skills"):
            result = mod.install_skill(self._entry(sha=""))
        assert result["status"] == "ok"
        assert actual_sha[:8] in result["detail"]


# ── check_skill ───────────────────────────────────────────────────────────────

class TestCheckSkill:
    def _entry(self, name="test-skill", sha=""):
        return {"name": name, "url": "https://x.com", "sha256": sha}

    def test_placeholder_skipped(self):
        result = mod.check_skill({"name": "_x", "url": "", "sha256": ""})
        assert result["status"] == "skipped"

    def test_missing_file(self, tmp_path):
        with patch.object(mod, "SKILLS_DIR", tmp_path / ".agents" / "skills"):
            result = mod.check_skill(self._entry())
        assert result["status"] == "missing"

    def test_no_sha_unverified(self, tmp_path):
        target = tmp_path / ".agents" / "skills" / "test-skill" / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"x")
        with patch.object(mod, "SKILLS_DIR", tmp_path / ".agents" / "skills"):
            result = mod.check_skill(self._entry(sha=""))
        assert result["status"] == "unverified"

    def test_sha_matches(self, tmp_path):
        data = b"content"
        sha = hashlib.sha256(data).hexdigest()
        target = tmp_path / ".agents" / "skills" / "test-skill" / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_bytes(data)
        with patch.object(mod, "SKILLS_DIR", tmp_path / ".agents" / "skills"):
            result = mod.check_skill(self._entry(sha=sha))
        assert result["status"] == "ok"

    def test_sha_drift(self, tmp_path):
        target = tmp_path / ".agents" / "skills" / "test-skill" / "SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"tampered")
        with patch.object(mod, "SKILLS_DIR", tmp_path / ".agents" / "skills"):
            result = mod.check_skill(self._entry(sha="0" * 64))
        assert result["status"] == "drift"
