#!/usr/bin/env python3
"""factory_audit_writes.py — Post-spawn file-write audit for the AIDLC Orchestrator.

Checks that files created by a stage agent respect the locks_required[] globs.
Uses `git diff --name-only --diff-filter=A` to detect newly created files, then
cross-references each path against the declared lock globs.

Usage
-----
    factory_audit_writes.py <run-id> <holder> --locks <glob> [<glob>...]

Exit codes:
    0 — all new files are within declared lock globs
    1 — one or more files outside declared lock globs
    2 — usage error
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import subprocess
import sys
from pathlib import Path


def _die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def get_new_files(repo_root: Path) -> list[str]:
    """Return list of newly created files (git Added) relative to repo_root."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=A", "--relative"],
            capture_output=True, text=True, cwd=str(repo_root),
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        _die("git diff timed out")
    except FileNotFoundError:
        _die("git not found in PATH")
    if result.returncode != 0:
        _die(f"git diff failed: {result.stderr.strip()}")
    return [f for f in result.stdout.splitlines() if f.strip()]


def path_matches_any_glob(path: str, globs: list[str]) -> bool:
    """Check if path matches any of the glob patterns."""
    for g in globs:
        if fnmatch.fnmatchcase(path, g):
            return True
        # Also try with **/ prefix for globs like "src/**"
        if g.endswith("/**") and path.startswith(g[:-3]):
            return True
        if fnmatch.fnmatchcase(path, g.rstrip("/") + "/*"):
            return True
    return False


def main() -> None:
    p = argparse.ArgumentParser(description="Post-spawn file-write audit")
    p.add_argument("run_id", help="run identifier")
    p.add_argument("holder", help="holder name (e.g. code-generator:auth)")
    p.add_argument("--locks", nargs="+", required=True,
                   help="declared lock globs from the unit's input handoff")
    p.add_argument("--repo-root", default=None,
                   help="repo root (default: auto-detect from CWD)")
    p.add_argument("--json", action="store_true",
                   help="output as JSON")
    args = p.parse_args()

    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path.cwd()

    new_files = get_new_files(repo_root)
    violations: list[str] = []
    for f in new_files:
        if not path_matches_any_glob(f, args.locks):
            violations.append(f)

    result = {
        "run_id": args.run_id,
        "holder": args.holder,
        "locks": args.locks,
        "new_files_count": len(new_files),
        "violations_count": len(violations),
        "violations": violations,
        "status": "violation" if violations else "ok",
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Audit: {args.holder} @ {args.run_id}")
        print(f"  New files: {len(new_files)}")
        if violations:
            print(f"  ❌ {len(violations)} violation(s) — files outside declared locks:")
            for v in violations:
                print(f"     - {v}")
        else:
            print(f"  ✅ All files match lock globs")
        if not new_files and not violations:
            print(f"  (no new files detected)")

    if violations:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
