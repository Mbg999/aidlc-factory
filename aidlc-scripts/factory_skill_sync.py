#!/usr/bin/env python3
"""factory_skill_sync.py — Sync skills using a local clone of autoskills.

Instead of running `npx autoskills`, this script:
  1. Shallow-clones the autoskills fork into a local cache
  2. Builds the TypeScript package (cached when already built)
  3. Runs the compiled CLI directly with `node`

The fork already handles monorepo scanning internally, so this script
no longer performs its own workspace discovery.

Two subcommands:

  sync   Run autoskills CLI in the project root. For greenfield projects
         (no manifest files), pass --tech to force technologies.

  select List all skills currently installed and output their paths for use
         in stage input handoffs (skill_paths_resolved[]).

Usage:
    python3 aidlc-scripts/factory_skill_sync.py sync [--repo-root PATH] [--dry-run] [--tech react,nextjs]
    python3 aidlc-scripts/factory_skill_sync.py select [--repo-root PATH] [--output json|text]

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
AUTOSKILLS_ENTRY = AUTOSKILLS_PKG_DIR / "dist" / "main.js"
AUTOSKILLS_NODE_MIN = (22, 6, 0)

# Manifest files used to detect whether a project is greenfield.
_MANIFEST_FILES = frozenset({
    "package.json", "pyproject.toml", "Cargo.toml", "go.mod",
    "requirements.txt", "setup.py", "Pipfile", "Gemfile",
    "composer.json", "build.gradle", "build.gradle.kts", "pom.xml",
    "deno.json", "deno.jsonc", "bun.lockb", "bun.lock", "bunfig.toml",
})


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
    cmd = node_cmd + [str(entry), "-y"]
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


# ── Greenfield detection ──────────────────────────────────────────────────────

def _is_greenfield(project_dir: Path) -> bool:
    """True if no recognised manifest files exist in project_dir."""
    return not any((project_dir / m).exists() for m in _MANIFEST_FILES)


def _infer_techs_for_greenfield(project_dir: Path) -> list[str]:
    """Best-effort tech inference when no manifests are present.

    For AIDLC repos (this codebase), we detect Python via requirements.txt
    or pyproject.toml — but those would make _is_greenfield return False.
    When truly greenfield, we return an empty list and let the user pass
    --tech if they want to force something.
    """
    return []


# ── consolidation helpers (kept for edge-cases) ─────────────────────────────

def _copy_skill(src: Path, dest: Path) -> None:
    """Copy all files from src skill dir to dest, preserving sub-structure."""
    real_src = src.resolve() if src.is_symlink() else src
    dest.mkdir(parents=True, exist_ok=True)
    for file in real_src.rglob("*"):
        if file.is_file():
            rel = file.relative_to(real_src)
            dest_file = dest / rel
            dest_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(file, dest_file)


def _remove(path: Path) -> None:
    """Remove a path whether it is a directory, a symlink, or a symlink-to-dir."""
    if path.is_symlink():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(path, ignore_errors=True)


def _skill_is_current(src: Path, dest: Path) -> bool:
    """True if dest/SKILL.md already has the same SHA-256 as src/SKILL.md."""
    src_md = src / "SKILL.md"
    dest_md = dest / "SKILL.md"
    return (
        src_md.exists()
        and dest_md.exists()
        and sha256_file(src_md) == sha256_file(dest_md)
    )


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

    try:
        _build_autoskills(autoskills_dir, dry_run)
    except RuntimeError as e:
        print(f"WARNING: autoskills build failed: {e}")
        return 0

    # Determine whether to pass --tech
    inferred_techs = techs
    if inferred_techs is None and _is_greenfield(repo_root):
        inferred_techs = _infer_techs_for_greenfield(repo_root)
        if inferred_techs:
            print(f"[Sync] greenfield project — forcing techs: {','.join(inferred_techs)}")

    installed = _run_local_autoskills(
        repo_root, autoskills_dir, techs=inferred_techs, dry_run=dry_run
    )

    if not installed and not dry_run:
        print("[Sync] autoskills installed no skills (no matching technologies detected)")

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

    args = parser.parse_args()
    repo_root = args.repo_root or REPO_ROOT_DEFAULT

    if args.command == "sync":
        techs = None
        if args.tech:
            techs = [t.strip() for t in args.tech.split(",") if t.strip()]
        sys.exit(cmd_sync(repo_root, dry_run=getattr(args, "dry_run", False), techs=techs))
    elif args.command == "select":
        sys.exit(cmd_select(repo_root, output_format=getattr(args, "output", "json")))
    else:
        parser.print_help()
        sys.exit(2)


if __name__ == "__main__":
    main()
