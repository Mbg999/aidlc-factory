#!/usr/bin/env python3
"""factory_complexity.py — Complexity Router for the AIDLC Orchestrator.

Always returns the full comprehensive routing (LARGE tier, no skipped stages,
full reviewer pool). The triage/FAST_PATH/tier system has been removed —
every request goes through the same complete pipeline.

Usage
-----
    factory_complexity.py <run-id> [--apply]

Output (stdout)
---------------
    JSON object with the comprehensive routing config.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from skill_utils import _log
except ImportError:
    def _log(level: str, msg: str, **kwargs) -> None:
        stream = sys.stderr if level in ("ERROR", "WARNING") else sys.stdout
        print(f"[{level}] {msg}", file=stream)

try:
    import yaml
except ImportError:
    print(f"missing dependency: {sys.executable} -m pip install pyyaml", file=sys.stderr)
    sys.exit(2)


REPO_ROOT = Path(__file__).resolve().parents[1]
_AIDLC_ROOT = Path(os.environ["AIDLC_ROOT"]) if "AIDLC_ROOT" in os.environ else REPO_ROOT
RUNS_ROOT = _AIDLC_ROOT / ".aidlc-orchestrator" / "runs"

COMPREHENSIVE_ROUTING = {
    "complexity_tier": "LARGE",
    "fast_path": False,
    "skip_stages": [],
    "merge_codegen_gate": False,
    "reviewer_pool": [
        "reviewer-code",
        "reviewer-security",
        "reviewer-performance",
        "reviewer-simplifier",
    ],
    "tokens_max": 5_000_000,
    "wall_clock_max_min": 240,
}


def cmd_assess(args: argparse.Namespace) -> None:
    result = dict(COMPREHENSIVE_ROUTING)
    result["rationale"] = "Always full pipeline — no triage, all stages run."
    print(json.dumps(result, indent=2))

    if args.apply:
        _apply_to_budget(args.run_id, result)


def _apply_to_budget(run_id: str, routing: dict) -> None:
    budget_path = RUNS_ROOT / run_id / "budget.yaml"
    if not budget_path.exists():
        print(
            f"[ComplexityGov] budget.yaml not found at {budget_path} — skipping apply",
            file=sys.stderr,
        )
        return
    state = yaml.safe_load(budget_path.read_text(encoding="utf-8")) or {}
    state.setdefault("budget", {})
    state["budget"]["tokens_max"] = routing["tokens_max"]
    state["budget"]["wall_clock_max_min"] = routing["wall_clock_max_min"]
    state["complexity_tier"] = routing["complexity_tier"]
    tmp = budget_path.with_suffix(".yaml.tmp")
    tmp.write_text(yaml.safe_dump(state, default_flow_style=False, sort_keys=False), encoding="utf-8")
    tmp.replace(budget_path)
    print(
        f"[ComplexityGov] Applied comprehensive routing: tokens_max={routing['tokens_max']:,}, "
        f"wall_clock_max_min={routing['wall_clock_max_min']}",
        file=sys.stderr,
    )


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="factory_complexity.py",
        description="Assign comprehensive routing to an AIDLC run.",
    )
    p.add_argument("run_id", help="Run ID (directory under .aidlc-orchestrator/runs/)")
    p.add_argument(
        "--apply",
        action="store_true",
        help="Write token cap into the run's budget.yaml",
    )
    return p


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    cmd_assess(args)


if __name__ == "__main__":
    main()
