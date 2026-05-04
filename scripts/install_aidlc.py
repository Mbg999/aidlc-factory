#!/usr/bin/env python3
"""
install_aidlc.py

Simple installer to copy AI-DLC rule files into the chosen agent integration
location (Kiro, Amazon Q, Cursor, Cline, Claude Code, GitHub Copilot, Other).

Usage examples:
  python scripts/install_aidlc.py --tool cursor
  python scripts/install_aidlc.py --tool copilot --yes
  python scripts/install_aidlc.py --tool kiro --dry-run
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
import textwrap


def copy_tree(src: Path, dst: Path, dry_run: bool) -> None:
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {src}")
    if dry_run:
        print(f"[DRY-RUN] Would copy {src} -> {dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(src, dst, dirs_exist_ok=True)
    except TypeError:
        # older Python fallback
        if not dst.exists():
            shutil.copytree(src, dst)
        else:
            for p in src.rglob("*"):
                rel = p.relative_to(src)
                target = dst / rel
                if p.is_dir():
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(p, target)


def write_file(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[DRY-RUN] Would write file {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def run_install(tool: str, src_rules: Path, src_details: Path, target_root: Path, dry_run: bool, include_scripts: bool = True) -> None:
    core_md = src_rules / "core-workflow.md"
    if not core_md.exists():
        core_md = src_rules / "core-workflow.md"
    core_content = core_md.read_text(encoding="utf-8") if core_md.exists() else ""

    if tool == "kiro":
        dest_rules = target_root / ".kiro" / "steering" / "aws-aidlc-rules"
        dest_details = target_root / ".kiro" / "aws-aidlc-rule-details"
        print(f"Installing for Kiro: {dest_rules}")
        copy_tree(src_rules, dest_rules, dry_run)
        copy_tree(src_details, dest_details, dry_run)

    elif tool == "amazonq":
        dest_rules = target_root / ".amazonq" / "rules" / "aws-aidlc-rules"
        dest_details = target_root / ".amazonq" / "aws-aidlc-rule-details"
        print(f"Installing for Amazon Q Developer: {dest_rules}")
        copy_tree(src_rules, dest_rules, dry_run)
        copy_tree(src_details, dest_details, dry_run)

    elif tool == "cursor":
        dest_rules_file = target_root / ".cursor" / "rules" / "ai-dlc-workflow.mdc"
        frontmatter = textwrap.dedent("""\
        ---
        description: "AI-DLC (AI-Driven Development Life Cycle) adaptive workflow for software development"
        alwaysApply: true
        ---

        """)
        print(f"Installing for Cursor: {dest_rules_file}")
        write_file(dest_rules_file, frontmatter + core_content, dry_run)
        dest_details = target_root / ".aidlc-rule-details"
        copy_tree(src_details, dest_details, dry_run)

    elif tool == "cline":
        dest = target_root / ".clinerules" / "core-workflow.md"
        print(f"Installing for Cline: {dest}")
        write_file(dest, core_content, dry_run)
        dest_details = target_root / ".aidlc-rule-details"
        copy_tree(src_details, dest_details, dry_run)

    elif tool == "claude":
        dest = target_root / "CLAUDE.md"
        print(f"Installing for Claude Code: {dest}")
        write_file(dest, core_content, dry_run)
        dest_details = target_root / ".aidlc-rule-details"
        copy_tree(src_details, dest_details, dry_run)

    elif tool == "copilot":
        dest = target_root / ".github" / "copilot-instructions.md"
        print(f"Installing for GitHub Copilot: {dest}")
        write_file(dest, core_content, dry_run)
        dest_details = target_root / ".aidlc-rule-details"
        copy_tree(src_details, dest_details, dry_run)

    elif tool == "other":
        dest = target_root / "AGENTS.md"
        print(f"Installing generic AGENTS.md: {dest}")
        write_file(dest, core_content, dry_run)
        dest_details = target_root / ".aidlc-rule-details"
        copy_tree(src_details, dest_details, dry_run)

    else:
        raise ValueError(f"Unknown tool: {tool}")

    print("\nInstallation summary: (source -> target)")
    print(f"  rules: {src_rules} -> {target_root}")
    print(f"  details: {src_details} -> {target_root}")

    # Copy helper scripts (subagents, executors, aidlc-evaluator) from this repo
    if include_scripts:
        repo_root = src_rules.parent.parent
        scripts_dir = repo_root / "scripts"
        to_copy = ["subagents", "executors", "aidlc-evaluator"]
        printed_any = False
        for sub in to_copy:
            ssrc = scripts_dir / sub
            if ssrc.exists():
                printed_any = True
                dest = target_root / "scripts" / sub
                print(f"Copying scripts: {ssrc} -> {dest}")
                copy_tree(ssrc, dest, dry_run)
        if printed_any:
            print(f"  scripts: {scripts_dir} -> {target_root / 'scripts'}")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Install AI-DLC rules into a project for a selected agent tool")
    p.add_argument("--tool", choices=["kiro", "amazonq", "cursor", "cline", "claude", "copilot", "other"], required=False,
                   help="Target agent/tool to install rules for")
    p.add_argument("--yes", action="store_true", help="Assume yes for confirmations")
    p.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    p.add_argument("--source", type=str, default=None, help="Optional source path for aidlc rules (defaults to packaged rules)")
    p.add_argument("--dest", type=str, default=None, help="Destination path to install rules into (defaults to current directory)")
    p.add_argument("--no-scripts", action="store_true", help="Do not copy helper scripts (subagents/executors/aidlc-evaluator) into destination")
    return p.parse_args()


def interactive_choose() -> str:
    choices = ["kiro", "amazonq", "cursor", "cline", "claude", "copilot", "other"]
    print("Select the agentic coding tool to install AI-DLC for:")
    for i, c in enumerate(choices, 1):
        print(f" {i}) {c}")
    while True:
        v = input("Enter number: ").strip()
        if not v:
            continue
        try:
            idx = int(v) - 1
            if 0 <= idx < len(choices):
                return choices[idx]
        except Exception:
            pass
        print("Invalid selection, try again")


def main() -> int:
    args = parse_args()
    # Determine destination root: prefer --dest, otherwise ask interactively
    if args.dest:
        target_root = Path(args.dest).expanduser().resolve()
    else:
        # prompt for destination path (default: current directory)
        try:
            resp = input(f"Destination path (default: {Path.cwd()}): ").strip()
        except KeyboardInterrupt:
            print("\nAborted by user")
            return 1
        if resp:
            target_root = Path(resp).expanduser().resolve()
        else:
            target_root = Path.cwd()
    repo_root = Path(__file__).resolve().parent.parent
    src_base = Path(args.source) if args.source else repo_root / "aidlc-rules" / "aws-aidlc-rules"
    src_details = Path(args.source) if args.source else repo_root / "aidlc-rules" / "aws-aidlc-rule-details"

    if not src_base.exists() or not src_details.exists():
        print("ERROR: Could not find local rule files. Make sure this script is run from the AI-DLC repository or provide --source")
        print(f"Expected rule dir: {repo_root / 'aidlc-rules' / 'aws-aidlc-rules'}")
        return 2

    tool = args.tool or interactive_choose()
    print(f"Selected tool: {tool}")
    if not args.yes:
        try:
            resp = input(f"Proceed to install AI-DLC for '{tool}' into {target_root}? [y/N]: ").strip().lower()
        except KeyboardInterrupt:
            print("\nAborted by user")
            return 1
        if resp not in ("y", "yes"):
            print("Aborted by user")
            return 1

    try:
        include_scripts = not args.no_scripts
        run_install(tool, src_base, src_details, target_root, args.dry_run, include_scripts=include_scripts)
    except Exception as e:
        print("ERROR during installation:", e)
        return 3

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
