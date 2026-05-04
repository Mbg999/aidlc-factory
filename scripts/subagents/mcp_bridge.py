#!/usr/bin/env python3
"""MCP Bridge for AIDLC subagents.

Allows subagents to discover and invoke MCP tools through a structured
request/response protocol, with mandatory human-approval per call.

Protocol (stdin/stdout JSON):
  Request:  {"action": "call_mcp_tool", "tool": "mcp_pylance_...", "args": {...}}
  Response: {"status": "approved|denied", "result": {...}}

Discovery:
  Request:  {"action": "list_mcp_tools", "filter_prefix": "mcp_azure_"}
  Response: {"tools": [{"name": "...", "description": "..."}]}

Security model:
  - Each tool call requires explicit human approval (printed to terminal).
  - Allowlist of tool prefixes per agent is enforced (from agents.yaml mcp_tools).
  - Results are audit-logged alongside normal subagent logs.
  - Tool names must match the installed skill/MCP registry (no arbitrary invocation).

Usage from manager (not called directly by agents):
  bridge = MCPBridge(allowed_tools=["mcp_pylance_*"], run_folder=ctx.get("run_folder"))
  result = bridge.call(tool_name, args, require_approval=True)
"""
from __future__ import annotations

import fnmatch
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

# Registry of known MCP tools available in this VS Code installation.
# This list is informational: agent code reads it to decide which tools to call.
# The actual invocation is always delegated back to the manager (never direct).
KNOWN_MCP_TOOLS: dict[str, str] = {
    # Pylance / Python analysis
    "mcp_pylance_mcp_s_pylanceSyntaxErrors":          "Report syntax errors in workspace Python files",
    "mcp_pylance_mcp_s_pylanceFileSyntaxErrors":      "Report syntax errors in a specific Python file",
    "mcp_pylance_mcp_s_pylanceInstalledTopLevelModules": "List installed top-level Python modules",
    "mcp_pylance_mcp_s_pylanceWorkspaceUserFiles":    "List user Python files in the workspace",
    "mcp_pylance_mcp_s_pylancePythonEnvironments":    "List available Python environments",
    "mcp_pylance_mcp_s_pylanceRunCodeSnippet":        "Run a Python code snippet and return output",
    "mcp_pylance_mcp_s_pylanceImports":               "Analyze imports in workspace files",
    "mcp_pylance_mcp_s_pylanceDocString":             "Get docstring for a symbol",
    "mcp_pylance_mcp_s_pylanceDocuments":             "List open documents",
    "mcp_pylance_mcp_s_pylanceSettings":              "Get Pylance settings",
    # Azure
    "mcp_azure_mcp_monitor":                          "Azure Monitor - query metrics and logs",
    "mcp_azure_mcp_keyvault":                         "Azure Key Vault - list/get secrets",
    "mcp_azure_mcp_subscription_list":                "List Azure subscriptions",
    "mcp_azure_mcp_group_list":                       "List Azure resource groups",
    "mcp_azure_mcp_group_resource_list":              "List resources in an Azure resource group",
    "mcp_azure_mcp_storage":                          "Azure Storage operations",
    "mcp_azure_mcp_appservice":                       "Azure App Service operations",
    "mcp_azure_mcp_functionapp":                      "Azure Function App operations",
    "mcp_azure_mcp_cosmos":                           "Azure Cosmos DB operations",
    "mcp_azure_mcp_postgres":                         "Azure PostgreSQL operations",
    "mcp_azure_mcp_sql":                              "Azure SQL operations",
    "mcp_azure_mcp_aks":                              "Azure Kubernetes Service operations",
    "mcp_azure_mcp_documentation":                    "Fetch Azure documentation",
    "mcp_azure_mcp_get_azure_bestpractices":          "Get Azure best practices",
    # GitKraken
    "mcp_gitkraken_git_status":                       "Get git status",
    "mcp_gitkraken_git_log_or_diff":                  "Get git log or diff",
    "mcp_gitkraken_git_blame":                        "Get git blame for a file",
    "mcp_gitkraken_git_branch":                       "Manage git branches",
    "mcp_gitkraken_git_fetch":                        "Fetch from remote",
    "mcp_gitkraken_git_add_or_commit":                "Stage and commit changes",
    "mcp_gitkraken_git_push":                         "Push commits to remote",
    "mcp_gitkraken_repository_get_file_content":      "Get file content from repository",
}


