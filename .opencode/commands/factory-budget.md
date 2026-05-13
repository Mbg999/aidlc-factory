---
description: Configure and monitor the Cost Governor — token budgets, wall-clock limits, model assignment per stage.
argument-hint: [status | config | help]
---

# Cost Governor — Budget Guide

The Cost Governor prevents runs from burning unlimited tokens.
Three layers: **default policy** → **per-run budget** → **per-stage gate**.

---

## Quick commands

```bash
# View current budget state for a run
python3 aidlc-scripts/factory_budget.py status <run-id>

# View budget trends across runs
python3 aidlc-scripts/factory_budget.py trends <prefix>

# Re-initialize budget (e.g. after editing default.yaml)
python3 aidlc-scripts/factory_budget.py init <run-id>
```

---

## How it works

```
┌─────────────────────────────────────────────┐
│  budgets/default.yaml  ← you edit this       │
│  ┌─────────────────────────────────────────┐ │
│  │ run.tokens_max: 5_000_000               │ │
│  │ run.wall_clock_max_min: 240             │ │
│  │ per_stage.code-generator.tokens: 500K   │ │
│  │ per_stage.code-generator.model: opus    │ │
│  └─────────────────────────────────────────┘ │
├─────────────────────────────────────────────┤
│  factory_budget.py init <run-id>              │
│  → copies defaults into run's budget.yaml    │
├─────────────────────────────────────────────┤
│  factory_budget.py check <run-id> <stage>     │
│  → pre-flight gate: ok | downshift | skip     │
├─────────────────────────────────────────────┤
│  factory_budget.py deduct <run-id> <stage>    │
│  → post-flight: subtracts actual tokens      │
└─────────────────────────────────────────────┘
```

---

## Configuring `budgets/default.yaml`

### 1. Run limits

```yaml
run:
  tokens_max: 5_000_000       # Hard cap. Run halts when exceeded.
  wall_clock_max_min: 240     # 4 hours max wall time.
```

Raise these for big refactors, lower for small features.

### 2. Per-stage tokens

```yaml
per_stage:
  code-generator:
    tokens: 500_000      # Estimated max per spawn
    wall_min: 30         # Estimated max duration
    retries: 2           # How many times to retry on failure
    model: opus          # Model to use (sonnet | opus | haiku)
```

**Model assignment** controls which model each stage uses:
- `opus` — for requirements, planning, code-gen (need reasoning)
- `sonnet` — for scout, build-test, reviewers (pattern-matching, cheaper)

Override per-run via env vars: `AIDLC_MODEL_CODE_GENERATOR=haiku`

### 3. Adaptive depth

```yaml
adaptive_depth:
  threshold_pct_remaining: 30   # When <30% budget remains...
  downshift_order:
    - comprehensive→standard     # ...reduce depth
    - standard→minimal
    - skip-optional              # ...skip story-writer, unit-decomposer
```

When budget gets tight, the Cost Governor automatically reduces stage scope
instead of halting. Requiremements-analyst and workflow-planner support
`minimal/standard/comprehensive` depth.

### 4. Complexity tiers

```yaml
complexity_tiers:
  SMALL:  { tokens_max: 500_000,   wall_clock_max_min: 30  }
  MEDIUM: { tokens_max: 1_500_000, wall_clock_max_min: 90  }
  LARGE:  { tokens_max: 5_000_000, wall_clock_max_min: 240 }
```

Set after requirements-analyst. SMALL runs get tighter caps automatically.

---

## Monitoring

```bash
# Per-run: current usage
python3 aidlc-scripts/factory_budget.py status <run-id>

# Per-run: approval gate latency
python3 aidlc-scripts/factory_run.py status <run-id> --latency

# Across runs: which stages consume the most
python3 aidlc-scripts/factory_budget.py trends 2026-05
```

---

## Common adjustments

| Goal | Change |
|------|--------|
| Cheaper runs | Lower `run.tokens_max`, set more stages to `model: sonnet` |
| Faster runs | Lower `wall_clock_max_min` so Cost Governor skips optional stages earlier |
| Better code-gen | Set `code-generator.model: opus` (slower, more expensive, better quality) |
| Cheaper code-gen | Set `code-generator.model: sonnet` (faster, cheaper, good enough for simple tasks) |
| Skip reviewers | Set `reviewer-*.tokens: 0` (Cost Governor skips stages with 0 tokens) |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| Run halts immediately | `tokens_max` too low for first stage | Check `workspace-scout` estimate; double `tokens_max` |
| "Negative remaining" in status | Overspent — `deduct` ran without `check` | Re-init: `factory_budget.py init <run-id>` |
| Stage unexpectedly skipped | Under `threshold_pct_remaining` | Raise threshold or lower stage estimates |
| Wrong model used for stage | `model_override` set but tool doesn't support it | Claude Code respects it; other tools ignore it |
