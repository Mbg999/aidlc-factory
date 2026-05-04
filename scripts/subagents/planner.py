#!/usr/bin/env python3
"""Construction Planner subagent — generates a construction/build plan.

Writes `aidlc-docs/construction-plan.md` with suggested steps based on
detected manifests in the `workspace`.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

AGENT_ID = "planner"


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
    plan: List[str] = []

    if "requirements.txt" in manifests or "pyproject.toml" in manifests:
        plan.append("Install Python dependencies (pip install -r requirements.txt or poetry install)")
    if "package.json" in manifests:
        plan.append("Install Node dependencies (npm ci or pnpm install)")
    if "go.mod" in manifests:
        plan.append("Run `go mod download` and `go build` as appropriate")
    if "pom.xml" in manifests:
        plan.append("Run Maven build (mvn -B package)")

    if not manifests:
        plan.append("No dependency manifests detected — run language detection and request instructions")

    plan.append("Run unit tests (pytest, npm test, go test, etc.)")
    plan.append("Run static analysis and linters")
    plan.append("Build artifacts and run smoke tests")

    out = docs / "construction-plan.md"
    lines: List[str] = ["# Construction Plan\n\n", f"Workspace: {workspace}\n\n", "## Detected manifests\n\n"]
    if manifests:
        for m in manifests:
            lines.append(f"- {m}\n")
    else:
        lines.append("None\n")

    lines.append("\n## Proposed steps\n\n")
    for s in plan:
        lines.append(f"- {s}\n")

    try:
        out.write_text("".join(lines), encoding="utf-8")
    except Exception as e:
        return {"agent_id": AGENT_ID, "status": "error", "error": str(e)}

    # AutoSkills awareness: include a short summary when provided in context
    autoskills = ctx.get("autoskills") if isinstance(ctx, dict) else None
    autosummary = None
    if autoskills:
        try:
            autos_dir = autoskills.get("autoskills_dir")
            skills = []
            if autos_dir:
                from pathlib import Path as _P

                p = _P(autos_dir)
                # If path doesn't exist (relative paths), try resolving against
                # the provided run_folder or the repository root.
                if not p.exists():
                    rf = ctx.get("run_folder") if isinstance(ctx, dict) else None
                    if rf:
                        cand = _P(rf) / autos_dir
                        if cand.exists():
                            p = cand
                if not p.exists():
                    # Fallback to repo root relative
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

    # --- Memory: emit learnings for write-back by the manager ---
    memory_observations: List[Dict] = []
    if plan:
        memory_observations.append({
            "content": f"Construction plan for {workspace.name}: {'; '.join(plan[:5])}",
            "tags": ["plan", "construction", workspace.name],
            "memory_type": "semantic",
        })
    if manifests:
        memory_observations.append({
            "content": f"Detected manifests at {workspace.name}: {', '.join(manifests)}",
            "tags": ["manifests", "dependencies", workspace.name],
            "memory_type": "semantic",
        })

    return {"agent_id": AGENT_ID, "status": "ok", "plan_path": str(out), "plan": plan, "autoskills": autosummary, "memory_observations": memory_observations}


if __name__ == "__main__":
    import sys

    ctx = {}
    if len(sys.argv) > 1:
        try:
            ctx = json.loads(sys.argv[1])
        except Exception:
            ctx = {"raw": sys.argv[1]}
    print(json.dumps(run(ctx), ensure_ascii=False, indent=2))
