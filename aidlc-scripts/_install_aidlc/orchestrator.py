from __future__ import annotations

import argparse
import json
from pathlib import Path

from .constants import (
    ORCHESTRATOR_CLAUDE_COMMANDS_GLOB,
    ORCHESTRATOR_CLAUDE_POINTER_BLOCK,
    ORCHESTRATOR_CLAUDE_POINTER_MARKER,
    ORCHESTRATOR_CODEX_POINTER_BLOCK,
    ORCHESTRATOR_COPILOT_INSTRUCTION_FILES,
    ORCHESTRATOR_COPILOT_POINTER_BLOCK,
    ORCHESTRATOR_EXECUTOR_PKG_DIR,
    ORCHESTRATOR_FACTORY_SCRIPTS,
    ORCHESTRATOR_FRIDA_POINTER_BLOCK,
    ORCHESTRATOR_GITIGNORE_ENTRIES,
    ORCHESTRATOR_GITIGNORE_HEADER,
    ORCHESTRATOR_PYTHON_DEPS,
    ORCHESTRATOR_QUALITY_DOCS,
    ORCHESTRATOR_ROOT_CONFIGS,
    ORCHESTRATOR_TOOL_MCP_CONFIGS,
)
from .frida import _ensure_frida_mcp_config
from .utils import copy_file, copy_tree
from .workflow import (
    _tool_agent_dir,
    _tool_commands_dir,
    _tool_core_workflow_content,
    _tool_workflow_doc,
    update_gitignore,
    update_requirements,
    update_workflow_doc_pointer,
)


