# Complexity Threshold — Implementation Plan

## Problem

Every run executes the same stage sequence regardless of scope. A 35-line server
takes as long as a 500-line multi-service refactor. The overhead is proportional
to *process*, not *work*.

## Solution

After `requirements-analyst` completes, a new script reads its output and assigns
a **complexity tier** (SMALL / MEDIUM / LARGE). The orchestrator uses that tier to
skip stages, reduce gate count, and cap the reviewer pool — before any further
agents spawn.

The `requirements-analyst` output already emits `request_classification.scope` and
`request_classification.complexity` — no new LLM inference needed. The tier mapping
is pure deterministic Python.

---

## Tier Definitions

| Tier | Criteria (from `request_classification`) | Token budget cap |
|---|---|---|
| **SMALL** | scope=`Single File` or `Single Component` AND complexity=`Trivial` or `Simple` | 500K |
| **MEDIUM** | scope=`Multiple Components` OR complexity=`Moderate` | 1.5M |
| **LARGE** | scope=`System-wide` or `Cross-system` OR complexity=`Complex` | 5M (current default) |

Tie-break rule: when scope and complexity point to different tiers, take the higher one.

---

## Stage Routing Per Tier

| Stage | SMALL | MEDIUM | LARGE |
|---|---|---|---|
| story-writer | skip | skip | run |
| unit-decomposer | skip | run if unit_count ≥ 3 | run |
| code-generator plan gate | merged into generate pass | keep | keep |
| code-generator generate gate | 1 approval total | 1 per unit | 1 per unit |
| build-test-agent | run | run | run |
| reviewer-code | run | run | run |
| reviewer-security | skip | run | run |
| reviewer-performance | skip | skip | run |
| reviewer-simplifier | skip | run | run |
| **Total human gates** | **2** | **3–4** | **6+** |

For SMALL: code-generator receives `merged_plan_generate: true` in its input
handoff. It skips the inner plan approval and presents plan + code in a single
output block (one `needs_human` instead of two).

---

## Files to Create / Modify

### 1. `aidlc-scripts/factory_complexity.py` *(new)*

Reads the requirements-analyst output YAML, maps `scope` + `complexity` to a tier,
prints a JSON routing decision, exits 0 on success / 1 on missing input.

```
Input:  .aidlc-orchestrator/runs/<run-id>/handoffs/requirements-analyst.output.yaml
Output: JSON printed to stdout
        {
          "tier": "SMALL" | "MEDIUM" | "LARGE",
          "skip_stages": ["story-writer", "unit-decomposer"],
          "merge_codegen_gate": true | false,
          "reviewer_pool": ["reviewer-code"],
          "tokens_max": 500000,
          "wall_clock_max_min": 30,
          "rationale": "<scope> + <complexity> → SMALL"
        }
Exit:   0 = success
        1 = requirements output file missing or unparseable
```

No LLM calls. No network I/O. Pure mapping logic.

### 2. `.claude/agents/orchestrator.md` *(modify)*

Add **"Complexity Routing Gate"** section immediately after the
`requirements-analyst` stage completes:

```
1. python3 aidlc-scripts/factory_complexity.py <run-id>         # determine tier
2. factory_run.py set <run-id>                            # store in manifest
       --field complexity_tier=<TIER>
       --field skip_stages=["story-writer","unit-decomposer"]
       --field reviewer_pool=["reviewer-code"]
3. factory_run.py emit <run-id>                           # timeline event
       --evt orchestrator_note
       --field summary="[ComplexityGov] tier=SMALL, skip_stages=[...]"
4. Append audit entry: [ComplexityGov] tier=SMALL, skipping: <stages>
```

All subsequent `if stage in manifest.skip_stages → skip` checks use this field.
A skipped stage emits a `stage_skipped` timeline event (already supported by
`factory_run.py`).

### 3. `.aidlc-orchestrator/budgets/default.yaml` *(modify)*

Add tier-based caps below the existing `per_stage:` block:

```yaml
complexity_tiers:
  SMALL:  { tokens_max: 500_000,   wall_clock_max_min: 30  }
  MEDIUM: { tokens_max: 1_500_000, wall_clock_max_min: 90  }
  LARGE:  { tokens_max: 5_000_000, wall_clock_max_min: 240 }
```

