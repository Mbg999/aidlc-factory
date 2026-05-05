#!/usr/bin/env python3
"""Construction Reviewer subagent — automated review during construction.

Performs lightweight checks (TODOs, secrets) and runs linters if available
(flake8, eslint). Writes `aidlc-docs/construction-review.md` and returns a
summary object.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

AGENT_ID = "construction-reviewer"


_SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__", ".git", "dist", "build", ".tox", ".mypy_cache", ".eggs"}


def _gather_files(base: Path, patterns: List[str]) -> List[Path]:
    out: List[Path] = []
    for p in base.rglob("*"):
        if any(part in _SKIP_DIRS for part in p.relative_to(base).parts):
            continue
        if not p.is_file():
            continue
        for pat in patterns:
            if p.match(pat) or p.name.endswith(pat.lstrip("*")):
                out.append(p)
                break
    return sorted(out)


def _search_todos_and_secrets(files: List[Path]) -> Dict[str, List[str]]:
    todos: List[str] = []
    secrets: List[str] = []
    todo_re = re.compile(r"TODO|FIXME", re.I)
    secret_re = re.compile(r"password\b|passwd\b|secret\b|api[_-]?key|token", re.I)
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        if todo_re.search(text):
            todos.append(str(f))
        if secret_re.search(text):
            secrets.append(str(f))
    return {"todos": todos, "secrets": secrets}


def _run_linter(cmd: List[str], cwd: Path, timeout: int = 30) -> Dict:
    try:
        proc = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True, timeout=timeout)
        return {"exit_code": proc.returncode, "stdout": proc.stdout[:20000], "stderr": proc.stderr[:20000]}
    except Exception as e:
        return {"error": str(e)}


def run(context: Dict | None = None) -> Dict:
    ctx = context or {}
    workspace = Path(ctx.get("workspace") or ctx.get("path") or ".")
    if not workspace.is_absolute():
        workspace = (Path(__file__).resolve().parents[2] / workspace).resolve()

    docs = Path(ctx.get("aidlc_docs") or workspace.parent / "aidlc-docs")
    docs.mkdir(parents=True, exist_ok=True)

    code_files = _gather_files(workspace, ["*.py", "*.js", "*.ts"])
    scan = _search_todos_and_secrets(code_files)

    linters: Dict[str, Dict] = {}
    if shutil.which("ruff"):
        linters["ruff"] = _run_linter(["ruff", "check", "--output-format", "concise", str(workspace)], workspace)
    elif shutil.which("flake8"):
        linters["flake8"] = _run_linter(["flake8", str(workspace)], workspace)
    if shutil.which("eslint"):
        linters["eslint"] = _run_linter(["eslint", "--format", "compact", str(workspace)], workspace)

    out = docs / "construction-review.md"
    lines: List[str] = ["# Construction Review\n\n", f"Workspace: {workspace}\n\n"]
    lines.append("## TODOs detected\n\n")
    if scan.get("todos"):
        for t in scan["todos"]:
            lines.append(f"- {t}\n")
    else:
        lines.append("None\n")

    lines.append("\n## Potential secrets\n\n")
    if scan.get("secrets"):
        for s in scan["secrets"]:
            lines.append(f"- {s}\n")
    else:
        lines.append("None\n")

    if linters:
        lines.append("\n## Linter outputs\n\n")
        for name, res in linters.items():
            lines.append(f"### {name}\n\n")
            if res.get("error"):
                lines.append(f"Error: {res.get('error')}\n")
            else:
                lines.append("```")
                lines.append((res.get("stdout") or "")[:1000])
                lines.append("```\n\n")

    # AutoSkills awareness: if autoskills info is provided, list installed skills
    autoskills = ctx.get("autoskills") if isinstance(ctx, dict) else None
    autosummary = None
    if autoskills:
        try:
            autos_dir = autoskills.get("autoskills_dir")
            skills = []
            if autos_dir:
                from pathlib import Path as _P

                p = _P(autos_dir)
                if not p.exists():
                    rf = ctx.get("run_folder") if isinstance(ctx, dict) else None
                    if rf:
                        cand = _P(rf) / autos_dir
                        if cand.exists():
                            p = cand
                if not p.exists():
                    repo_root = _P(__file__).resolve().parents[2]
                    cand2 = repo_root / autos_dir
                    if cand2.exists():
                        p = cand2
                if p.exists() and p.is_dir():
                    for d in sorted(x.name for x in p.iterdir() if x.is_dir()):
                        skills.append(d)
            autosummary = {"autoskills_dir": autos_dir, "skills": skills}
            lines.append("\n## AutoSkills detected\n\n")
            if skills:
                for s in skills:
                    lines.append(f"- {s}\n")
            else:
                lines.append("None detected\n")
        except Exception:
            autosummary = {"error": "failed to read autoskills directory"}

    try:
        out.write_text("".join(lines), encoding="utf-8")
    except Exception as e:
        return {"agent_id": AGENT_ID, "status": "error", "error": str(e)}

    summary = {"todos": len(scan.get("todos", [])), "secrets": len(scan.get("secrets", [])), "linters": list(linters.keys())}

    # --- Memory: emit learnings for write-back by the manager ---
    memory_observations: List[Dict] = []
    n_todos = len(scan.get("todos", []))
    n_secrets = len(scan.get("secrets", []))
    if n_todos or n_secrets:
        memory_observations.append({
            "content": (
                f"Construction review of {workspace.name}: "
                f"{n_todos} TODO files, {n_secrets} potential secret files"
            ),
            "tags": ["review", "quality", workspace.name],
            "memory_type": "episodic",
        })
    if linters:
        clean = [name for name, res in linters.items() if res.get("exit_code") == 0]
        memory_observations.append({
            "content": f"Linters run on {workspace.name}: {list(linters.keys())}. Clean: {clean}",
            "tags": ["linting", "review", workspace.name],
            "memory_type": "semantic",
        })

    return {"agent_id": AGENT_ID, "status": "ok", "report_path": str(out), "summary": summary, "autoskills": autosummary, "memory_observations": memory_observations}


if __name__ == "__main__":
    import sys

    ctx = {}
    if len(sys.argv) > 1:
        try:
            ctx = json.loads(sys.argv[1])
        except Exception:
            ctx = {"raw": sys.argv[1]}
    print(json.dumps(run(ctx), ensure_ascii=False, indent=2))