def _install_vscode_copilot_settings(target_root: Path, dry_run: bool) -> None:
    vscode_settings = target_root / ".vscode" / "settings.json"
    desired: dict = {
        "chat.subagents.allowInvocationsFromSubagents": True,
        "chat.agentFilesLocations": {".github/agents": True},
        "chat.promptFilesLocations": {".github/prompts": True},
        "chat.instructionsFilesLocations": {".github/instructions": True},
    }
    if dry_run:
        print(f"[DRY-RUN] Would merge Copilot settings into {vscode_settings}")
        return
    existing: dict = {}
    if vscode_settings.exists():
        try:
            existing = json.loads(vscode_settings.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            pass
    changed = False
    for key, value in desired.items():
        if existing.get(key) != value:
            existing[key] = value
            changed = True
    if not changed:
        print(f"  .vscode/settings.json already has Copilot AIDLC settings -- skipping")
        return
    vscode_settings.parent.mkdir(parents=True, exist_ok=True)
    vscode_settings.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    print(f"  .vscode/settings.json -- merged Copilot AIDLC settings")


def _install_copilot_instruction_files(repo_root: Path, target_root: Path, dry_run: bool, force: bool) -> None:
    src_github = repo_root / ".github"
    dst_github = target_root / ".github"
    for name in ORCHESTRATOR_COPILOT_INSTRUCTION_FILES:
        src = src_github / name
        dst = dst_github / name
        if not src.exists():
            continue
        if dst.exists() and not force:
            print(f"  {name} already exists -- skipping (use --force to overwrite)")
            continue
        print(f"  {name} -> .github/{name}")
        copy_file(src, dst, dry_run)


def _install_factory_scripts(repo_root: Path, target_root: Path, dry_run: bool, force: bool) -> None:
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
    for rel_src, label, is_dir in [
        (repo_root / ".aidlc-orchestrator" / "contracts", "contracts", True),
        (repo_root / ".aidlc-orchestrator" / "runtime", "runtime", True),
        (repo_root / ".aidlc-orchestrator" / "prompts", "prompts", True),
    ]:
        if rel_src.exists():
            dst = target_root / rel_src.relative_to(repo_root)
            print(f"  {label} -> {dst.relative_to(target_root)}/")
            copy_tree(rel_src, dst, dry_run)
    src_budget = repo_root / ".aidlc-orchestrator" / "budgets" / "default.yaml"
    dst_budget = target_root / ".aidlc-orchestrator" / "budgets" / "default.yaml"
    if src_budget.exists():
        print(f"  budget policy -> {dst_budget.relative_to(target_root)}")
        copy_file(src_budget, dst_budget, dry_run)
    src_executors = repo_root / ORCHESTRATOR_EXECUTOR_PKG_DIR
    dst_executors = target_root / ORCHESTRATOR_EXECUTOR_PKG_DIR
    if src_executors.exists():
        print(f"  executor adapters -> {dst_executors.relative_to(target_root)}/")
        copy_tree(src_executors, dst_executors, dry_run)
    for rel in ORCHESTRATOR_QUALITY_DOCS:
        src_q = repo_root / rel
        dst_q = target_root / rel
        if src_q.exists():
            print(f"  quality doc -> {dst_q.relative_to(target_root)}")
            copy_file(src_q, dst_q, dry_run)
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


def _install_per_tool_layer(tool: str, repo_root: Path, target_root: Path, dry_run: bool, force: bool) -> None:
    print(f"\n  -- {tool} --")
    agent_dir = _tool_agent_dir(tool)
    cmd_dir = _tool_commands_dir(tool)
    if tool == "opencode":
        src_agents = repo_root / ".opencode" / "agents"
        src_cmds = repo_root / ".opencode" / "commands"
    elif tool == "copilot":
        src_agents = repo_root / ".github" / "agents"
        src_cmds = None
    elif tool == "cursor":
        src_agents = repo_root / ".cursor" / "agents"
        src_cmds = repo_root / ".cursor" / "commands"
    elif tool == "codex":
        src_agents = repo_root / ".codex" / "agents"
        src_cmds = None
    else:
        src_agents = repo_root / ".claude" / "agents"
        src_cmds = repo_root / ".claude" / "commands"
    if agent_dir is not None and src_agents is not None and src_agents.exists():
        dst_agents = target_root / agent_dir
        print(f"  agents -> {agent_dir}/")
        copy_tree(src_agents, dst_agents, dry_run)
    if cmd_dir is not None and src_cmds is not None:
        dst_cmds = target_root / cmd_dir
        if src_cmds.exists():
            print(f"  slash commands -> {cmd_dir}/factory-*.md")
            for cmd_file in sorted(src_cmds.glob(ORCHESTRATOR_CLAUDE_COMMANDS_GLOB)):
                copy_file(cmd_file, dst_cmds / cmd_file.name, dry_run)
    if tool == "copilot":
        src_skills = repo_root / ".agents" / "custom-skills"
        dst_skills_github = target_root / ".github" / "skills"
        dst_skills_custom = target_root / ".agents" / "custom-skills"
        if src_skills.exists():
            print(f"  skills -> .github/skills/ + .agents/custom-skills/")
            copy_tree(src_skills, dst_skills_github, dry_run)
            copy_tree(src_skills, dst_skills_custom, dry_run)
        src_prompts = repo_root / ".github" / "prompts"
        dst_prompts = target_root / ".github" / "prompts"
        if src_prompts.exists():
            print(f"  prompts -> .github/prompts/")
            copy_tree(src_prompts, dst_prompts, dry_run)
        src_instructions = repo_root / ".github" / "instructions"
        dst_instructions = target_root / ".github" / "instructions"
        if src_instructions.exists():
            print(f"  instructions -> .github/instructions/")
            copy_tree(src_instructions, dst_instructions, dry_run)
        _install_copilot_instruction_files(repo_root, target_root, dry_run, force)
        _install_vscode_copilot_settings(target_root, dry_run)
    if tool == "codex":
        src_codex_cfg = repo_root / ".codex" / "config.toml"
        dst_codex_cfg = target_root / ".codex" / "config.toml"
        if src_codex_cfg.exists():
            if dst_codex_cfg.exists() and not force:
                print(f"  .codex/config.toml already exists -- skipping (use --force to overwrite)")
            else:
                print(f"  codex config -> .codex/config.toml")
                copy_file(src_codex_cfg, dst_codex_cfg, dry_run)
    if tool in ("claude", "opencode", "cursor", "codex"):
        src_custom_skills = repo_root / ".agents" / "custom-skills"
        dst_custom_skills = target_root / ".agents" / "custom-skills"
        if src_custom_skills.exists():
            print(f"  custom skills -> .agents/custom-skills/")
            copy_tree(src_custom_skills, dst_custom_skills, dry_run)
    if tool == "frida":
        src_frida_skills = repo_root / ".frida" / "skills"
        dst_frida_skills = target_root / ".agents" / "skills"
        if src_frida_skills.exists():
            print(f"  factory-command skills -> .agents/skills/")
            copy_tree(src_frida_skills, dst_frida_skills, dry_run)
        src_frida_custom = repo_root / ".agents" / "custom-skills"
        dst_frida_custom = target_root / ".agents" / "skills"
        if src_frida_custom.exists():
            print(f"  custom skills -> .agents/skills/")
            copy_tree(src_frida_custom, dst_frida_custom, dry_run)
        _ensure_frida_mcp_config(str(target_root), dry_run)
    if tool == "frida":
        pass
    else:
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
    _install_workflow_pointer(tool, repo_root, target_root, dry_run, force)


def _install_workflow_pointer(tool: str, repo_root: Path, target_root: Path, dry_run: bool, force: bool) -> None:
    wf_doc = _tool_workflow_doc(tool, target_root)
    if not wf_doc:
        return
    print(f"  workflow content -> {wf_doc.name}")
    core_content = _tool_core_workflow_content(repo_root, tool)
    if core_content is None:
        fallback_blocks = {
            "opencode": ORCHESTRATOR_CLAUDE_POINTER_BLOCK.replace(
                ".claude/agents/", ".opencode/agents/"
            ).replace(".claude/commands/", ".opencode/commands/"),
            "copilot": ORCHESTRATOR_COPILOT_POINTER_BLOCK,
            "cursor": ORCHESTRATOR_CLAUDE_POINTER_BLOCK.replace(
                ".claude/agents/", ".cursor/agents/"
            ).replace("/factory-", " /orchestrator factory-"),
            "codex": ORCHESTRATOR_CODEX_POINTER_BLOCK,
            "frida": ORCHESTRATOR_FRIDA_POINTER_BLOCK,
        }
        pointer_block = fallback_blocks.get(tool, ORCHESTRATOR_CLAUDE_POINTER_BLOCK)
        update_workflow_doc_pointer(
            wf_doc, ORCHESTRATOR_CLAUDE_POINTER_MARKER, pointer_block,
            dry_run, force=force, core_workflow_content=None,
        )
    else:
        update_workflow_doc_pointer(
            wf_doc, ORCHESTRATOR_CLAUDE_POINTER_MARKER, "",
            dry_run, force=force, core_workflow_content=core_content,
        )


def _install_shared_deps(tools: list[str], target_root: Path, dry_run: bool, force: bool) -> None:
    print(f"\n  Python deps -> requirements.txt")
    update_requirements(target_root, ORCHESTRATOR_PYTHON_DEPS, dry_run)
    print(f"  runtime state -> .gitignore")
    update_gitignore(target_root, ORCHESTRATOR_GITIGNORE_ENTRIES, ORCHESTRATOR_GITIGNORE_HEADER, dry_run, force=force)
    if not dry_run:
        print(f"\n  Then: invoke /factory-spec <feature> in the tool to start a run.")
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


def install_orchestrator(tools: list[str], repo_root: Path, target_root: Path, dry_run: bool, force: bool = False, args: argparse.Namespace | None = None) -> None:
    tools_label = ", ".join(tools)
    print(f"\n--- Installing AIDLC Orchestrator (Phases 0-6) for {tools_label} ---")
    _install_factory_scripts(repo_root, target_root, dry_run, force)
    for tool in tools:
        _install_per_tool_layer(tool, repo_root, target_root, dry_run, force)
    _install_shared_deps(tools, target_root, dry_run, force)