`factory_budget.py` reads `run.tokens_max` today — add a single branch: if
manifest has `complexity_tier`, use `complexity_tiers[tier].tokens_max` instead.

### 4. `.aidlc-orchestrator/contracts/shared/complexity-tier.schema.yaml` *(new)*

JSON Schema fragment validating the manifest fields written by
`factory_complexity.py`. Used by `factory_validate.py`.

### 5. `contracts/code-generator.input.v1.json` *(modify)*

Add optional field:

```json
"merged_plan_generate": {
  "type": "boolean",
  "default": false,
  "description": "When true, skip inner plan approval gate and present plan + code in single output."
}
```

---

## Implementation Tasks

### T1 — `aidlc-scripts/factory_complexity.py`
- [ ] Parse `requirements-analyst.output.yaml`, read `request_classification`
- [ ] Apply tier table (tie-break: take higher tier)
- [ ] Emit reviewer pool based on tier
- [ ] Print JSON to stdout, exit 0
- [ ] Exit 1 with message to stderr if file missing or `request_classification` absent

**AC:**
- scope=`Single Component` + complexity=`Simple` → `tier=SMALL`, `merge_codegen_gate=true`
- scope=`Cross-system` + complexity=`Trivial` → `tier=LARGE` (scope wins tie-break)
- Missing file → exit 1, no stdout

### T2 — `orchestrator.md`: complexity routing gate
- [ ] Add "Complexity Routing Gate" section after requirements-analyst approval
- [ ] Document the 4-step sequence (run script → set manifest → emit event → audit)
- [ ] Add skip logic: `for stage in skip_stages → emit stage_skipped, log [ComplexityGov]`
- [ ] Add reviewer pool routing: use `manifest.reviewer_pool` instead of hardcoded list

**AC:**
- Tier stored in manifest before any downstream stage spawns
- Each skipped stage has a `stage_skipped` timeline event
- `[ComplexityGov]` audit entry written per skipped stage

### T3 — `budgets/default.yaml` + `factory_budget.py`
- [ ] Add `complexity_tiers` block to `default.yaml`
- [ ] In `factory_budget.py check`: if `manifest.complexity_tier` present, apply tier cap
- [ ] LARGE tier = no change to current behavior (regression guard)

**AC:**
- `factory_budget.py check <run-id> <stage>` respects tier cap
- Existing tests pass unmodified for LARGE / no-tier runs

### T4 — Code-generator: `merged_plan_generate` mode
- [ ] Add field to `code-generator.input.v1.json`
- [ ] Document behavior in `.claude/agents/stage/code-generator.md`
- [ ] When `merged_plan_generate=true`: present plan inline with generated code,
      output `sub_stage: generated` directly (no intermediate `sub_stage: plan`)

**AC:**
- SMALL run triggers only 1 code-generator approval gate per unit (not 2)
- MEDIUM/LARGE runs unaffected

### T5 — `contracts/shared/complexity-tier.schema.yaml`
- [ ] Define schema for `complexity_tier`, `skip_stages`, `reviewer_pool`, `merge_codegen_gate`
- [ ] Register in `factory_validate.py` manifest validation path

**AC:**
- `factory_validate.py` rejects manifest with `complexity_tier: SMOL` (typo)
- `factory_validate.py` accepts valid tier with empty `skip_stages`

---

## Expected Impact

The `pruebaaidlcv2` healthz-endpoint run would have been classified **SMALL**
(Single Component + Simple):

| Metric | Before | After (SMALL) |
|---|---|---|
| Stages skipped | 0 | 2 (story-writer, unit-decomposer) |
| Human gates | 6 | 2 |
| Reviewer agents | 4 | 1 |
| Token budget cap | 5M | 500K |
| Estimated wall time | ~120 min | ~20 min |

LARGE features: zero regression. Full path runs as today.

---

## Order of Implementation

T1 → T3 → T2 → T5 → T4

Rationale: T1 (script) and T3 (budget) are independent and unblock T2 (orchestrator
routing). T5 (schema) is a safety net and can be added after T2. T4 (merged gate)
is the highest-risk change and goes last.
