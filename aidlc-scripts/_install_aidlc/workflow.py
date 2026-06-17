from __future__ import annotations

from pathlib import Path

from .constants import (
    CURSOR_MDC_FRONTMATTER,
    ORCHESTRATOR_CLAUDE_POINTER_BLOCK,
    ORCHESTRATOR_CLAUDE_POINTER_MARKER,
    ORCHESTRATOR_CODEX_POINTER_BLOCK,
    ORCHESTRATOR_COPILOT_POINTER_BLOCK,
    ORCHESTRATOR_FRIDA_POINTER_BLOCK,
)


def update_requirements(target_root: Path, deps: list[str], dry_run: bool) -> None:
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


def _read_core_workflow(repo_root: Path) -> str | None:
    cwf = repo_root / ".aidlc-orchestrator" / "runtime" / "core-workflow.md"
    if cwf.exists():
        return cwf.read_text(encoding="utf-8")
    return None


def _tool_core_workflow_content(repo_root: Path, tool: str) -> str | None:
    content = _read_core_workflow(repo_root)
    if content is None:
        return None
    if tool == "cursor":
        return CURSOR_MDC_FRONTMATTER + content.replace(
            ".claude/agents/", ".cursor/agents/"
        ).replace(".claude/commands/", ".cursor/commands/")
    if tool == "opencode":
        return content.replace(
            ".claude/agents/", ".opencode/agents/"
        ).replace(".claude/commands/", ".opencode/commands/")
    if tool == "copilot":
        return content.replace(
            ".claude/agents/", ".github/agents/"
        ).replace(".claude/commands/", ".github/commands/")
    if tool == "codex":
        return content.replace(
            ".claude/agents/", ".codex/agents/"
        ).replace(".claude/commands/", ".codex/commands/")
    if tool == "frida":
        return content.replace(
            ".claude/agents/", ".aidlc-orchestrator/agents/"
        ).replace(".claude/commands/", ".aidlc-orchestrator/commands/")
    return content


def update_workflow_doc_pointer(claude_md_path: Path, marker: str, block: str, dry_run: bool, force: bool = False, core_workflow_content: str | None = None) -> None:
    content_to_write = core_workflow_content if core_workflow_content is not None else block
    if dry_run:
        action = "replace" if force else "append"
        source = "full core-workflow.md" if core_workflow_content else "pointer block"
        print(f"[DRY-RUN] Would {action} {source} in {claude_md_path}")
        return
    if claude_md_path.exists():
        existing = claude_md_path.read_text(encoding="utf-8")
        if marker in existing:
            if not force:
                print(f"  workflow doc already contains AIDLC workflow -- no changes")
                return
            start = existing.index(marker)
            end = existing.index("\n## ", start + len(marker)) if "\n## " in existing[start:] else len(existing)
            updated = existing[:start] + content_to_write.lstrip()
            claude_md_path.write_text(updated, encoding="utf-8")
            source = "full core-workflow.md" if core_workflow_content else "pointer block"
            print(f"  replaced {source} in {claude_md_path.relative_to(claude_md_path.parent)}")
            return
        with claude_md_path.open("a", encoding="utf-8") as f:
            if not existing.endswith("\n"):
                f.write("\n")
            f.write(content_to_write)
        source = "full core-workflow.md" if core_workflow_content else "pointer block"
        print(f"  appended {source} to {claude_md_path.relative_to(claude_md_path.parent)}")
    else:
        claude_md_path.parent.mkdir(parents=True, exist_ok=True)
        claude_md_path.write_text(content_to_write.lstrip(), encoding="utf-8")
        source = "full core-workflow.md" if core_workflow_content else "pointer block"
        print(f"  created {claude_md_path.name} with {source}")


def _tool_agent_dir(tool: str) -> str | None:
    return {
        "claude": ".claude/agents",
        "opencode": ".opencode/agents",
        "cursor": ".cursor/agents",
        "copilot": ".github/agents",
        "codex": ".codex/agents",
        "frida": ".aidlc-orchestrator/agents",
    }.get(tool, ".aidlc-orchestrator/agents")


def _tool_commands_dir(tool: str) -> str | None:
    return {
        "claude": ".claude/commands",
        "opencode": ".opencode/commands",
        "cursor": ".cursor/commands",
        "codex": None,
        "frida": None,
    }.get(tool, ".aidlc-orchestrator/commands")


def _tool_workflow_doc(tool: str, target_root: Path) -> Path | None:
    mapping = {
        "claude": target_root / "CLAUDE.md",
        "opencode": target_root / "AGENTS.md",
        "copilot": target_root / ".github" / "copilot-instructions.md",
        "codex": target_root / "AGENTS.md",
        "frida": target_root / "FRIDA.md",
    }
    return mapping.get(tool)
