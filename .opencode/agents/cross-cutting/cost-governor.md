---
description: AIDLC Orchestrator's budget enforcement layer. Owns the per-run token/wall-clock budget, four-path decision gate (ok/downshift/skip/halt), and adaptive-depth routing. NOT a Task() subagent — orchestrator invokes aidlc-scripts/factory_budget.py directly.
---

# Cost Governor (Phase 2 — active)

> **Architectural note:** the Cost Governor is **not** a Task()-spawnable
> subagent. It is a *capability* the orchestrator exercises by calling
> `aidlc-scripts/factory_budget.py` (CLI) and parsing its exit codes. This file
> is the canonical spec for HOW the orchestrator integrates budget
> enforcement into every spawn cycle.

## Purpose

Prevent the multi-agent system from being economically absurd. The Cost
Governor enforces budget at two checkpoints around every stage spawn:

1. **Pre-flight gate** — before spawning a stage, check whether the
   estimated cost fits within remaining budget. Returns one of four
   decisions (`ok`, `downshift`, `skip`, `halt`) the orchestrator routes on.
2. **Post-flight reconciliation** — after the stage returns, deduct actual
   usage from `cost.{tokens_in, tokens_out, wall_clock_min}` in the output.
   Falls back to default-budget estimate if the `cost` block is absent
   (logged as `[CostGov] Estimated`).

## Storage

```
.aidlc-orchestrator/
├── budgets/default.yaml             # policy: tokens_max, wall_clock_max_min,
│                                    # per-stage estimates, adaptive_depth threshold
└── runs/<run-id>/budget.yaml        # per-run state: used totals, per-stage actuals,
                                     # event log
```

`budgets/default.yaml` is committed (it's the policy). `runs/<run-id>/budget.yaml`
is per-run runtime state and gitignored.

## Four-path decision

Each `python3 aidlc-scripts/factory_budget.py check <run-id> <stage>` call returns
one of four exit codes the orchestrator MUST route on:

| Exit | Decision | Orchestrator action |
|---|---|---|
| 0 | `ok` | spawn the stage as planned |
| 1 | `downshift_minimal` | spawn with `depth_override: minimal` in the input handoff (depth-flexible stages only) |
| 2 | `skip` | conditional/optional stage falls under threshold — skip entirely, mark in `manifest.skipped_stages[]` |
| 3 | `halt` | required stage's estimated cost exceeds remaining tokens — pause the run, write `[CostGov] HALT <stage>: <reason>` to audit, surface to user |

Stages classified by the `default.yaml` policy:
- **Optional**: `story-writer`, `unit-decomposer` (`reverse-engineer` is optional but
  conditional on brownfield, not on budget).
- **Depth-flexible**: `requirements-analyst`, `workflow-planner` (honor `depth_override`
  via the contract field added in Phase 2).
- **Required, fixed depth**: everything else — they only see exit codes 0 or 3.

## Adaptive depth

When `remaining_pct < threshold_pct_remaining` (default `30%` from
`budgets/default.yaml`):

- Depth-flexible stages get `depth_override: minimal` injected into their input.
- Optional stages are skipped (exit code 2).
- Required, fixed-depth stages either pass (exit 0) or halt (exit 3) — there's
  no third option for them.

The override field exists on `requirements-analyst.input.v1.json` and
`workflow-planner.input.v1.json`. Both agents are required to honor it
and log `[CostGov] Depth overridden minimal (remaining: <pct>%)` to audit.

## Integration points (orchestrator-side)

In every flow's "All flows share the same primitives" sequence:

- **Step 1 (pre-flight gate)** — run before any `Task()` spawn:
  ```bash
  python3 aidlc-scripts/factory_budget.py check <run-id> <stage>
  # Read exit code → route per the table above.
  # Read JSON on stdout for decision details (estimated tokens, threshold pct).
  ```
- **Step 5 (post-flight reconciliation)** — run after every `Task()` returns:
  ```bash
  python3 aidlc-scripts/factory_budget.py deduct <run-id> <stage> \
    --tokens-in <n> --tokens-out <n> --wall-min <n>
  ```
  If the stage output omits a `cost` block, deduct using the default
  estimate from `default.yaml` and log `[CostGov] Estimated <stage>: <tokens>`.

For run setup (Phase 0 Step 1 / Phase 1 run lookup), the orchestrator
also runs:
```bash
python3 aidlc-scripts/factory_budget.py init <run-id>
```
This is idempotent — if `runs/<run-id>/budget.yaml` already exists (legacy
adoption case), the script leaves it alone.

## Surfacing budget state

Every stage completion message MUST include a one-line budget summary:

```
Budget: 3.6M / 5M tokens used (72%) — 1.4M remaining
```

The values come from `python3 aidlc-scripts/factory_budget.py status <run-id>`.

## Honor system on stage agents

Every input handoff carries a `budget` block (see §4.1 of
`ORCHESTRATOR-PLAN.md`). Stage agent system prompts instruct the agent
to prefer emitting a partial output with `status: blocked: budget` over
silently overshooting. This is advisory — see *Limitations* below.

## Limitations

- **Mid-flight cancellation is not possible.** Claude Code `Task()` returns
  are atomic — the orchestrator cannot interrupt a running spawn. Enforcement
  is pre-flight (estimate-based) + post-flight (actuals-based). A wildly
  overshooting agent will only be caught AFTER it finishes; the NEXT stage's
  gate then halts the run.
- **Token usage during a spawn is not visible** until the agent returns.
  Heartbeat-based mid-flight monitoring (mentioned in `ORCHESTRATOR-PLAN.md
  §6.3` as future work) is not implemented and would require changes outside
  the orchestrator's purview.
- **No cross-run quota.** Budget is per-run only. Multiple concurrent runs
  on the same machine each get their own token ceiling.
- **No USD accounting.** Token budget is the sole hard constraint.
  USD/cost tracking was intentionally dropped (Bug #2 / 2026-05-09) — token
  rates change frequently and the rate table would have decayed faster than
  it could be maintained. If USD tracking becomes important, revive via a
  `pricing` block in `budgets/default.yaml` keyed by model.

## Configuration

`budgets/default.yaml`:
```yaml
run:
  tokens_max: 5000000
  wall_clock_max_min: 240
per_stage:
  workspace-scout: { tokens: 50000, wall_min: 5, retries: 1 }
  requirements-analyst: { tokens: 800000, wall_min: 30, retries: 2, depth_flexible: true }
  workflow-planner: { tokens: 600000, wall_min: 25, retries: 2, depth_flexible: true }
  story-writer: { tokens: 300000, wall_min: 15, retries: 1, optional: true }
  unit-decomposer: { tokens: 400000, wall_min: 20, retries: 1, optional: true }
  code-generator: { tokens: 500000, wall_min: 30, retries: 2 }
  build-test-agent: { tokens: 300000, wall_min: 20, retries: 3 }
  reviewer-code: { tokens: 200000, wall_min: 15, retries: 1 }
  reviewer-security: { tokens: 250000, wall_min: 15, retries: 1 }
  reviewer-performance: { tokens: 200000, wall_min: 15, retries: 1 }
  reviewer-simplifier: { tokens: 200000, wall_min: 15, retries: 1 }
  ship-agent: { tokens: 300000, wall_min: 15, retries: 1 }
concurrency:
  max_parallel: 4
adaptive_depth:
  threshold_pct_remaining: 30
```

Per-run overrides go in `.aidlc-orchestrator/budgets/overrides/<run-id>.yaml`
and are merged on top of `default.yaml` at `init` time.
