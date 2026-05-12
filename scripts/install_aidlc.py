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
import os
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


def _rmtree_force(path: Path) -> None:
    """Remove a directory tree, handling Windows read-only files (e.g. .git pack files)."""
    if not path.exists():
        return
    for p in path.rglob("*"):
        if p.is_file():
            try:
                p.chmod(0o777)
            except OSError:
                pass
    shutil.rmtree(path, ignore_errors=False)


def write_file(path: Path, content: str, dry_run: bool) -> None:
    if dry_run:
        print(f"[DRY-RUN] Would write file {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _retry_op(func, path: Path, max_retries: int = 3) -> None:
    """Retry a file operation with backoff, handling Windows lock races."""
    import time
    for attempt in range(max_retries):
        try:
            func(path)
            return
        except OSError as e:
            if attempt == max_retries - 1:
                raise
            print(f"  (retrying {path.name}: {e})", file=sys.stderr)
            time.sleep(0.5)


def copy_file(src: Path, dst: Path, dry_run: bool) -> None:
    if not src.exists():
        raise FileNotFoundError(f"Source not found: {src}")
    if dry_run:
        print(f"[DRY-RUN] Would copy file {src} -> {dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    # chmod with retry — Windows Defender sometimes locks new files
    _retry_op(lambda p: p.chmod(0o755), dst)



AGENT_SKILLS_REPO = "https://github.com/addyosmani/agent-skills.git"
AGENT_SKILLS_DIRS = ["skills", "references"]


# AIDLC Orchestrator (Phases 0-6) artifacts to install.
# Always-installed (any tool) — the contracts + scripts are useful for
# validation even when subagent spawning isn't available.
ORCHESTRATOR_FACTORY_SCRIPTS = [
    "factory_validate.py",
    "factory_budget.py",
    "factory_merge_reviews.py",
    "factory_conflict.py",
    "factory_run.py",
    "factory_triage.py",
    "factory_audit_writes.py",
    "factory_secretscan.py",
    "factory_build_cache.py",
    "factory_complexity.py",
    "factory_model.py",
    "factory_graph.py",
]

# Claude-Code-only artifacts. Per ORCHESTRATOR-PLAN.md §8.4, Task() spawning
# is Claude Code native; other tools fall back to single-agent role-switching.
ORCHESTRATOR_CLAUDE_TREES = [
    Path(".claude/agents"),       # orchestrator.md + stage/* + cross-cutting/*
]
ORCHESTRATOR_CLAUDE_COMMANDS_GLOB = "factory-*.md"   # under .claude/commands/

ORCHESTRATOR_PYTHON_DEPS = [
    "jsonschema>=4.0",
    "pyyaml>=6.0",
    # Phase 5.5: TS/JS AST diff for factory_conflict.py.
    # Optional at runtime — factory_conflict.py degrades gracefully when
    # tree-sitter is missing (Python AST diff still works).
    "tree-sitter>=0.21",
    "tree-sitter-typescript>=0.21",
    "tree-sitter-javascript>=0.21",
]

# Runtime state that the orchestrator writes per-run. Must be gitignored so
# manifests (with verbatim user prompts), budget usage, and timeline events
# don't leak into commits.
ORCHESTRATOR_GITIGNORE_ENTRIES = [
    ".aidlc-orchestrator/runs/",
    ".aidlc-orchestrator/knowledge/",
]
ORCHESTRATOR_GITIGNORE_HEADER = "# AIDLC orchestrator runtime state"

ORCHESTRATOR_CLAUDE_POINTER_MARKER = "<!-- AIDLC-ORCHESTRATOR-POINTER -->"
ORCHESTRATOR_CLAUDE_POINTER_BLOCK = (
    f"\n{ORCHESTRATOR_CLAUDE_POINTER_MARKER}\n"
    "## AIDLC Orchestrator (multi-agent factory mode)\n\n"
    "This project ships with the AIDLC orchestrator. To run the multi-agent factory:\n\n"
    "- `/factory-onboarding` — guided tour of the orchestrator system\n"
     "- `/factory-help [command]` — quick command reference\n"
     "- `/factory-state <run-id>` — current stage, next step, budget, timeline\n"
     "- `/factory-self <task>` — run the orchestrator on its own codebase\n"
     "- `/factory-spec <feature>` — workspace scout + (reverse-engineer) + requirements + (stories) + plan\n"
     "- `/factory-plan` — decompose plan into per-unit specs (multi-component features only)\n"
     "- `/factory-build` — layer-parallel code generation with file-glob locks + AST symbol drift checks\n"
     "- `/factory-review` — parallel reviewer pool (code, security, performance, simplifier)\n"
     "- `/factory-ship` — release notes, ADRs, CI/CD wiring, CHANGELOG, migration plan\n"
     "- `/factory-resume <run-id>` — resume an interrupted run (or adopt a legacy `aidlc-docs/` project)\n"
     "- `/factory-replay <run-id> --from <stage>` — re-run from a specific stage\n\n"
    "Roles, contracts, budgets, and parallelism rules: see `.claude/agents/orchestrator.md`,\n"
    "`.aidlc-orchestrator/contracts/`, and `.aidlc-orchestrator/budgets/default.yaml`.\n"
    "Design rationale and phase plan: `ORCHESTRATOR-PLAN.md` in the AIDLC source repo.\n"
)

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


def update_requirements(target_root: Path, deps: list[str], dry_run: bool) -> None:
    """Append AIDLC orchestrator deps to target's requirements.txt.

    If the file exists, append only deps that aren't already listed (case-insensitive
    package-name match). If the file doesn't exist, create a minimal one.
    Adds a comment header so the addition is attributable.
    """
    req_path = target_root / "requirements.txt"

    def pkg_name(spec: str) -> str:
        for sep in (">=", "==", "<=", ">", "<", "="):
            if sep in spec:
                return spec.split(sep, 1)[0].strip().lower()
        return spec.strip().lower()

    if dry_run:
        print(f"[DRY-RUN] Would update {req_path} with: {', '.join(deps)}")
        return

    if req_path.exists():
        existing_text = req_path.read_text()
        existing_pkgs = {pkg_name(line) for line in existing_text.splitlines() if line.strip() and not line.strip().startswith("#")}
        new_lines = [d for d in deps if pkg_name(d) not in existing_pkgs]
        if not new_lines:
            print(f"  requirements.txt already lists AIDLC deps — no changes")
            return
        with req_path.open("a") as f:
            if not existing_text.endswith("\n"):
                f.write("\n")
            f.write("\n# AIDLC orchestrator (factory scripts)\n")
            for line in new_lines:
                f.write(f"{line}\n")
        print(f"  appended {len(new_lines)} dep(s) to {req_path.relative_to(target_root)}")
    else:
        content = "# AIDLC orchestrator (factory scripts)\n" + "\n".join(deps) + "\n"
        req_path.write_text(content)
        print(f"  created {req_path.relative_to(target_root)} with {len(deps)} dep(s)")


def update_gitignore(target_root: Path, entries: list[str], header: str, dry_run: bool) -> None:
    """Append orchestrator runtime-state patterns to target's .gitignore.

    Idempotent: only adds patterns not already present (exact-line match).
    Creates the file if missing.
    """
    gi_path = target_root / ".gitignore"

    if dry_run:
        print(f"[DRY-RUN] Would update {gi_path} with: {', '.join(entries)}")
        return

    if gi_path.exists():
        existing_text = gi_path.read_text()
        existing_lines = {line.strip() for line in existing_text.splitlines()}
        new_lines = [e for e in entries if e not in existing_lines]
        if not new_lines:
            print(f"  .gitignore already lists orchestrator runtime patterns — no changes")
            return
        with gi_path.open("a") as f:
            if not existing_text.endswith("\n"):
                f.write("\n")
            f.write(f"\n{header}\n")
            for line in new_lines:
                f.write(f"{line}\n")
        print(f"  appended {len(new_lines)} pattern(s) to {gi_path.relative_to(target_root)}")
    else:
        content = f"{header}\n" + "\n".join(entries) + "\n"
        gi_path.write_text(content)
        print(f"  created {gi_path.relative_to(target_root)} with {len(entries)} pattern(s)")


def update_workflow_doc_pointer(claude_md_path: Path, marker: str, block: str, dry_run: bool) -> None:
    """Append the orchestrator pointer block to CLAUDE.md once.

    Idempotent: skips if marker already present. Creates the file if missing
    (which would only happen if rules install was skipped — rare but safe).
    """
    if dry_run:
        print(f"[DRY-RUN] Would append orchestrator pointer to {claude_md_path}")
        return

    if claude_md_path.exists():
        existing = claude_md_path.read_text(encoding="utf-8")
        if marker in existing:
            print(f"  CLAUDE.md already contains orchestrator pointer — no changes")
            return
        with claude_md_path.open("a", encoding="utf-8") as f:
            if not existing.endswith("\n"):
                f.write("\n")
            f.write(block)
        print(f"  appended orchestrator pointer to {claude_md_path.relative_to(claude_md_path.parent)}")
    else:
        claude_md_path.parent.mkdir(parents=True, exist_ok=True)
        claude_md_path.write_text(block.lstrip(), encoding="utf-8")
        print(f"  created {claude_md_path.name} with orchestrator pointer")


def _tool_agent_dir(tool: str) -> str:
    """Return the agent directory for the given tool."""
    return {
        "claude": ".claude/agents",
        "opencode": ".opencode/agents",
        "codex": ".codex/agents",
    }.get(tool, ".aidlc-orchestrator/agents")


def _tool_commands_dir(tool: str) -> str:
    """Return the commands directory for the given tool."""
    return {
        "claude": ".claude/commands",
        "opencode": ".opencode/commands",
        "codex": ".codex/commands",
    }.get(tool, ".aidlc-orchestrator/commands")


def _tool_workflow_doc(tool: str, target_root: Path) -> Path | None:
    """Return the workflow doc path for tools that have one, or None."""
    mapping = {
        "claude": target_root / "CLAUDE.md",
        "opencode": target_root / "AGENTS.md",
        "copilot": target_root / ".github" / "copilot-instructions.md",
    }
    return mapping.get(tool)


def install_orchestrator(tool: str, repo_root: Path, target_root: Path, dry_run: bool) -> None:
    """Install AIDLC Orchestrator (Phases 0-6) artifacts.

    Layers:
      1. Always (any tool): factory scripts, contracts, default budget
      2. Tool-specific: subagents + slash commands (Claude Code, OpenCode, Codex CLI)
      3. Reference copy (Cursor, Cline, Windsurf, other): agents + commands under .aidlc-orchestrator/
      4. Always: Python deps, gitignore, workflow doc pointer
    """
    print(f"\n--- Installing AIDLC Orchestrator (Phases 0-6) for {tool} ---")

    # Layer 1: factory scripts (any tool)
    src_scripts = repo_root / "scripts"
    dst_scripts = target_root / "scripts"
    print(f"  factory scripts -> {dst_scripts.relative_to(target_root)}/")
    for name in ORCHESTRATOR_FACTORY_SCRIPTS:
        src = src_scripts / name
        if not src.exists():
            print(f"    WARNING: missing source script {src}")
            continue
        dst = dst_scripts / name
        copy_file(src, dst, dry_run)
        if not dry_run:
            try:
                dst.chmod(0o755)
            except OSError:
                pass

    # Layer 1: contracts + default budget (any tool)
    src_contracts = repo_root / ".aidlc-orchestrator" / "contracts"
    dst_contracts = target_root / ".aidlc-orchestrator" / "contracts"
    if src_contracts.exists():
        print(f"  contracts -> {dst_contracts.relative_to(target_root)}/")
        copy_tree(src_contracts, dst_contracts, dry_run)

    src_budget = repo_root / ".aidlc-orchestrator" / "budgets" / "default.yaml"
    dst_budget = target_root / ".aidlc-orchestrator" / "budgets" / "default.yaml"
    if src_budget.exists():
        print(f"  budget policy -> {dst_budget.relative_to(target_root)}")
        copy_file(src_budget, dst_budget, dry_run)

    # Layer 2: tool-specific subagents + slash commands
    agent_dir = _tool_agent_dir(tool)
    cmd_dir = _tool_commands_dir(tool)

    src_agents = repo_root / ".claude" / "agents"
    dst_agents = target_root / agent_dir
    if src_agents.exists():
        print(f"  subagents -> {agent_dir}/")
        copy_tree(src_agents, dst_agents, dry_run)

    src_cmds = repo_root / ".claude" / "commands"
    dst_cmds = target_root / cmd_dir
    if src_cmds.exists():
        print(f"  slash commands -> {cmd_dir}/factory-*.md")
        for cmd_file in sorted(src_cmds.glob(ORCHESTRATOR_CLAUDE_COMMANDS_GLOB)):
            copy_file(cmd_file, dst_cmds / cmd_file.name, dry_run)

    # Layer 3: Python deps
    print(f"  Python deps -> requirements.txt")
    update_requirements(target_root, ORCHESTRATOR_PYTHON_DEPS, dry_run)

    # Layer 3: gitignore runtime state (any tool)
    print(f"  runtime state -> .gitignore")
    update_gitignore(target_root, ORCHESTRATOR_GITIGNORE_ENTRIES, ORCHESTRATOR_GITIGNORE_HEADER, dry_run)

    # Layer 3: workflow doc pointer
    wf_doc = _tool_workflow_doc(tool, target_root)
    if wf_doc:
        print(f"  workflow pointer -> {wf_doc.name}")
        update_workflow_doc_pointer(
            wf_doc,
            ORCHESTRATOR_CLAUDE_POINTER_MARKER,
            ORCHESTRATOR_CLAUDE_POINTER_BLOCK,
            dry_run,
        )

    if not dry_run:
        print(f"\n  Next: pip install -r requirements.txt")
        print(f"  Then: invoke /factory-spec <feature> in the tool to start a run.")


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

    elif tool == "codex":
        dest = target_root / "AGENTS.md"
        print(f"Installing for Codex CLI: {dest}")
        write_file(dest, core_content, dry_run)
        dest_details = target_root / ".aidlc-rule-details"
        copy_tree(src_details, dest_details, dry_run, exclude={"update.md"})

    elif tool == "windsurf":
        dest_rules_file = target_root / ".windsurf" / "rules" / "ai-dlc-workflow.md"
        print(f"Installing for Windsurf: {dest_rules_file}")
        write_file(dest_rules_file, core_content, dry_run)
        dest_details = target_root / ".aidlc-rule-details"
        copy_tree(src_details, dest_details, dry_run, exclude={"update.md"})

    elif tool == "copilot":
        dest = target_root / ".github" / "copilot-instructions.md"
        print(f"Installing for GitHub Copilot: {dest}")
        write_file(dest, core_content, dry_run)
        dest_details = target_root / ".aidlc-rule-details"
        copy_tree(src_details, dest_details, dry_run, exclude={"update.md"})

    elif tool == "opencode":
        dest = target_root / "AGENTS.md"
        print(f"Installing for OpenCode: {dest}")
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
        "opencode": "generic.md",
        "codex": "generic.md",
        "windsurf": "generic.md",
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
    p.add_argument("--tool", choices=["kiro", "amazonq", "cursor", "cline", "claude", "copilot", "opencode", "codex", "windsurf", "other"], required=False,
                   help="Target agent/tool to install rules for")
    p.add_argument("--yes", action="store_true", help="Assume yes for confirmations")
    p.add_argument("--dry-run", action="store_true", help="Show what would be done without making changes")
    p.add_argument("--source", type=str, default=None, help="Optional source path for aidlc rules (defaults to packaged rules)")
    p.add_argument("--dest", type=str, default=None, help="Destination path to install rules into (defaults to current directory)")
    p.add_argument("--with-agent-skills", action="store_true", default=True,
                   help="Always install engineering process skills from github.com/addyosmani/agent-skills (default: install)")
    p.add_argument("--agent-skills-path", type=str, default=None,
                   help="Local path to an existing agent-skills clone (skips git clone)")
    p.add_argument("--custom-skills-path", type=str, default=None,
                   help="Path to custom/project-specific skills. Each subdirectory should contain a SKILL.md. "
                        "Installed to .agents/skills/ and override agent-skills with the same name.")
    p.add_argument("--with-orchestrator", dest="with_orchestrator", action="store_true", default=None,
                   help="Install the AIDLC orchestrator (factory scripts + subagents + slash commands). "
                        "If neither --with-orchestrator nor --no-orchestrator is set, prompts interactively (default: yes).")
    p.add_argument("--no-orchestrator", dest="with_orchestrator", action="store_false",
                   help="Skip orchestrator installation.")
    return p.parse_args()


def ask_orchestrator(tool: str) -> bool:
    """Prompt user whether to install the AIDLC orchestrator. Default: yes."""
    if tool in ("claude", "opencode"):
        msg = ("Install the AIDLC orchestrator (factory scripts + subagents + slash commands)?\n"
               "  Includes: 13 stage subagents, 11 /factory-* slash commands, 9 factory_*.py scripts,\n"
               "  20+ JSON schema contracts, default budget policy.\n"
               "  [Y/n]: ")
    else:
        msg = (f"Install the AIDLC orchestrator infrastructure for {tool}?\n"
               f"  You'll get the factory_*.py scripts and contracts (usable for manual validation).\n"
               f"  Subagent spawning is Claude Code only — for {tool} the multi-agent factory\n"
               f"  runs in degraded mode (single-agent role-switching) per ORCHESTRATOR-PLAN.md §8.4.\n"
               f"  [Y/n]: ")
    try:
        resp = input(msg).strip().lower()
    except KeyboardInterrupt:
        return False
    return resp not in ("n", "no")


def interactive_choose() -> str:
    choices = ["kiro", "amazonq", "cursor", "cline", "claude", "copilot", "opencode", "codex", "windsurf", "other"]
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
            resp = input(f"Destination path (default: {Path.cwd()}): ").strip().strip("'\"")
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
            _rmtree_force(skills_repo)
        elif args.dry_run and not args.agent_skills_path:
            print(f"[DRY-RUN] Would remove temporary clone: {skills_repo}")

    # --- Custom Skills ---
    if args.custom_skills_path:
        custom_src = Path(args.custom_skills_path).expanduser().resolve()
        if not custom_src.exists():
            print(f"ERROR: Custom skills path not found: {custom_src}")
            return 5
        print(f"\n--- Installing Custom Skills ---")
        skills_dest = target_root / ".agents" / "skills"
        skills_dest.mkdir(parents=True, exist_ok=True)
        count = 0
        for skill_dir in sorted(custom_src.iterdir()):
            if not skill_dir.is_dir():
                continue
            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue
            target_dir = skills_dest / skill_dir.name
            if args.dry_run:
                print(f"[DRY-RUN]   {skill_dir.name}/ -> {target_dir}")
            else:
                print(f"  {skill_dir.name}/ -> .agents/skills/{skill_dir.name}/")
                copy_tree(skill_dir, target_dir, dry_run=False)
            count += 1
        if count == 0 and not args.dry_run:
            print("  (no SKILL.md files found in custom skills path)")
        print(f"Installed {count} custom skill(s)")
    else:
        # Also check for bundled custom skills in the repo itself
        bundled_custom = repo_root / ".agents" / "custom-skills"
        if bundled_custom.exists():
            print(f"\n--- Installing Bundled Custom Skills ---")
            skills_dest = target_root / ".agents" / "skills"
            skills_dest.mkdir(parents=True, exist_ok=True)
            count = 0
            for skill_dir in sorted(bundled_custom.iterdir()):
                if not skill_dir.is_dir():
                    continue
                skill_md = skill_dir / "SKILL.md"
                if not skill_md.exists():
                    continue
                target_dir = skills_dest / skill_dir.name
                if args.dry_run:
                    print(f"[DRY-RUN]   {skill_dir.name}/ -> {target_dir}")
                else:
                    print(f"  {skill_dir.name}/ -> .agents/skills/{skill_dir.name}/")
                    copy_tree(skill_dir, target_dir, dry_run=False)
                count += 1
            if count:
                print(f"Installed {count} bundled custom skill(s)")

    # --- AIDLC Orchestrator (Phases 0-6) ---
    install_orch: bool
    if args.with_orchestrator is not None:
        install_orch = args.with_orchestrator
    elif args.yes:
        install_orch = True   # default yes in non-interactive mode
    else:
        install_orch = ask_orchestrator(tool)

    if install_orch:
        try:
            install_orchestrator(tool, repo_root, target_root, args.dry_run)
        except Exception as e:
            print(f"ERROR installing orchestrator: {e}")
            return 6
    else:
        print("\nSkipped AIDLC orchestrator installation.")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
