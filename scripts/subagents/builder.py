#!/usr/bin/env python3
"""Construction Builder subagent — suggests build commands and optional non-destructive checks.

Writes `aidlc-docs/build-report.md`. By default this agent only *suggests*
commands; it will run anything only if `context['run_build']` is truthy.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List

AGENT_ID = "builder"


def _detect_manifests(ws: Path) -> List[str]:
    files = []
    if (ws / "requirements.txt").exists():
        files.append("requirements.txt")
    if (ws / "pyproject.toml").exists():
        files.append("pyproject.toml")
    if (ws / "package.json").exists():
        files.append("package.json")
    if (ws / "go.mod").exists():
        files.append("go.mod")
    if (ws / "pom.xml").exists():
        files.append("pom.xml")
    return files


def run(context: Dict | None = None) -> Dict:
    ctx = context or {}
    workspace = Path(ctx.get("workspace") or ctx.get("path") or ".")
    if not workspace.is_absolute():
        workspace = (Path(__file__).resolve().parents[2] / workspace).resolve()

    docs = Path(ctx.get("aidlc_docs") or workspace.parent / "aidlc-docs")
    docs.mkdir(parents=True, exist_ok=True)

    manifests = _detect_manifests(workspace)
    suggested: List[str] = []
    if "requirements.txt" in manifests:
        suggested.append("python -m pip install -r requirements.txt")
    if "pyproject.toml" in manifests:
        suggested.append("poetry install (or pip-compile + pip install)")
    if "package.json" in manifests:
        suggested.append("npm ci || pnpm install || yarn install")
    if "go.mod" in manifests:
        suggested.append("go build ./...")
    if "pom.xml" in manifests:
        suggested.append("mvn -B package")

    suggested.append("Run unit tests (pytest, npm test, go test)")
    suggested.append("Run linter/static analysis")

    ran: Dict[str, Dict] = {}
    if ctx.get("run_build"):
        # Only perform safe, read-only checks by default.
        # Example: check tool availability
        for tool in ("python", "node", "go", "mvn", "npm", "flake8"):
            ran[tool] = {"available": bool(shutil.which(tool))}

    out = docs / "build-report.md"
    lines: List[str] = ["# Build Report\n\n", f"Workspace: {workspace}\n\n", "## Detected manifests\n\n"]
    if manifests:
        for m in manifests:
            lines.append(f"- {m}\n")
    else:
        lines.append("None\n")

    lines.append("\n## Suggested commands\n\n")
    for s in suggested:
        lines.append(f"- {s}\n")

    if ran:
        lines.append("\n## Environment checks (run_build=true)\n\n")
        for t, r in ran.items():
            lines.append(f"- {t}: {'available' if r.get('available') else 'missing'}\n")

    try:
        out.write_text("".join(lines), encoding="utf-8")
    except Exception as e:
        return {"agent_id": AGENT_ID, "status": "error", "error": str(e)}

    # AutoSkills awareness: summarize installed skills if provided
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
            out.write_text("".join(lines), encoding="utf-8")
        except Exception:
            autosummary = {"error": "failed to read autoskills directory"}

    return {"agent_id": AGENT_ID, "status": "ok", "report_path": str(out), "suggested": suggested, "env_checks": ran, "autoskills": autosummary}


if __name__ == "__main__":
    import sys

    ctx = {}
    if len(sys.argv) > 1:
        try:
            ctx = json.loads(sys.argv[1])
        except Exception:
            ctx = {"raw": sys.argv[1]}
    print(json.dumps(run(ctx), ensure_ascii=False, indent=2))
