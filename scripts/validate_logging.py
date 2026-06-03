#!/usr/bin/env python3
"""validate_logging.py — Check that no factory script uses bare print() for errors/warnings.

Usage:
    python scripts/validate_logging.py

Exits 0 if all scripts pass, 1 if violations are found.
Skipped files: __pycache__, executors/, aidlc-evaluator/
"""
from __future__ import annotations

import glob
import os
import re
import sys

SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "..", "aidlc-scripts")
EXCLUDE_DIRS = {"__pycache__", "executors", "aidlc-evaluator"}

# Pattern: print(...) containing an error/warning-related word as a literal string.
VIOLATION_RE = re.compile(
    r'print\s*\([^)]*\b(?:[Ee]rror|[Ww]arn(?:ing)?)\b'
)


def check_file(path: str) -> list[str]:
    """Check one file for bare print() error/warning violations. Returns list of issue lines."""
    violations: list[str] = []
    rel = os.path.relpath(path, os.path.dirname(SCRIPTS_DIR))
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, 1):
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


def main() -> int:
    if not os.path.isdir(SCRIPTS_DIR):
        print(f"ERROR: scripts directory not found: {SCRIPTS_DIR}", file=sys.stderr)
        return 1

    all_violations: list[str] = []
    for f in sorted(glob.glob(os.path.join(SCRIPTS_DIR, "*.py"))):
        basename = os.path.basename(f)
        if basename == "__init__.py":
            continue
        subdir = os.path.relpath(f, SCRIPTS_DIR).split(os.sep)
        if any(p in EXCLUDE_DIRS for p in subdir):
            continue
        all_violations.extend(check_file(f))

    if all_violations:
        print(f"Found {len(all_violations)} bare print() error/warning violation(s):", file=sys.stderr)
        for v in all_violations:
            print(v, file=sys.stderr)
        return 1

    print("OK — no bare print() error/warning violations detected.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
