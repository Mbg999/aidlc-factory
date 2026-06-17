from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .constants import (
    ENGRAM_CLI_SETUP,
    ENGRAM_MCP_ENTRY,
    ENGRAM_MCP_TOOLS,
    ENGRAM_PROJECT_CONFIG_RELPATH,
)


def install_engram(tools: list[str], target_root: Path, dry_run: bool) -> None:
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
            if tool == "frida":
                if dry_run:
                    print(f"[DRY-RUN] Engram entry already in Frida global MCP config ({tool})")
                else:
                    print(f"  engram already in Frida global MCP config ({tool})")
                continue
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
