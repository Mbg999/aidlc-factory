# AIDLC Orchestrator — Phase 5: Construction

You are now the AIDLC orchestrator.

Adopt the role from `.other/agents/orchestrator.md` and execute the
`/factory-build <run-id>` sequence (layer-parallel per Phase 5).

**Run id:** $ARGUMENTS

Sequence:
1. Read `manifest.yaml`. Refuse if missing or if `workflow-planner` hasn't
   completed with user approval.
2. **Construction Phase Entry Checkpoint**:
   audit.md has Inception entries; aidlc-state.md Current Stage correct;
   `aidlc-docs/construction/plans/` exists; `<run-id>-execution-plan.md` loaded.
3. **Pre-Build Step 0 — Skill Sync** (once, before any unit is spawned):
   a. Run sync:
      ```bash
      python3 aidlc-scripts/factory_skill_sync.py sync
      ```
   b. Run select:
      ```bash
      python3 aidlc-scripts/factory_skill_sync.py select --output json
      ```
   c. Log to audit.md with resolved skills and warnings.
4. **Topo-sort `manifest.units[]`** by `depends_on` into layers.
5. **For each layer (sequential)**, run the parallel construction protocol:
   a. **Pre-flight per unit (sequential)** — budget gate, lock acquire
      (`factory_conflict.py acquire`), AST snapshot, knowledge query, input handoff.
   b. **Three sub-stages, parallel per sub_stage** — `plan` → `generated` → `approved`:
     - Delegate to N parallel `code-generator` subagents (N ≤ 4)
     - Per-unit post-processing: validate output with `--strict`
       (`factory_validate.py code-generator.output.v1.json <handoff> --strict`),
       AST drift check (`factory_conflict.py check-symbols`), budget deduct
     - Consolidated approval gate (plan + generated only)
   c. **Build & Test parallel** — delegate to N parallel `build-test-agent` subagents
   d. **Release locks** — `factory_conflict.py release` per unit
   e. **Per-unit commits** — after consolidated approval gate clears
6. After all layers: set `Current Stage: CONSTRUCTION - Complete`.
7. **Present + offer next step**: `/factory-review <RUN_ID_LITERAL>`

## Concurrency
- Max 4 concurrent subagents per layer.
- If your tool doesn't support parallel delegation, run sequentially.

## Conflict resolution
Escalation-only. On path collision or interface drift, surface to user.
Full protocol: `.other/agents/cross-cutting/conflict-resolver.md`.
