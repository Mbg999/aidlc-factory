#!/usr/bin/env python3
"""Pipeline executor for AIDLC subagents.

Reads pipeline definitions from agents.yaml (``pipelines`` key) and executes
them as a DAG: stages run sequentially, agents within a stage run in parallel.

Usage:
  python scripts/subagents/pipeline.py <pipeline_id> [json_context]
  python scripts/subagents/pipeline.py --list

Example:
  python scripts/subagents/pipeline.py construction-full '{"run_folder": "runs/my-run"}'

Pipeline YAML schema (defined in agents.yaml):
  pipelines:
    - id: construction-full
      name: Full construction pipeline
      stages:
        - group:
            - planner
        - group:
            - builder
            - code-reviewer
        - group:
            - construction-reviewer

Exit codes:
  0  All stages completed (some agents may have warnings)
  1  At least one agent returned an error (check results for details)
  2  Pipeline not found or config error
"""
from __future__ import annotations

import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]

# Import manager run() — same package
try:
    import runpy as _runpy
    _mgr_globals = _runpy.run_path(str(REPO_ROOT / "scripts" / "subagents" / "manager.py"))
    _manager_run = _mgr_globals["run"]
    _load_agents = _mgr_globals["load_agents"]
    _write_audit_log = _mgr_globals["_write_audit_log"]
    _sanitize_context = _mgr_globals["_sanitize_context"]
    AGENTS_CONF_CANDIDATES = _mgr_globals["AGENTS_CONF_CANDIDATES"]
except Exception as e:
    print(json.dumps({"error": f"Failed to load manager: {e}"}))
    sys.exit(2)

try:
    import yaml  # type: ignore
except ImportError:
    yaml = None


def load_pipelines(conf_path: Path | None = None) -> list[dict]:
    """Load pipeline definitions from agents.yaml."""
    if conf_path is None:
        conf_path = next(
            (p for p in AGENTS_CONF_CANDIDATES if p.exists()),
            AGENTS_CONF_CANDIDATES[0],
        )
    if yaml is not None and conf_path.exists():
        with open(conf_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        return data.get("pipelines", [])
    return []


def find_pipeline(pipeline_id: str, conf_path: Path | None = None) -> dict | None:
    return next(
        (p for p in load_pipelines(conf_path) if p.get("id") == pipeline_id),
        None,
    )


def _run_agent_safe(agent_id: str, context: dict) -> dict:
    """Run a single agent, returning a result dict (never raises)."""
    try:
        return _manager_run(agent_id, context)
    except Exception as e:
        return {"agent_id": agent_id, "status": "error", "error": str(e)}


def run_pipeline(
    pipeline_id: str,
    context: dict | None = None,
    conf_path: Path | None = None,
    max_workers: int = 4,
) -> dict:
    """Execute a pipeline by id.

    Returns a summary dict:
      {
        "pipeline_id": str,
        "status": "success" | "partial_failure" | "error",
        "stages": [
          {
            "stage_index": int,
            "group": [agent_id, ...],
            "results": {agent_id: result_dict},
            "status": "success" | "partial_failure",
          },
          ...
        ],
        "started_at": ISO8601,
        "finished_at": ISO8601,
        "duration_seconds": float,
      }
    """
    pipeline = find_pipeline(pipeline_id, conf_path)
    if pipeline is None:
        return {"error": f"Pipeline not found: '{pipeline_id}'", "status": "error"}

    ctx = context or {}
    sanitized = _sanitize_context(ctx)
    started_at = datetime.now(timezone.utc)

    stage_results: list[dict[str, Any]] = []
    overall_ok = True

    for i, stage_def in enumerate(pipeline.get("stages", [])):
        group: list[str] = stage_def.get("group", [])
        if not group:
            continue

        stage_summary: dict[str, Any] = {
            "stage_index": i,
            "group": group,
            "results": {},
            "status": "success",
        }

        if len(group) == 1:
            # Single agent — no threading overhead
            agent_id = group[0]
            result = _run_agent_safe(agent_id, ctx)
            stage_summary["results"][agent_id] = result
            if isinstance(result, dict) and result.get("error"):
                stage_summary["status"] = "partial_failure"
                overall_ok = False
        else:
            # Multiple agents — run in parallel
            with ThreadPoolExecutor(max_workers=min(max_workers, len(group))) as executor:
                futures = {
                    executor.submit(_run_agent_safe, agent_id, ctx): agent_id
                    for agent_id in group
                }
                for future in as_completed(futures):
                    agent_id = futures[future]
                    try:
                        result = future.result()
                    except Exception as e:
                        result = {"agent_id": agent_id, "status": "error", "error": str(e)}
                    stage_summary["results"][agent_id] = result
                    if isinstance(result, dict) and result.get("error"):
                        stage_summary["status"] = "partial_failure"
                        overall_ok = False

        stage_results.append(stage_summary)

    finished_at = datetime.now(timezone.utc)
    summary = {
        "pipeline_id": pipeline_id,
        "pipeline_name": pipeline.get("name", pipeline_id),
        "status": "success" if overall_ok else "partial_failure",
        "stages": stage_results,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "duration_seconds": (finished_at - started_at).total_seconds(),
    }

    # Audit log the pipeline run
    _write_audit_log(sanitized, f"pipeline_{pipeline_id}", summary)

    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="AIDLC pipeline executor")
    parser.add_argument("pipeline_id", nargs="?", help="Pipeline id to execute")
    parser.add_argument("context_json", nargs="?", default="{}", help="JSON context string")
    parser.add_argument("--list", action="store_true", help="List available pipelines")
    parser.add_argument("--max-workers", type=int, default=4, help="Max parallel agents per stage")
    args = parser.parse_args()

    if args.list:
        pipelines = load_pipelines()
        if not pipelines:
            print("No pipelines defined in agents.yaml")
        else:
            for p in pipelines:
                stages = p.get("stages", [])
                print(f"  {p['id']}: {p.get('name', '')} ({len(stages)} stage(s))")
        sys.exit(0)

    if not args.pipeline_id:
        parser.print_help()
        sys.exit(2)

    try:
        ctx = json.loads(args.context_json)
    except Exception:
        ctx = {}

    result = run_pipeline(args.pipeline_id, ctx, max_workers=args.max_workers)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("status") == "success" else 1)
