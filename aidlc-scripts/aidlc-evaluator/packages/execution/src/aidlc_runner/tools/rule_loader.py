"""AIDLC rule loading tool.

Provides a tool for agents to dynamically read AIDLC rule files on demand,
keeping context window usage low by only loading rules as the workflow needs them.
"""

from __future__ import annotations

from pathlib import Path

from strands import tool


def make_rule_loader(rules_dir: Path) -> object:
    """Create a rule loader tool bound to a specific runtime directory.

    Args:
        rules_dir: Path to the .aidlc-orchestrator/runtime directory.
                   Contains core-workflow.md and common/ lazy-load files.

    Returns:
        A tool-decorated function: load_rule.
    """
    rules_dir = rules_dir.resolve()

    @tool
    def load_rule(rule_path: str) -> str:
        """Load an AIDLC rule file by path.

        Use this to read AIDLC workflow rules lazily as you progress.

        Args:
            rule_path: Path relative to the runtime directory. Examples:
                - 'core-workflow' (shorthand for core-workflow.md)
                - 'common/error-handling.md' (loads from common/)
                - 'common/ascii-diagram-standards.md'
        """
        # Handle the core-workflow shorthand
        if rule_path in ("core-workflow", "core-workflow.md"):
            target = rules_dir / "core-workflow.md"
        else:
            target = rules_dir / rule_path
            if not target.suffix:
                target = target.with_suffix(".md")

        resolved = target.resolve()
        # Safety: stay within rules_dir
        if not str(resolved).startswith(str(rules_dir)):
            return f"Error: Path traversal denied: {rule_path}"

        if not resolved.exists():
            # List available rules to help the agent
            available = _list_available_rules(rules_dir)
            return f"Error: Rule file not found: {rule_path}\n\nAvailable rules:\n{available}"

        return resolved.read_text(encoding="utf-8")

    return load_rule


def _list_available_rules(rules_dir: Path) -> str:
    """List all available rule files for error messages."""
    lines = []

    core = rules_dir / "core-workflow.md"
    if core.exists():
        lines.append("  core-workflow (shorthand)")

    for md_file in sorted(rules_dir.rglob("*.md")):
        rel = md_file.relative_to(rules_dir)
        if rel.name != "core-workflow.md":
            lines.append(f"  {rel}")

    return "\n".join(lines) if lines else "  (no rules found)"
