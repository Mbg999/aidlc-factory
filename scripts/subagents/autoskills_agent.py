#!/usr/bin/env python3
"""AutoSkills subagent wrapper.

Runs `npx autoskills` in the target project and returns a JSON-friendly report.

Usage (from manager):
  python3 scripts/subagents/manager.py midudev-autoskills '{"path":".", "install": false}'

The agent attempts a safe dry-run by default. It requires `npx` (Node.js >= 22).
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

REPO_ROOT = Path(__file__).resolve().parents[2]
AGENT_ID = "midudev-autoskills"


def detect_mode(project_path: Path) -> str:
    # Heuristic: presence of common manifest/build files or source files -> brownfield
    manifests = [
        "package.json",
        "pyproject.toml",
        "go.mod",
        "pom.xml",
        "build.gradle",
        "build.gradle.kts",
    ]
    for m in manifests:
        if (project_path / m).exists():
            return "brownfield"

    # Look for source files
    exts = [".py", ".js", ".ts", ".go", ".java", ".kt", ".swift", ".dart"]
    for ext in exts:
        if any(project_path.rglob(f"*{ext}")):
            return "brownfield"

    return "greenfield"


def run_autoskills(project_path: Path, dry_run: bool = True, yes: bool = True, timeout: int = 300) -> Dict[str, Any]:
    cmd = ["npx", "autoskills"]
    if dry_run:
        cmd.append("--dry-run")
    if yes:
        cmd.append("--yes")

    proc = subprocess.run(cmd, cwd=str(project_path), capture_output=True, text=True, timeout=timeout)
    return {"returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr}


def parse_recommendations(stdout: str) -> List[str]:
    out: List[str] = []
    for ln in stdout.splitlines():
        s = ln.strip()
        if not s:
            continue
        if s.startswith("-") or s.startswith("•"):
            s = s.lstrip("-•").strip()
            out.append(s)
        elif "install" in s.lower() or "skill" in s.lower():
            out.append(s)
    # Deduplicate while preserving order
    seen = set()
    res = []
    for v in out:
        if v not in seen:
            seen.add(v)
            res.append(v)
    return res


def run(context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    ctx = context or {}
    project_path = Path(ctx.get("path", "."))
    if not project_path.is_absolute():
        project_path = (REPO_ROOT / project_path).resolve()

    mode = ctx.get("mode") or detect_mode(project_path)
    install = bool(ctx.get("install", False))

    result: Dict[str, Any] = {
        "project_path": str(project_path),
        "detected_mode": mode,
        "node_available": shutil.which("node") is not None,
        "npx_available": shutil.which("npx") is not None,
    }

    if not result["npx_available"]:
        result["error"] = "npx not found; please install Node.js >= 22 and run again"
        # Conform to manager expected schema
        result["agent_id"] = AGENT_ID
        result["status"] = "error"
        return result

    try:
        out = run_autoskills(project_path, dry_run=not install, yes=True)
        result["autoskills_exit_code"] = out["returncode"]
        result["autoskills_stdout"] = out["stdout"]
        result["autoskills_stderr"] = out["stderr"]
        result["recommendations"] = parse_recommendations(out["stdout"])
    except Exception as e:
        result["error"] = f"Exception running autoskills: {e}"

    # Provide minimal manager contract fields
    result.setdefault("agent_id", AGENT_ID)
    # status: 'error' when there is an error key, otherwise 'ok'
    result.setdefault("status", "error" if "error" in result else "ok")

    return result


if __name__ == "__main__":
    import sys

    ctx = {}
    if len(sys.argv) > 1:
        try:
            ctx = json.loads(sys.argv[1])
        except Exception:
            ctx = {"raw": sys.argv[1]}

    print(json.dumps(run(ctx), ensure_ascii=False, indent=2))
