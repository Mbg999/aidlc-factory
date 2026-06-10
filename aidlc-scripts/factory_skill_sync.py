#!/usr/bin/env python3
"""factory_skill_sync.py — Sync skills via npx @aidlc-factory/autoskills.

Three subcommands:

  sync      Run `npx @aidlc-factory/autoskills` in the project root to install
            framework skills. Pass --tech to force technologies (required for
            greenfield projects).

  select    List all skills currently installed and output their paths for use
            in stage input handoffs (skill_paths_resolved[]).

  list-tech List all supported technology IDs from the published autoskills
            package via `npx ... --list-tech`.

Usage:
    python3 aidlc-scripts/factory_skill_sync.py sync [--repo-root PATH] [--dry-run] [--tech react,nextjs]
    python3 aidlc-scripts/factory_skill_sync.py select [--repo-root PATH] [--output json|text]
    python3 aidlc-scripts/factory_skill_sync.py list-tech [--repo-root PATH]

Exit codes:
    0  success (or graceful degradation — npx missing, network error)
    1  hard error (file-system write failure)
    2  usage error
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

_SCRIPT_DIR = Path(__file__).parent
REPO_ROOT_DEFAULT = _SCRIPT_DIR.parent

sys.path.insert(0, str(_SCRIPT_DIR))
from skill_utils import discover_skills, sha256_file


PACKAGE_NAME = "@aidlc-factory/autoskills"
NODE_MIN = (22, 6, 0)


def _parse_node_version(version_str: str) -> tuple[int, int, int] | None:
    raw = version_str.strip().lstrip("v")
    if not raw:
        return None
    parts = raw.split(".")
    try:
        nums = [int(p) for p in parts[:3]]
    except ValueError:
        return None
    while len(nums) < 3:
        nums.append(0)
    return (nums[0], nums[1], nums[2])


def _resolve_npx() -> tuple[list[str], str] | None:
    """Check npx is available and Node >= 22.6.0. Returns (node cmd list, label) or None."""
    for node_cmd in (["node"], ["fnm", "exec", "--using=22", "--"],
                     ["volta", "run", "--node", "22"]):
        try:
            result = subprocess.run(
                node_cmd + ["--version"], capture_output=True, text=True, timeout=10
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue
        if result.returncode != 0:
            continue
        parsed = _parse_node_version(result.stdout.strip())
        if parsed is not None and parsed >= NODE_MIN:
            return node_cmd, f"{node_cmd[0]} ({result.stdout.strip()})"
    return None


def _run_npx(
    npx_cmd: list[str],
    args: list[str],
    project_dir: Path | None = None,
    timeout: int = 180,
) -> subprocess.CompletedProcess | None:
    cmd = npx_cmd + ["npx", "-y", PACKAGE_NAME] + args
    cwd = str(project_dir) if project_dir else None
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None


def _collect_installed_skills(project_dir: Path) -> list[Path]:
    installed: list[Path] = []
    skills_dir = project_dir / ".agents" / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                installed.append(skill_dir)
    return installed


# ── list-tech subcommand ──────────────────────────────────────

def cmd_list_tech(repo_root: Path, dry_run: bool = False) -> int:
    resolved = _resolve_npx()
    if resolved is None:
        print("[list-tech] SKIP (no Node >= 22.6.0 available)")
        return 0

    if dry_run:
        print(f"[DRY-RUN] Would run: npx {PACKAGE_NAME} --list-tech")
        return 0

    result = subprocess.run(
        ["npx", "-y", PACKAGE_NAME, "--list-tech"],
        capture_output=True, text=True, timeout=180,
    )

    if result.returncode == 0:
        print(result.stdout)
    else:
        print(f"[list-tech] autoskills exited {result.returncode}")
        if result.stderr:
            for line in result.stderr.strip().splitlines()[:10]:
                print(f"  {line}", file=sys.stderr)

    return 0


# ── sync subcommand ───────────────────────────────────────────

def cmd_sync(repo_root: Path, dry_run: bool = False, techs: list[str] | None = None) -> int:
    resolved = _resolve_npx()
    if resolved is None:
        return 0
    npx_cmd, node_label = resolved
    print(f"[Sync] using {node_label}")

    if dry_run:
        tech_flag = f" --tech {','.join(techs)}" if techs else ""
        print(f"[DRY-RUN] Would run: npx {PACKAGE_NAME} -y --path {repo_root}{tech_flag}")
        installed = _collect_installed_skills(repo_root)
        print(f"[Sync] dry-run — currently {len(installed)} skill(s) in .agents/skills/")
        return 0

    args = ["-y", "--path", str(repo_root)]
    if techs:
        args.extend(["--tech", ",".join(techs)])

    result = _run_npx(npx_cmd, args, project_dir=repo_root)
    if result is None:
        print("[Sync] SKIP (npx runner failed)")
        return 0

    if result.returncode != 0:
        print(f"[Sync] autoskills exited {result.returncode}")
        for line in result.stderr.strip().splitlines()[:5]:
            print(f"    {line}", file=sys.stderr)

    for line in (result.stdout + result.stderr).splitlines():
        lower = line.lower()
        if any(kw in lower for kw in ("flagged", "warning", "no skill", "warning:")):
            print(f"    [WARN] {line.strip()}")

    installed = _collect_installed_skills(repo_root)
    if not installed:
        print("[Sync] autoskills installed no skills (no matching technologies detected)")

    print(f"[Sync] done — {len(installed)} skill(s) in .agents/skills/")
    return 0


# ── select subcommand ─────────────────────────────────────────

def cmd_select(repo_root: Path, output_format: str = "json") -> int:
    skills = discover_skills(repo_root)

    custom_paths: list[str] = []
    framework_paths: list[str] = []

    for skill in skills:
        try:
            path_str = str(skill.path.relative_to(repo_root))
        except ValueError:
            path_str = str(skill.path)

        tier = skill.path.parent.parent.name
        if tier == "custom-skills":
            custom_paths.append(path_str)
        else:
            framework_paths.append(path_str)

    skill_paths_resolved = custom_paths + framework_paths

    framework_skill_names = sorted(set(
        Path(p).parent.name for p in framework_paths
        if p.startswith(".agents/skills/")
    ))

    warnings: list[str] = []
    resolved = _resolve_npx()
    if resolved is None:
        warnings.append(
            f"autoskills was SKIPPED: no Node >= {NODE_MIN[0]}.{NODE_MIN[1]} available"
        )
    elif not framework_paths:
        warnings.append(
            "no framework skills resolved — autoskills detected no matching technologies"
        )

    result = {
        "skill_paths_resolved": skill_paths_resolved,
        "framework_skill_names": framework_skill_names,
        "skill_count": len(skill_paths_resolved),
        "warnings": warnings,
    }

    if output_format == "json":
        print(json.dumps(result, indent=2))
    else:
        for path in skill_paths_resolved:
            print(path)

    return 0


# ── CLI ───────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--repo-root", type=Path, default=None,
        help="Repository root (default: parent of aidlc-scripts/)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_sync = sub.add_parser("sync", help="Install skills via autoskills")
    p_sync.add_argument("--dry-run", action="store_true",
                        help="Preview actions without installing")
    p_sync.add_argument("--tech", type=str, default=None,
                        help="Force specific technologies (comma-separated), e.g. react,nextjs,python")

    p_select = sub.add_parser("select", help="Output skill_paths_resolved[] for stage handoffs")
    p_select.add_argument("--output", choices=["json", "text"], default="json",
                          help="Output format (default: json)")

    p_list = sub.add_parser("list-tech", help="List all supported technology IDs from autoskills")
    p_list.add_argument("--dry-run", action="store_true",
                        help="Preview without calling npx")

    args = parser.parse_args()
    repo_root = args.repo_root or REPO_ROOT_DEFAULT

    if args.command == "sync":
        techs = None
        if args.tech:
            techs = [t.strip() for t in args.tech.split(",") if t.strip()]
        sys.exit(cmd_sync(repo_root, dry_run=getattr(args, "dry_run", False), techs=techs))
    elif args.command == "select":
        sys.exit(cmd_select(repo_root, output_format=getattr(args, "output", "json")))
    elif args.command == "list-tech":
        sys.exit(cmd_list_tech(repo_root, dry_run=getattr(args, "dry_run", False)))
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
