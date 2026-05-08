#!/usr/bin/env python3
"""
install_aidlc.py

Simple installer to copy AI-DLC rule files into the chosen agent integration
location (Kiro, Amazon Q, Cursor, Cline, Claude Code, GitHub Copilot, Other).

Optionally fetches and installs specialist agents from
https://github.com/msitarzewski/agency-agents (The Agency).

Optionally fetches and installs engineering process skills from
https://github.com/addyosmani/agent-skills.

Usage examples:
  python scripts/install_aidlc.py --tool cursor
  python scripts/install_aidlc.py --tool copilot --yes
  python scripts/install_aidlc.py --tool kiro --dry-run
  python scripts/install_aidlc.py --tool copilot --with-agency-agents
  python scripts/install_aidlc.py --tool copilot --with-agency-agents --agency-divisions engineering,testing
  python scripts/install_aidlc.py --tool copilot --with-agent-skills
  python scripts/install_aidlc.py --tool copilot --with-agent-skills --with-agency-agents
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path
import textwrap
import subprocess


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


def copy_file(src: Path, dst: Path, dry_run: bool) -> None:
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {src}")
    if dry_run:
        print(f"[DRY-RUN] Would copy file {src} -> {dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def create_venv_and_install_requirements(target_root: Path, requirements_path: Path, dry_run: bool) -> None:
    venv_path = target_root / ".venv"
    python_cmds = ["python", "python3"]
    created = False
    last_err = None

    for cmd in python_cmds:
        try:
            if dry_run:
                print(f"[DRY-RUN] Would run: {cmd} -m venv {venv_path}")
                created = True
                break
            print(f"Creating virtual environment using '{cmd}'...")
            subprocess.run([cmd, "-m", "venv", str(venv_path)], check=True)
            created = True
            break
        except FileNotFoundError as e:
            last_err = e
            continue
        except subprocess.CalledProcessError as e:
            last_err = e
            continue

    if not created:
        raise EnvironmentError("Could not create virtual environment: 'python' and 'python3' not found or failed. Python is required.")
    if dry_run:
        # In dry-run mode we already printed the venv creation step; nothing more to do here.
        return

    # locate the python executable inside the venv
    venv_python = venv_path / "bin" / "python"
    if not venv_python.exists():
        venv_python = venv_path / "Scripts" / "python.exe"
    if not venv_python.exists():
        raise EnvironmentError(f"Could not find python executable in virtualenv at {venv_path}")

    if dry_run:
        print(f"[DRY-RUN] Would install requirements using {venv_python} -m pip install -r {requirements_path}")
        return

    try:
        print("Upgrading pip in virtualenv...")
        subprocess.run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip"], check=True)
    except subprocess.CalledProcessError:
        print("Warning: Failed to upgrade pip in the virtualenv; continuing to install requirements.")

    try:
        print(f"Installing requirements from {requirements_path} into virtualenv...")
        subprocess.run([str(venv_python), "-m", "pip", "install", "-r", str(requirements_path)], check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to install requirements: {e}")


AGENCY_AGENTS_REPO = "https://github.com/msitarzewski/agency-agents.git"
AGENCY_AGENTS_DIVISIONS = [
    "academic", "design", "engineering", "finance", "game-development",
    "marketing", "paid-media", "product", "project-management",
    "sales", "spatial-computing", "specialized", "strategy", "support", "testing",
]

AGENT_SKILLS_REPO = "https://github.com/addyosmani/agent-skills.git"
AGENT_SKILLS_DIRS = ["skills", "references", "agents"]

# Skills explicitly referenced in workflow rule files (SKILL.md paths).
# The upstream repo has 20 skills total; `code-simplification` and
# `using-agent-skills` (meta) are not referenced but still installed.
WORKFLOW_REQUIRED_SKILLS = [
    "api-and-interface-design",
    "browser-testing-with-devtools",
    "ci-cd-and-automation",
    "code-review-and-quality",
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


def clone_agency_agents(dest: Path, dry_run: bool) -> Path:
    """Clone the agency-agents repo into a temporary or specified location."""
    if dry_run:
        print(f"[DRY-RUN] Would clone {AGENCY_AGENTS_REPO} into {dest}")
        return dest
    if dest.exists() and (dest / ".git").exists():
        print(f"Agency-agents repo already exists at {dest}, pulling latest...")
        subprocess.run(["git", "-C", str(dest), "pull", "--ff-only"], check=False)
        return dest
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Cloning agency-agents from {AGENCY_AGENTS_REPO}...")
    subprocess.run(
        ["git", "clone", "--depth", "1", AGENCY_AGENTS_REPO, str(dest)],
        check=True,
    )
    return dest


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
    """Install skill directories from agent-skills repo into tool-specific locations.

    Installation paths per tool (following upstream docs):
      - copilot:  .github/skills/<name>/SKILL.md  + .github/agents/*.md
      - cursor:   .cursor/rules/<name>.md          (flattened, no subdirs)
      - claude:   .agents/skills/<name>/SKILL.md   + .claude/commands/
      - kiro:     .kiro/skills/<name>/SKILL.md
      - amazonq:  .amazonq/skills/<name>/SKILL.md
      - cline:    .agents/skills/<name>/SKILL.md
      - other:    .agents/skills/<name>/SKILL.md

    Returns count of skills installed.
    """
    # Determine destination paths per tool
    if tool == "copilot":
        skills_dest = target_root / ".github" / "skills"
        agents_dest = target_root / ".github" / "agents"
    elif tool == "cursor":
        skills_dest = target_root / ".cursor" / "rules"
        agents_dest = target_root / ".cursor" / "rules"
    elif tool == "claude":
        skills_dest = target_root / ".agents" / "skills"
        agents_dest = target_root / ".agents"
    elif tool == "kiro":
        skills_dest = target_root / ".kiro" / "skills"
        agents_dest = target_root / ".kiro" / "agents"
    elif tool == "amazonq":
        skills_dest = target_root / ".amazonq" / "skills"
        agents_dest = target_root / ".amazonq" / "agents"
    else:  # cline, other
        skills_dest = target_root / ".agents" / "skills"
        agents_dest = target_root / ".agents"

    count = 0

    if dry_run:
        print(f"[DRY-RUN] Would install agent-skills to {skills_dest}")
    else:
        skills_dest.mkdir(parents=True, exist_ok=True)

    # --- Copy skill directories ---
    skills_src = skills_repo / "skills"
    if skills_src.exists():
        for skill_dir in sorted(skills_src.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            if tool == "cursor":
                # Cursor: flatten to single .md files in .cursor/rules/
                target_file = skills_dest / f"{skill_dir.name}.md"
                if dry_run:
                    print(f"[DRY-RUN]   {skill_dir.name}/SKILL.md -> {target_file}")
                else:
                    shutil.copy2(skill_md, target_file)
            else:
                # All others: keep directory structure with SKILL.md
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

    # --- Copy agent personas into tool-specific agent directory ---
    agents_src = skills_repo / "agents"
    if agents_src.exists():
        if dry_run:
            print(f"[DRY-RUN]   agents/ -> {agents_dest}")
        else:
            agents_dest.mkdir(parents=True, exist_ok=True)
        for md_file in sorted(agents_src.glob("*.md")):
            if tool == "cursor":
                target_file = agents_dest / f"{md_file.stem}.mdc"
            else:
                target_file = agents_dest / md_file.name
            if dry_run:
                print(f"[DRY-RUN]     {md_file.name} -> {target_file}")
            else:
                shutil.copy2(md_file, target_file)

    # --- Copy hooks (session lifecycle) ---
    hooks_src = skills_repo / "hooks"
    if hooks_src.exists():
        hooks_dest = skills_dest.parent / "hooks"
        if dry_run:
            print(f"[DRY-RUN]   hooks/ -> {hooks_dest}")
        else:
            copy_tree(hooks_src, hooks_dest, dry_run=False)

    # --- Copy slash commands for Claude Code ---
    if tool == "claude":
        commands_src = skills_repo / ".claude" / "commands"
        if commands_src.exists():
            commands_dest = target_root / ".claude" / "commands"
            if dry_run:
                print(f"[DRY-RUN]   .claude/commands/ -> {commands_dest}")
            else:
                copy_tree(commands_src, commands_dest, dry_run=False)

    if not dry_run:
        print(f"Installed {count} agent-skills -> {skills_dest}")
    else:
        print(f"[DRY-RUN] Would install {count} skills to {skills_dest}")

    # Report workflow-required skill coverage
    if not dry_run and skills_dest.exists():
        if tool == "cursor":
            installed_names = {f.stem for f in skills_dest.iterdir() if f.is_file() and f.suffix == ".md"}
        else:
            installed_names = {d.name for d in skills_dest.iterdir() if d.is_dir()}
        found = sorted(set(WORKFLOW_REQUIRED_SKILLS) & installed_names)
        missing = sorted(set(WORKFLOW_REQUIRED_SKILLS) - installed_names)
        print(f"\n  Workflow skills coverage: {len(found)}/{len(WORKFLOW_REQUIRED_SKILLS)}")
        if missing:
            print(f"  Missing (workflow will skip gracefully): {', '.join(missing)}")

    return count


def install_agency_agents(tool: str, agency_repo: Path, target_root: Path, divisions: list[str] | None, dry_run: bool) -> int:
    """Install agent .md files from agency-agents repo for the selected tool.

    Returns count of agents installed.
    """
    selected_divisions = divisions if divisions else AGENCY_AGENTS_DIVISIONS
    count = 0

    if tool == "copilot":
        dest = target_root / ".github" / "agents"
    elif tool == "claude":
        dest = target_root / ".claude" / "agents"
    elif tool == "cursor":
        dest = target_root / ".cursor" / "rules"
    elif tool == "cline":
        dest = target_root / ".clinerules" / "agents"
    elif tool in ("kiro", "amazonq", "other"):
        dest = target_root / ".agents"
    else:
        dest = target_root / ".agents"

    if dry_run:
        print(f"[DRY-RUN] Would install agency-agents to {dest}")
    else:
        dest.mkdir(parents=True, exist_ok=True)

    for division in selected_divisions:
        div_path = agency_repo / division
        if not div_path.exists():
            continue
        for md_file in sorted(div_path.rglob("*.md")):
            # Only install files with YAML frontmatter (real agent files)
            try:
                first_line = md_file.read_text(encoding="utf-8").split("\n", 1)[0]
            except (OSError, UnicodeDecodeError):
                continue
            if first_line.strip() != "---":
                continue

            if tool == "cursor":
                # Cursor needs .mdc extension
                target_file = dest / (md_file.stem + ".mdc")
            else:
                target_file = dest / md_file.name

            if dry_run:
                print(f"[DRY-RUN]   {md_file.name} -> {target_file}")
            else:
                shutil.copy2(md_file, target_file)
            count += 1

    if not dry_run:
        print(f"Installed {count} agency-agents ({', '.join(selected_divisions)}) -> {dest}")
    else:
        print(f"[DRY-RUN] Would install {count} agents to {dest}")
    return count


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

    # Copy requirements.txt from the repo and try to create a venv + install
    repo_root = src_rules.parent.parent
    req_src = repo_root / "requirements.txt"
    if req_src.exists():
        dest_req = target_root / "requirements.txt"
        print(f"Copying requirements: {req_src} -> {dest_req}")
        try:
            copy_file(req_src, dest_req, dry_run)
        except Exception as e:
            print(f"Warning: failed to copy requirements.txt: {e}")

        try:
            create_venv_and_install_requirements(target_root, dest_req, dry_run)
        except EnvironmentError as e:
            print("ERROR: Python is required to create a virtual environment and install requirements:", e)
        except RuntimeError as e:
            print("ERROR: Failed to install requirements:", e)
    else:
        print(f"No requirements.txt found at {req_src}; skipping venv setup and package installation")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Install AI-DLC rules into a project for a selected agent tool")
    p.add_argument("--tool", choices=["kiro", "amazonq", "cursor", "cline", "claude", "copilot", "other"], required=False,
                   help="Target agent/tool to install rules for")
    p.add_argument("--yes", action="store_true", help="Assume yes for confirmations")
    p.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    p.add_argument("--source", type=str, default=None, help="Optional source path for aidlc rules (defaults to packaged rules)")
    p.add_argument("--dest", type=str, default=None, help="Destination path to install rules into (defaults to current directory)")
    p.add_argument("--no-scripts", action="store_true", help="Do not copy helper scripts (subagents/executors/aidlc-evaluator) into destination")
    p.add_argument("--with-agency-agents", action="store_true",
                   help="Also install specialist agents from github.com/msitarzewski/agency-agents")
    p.add_argument("--agency-divisions", type=str, default=None,
                   help="Comma-separated list of agency-agents divisions to install (default: all). "
                        f"Available: {','.join(AGENCY_AGENTS_DIVISIONS)}")
    p.add_argument("--agency-agents-path", type=str, default=None,
                   help="Local path to an existing agency-agents clone (skips git clone)")
    p.add_argument("--with-agent-skills", action="store_true",
                   help="Also install engineering process skills from github.com/addyosmani/agent-skills")
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

    # --- Interactive prompts for optional integrations (when CLI flags not set) ---
    if not args.yes and not args.with_agent_skills:
        print(f"\n  The AI-DLC workflow references {len(WORKFLOW_REQUIRED_SKILLS)} agent skills")
        print(f"  (from github.com/addyosmani/agent-skills).")
        print(f"  Skills are optional — stages skip gracefully if missing —")
        print(f"  but installing them enables richer guidance.\n")
        print(f"  Referenced skills: {', '.join(WORKFLOW_REQUIRED_SKILLS[:5])} ... (+{len(WORKFLOW_REQUIRED_SKILLS)-5} more)")
        try:
            resp = input("  Install agent skills? [y/N]: ").strip().lower()
        except KeyboardInterrupt:
            print("\nAborted by user")
            return 1
        if resp in ("y", "yes"):
            args.with_agent_skills = True

    if not args.yes and not args.with_agency_agents:
        print(f"\n  Optionally install specialist agents from")
        print(f"  github.com/msitarzewski/agency-agents (The Agency).")
        print(f"  Divisions: {', '.join(AGENCY_AGENTS_DIVISIONS[:5])} ... (+{len(AGENCY_AGENTS_DIVISIONS)-5} more)")
        try:
            resp = input("  Install agency agents? [y/N]: ").strip().lower()
        except KeyboardInterrupt:
            print("\nAborted by user")
            return 1
        if resp in ("y", "yes"):
            args.with_agency_agents = True

    # --- Agency Agents integration ---
    if args.with_agency_agents:
        print("\n--- Installing Agency Agents (The Agency) ---")
        divisions = None
        if args.agency_divisions:
            divisions = [d.strip() for d in args.agency_divisions.split(",") if d.strip()]
            invalid = [d for d in divisions if d not in AGENCY_AGENTS_DIVISIONS]
            if invalid:
                print(f"WARNING: Unknown divisions ignored: {', '.join(invalid)}")
                divisions = [d for d in divisions if d in AGENCY_AGENTS_DIVISIONS]

        if args.agency_agents_path:
            agency_repo = Path(args.agency_agents_path).expanduser().resolve()
            if not agency_repo.exists():
                print(f"ERROR: Provided agency-agents path does not exist: {agency_repo}")
                return 4
        else:
            agency_repo = target_root / ".agency-agents-repo"
            try:
                clone_agency_agents(agency_repo, args.dry_run)
            except (subprocess.CalledProcessError, FileNotFoundError) as e:
                print(f"ERROR: Failed to clone agency-agents repo: {e}")
                print("  Ensure 'git' is installed, or use --agency-agents-path to provide a local clone.")
                return 4

        try:
            install_agency_agents(tool, agency_repo, target_root, divisions, args.dry_run)
        except Exception as e:
            print(f"ERROR installing agency-agents: {e}")
            return 4

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

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
