from __future__ import annotations

import json
from pathlib import Path

from .constants import (
    COOKBOOK_MCP_SERVER_ENTRY,
    COOKBOOK_MCP_SERVER_ENTRY_OPENCODE,
    COOKBOOK_MCP_TARGET_FILES,
    COOKBOOK_MCP_TOOL_FILES,
    COOKBOOK_SKILL_DIR,
    COOKBOOK_SKILL_NAME,
    COOKBOOK_SKILL_RELPATH,
)


def _write_cookbook_mcp_config(target_root: Path, dry_run: bool,
                                tools: list[str] | None = None) -> int:
    written = 0
    allowed = set()
    if tools:
        for t in tools:
            allowed.update(COOKBOOK_MCP_TOOL_FILES.get(t, []))
    else:
        for f, _ in COOKBOOK_MCP_TARGET_FILES:
            allowed.add(f)
    for relpath, servers_key in COOKBOOK_MCP_TARGET_FILES:
        if relpath not in allowed:
            continue
        mcp_path = target_root / relpath
        if dry_run:
            print(f"[DRY-RUN] Would merge Cookbook MCP entry into {relpath}")
            written += 1
            continue
        existing: dict = {}
        if mcp_path.exists():
            try:
                existing = json.loads(mcp_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                existing = {}
        if relpath == "opencode.json":
            existing.setdefault(servers_key, {})
            if COOKBOOK_SKILL_NAME in existing[servers_key]:
                print(f"  {relpath} already has '{COOKBOOK_SKILL_NAME}' -- skipping")
                continue
            existing[servers_key][COOKBOOK_SKILL_NAME] = COOKBOOK_MCP_SERVER_ENTRY_OPENCODE
        else:
            existing.setdefault(servers_key, {})
            if COOKBOOK_SKILL_NAME in existing[servers_key]:
                print(f"  {relpath} already has '{COOKBOOK_SKILL_NAME}' -- skipping")
                continue
            existing[servers_key][COOKBOOK_SKILL_NAME] = dict(COOKBOOK_MCP_SERVER_ENTRY)
        mcp_path.parent.mkdir(parents=True, exist_ok=True)
        mcp_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
        print(f"  Cookbook MCP -> {relpath}")
        written += 1
    return written


def _read_cookbook_skill_content(repo_root: Path) -> str | None:
    skill_src = repo_root / COOKBOOK_SKILL_RELPATH
    if skill_src.exists():
        return skill_src.read_text(encoding="utf-8")
    return None


def _write_cookbook_skill(repo_root: Path, target_root: Path, dry_run: bool) -> bool:
    skill_dir = target_root / COOKBOOK_SKILL_DIR
    skill_path = skill_dir / "SKILL.md"
    if dry_run:
        print(f"[DRY-RUN] Would write Cookbook skill to {skill_path.relative_to(target_root)}")
        return True
    content = _read_cookbook_skill_content(repo_root)
    if content is None:
        print(f"  WARNING: Cookbook skill source not found at {repo_root / COOKBOOK_SKILL_RELPATH} -- skipping skill registration.")
        return False
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_path.write_text(content, encoding="utf-8")
    print(f"  Cookbook skill -> {COOKBOOK_SKILL_DIR}/SKILL.md")
    return True


def _set_cookbook_budget_flag(target_root: Path, dry_run: bool) -> bool:
    budget_path = target_root / ".aidlc-orchestrator" / "budgets" / "default.yaml"
    if dry_run:
        print(f"[DRY-RUN] Would set architecture_cookbook_enabled: true in {budget_path.relative_to(target_root)}")
        return True
    if not budget_path.exists():
        print(f"  WARNING: budget file not found at {budget_path.relative_to(target_root)} -- skipping flag.")
        return False
    content = budget_path.read_text(encoding="utf-8")
    if "architecture_cookbook_enabled: true" in content:
        print(f"  Budget flag already set -- skipping.")
        return True
    if "architecture_cookbook_enabled: false" in content:
        updated = content.replace(
            "architecture_cookbook_enabled: false",
            "architecture_cookbook_enabled: true"
        )
        budget_path.write_text(updated, encoding="utf-8")
        print(f"  Budget flag: architecture_cookbook_enabled: true")
        return True
    print(f"  Budget flag: architecture_cookbook_enabled: true (appended)")
    with budget_path.open("a") as f:
        f.write(f"\n  architecture_cookbook_enabled: true\n")
    return True


def _install_cookbook(repo_root: Path, target_root: Path, dry_run: bool,
                      tools: list[str] | None = None) -> None:
    print("\n--- Installing AI Architecture Cookbook ---")
    written = _write_cookbook_mcp_config(target_root, dry_run, tools=tools)
    if not dry_run:
        print(f"  MCP config written to {written} files.")
    print("  MCP server: npx @ai-architecture-cookbook/mcp-server")
    _write_cookbook_skill(repo_root, target_root, dry_run)
    _set_cookbook_budget_flag(target_root, dry_run)
    print("  Cookbook installation complete.")
