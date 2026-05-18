from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = REPO_ROOT / "aidlc-scripts"


def _factory_scripts() -> list[Path]:
    return sorted(SCRIPTS.glob("factory_*.py"))


DEP_MESSAGE_RE = re.compile(
    r'(missing dependency|is required).*?({sys\.executable}).*?-m pip install'
)


class TestFactoryDepMessages:
    """Verify all factory scripts use {sys.executable} -m pip in dep messages."""

    def test_all_factory_scripts_use_sys_executable(self):
        bad: list[str] = []
        for f in _factory_scripts():
            text = f.read_text()
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    func = _call_func_name(node)
                    if func in ("print", "_die"):
                        for arg in node.args:
                            if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                                if "pip install " in arg.value and "python3 -m pip" in arg.value:
                                    bad.append(
                                        f"{f.name}:{node.lineno}: hardcoded 'python3 -m pip' "
                                        f"instead of '{{sys.executable}} -m pip'"
                                    )
                                if "pip install " in arg.value and "sys.executable" not in text:
                                    bad.append(
                                        f"{f.name}:{node.lineno}: bare 'pip install' message "
                                        f"without sys.executable"
                                    )
                            elif isinstance(arg, ast.JoinedStr) and "pip install" in text.splitlines()[node.lineno - 1]:
                                has_exec = any(
                                    isinstance(v, ast.FormattedValue)
                                    and hasattr(v, "value")
                                    and isinstance(v.value, ast.Attribute)
                                    and isinstance(v.value.value, ast.Name)
                                    and v.value.value.id == "sys"
                                    and v.value.attr == "executable"
                                    for v in arg.values
                                )
                                if not has_exec:
                                    bad.append(
                                        f"{f.name}:{node.lineno}: f-string with 'pip install' "
                                        f"missing sys.executable"
                                    )
        if bad:
            pytest.fail("\n".join(bad))

    def test_no_bare_pip_install_in_any_factory_script(self):
        bad: list[str] = []
        for f in _factory_scripts():
            text = f.read_text()
            for i, line in enumerate(text.splitlines(), 1):
                if "pip install " in line and "-m pip install" not in line and "pip install -r" not in line and "pip install --upgrade" not in line and "pip install -e" not in line:
                    bad.append(f"{f.name}:{i}: {line.strip()}")
        if bad:
            pytest.fail("\n all dep-install hints must use `sys.executable -m pip`\n" + "\n".join(bad))


def _call_func_name(node: ast.Call) -> str:
    if isinstance(node.func, ast.Name):
        return node.func.id
    if isinstance(node.func, ast.Attribute):
        return node.func.attr
    return ""


class TestFactoryScriptsSyntax:
    """Verify all factory scripts are syntactically valid Python."""

    @pytest.mark.parametrize("script", _factory_scripts(), ids=lambda p: p.name)
    def test_syntax(self, script: Path):
        try:
            ast.parse(script.read_text())
        except SyntaxError as e:
            pytest.fail(f"{script.name}: {e}")

    @pytest.mark.parametrize("script", _factory_scripts(), ids=lambda p: p.name)
    def test_has_sys_import(self, script: Path):
        """All factory scripts must import sys (used in dep messages)."""
        text = script.read_text()
        assert "import sys" in text, f"{script.name}: missing import sys"
