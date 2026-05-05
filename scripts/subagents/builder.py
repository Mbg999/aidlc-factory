#!/usr/bin/env python3
"""Construction Builder subagent — suggests build commands and optional non-destructive checks.

Writes `aidlc-docs/build-report.md`. By default this agent only *suggests*
commands; it will run anything only if `context['run_build']` is truthy.
Scans recursively so manifests inside sub-project directories are detected.
"""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

AGENT_ID = "builder"

_SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__", ".git", "dist", "build", ".tox", ".mypy_cache", ".eggs"}
_MANIFEST_FILES = {"requirements.txt", "pyproject.toml", "package.json", "go.mod", "pom.xml", "Cargo.toml", "Gemfile", "build.gradle"}


def _detect_manifests(ws: Path) -> Dict[Path, List[str]]:
    """Recursively find manifest files grouped by directory. Skips noise dirs."""
    found: Dict[Path, List[str]] = {}
    for path in sorted(ws.rglob("*")):
        if any(part in _SKIP_DIRS for part in path.relative_to(ws).parts):
            continue
        if path.is_file() and path.name in _MANIFEST_FILES:
            found.setdefault(path.parent, []).append(path.name)
    return found


def _commands_for_dir(ws: Path, abs_dir: Path, manifests: List[str]) -> List[Tuple[str, str]]:
    """Return (description, command) pairs for one sub-project directory."""
    try:
        rel = abs_dir.relative_to(ws)
        prefix = f"cd {rel} && " if str(rel) != "." else ""
        label = str(rel) if str(rel) != "." else "(root)"
    except ValueError:
        prefix = ""
        label = str(abs_dir)

    cmds: List[Tuple[str, str]] = []

    if "requirements.txt" in manifests:
        cmds.append(("Install Python deps", f"{prefix}pip install -r requirements.txt"))
    if "pyproject.toml" in manifests and "requirements.txt" not in manifests:
        cmds.append(("Install Python deps", f"{prefix}pip install -e '.[dev]'  # or: poetry install / uv sync"))
    if "package.json" in manifests:
        cmds.append(("Install Node deps", f"{prefix}npm ci"))
    if "go.mod" in manifests:
        cmds.append(("Build Go", f"{prefix}go build ./..."))
    if "pom.xml" in manifests:
        cmds.append(("Maven build", f"{prefix}mvn -B package -DskipTests"))
    if "Cargo.toml" in manifests:
        cmds.append(("Cargo build", f"{prefix}cargo build"))
    if "Gemfile" in manifests:
        cmds.append(("Bundle install", f"{prefix}bundle install"))
    if "build.gradle" in manifests:
        cmds.append(("Gradle build", f"{prefix}./gradlew build -x test"))

    # Test
    if "requirements.txt" in manifests or "pyproject.toml" in manifests:
        cmds.append(("Run tests", f"{prefix}pytest"))
    if "package.json" in manifests:
        cmds.append(("Run tests", f"{prefix}npm test"))
    if "go.mod" in manifests:
        cmds.append(("Run tests", f"{prefix}go test ./..."))
    if "pom.xml" in manifests:
        cmds.append(("Run tests", f"{prefix}mvn -B test"))
    if "Cargo.toml" in manifests:
        cmds.append(("Run tests", f"{prefix}cargo test"))

    return [(f"[{label}] {desc}", cmd) for desc, cmd in cmds]


def run(context: Dict | None = None) -> Dict:
    ctx = context or {}
    workspace = Path(ctx.get("workspace") or ctx.get("path") or ".")
    if not workspace.is_absolute():
        workspace = (Path(__file__).resolve().parents[2] / workspace).resolve()

    docs = Path(ctx.get("aidlc_docs") or workspace.parent / "aidlc-docs")
    docs.mkdir(parents=True, exist_ok=True)

    manifests_by_dir = _detect_manifests(workspace)

    all_cmds: List[Tuple[str, str]] = []
    for abs_dir, dir_manifests in sorted(manifests_by_dir.items()):
        all_cmds.extend(_commands_for_dir(workspace, abs_dir, dir_manifests))

    if not manifests_by_dir:
        all_cmds.append(("No manifests found", "# No dependency manifests detected — inspect workspace manually"))

    suggested: List[str] = [cmd for _, cmd in all_cmds]

    ran: Dict[str, Dict] = {}
    if ctx.get("run_build"):
        for tool in ("python3", "node", "go", "mvn", "npm", "cargo", "ruff", "flake8"):
            ran[tool] = {"available": bool(shutil.which(tool))}

    out = docs / "build-report.md"
    lines: List[str] = ["# Build Report\n\n", f"Workspace: {workspace}\n\n"]

    lines.append("## Detected manifests\n\n")
    if manifests_by_dir:
        for abs_dir, dir_manifests in sorted(manifests_by_dir.items()):
            try:
                rel = abs_dir.relative_to(workspace)
                label = str(rel) if str(rel) != "." else "(root)"
            except ValueError:
                label = str(abs_dir)
            lines.append(f"- `{label}`: {', '.join(sorted(dir_manifests))}\n")
    else:
        lines.append("None\n")

    lines.append("\n## Suggested commands\n\n")
    for desc, cmd in all_cmds:
        lines.append(f"### {desc}\n\n```bash\n{cmd}\n```\n\n")

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

    # --- Memory: emit learnings for write-back by the manager ---
    all_manifest_names = sorted({m for ms in manifests_by_dir.values() for m in ms})
    memory_observations: List[Dict] = []
    if manifests_by_dir:
        memory_observations.append({
            "content": f"Project at {workspace.name} uses: {', '.join(all_manifest_names)} in {len(manifests_by_dir)} director(y/ies)",
            "tags": ["build", "dependencies", workspace.name],
            "memory_type": "semantic",
        })
    if suggested:
        memory_observations.append({
            "content": f"Build commands for {workspace.name}: {'; '.join(suggested[:5])}",
            "tags": ["build", "commands", workspace.name],
            "memory_type": "semantic",
        })

    return {"agent_id": AGENT_ID, "status": "ok", "report_path": str(out), "suggested": suggested, "env_checks": ran, "autoskills": autosummary, "memory_observations": memory_observations}


if __name__ == "__main__":
    import sys

    ctx = {}
    if len(sys.argv) > 1:
        try:
            ctx = json.loads(sys.argv[1])
        except Exception:
            ctx = {"raw": sys.argv[1]}
    print(json.dumps(run(ctx), ensure_ascii=False, indent=2))
