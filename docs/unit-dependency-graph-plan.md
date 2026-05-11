# Unit Dependency Graph — LARGE-Tier Parallelism Plan

## Goal
Make unit dependency waves **deterministic, inspectable, and persisted in the
manifest** so layer-parallel codegen has a single source of truth instead of
being re-derived inline by the orchestrator on every `/factory-build`. The
existing orchestrator already runs layer-parallel `Task()` spawns for multi-unit
runs (Phase 5), so this change is centralization + persistence, not the
introduction of parallelism.

Applies wherever `unit-decomposer` ran (MEDIUM + LARGE tiers). SMALL is a no-op
because it has no decomposer output.

## Non-Goals
- Not for SMALL tier (no decomposer output — nothing to compute).
- Not removing approval gates — batched approval per wave, not skipped.
- Not changing TDD red-green-refactor inside a unit. Parallelism is between
  units, never within.
- Not auto-inferring dependencies from code analysis. `dependencies` is declared
  by `unit-decomposer`, not derived after the fact.
- Not introducing parallel spawning — that already exists in the orchestrator's
  `/factory-build` Step B.2. This change replaces the inline topo-sort with a
  scripted, persisted one.

## Tier Behavior

| Tier   | Unit Execution                       | Wave Source                    | Approval Gates                |
|--------|--------------------------------------|--------------------------------|-------------------------------|
| SMALL  | Single unit (no decomposer ran)      | Synthetic `[["__monolith__"]]` | Single merged gate            |
| MEDIUM | Layer-parallel (existing behavior)   | `factory_graph.py` → manifest  | Per-wave batched gate         |
| LARGE  | Layer-parallel (existing behavior)   | `factory_graph.py` → manifest  | Per-wave batched gate         |

## Design

### 1. Dependency declaration (`unit-decomposer` output)
Each unit spec gains an optional field:
```yaml
unit_name: payment-service
depends_on: [user-service, schema-migrations]
```
Semantics: "this unit cannot start until every listed unit has completed."

Default `depends_on: []` (independent — runs in wave 0).

`unit-decomposer` infers `depends_on` from:
- Shared file paths (Unit A writes `db/schema.sql`, Unit B reads it)
- API contracts (Unit A exposes endpoint, Unit B consumes it)
- Data model ordering (entity definitions before services)
- Explicit ordering hints in the execution plan

### 2. Graph computation (`scripts/factory_graph.py`)
New script. Subcommands:

```bash
# Compute waves from unit specs, write to manifest
python3 scripts/factory_graph.py compute <run-id>

# Print current waves (debug)
python3 scripts/factory_graph.py show <run-id>
```

Algorithm: Kahn's topological sort.
- Read all `aidlc-docs/construction/units/*.yaml`
- Build DAG: node = unit_name, edge = depends_on
- Cycle detection → exit 1 with error listing cycle members
- Output: `manifest.unit_waves: [[u1, u2], [u3], [u4, u5]]`
  - Wave 0: units with zero dependencies
  - Wave N: units whose deps all live in waves 0..N-1

Exit codes:
- 0 — waves computed, written to manifest
- 1 — cycle detected or unit referenced but not defined
- 2 — usage / missing files

### 3. Wave-aware spawn protocol (orchestrator `/factory-build`)

Pre-flight check (runs once at /factory-build entry):
```
if unit-decomposer output exists:
    run factory_graph.py compute <run-id> --apply
    if exit 0:
        proceed to wave execution using manifest.unit_waves
    else:
        log [UnitGraph] ERROR, synthesize single wave with all units, continue
else:
    # SMALL or monolith run
    synthesize manifest.unit_waves: [["__monolith__"]]
    proceed
```

Per-wave execution loop:
```
for wave_idx, wave in enumerate(manifest.unit_waves):
    if len(wave) == 1:
        # Single unit — sequential path (no parallelism overhead)
        spawn_code_generator(wave[0])
        await_completion()
    else:
        # Pre-flight: conflict-resolver collision check
        result = conflict_resolver.check_wave_locks(wave)
        if result.has_collision:
            # Defensive split — drop colliding units to next wave
            log_warning(result)
            wave, deferred = split_wave(wave, result)
            inject deferred into wave_idx + 1
        
        # Parallel spawn — single message, multiple Task() calls
        spawn_all_in_parallel(wave)
        await_all()
    
    # Batched approval gate (per wave, not per unit)
    present_wave_artifacts_to_user(wave)
    wait_for_approval()
```

### 4. Batched approval gate
After a wave's code-generators all emit `status: needs_human`, the orchestrator
presents a single consolidated view:
```
WAVE 1 OF 3 — 2 units ready for approval
  ├─ payment-service: 5 slices, 12 tests added, all green
  └─ notification-service: 3 slices, 8 tests added, all green

Approve all? [y/n/diff]
```

User answers once for the wave. On approval, all units in the wave are marked
complete and the next wave begins.

On rejection: orchestrator halts. User can re-approve individual units or roll
back via `factory_run.py rollback`.

### 5. Conflict-resolver safety net
Existing `scripts/factory_conflict.py` already handles file-glob locks and AST
symbol-drift. New integration point: **pre-flight wave validation.**

Before spawning a wave of N>1 units, call:
```bash
python3 scripts/factory_conflict.py check-wave <run-id> --wave-idx <N>
```

Returns JSON:
```json
{
  "safe": false,
  "collisions": [
    {"unit_a": "payment-service", "unit_b": "billing-service",
     "shared_globs": ["src/db/**"]}
  ]
}
```

