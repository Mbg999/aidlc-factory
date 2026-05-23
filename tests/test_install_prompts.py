"""Snapshot tests for install_aidlc.py interactive prompts.

Guards against regression of B9 — interactive prompts must keep the
WHAT + WHY + EXAMPLE + DEFAULT structure with English copy. If a prompt's
wording changes, update the expected substrings here intentionally.
"""

from __future__ import annotations

import io
import sys
from pathlib import Path
from unittest.mock import patch

import pytest


SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "aidlc-scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

import install_aidlc as M  # noqa: E402


# ── interactive_choose_tools ──────────────────────────────────────────────────


class TestInteractiveChooseTools:
    def test_prompt_includes_what_why_example(self, capsys, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO("2\n"))
        result = M.interactive_choose_tools()
        out = capsys.readouterr().out
        assert "Which agentic coding tool(s) do you use?" in out
        assert "AIDLC will install" in out  # WHY
        assert "Pick one number" in out  # HOW
        assert "Examples:" in out
        assert "'2'    -> Claude Code only" in out
        assert "'2,4'  -> Claude Code + OpenCode" in out
        assert result == ["claude"]

    def test_each_tool_has_description(self, capsys, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO("2\n"))
        M.interactive_choose_tools()
        out = capsys.readouterr().out
        for tool in M.VALID_TOOLS:
            assert tool in out
            # description column non-empty for each tool
            assert M.TOOL_DESCRIPTIONS[tool] in out

    def test_invalid_input_diagnostic(self, capsys, monkeypatch):
        # First a junk string, then a number out of range, then valid
        monkeypatch.setattr("sys.stdin", io.StringIO("foo\n99\n2\n"))
        result = M.interactive_choose_tools()
        out = capsys.readouterr().out
        assert "doesn't look right" in out  # diagnostic for non-numeric
        assert "Out of range" in out         # diagnostic for too-large
        assert result == ["claude"]

    def test_empty_input_diagnostic(self, capsys, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO("\n2\n"))
        result = M.interactive_choose_tools()
        out = capsys.readouterr().out
        assert "Please enter a number" in out
        assert result == ["claude"]

    def test_multi_select(self, capsys, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO("2,4\n"))
        result = M.interactive_choose_tools()
        # order is preserved + dedupe
        assert result == ["claude", "opencode"]

    def test_multi_select_dedupes(self, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO("2,2,4\n"))
        result = M.interactive_choose_tools()
        assert result == ["claude", "opencode"]


# ── ask_orchestrator was removed — orchestrator is always installed ──────────────


# ── _prompt_destination ───────────────────────────────────────────────────────


class TestPromptDestination:
    def test_prompt_includes_examples(self, capsys, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO("\n"))  # accept default
        cwd = Path.cwd()
        result = M._prompt_destination()
        out = capsys.readouterr().out
        assert "Where should AIDLC be installed?" in out
        assert "Examples:" in out
        assert ".                           current directory" in out
        assert "~/projects/my-app           absolute path with home expansion" in out
        assert "full absolute path" in out
        assert "Destination [default:" in out
        assert result == cwd

    def test_explicit_path(self, monkeypatch, tmp_path):
        monkeypatch.setattr("sys.stdin", io.StringIO(f"{tmp_path}\n"))
        assert M._prompt_destination() == tmp_path.resolve()

    def test_strips_quotes(self, monkeypatch, tmp_path):
        # path with quotes (e.g. shell-pasted)
        monkeypatch.setattr("sys.stdin", io.StringIO(f"'{tmp_path}'\n"))
        assert M._prompt_destination() == tmp_path.resolve()


# ── language hygiene ──────────────────────────────────────────────────────────


class TestLanguageHygiene:
    """B9 requires all prompt copy in English. Catch Spanish leakage."""

    SPANISH_TOKENS = (
        " sí ", " también ", " elige ", " cuál ", " seleccione ",
        " predeterminado ", " continuar ", " instalar ", " omitir ",
    )

    def test_choose_tools_english_only(self, capsys, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO("2\n"))
        M.interactive_choose_tools()
        out = capsys.readouterr().out.lower()
        for token in self.SPANISH_TOKENS:
            assert token not in out, f"Spanish token {token!r} found in tool selector"



    def test_destination_english_only(self, capsys, monkeypatch):
        monkeypatch.setattr("sys.stdin", io.StringIO("\n"))
        M._prompt_destination()
        out = capsys.readouterr().out.lower()
        for token in self.SPANISH_TOKENS:
            assert token not in out, f"Spanish token {token!r} found in destination prompt"
