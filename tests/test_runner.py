"""Test executors/runner.py cross-platform path handling.

Regression test for Bug 8 — .venv/bin hardcoded on Windows.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

SCRIPTS = Path(__file__).resolve().parent.parent / "aidlc-scripts"


@pytest.fixture
def runner_mod():
    import importlib.util
    runner_path = SCRIPTS / "executors" / "runner.py"
    spec = importlib.util.spec_from_file_location("runner", runner_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class TestVenvBin:
    def test_venv_bin_unix(self, runner_mod):
        with patch.object(sys, "platform", "linux"):
            result = runner_mod._venv_bin()
        assert result == ".venv/bin"

    def test_venv_bin_macos(self, runner_mod):
        with patch.object(sys, "platform", "darwin"):
            result = runner_mod._venv_bin()
        assert result == ".venv/bin"

    def test_venv_bin_windows(self, runner_mod):
        with patch.object(sys, "platform", "win32"):
            result = runner_mod._venv_bin()
        assert result == ".venv\\Scripts"

    def test_venv_bin_cygwin(self, runner_mod):
        with patch.object(sys, "platform", "cygwin"):
            result = runner_mod._venv_bin()
        assert result == ".venv/bin"


class TestAllowedBases:
    def test_windows_includes_scripts(self, runner_mod):
        """On Windows, allowed bases must include .venv\\Scripts, not .venv/bin."""
        with patch.object(sys, "platform", "win32"):
            bases = runner_mod._allowed_bases()
        paths = [str(b) for b in bases]
        assert any("Scripts" in p for p in paths), (
            f"No .venv\\\\Scripts in allowed bases: {paths}"
        )

    def test_unix_includes_bin(self, runner_mod):
        with patch.object(sys, "platform", "linux"):
            bases = runner_mod._allowed_bases()
        paths = [str(b) for b in bases]
        assert any(b.endswith(".venv/bin") for b in paths), (
            f"No .venv/bin in allowed bases: {paths}"
        )


class TestIsAllowed:
    def test_venv_script_base_allowed_windows(self, runner_mod):
        """.venv\\Scripts base must be allowed on Windows."""
        with patch.object(sys, "platform", "win32"):
            bases = runner_mod._allowed_bases()
            for base in bases:
                if "Scripts" in str(base):
                    assert runner_mod._is_allowed(base), (
                        f"Base {base} should be allowed on win32"
                    )
                    return
        pytest.fail("No Scripts base found on win32")

    def test_venv_bin_base_allowed_unix(self, runner_mod):
        with patch.object(sys, "platform", "linux"):
            bases = runner_mod._allowed_bases()
            for base in bases:
                if base.match(".venv/bin"):
                    assert runner_mod._is_allowed(base), (
                        f"Base {base} should be allowed on linux"
                    )
                    return
        pytest.fail("No .venv/bin base found on linux")
