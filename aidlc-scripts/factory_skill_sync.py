#!/usr/bin/env python3
"""factory_skill_sync.py — Sync skills using a local clone of autoskills.

Instead of running `npx autoskills`, this script:
  1. Shallow-clones the autoskills fork into a local cache
  2. Runs the compiled CLI directly with `node` (no build needed)

The fork already handles monorepo scanning internally, so this script
no longer performs its own workspace discovery. Skills live exclusively in
`.agents/skills/` — no symlinks are created in agent-specific folders.

Three subcommands:

  sync      Run autoskills CLI in the project root. For greenfield projects
            (no manifest files), pass --tech to force technologies.

  select    List all skills currently installed and output their paths for use
            in stage input handoffs (skill_paths_resolved[]).

  list-tech List all supported technology IDs from autoskills (useful for
            choosing --tech values, especially in greenfield projects).

Usage:
    python3 aidlc-scripts/factory_skill_sync.py sync [--repo-root PATH] [--dry-run] [--tech react,nextjs]
    python3 aidlc-scripts/factory_skill_sync.py select [--repo-root PATH] [--output json|text]
    python3 aidlc-scripts/factory_skill_sync.py list-tech [--repo-root PATH]

Exit codes:
    0  success (or graceful degradation — Node.js missing, network error)
    1  hard error (file-system write failure)
    2  usage error
"""

from __future__ import annotations

import argparse
import hashlib
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


# ── Constants ─────────────────────────────────────────────────────────────────

AUTOSKILLS_REPO = "https://github.com/Mbg999/autoskills-for-aidlc-factory.git"
AUTOSKILLS_PKG_DIR = Path("packages/autoskills")
AUTOSKILLS_CACHE_DIR = Path(".autoskills-cache")
AUTOSKILLS_ENTRY = Path("index.mjs")
AUTOSKILLS_NODE_MIN = (22, 6, 0)

# (manifest files list removed — no longer used for greenfield detection)


# ── Node.js resolution (simplified) ───────────────────────────────────────────

def _parse_node_version(version_str: str) -> tuple[int, int, int] | None:
    """Parse 'v22.12.0' / '22.12.0' / '22.12' / '22' → (major, minor, patch)."""
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