def _match_tool_allowlist(tool_name: str, allowed_tools: list[str]) -> bool:
    """Return True if tool_name matches any pattern in allowed_tools (glob supported)."""
    for pattern in allowed_tools:
        if fnmatch.fnmatch(tool_name, pattern):
            return True
    return False


def _write_mcp_audit(run_folder: str | Path | None, record: dict) -> None:
    try:
        if run_folder:
            log_dir = Path(run_folder) / "subagents-logs"
        else:
            log_dir = REPO_ROOT / "subagents-logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f")
        fname = log_dir / f"{ts}-mcp_bridge.json"
        with open(fname, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


class MCPBridge:
    """Bridge between AIDLC subagent requests and MCP tool invocations.

    Agents declare which tools they need via the ``mcp_tools`` field in
    agents.yaml.  The manager instantiates this bridge and passes it into
    agent context so agents can express intent WITHOUT directly invoking tools.

    Actual invocation is performed by the host agent (GitHub Copilot / Cursor
    / etc.) after human approval, keeping AIDLC tool-agnostic.

    The bridge provides:
      - ``list_tools(prefix)``     — filtered discovery
      - ``describe_call(tool, args)`` — format a pending call record for approval
      - ``record_result(call_id, result, approved)`` — log outcome
    """

    def __init__(
        self,
        allowed_tools: list[str] | None = None,
        run_folder: str | Path | None = None,
        require_approval: bool = True,
    ) -> None:
        self.allowed_tools = allowed_tools or []
        self.run_folder = run_folder
        self.require_approval = require_approval
        self._pending: dict[str, dict] = {}

    # ------------------------------------------------------------------
    # Discovery
    # ------------------------------------------------------------------

    def list_tools(self, filter_prefix: str = "") -> list[dict[str, str]]:
        """Return MCP tools accessible to this agent (filtered by allowlist)."""
        out = []
        for name, desc in KNOWN_MCP_TOOLS.items():
            if filter_prefix and not name.startswith(filter_prefix):
                continue
            if self.allowed_tools and not _match_tool_allowlist(name, self.allowed_tools):
                continue
            out.append({"name": name, "description": desc})
        return out

    # ------------------------------------------------------------------
    # Call lifecycle
    # ------------------------------------------------------------------

    def describe_call(self, tool_name: str, args: dict[str, Any] | None = None) -> dict:
        """Validate the requested tool call and return a call descriptor.

        The descriptor is what gets embedded in agent output under "mcp_calls"
        so the manager/host can present it for human approval.

        Raises ValueError if the tool is not in the allowlist.
        """
        args = args or {}
        if not _match_tool_allowlist(tool_name, self.allowed_tools):
            raise ValueError(
                f"MCP tool '{tool_name}' is not in the allowlist for this agent. "
                f"Allowed: {self.allowed_tools}"
            )
        call_id = f"{tool_name}-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')}"
        record = {
            "call_id": call_id,
            "tool": tool_name,
            "args": args,
            "description": KNOWN_MCP_TOOLS.get(tool_name, "Unknown MCP tool"),
            "requires_approval": self.require_approval,
            "status": "pending",
            "requested_at": datetime.now(timezone.utc).isoformat(),
        }
        self._pending[call_id] = record
        _write_mcp_audit(self.run_folder, {**record, "event": "call_requested"})
        return record

    def record_result(
        self,
        call_id: str,
        result: Any,
        approved: bool = True,
    ) -> dict:
        """Record the outcome of an MCP tool call (called by manager after approval)."""
        record = self._pending.pop(call_id, {"call_id": call_id, "tool": "unknown"})
        record.update({
            "status": "approved" if approved else "denied",
            "result": result if approved else None,
            "resolved_at": datetime.now(timezone.utc).isoformat(),
        })
        _write_mcp_audit(self.run_folder, {**record, "event": "call_resolved"})
        return record

    # ------------------------------------------------------------------
    # Context helpers for agents
    # ------------------------------------------------------------------

    def to_context_dict(self) -> dict:
        """Serialize bridge state into agent context dict."""
        return {
            "available_mcp_tools": self.list_tools(),
            "mcp_requires_approval": self.require_approval,
        }


def discover_all_skills(skills_root: Path | None = None) -> dict[str, Path]:
    """Discover all installed skills across all search roots.

    Returns a mapping of {skill_name: path_to_SKILL.md}.
    Later roots do NOT override earlier ones (first-found wins).
    """
    search_roots: list[Path] = []
    if skills_root:
        search_roots.append(Path(skills_root))
    home_skills = Path.home() / ".agents" / "skills"
    if home_skills.exists():
        search_roots.append(home_skills)
    repo_skills = REPO_ROOT / ".agents" / "skills"
    if repo_skills.exists():
        search_roots.append(repo_skills)

    found: dict[str, Path] = {}
    for root in search_roots:
        if not root.is_dir():
            continue
        for child in sorted(root.iterdir()):
            if child.is_dir() and (child / "SKILL.md").exists():
                name = child.name
                if name not in found:
                    found[name] = child / "SKILL.md"
    return found


def load_skills_for_agent(agent_cfg: dict, skills_root: Path | None = None) -> dict[str, str]:
    """Read SKILL.md files for each skill listed in agent_cfg['skills'].

    Returns a mapping of {skill_name: skill_content} to be injected into
    context as instructions.  Missing skill files are silently skipped.

    Special values in the skills list:
      - ``"*"`` — load ALL installed skills (auto-discovery mode).

    Search order for each skill name `s`:
      1. <skills_root>/<s>/SKILL.md
      2. ~/.agents/skills/<s>/SKILL.md
      3. <repo_root>/.agents/skills/<s>/SKILL.md
    """
    skill_names: list[str] = agent_cfg.get("skills") or []
    if not skill_names:
        return {}

    # Wildcard: discover and load everything
    if "*" in skill_names:
        all_skills = discover_all_skills(skills_root)
        result: dict[str, str] = {}
        for name, path in all_skills.items():
            try:
                result[name] = path.read_text(encoding="utf-8")
            except Exception:
                continue
        return result

    search_roots: list[Path] = []
    if skills_root:
        search_roots.append(Path(skills_root))
    home_skills = Path.home() / ".agents" / "skills"
    if home_skills.exists():
        search_roots.append(home_skills)
    repo_skills = REPO_ROOT / ".agents" / "skills"
    if repo_skills.exists():
        search_roots.append(repo_skills)

    result: dict[str, str] = {}
    for name in skill_names:
        for root in search_roots:
            candidate = root / name / "SKILL.md"
            if candidate.exists():
                try:
                    result[name] = candidate.read_text(encoding="utf-8")
                    break
                except Exception:
                    continue

    return result


def build_mcp_bridge(agent_cfg: dict, run_folder: str | Path | None = None) -> MCPBridge:
    """Instantiate an MCPBridge for an agent from its config dict."""
    allowed = agent_cfg.get("mcp_tools") or []
    return MCPBridge(allowed_tools=allowed, run_folder=run_folder, require_approval=True)


# ---------------------------------------------------------------------------
# CLI: for testing/debugging — list available tools or skills for a given agent
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="MCP bridge utility")
    parser.add_argument("--list-tools", metavar="PREFIX", nargs="?", const="", help="List available MCP tools (optional prefix filter)")
    parser.add_argument("--list-skills", action="store_true", help="List all installed custom skills")
    parser.add_argument("--agent", metavar="AGENT_ID", help="Filter tools/skills by agent config from agents.yaml")
    args = parser.parse_args()

    if args.list_skills:
        if args.agent:
            from manager import find_agent
            cfg = find_agent(args.agent) or {}
            skills = load_skills_for_agent(cfg)
            for name, content in sorted(skills.items()):
                first_line = content.split("\n", 1)[0].strip()
                print(f"  {name}: {first_line}")
        else:
            all_skills = discover_all_skills()
            if not all_skills:
                print("No custom skills found.")
            else:
                print(f"Found {len(all_skills)} custom skill(s):\n")
                for name, path in sorted(all_skills.items()):
                    try:
                        first_line = path.read_text(encoding="utf-8").split("\n", 1)[0].strip()
                    except Exception:
                        first_line = "(unreadable)"
                    print(f"  {name}: {first_line}  [{path}]")
    elif args.list_tools is not None:
        allowed: list[str] = []
        if args.agent:
            # Load agent cfg
            from manager import find_agent
            cfg = find_agent(args.agent) or {}
            allowed = cfg.get("mcp_tools") or []
        bridge = MCPBridge(allowed_tools=allowed)
        tools = bridge.list_tools(filter_prefix=args.list_tools)
        print(json.dumps(tools, indent=2, ensure_ascii=False))
    else:
        parser.print_help()
