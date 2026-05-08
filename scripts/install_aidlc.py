#!/usr/bin/env python3
"""
install_aidlc.py

Simple installer to copy AI-DLC rule files into the chosen agent integration
location (Kiro, Amazon Q, Cursor, Cline, Claude Code, GitHub Copilot, Other).

Optionally fetches and installs engineering process skills from
https://github.com/addyosmani/agent-skills.

Usage examples:
  python scripts/install_aidlc.py --tool cursor
  python scripts/install_aidlc.py --tool copilot --yes
  python scripts/install_aidlc.py --tool kiro --dry-run
  python scripts/install_aidlc.py --tool copilot --with-agent-skills
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
import textwrap
import subprocess


def copy_tree(src: Path, dst: Path, dry_run: bool, exclude: set[str] | None = None) -> None:
    """Copy a directory tree from `src` to `dst`.

    If `exclude` is provided, file basenames in that set will be skipped.
    """
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {src}")
    excl = set(exclude) if exclude else set()
    if dry_run:
        if excl:
            print(f"[DRY-RUN] Would copy {src} -> {dst} (excluding: {', '.join(sorted(excl))})")
        else:
            print(f"[DRY-RUN] Would copy {src} -> {dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        # Prefer the modern shutil API when available (supports dirs_exist_ok and ignore)
        if excl:
            ignore = shutil.ignore_patterns(*sorted(excl))
            shutil.copytree(src, dst, dirs_exist_ok=True, ignore=ignore)
        else:
            shutil.copytree(src, dst, dirs_exist_ok=True)
    except TypeError:
        # older Python fallback: try copytree without dirs_exist_ok, then manual copy
        if not dst.exists():
            if excl:
                ignore = shutil.ignore_patterns(*sorted(excl))
                shutil.copytree(src, dst, ignore=ignore)
            else:
                shutil.copytree(src, dst)
        else:
            for p in src.rglob("*"):
                # skip excluded basenames
                if p.name in excl:
                    continue
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


def copy_file(src: Path, dst: Path, dry_run: bool) -> None:
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {src}")
    if dry_run:
        print(f"[DRY-RUN] Would copy file {src} -> {dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)



AGENT_SKILLS_REPO = "https://github.com/addyosmani/agent-skills.git"
AGENT_SKILLS_DIRS = ["skills", "references"]

# Skills explicitly referenced in workflow rule files (SKILL.md paths).
# These are MANDATORY for full workflow enforcement — without them,
# the workflow uses inline fallback processes.
WORKFLOW_REQUIRED_SKILLS = [
    "api-and-interface-design",
    "browser-testing-with-devtools",
    "ci-cd-and-automation",
    "code-review-and-quality",
    "code-simplification",
    "context-engineering",
    "debugging-and-error-recovery",
    "deprecation-and-migration",
    "documentation-and-adrs",
    "frontend-ui-engineering",
    "git-workflow-and-versioning",
    "idea-refine",
    "incremental-implementation",
    "performance-optimization",
    "planning-and-task-breakdown",
    "security-and-hardening",
    "shipping-and-launch",
    "source-driven-development",
    "spec-driven-development",
    "test-driven-development",
]


def clone_agent_skills(dest: Path, dry_run: bool) -> Path:
    """Clone the agent-skills repo into a temporary or specified location."""
    if dry_run:
        print(f"[DRY-RUN] Would clone {AGENT_SKILLS_REPO} into {dest}")
        return dest
    if dest.exists() and (dest / ".git").exists():
        print(f"Agent-skills repo already exists at {dest}, pulling latest...")
        subprocess.run(["git", "-C", str(dest), "pull", "--ff-only"], check=False)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Cloning agent-skills from {AGENT_SKILLS_REPO}...")
    subprocess.run(
        ["git", "clone", "--depth", "1", AGENT_SKILLS_REPO, str(dest)],
        check=True,
    )
    return dest


def install_agent_skills(tool: str, skills_repo: Path, target_root: Path, dry_run: bool) -> int:
    """Install skill directories from agent-skills repo.

    Skills are always installed to the canonical location:
      .agents/skills/<name>/SKILL.md

    This is the path the AI-DLC workflow uses to load skill processes.

    Returns count of skills installed.
    """
    # Canonical skill location — always the same regardless of tool
    skills_dest = target_root / ".agents" / "skills"

    count = 0

    if dry_run:
        print(f"[DRY-RUN] Would install agent-skills to {skills_dest}")
    else:
        skills_dest.mkdir(parents=True, exist_ok=True)

    # --- Copy skill directories (always structured: .agents/skills/<name>/SKILL.md) ---
    skills_src = skills_repo / "skills"
    if skills_src.exists():
        for skill_dir in sorted(skills_src.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            target_dir = skills_dest / skill_dir.name
            if dry_run:
                print(f"[DRY-RUN]   {skill_dir.name}/ -> {target_dir}")
            else:
                copy_tree(skill_dir, target_dir, dry_run=False)
            count += 1

    # --- Copy reference checklists ---
    refs_src = skills_repo / "references"
    if refs_src.exists():
        refs_dest = skills_dest / "_references"
        if dry_run:
            print(f"[DRY-RUN]   references/ -> {refs_dest}")
        else:
            copy_tree(refs_src, refs_dest, dry_run=False)

    # --- Copy hooks (session lifecycle) ---
    hooks_src = skills_repo / "hooks"
    if hooks_src.exists():
        hooks_dest = skills_dest.parent / "hooks"
        if dry_run:
            print(f"[DRY-RUN]   hooks/ -> {hooks_dest}")
        else:
            copy_tree(hooks_src, hooks_dest, dry_run=False)

    if not dry_run:
        print(f"Installed {count} agent-skills -> {skills_dest}")
    else:
        print(f"[DRY-RUN] Would install {count} skills to {skills_dest}")

    # Report workflow-required skill coverage
    if not dry_run and skills_dest.exists():
        installed_names = {d.name for d in skills_dest.iterdir() if d.is_dir()}
        found = sorted(set(WORKFLOW_REQUIRED_SKILLS) & installed_names)
        missing = sorted(set(WORKFLOW_REQUIRED_SKILLS) - installed_names)
        print(f"\n  Workflow skills coverage: {len(found)}/{len(WORKFLOW_REQUIRED_SKILLS)}")
        if missing:
            print(f"  WARNING — Missing skills (workflow will use inline fallbacks): {', '.join(missing)}")

    return count


def run_install(tool: str, src_rules: Path, src_details: Path, target_root: Path, dry_run: bool) -> None:
    core_md = src_rules / "core-workflow.md"
    if not core_md.exists():
        core_md = src_rules / "core-workflow.md"
    core_content = core_md.read_text(encoding="utf-8") if core_md.exists() else ""

    if tool == "kiro":
        dest_rules = target_root / ".kiro" / "steering" / "aws-aidlc-rules"
        dest_details = target_root / ".kiro" / "aws-aidlc-rule-details"
        print(f"Installing for Kiro: {dest_rules}")
        copy_tree(src_rules, dest_rules, dry_run)
        copy_tree(src_details, dest_details, dry_run, exclude={"update.md"})

    elif tool == "amazonq":
        dest_rules = target_root / ".amazonq" / "rules" / "aws-aidlc-rules"
        dest_details = target_root / ".amazonq" / "aws-aidlc-rule-details"
        print(f"Installing for Amazon Q Developer: {dest_rules}")
        copy_tree(src_rules, dest_rules, dry_run)
        copy_tree(src_details, dest_details, dry_run, exclude={"update.md"})

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
        copy_tree(src_details, dest_details, dry_run, exclude={"update.md"})

    elif tool == "cline":
        dest = target_root / ".clinerules" / "core-workflow.md"
        print(f"Installing for Cline: {dest}")
        write_file(dest, core_content, dry_run)
        dest_details = target_root / ".aidlc-rule-details"
        copy_tree(src_details, dest_details, dry_run, exclude={"update.md"})

    elif tool == "claude":
        dest = target_root / "CLAUDE.md"
        print(f"Installing for Claude Code: {dest}")
        write_file(dest, core_content, dry_run)
        dest_details = target_root / ".aidlc-rule-details"
        copy_tree(src_details, dest_details, dry_run, exclude={"update.md"})

    elif tool == "copilot":
        dest = target_root / ".github" / "copilot-instructions.md"
        print(f"Installing for GitHub Copilot: {dest}")
        write_file(dest, core_content, dry_run)
        dest_details = target_root / ".aidlc-rule-details"
        copy_tree(src_details, dest_details, dry_run, exclude={"update.md"})

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

    # Copy the tool-specific adapter file into the destination for reference
    repo_root_adapters = src_rules.parent.parent
    adapters_dir = repo_root_adapters / "aidlc-rules" / "adapters"
    adapter_map = {
        "copilot": "copilot.md",
        "cursor": "cursor.md",
        "claude": "claude-code.md",
        "cline": "cline.md",
        "other": "generic.md",
        "kiro": "generic.md",
        "amazonq": "generic.md",
    }
    adapter_file = adapters_dir / adapter_map.get(tool, "generic.md")
    if adapter_file.exists():
        if tool == "kiro":
            adapter_dest = target_root / ".kiro" / "aws-aidlc-rule-details" / "adapters" / adapter_file.name
        elif tool == "amazonq":
            adapter_dest = target_root / ".amazonq" / "aws-aidlc-rule-details" / "adapters" / adapter_file.name
        else:
            adapter_dest = target_root / ".aidlc-rule-details" / "adapters" / adapter_file.name
        print(f"Copying adapter: {adapter_file} -> {adapter_dest}")
        copy_file(adapter_file, adapter_dest, dry_run)




def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Install AI-DLC rules into a project for a selected agent tool")
    p.add_argument("--tool", choices=["kiro", "amazonq", "cursor", "cline", "claude", "copilot", "other"], required=False,
                   help="Target agent/tool to install rules for")
    p.add_argument("--yes", action="store_true", help="Assume yes for confirmations")
    p.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    p.add_argument("--source", type=str, default=None, help="Optional source path for aidlc rules (defaults to packaged rules)")
    p.add_argument("--dest", type=str, default=None, help="Destination path to install rules into (defaults to current directory)")
    p.add_argument("--with-agent-skills", action="store_true", default=True,
                   help="Always install engineering process skills from github.com/addyosmani/agent-skills (default: install)")
    p.add_argument("--agent-skills-path", type=str, default=None,
                   help="Local path to an existing agent-skills clone (skips git clone)")
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
            resp = input(f"Proceed to install AI-DLC for '{tool}' into {target_root}? [Y/n]: ").strip().lower()
        except KeyboardInterrupt:
            print("\nAborted by user")
            return 1
        # Default to yes on empty response; only abort on explicit 'no'
        if resp in ("n", "no"):
            print("Aborted by user")
            return 1

    try:
        run_install(tool, src_base, src_details, target_root, args.dry_run)
    except Exception as e:
        print("ERROR during installation:", e)
        return 3

    # Agent skills will be installed by default (no interactive prompt)

    # --- Agent Skills integration ---
    if args.with_agent_skills:
        print("\n--- Installing Agent Skills (addyosmani/agent-skills) ---")

        if args.agent_skills_path:
            skills_repo = Path(args.agent_skills_path).expanduser().resolve()
            if not skills_repo.exists():
                print(f"ERROR: Provided agent-skills path does not exist: {skills_repo}")
                return 5
        else:
            skills_repo = target_root / ".agent-skills-repo"
            try:
                clone_agent_skills(skills_repo, args.dry_run)
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print(f"ERROR: Failed to clone agent-skills repo: {e}")
                print("  Ensure 'git' is installed, or use --agent-skills-path to provide a local clone.")
                return 5

        try:
            install_agent_skills(tool, skills_repo, target_root, args.dry_run)
        except Exception as e:
            print(f"ERROR installing agent-skills: {e}")
            return 5

        # Clean up the cloned repo — its contents have been copied into the project
        if not args.agent_skills_path and skills_repo.exists() and not args.dry_run:
            print(f"Cleaning up temporary clone: {skills_repo}")
            shutil.rmtree(skills_repo)
        elif args.dry_run and not args.agent_skills_path:
            print(f"[DRY-RUN] Would remove temporary clone: {skills_repo}")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
