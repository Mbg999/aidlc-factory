#!/usr/bin/env python3
"""factory_budget.py — Cost Governor for the AIDLC Orchestrator (Phase 2).

Subcommands
-----------
    init <run-id>
        Initialize per-run budget state at .aidlc-orchestrator/runs/<run-id>/budget.yaml,
        seeded from .aidlc-orchestrator/budgets/default.yaml.

    check <run-id> <stage-name>
        Pre-flight gate. Decides whether the orchestrator may spawn this stage,
        and at what depth.

        Exit codes:
            0 — OK at full depth
            1 — OK but downshift depth to "minimal" (depth-flexible stages only)
            2 — Skip this stage (optional and over threshold)
            3 — Halt run (would exceed remaining run budget on a required stage)

        Always prints a JSON object to stdout with the decision context, and a
        DECISION line to stderr.

    deduct <run-id> <stage-name> --tokens-in N --tokens-out N --wall-min F
        Post-flight reconciliation. Subtracts a stage's actual usage from the
        per-run budget and appends an event to events[].

    status <run-id>
        Pretty-prints the current budget state as YAML.

Limitations
-----------
Claude Code Task() spawns are atomic — once spawned, a subagent runs to
completion. There is no mid-flight cancellation. So this script provides:
    - pre-flight enforcement (check before spawn),
    - post-flight reconciliation (deduct after return),
    - adaptive depth recommendation (downshift on close-to-threshold),
    - hard halt when a required stage cannot fit.
Stage agents themselves are honor-system — they receive `budget` in input and
SHOULD self-monitor, emitting `status: blocked: budget` and partial output
rather than silently overshooting.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("missing dependency: pip install pyyaml", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(os.environ.get("AIDLC_ROOT", Path(__file__).resolve().parents[1]))
DEFAULT_BUDGET = REPO_ROOT / ".aidlc-orchestrator" / "budgets" / "default.yaml"
RUNS_ROOT = REPO_ROOT / ".aidlc-orchestrator" / "runs"

_RUN_ID_RE = re.compile(r"^[a-zA-Z0-9_.-]+$")


def validate_run_id(run_id: str) -> None:
    if not _RUN_ID_RE.match(run_id):
        _die(f"invalid run_id: {run_id!r}")


OPTIONAL_STAGES = {"story-writer", "unit-decomposer"}
DEPTH_FLEXIBLE_STAGES = {"requirements-analyst", "workflow-planner"}
FALLBACK_STAGE_TOKENS = 300_000


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _die(msg: str, code: int = 2) -> None:
    print(msg, file=sys.stderr)
    sys.exit(code)


def load_default() -> dict:
    if not DEFAULT_BUDGET.exists():
        _die(f"default budget not found: {DEFAULT_BUDGET}")
    return yaml.safe_load(DEFAULT_BUDGET.read_text())


def run_budget_path(run_id: str) -> Path:
    validate_run_id(run_id)
    return RUNS_ROOT / run_id / "budget.yaml"


def load_run_budget(run_id: str) -> dict:
    p = run_budget_path(run_id)
    if not p.exists():
        _die(f"run budget not found: {p} (call `init` first)")
    return yaml.safe_load(p.read_text())


def save_run_budget(run_id: str, state: dict) -> None:
    p = run_budget_path(run_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(state, default_flow_style=False, sort_keys=False))


def cmd_init(args: argparse.Namespace) -> None:
    default = load_default()
    state = {
        "run_id": args.run_id,
        "initialized_at": now_iso(),
        "budget": default["run"],
        "used": {"tokens": 0, "wall_clock_min": 0.0},
        "per_stage_used": {},
        "events": [
            {"ts": now_iso(), "action": "init", "source": "factory_budget.py"}
        ],
    }
    save_run_budget(args.run_id, state)
    print(f"initialized {run_budget_path(args.run_id)}")


def estimate_stage_tokens(default: dict, stage: str) -> int:
    per = default.get("per_stage", {})
    # reviewer-* all share `reviewer-*` style budget under per_stage
    for key in (stage, stage.replace("-code", "-*").replace("-security", "-*")
                .replace("-performance", "-*").replace("-simplifier", "-*"),
                "reviewer-*"):
        if key in per:
            return int(per[key]["tokens"])
    return FALLBACK_STAGE_TOKENS


def cmd_check(args: argparse.Namespace) -> None:
    default = load_default()
    state = load_run_budget(args.run_id)

    # If a complexity tier was applied, use its cap instead of the run default.
    tier = state.get("complexity_tier")
    if tier:
        tier_caps = default.get("complexity_tiers", {}).get(tier, {})
        run_max = int(tier_caps.get("tokens_max", state["budget"]["tokens_max"]))
    else:
        run_max = int(state["budget"]["tokens_max"])
    used = int(state["used"]["tokens"])
    remaining = run_max - used
    pct_remaining = (remaining / run_max) * 100.0 if run_max > 0 else 0.0

    threshold_pct = float(default.get("adaptive_depth", {}).get("threshold_pct_remaining", 30))
    estimated = estimate_stage_tokens(default, args.stage)

    remaining_wall = float(state["budget"]["wall_clock_max_min"]) - float(state["used"]["wall_clock_min"])

    decision_obj = {
        "run_id": args.run_id,
        "stage": args.stage,
        "remaining_tokens": remaining,
        "remaining_pct": round(pct_remaining, 1),
        "remaining_wall_min": round(remaining_wall, 1),
        "estimated_tokens": estimated,
        "threshold_pct": threshold_pct,
        "optional": args.stage in OPTIONAL_STAGES,
        "depth_flexible": args.stage in DEPTH_FLEXIBLE_STAGES,
    }

    if remaining_wall <= 0:
        decision_obj["decision"] = "skip" if args.stage in OPTIONAL_STAGES else "halt"
        decision_obj["reason"] = "wall_clock_exhausted"
        print(json.dumps(decision_obj))
        if args.stage in OPTIONAL_STAGES:
            print(f"DECISION: skip ({args.stage} optional; wall clock exhausted)", file=sys.stderr)
            sys.exit(2)
        print(f"DECISION: halt (required {args.stage} would exceed wall clock budget)", file=sys.stderr)
        sys.exit(3)

    if estimated > remaining:
        decision_obj["decision"] = "skip" if args.stage in OPTIONAL_STAGES else "halt"
        decision_obj["reason"] = "estimated_tokens_exceed_remaining"
        print(json.dumps(decision_obj))
        if args.stage in OPTIONAL_STAGES:
            print(f"DECISION: skip ({args.stage} optional; would exceed remaining)", file=sys.stderr)
            sys.exit(2)
        print(f"DECISION: halt (required {args.stage} would exceed remaining budget)", file=sys.stderr)
        sys.exit(3)

    if pct_remaining < threshold_pct:
        if args.stage in OPTIONAL_STAGES:
            decision_obj["decision"] = "skip"
            decision_obj["reason"] = f"under_threshold_pct_{int(threshold_pct)}"
            print(json.dumps(decision_obj))
            print(f"DECISION: skip ({args.stage} optional; under {threshold_pct}% threshold)", file=sys.stderr)
            sys.exit(2)
        if args.stage in DEPTH_FLEXIBLE_STAGES:
            decision_obj["decision"] = "downshift_minimal"
            decision_obj["reason"] = f"under_threshold_pct_{int(threshold_pct)}"
            print(json.dumps(decision_obj))
            print(f"DECISION: downshift depth=minimal ({args.stage} under threshold)", file=sys.stderr)
            sys.exit(1)

    decision_obj["decision"] = "ok"
    decision_obj["reason"] = "within_budget"
    print(json.dumps(decision_obj))
    print(f"DECISION: ok ({args.stage}, {remaining:,} tokens remaining)", file=sys.stderr)
    sys.exit(0)


def cmd_deduct(args: argparse.Namespace) -> None:
    state = load_run_budget(args.run_id)
    if args.tokens_in < 0 or args.tokens_out < 0 or args.wall_min < 0:
        _die(f"negative values not allowed: tokens_in={args.tokens_in}, "
             f"tokens_out={args.tokens_out}, wall_min={args.wall_min}")
    tokens = int(args.tokens_in) + int(args.tokens_out)

    state["used"]["tokens"] = int(state["used"].get("tokens", 0)) + tokens
    state["used"]["wall_clock_min"] = round(
        float(state["used"].get("wall_clock_min", 0.0)) + float(args.wall_min), 1
    )

    per = state.setdefault("per_stage_used", {})
    bucket = per.setdefault(args.stage, {"tokens": 0, "wall_min": 0.0, "calls": 0})
    bucket["tokens"] = int(bucket.get("tokens", 0)) + tokens
    bucket["wall_min"] = round(float(bucket.get("wall_min", 0.0)) + float(args.wall_min), 1)
    bucket["calls"] = int(bucket.get("calls", 0)) + 1

    state["events"].append({
        "ts": now_iso(),
        "stage": args.stage,
        "action": "deduct",
        "tokens_in": int(args.tokens_in),
        "tokens_out": int(args.tokens_out),
        "wall_min": float(args.wall_min),
    })

    save_run_budget(args.run_id, state)
    remaining = int(state["budget"]["tokens_max"]) - int(state["used"]["tokens"])
    print(f"deducted {tokens:,} tokens, {args.wall_min}m for {args.stage}; remaining tokens: {remaining:,}")


def cmd_trends(args: argparse.Namespace) -> None:
    """Aggregate per-stage budget usage across runs matching a prefix."""
    runs_dir = RUNS_ROOT
    if not runs_dir.exists():
        print("no runs directory found", file=sys.stderr)
        sys.exit(1)

    matching = sorted(runs_dir.glob(f"{args.prefix}*/budget.yaml"))
    if not matching:
        print(f"no runs matching prefix {args.prefix!r}", file=sys.stderr)
        sys.exit(1)

    stage_data: dict[str, list[dict]] = {}
    for bp in matching:
        try:
            state = yaml.safe_load(bp.read_text()) or {}
        except Exception:
            continue
        per_stage = state.get("per_stage_used", {}) or {}
        for stage, usage in per_stage.items():
            stage_data.setdefault(stage, []).append(usage)

    if not stage_data:
        print("no per-stage usage data found in any run", file=sys.stderr)
        sys.exit(1)

    print(f"{'Stage':30s} {'Avg tokens':>12s} {'Avg wall':>10s} {'Runs':>6s}")
    print("-" * 60)
    for stage in sorted(stage_data.keys()):
        entries = stage_data[stage]
        avg_tokens = int(sum(e.get("tokens", 0) for e in entries) / len(entries))
        avg_wall = round(sum(e.get("wall_min", 0.0) for e in entries) / len(entries), 1)
        print(f"{stage:30s} {avg_tokens:>12,d} {avg_wall:>8.1f}m {len(entries):>6d}")

    # Store aggregate stats
    stats_dir = REPO_ROOT / ".aidlc-orchestrator" / "stats"
    if not args.dry_run:
        stats_dir.mkdir(parents=True, exist_ok=True)
        agg = {}
        for stage, entries in stage_data.items():
            agg[stage] = {
                "avg_tokens": int(sum(e.get("tokens", 0) for e in entries) / len(entries)),
                "avg_wall_min": round(sum(e.get("wall_min", 0.0) for e in entries) / len(entries), 1),
                "runs": len(entries),
            }
        (stats_dir / "per-stage.yaml").write_text(
            yaml.safe_dump(agg, default_flow_style=False, sort_keys=False)
        )
        print(f"\n(wrote aggregate to {stats_dir / 'per-stage.yaml'})")


def cmd_status(args: argparse.Namespace) -> None:
    state = load_run_budget(args.run_id)
    print(yaml.safe_dump(state, default_flow_style=False, sort_keys=False))


def main() -> None:
    p = argparse.ArgumentParser(description="AIDLC Orchestrator Cost Governor")
    sub = p.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="initialize per-run budget state")
    p_init.add_argument("run_id")
    p_init.set_defaults(func=cmd_init)

    p_check = sub.add_parser("check", help="pre-flight budget gate")
    p_check.add_argument("run_id")
    p_check.add_argument("stage")
    p_check.set_defaults(func=cmd_check)

    p_deduct = sub.add_parser("deduct", help="post-flight reconciliation")
    p_deduct.add_argument("run_id")
    p_deduct.add_argument("stage")
    p_deduct.add_argument("--tokens-in", type=int, default=0)
    p_deduct.add_argument("--tokens-out", type=int, default=0)
    p_deduct.add_argument("--wall-min", type=float, default=0.0)
    p_deduct.set_defaults(func=cmd_deduct)

    p_status = sub.add_parser("status", help="print current budget state")
    p_status.add_argument("run_id")
    p_status.set_defaults(func=cmd_status)

    p_trends = sub.add_parser("trends", help="aggregate per-stage usage across runs")
    p_trends.add_argument("prefix", help="run-id prefix to match (e.g. 2026-05)")
    p_trends.add_argument("--dry-run", action="store_true", help="print trends without writing aggregate")
    p_trends.set_defaults(func=cmd_trends)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
