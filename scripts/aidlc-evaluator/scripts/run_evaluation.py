#!/usr/bin/env python3
"""Full evaluation suite — run AIDLC workflow, then score the outputs.

This is the controlling script for the AIDLC evaluation framework. It
orchestrates six stages:

  1. EXECUTION    — Run the AIDLC two-agent workflow (packages/execution)
                    to produce aidlc-docs + workspace code from a vision doc.
  2. POST-RUN     — Automatically install deps and run generated tests
                    (handled inside the execution stage).
  3. QUANTITATIVE — Lint and security scan the generated code
                    (packages/quantitative).
  4. CONTRACT     — Spin up the generated app and validate endpoints
                    against an API spec (packages/contracttest).
  5. QUALITATIVE  — Compare the produced aidlc-docs against a golden
                    reference using Bedrock for semantic similarity scoring.
  6. REPORT       — Generate a consolidated Markdown + HTML report
                    aggregating all evaluation data (packages/reporting).

Usage:

  # Full pipeline: execute AIDLC workflow + semantic evaluation
  python run_evaluation.py \
      --vision test_cases/sci-calc/vision.md \
      --tech-env test_cases/sci-calc/tech-env.md \
      --golden test_cases/sci-calc/golden-aidlc-docs

  # Evaluate an existing run (skip execution, just score)
  python run_evaluation.py \
      --evaluate-only runs/20260213T202730-.../aidlc-docs \
      --golden test_cases/sci-calc/golden-aidlc-docs

  # Run unit tests for all packages
  python run_evaluation.py --test
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
import runpy

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
PACKAGES = REPO_ROOT / "packages"
TEST_CASES_DIR = REPO_ROOT / "test_cases"

# Add shared package to path
sys.path.insert(0, str(PACKAGES / "shared" / "src"))
from shared.io import atomic_yaml_dump  # noqa: E402
from shared.scenario import resolve_scenario  # noqa: E402


# ── helpers ──────────────────────────────────────────────────────────────────

def _read_test_status(test_results_path: Path) -> dict | None:
    """Read test-results.yaml and return a normalized status dict, or None."""
    if not test_results_path.exists():
        return None

    with open(test_results_path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}

    status = data.get("status", "unknown")
    install_ok = data.get("install", {}).get("success", False)
    test_ok = data.get("test", {}).get("success", False)
    parsed = data.get("test", {}).get("parsed_results", {})
    passed = parsed.get("passed")
    failed = parsed.get("failed")
    errors = parsed.get("errors")
    total = parsed.get("total")

    if status == "install_failed":
        summary = f"install failed — {data.get('install', {}).get('output', '')[:120]}"
        tests_passed = False
    elif not test_ok:
        if total is not None:
            summary = f"{passed or 0} passed, {failed or 0} failed, {errors or 0} errors (of {total})"
        else:
            summary = f"tests failed — {data.get('test', {}).get('output', '')[:120]}"
        tests_passed = False
    else:
        summary = f"{passed or 0} passed, {failed or 0} failed (of {total})"
        tests_passed = (failed or 0) == 0 and (errors or 0) == 0

    return {
        "tests_passed": tests_passed,
        "install_ok": install_ok,
        "test_ok": test_ok,
        "summary": summary,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "total": total,
        "raw_status": status,
    }


def _print_test_summary(test_status: dict | None) -> None:
    """Print a clear post-run test summary."""
    print(f"\n{'=' * 60}")
    print("  Stage 2: Post-Run Test Results")
    print(f"{'=' * 60}\n")
    if test_status is None:
        print("  No testable project detected — skipped.")
        return
    if test_status["tests_passed"]:
        print(f"  PASS  {test_status['summary']}")
    else:
        print(f"  FAIL  {test_status['summary']}")
        if not test_status["install_ok"]:
            print("        (dependency install failed — tests could not run)")


def _run_cmd(cmd: list[str], label: str, **kwargs) -> subprocess.CompletedProcess:
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}\n")
    # nosec B603 - Executing trusted framework evaluation packages with validated args
    # nosemgrep: dangerous-subprocess-use-audit
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        print(f"\n[FAILED] {label} (exit code {result.returncode})", file=sys.stderr)
    return result


def _get_repo_info() -> dict:
    """Get git info for the aidlc-regression repository."""
    # nosec B603, B607 - Static git commands for repo metadata collection
    # nosemgrep: dangerous-subprocess-use-audit
    info: dict = {}
    try:
        info["commit"] = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True, cwd=REPO_ROOT,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        info["commit"] = None

    try:
        info["branch"] = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, check=True, cwd=REPO_ROOT,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        info["branch"] = None

    try:
        porcelain = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, check=True, cwd=REPO_ROOT,
        ).stdout.strip()
        info["dirty"] = bool(porcelain)
    except (subprocess.CalledProcessError, FileNotFoundError):
        info["dirty"] = None

    return info


def _save_evaluation_config(
    run_folder: Path,
    args: argparse.Namespace,
    cfg_data: dict,
) -> None:
    """Write aidlc-regression repo info and full resolved configuration to the run folder.

    Creates evaluation-config.yaml with the full config dump, and also
    updates run-meta.yaml with evaluation-level fields (scorer model,
    golden/openapi paths, git commit, etc.).
    """
    repo_info = _get_repo_info()

    def _rel(p: Path | None) -> str | None:
        if p is None:
            return None
        try:
            return str(p.resolve().relative_to(Path.cwd().resolve()))
        except ValueError:
            return str(p)

    eval_config: dict = {
        "saved_at": datetime.now(timezone.utc).isoformat(),
        "aidlc_regression_repo": repo_info,
        "config_file": _rel(args.config),
        "resolved_config": cfg_data,
        "cli_args": {
            "vision": _rel(args.vision),
            "tech_env": _rel(args.tech_env),
            "golden": _rel(args.golden),
            "openapi": _rel(args.openapi),
            "evaluate_only": _rel(args.evaluate_only),
            "profile": args.profile,
            "region": args.region,
            "scorer_model": args.scorer_model,
            "executor_model": args.executor_model,
            "rules_ref": args.rules_ref,
            "output_dir": _rel(args.output_dir),
            "sandbox": args.sandbox,
            "report_format": args.report_format,
        },
    }

    atomic_yaml_dump(eval_config, run_folder / "evaluation-config.yaml")

    # Also update run-meta.yaml with evaluation-level fields
    meta_path = run_folder / "run-meta.yaml"
    if meta_path.exists():
        with open(meta_path, encoding="utf-8") as f:
            meta = yaml.safe_load(f) or {}
    else:
        meta = {}

    meta["aidlc_regression_commit"] = repo_info.get("commit")
    meta["aidlc_regression_branch"] = repo_info.get("branch")
    meta["aidlc_regression_dirty"] = repo_info.get("dirty")
    meta.setdefault("config", {})["scorer_model"] = args.scorer_model
    meta["golden_dir"] = _rel(args.golden)
    meta["openapi_spec"] = _rel(args.openapi)
    meta["baseline"] = _rel(args.baseline)

    atomic_yaml_dump(meta, meta_path)


_SENTINEL_NAME = ".last_run_folder"


def _read_run_sentinel(output_dir: Path) -> Path | None:
    """Read the sentinel file written by create_run_folder().

    Returns the run folder path if the sentinel exists and the directory
    is valid, otherwise None.  The sentinel is removed after reading so
    it does not confuse subsequent runs.
    """
    sentinel = output_dir / _SENTINEL_NAME
    if not sentinel.is_file():
        return None
    try:
        run_folder = Path(sentinel.read_text(encoding="utf-8").strip())
        sentinel.unlink(missing_ok=True)
        if run_folder.is_dir():
            return run_folder
    except OSError:
        pass
    return None


def _list_run_folders(output_dir: Path | None = None) -> set[Path]:
    """Return the current set of run folders under runs/.

    Args:
        output_dir: Directory to search for run folders. Defaults to REPO_ROOT / "runs".
    """
    runs_dir = output_dir if output_dir else REPO_ROOT / "runs"
    if not runs_dir.is_dir():
        return set()
    return {d for d in runs_dir.iterdir() if d.is_dir() and not d.name.startswith(".")}


def _find_new_run(before: set[Path], output_dir: Path | None = None) -> Path | None:
    """Find the single new run folder created since *before* was captured.

    Falls back to the newest folder if multiple appeared (shouldn't happen
    in normal single-run usage).

    Args:
        before: Set of run folders that existed before execution.
        output_dir: Directory to search for new run folders. Defaults to REPO_ROOT / "runs".

    .. deprecated::
        Prefer :func:`_read_run_sentinel` which avoids the TOCTOU race
        condition inherent in before/after directory listing.
    """
    after = _list_run_folders(output_dir)
    new = sorted(after - before, reverse=True)
    return new[0] if new else None


def _find_latest_run(scenario_name: str | None = None) -> Path | None:
    """Find the most recent timestamped run folder under runs/.

    Only matches directories whose names start with a digit (YYYYMMDD...),
    skipping model-named directories (e.g., nova-pro/, sonnet-4-5/) that
    the batch runner creates.

    If *scenario_name* is given, searches under ``runs/<scenario_name>/``
    instead of ``runs/``.
    """
    runs_dir = REPO_ROOT / "runs"
    if scenario_name:
        runs_dir = runs_dir / scenario_name
    if not runs_dir.is_dir():
        return None
    folders = sorted(
        (d for d in runs_dir.iterdir()
         if d.is_dir() and not d.name.startswith(".") and d.name[0:1].isdigit()),
        reverse=True,
    )
    return folders[0] if folders else None


# ── stages ───────────────────────────────────────────────────────────────────

def stage_execute(args: argparse.Namespace) -> Path | None:
    """Stage 1: Run the AIDLC workflow via packages/execution.

    Returns the run folder even if the runner exits non-zero, as long as
    aidlc-docs were produced (the swarm may fail on a late handoff after
    all documents are already written).
    """
    cmd = [
        sys.executable, "-m", "aidlc_runner",
        "--vision", str(args.vision),
        "--config", str(args.config),
    ]
    if args.tech_env:
        cmd += ["--tech-env", str(args.tech_env)]
    if args.profile:
        cmd += ["--aws-profile", args.profile]
    if args.region:
        cmd += ["--aws-region", args.region]
    if args.executor_model:
        cmd += ["--executor-model", args.executor_model]
    if args.rules_ref:
        cmd += ["--rules-ref", args.rules_ref]
    # Route output under runs/<scenario>/ by default
    output_dir = args.output_dir
    if not output_dir and hasattr(args, "_scenario_name"):
        output_dir = REPO_ROOT / "runs" / args._scenario_name
    if output_dir:
        cmd += ["--output-dir", str(output_dir)]

    env_pythonpath = os.pathsep.join([
        str(PACKAGES / "execution" / "src"),
        str(PACKAGES / "shared" / "src"),
    ])
    env = {**os.environ, "PYTHONPATH": env_pythonpath}

    # Determine the output directory so we can read the sentinel file after.
    effective_output_dir = output_dir or (REPO_ROOT / "runs")

    # Snapshot for the legacy fallback (in case the runner doesn't write
    # the sentinel, e.g. older runner versions).
    existing_runs = _list_run_folders(output_dir)

    result = _run_cmd(cmd, "Stage 1: AIDLC Workflow Execution", env=env)

    # Prefer the sentinel file written by create_run_folder() — it avoids
    # the TOCTOU race inherent in before/after directory listing.
    run_folder = _read_run_sentinel(effective_output_dir)
    if run_folder is None:
        # Fall back to directory-diff for backwards compatibility.
        run_folder = _find_new_run(existing_runs, output_dir)
    if run_folder is None:
        return None

    docs_dir = run_folder / "aidlc-docs"
    doc_files = list(docs_dir.rglob("*.md")) if docs_dir.is_dir() else []
    real_docs = [f for f in doc_files if f.name not in ("aidlc-state.md", "audit.md")]

    if result.returncode != 0:
        if real_docs:
            print(
                f"\n[WARN] Execution exited non-zero but {len(real_docs)} "
                f"aidlc-doc(s) were produced — continuing evaluation.",
                file=sys.stderr,
            )
        else:
            print(
                "\n[ABORT] Execution failed and no aidlc-docs were produced.",
                file=sys.stderr,
            )
            return None

    return run_folder


def run_subagents_for_phases(run_folder: Path, phases: list[str]) -> dict:
    """Run enabled subagents whose `enforce_in_phases` intersects *phases*.

    This helper loads `scripts/subagents/manager.py` from the repository root
    and invokes `run(agent_id, context)` for each matching agent. Results are
    returned as a mapping of agent_id -> result dict (or error info).
    """
    results: dict = {}
    try:
        # Project root is two levels above this script's REPO_ROOT
        project_root = REPO_ROOT.parent.parent
        manager_path = project_root / "scripts" / "subagents" / "manager.py"
        if not manager_path.exists():
            print(f"Subagent manager not found: {manager_path}")
            return results

        mgr = runpy.run_path(str(manager_path))
        load_agents = mgr.get("load_agents")
        run_agent = mgr.get("run")
        if not load_agents or not run_agent:
            print("Subagent manager missing required functions (load_agents/run)")
            return results

        agents = load_agents()
        context = {
            "run_folder": str(run_folder),
            "workspace": str(run_folder / "workspace"),
            "path": str(run_folder / "workspace"),
            "aidlc_docs": str(run_folder / "aidlc-docs"),
        }

        # AutoSkills integration: detect any AutoSkills artifacts produced
        # during reverse-engineering (skills-lock.json or .agents/skills/) and
        # include them in the context passed to subagents. Subagents can
        # consult `context['autoskills']` to adapt behavior or apply skills.
        try:
            workspace_dir = Path(context["workspace"])
            skills_lock = workspace_dir / "skills-lock.json"
            autoskills_dir = workspace_dir / ".agents" / "skills"
            if skills_lock.exists():
                import json as _json
                with open(skills_lock, encoding="utf-8") as f:
                    skills_lock_data = _json.load(f)
                context["autoskills"] = {
                    "skills_lock_path": str(skills_lock),
                    "skills_lock": skills_lock_data,
                    "autoskills_dir": str(autoskills_dir) if autoskills_dir.exists() else None,
                }
            elif autoskills_dir.exists():
                context["autoskills"] = {
                    "skills_lock_path": None,
                    "skills_lock": None,
                    "autoskills_dir": str(autoskills_dir),
                }
            else:
                context["autoskills"] = {"skills_lock_path": None, "skills_lock": None, "autoskills_dir": None}
        except Exception as e:  # pragma: no cover - best-effort detection
            print(f"[WARN] Failed to detect AutoSkills artifacts: {e}", file=sys.stderr)
            context.setdefault("autoskills", {"skills_lock_path": None, "skills_lock": None, "autoskills_dir": None})
        # Run matching agents concurrently with a configurable concurrency limit
        to_run = [a for a in agents if any(p in (a.get("enforce_in_phases") or []) for p in phases)]
        if to_run:
            import concurrent.futures
            concurrency = int(os.environ.get("AIDLC_SUBAGENT_CONCURRENCY", "4"))
            max_workers = min(len(to_run), max(1, concurrency))
            futures: dict = {}
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as ex:
                for a in to_run:
                    agent_id = a.get("id")
                    # Agent may declare a timeout in its metadata
                    agent_timeout = a.get("timeout") or 120
                    futures[ex.submit(run_agent, agent_id, context, None, agent_timeout)] = agent_id

                for fut in concurrent.futures.as_completed(futures):
                    aid = futures[fut]
                    try:
                        res = fut.result()
                        results[aid] = {"ok": True, "result": res}
                    except Exception as e:  # pragma: no cover - best-effort
                        results[aid] = {"ok": False, "error": str(e)}
                        print(f"[SUBAGENT ERROR] {aid}: {e}", file=sys.stderr)

    except Exception as e:  # pragma: no cover - protect evaluation runner
        print(f"Error running subagents: {e}", file=sys.stderr)

    return results


def generate_autoskills_recommendations(run_folder: Path, subagent_results: dict) -> Path | None:
    """Generate a human-friendly Markdown summary of AutoSkills recommendations.

    Writes `aidlc-docs/autoskills-recommendations.md` inside the run folder
    when the `midudev-autoskills` subagent produced recommendations.
    Returns the path to the written file, or None if nothing was written.
    """
    try:
        autos = subagent_results.get("midudev-autoskills")
        if not autos:
            return None

        docs_dir = run_folder / "aidlc-docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        out_path = docs_dir / "autoskills-recommendations.md"

        if not autos.get("ok"):
            content = [
                "# AutoSkills — Recommendations\n\n",
                "AutoSkills subagent failed to run during reverse-engineering.\n\n",
                f"Error: {autos.get('error')}\n",
            ]
            out_path.write_text("".join(content), encoding="utf-8")
            return out_path

        res = autos.get("result", {})
        recommendations = res.get("recommendations", []) or []
        exit_code = res.get("autoskills_exit_code")

        lines: list[str] = []
        lines.append("# AutoSkills — Recommendations\n\n")
        lines.append("AutoSkills scanned the project during Reverse Engineering and produced the following proposed skills.\n\n")

        if not recommendations:
            lines.append("No recommended skills were detected.\n")
        else:
            lines.append("## Proposed skills\n\n")
            for i, r in enumerate(recommendations, start=1):
                lines.append(f"{i}. {r}\n")
            lines.append("\n")
            lines.append("## Next steps\n\n")
            lines.append("- Review the proposed skills and rationale above.\n")
            lines.append("- If you approve installation, run the install command below (requires Node.js >= 22 and npx).\n\n")
            lines.append("```bash\n")
            lines.append(
                f"python3 scripts/subagents/manager.py midudev-autoskills '{{\"path\": \"{str(run_folder / 'workspace')}\", \"install\": true}}'\n"
            )
            lines.append("```\n\n")
            lines.append("**Security note:** Before installing, validate any files that would be written by AutoSkills using the content validation guidance (see `aidlc-rules/aws-aidlc-rule-details/common/content-validation.md`) and record results in `aidlc-docs/audit.md`.\n\n")
            lines.append("Approval options: Request Changes (edit this file and note concerns) or Approve and Install (run the install command above).\n")

        lines.append(f"\n_AutoSkills exit code: {exit_code}_\n")

        out_path.write_text("".join(lines), encoding="utf-8")
        return out_path

    except Exception as e:  # pragma: no cover - best-effort reporting
        print(f"Error writing autoskills recommendations: {e}", file=sys.stderr)
        return None


def auto_install_autoskills(run_folder: Path) -> dict:
    """Run the `midudev-autoskills` subagent with `install=true` and return the result dict.

    Returns a dict with keys `ok` and either `result` (on success) or `error` (on failure).
    """
    try:
        project_root = REPO_ROOT.parent.parent
        manager_path = project_root / "scripts" / "subagents" / "manager.py"
        if not manager_path.exists():
            return {"ok": False, "error": f"Subagent manager not found: {manager_path}"}

        mgr = runpy.run_path(str(manager_path))
        run_agent = mgr.get("run")
        if not run_agent:
            return {"ok": False, "error": "Subagent manager missing required run()"}

        ctx = {
            "path": str(run_folder / "workspace"),
            "run_folder": str(run_folder),
            "workspace": str(run_folder / "workspace"),
            "aidlc_docs": str(run_folder / "aidlc-docs"),
            "install": True,
        }
        res = run_agent("midudev-autoskills", ctx)
        return {"ok": True, "result": res}
    except Exception as e:  # pragma: no cover - best-effort
        return {"ok": False, "error": str(e)}


def apply_autoskills(run_folder: Path) -> dict:
    """Attempt to apply installed AutoSkills by executing well-known
    entry scripts inside each skill directory under `.agents/skills/`.

    This is opt-in and should be used only when the installation has been
    audited. The function returns a mapping skill_name -> result dict.
    """
    results: dict = {}
    try:
        workspace = run_folder / "workspace"
        skills_base = workspace / ".agents" / "skills"
        if not skills_base.exists() or not skills_base.is_dir():
            return {"ok": False, "error": "skills directory not found", "path": str(skills_base)}

        for skill_dir in sorted([p for p in skills_base.iterdir() if p.is_dir()]):
            name = skill_dir.name
            results[name] = {"ok": False, "tried": [], "error": None}
            # Candidate entrypoints (checked in order)
            cand = ["apply.py", "install.py", "entrypoint.py", "run.py", "main.py", "apply.sh", "install.sh"]
            found = None
            for c in cand:
                p = skill_dir / c
                if p.exists():
                    found = p
                    break
            if not found:
                results[name]["error"] = "no apply script found"
                continue

            results[name]["tried"].append(str(found.relative_to(workspace)))
            try:
                if found.suffix == ".py":
                    cmd = [sys.executable, str(found)]
                else:
                    # Shell script
                    cmd = ["bash", str(found)]

                proc = subprocess.run(cmd, cwd=str(skill_dir), capture_output=True, text=True, timeout=300)
                results[name]["exit_code"] = proc.returncode
                results[name]["stdout"] = (proc.stdout or "")[:20000]
                results[name]["stderr"] = (proc.stderr or "")[:20000]
                results[name]["ok"] = proc.returncode == 0
            except Exception as e:  # pragma: no cover - best-effort
                results[name]["error"] = str(e)

        return {"ok": True, "results": results}
    except Exception as e:  # pragma: no cover - best-effort
        return {"ok": False, "error": str(e)}


def generate_autoskills_installation_report(run_folder: Path, install_result: dict) -> Path | None:
    """Generate a Markdown installation report summarizing AutoSkills installation.

    Writes `aidlc-docs/autoskills-installation.md` and returns its path, or None on error.
    """
    try:
        docs_dir = run_folder / "aidlc-docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        out_path = docs_dir / "autoskills-installation.md"

        lines: list[str] = ["# AutoSkills — Installation Report\n\n"]
        ts = datetime.now(timezone.utc).isoformat()

        if not install_result.get("ok"):
            lines.append(f"Installation attempted at {ts} and FAILED.\n\n")
            lines.append(f"Error: {install_result.get('error')}\n")
            out_path.write_text("".join(lines), encoding="utf-8")
            return out_path

        res = install_result.get("result", {})
        exit_code = res.get("autoskills_exit_code")
        stdout = (res.get("autoskills_stdout") or "").strip()
        stderr = (res.get("autoskills_stderr") or "").strip()

        lines.append(f"Installation completed at {ts}. Exit code: {exit_code}\n\n")
        if stdout:
            lines.append("## AutoSkills stdout\n\n```")
            lines.append(stdout[:800])
            lines.append("\n```\n\n")
        if stderr:
            lines.append("## AutoSkills stderr\n\n```")
            lines.append(stderr[:800])
            lines.append("\n```\n\n")

        # Detect created/modified files (best-effort)
        workspace = run_folder / "workspace"
        created: list[str] = []
        skills_lock = workspace / "skills-lock.json"
        autoskills_dir = workspace / ".agents" / "skills"
        if skills_lock.exists():
            created.append(str(skills_lock.relative_to(run_folder)))
        if autoskills_dir.exists():
            for p in sorted(autoskills_dir.rglob("*")):
                if p.is_file():
                    try:
                        created.append(str(p.relative_to(run_folder)))
                    except Exception:
                        created.append(str(p))

        if created:
            lines.append("## Files written/updated by AutoSkills\n\n")
            for c in created:
                lines.append(f"- {c}\n")
        else:
            lines.append("No skill files detected in workspace after installation (check AutoSkills output).\n")

        lines.append("\n**Security note:** Verify all installed skill files per content-validation guidance and record results in `aidlc-docs/audit.md`.\n")

        out_path.write_text("".join(lines), encoding="utf-8")
        return out_path
    except Exception as e:  # pragma: no cover - best-effort
        print(f"Error writing autoskills installation report: {e}", file=sys.stderr)
        return None


def stage_quantitative(workspace: Path, output_path: Path, pmd_path: str | None = None) -> dict | None:
    """Stage 3: Lint and security analysis on generated code."""
    import os

    env_pythonpath = str(PACKAGES / "quantitative" / "src")
    env = {**os.environ, "PYTHONPATH": env_pythonpath}

    cmd = [
        sys.executable, "-m", "quantitative", "analyze",
        str(workspace), "--output", str(output_path),
    ]
    if pmd_path:
        cmd += ["--pmd-path", pmd_path]
    result = _run_cmd(cmd, "Stage 3: Code Quality (Lint & Security)", env=env)

    if result.returncode != 0 or not output_path.exists():
        return None

    with open(output_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _read_quality_status(quality_data: dict | None) -> dict | None:
    """Normalize quality-report.yaml into a summary dict."""
    if quality_data is None:
        return None
    summary = quality_data.get("summary", {})
    lint_total = summary.get("lint_total", 0)
    lint_errors = summary.get("lint_errors", 0)
    sec_total = summary.get("security_total", 0)
    sec_high = summary.get("security_high", 0)

    passed = lint_errors == 0 and sec_high == 0
    parts = []
    if "lint_total" in summary:
        parts.append(f"lint: {lint_total} finding(s), {lint_errors} error(s)")
    if "security_total" in summary:
        parts.append(f"security: {sec_total} finding(s), {sec_high} high")
    text = "; ".join(parts) if parts else "no tools ran"

    return {
        "passed": passed,
        "summary": text,
        "lint_total": lint_total,
        "lint_errors": lint_errors,
        "security_total": sec_total,
        "security_high": sec_high,
    }


def stage_contract(
    workspace: Path,
    spec_path: Path,
    output_path: Path,
    use_sandbox: bool = True,
) -> dict | None:
    """Stage 4: API contract tests — spin up app and validate endpoints."""
    import os

    env_pythonpath = str(PACKAGES / "contracttest" / "src")
    shared_pythonpath = str(PACKAGES / "shared" / "src")
    env = {**os.environ, "PYTHONPATH": f"{env_pythonpath}{os.pathsep}{shared_pythonpath}"}

    cmd = [
        sys.executable, "-m", "contracttest", "run",
        str(workspace), "--openapi", str(spec_path),
        "--output", str(output_path),
    ]
    if use_sandbox:
        cmd.append("--sandbox")
    else:
        cmd.append("--no-sandbox")
    result = _run_cmd(cmd, "Stage 4: API Contract Tests", env=env)

    if not output_path.exists():
        return None

    with open(output_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def _read_contract_status(contract_data: dict | None) -> dict | None:
    """Normalize contract-test-results.yaml into a summary dict."""
    if contract_data is None:
        return None
    total = contract_data.get("total", 0)
    passed = contract_data.get("passed", 0)
    failed = contract_data.get("failed", 0)
    errors = contract_data.get("errors", 0)
    server_ok = contract_data.get("server_started", False)

    if not server_ok:
        summary = f"server failed to start — {contract_data.get('server_error', '?')[:120]}"
        ok = False
    else:
        summary = f"{passed}/{total} passed, {failed} failed, {errors} errors"
        ok = failed == 0 and errors == 0

    return {"passed": ok, "summary": summary, "total": total,
            "test_passed": passed, "test_failed": failed, "test_errors": errors}


def stage_qualitative(
    candidate_docs: Path,
    golden_docs: Path,
    output_path: Path | None,
    profile: str,
    region: str,
    model_id: str,
) -> int:
    """Stage 5: Semantic comparison of aidlc-docs via Bedrock."""
    cmd = [
        sys.executable, "-m", "qualitative", "compare",
        "--reference", str(golden_docs),
        "--candidate", str(candidate_docs),
        "--model-id", model_id,
    ]
    if profile:
        cmd += ["--profile", profile]
    if region:
        cmd += ["--region", region]
    if output_path:
        cmd += ["--output", str(output_path)]

    env_pythonpath = str(PACKAGES / "qualitative" / "src")
    import os
    env = {**os.environ, "PYTHONPATH": env_pythonpath}

    result = _run_cmd(cmd, "Stage 5: Qualitative (Semantic) Evaluation via Bedrock", env=env)
    return result.returncode


def stage_report(run_folder: Path, report_format: str, baseline: Path | None = None) -> None:
    """Stage 6: Generate consolidated Markdown + HTML report."""
    import os

    env_pythonpath = str(PACKAGES / "reporting" / "src")
    env = {**os.environ, "PYTHONPATH": env_pythonpath}

    cmd = [
        sys.executable, "-m", "reporting", "generate",
        str(run_folder), "--format", report_format,
    ]
    if baseline and baseline.is_file():
        cmd += ["--baseline", str(baseline)]
    _run_cmd(cmd, "Stage 6: Consolidated Report", env=env)


def stage_test() -> int:
    """Run unit tests for all packages."""
    import os

    pythonpath_parts = [
        str(PACKAGES / "execution" / "src"),
        str(PACKAGES / "qualitative" / "src"),
        str(PACKAGES / "quantitative" / "src"),
        str(PACKAGES / "contracttest" / "src"),
        str(PACKAGES / "reporting" / "src"),
        str(PACKAGES / "shared" / "src"),
        str(PACKAGES / "cli-harness" / "src"),
        str(PACKAGES / "ide-harness" / "src"),
    ]
    pythonpath = os.pathsep.join(pythonpath_parts)
    env = {**os.environ, "PYTHONPATH": pythonpath}

    test_dirs = [
        str(PACKAGES / "execution" / "tests"),
        str(PACKAGES / "qualitative" / "tests"),
        str(PACKAGES / "quantitative" / "tests"),
        str(PACKAGES / "contracttest" / "tests"),
        str(PACKAGES / "reporting" / "tests"),
        str(PACKAGES / "cli-harness" / "tests"),
        str(PACKAGES / "ide-harness" / "tests"),
    ]
    cmd = [sys.executable, "-m", "pytest"] + test_dirs + ["-v", "--import-mode=importlib"]

    result = _run_cmd(cmd, "Unit Tests: All Packages", env=env)
    return result.returncode


# ── CLI ──────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_evaluation",
        description="AIDLC Evaluation Suite — execute workflow + score outputs via Bedrock",
    )

    parser.add_argument(
        "--test", action="store_true",
        help="Run unit tests for all packages and exit",
    )

    # Scenario selection
    parser.add_argument(
        "--scenario", type=str, default="sci-calc",
        help="Scenario name or path to test case directory (default: sci-calc)",
    )

    # Execution config
    parser.add_argument(
        "--config", type=Path,
        default=REPO_ROOT / "config" / "default.yaml",
        help="Path to YAML config file for the execution stage (default: config/default.yaml)",
    )

    # Execution inputs (override scenario defaults)
    parser.add_argument(
        "--vision", type=Path, default=None,
        help="Path to vision markdown file (default: from scenario)",
    )
    parser.add_argument(
        "--tech-env", type=Path, default=None,
        help="Path to technical environment markdown file (default: from scenario)",
    )

    # Evaluation-only mode
    parser.add_argument(
        "--evaluate-only", type=Path, metavar="AIDLC_DOCS_PATH",
        help="Skip execution; evaluate an existing run's aidlc-docs against the golden baseline",
    )

    # Golden reference (override scenario default)
    parser.add_argument(
        "--golden", type=Path, default=None,
        help="Path to golden aidlc-docs directory (default: from scenario)",
    )

    # OpenAPI specification (override scenario default)
    parser.add_argument(
        "--openapi", type=Path, default=None,
        help="Path to OpenAPI 3.x spec with x-test-cases (default: from scenario)",
    )

    # Sandbox
    sandbox_group = parser.add_mutually_exclusive_group()
    sandbox_group.add_argument(
        "--sandbox", action="store_true", default=True,
        help="Run generated code in a Docker sandbox (default)",
    )
    sandbox_group.add_argument(
        "--no-sandbox", action="store_false", dest="sandbox",
        help="Run generated code directly on the host (no isolation)",
    )

    # Report format
    parser.add_argument(
        "--report-format", choices=["markdown", "html", "both"], default="both",
        help="Report output format (default: both)",
    )

    # Baseline for regression comparison (auto-discovered from scenario)
    parser.add_argument(
        "--baseline", type=Path, default=None,
        help="Path to golden.yaml for regression comparison (default: from scenario)",
    )

    # Output
    parser.add_argument(
        "--output-dir", type=Path,
        help="Override run output directory",
    )
    parser.add_argument(
        "--results", type=Path,
        help="Write qualitative results YAML to this path",
    )

    # AWS / Bedrock
    parser.add_argument("--profile", default=None, help="AWS profile (default: from config YAML)")
    parser.add_argument("--region", default=None, help="AWS region (default: from config YAML)")
    parser.add_argument(
        "--rules-ref", default=None,
        help="Git ref (branch/tag/commit) for AIDLC rules (overrides config value)",
    )
    parser.add_argument(
        "--executor-model", default=None,
        help="Override executor model ID",
    )
    parser.add_argument(
        "--scorer-model", default=None,
        help="Bedrock model for qualitative scoring (default: from config YAML)",
    )

    # Auto-install AutoSkills behavior (default: enabled)
    auto_group = parser.add_mutually_exclusive_group()
    auto_group.add_argument(
        "--auto-install-autoskills",
        dest="auto_install_autoskills",
        action="store_true",
        help="Enable automatic installation of AutoSkills recommended skills (default)",
    )
    auto_group.add_argument(
        "--no-auto-install-autoskills",
        dest="auto_install_autoskills",
        action="store_false",
        help="Disable automatic AutoSkills installation",
    )
    parser.set_defaults(auto_install_autoskills=True)

    # Apply installed AutoSkills (execute skill-provided apply scripts)
    apply_group = parser.add_mutually_exclusive_group()
    apply_group.add_argument(
        "--apply-autoskills",
        dest="apply_autoskills",
        action="store_true",
        help="After installing AutoSkills, attempt to apply each installed skill by executing its apply script (disabled by default)",
    )
    apply_group.add_argument(
        "--no-apply-autoskills",
        dest="apply_autoskills",
        action="store_false",
        help="Do not attempt to execute skill apply scripts",
    )
    parser.set_defaults(apply_autoskills=False)

    # Auto-enable opt-in subagents (writes run_folder/aidlc-docs/aidlc-state.yaml)
    enable_group = parser.add_mutually_exclusive_group()
    enable_group.add_argument(
        "--auto-enable-extensions",
        dest="auto_enable_extensions",
        action="store_true",
        help="Automatically enable opt-in subagents by writing run-level state",
    )
    enable_group.add_argument(
        "--no-auto-enable-extensions",
        dest="auto_enable_extensions",
        action="store_false",
        help="Do not auto-enable opt-in subagents (default)",
    )
    parser.set_defaults(auto_enable_extensions=False)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    # ── Test mode ────────────────────────────────────────────────────────
    if args.test:
        rc = stage_test()
        sys.exit(rc)

    # ── Resolve defaults from config YAML when not provided on CLI ──────
    cfg_data: dict = {}
    cfg_path = args.config
    if cfg_path and cfg_path.exists():
        with open(cfg_path, encoding="utf-8") as f:
            cfg_data = yaml.safe_load(f) or {}

    if args.profile is None:
        args.profile = cfg_data.get("aws", {}).get("profile")
    if args.region is None:
        args.region = cfg_data.get("aws", {}).get("region")
    if args.scorer_model is None:
        args.scorer_model = (
            cfg_data.get("models", {}).get("scorer", {}).get("model_id")
        )
        if args.scorer_model is None:
            parser.error(
                "--scorer-model is required (or set models.scorer.model_id in config YAML)"
            )

    # ── Optional tool paths from config ─────────────────────────────────
    pmd_path = cfg_data.get("tools", {}).get("pmd_path")

    # ── Resolve scenario and apply defaults ──────────────────────────────
    scenario = resolve_scenario(args.scenario, TEST_CASES_DIR)
    if args.vision is None:
        args.vision = scenario.vision_path
    if args.tech_env is None:
        args.tech_env = scenario.tech_env_path
    if args.golden is None:
        args.golden = scenario.golden_aidlc_docs_path
    if args.openapi is None:
        args.openapi = scenario.openapi_path
    if args.baseline is None:
        candidate = scenario.golden_baseline_path
        if candidate.is_file():
            args.baseline = candidate

    # Store scenario name for output path routing
    args._scenario_name = scenario.name

    # ── Evaluate-only mode ───────────────────────────────────────────────
    if args.evaluate_only:
        if not args.evaluate_only.is_dir():
            print(f"Error: path not found: {args.evaluate_only}", file=sys.stderr)
            sys.exit(1)
        if not args.golden.is_dir():
            print(f"Error: golden baseline not found: {args.golden}", file=sys.stderr)
            sys.exit(1)

        run_folder = args.evaluate_only.parent

        # Save evaluation config and repo info
        _save_evaluation_config(run_folder, args, cfg_data)

        # Show test results if evaluating a run folder that has them
        test_results_path = run_folder / "test-results.yaml"
        test_status = _read_test_status(test_results_path)
        if test_status:
            _print_test_summary(test_status)

        # Run quantitative analysis if workspace exists
        workspace = run_folder / "workspace"
        if workspace.is_dir():
            quality_report_path = run_folder / "quality-report.yaml"
            quality_data = stage_quantitative(workspace, quality_report_path, pmd_path=pmd_path)
            quality_status = _read_quality_status(quality_data)
            if quality_status and not quality_status["passed"]:
                print(f"\n  ** CODE QUALITY WARNINGS: {quality_status['summary']} **")

        # Run contract tests if spec exists and workspace is present
        if workspace.is_dir() and args.openapi and args.openapi.is_file():
            contract_report_path = run_folder / "contract-test-results.yaml"
            contract_data = stage_contract(
                workspace, args.openapi, contract_report_path,
                use_sandbox=args.sandbox,
            )
            contract_status = _read_contract_status(contract_data)
            if contract_status:
                _clabel = "PASS" if contract_status["passed"] else "FAIL"
                print(f"\n  Contract tests: {_clabel}  ({contract_status['summary']})")

        stage_qualitative(
            candidate_docs=args.evaluate_only,
            golden_docs=args.golden,
            output_path=args.results,
            profile=args.profile,
            region=args.region,
            model_id=args.scorer_model,
        )

        stage_report(run_folder, args.report_format, args.baseline)
        # Evaluation completed successfully - exit 0
        sys.exit(0)

    # ── Full pipeline ────────────────────────────────────────────────────
    if not args.vision.exists():
        print(f"Error: vision file not found: {args.vision}", file=sys.stderr)
        sys.exit(1)
    if not args.golden.is_dir():
        print(f"Error: golden baseline not found: {args.golden}", file=sys.stderr)
        sys.exit(1)

    print("AIDLC Evaluation Suite")
    print(f"  Scenario:  {scenario.name}")
    print(f"  Config:    {args.config}")
    print(f"  Vision:    {args.vision}")
    print(f"  Tech-env:  {args.tech_env or '(none)'}")
    print(f"  OpenAPI:   {args.openapi or '(none)'}")
    print(f"  Golden:    {args.golden}")
    print(f"  Baseline:  {args.baseline or '(none)'}")
    print(f"  Profile:   {args.profile}")
    print(f"  Region:    {args.region}")
    print(f"  Sandbox:   {'enabled' if args.sandbox else 'disabled'}")

    # Stage 1: Execute the AIDLC workflow
    run_folder = stage_execute(args)
    if run_folder is None:
        print("\n[ABORT] Execution stage failed.", file=sys.stderr)
        sys.exit(1)

    print(f"\nRun completed: {run_folder}")

    # Optionally auto-enable opt-in subagents by writing aidlc-state.yaml
    if getattr(args, "auto_enable_extensions", False):
        try:
            project_root = REPO_ROOT.parent.parent
            manager_path = project_root / "scripts" / "subagents" / "manager.py"
            if manager_path.exists():
                mgr = runpy.run_path(str(manager_path))
                load_agents = mgr.get("load_agents")
                if load_agents:
                    agents = load_agents()
                    to_enable = [a.get("id") for a in agents if a.get("opt_in") and a.get("id") != "midudev-autoskills"]
                    if to_enable:
                        docs_dir = run_folder / "aidlc-docs"
                        docs_dir.mkdir(parents=True, exist_ok=True)
                        state_path = docs_dir / "aidlc-state.yaml"
                        try:
                            existing = yaml.safe_load(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
                        except Exception:
                            existing = {}
                        subagents = existing.get("subagents", {}) if isinstance(existing, dict) else {}
                        for aid in to_enable:
                            subagents.setdefault(aid, True)
                        existing["subagents"] = subagents
                        atomic_yaml_dump(existing, state_path)
                        print(f"  Auto-enabled subagents: {', '.join(to_enable)}")
        except Exception as e:  # pragma: no cover - best-effort
            print(f"[WARN] Failed to auto-enable extensions: {e}", file=sys.stderr)

    # Run subagents that are configured to run during Reverse Engineering
    # (some agents, e.g., AutoSkills, are intended to run at this stage)
    print("\nRunning enabled subagents for phase: reverse-engineering")
    re_subagent_results = run_subagents_for_phases(run_folder, ["reverse-engineering"])
    if re_subagent_results:
        try:
            atomic_yaml_dump(re_subagent_results, run_folder / "subagents-reverse-engineering.yaml")
        except Exception:
            pass
        for aid, rec in re_subagent_results.items():
            if not rec.get("ok"):
                print(f"  SUBAGENT {aid}: FAIL — {rec.get('error')}")
            else:
                print(f"  SUBAGENT {aid}: OK")
        # Generate AutoSkills recommendations document if the autoskills subagent ran
        try:
            rec_path = generate_autoskills_recommendations(run_folder, re_subagent_results)
            if rec_path:
                print(f"  AutoSkills recommendations written: {rec_path}")
        except Exception:
            pass
        # If configured, perform automatic installation of recommended skills
        try:
            if args.auto_install_autoskills:
                print("  Auto-install AutoSkills enabled — installing recommended skills...")
                install_res = auto_install_autoskills(run_folder)
                try:
                    atomic_yaml_dump(install_res, run_folder / "autoskills-install-results.yaml")
                except Exception:
                    pass
                install_md = generate_autoskills_installation_report(run_folder, install_res)
                if install_md:
                    print(f"  AutoSkills installation report written: {install_md}")
                # Append audit entry
                try:
                    audit_path = run_folder / "aidlc-docs" / "audit.md"
                    audit_path.parent.mkdir(parents=True, exist_ok=True)
                    ts = datetime.now(timezone.utc).isoformat()
                    status = "success" if install_res.get("ok") else "failed"
                    with open(audit_path, "a", encoding="utf-8") as f:
                        f.write(f"- {ts} — AutoSkills automatic install: {status}\n")
                except Exception:
                    pass
                # Optionally apply installed skills (execute per-skill apply scripts)
                try:
                    if args.apply_autoskills:
                        print("  Applying installed AutoSkills to workspace...")
                        apply_res = apply_autoskills(run_folder)
                        try:
                            atomic_yaml_dump(apply_res, run_folder / "autoskills-apply-results.yaml")
                        except Exception:
                            pass
                        # Append audit entry
                        try:
                            ts2 = datetime.now(timezone.utc).isoformat()
                            status2 = "success" if apply_res.get("ok") else "failed"
                            with open(audit_path, "a", encoding="utf-8") as f:
                                f.write(f"- {ts2} — AutoSkills apply step: {status2}\n")
                        except Exception:
                            pass
                except Exception:
                    pass
        except Exception:
            pass

    # Save evaluation config and repo info
    _save_evaluation_config(run_folder, args, cfg_data)

    # Run subagents that are configured to run during Construction / Build & Test
    print("\nRunning enabled subagents for phases: construction, build-and-test")
    subagent_results = run_subagents_for_phases(run_folder, ["construction", "build-and-test"])
    if subagent_results:
        try:
            atomic_yaml_dump(subagent_results, run_folder / "subagents-results.yaml")
        except Exception:
            # best-effort save; do not fail the evaluation if dump fails
            pass
        # Print a concise summary
        for aid, rec in subagent_results.items():
            if not rec.get("ok"):
                print(f"  SUBAGENT {aid}: FAIL — {rec.get('error')}")
            else:
                print(f"  SUBAGENT {aid}: OK")

    # Stage 2: Post-run test results (executed inside the runner)
    test_results_path = run_folder / "test-results.yaml"
    test_status = _read_test_status(test_results_path)
    _print_test_summary(test_status)

    # Stage 3: Code quality (lint + security)
    quality_report_path = run_folder / "quality-report.yaml"
    workspace = run_folder / "workspace"
    quality_data = stage_quantitative(workspace, quality_report_path, pmd_path=pmd_path)
    quality_status = _read_quality_status(quality_data)

    # Stage 4: API contract tests
    contract_status: dict | None = None
    if args.openapi and args.openapi.is_file():
        contract_report_path = run_folder / "contract-test-results.yaml"
        contract_data = stage_contract(
            workspace, args.openapi, contract_report_path,
            use_sandbox=args.sandbox,
        )
        contract_status = _read_contract_status(contract_data)

    # Stage 5: Qualitative evaluation
    candidate_docs = run_folder / "aidlc-docs"
    results_path = args.results or (run_folder / "qualitative-comparison.yaml")

    qual_rc = stage_qualitative(
        candidate_docs=candidate_docs,
        golden_docs=args.golden,
        output_path=results_path,
        profile=args.profile,
        region=args.region,
        model_id=args.scorer_model,
    )

    # Stage 6: Consolidated report
    stage_report(run_folder, args.report_format, args.baseline)

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print("  Evaluation Complete")
    print(f"{'=' * 60}")
    print(f"  Run folder:              {run_folder}")
    print(f"  Run metrics:             {run_folder / 'run-metrics.yaml'}")
    if test_status:
        _label = "PASS" if test_status["tests_passed"] else "FAIL"
        print(f"  Post-run tests:          {_label}  ({test_status['summary']})")
    else:
        print(f"  Post-run tests:          N/A (no testable project detected)")
    if quality_status:
        _qlabel = "PASS" if quality_status["passed"] else "WARN"
        print(f"  Code quality:            {_qlabel}  ({quality_status['summary']})")
    else:
        print(f"  Code quality:            N/A (no workspace or tools unavailable)")
    if contract_status:
        _clabel = "PASS" if contract_status["passed"] else "FAIL"
        print(f"  Contract tests:          {_clabel}  ({contract_status['summary']})")
    else:
        print(f"  Contract tests:          N/A (no --openapi provided)")
    print(f"  Qualitative comparison:  {results_path}")
    print(f"  Qualitative score:       (see above)")

    # Report quality findings (not technical failures)
    findings = []
    if test_status and not test_status["tests_passed"]:
        findings.append(f"post-run tests ({test_status['summary']})")
    if contract_status and not contract_status["passed"]:
        findings.append(f"contract tests ({contract_status['summary']})")
    if quality_status and not quality_status["passed"]:
        findings.append(f"code quality ({quality_status['summary']})")

    if findings:
        print(f"\n  ** QUALITY ISSUES FOUND: {'; '.join(findings)} **")

    # Evaluation completed successfully - exit 0 regardless of quality findings
    # (Only exit 1 on technical failures like missing run folder, scorer crash, etc.)
    sys.exit(0)


if __name__ == "__main__":
    main()
