from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .constants import (
    CODEGRAPH_MCP_CONFIG,
    CODEGRAPH_NODE_MIN,
    CODEGRAPH_NPM_PACKAGE,
    CODEGRAPH_TOOL_MAP,
)
from .utils import _is_windows, _log, _probe_version, _rmtree_force


def _check_node_version(min_major: int) -> tuple[bool, str]:
    ok, version_str = _probe_version(["node", "--version"])
    if not ok:
        return False, "not found"
    try:
        major = int(version_str.lstrip("v").split(".")[0])
        return major >= min_major, version_str
    except (ValueError, IndexError, AttributeError):
        return False, "not found"


def _run_codegraph(cmd: list[str], target_root: Path | None = None, **kwargs) -> subprocess.CompletedProcess:
    if _is_windows():
        cmd_cmd = ["cmd", "/c"] + cmd
        return subprocess.run(cmd_cmd, cwd=str(target_root) if target_root else None, **kwargs)
    return subprocess.run(cmd, cwd=str(target_root) if target_root else None, **kwargs)


def _auto_init_codegraph(target_root: Path, dry_run: bool) -> None:
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
        _log("WARNING", "codegraph init -i exited with an error -- index may be incomplete.")
        print(f"  Run manually:  cd {target_root} && codegraph init -i")
    else:
        print("  CodeGraph index built successfully.")
        _run_codegraph(["codegraph", "status"], target_root)


def _cleanup_stale_codegraph_rules(tools: list[str], target_root: Path) -> None:
    _cg_rule_paths: dict[str, Path] = {
        "cursor": target_root / ".cursor" / "rules" / "codegraph.mdc",
    }
    selected = set(tools)
    for tool, rule_path in _cg_rule_paths.items():
        if tool not in selected and rule_path.exists():
            if rule_path.is_dir():
                _rmtree_force(rule_path)
            else:
                rule_path.unlink()
            print(f"  cleaned up stale codegraph rule: {rule_path.relative_to(target_root)}")


def install_codegraph(tools: list[str], target_root: Path, dry_run: bool) -> None:
    print("\n--- Installing CodeGraph (@colbymchenry/codegraph) ---")
    ok, version_str = _check_node_version(CODEGRAPH_NODE_MIN)
    if not ok:
        raise RuntimeError(
            f"CodeGraph requires Node >= {CODEGRAPH_NODE_MIN}. "
            f"Detected: {version_str}. Install Node {CODEGRAPH_NODE_MIN}+ and retry."
        )
    print(f"  Node: {version_str} (>= {CODEGRAPH_NODE_MIN}) -- OK")
    ok, cg_version = _probe_version(["codegraph", "--version"])
    if ok:
        print(f"  codegraph: {cg_version} -- already installed, skipping npm install")
    elif dry_run:
        print(f"[DRY-RUN] Would run: npm install -g {CODEGRAPH_NPM_PACKAGE}")
    else:
        print(f"  Installing {CODEGRAPH_NPM_PACKAGE} globally via npm...")
        npm_install = ["npm", "install", "-g", CODEGRAPH_NPM_PACKAGE]
        npm_cmd = (
            ["cmd", "/c"] + npm_install
            if _is_windows()
            else npm_install
        )
        result = subprocess.run(npm_cmd, capture_output=False)
        if result.returncode != 0:
            raise RuntimeError(
                f"npm install -g {CODEGRAPH_NPM_PACKAGE} failed (exit {result.returncode}). "
                "Check npm permissions or use --prefix for a local install."
            )
        ok, cg_version = _probe_version(["codegraph", "--version"])
        print(f"  codegraph: {cg_version}" if ok else "  codegraph: unknown")
    cg_targets = [CODEGRAPH_TOOL_MAP[t] for t in tools if t in CODEGRAPH_TOOL_MAP]
    if cg_targets and ok:
        target_str = ",".join(cg_targets)
        if dry_run:
            print(f"[DRY-RUN] Would run: codegraph install --target={target_str} --yes")
        else:
            print(f"  Running: codegraph install --target={target_str} --yes")
            install_result = _run_codegraph(
                ["codegraph", "install", f"--target={target_str}", "--yes"],
                target_root,
            )
            if install_result.returncode == 0:
                print(f"  CodeGraph configured for: {target_str}")
                _cleanup_stale_codegraph_rules(tools, target_root)
                return
            print(f"  codegraph install exited {install_result.returncode} -- falling back to manual .mcp.json")
    non_frida = [t for t in tools if t != "frida"]
    if not non_frida:
        if dry_run:
            print(f"[DRY-RUN] Skip .mcp.json write (Frida-only install — uses global config)")
        return
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
    _cleanup_stale_codegraph_rules(tools, target_root)
