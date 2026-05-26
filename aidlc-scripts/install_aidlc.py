#!/usr/bin/env python3
"""
install_aidlc.py

Simple installer to copy AI-DLC rule files into the chosen agent integration
location (Cursor, Claude Code, GitHub Copilot, OpenCode, Other).

Optionally fetches and installs engineering process skills from
https://github.com/addyosmani/agent-skills.

Usage examples:
  python aidlc-scripts/install_aidlc.py --tool cursor
  python aidlc-scripts/install_aidlc.py --tool copilot --yes
  python aidlc-scripts/install_aidlc.py --tool claude --dry-run
  python aidlc-scripts/install_aidlc.py --tool copilot --with-agent-skills
"""
from __future__ import annotations

import argparse
import os
import platform as _platform
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


def _is_windows() -> bool:
    return _platform.system() == "Windows"


def _venv_python(venv_path: Path) -> Path | None:
    """Return the Python executable inside a virtualenv (cross-platform)."""
    for candidate in (
        venv_path / "bin" / "python",          # macOS / Linux (canonical)
        venv_path / "bin" / "python3",          # some Linux distros
        venv_path / "Scripts" / "python.exe",   # Windows
        venv_path / "Scripts" / "python3.exe",  # Windows (alt)
    ):
        if candidate.exists():
            return candidate
    return None


def ensure_target_requirements(repo_root: Path, target_root: Path, dry_run: bool) -> Path | None:
    """Ensure target_root has a requirements.txt, seeding from the source repo if missing.

    Returns the path to the target requirements.txt, or None if neither target nor
    source has one. Existing target files are never overwritten — update_requirements()
    handles appending orchestrator-specific deps later.
    """
    target_req = target_root / "requirements.txt"
    if target_req.exists():
        return target_req
    src_req = repo_root / "requirements.txt"
    if not src_req.exists():
        return None
    if dry_run:
        print(f"[DRY-RUN] Would seed {target_req} from {src_req}")
        return target_req
    target_req.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src_req, target_req)
    print(f"  base deps -> {target_req.relative_to(target_root)}")
    return target_req


def create_venv_and_install_requirements(target_root: Path, requirements_path: Path, dry_run: bool) -> None:
    """Create .venv in target_root and pip install -r requirements_path inside it.

    Idempotent: `python -m venv` is a no-op when the venv exists; pip only installs
    missing/outdated deps. Raises EnvironmentError if python isn't available, or
    RuntimeError if pip install fails.
    """
    venv_path = target_root / ".venv"

    if dry_run:
        print(f"[DRY-RUN] Would create venv at {venv_path}")
        print(f"[DRY-RUN] Would install requirements from {requirements_path}")
        return

    python_cmds = (["py", "python3", "python"] if _is_windows()
                   else ["python3", "python"])
    created = False
    last_err: Exception | None = None
    for cmd in python_cmds:
        try:
            print(f"Creating virtual environment using '{cmd}' at .venv/...")
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
        raise EnvironmentError(
            f"Could not create virtual environment: no suitable Python found "
            f"(tried: {', '.join(python_cmds)}). Last error: {last_err}"
        )

    venv_python = _venv_python(venv_path)
    if venv_python is None:
        raise EnvironmentError(
            f"Could not find python executable in virtualenv at {venv_path}. "
            "Expected bin/python (macOS/Linux) or Scripts/python.exe (Windows)."
        )

    try:
        print("Upgrading pip in virtualenv...")
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"],
            check=True,
        )
    except subprocess.CalledProcessError:
        print("Warning: Failed to upgrade pip in the virtualenv; continuing.")

    try:
        rel = requirements_path.relative_to(target_root) if target_root in requirements_path.parents else requirements_path
        print(f"Installing requirements from {rel} into virtualenv...")
        subprocess.run(
            [str(venv_python), "-m", "pip", "install", "-r", str(requirements_path)],
            check=True,
        )
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to install requirements: {e}")



AGENT_SKILLS_REPO = "https://github.com/addyosmani/agent-skills.git"
AGENT_SKILLS_DIRS = ["skills", "references"]


VALID_TOOLS = (
    "cursor", "claude",
    "copilot", "opencode", "other",
)


def parse_tools_string(s: str) -> list[str]:
    """Parse a comma-separated tool list (e.g. 'claude,opencode') into a deduped list.

    Raises ValueError if any tool is not in VALID_TOOLS.
    """
    tools = [t.strip().lower() for t in s.split(",") if t.strip()]
    if not tools:
        raise ValueError("No tools specified")
    invalid = [t for t in tools if t not in VALID_TOOLS]
    if invalid:
        raise ValueError(
            f"Unknown tool(s): {', '.join(invalid)}. "
            f"Valid: {', '.join(VALID_TOOLS)}"
        )
    seen: set[str] = set()
    out: list[str] = []
    for t in tools:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out




# AIDLC Orchestrator (Phases 0-6) artifacts to install.
# Always-installed (any tool) — the contracts + scripts are useful for
# validation even when subagent spawning isn't available.
ORCHESTRATOR_FACTORY_SCRIPTS = [
    "factory_validate.py",
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
    "factory_agent_discover.py",
    "factory_telemetry.py",
    # Tier-god additions (Phase 1 + 2 + 3 + 4 of TIER-GOD-PLAN.md)
    "factory_content_validate.py",
    "factory_lint_rules.py",
    "factory_evidence_extract.py",
    "factory_features.py",
    "factory_stage_registry.py",
    "factory_cost_estimate.py",
    "factory_quality_report.py",
    "factory_prompt_ab.py",
    "factory_slo_check.py",
    "factory_knowledge_promote.py",
    "factory_knowledge_dashboard.py",
    # Hallucination prevention stack (Piece 3 + Piece 4)
    "factory_custom_skills.py",      # fetch+verify community skills from skill-sources.yaml
    "factory_skill_drift.py",     # detect skills whose version range lags behind latest stable
    # Design system pipeline (Figma input snapping, component-aware resolution, learn/approve/reject)
    "factory_design_system_snap.py",    # snap raw Figma values to canonical design tokens
    "factory_design_system_resolve.py", # lazy-load design system files for matching components
    "factory_design_system_learn.py",   # learn from approved/rejected UI output
    # Google Stitch integration (AI design tool input snapping, MCP registry)
    "factory_stitch_snap.py",   # snap Stitch HTML/CSS/DESIGN.md output to canonical design tokens
    "factory_stitch_mcp.py",    # Stitch MCP registry, health check, config fragment
    # Figma MCP integration (official Figma Remote MCP + community fallback)
    "factory_figma_mcp.py",     # Figma MCP registry, health check, config fragment
    # Skill sync layer — monorepo-aware autoskills bridge
    "factory_skill_sync.py",      # run autoskills per-workspace, consolidate to .agents/skills/
    "skill_utils.py",             # shared helpers (parse_frontmatter, ver_in_range, discover_skills)
    # CodeGraph integration (optional — installed when --with-codegraph is set)
    "factory_codegraph.py",       # install/init/index/status CLI helper for CodeGraph
]

