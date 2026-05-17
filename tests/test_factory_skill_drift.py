from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "aidlc-scripts"
sys.path.insert(0, str(SCRIPTS))

import factory_skill_drift as mod
from skill_utils import SkillInfo


# ── helpers ───────────────────────────────────────────────────────────────────

def _skill(name="my-skill", framework="", version_range="", has_applies_to=False, path=None):
    return SkillInfo(
        name=name,
        path=path or Path(f"/fake/{name}/SKILL.md"),
        framework=framework,
        version_range=version_range,
        has_applies_to=has_applies_to,
    )


# ── check_drift ───────────────────────────────────────────────────────────────

class TestCheckDrift:
    def test_no_applies_to_returns_no_applies_to(self):
        result = mod.check_drift(_skill(has_applies_to=False))
        assert result.status == "no-applies_to"

    def test_placeholder_framework_skipped(self):
        result = mod.check_drift(_skill(framework="_internal", has_applies_to=True))
        assert result.status == "no-applies_to"

    def test_unknown_framework_returns_unknown(self):
        result = mod.check_drift(_skill(framework="obscure-lang", has_applies_to=True))
        assert result.status == "unknown"
        assert "not in registry map" in result.detail

    def test_registry_error_returns_registry_error(self):
        with patch.object(mod, "resolve_latest", return_value=("npm", None)):
            result = mod.check_drift(_skill(
                framework="react", has_applies_to=True, version_range=">=18.0.0"
            ))
        assert result.status == "registry-error"

    def test_no_version_range_returns_unknown(self):
        with patch.object(mod, "resolve_latest", return_value=("npm", "18.2.0")):
            result = mod.check_drift(_skill(
                framework="react", has_applies_to=True, version_range=""
            ))
        assert result.status == "unknown"
        assert "version not declared" in result.detail

    def test_ok_when_latest_within_range(self):
        with patch.object(mod, "resolve_latest", return_value=("npm", "18.2.0")):
            result = mod.check_drift(_skill(
                framework="react", has_applies_to=True,
                version_range=">=18.0.0 <19.0.0"
            ))
        assert result.status == "ok"
        assert "18.2.0" in result.detail

    def test_stale_when_latest_outside_range(self):
        with patch.object(mod, "resolve_latest", return_value=("npm", "19.0.0")):
            result = mod.check_drift(_skill(
                framework="react", has_applies_to=True,
                version_range=">=18.0.0 <19.0.0"
            ))
        assert result.status == "stale"
        assert "OUTSIDE" in result.detail


# ── resolve_latest ────────────────────────────────────────────────────────────

class TestResolveLatest:
    def test_npm_framework_resolved(self):
        with patch.object(mod, "_latest_npm", return_value="18.2.0") as m:
            eco, ver = mod.resolve_latest("react")
        assert eco == "npm"
        assert ver == "18.2.0"
        m.assert_called_once_with("react")

    def test_pypi_framework_resolved(self):
        with patch.object(mod, "_latest_pypi", return_value="0.111.0") as m:
            eco, ver = mod.resolve_latest("fastapi")
        assert eco == "pip"
        assert ver == "0.111.0"

    def test_cargo_framework_resolved(self):
        with patch.object(mod, "_latest_crates", return_value="1.0.0") as m:
            eco, ver = mod.resolve_latest("axum")
        assert eco == "cargo"
        assert ver == "1.0.0"

    def test_unknown_framework_returns_unknown_eco(self):
        eco, ver = mod.resolve_latest("does-not-exist")
        assert eco == "unknown"
        assert ver is None

    def test_scoped_npm_package(self):
        with patch.object(mod, "_latest_npm", return_value="17.0.0") as m:
            eco, ver = mod.resolve_latest("@angular/core")
        assert eco == "npm"
        m.assert_called_once_with("@angular/core")


# ── npm URL encoding ──────────────────────────────────────────────────────────

class TestLatestNpmEncoding:
    def test_scoped_package_url_encoded(self):
        """_latest_npm must URL-encode @scope/name → @scope%2Fname."""
        captured = {}

        def fake_get_url(url, timeout=15):
            captured["url"] = url
            return {"version": "1.0.0"}

        with patch.object(mod, "_get_url", side_effect=fake_get_url):
            mod._latest_npm("@angular/core")

        assert "%2F" in captured["url"]
        assert "@angular/core" not in captured["url"]

    def test_unscoped_package_not_encoded(self):
        captured = {}

        def fake_get_url(url, timeout=15):
            captured["url"] = url
            return {"version": "1.0.0"}

        with patch.object(mod, "_get_url", side_effect=fake_get_url):
            mod._latest_npm("react")

        assert "/react/" in captured["url"]


# ── CLI: exit codes ───────────────────────────────────────────────────────────

class TestCliExitCodes:
    def _run(self, *args):
        import subprocess
        return subprocess.run(
            [sys.executable, str(SCRIPTS / "factory_skill_drift.py"), *args],
            capture_output=True, text=True,
        )

    def test_no_skills_found_exits_2(self, tmp_path):
        r = self._run("--skill", "does-not-exist-xyz")
        assert r.returncode == 2

    def test_help_exits_0(self):
        r = self._run("--help")
        assert r.returncode == 0