If unsafe: defensively split — the second colliding unit gets deferred to the
next wave. Logged to audit as `[UnitGraph] WARN: lock collision deferred X to
wave N+1`.

This protects against bad `depends_on` data without trusting it blindly.

### 6. Failure semantics
- **Wave fails fast**: if any unit in wave N fails, wave N+1 does not spawn.
- **Partial success persists**: completed units written to
  `manifest.completed_units[]` so resume picks up at the failed wave only.
- **Recovery**: `/factory-build <run-id>` re-entry skips completed units, retries
  failed unit, then continues.

## Files to Modify / Create

| File | Action | Purpose |
|------|--------|---------|
| `scripts/factory_graph.py` | **NEW** | Wave computation (Kahn topo-sort) |
| `scripts/factory_conflict.py` | MODIFY | Add `check-wave` subcommand |
| `.aidlc-orchestrator/contracts/unit-decomposer.output.v1.json` | MODIFY | Add `depends_on` per unit |
| `.aidlc-orchestrator/contracts/shared/unit-graph.schema.json` | **NEW** | Validate `manifest.unit_waves` |
| `aidlc-rules/aws-aidlc-rule-details/inception/unit-decomposition.md` | MODIFY | Document `depends_on` inference |
| `.claude/agents/stage/unit-decomposer.md` | MODIFY | Tell decomposer to emit deps |
| `.claude/agents/orchestrator.md` | MODIFY | `/factory-build` wave-aware loop |

## Implementation Tasks

### T1 — `factory_graph.py` with Kahn topo-sort + cycle detection
Deliverable: script reads unit specs, writes `manifest.unit_waves`, exits 0/1/2
appropriately. Tests:
- 3 independent units → 1 wave of 3
- A→B→C linear chain → 3 waves of 1 each
- A→B, A→C, B→D, C→D diamond → 3 waves: [A], [B,C], [D]
- A→B, B→A cycle → exit 1 with cycle members listed
- Reference to undefined unit → exit 1

### T2 — `unit-decomposer` emits `depends_on`
- Update contract schema (add field with default `[]`)
- Update agent instructions to infer deps from execution plan + file overlap
- Existing decomposer output stays valid (default empty array)

### T3 — `factory_conflict.py check-wave` subcommand
- New subcommand reads wave units from manifest
- Computes pairwise lock overlap from each unit's declared `locks_required[]`
- Returns JSON with `safe: bool` + `collisions: []`
- Exit 0 always (informational; orchestrator decides what to do)

### T4 — Orchestrator `/factory-build` reads waves from manifest
- Replace the inline topo-sort in Step A with a call to
  `factory_graph.py compute --apply`
- Insert wave collision pre-flight (`factory_conflict.py check-wave`) between
  B.1 (per-unit pre-flight) and B.2 (parallel spawn)
- On collision: defer `unit_b` to next wave, release any locks already acquired,
  audit-emit `[UnitGraph] wave <N>: deferred <unit> to wave <N+1>`
- Existing parallel-spawn protocol (B.2 sub-stages) unchanged — it already reads
  the active set per layer
- SMALL/monolith fallback: synthesize `[["__monolith__"]]` and proceed

### T5 — Schema + audit trail
- `unit-graph.schema.json` validates `manifest.unit_waves` (array of arrays of strings)
- Audit emits `[UnitGraph] tier=LARGE, waves=N, max_parallelism=M` at build start
- Audit emits `[UnitGraph] wave <i> complete (P parallel units, Q passed, R failed)` after each wave

## Expected Impact

For a typical LARGE-tier feature with 5 units:

| Topology | Sequential | Parallel Waves | Speedup |
|----------|-----------|----------------|---------|
| Linear chain A→B→C→D→E | 5T | 5T (no gain) | 0% |
| Star A → B,C,D,E | 5T | 2T (wave 0: A; wave 1: B,C,D,E) | 60% |
| 2 chains: A→B, C→D, E | 5T | 2T (wave 0: A,C,E; wave 1: B,D) | 60% |
| All independent | 5T | 1T | 80% |

T = single-unit time. Real-world LARGE features typically land between Star and
2-chains topology, so ~50% generate-phase speedup is realistic. Approval gates
remain serialized but are now per-wave, not per-unit — cuts approval prompts
from N to W where W = wave count.

## Risks & Mitigations

| Risk | Mitigation |
|------|-----------|
| `unit-decomposer` produces wrong `depends_on` → false dependency causes serialization that didn't need to happen | Acceptable — slower than ideal, but correct |
| `unit-decomposer` misses a real dependency → race condition in parallel codegen | `conflict-resolver check-wave` catches lock collisions; defensive split |
| Cycle in `depends_on` blocks the whole run | `factory_graph.py` exits 1 with cycle listed; orchestrator falls back to sequential with warning |
| User rejects batched approval — granularity is too coarse | Future: per-unit re-approval inside wave. Phase 2 enhancement. |
| Parallel spawn exceeds rate limits / budget | `factory_budget.py` already gates pre-spawn; if any unit's check returns halt, the wave halts before spawning |

## Out of Scope (Future Phases)
- Auto-inferring `depends_on` from code analysis (vs. decomposer declaration)
- Per-unit re-approval within a rejected wave
- Wave-level parallelism inside `/factory-review` (reviewers per unit)
- Cross-run unit memoization (skip units already built with identical specs)
