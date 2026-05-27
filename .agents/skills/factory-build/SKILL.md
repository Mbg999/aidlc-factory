---
name: factory-build
description: Run AIDLC construction (per-unit code generation + build/test) for an existing run. Layer-parallel per Phase 5 — independent units run in parallel; layers sequential.
---

# factory-build — AIDLC Construction

Adopt the role from `.aidlc-orchestrator/agents/orchestrator.md` and execute the
`/factory-build <run-id>` sequence (layer-parallel per Phase 5).

**Run id:** the run-id provided by the user.

Sequence:
1. Read `manifest.yaml`. Refuse if missing or if `workflow-planner` hasn't
   completed with user approval.
2. **Construction Phase Entry Checkpoint** — audit.md has Inception entries;
   aidlc-state.md Current Stage correct; execution plan exists.
3. **Pre-Build Step 0 — Skill Sync**:
   a. Determine tech stack from `manifest.yaml` -> `tech_stack[]` and `project_type`.
   b. Build `--tech` argument from tech_stack package names.
   c. Run sync:
      ```bash
      python3 aidlc-scripts/factory_skill_sync.py sync${TECH_FLAGS:+ --tech "$TECH_FLAGS"}
      ```
   d. Run select:
      ```bash
      python3 aidlc-scripts/factory_skill_sync.py select --output json
      ```
   e. Log to audit.md with resolved skills and warnings.
4. **Topo-sort `manifest.units[]`** by `depends_on` into layers.
5. **For each layer (sequential)**:
   a. Pre-flight per unit: budget gate, lock acquire, AST snapshot, knowledge query.
   b. Three sub-stages in parallel: `plan` -> `generated` -> `approved`.
   c. **Build & Test parallel** — per-unit build-test-agent runs.
   d. Release locks via `factory_conflict.py release`.
   e. Per-unit auto-commits.
6. After all layers: set `Current Stage: CONSTRUCTION - Complete`.
7. **Offer next step:** `/factory-review <RUN_ID_LITERAL>`

**Concurrency cap: 4.** Batch units within a layer if > 4.

**Conflict resolution**: escalation-only. On path collision or interface drift,
surface to user.

Hard rules from `.aidlc-orchestrator/agents/orchestrator.md` apply.
