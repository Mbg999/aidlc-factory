# Unit Dependency Graph — Governance Fixes Plan

## Goal
Fix the 5 governance/reproducibility issues identified in the post-implementation
audit. All fixes are markdown edits in [orchestrator.md](.claude/agents/orchestrator.md);
no script changes required.

## Prerequisite
Selective rollback already done — orchestrator.md is back to its pre-T4 state.
`factory_graph.py`, `check-wave`, and the schema remain as tested-but-unused
infrastructure ready for clean re-wire-up.

## Fixes (in landing order)

### F1 — Reorder Step B.1 so collision check precedes lock acquire (fixes Issue #1)

**Problem:** locks and AST snapshots taken before `check-wave` get stranded
when a unit is deferred — files may mutate between lock release and re-acquire,
silently invalidating the AST baseline.

**Fix:** split the existing B.1 into two phases.

New ordering inside `/factory-build` Step B:
```
B.1a — Cheap pre-flight (no side effects) per unit:
  1. Budget gate          (factory_budget.py check)
  2. Knowledge query      (mem_search → context_pointers[])
  3. Build input handoff  (write code-generator.<unit>.input.yaml — declares locks_required[])

B.1b — Wave collision pre-flight (only if active set ≥ 2):
  factory_conflict.py check-wave <run-id> --wave-idx <N>
  - safe: true  → proceed to B.1c with full active set
  - safe: false → defer per F2; deferred units skip B.1c entirely

B.1c — Side-effect pre-flight per surviving unit:
  4. Lock acquire    (factory_conflict.py acquire)
  5. AST snapshot    (factory_conflict.py snapshot, Python only)
```
Deferred units never acquire locks or take snapshots in this wave — no
staleness risk on re-acquire later.

### F2 — Keep `manifest.unit_waves` immutable; track deferrals separately (fixes Issue #2)

**Problem:** mutating `unit_waves` mid-execution destroys the Step A
deterministic plan, breaking replay-from-manifest.

**Fix:** add a sibling field `manifest.deferrals[]` (append-only).

On collision in B.1b, instead of read-modify-write of `unit_waves`:
```yaml
# manifest.yaml grows a new field
deferrals:
  - from_wave: 0
    to_wave: 1
    unit: payment-service
    reason: "glob overlap: src/db/** ∩ src/db/schema.sql with user-service"
    detected_at: <ts>
```

Wave execution loop (orchestrator-side):
```
for wave_idx in range(len(manifest.unit_waves)):
    active_set = list(manifest.unit_waves[wave_idx])
    # Pull in any units deferred into this wave
    active_set += [d.unit for d in manifest.deferrals if d.to_wave == wave_idx]
    # ...proceed with B.1a → B.1b → B.1c
```

`unit_waves` stays exactly as `factory_graph.py` wrote it. Execution path is
reconstructable from `unit_waves` + `deferrals[]` together.

### F3 — Event-first protocol for new audit blocks (fixes Issue #3)

**Problem:** I prescribed audit blocks with `<ts>` placeholders but never
specified the `factory_run.py emit` calls that produce them, violating the
"timeline is source of truth" rule.

**Fix:** prefix every new audit block with an explicit emit step.

For the unit-graph-computed audit in Step A:
```bash
python3 scripts/factory_run.py emit <run-id> --evt unit_graph_computed \
    --field tier=<tier> \
    --field wave_count=<N> \
    --field max_parallelism=<M>
# Capture stdout ts → use as <ts> in the audit block below
```
Then append:
```
## <ts> CONSTRUCTION - UNIT GRAPH
- [UnitGraph] tier=<tier>, waves=<N>, max_parallelism=<M>
- [UnitGraph] wave 0: <units...>
- [UnitGraph] wave 1: <units...>
```

For collision deferrals in B.1b:
```bash
python3 scripts/factory_run.py emit <run-id> --evt wave_collision_deferred \
    --stage code-generator \
    --field wave_idx=<N> \
    --field deferred_unit=<u> \
    --field reason="<glob_a> ∩ <glob_b>"
```
Same pattern — capture timestamp, use in audit block.

### F4 — Cycle fallback synthesizes one wave per unit (fixes Issue #4)

**Problem:** on cycle detection, my fallback says "single wave containing all
units" — which means parallel spawn. We just decided we don't trust the deps.

**Fix:** change Step A fallback text from:
> ...synthesize a single wave containing all units in declared order.

To:
> ...synthesize **one wave per unit** in declared order (fully sequential —
> `[[u1], [u2], [u3]]`). Cycle detection means dependency declarations are
> untrustworthy; sequential execution is the only safe fallback.

### F5 — Document the wave-level resume gap (acknowledges Issue #5)

**Problem:** `manifest.completed_units[]` exists but `completed_waves[]` does
not, so resume after interruption re-derives wave state instead of reading it.

**Fix:** add a "Known Limitations" note to Step A:

```
> KNOWN LIMITATION: wave completion state is not first-class in the manifest.
> Resume after interruption derives wave progress from
> manifest.completed_units[] by checking which units in each wave have entries.
> This works correctly but is implicit; future work may add explicit
> manifest.completed_waves[] tracking.
```

No code change. Just disclosure so future maintainers don't assume the field
exists.

## Files Touched
| File | Lines (approx) | Risk |
|------|---------------|------|
| `.claude/agents/orchestrator.md` | ~60 lines edited across Step A and B.1 | Low — markdown only, no script changes |

## Acceptance Criteria
After F1–F5 land:
- [ ] B.1 has three sub-phases (a/b/c) with `check-wave` between handoff-build and lock-acquire
- [ ] No instruction anywhere says to mutate `manifest.unit_waves`
- [ ] Every `## <ts>` audit block has an explicit `factory_run.py emit` call preceding it
- [ ] Step A cycle fallback says "one wave per unit" not "single wave"
- [ ] Step A includes the wave-completion-tracking limitation note

## Out of Scope
- Adding `manifest.completed_waves[]` — deferred until wave-level resume becomes a real pain point.
- Re-snapshot-on-re-acquire logic — F1 makes it moot by never snapshotting deferred units in the first place.
- Auto-resolution of deferrals (vs. surface to user) — same as current Phase 5 escalation model.

## Testing
After landing, the only way to fully validate is an end-to-end multi-unit run.
Static checks possible before that:
- Re-read orchestrator.md Step A and B.1 — verify event-first ordering
- Grep orchestrator.md for any remaining `## <ts>` block without a preceding emit
- Grep for any remaining mention of "modify unit_waves" or "single wave containing all"
