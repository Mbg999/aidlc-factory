#!/usr/bin/env python3
"""validate_logging.py — Check that no factory script uses bare print() for errors/warnings.

Usage:
    python scripts/validate_logging.py [--root PATH]

Exits 0 if all scripts pass, 1 if violations are found.
Skipped files: __pycache__, executors/, aidlc-evaluator/
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

try:
    from skill_utils import _log
except ImportError:
    def _log(level: str, msg: str, **kwargs) -> None:
        """Fallback _log if skill_utils is not available."""
        stream = sys.stderr if level.upper() in ("ERROR", "WARNING", "CRITICAL") else sys.stdout
        print(f"[{level}] {msg}", file=stream)


def _scripts_dir(root: str | None = None) -> Path:
    """Resolve the aidlc-scripts directory from --root or script-relative path."""
    if root:
        return Path(root).resolve() / "aidlc-scripts"
    return Path(__file__).resolve().parent.parent / "aidlc-scripts"


EXCLUDE_DIRS = {"__pycache__", "executors", "aidlc-evaluator"}

# Pattern: bare print(...) containing an error/warning-related word.
# Negative lookbehind ensures we don't flag _log("ERROR", ...) calls.
# This targets bare print() calls that bypass the _log() infrastructure.
VIOLATION_RE = re.compile(
    r'(?<!_log\()print\s*\([^)]*\b(?:[Ee]rror|[Ww]arn(?:ing)?)\b'
)


def check_file(path: Path, scripts_root: Path) -> list[str]:
    """Check one file for bare print() error/warning violations. Returns list of issue lines."""
    violations: list[str] = []
    rel = path.relative_to(scripts_root.parent)
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        for i, line in enumerate(text.splitlines(), 1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if VIOLATION_RE.search(stripped):
                # Skip class/function definitions and non-print usage
                if any(kw in stripped for kw in ("class ", "def ", '="warning"', '="error"')):
                    continue
                violations.append(f"  {rel}:{i}: {stripped[:120]}")
    except (OSError, UnicodeDecodeError) as e:
        violations.append(f"  {rel}: ERROR reading file: {e}")
    return violations


def main(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        description="Check that no factory script uses bare print() for errors/warnings."
    )
    parser.add_argument(
        "--root", default=None,
        help="Path to repo root containing aidlc-scripts/ (default: parent of scripts/)"
    )
    args = parser.parse_args(argv)

    scripts_root = _scripts_dir(args.root)

    if not scripts_root.is_dir():
        _log("ERROR", f"scripts directory not found: {scripts_root}")
        return 1

    all_violations: list[str] = []
    for f in sorted(scripts_root.glob("*.py")):
        basename = f.name
        if basename == "__init__.py":
            continue
        all_violations.extend(check_file(f, scripts_root))

    if all_violations:
        _log("WARNING", f"Found {len(all_violations)} bare print() error/warning violation(s):")
        for v in all_violations:
            _log("WARNING", v)
        return 1

    print("OK — no bare print() error/warning violations detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
