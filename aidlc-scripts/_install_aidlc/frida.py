from __future__ import annotations

import copy
import json
import os
from pathlib import Path

from .constants import (
    FRIDA_MCP_FALLBACK_CHROME,
    FRIDA_MCP_FALLBACK_CODEGRAPH,
    FRIDA_MCP_FALLBACK_CONTEXT7,
    FRIDA_MCP_FALLBACK_ENGRAM,
)
from .utils import _is_windows


def _frida_mcp_global_path() -> Path:
    if _is_windows():
        appdata = os.environ.get("APPDATA", "")
        return (
            Path(appdata)
            / "Code" / "User" / "globalStorage"
            / "fridaplatform.fridagpt"
            / "frida_code_copilot_mcp_settings.json"
        )
    return Path.home() / ".config" / "frida" / "mcp_settings.json"


def _build_frida_mcp_config(project_path: str) -> dict:
    cg_entry = copy.deepcopy(FRIDA_MCP_FALLBACK_CODEGRAPH)
    cg_entry["args"] = ["serve", "--mcp", "--path", project_path]
    return {
        "mcpServers": {
            "context7": dict(FRIDA_MCP_FALLBACK_CONTEXT7),
            "chrome-devtools": dict(FRIDA_MCP_FALLBACK_CHROME),
            "codegraph": cg_entry,
            "engram": dict(FRIDA_MCP_FALLBACK_ENGRAM),
        }
    }


def _ensure_frida_mcp_config(project_path_str: str, dry_run: bool) -> None:
    dst = _frida_mcp_global_path()
    if dry_run:
        print(f"[DRY-RUN] Would merge Frida MCP entries into {dst}")
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    existing: dict = {}
    if dst.exists():
        try:
            existing = json.loads(dst.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            existing = {}
    existing.setdefault("mcpServers", {})
    our_config = _build_frida_mcp_config(project_path_str)
    merged = 0
    skipped = 0
    for name, entry in our_config["mcpServers"].items():
        if name in existing["mcpServers"]:
            skipped += 1
        else:
            existing["mcpServers"][name] = entry
            merged += 1
    dst.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")
    parts = []
    if merged:
        parts.append(f"added {merged} MCP server(s)")
    if skipped:
        parts.append(f"{skipped} already present — skipped")
    summary = "; ".join(parts) if parts else "no changes"
    print(f"  frida MCP config -> {dst} ({summary})")