# Root-level config files installed once alongside the orchestrator.
# skill-sources.yaml is user-customizable — never overwrite on re-install (use --force).
ORCHESTRATOR_ROOT_CONFIGS = [
    "skill-sources.yaml",
]

# Per-tool MCP config files (Context7 + Chrome DevTools, locally-run via npx).
# Each tool reads its MCP servers from a different path/format, so we ship one
# config per tool and let the installer place only the relevant one.
# User-customizable — never overwrite on re-install (use --force).
ORCHESTRATOR_TOOL_MCP_CONFIGS = {
    "claude":   Path(".mcp.json"),
    "cursor":   Path(".cursor/mcp.json"),
    "copilot":  Path(".vscode/mcp.json"),
    "opencode": Path("opencode.json"),
}

# Phase 5 — executor adapter package (tool-agnostic spawn layer).
# Shipped to every consumer; the active adapter is picked at runtime per
# --tool. See aidlc-scripts/executors/registry.yaml and
# .aidlc-orchestrator/contracts/executor.v1.md.
ORCHESTRATOR_EXECUTOR_PKG_DIR = Path("aidlc-scripts/executors")

# Phase 3 — quality docs (SLO definitions + CodeGraph baseline template).
ORCHESTRATOR_QUALITY_DOCS = [
    Path("aidlc-docs/quality/slos.md"),
    Path("aidlc-docs/quality/codegraph-baseline.md"),
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
    ".codegraph/",  # CodeGraph index — rebuilt locally, no git history value
]
ORCHESTRATOR_GITIGNORE_HEADER = "# AIDLC orchestrator runtime state"

ORCHESTRATOR_COPILOT_POINTER_BLOCK = (
    "\n<!-- AIDLC-ORCHESTRATOR-POINTER -->\n"
    "## AIDLC Orchestrator (multi-agent factory mode)\n\n"
    "This project ships with the AIDLC orchestrator. Stage agents: `.github/agents/stage/`;\n"
    "cross-cutting agents: `.github/agents/cross-cutting/`; orchestrator: `.github/agents/orchestrator.md`;\n"
    "skills: `.github/skills/`; prompts (user-invocable commands): `.github/prompts/`.\n\n"
    "Invoke from Copilot Chat by typing `/` and selecting the prompt:\n\n"
    "- `/factory-code-tour` — dependency-ordered codebase tour: foundations → entry points\n"
    "- `/factory-spec` — workspace scout + requirements + plan\n"
    "- `/factory-plan` — decompose plan into per-unit specs\n"
    "- `/factory-build` — layer-parallel code generation\n"
    "- `/factory-review` — parallel reviewer pool (code, security, performance, simplifier)\n"
    "- `/factory-ship` — release notes, ADRs, CI/CD wiring, CHANGELOG\n"
    "- `/factory-resume` — resume an interrupted run\n"
    "- `/factory-replay` — re-run from a specific stage\n"
    "- `/factory-state` — show run status, stage, budget\n\n"
    "Roles, contracts, budgets: `.aidlc-orchestrator/contracts/`, `.aidlc-orchestrator/budgets/default.yaml`.\n\n"
    "**Required VS Code setting** (enables nested subagent spawning):\n"
    "```json\n"
    '{ "chat.subagents.allowInvocationsFromSubagents": true }\n'
    "```\n"
)

