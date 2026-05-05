#!/usr/bin/env python3
"""Construction Planner subagent — generates a construction/build plan.

Writes `aidlc-docs/construction-plan.md` with suggested steps based on
detected manifests in the `workspace`. Scans recursively so manifests
inside sub-project directories (e.g. /root/original-project/package.json)
are found and generate concrete, path-specific commands.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Tuple

AGENT_ID = "planner"

_SKIP_DIRS = {"node_modules", ".venv", "venv", "__pycache__", ".git", "dist", "build", ".tox", ".mypy_cache", ".eggs"}
_MANIFEST_FILES = {"requirements.txt", "pyproject.toml", "package.json", "go.mod", "pom.xml", "Cargo.toml", "Gemfile", "build.gradle"}


def _detect_manifests(ws: Path) -> Dict[Path, List[str]]:
    """Recursively find manifest files, grouped by their parent directory.

    Returns a dict mapping absolute directory Path → list of manifest filenames
    found in that directory. Skips common noise directories.
    """
    found: Dict[Path, List[str]] = {}
    for path in sorted(ws.rglob("*")):
        if any(part in _SKIP_DIRS for part in path.relative_to(ws).parts):
            continue
        if path.is_file() and path.name in _MANIFEST_FILES:
            found.setdefault(path.parent, []).append(path.name)
    return found


def _steps_for_dir(ws: Path, abs_dir: Path, manifests: List[str]) -> List[Tuple[str, str]]:
    """Return concrete (description, command) pairs for a directory's manifests.

    Commands use 'cd <rel>' prefix when the manifest is not at workspace root.
    """
    try:
        rel = abs_dir.relative_to(ws)
        prefix = f"cd {rel} && " if str(rel) != "." else ""
        dir_label = str(rel) if str(rel) != "." else "(root)"
    except ValueError:
        prefix = ""
        dir_label = str(abs_dir)

    steps: List[Tuple[str, str]] = []

    # Install
    if "requirements.txt" in manifests:
        steps.append(("Install Python deps", f"{prefix}pip install -r requirements.txt"))
    if "pyproject.toml" in manifests:
        # prefer uv/poetry if requirements.txt is absent to avoid double-install
        if "requirements.txt" not in manifests:
            steps.append(("Install Python deps (pyproject)", f"{prefix}pip install -e '.[dev]'  # or: poetry install / uv sync"))
    if "package.json" in manifests:
        steps.append(("Install Node deps", f"{prefix}npm ci"))
    if "go.mod" in manifests:
        steps.append(("Download Go modules", f"{prefix}go mod download"))
        steps.append(("Build Go project", f"{prefix}go build ./..."))
    if "pom.xml" in manifests:
        steps.append(("Maven build", f"{prefix}mvn -B package -DskipTests"))
    if "Cargo.toml" in manifests:
        steps.append(("Cargo build", f"{prefix}cargo build"))
    if "Gemfile" in manifests:
        steps.append(("Bundle install", f"{prefix}bundle install"))
    if "build.gradle" in manifests:
        steps.append(("Gradle build", f"{prefix}./gradlew build -x test"))

    # Test
    if "requirements.txt" in manifests or "pyproject.toml" in manifests:
        steps.append(("Run Python tests", f"{prefix}pytest"))
    if "package.json" in manifests:
        steps.append(("Run Node tests", f"{prefix}npm test"))
    if "go.mod" in manifests:
        steps.append(("Run Go tests", f"{prefix}go test ./..."))
    if "pom.xml" in manifests:
        steps.append(("Run Maven tests", f"{prefix}mvn -B test"))
    if "Cargo.toml" in manifests:
        steps.append(("Run Cargo tests", f"{prefix}cargo test"))

    # Lint
    if "requirements.txt" in manifests or "pyproject.toml" in manifests:
        steps.append(("Lint Python", f"{prefix}ruff check .  # or: flake8 ."))
    if "package.json" in manifests:
        steps.append(("Lint JS/TS", f"{prefix}npx eslint ."))
    if "go.mod" in manifests:
        steps.append(("Lint Go", f"{prefix}go vet ./..."))

    return [(f"[{dir_label}] {desc}", cmd) for desc, cmd in steps]


def run(context: Dict | None = None) -> Dict:
    ctx = context or {}
    workspace = Path(ctx.get("workspace") or ctx.get("path") or ".")
    if not workspace.is_absolute():
        workspace = (Path(__file__).resolve().parents[2] / workspace).resolve()

    docs = Path(ctx.get("aidlc_docs") or workspace.parent / "aidlc-docs")
    docs.mkdir(parents=True, exist_ok=True)

    manifests_by_dir = _detect_manifests(workspace)

    # Build per-directory step lists
    all_steps: List[Tuple[str, str]] = []  # (description, command)
    for abs_dir, dir_manifests in sorted(manifests_by_dir.items()):
        all_steps.extend(_steps_for_dir(workspace, abs_dir, dir_manifests))

    if not manifests_by_dir:
        all_steps.append(("No manifests detected", "# No dependency manifests found — inspect the workspace and run setup manually"))

    # Flatten plan for backward-compat return value
    plan: List[str] = [cmd for _, cmd in all_steps]

    # Build report lines
    out = docs / "construction-plan.md"
    lines: List[str] = ["# Construction Plan\n\n", f"Workspace: {workspace}\n\n"]

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

    lines.append("\n## Proposed steps\n\n")
    for desc, cmd in all_steps:
        lines.append(f"### {desc}\n\n```bash\n{cmd}\n```\n\n")

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
    all_manifest_names = sorted({m for ms in manifests_by_dir.values() for m in ms})
    memory_observations: List[Dict] = []
    if plan:
        memory_observations.append({
            "content": f"Construction plan for {workspace.name}: {'; '.join(plan[:5])}",
            "tags": ["plan", "construction", workspace.name],
            "memory_type": "semantic",
        })
    if manifests_by_dir:
        memory_observations.append({
            "content": f"Detected manifests at {workspace.name}: {', '.join(all_manifest_names)} in {len(manifests_by_dir)} director(y/ies)",
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