def _resolve_node() -> tuple[list[str], str] | None:
    """Find Node >= 22.6.0. Returns (prefix cmd list, label) or None."""
    for cmd in (["node"], ["fnm", "exec", "--using=22", "--"],
                ["volta", "run", "--node", "22"]):
        try:
            result = subprocess.run(
                cmd + ["--version"], capture_output=True, text=True, timeout=10
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue
        if result.returncode != 0:
            continue
        version = result.stdout.strip()
        parsed = _parse_node_version(version)
        if parsed is not None and parsed >= AUTOSKILLS_NODE_MIN:
            return cmd, f"{cmd[0]} ({version})"

    # nvm fallback
    nvm_dir = os.environ.get("NVM_DIR") or str(Path.home() / ".nvm")
    nvm_sh = Path(nvm_dir) / "nvm.sh"
    if nvm_sh.exists():
        try:
            result = subprocess.run(
                ["bash", "-lc",
                 f'export NVM_DIR="{nvm_dir}" && source "{nvm_sh}" && '
                 'nvm install 22 >/dev/null 2>&1 && nvm use 22 >/dev/null 2>&1 && node --version'],
                capture_output=True, text=True, timeout=300,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            result = None
        if result and result.returncode == 0:
            version = result.stdout.strip().splitlines()[-1].strip()
            parsed = _parse_node_version(version)
            if parsed is not None and parsed >= AUTOSKILLS_NODE_MIN:
                return ["bash", "-lc",
                        f'export NVM_DIR="{nvm_dir}" && source "{nvm_sh}" && nvm use 22 >/dev/null 2>&1 && node'], \
                       f"nvm ({version})"
    return None


# ── Clone helper ──────────────────────────────────────────────────────────────

def clone_autoskills(dest: Path, dry_run: bool) -> Path:
    """Shallow-clone the autoskills fork."""
    if dry_run:
        print(f"[DRY-RUN] Would clone {AUTOSKILLS_REPO} into {dest}")
        return dest
    if dest.exists() and (dest / ".git").exists():
        print(f"autoskills repo already at {dest}, pulling latest...")
        subprocess.run(
            ["git", "-C", str(dest), "pull", "--ff-only"],
            check=False, capture_output=True,
        )
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Cloning autoskills from {AUTOSKILLS_REPO}...")
    subprocess.run(
        ["git", "clone", "--depth", "1", "--single-branch", "--no-tags",
         AUTOSKILLS_REPO, str(dest)],
        check=True,
    )
    return dest


# ── Build helper ──────────────────────────────────────────────────────────────

def _build_autoskills(autoskills_dir: Path, dry_run: bool) -> None:
    """Install deps and build the TypeScript package (noop when already built)."""
    pkg_dir = autoskills_dir / AUTOSKILLS_PKG_DIR
    entry = pkg_dir / AUTOSKILLS_ENTRY

    # Cache: skip if dist/main.js exists and is newer than all *.ts sources
    if entry.exists():
        entry_mtime = entry.stat().st_mtime
        ts_files = list(pkg_dir.glob("*.ts"))
        if ts_files and all(entry_mtime >= f.stat().st_mtime for f in ts_files):
            print("  autoskills already built (cache hit)")
            return

    pkg_mgr = "pnpm" if (pkg_dir / "pnpm-lock.yaml").exists() else "npm"

    if dry_run:
        print(f"[DRY-RUN] Would build autoskills in {pkg_dir} ({pkg_mgr})")
        return

    print(f"  Building autoskills ({pkg_mgr})...")
    for step, args in (("install", [pkg_mgr, "install"]),
                       ("build", [pkg_mgr, "run", "build"])):
        result = subprocess.run(
            args, cwd=str(pkg_dir), capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"autoskills {step} failed in {pkg_dir}: {result.stderr.strip()[:200]}"
            )

    if not entry.exists():
        raise RuntimeError(
            f"autoskills build did not produce {AUTOSKILLS_ENTRY}"
        )
    print("  autoskills built successfully")


# ── Local autoskills runner ───────────────────────────────────────────────────

def _run_local_autoskills(
    project_dir: Path,
    autoskills_dir: Path,
    techs: list[str] | None = None,
    dry_run: bool = False,
) -> list[Path]:
    """Run the compiled autoskills CLI directly with node."""
    label = str(project_dir.name) or "."
    print(f"  -> {label}/ ", end="", flush=True)

    if dry_run:
        print("[dry-run]")
        return []

    node_cmd, _ = _resolve_node() or ([], "")
    if not node_cmd:
        print("SKIP (no node)")
        return []

    entry = autoskills_dir / AUTOSKILLS_PKG_DIR / AUTOSKILLS_ENTRY
    cmd = node_cmd + [str(entry), "-y", "--path", str(project_dir)]
    if dry_run:
        cmd.append("--dry-run")
    if techs:
        cmd.extend(["--tech", ",".join(techs)])

    try:
        if node_cmd[0] == "bash":
            # node_cmd is a bash -lc wrapper; append the script + args to the command string
            base_cmd = " ".join(node_cmd[1:])  # the -lc part is the command string... wait
            # Actually node_cmd is ["bash", "-lc", "... node"] for nvm. We need to append the entry.
            # The nvm node_cmd is the full bash -lc command ending with "node". We need to run node <entry>.
            # Let's reconstruct.
            bash_cmd = node_cmd[2]  # the -c argument
            # Replace trailing "node" with the full command
            full_bash = bash_cmd.rstrip() + " " + str(entry) + " -y"
            if techs:
                full_bash += " --tech " + ",".join(techs)
            result = subprocess.run(
                ["bash", "-lc", full_bash],
                cwd=str(project_dir), capture_output=True, text=True, timeout=180,
            )
        else:
            result = subprocess.run(
                cmd, cwd=str(project_dir), capture_output=True, text=True, timeout=180,
            )
    except subprocess.TimeoutExpired:
        print("TIMEOUT")
        print(f"    WARNING: autoskills timed out in {project_dir}", file=sys.stderr)
        return []
    except FileNotFoundError:
        print("SKIP (runner not found)")
        return []

    if result.returncode != 0:
        print(f"WARN (exit {result.returncode})")
        for line in result.stderr.strip().splitlines()[:5]:
            print(f"    {line}", file=sys.stderr)
        return []

    print("done")

    for line in (result.stdout + result.stderr).splitlines():
        lower = line.lower()
        if any(kw in lower for kw in ("flagged", "warning", "no skill", "warning:")):
            print(f"    [WARN] {line.strip()}")

    # Collect installed skill directories
    installed: list[Path] = []
    skills_dir = project_dir / ".agents" / "skills"
    if skills_dir.exists():
        for skill_dir in skills_dir.iterdir():
            if skill_dir.is_dir() and (skill_dir / "SKILL.md").exists():
                installed.append(skill_dir)
    return installed


# ── (greenfield detection removed — orchestrator always passes --tech explicitly)

# ── list-tech subcommand ──────────────────────────────────────────────────────

def cmd_list_tech(repo_root: Path, dry_run: bool = False) -> int:
    """List all supported technology IDs from the autoskills skills registry."""
    node = _resolve_node()
    if node is None:
        print("[list-tech] SKIP (no Node >= 22.6.0 available)")
        return 0
    node_cmd, node_label = node

    autoskills_dir = repo_root / AUTOSKILLS_CACHE_DIR
    try:
        clone_autoskills(autoskills_dir, dry_run)
    except subprocess.CalledProcessError as e:
        print(f"WARNING: failed to clone autoskills: {e}")
        return 0

    if dry_run:
        print(f"[DRY-RUN] Would run {node_label} --list-tech")
        return 0

    entry = autoskills_dir / AUTOSKILLS_PKG_DIR / AUTOSKILLS_ENTRY
    try:
        if node_cmd[0] == "bash":
            # nvm-based node_cmd is ["bash", "-lc", "... node"]; append entry + args
            bash_cmd = node_cmd[2]
            full_bash = bash_cmd.rstrip() + " " + str(entry) + " --list-tech"
            result = subprocess.run(
                ["bash", "-lc", full_bash],
                capture_output=True, text=True, timeout=180,
            )
        else:
            cmd = node_cmd + [str(entry), "--list-tech"]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=180,
            )

        if result.returncode == 0:
            print(result.stdout)
        else:
            print(f"[list-tech] autoskills exited {result.returncode}")
            if result.stderr:
                for line in result.stderr.strip().splitlines()[:10]:
                    print(f"  {line}", file=sys.stderr)
    except subprocess.TimeoutExpired:
        print("[list-tech] TIMEOUT")

    # Clean up cache
    cache_dir = repo_root / AUTOSKILLS_CACHE_DIR
    if cache_dir.exists() and not dry_run:
        shutil.rmtree(cache_dir, ignore_errors=True)

    return 0


# ── sync subcommand ───────────────────────────────────────────────────────────

def cmd_sync(repo_root: Path, dry_run: bool = False, techs: list[str] | None = None) -> int:
    node = _resolve_node()
    if node is None:
        # Silent skip — autoskills is best-effort, never blocking.
        return 0
    node_cmd, node_label = node
    print(f"[Sync] using {node_label}")

    autoskills_dir = repo_root / AUTOSKILLS_CACHE_DIR
    try:
        clone_autoskills(autoskills_dir, dry_run)
    except subprocess.CalledProcessError as e:
        print(f"WARNING: failed to clone autoskills: {e}")
        return 0

    # Build not needed — index.mjs handles running main.ts via --experimental-strip-types

    # --tech is always passed explicitly by the orchestrator from the target
    # project's tech stack. No auto-inference here (greenfield detection is
    # misleading when repo_root defaults to the AIDLC toolchain itself).

    installed = _run_local_autoskills(
        repo_root, autoskills_dir, techs=techs, dry_run=dry_run
    )

    if not installed and not dry_run:
        print("[Sync] autoskills installed no skills (no matching technologies detected)")

    # Clean up autoskills cache — never leave build artifacts behind
    cache_dir = repo_root / AUTOSKILLS_CACHE_DIR
    if cache_dir.exists() and not dry_run:
        shutil.rmtree(cache_dir, ignore_errors=True)
        print(f"[Sync] cleaned up {AUTOSKILLS_CACHE_DIR}")

    suffix = " (dry-run)" if dry_run else ""
    print(f"[Sync] done{suffix} — {len(installed)} skill(s) in .agents/skills/")
    return 0


# ── select subcommand ─────────────────────────────────────────────────────────

def cmd_select(repo_root: Path, output_format: str = "json") -> int:
    """Resolve skill_paths_resolved[] for stage input handoffs.

    ALL skills in .agents/skills/ are relevant. Custom-skills (process skills)
    come first to match the skill-protocol load order.
    """
    skills = discover_skills(repo_root)

    custom_paths: list[str] = []
    framework_paths: list[str] = []

    for skill in skills:
        try:
            path_str = str(skill.path.relative_to(repo_root))
        except ValueError:
            path_str = str(skill.path)

        tier = skill.path.parent.parent.name  # "custom-skills" or "skills"
        if tier == "custom-skills":
            custom_paths.append(path_str)
        else:
            framework_paths.append(path_str)

    skill_paths_resolved = custom_paths + framework_paths

    # Extract skill names from .agents/skills/ only for skills_required[] injection.
    # Framework paths from ~/.agents/skills/ (user-global) are excluded — they're
    # already available via fallback resolution and shouldn't be force-injected.
    # Path format: .agents/skills/<skill-name>/SKILL.md → parent.name = <skill-name>
    framework_skill_names = sorted(set(
        Path(p).parent.name for p in framework_paths
        if p.startswith(".agents/skills/")
    ))

    warnings: list[str] = []
    node = _resolve_node()
    if node is None:
        warnings.append(
            f"autoskills build/run was SKIPPED: no Node >= {AUTOSKILLS_NODE_MIN[0]}.{AUTOSKILLS_NODE_MIN[1]} available"
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


# ── CLI ───────────────────────────────────────────────────────────────────────

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
                        help="Preview actions without writing files")
    p_sync.add_argument("--tech", type=str, default=None,
                        help="Force specific technologies (comma-separated), e.g. react,nextjs,python")

    p_select = sub.add_parser("select", help="Output skill_paths_resolved[] for stage handoffs")
    p_select.add_argument("--output", choices=["json", "text"], default="json",
                          help="Output format (default: json)")

    p_list = sub.add_parser("list-tech", help="List all supported technology IDs from autoskills")
    p_list.add_argument("--dry-run", action="store_true",
                        help="Preview without cloning")

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