ORCHESTRATOR_CLAUDE_POINTER_MARKER = "<!-- AIDLC-ORCHESTRATOR-POINTER -->"
ORCHESTRATOR_CLAUDE_POINTER_BLOCK = (
    f"\n{ORCHESTRATOR_CLAUDE_POINTER_MARKER}\n"
    "## AIDLC Orchestrator (multi-agent factory mode)\n\n"
    "This project ships with the AIDLC orchestrator. To run the multi-agent factory:\n\n"
    "- `/factory-onboarding` — guided tour of the orchestrator system\n"
    "- `/factory-code-tour` — guided human tour of any codebase: architecture, key flows, conventions\n"
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
        existing_text = req_path.read_text(encoding="utf-8")
        existing_pkgs = {pkg_name(line) for line in existing_text.splitlines() if line.strip() and not line.strip().startswith("#")}
        new_lines = [d for d in deps if pkg_name(d) not in existing_pkgs]
        if not new_lines:
            print(f"  requirements.txt already lists AIDLC deps -- no changes")
            return
        with req_path.open("a", encoding="utf-8") as f:
            if not existing_text.endswith("\n"):
                f.write("\n")
            f.write("\n# AIDLC orchestrator (factory scripts)\n")
            for line in new_lines:
                f.write(f"{line}\n")
        print(f"  appended {len(new_lines)} dep(s) to {req_path.relative_to(target_root)}")
    else:
        content = "# AIDLC orchestrator (factory scripts)\n" + "\n".join(deps) + "\n"
        req_path.write_text(content, encoding="utf-8")
        print(f"  created {req_path.relative_to(target_root)} with {len(deps)} dep(s)")


def update_gitignore(target_root: Path, entries: list[str], header: str, dry_run: bool, force: bool = False) -> None:
    """Append orchestrator runtime-state patterns to target's .gitignore.

    Idempotent: only adds patterns not already present (exact-line match).
    Creates the file if missing.
    """
    gi_path = target_root / ".gitignore"

    if dry_run:
        print(f"[DRY-RUN] Would update {gi_path} with: {', '.join(entries)}")
        return

    existing_text = gi_path.read_text(encoding="utf-8") if gi_path.exists() else ""
    existing_lines = {line.strip() for line in existing_text.splitlines()}
    new_lines = [e for e in entries if e not in existing_lines]

    if not force and not new_lines:
        print(f"  .gitignore already lists orchestrator runtime patterns -- no changes")
        return

    lines_to_write = entries if force else new_lines

    with gi_path.open("a", encoding="utf-8") as f:
        if existing_text:
            if not existing_text.endswith("\n"):
                f.write("\n")
            f.write("\n")
        f.write(f"{header}\n")
        for line in lines_to_write:
            f.write(f"{line}\n")
    print(f"  appended {len(lines_to_write)} pattern(s) to {gi_path.relative_to(target_root)}")


def update_workflow_doc_pointer(claude_md_path: Path, marker: str, block: str, dry_run: bool, force: bool = False) -> None:
    """Append or update the orchestrator pointer block in the workflow doc.

    Idempotent: skips if marker already present and force=False.
    With force=True: replaces the existing block between markers.
    Creates the file if missing.
    """
    if dry_run:
        action = "replace" if force else "append"
        print(f"[DRY-RUN] Would {action} orchestrator pointer in {claude_md_path}")
        return

    if claude_md_path.exists():
        existing = claude_md_path.read_text(encoding="utf-8")
        if marker in existing:
            if not force:
                print(f"  workflow doc already contains orchestrator pointer -- no changes")
                return
            # Replace content between markers (inclusive)
            start = existing.index(marker)
            end = existing.index("\n## ", start + len(marker)) if "\n## " in existing[start:] else len(existing)
            # Keep everything before the marker, append new block
            updated = existing[:start] + block.lstrip()
            claude_md_path.write_text(updated, encoding="utf-8")
            print(f"  replaced orchestrator pointer in {claude_md_path.relative_to(claude_md_path.parent)}")
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


# Stitch MCP entries — format varies per tool config format.
STITCH_MCP_ENTRIES = {
    "claude":   {"stitch": {"type": "stdio", "command": "npx", "args": ["-y", "@_davideast/stitch-mcp", "proxy"], "env": {}}},
    "cursor":   {"stitch": {"command": "npx", "args": ["-y", "@_davideast/stitch-mcp", "proxy"]}},
    "copilot":  {"stitch": {"type": "stdio", "command": "npx", "args": ["-y", "@_davideast/stitch-mcp", "proxy"]}},
    "opencode": {"stitch": {"type": "local", "command": ["npx", "-y", "@_davideast/stitch-mcp", "proxy"], "enabled": True}},
}

# Figma MCP entries — format varies per tool config format.
FIGMA_MCP_ENTRIES = {
    "claude":   {"figma": {"type": "http", "url": "https://mcp.figma.com/mcp"}},
    "cursor":   {"figma": {"type": "http", "url": "https://mcp.figma.com/mcp"}},
    "copilot":  {"figma": {"type": "stdio", "command": "npx", "args": ["-y", "figma-mcp"]}},
    "opencode": {"figma": {"type": "http", "url": "https://mcp.figma.com/mcp", "enabled": True}},
}


def _apply_mcp_config(config_path: Path, tool: str, with_stitch: bool, with_figma: bool, dry_run: bool) -> None:
    """Add Stitch/Figma MCP server entries to config only when user opted in.

    Handles all config formats:
      - .mcp.json / .cursor/mcp.json: { "mcpServers": { ... } }
      - .vscode/mcp.json:              { "servers": { ... } }
      - opencode.json:                 { "mcp": { ... } }
    """
    if not config_path.exists():
        return
    if dry_run:
        if with_stitch:
            print(f"  [DRY-RUN] Would add stitch MCP entry to {config_path.name}")
        if with_figma:
            print(f"  [DRY-RUN] Would add figma MCP entry to {config_path.name}")
        return
    import json
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return

    servers: dict | None = None
    servers_key: str | None = None
    for key in ("mcpServers", "servers", "mcp"):
        if key in data and isinstance(data[key], dict):
            servers = data[key]
            servers_key = key
            break
    if servers is None or servers_key is None:
        return

    if with_stitch and "stitch" not in servers:
        stitch_data = STITCH_MCP_ENTRIES.get(tool, STITCH_MCP_ENTRIES["claude"])
        servers["stitch"] = stitch_data["stitch"]

    if with_figma and "figma" not in servers:
        figma_data = FIGMA_MCP_ENTRIES.get(tool, FIGMA_MCP_ENTRIES["claude"])
        servers["figma"] = figma_data["figma"]

    config_path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _tool_agent_dir(tool: str) -> str:
    """Return the agent directory for the given tool."""
    return {
        "claude": ".claude/agents",
        "opencode": ".opencode/agents",
        "cursor": ".cursor/agents",
        "copilot": ".github/agents",
    }.get(tool, ".aidlc-orchestrator/agents")


def _tool_commands_dir(tool: str) -> str:
    """Return the commands directory for the given tool."""
    return {
        "claude": ".claude/commands",
        "opencode": ".opencode/commands",
        "cursor": ".cursor/commands",
    }.get(tool, ".aidlc-orchestrator/commands")


def _tool_workflow_doc(tool: str, target_root: Path) -> Path | None:
    """Return the workflow doc path for tools that have one, or None."""
    mapping = {
        "claude": target_root / "CLAUDE.md",
        "opencode": target_root / "AGENTS.md",
        "copilot": target_root / ".github" / "copilot-instructions.md",
    }
    return mapping.get(tool)


def _install_vscode_copilot_settings(target_root: Path, dry_run: bool) -> None:
    """Write/merge .vscode/settings.json with Copilot subagent setting."""
    import json
    vscode_settings = target_root / ".vscode" / "settings.json"
    key = "chat.subagents.allowInvocationsFromSubagents"
    if dry_run:
        print(f"[DRY-RUN] Would set {key}=true in {vscode_settings}")
        return
    existing: dict = {}
    if vscode_settings.exists():
        try:
            existing = json.loads(vscode_settings.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    if existing.get(key) is True:
        print(f"  .vscode/settings.json already has {key} -- skipping")
        return
    existing[key] = True
    vscode_settings.parent.mkdir(parents=True, exist_ok=True)
    vscode_settings.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    print(f"  .vscode/settings.json -- set {key}=true")


def install_orchestrator(tools: list[str], repo_root: Path, target_root: Path, dry_run: bool, force: bool = False, args: argparse.Namespace | None = None) -> None:
    """Install AIDLC Orchestrator (Phases 0-6) artifacts for one or more tools.

    Layers:
      1. Shared (runs once regardless of tool count): factory scripts, contracts, default budget
      2. Per-tool: subagents + slash commands + workflow doc pointer
      3. Shared: Python deps, gitignore runtime state, optional .aidlc-env (non-Claude tools)
    """
    tools_label = ", ".join(tools)
    print(f"\n--- Installing AIDLC Orchestrator (Phases 0-6) for {tools_label} ---")

    # Shared Layer 1: factory scripts (any tool)
    src_scripts = repo_root / "aidlc-scripts"
    dst_scripts = target_root / "aidlc-scripts"
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

    # Shared Layer 1: contracts + default budget (any tool)
    src_contracts = repo_root / ".aidlc-orchestrator" / "contracts"
    dst_contracts = target_root / ".aidlc-orchestrator" / "contracts"
    if src_contracts.exists():
        print(f"  contracts -> {dst_contracts.relative_to(target_root)}/")
        copy_tree(src_contracts, dst_contracts, dry_run)

    # Shared Layer 1: runtime architecture + commands (any tool)
    src_runtime = repo_root / ".aidlc-orchestrator" / "runtime"
    dst_runtime = target_root / ".aidlc-orchestrator" / "runtime"
    if src_runtime.exists():
        print(f"  runtime -> {dst_runtime.relative_to(target_root)}/")
        copy_tree(src_runtime, dst_runtime, dry_run)

    src_budget = repo_root / ".aidlc-orchestrator" / "budgets" / "default.yaml"
    dst_budget = target_root / ".aidlc-orchestrator" / "budgets" / "default.yaml"
    if src_budget.exists():
        print(f"  budget policy -> {dst_budget.relative_to(target_root)}")
        copy_file(src_budget, dst_budget, dry_run)

    # Shared Layer 1: executor adapter package (Phase 5 — tool-agnostic spawn)
    src_executors = repo_root / ORCHESTRATOR_EXECUTOR_PKG_DIR
    dst_executors = target_root / ORCHESTRATOR_EXECUTOR_PKG_DIR
    if src_executors.exists():
        print(f"  executor adapters -> {dst_executors.relative_to(target_root)}/")
        copy_tree(src_executors, dst_executors, dry_run)

    # Shared Layer 1: quality docs (Phase 3 — SLO definitions)
    for rel in ORCHESTRATOR_QUALITY_DOCS:
        src_q = repo_root / rel
        dst_q = target_root / rel
        if src_q.exists():
            print(f"  quality doc -> {dst_q.relative_to(target_root)}")
            copy_file(src_q, dst_q, dry_run)

    # Shared Layer 1: root-level config files (e.g. skill-sources.yaml).
    # Never overwrite existing files unless --force — users customise these.
    for name in ORCHESTRATOR_ROOT_CONFIGS:
        src_cfg = repo_root / name
        dst_cfg = target_root / name
        if not src_cfg.exists():
            continue
        if dst_cfg.exists() and not force:
            print(f"  {name} already exists -- skipping (use --force to overwrite)")
            continue
        print(f"  {name} -> {dst_cfg.relative_to(target_root)}")
        copy_file(src_cfg, dst_cfg, dry_run)

    # Per-tool Layer 2: subagents + slash commands + workflow doc pointer
    for tool in tools:
        print(f"\n  -- {tool} --")
        agent_dir = _tool_agent_dir(tool)
        cmd_dir = _tool_commands_dir(tool)

        # Source agent/command dirs vary per tool
        # OpenCode and Cursor have pre-adapted agent files; others use the canonical Claude source
        if tool == "opencode":
            src_agents = repo_root / ".opencode" / "agents"
            src_cmds = repo_root / ".opencode" / "commands"
        elif tool == "copilot":
            src_agents = repo_root / ".github" / "agents"
            src_cmds = None  # Copilot uses prompt files, not slash commands
        elif tool == "cursor":
            src_agents = repo_root / ".cursor" / "agents"
            src_cmds = repo_root / ".cursor" / "commands"
        else:
            src_agents = repo_root / ".claude" / "agents"
            src_cmds = repo_root / ".claude" / "commands"

        dst_agents = target_root / agent_dir
        if src_agents is not None and src_agents.exists():
            print(f"  agents -> {agent_dir}/")
            copy_tree(src_agents, dst_agents, dry_run)

        if src_cmds is not None:
            dst_cmds = target_root / cmd_dir
            if src_cmds.exists():
                print(f"  slash commands -> {cmd_dir}/factory-*.md")
                for cmd_file in sorted(src_cmds.glob(ORCHESTRATOR_CLAUDE_COMMANDS_GLOB)):
                    copy_file(cmd_file, dst_cmds / cmd_file.name, dry_run)

        # Copilot: copy skills + prompts and write VS Code settings
        if tool == "copilot":
            src_skills = repo_root / ".agents" / "custom-skills"
            dst_skills = target_root / ".github" / "skills"
            if src_skills.exists():
                print(f"  skills -> .github/skills/")
                copy_tree(src_skills, dst_skills, dry_run)
            src_prompts = repo_root / ".github" / "prompts"
            dst_prompts = target_root / ".github" / "prompts"
            if src_prompts.exists():
                print(f"  prompts -> .github/prompts/")
                copy_tree(src_prompts, dst_prompts, dry_run)
            _install_vscode_copilot_settings(target_root, dry_run)

        # Per-tool MCP config (Context7 + Chrome DevTools). User-customizable —
        # skip if destination already exists unless --force.
        mcp_rel = ORCHESTRATOR_TOOL_MCP_CONFIGS.get(tool)
        if mcp_rel is not None:
            src_mcp = repo_root / mcp_rel
            dst_mcp = target_root / mcp_rel
            if src_mcp.exists():
                if dst_mcp.exists() and not force:
                    print(f"  {mcp_rel} already exists -- skipping (use --force to overwrite)")
                else:
                    print(f"  mcp config -> {mcp_rel}")
                    copy_file(src_mcp, dst_mcp, dry_run)
                    # Add Stitch/Figma MCP servers only when user opted in
                    _apply_mcp_config(
                        dst_mcp,
                        tool=tool,
                        with_stitch=bool(args and args.with_stitch_mcp),
                        with_figma=bool(args and args.with_figma_mcp),
                        dry_run=dry_run,
                    )

        wf_doc = _tool_workflow_doc(tool, target_root)
        if wf_doc:
            print(f"  workflow pointer -> {wf_doc.name}")
            if tool == "opencode":
                pointer_block = ORCHESTRATOR_CLAUDE_POINTER_BLOCK.replace(
                    ".claude/agents/", ".opencode/agents/"
                ).replace(
                    ".claude/commands/", ".opencode/commands/"
                )
            elif tool == "copilot":
                pointer_block = ORCHESTRATOR_COPILOT_POINTER_BLOCK
            elif tool == "cursor":
                pointer_block = ORCHESTRATOR_CLAUDE_POINTER_BLOCK.replace(
                    ".claude/agents/", ".cursor/agents/"
                ).replace(
                    "/factory-", " /orchestrator factory-"
                )
            else:
                pointer_block = ORCHESTRATOR_CLAUDE_POINTER_BLOCK
            update_workflow_doc_pointer(
                wf_doc,
                ORCHESTRATOR_CLAUDE_POINTER_MARKER,
                pointer_block,
                dry_run,
                force=force,
            )

    # Shared Layer 3: Python deps
    print(f"\n  Python deps -> requirements.txt")
    update_requirements(target_root, ORCHESTRATOR_PYTHON_DEPS, dry_run)

    # Shared Layer 3: gitignore runtime state (any tool)
    print(f"  runtime state -> .gitignore")
    update_gitignore(target_root, ORCHESTRATOR_GITIGNORE_ENTRIES, ORCHESTRATOR_GITIGNORE_HEADER, dry_run, force=force)

    if not dry_run:
        print(f"\n  Then: invoke /factory-spec <feature> in the tool to start a run.")
        # Non-Claude tools need AIDLC_DEFAULT_MODEL to skip Claude-specific model names
        non_claude = [t for t in tools if t != "claude"]
        if non_claude:
            env_path = target_root / ".aidlc-env"
            if not env_path.exists():
                env_path.write_text(
                    "# AIDLC orchestrator — non-Claude tools should use default model\n"
                    "AIDLC_DEFAULT_MODEL=default\n"
                )
            print(f"\n  NOTE: Budget default.yaml contains Claude model names (sonnet/opus).")
            print(f"  Non-Claude tool(s) selected ({', '.join(non_claude)}) should set:")
            print(f"    export AIDLC_DEFAULT_MODEL=default")
            print(f"  Or source the env file:  source {env_path.relative_to(target_root)}")


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
            print(f"  WARNING -- Missing skills (workflow will use inline fallbacks): {', '.join(missing)}")

    return count




CODEGRAPH_NPM_PACKAGE = "@colbymchenry/codegraph"
CODEGRAPH_NODE_MIN = 18

CODEGRAPH_MCP_CONFIG = {
    "mcpServers": {
        "codegraph": {
            "command": "codegraph",
            "args": ["mcp"],
            "env": {}
        }
    }
}

# Allowlist of CodeGraph MCP tools that stage subagents may call.
# Note: codegraph_context and codegraph_explore are EXCLUDED from the
# orchestrator's main session — they return large source sections.
CODEGRAPH_SAFE_ORCHESTRATOR_TOOLS = [
    "codegraph_search",
    "codegraph_node",
    "codegraph_files",
    "codegraph_status",
]


def _check_node_version(min_major: int) -> tuple[bool, str]:
    """Return (ok, version_string). ok=False when node < min_major or not found."""
    try:
        result = subprocess.run(
            ["node", "--version"], capture_output=True, text=True, timeout=10
        )
        version_str = result.stdout.strip()  # e.g. "v20.11.0"
        major = int(version_str.lstrip("v").split(".")[0])
        return major >= min_major, version_str
    except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
        return False, "not found"


def _run_codegraph(cmd: list[str], target_root: Path | None = None, **kwargs) -> subprocess.CompletedProcess:
    """Run a codegraph command, using PowerShell on Windows to resolve .ps1 wrappers."""
    if _is_windows():
        pwsh_cmd = ["powershell", "-NoProfile", "-Command", " ".join(cmd)]
        return subprocess.run(pwsh_cmd, cwd=str(target_root) if target_root else None, **kwargs)
    return subprocess.run(cmd, cwd=str(target_root) if target_root else None, **kwargs)


def _auto_init_codegraph(target_root: Path, dry_run: bool) -> None:
    """Auto-detect codegraph on PATH and run `codegraph init -i` if .codegraph/ missing.

    This is a lightweight post-install step — does NOT install codegraph, only
    initializes an existing installation. Silent skip if codegraph not found.
    """
    cg_dir = target_root / ".codegraph"
    if cg_dir.exists():
        return

    ok, version_str = _check_node_version(CODEGRAPH_NODE_MIN)
    if not ok:
        return

    ok, cg_version = _probe_version(["codegraph", "--version"])
    if not ok:
        return

    print(f"\n--- CodeGraph detected ({cg_version}) -- initializing index ---")
    if dry_run:
        print(f"[DRY-RUN] Would run: codegraph init -i in {target_root}")
        return

    print("  Running codegraph init -i (may take 30s-4min)...")
    init_result = _run_codegraph(["codegraph", "init", "-i"], target_root)
    if init_result.returncode != 0:
        print("  WARNING: codegraph init -i exited with an error -- index may be incomplete.")
        print(f"  Run manually:  cd {target_root} && codegraph init -i")
    else:
        print("  CodeGraph index built successfully.")
        _run_codegraph(["codegraph", "status"], target_root)


def install_codegraph(target_root: Path, dry_run: bool) -> None:
    """Install CodeGraph globally via npm and write .mcp.json to target_root.

    Steps:
      1. Check Node >= 18.
      2. npm install -g @colbymchenry/codegraph.
      3. Write project-local .mcp.json with the codegraph MCP server entry.
         Merges into existing .mcp.json if present.

    Raises RuntimeError if Node < 18 or npm install fails.
    """
    import json

    print("\n--- Installing CodeGraph (@colbymchenry/codegraph) ---")

    # Step 1: Node version check
    ok, version_str = _check_node_version(CODEGRAPH_NODE_MIN)
    if not ok:
        raise RuntimeError(
            f"CodeGraph requires Node >= {CODEGRAPH_NODE_MIN}. "
            f"Detected: {version_str}. Install Node {CODEGRAPH_NODE_MIN}+ and retry."
        )
    print(f"  Node: {version_str} (>= {CODEGRAPH_NODE_MIN}) -- OK")

    # Step 2: check if already installed
    ok, cg_version = _probe_version(["codegraph", "--version"])
    if ok:
        print(f"  codegraph: {cg_version} -- already installed, skipping npm install")
    elif dry_run:
        print(f"[DRY-RUN] Would run: npm install -g {CODEGRAPH_NPM_PACKAGE}")
    else:
        print(f"  Installing {CODEGRAPH_NPM_PACKAGE} globally via npm...")
        # On Windows npm may be a .ps1 script (not resolved by subprocess.run).
        # Use PowerShell explicitly to handle this.
        npm_cmd = (
            ["powershell", "-NoProfile", "-Command", f"npm install -g {CODEGRAPH_NPM_PACKAGE}"]
            if _is_windows()
            else ["npm", "install", "-g", CODEGRAPH_NPM_PACKAGE]
        )
        result = subprocess.run(npm_cmd, capture_output=False)
        if result.returncode != 0:
            raise RuntimeError(
                f"npm install -g {CODEGRAPH_NPM_PACKAGE} failed (exit {result.returncode}). "
                "Check npm permissions or use --prefix for a local install."
            )
        ok, cg_version = _probe_version(["codegraph", "--version"])
        print(f"  codegraph: {cg_version}" if ok else "  codegraph: unknown")

    # Step 3: Write .mcp.json
    mcp_path = target_root / ".mcp.json"
    if dry_run:
        print(f"[DRY-RUN] Would write/merge CodeGraph MCP entry into {mcp_path}")
        return

    if mcp_path.exists():
        try:
            existing = json.loads(mcp_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}
    else:
        existing = {}

    existing.setdefault("mcpServers", {})
    if "codegraph" in existing["mcpServers"]:
        print(f"  .mcp.json already has 'codegraph' MCP entry -- skipping merge")
    else:
        existing["mcpServers"]["codegraph"] = CODEGRAPH_MCP_CONFIG["mcpServers"]["codegraph"]
        mcp_path.write_text(
            json.dumps(existing, indent=2) + "\n", encoding="utf-8"
        )
        print(f"  .mcp.json -- added 'codegraph' MCP server entry")


# ─── Engram persistent memory ────────────────────────────────────────────────

# Per-tool engram setup commands (ordered list of token-lists per tool).
ENGRAM_CLI_SETUP: dict[str, list[list[str]]] = {
    "claude": [
        ["claude", "plugin", "marketplace", "add", "Gentleman-Programming/engram"],
        ["claude", "plugin", "install", "engram"],
    ],
    "opencode": [["engram", "setup", "opencode"]],
}

# MCP-based tools receive an .mcp.json entry instead of a CLI setup command.
ENGRAM_MCP_TOOLS: frozenset[str] = frozenset(
    {"cursor", "copilot", "other"}
)

ENGRAM_MCP_ENTRY: dict = {"command": "engram", "args": ["mcp"]}
ENGRAM_PROJECT_CONFIG_RELPATH = Path(".engram") / "project.json"


def install_engram(tools: list[str], target_root: Path, dry_run: bool) -> None:
    """Wire Engram persistent memory for each selected tool.

    CLI-native tools (claude, opencode): runs the tool-specific setup command(s).
    MCP-based tools (cursor, copilot, …): merges the engram entry into .mcp.json.
    Always writes .engram/project.json with project_name = target_root.name.
    """
    import json

    print("\n--- Installing Engram persistent memory ---")
    project_name = target_root.name

    for tool in tools:
        if tool in ENGRAM_CLI_SETUP:
            ok = True
            for cmd in ENGRAM_CLI_SETUP[tool]:
                if not ok:
                    break
                cmd_str = " ".join(cmd)
                if dry_run:
                    print(f"[DRY-RUN] Would run: {cmd_str}")
                else:
                    print(f"  {cmd_str}")
                    try:
                        result = subprocess.run(cmd, timeout=60)
                        if result.returncode != 0:
                            print(f"  WARNING: exited {result.returncode} -- run manually: {cmd_str}")
                            ok = False
                    except FileNotFoundError:
                        print(f"  WARNING: '{cmd[0]}' not found -- run manually: {cmd_str}")
                        ok = False
                    except subprocess.TimeoutExpired:
                        print(f"  WARNING: command timed out -- run manually: {cmd_str}")
                        ok = False
        elif tool in ENGRAM_MCP_TOOLS:
            mcp_path = target_root / ".mcp.json"
            if dry_run:
                print(f"[DRY-RUN] Would merge engram into {mcp_path.name} ({tool})")
                continue
            existing: dict = {}
            if mcp_path.exists():
                try:
                    existing = json.loads(mcp_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    pass
            existing.setdefault("mcpServers", {})
            if "engram" not in existing["mcpServers"]:
                existing["mcpServers"]["engram"] = ENGRAM_MCP_ENTRY
                mcp_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
                print(f"  engram -> {mcp_path.name} ({tool})")
            else:
                print(f"  .mcp.json already has 'engram' -- skipping ({tool})")

    config_path = target_root / ENGRAM_PROJECT_CONFIG_RELPATH
    if dry_run:
        print(f"[DRY-RUN] Would write {config_path} with project_name={project_name!r}")
    else:
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(
            json.dumps({"project_name": project_name}, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"  project config -> .engram/project.json (project_name={project_name!r})")


# ── Design System (optional, --with-design-system) ──────────────────────────


DESIGN_SYSTEM_SRCS = frozenset({
    "design-system",
    ".agents/custom-skills/design-system-composer",
    ".agents/custom-skills/ui-constraint-validator",
})


def install_design_system(repo_root: Path, target_root: Path, dry_run: bool) -> None:
    """Install design system directory and related skills into target project.

    Copies:
      - design-system/ (tokens, primitives, patterns, anti-patterns)
      - .agents/custom-skills/design-system-composer/
      - .agents/custom-skills/ui-constraint-validator/
    """
    print("\n--- Installing Design System ---")

    for src_name in sorted(DESIGN_SYSTEM_SRCS):
        src = repo_root / src_name
        dst = target_root / src_name
        if not src.exists():
            print(f"  SKIP {src_name} -- not found in repo")
            continue
        if dry_run:
            print(f"[DRY-RUN] Would copy {src_name}/ -> {dst.parent}/")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            _rmtree_force(dst)  # clean install
            copy_tree(src, dst, dry_run=False)
            print(f"  {src_name}/ -> {dst}")

    print("  Design system installed.")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="Install AI-DLC rules into a project for one or more agent tools")
    p.add_argument("--tool", required=False,
                   help="Target agent/tool(s) to install rules for. Comma-separated for multiple "
                        "(e.g., --tool claude,opencode). Valid: " + ", ".join(VALID_TOOLS))
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

    p.add_argument("--force", action="store_true",
                   help="Re-install / upgrade over an existing installation. Overwrites all "
                        "orchestrator files (kernel, runtime, scripts, contracts, subagents) "
                        "while preserving run state (runs/, knowledge/). "
                        "Without this flag, already-installed tools are skipped (merge mode).")
    p.add_argument("--no-venv", dest="no_venv", action="store_true",
                   help="Skip creating .venv and pip-installing requirements.txt. "
                        "Default: a virtualenv is created at <dest>/.venv and the "
                        "target's requirements.txt is installed into it.")
    p.add_argument("--no-codegraph", dest="with_codegraph", action="store_false", default=True,
                   help="Skip CodeGraph installation.")
    p.add_argument("--no-engram", dest="with_engram", action="store_false", default=True,
                   help="Skip Engram persistent memory setup.")
    p.add_argument("--with-design-system", action="store_true", default=True,
                   help="Install the design system (tokens, primitives, patterns, skills). "
                        "Copies design-system/ + design-system-composer + ui-constraint-validator skills. "
                        "Default: install (recommended for UI projects).")
    p.add_argument("--no-design-system", dest="with_design_system", action="store_false",
                   help="Skip design system installation.")
    p.add_argument("--with-stitch-mcp", action="store_true", default=False,
                   help="Install Google Stitch MCP server config (@_davideast/stitch-mcp). "
                        "Default: skip (opt-in — requires Node 18+, GOOGLE_CLOUD_PROJECT, gcloud auth).")
    p.add_argument("--with-figma-mcp", action="store_true", default=False,
                   help="Install Figma MCP server config (official Figma Remote MCP + community fallback). "
                        "Default: skip (opt-in — requires Figma account, OAuth or FIGMA_API_KEY).")
    p.add_argument("--skip-preflight", action="store_true",
                   help="Skip the upfront prerequisite check (python/git/node/npm/etc). "
                        "Use only if you know what you're doing — missing prereqs will "
                        "surface as cryptic errors later in the install.")
    return p.parse_args()


TOOL_DESCRIPTIONS = {
    "cursor":   "Cursor editor — writes to .cursor/agents/ and .cursor/commands/",
    "claude":   "Claude Code CLI — writes to .claude/agents/ and .claude/commands/",
    "copilot":  "GitHub Copilot in VS Code — writes to .github/agents/, .github/prompts/, .github/skills/",
    "opencode": "OpenCode TUI — writes to .opencode/agents/ and .opencode/commands/",
    "other":    "Generic install — writes to .aidlc-orchestrator/agents/ (no native subagent spawning)",
}


# ── Preflight prerequisite gate ──────────────────────────────────────────────


def _parse_semver(raw: str) -> tuple[int, ...] | None:
    """Extract a leading semver-ish tuple from a version string. None on failure."""
    import re
    m = re.search(r"(\d+)(?:\.(\d+))?(?:\.(\d+))?", raw)
    if not m:
        return None
    return tuple(int(x) if x else 0 for x in m.groups())


def _probe_version(cmd: list[str]) -> tuple[bool, str]:
    """Run cmd and return (found, raw-version-string). found=False on any failure."""
    # Windows: many tools (npm, codegraph, …) are .cmd or .ps1 scripts that
    # subprocess.run(CreateProcess) cannot launch directly. Use PowerShell
    # as the primary strategy on Windows; direct subprocess as fallback.
    attempts: list[list[str]] = [cmd]
    if _is_windows():
        pwsh_cmd = ["powershell", "-NoProfile", "-Command", " ".join(cmd)]
        attempts = [pwsh_cmd, cmd]

    for candidate in attempts:
        try:
            result = subprocess.run(candidate, capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                out = (result.stdout or result.stderr or "").strip().splitlines()
                return (True, out[0]) if out else (True, "")
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue

    return False, "not found"


# Each entry: (display_name, probe_cmd, min_version_tuple_or_None,
#              required_when_predicate, install_url, install_hints[],
#              skip_reason_or_None)
def _preflight_specs(args: argparse.Namespace, tools: list[str] | None = None) -> list[tuple]:
    """Build the preflight probe list. `tools` is the resolved tool list — when
    None, conditional probes that depend on tool selection are skipped (caller
    must run a second preflight pass after interactive tool selection)."""
    tools = tools or []
    with_engram = bool(getattr(args, "with_engram", True))
    with_codegraph = bool(getattr(args, "with_codegraph", True))
    using_agent_skills = bool(getattr(args, "with_agent_skills", True)) and not getattr(args, "agent_skills_path", None)

    specs = [
        (
            "Python", [sys.executable, "--version"], (3, 10, 0),
            lambda: True,
            "https://www.python.org/downloads/",
            ["Python 3.10+ is required to run the installer and AIDLC factory scripts.",
             "macOS:          brew install python@3.12  (or: pyenv install 3.12)",
             "Linux (Debian): sudo apt-get install python3 python3-venv python3-pip",
             "Linux (RHEL):   sudo dnf install python3 python3-pip",
             "Windows:        winget install Python.Python.3.12",
             "All platforms:  https://www.python.org/downloads/"],
            None,
        ),
        (
            "Git", ["git", "--version"], None,
            lambda: using_agent_skills,
            "https://git-scm.com/downloads",
            ["macOS:          xcode-select --install",
             "Linux (Debian): sudo apt-get install git",
             "Linux (RHEL):   sudo dnf install git",
             "Windows:        winget install Git.Git",
             "All platforms:  https://git-scm.com/downloads"],
            "not needed (agent skills disabled or local path provided)",
        ),
        (
            "Node.js", ["node", "--version"], (22, 6, 0),
            lambda: True,
            "https://nodejs.org/en/download",
            ["macOS via brew:      brew install node@22",
             "macOS/Linux via nvm:",
             "  curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.1/install.sh | bash",
             "  nvm install 22 && nvm use 22",
             "Linux (Debian):      sudo apt-get install -y nodejs npm",
             "Linux (RHEL):        sudo dnf install nodejs npm",
             "Windows via winget:  winget install OpenJS.NodeJS.LTS",
             "Windows via nvm-win: https://github.com/coreybutler/nvm-windows",
             "All platforms:       https://nodejs.org/en/download",
             "Required for autoskills — Node < 22.6 means lockfile-aware skills will not be installed."],
            None,
        ),
        (
            "npm", ["npm", "--version"], None,
            lambda: True,
            "https://nodejs.org/en/download",
            ["npm ships with Node.js — install Node 22+ and npm comes with it."],
            None,
        ),
    ]

    # Tool-conditional probes — only included when the user has already selected
    # their tool(s). In the first preflight pass (tools=[]) these are omitted so
    # the user doesn't see confusing skip messages before choosing a platform.
    # CodeGraph is NOT probed here — the installer installs it, so there's nothing
    # to preflight-check beyond Node/npm (already verified in pass 1).
    if tools:
        specs += [
            (
                "Claude Code CLI", ["claude", "--version"], None,
                lambda: with_engram and "claude" in tools,
                "https://docs.claude.com/claude-code",
                ["macOS via brew: brew install anthropic/claude/claude",
                 "Or follow the official install at https://docs.claude.com/claude-code",
                 "Not needed if you use --no-engram or a different tool."],
                "not required (engram on Claude uses the claude CLI — no standalone binary needed)",
            ),
            (
                "Engram CLI", ["engram", "--version"], None,
                lambda: with_engram and "opencode" in tools,
                "https://github.com/Gentleman-Programming/engram",
                ["Follow the install instructions at https://github.com/Gentleman-Programming/engram",
                 "Not needed if you use --no-engram or a different tool."],
                "not required (only for engram on OpenCode — for Claude the claude plugin is used instead)",
            ),
        ]

    return specs


PREFLIGHT_EXIT_CODE = 9


def preflight_check(args: argparse.Namespace, tools: list[str] | None = None, label: str = "") -> int:
    """Probe required tools BEFORE writing anything. Exit 9 on any failure.

    Honours --dry-run by printing the checklist but never returning non-zero.
    Honours --skip-preflight by returning 0 immediately.

    `tools`: when None, conditional probes (claude/engram/codegraph CLIs) are
    skipped. Call this function a SECOND time with the resolved tools list
    once interactive tool selection completes.
    `label`: short suffix appended to the header so multi-pass invocations are
    distinguishable in output (e.g. "core" / "tool-specific").
    """
    if getattr(args, "skip_preflight", False):
        print(f"--- Preflight check skipped (--skip-preflight){' -- ' + label if label else ''} ---")
        return 0

    header = "--- Preflight check (prerequisites)"
    if label:
        header += f" -- {label}"
    header += " ---"
    print(f"\n{header}")
    specs = _preflight_specs(args, tools)
    failures: list[tuple] = []
    for spec in specs:
        name, cmd, min_v, required_when, url, hints = spec[:6]
        skip_reason = spec[6] if len(spec) > 6 else None
        if not required_when():
            reason = skip_reason or "not required for this install"
            print(f"  {name:18s} [SKIP]  {reason}")
            continue
        ok, raw = _probe_version(cmd)
        if not ok:
            failures.append((name, "missing", min_v, url, hints, raw))
            print(f"  {name:18s} [FAIL] {raw}")
            continue
        if min_v is None:
            print(f"  {name:18s} [OK] {raw}")
            continue
        parsed = _parse_semver(raw)
        if parsed is None or parsed < min_v:
            failures.append((name, "version_too_old", min_v, url, hints, raw))
            min_v_str = ".".join(str(p) for p in min_v)
            print(f"  {name:18s} [FAIL] {raw} (need >= {min_v_str})")
        else:
            min_v_str = ".".join(str(p) for p in min_v)
            print(f"  {name:18s} [OK] {raw} (>= {min_v_str})")

    if not failures:
        print("  All prerequisites satisfied.\n")
        return 0

    if args.dry_run:
        print(f"\n[DRY-RUN] {len(failures)} prerequisite(s) would block this install -- continuing dry-run.\n")
        return 0

    print()
    print("=" * 70)
    print(f"[FAIL] Cannot proceed -- {len(failures)} prerequisite(s) missing.")
    print("=" * 70)
    for name, kind, min_v, url, hints, raw in failures:
        print()
        if kind == "missing":
            print(f"  Missing: {name}")
        else:
            min_v_str = ".".join(str(p) for p in min_v)
            print(f"  Outdated: {name} -- detected {raw}, need >= {min_v_str}")
        print(f"  Docs:    {url}")
        for h in hints:
            print(f"    {h}")
    print()
    print("Fix the failures above, then re-run this installer.")
    print("(To bypass at your own risk, re-run with --skip-preflight.)")
    print()
    return PREFLIGHT_EXIT_CODE





def interactive_choose_tools() -> list[str]:
    """Prompt user to select one or more tools (comma-separated indices)."""
    choices = list(VALID_TOOLS)
    print()
    print("Which agentic coding tool(s) do you use?")
    print("AIDLC will install the integration files for each tool you select.")
    print()
    for i, c in enumerate(choices, 1):
        desc = TOOL_DESCRIPTIONS.get(c, "")
        print(f"  {i}) {c:9s} {desc}")
    print()
    print("Pick one number, or comma-separated for multiple.")
    print("Examples:")
    print("  '2'    -> Claude Code only")
    print("  '2,4'  -> Claude Code + OpenCode")
    while True:
        try:
            v = input("Your choice: ").strip()
        except KeyboardInterrupt:
            print("\nAborted by user")
            sys.exit(1)
        if not v:
            print("  Please enter a number from 1 to {}. Example: '2'.".format(len(choices)))
            continue
        try:
            indices = [int(x.strip()) - 1 for x in v.split(",") if x.strip()]
        except ValueError:
            print(f"  That doesn't look right -- enter numbers only (you entered: {v!r}).")
            print(f"  Example: '2' or '2,4'.")
            continue
        if not indices:
            print(f"  No numbers found in {v!r}. Example: '2' or '2,4'.")
            continue
        out_of_range = [i + 1 for i in indices if i < 0 or i >= len(choices)]
        if out_of_range:
            print(f"  Out of range: {out_of_range}. Valid: 1-{len(choices)}.")
            continue
        seen: set[str] = set()
        out: list[str] = []
        for idx in indices:
            name = choices[idx]
            if name not in seen:
                seen.add(name)
                out.append(name)
        return out


def _prompt_destination() -> Path:
    """Prompt for install destination with examples + current-dir default."""
    cwd = Path.cwd()
    print()
    print("Where should AIDLC be installed?")
    print("This is the root of the project you want to add AIDLC to.")
    print()
    print("Examples:")
    print("  .                           current directory")
    print("  ~/projects/my-app           absolute path with home expansion")
    print(f"  {cwd}   full absolute path")
    print()
    while True:
        try:
            resp = input(f"Destination [default: {cwd}]: ").strip().strip("'\"")
        except KeyboardInterrupt:
            print("\nAborted by user")
            sys.exit(1)
        if not resp:
            return cwd
        try:
            return Path(resp).expanduser().resolve()
        except (OSError, RuntimeError) as e:
            print(f"  Could not resolve {resp!r}: {e}. Try again.")


def main() -> int:
    args = parse_args()

    # Pass 1 — core preflight (python/git/node/npm + any conditional probes
    # whose required_when() can be resolved from --tool/--with-* flags alone).
    rc = preflight_check(args, tools=None, label="core")
    if rc != 0:
        return rc

    if args.dest:
        target_root = Path(args.dest).expanduser().resolve()
    else:
        target_root = _prompt_destination()
    repo_root = Path(__file__).resolve().parent.parent

    if args.tool:
        try:
            tools = parse_tools_string(args.tool)
        except ValueError as e:
            print(f"ERROR: {e}")
            return 2
    else:
        tools = interactive_choose_tools()

    # Pass 2 — tool-conditional preflight. If the user picked --tool
    # interactively (no CLI flag), conditional probes for claude / engram /
    # codegraph CLIs need to fire NOW that tools are resolved.
    if not args.tool:
        rc = preflight_check(args, tools=tools, label="tool-specific")
        if rc != 0:
            return rc

    # --- Stitch MCP (opt-in, interactive when no CLI flag set) ---
    if not args.with_stitch_mcp and not args.tool:
        print()
        resp = input("Install Google Stitch MCP server? (y/N): ").strip().lower()
        args.with_stitch_mcp = resp in ("y", "yes", "sí", "dale")
        if args.with_stitch_mcp:
            print("  Stitch MCP will be installed (requires Node 18+, GOOGLE_CLOUD_PROJECT, gcloud auth).")

    # --- Figma MCP (opt-in, interactive when no CLI flag set) ---
    if not args.with_figma_mcp and not args.tool:
        print()
        resp = input("Install Figma MCP server? (y/N): ").strip().lower()
        args.with_figma_mcp = resp in ("y", "yes", "sí", "dale")
        if args.with_figma_mcp:
            print("  Figma MCP will be installed (requires Figma account, OAuth or FIGMA_API_KEY).")

    # Agent skills will be installed by default (no interactive prompt)

    # --- Agent Skills integration ---
    skills_dir = target_root / ".agents" / "skills"
    skills_already = skills_dir.exists() and any(skills_dir.iterdir()) if skills_dir.exists() else False
    if args.with_agent_skills and skills_already and not args.force:
        print(f"\nAgent skills already installed at {skills_dir.relative_to(target_root)} -- skipping (use --force to re-install).")
    elif args.with_agent_skills:
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
            for tool in tools:
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

    # --- AIDLC Orchestrator (always installed — mandatory for full workflow) ---
    try:
        install_orchestrator(tools, repo_root, target_root, args.dry_run, force=args.force, args=args)
    except Exception as e:
        print(f"ERROR installing orchestrator: {e}")
        return 6

    # --- CodeGraph (default: install, opt-out via --no-codegraph) ---
    if args.with_codegraph:
        try:
            install_codegraph(target_root, args.dry_run)
        except Exception as e:
            print(f"ERROR installing CodeGraph: {e}")
            print("  CodeGraph is optional -- AIDLC will degrade gracefully without it.")

    # --- Engram (default: install, opt-out via --no-engram) ---
    if args.with_engram:
        install_engram(tools, target_root, args.dry_run)

    # --- Design System (optional, --with-design-system / --no-design-system) ---
    if args.with_design_system:
        try:
            install_design_system(repo_root, target_root, args.dry_run)
        except Exception as e:
            print(f"ERROR installing design system: {e}")
            print("  Design system is optional -- AIDLC will degrade gracefully without it.")

    # --- Python venv + dependencies ---
    if args.no_venv:
        print("\nSkipped Python venv setup (--no-venv).")
    else:
        req_path = ensure_target_requirements(repo_root, target_root, args.dry_run)
        if req_path is None:
            print("\nNo requirements.txt found in target or source -- skipping venv setup.")
        else:
            print("\n--- Setting up Python venv + dependencies ---")
            try:
                create_venv_and_install_requirements(target_root, req_path, args.dry_run)
            except EnvironmentError as e:
                print(f"WARNING: Could not create venv: {e}")
                print("  You can install deps manually:  pip install -r requirements.txt")
            except RuntimeError as e:
                print(f"WARNING: {e}")
                _pip_venv = ".venv/bin/pip" if sys.platform != "win32" else ".venv\\Scripts\\pip"
                print(f"  You can retry manually:  {_pip_venv} install -r requirements.txt")

    # --- CodeGraph init (last step — runs after everything else) ---
    if args.with_codegraph:
        _auto_init_codegraph(target_root, args.dry_run)

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
