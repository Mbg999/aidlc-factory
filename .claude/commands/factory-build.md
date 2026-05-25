---
description: Run AIDLC construction (per-unit code generation + build/test) for an existing run. Layer-parallel per Phase 5 — independent units run in parallel; layers sequential.
argument-hint: <run-id>
---

You are now the AIDLC orchestrator.

Adopt the role from @.claude/agents/orchestrator.md and execute the
`/factory-build <run-id>` sequence (now **layer-parallel** per Phase 5).

**Run id:** $ARGUMENTS

Sequence:
1. Read `manifest.yaml`. Refuse if missing or if `workflow-planner` hasn't
   completed with user approval.
2. **Construction Phase Entry Checkpoint** (per core-workflow.md MANDATORY):
   audit.md has Inception entries; aidlc-state.md Current Stage correct;
    `aidlc-docs/construction/plans/` exists; `<run-id>-execution-plan.md` loaded.
3. **Pre-Build Step 0 — Skill Sync** (once, before any unit is spawned):
   a. Run sync:
      ```bash
      python3 aidlc-scripts/factory_skill_sync.py sync
      ```
      Capture stdout. Each `[Sync]` line is the single source of truth for the
      audit — copy them verbatim into audit.md under `[Skills]` prefix
      (e.g. `[Sync] SKIPPED — Node.js v18 ...` becomes `[Skills] SKIPPED — Node.js v18 ...`).
      On non-zero exit or Node.js missing: skill_sync.py prints a structured
      `[Sync] SKIPPED + WARN:` block — surface those lines as-is. Skill failure
      never blocks a build (pre-shipped custom-skills still apply).
   b. Run select:
      ```bash
      python3 aidlc-scripts/factory_skill_sync.py select --output json
      ```
      Parse JSON → store `skill_paths_resolved` list in `manifest.yaml`. Include
      this list in every subsequent stage input handoff YAML for this run.
   c. Log to audit.md — use the actual data from select's JSON output:
      ```
      [Skills] resolved <N> skills: <name-list>
      [Skills] warnings: <each entry from result.warnings[] on its own line, or "none">
      ```
      **Honesty rule:** if `[Sync] SKIPPED` appeared in step (a) but select's
      `warnings[]` does not mention it, append a defensive
      `[Skills] WARN: sync was skipped — see [Sync] block above` line.
      Never emit `[Skills] warnings: none` while a `[Sync] SKIPPED` bullet
      sits above it.
4. **Topo-sort `manifest.units[]`** by `depends_on` into layers. Layer 0 = no
   deps; Layer N = deps all in layers < N. Monolith → single virtual unit.
5. **For each layer (sequential)**, run the parallel construction protocol:
   a. **Pre-flight per unit (sequential, cheap)** — budget gate, lock acquire
      (`factory_conflict.py acquire`), AST snapshot (Python only), knowledge
      query, build+validate input handoff.
   b. **Three sub-stages, parallel per sub_stage** —
      `plan` → `generated` → `approved`. For each:
        - Single message with N parallel `Task(subagent_type=code-generator, ...)`
          calls (N = active set, ≤ 4)
        - Wait for all
        - Per-unit post-processing: validate output **with `--strict`**
          (`factory_validate.py code-generator.output.v1.json <handoff> --strict`
          — enforces plan-artifact existence on disk for non-fast_path runs;
          catches silent skip of construction plan), AST drift check
          (`factory_conflict.py check-symbols`), budget deduct, knowledge save,
          audit append
        - Surface any drift conflicts OR strict-validation failures BEFORE the approval gate
        - Consolidated approval gate (plan + generated only)
   c. **Build & Test parallel** — single message with N parallel
      `Task(subagent_type=build-test-agent, ...)` calls; per-unit
      post-processing; consolidated approval gate.
   d. **Release locks** — `factory_conflict.py release` per unit. Always
      release, even on failure.
   e. **Per-unit auto-commits** — `feat(<unit>): generate <unit> code` and
      `build(<unit>): complete build and test`.
6. After all layers: set `Current Stage: CONSTRUCTION - Complete`.
7. **Present + offer next step (substitute `<run-id>` literally):** Run
   `python3 aidlc-scripts/factory_run.py status <run-id> --next-cmd` to get
   the ready-to-paste command, OR format manually as `/factory-review <RUN_ID_LITERAL>`
   — replace `<RUN_ID_LITERAL>` with the actual run_id (e.g.
   `2026-05-22T10-00-00Z-jwt-auth`). **Never present `<run-id>` literally to the user.**

Hard rules from @.claude/agents/orchestrator.md apply.

**Concurrency cap: 4.** If a layer has > 4 units, batch them (4 at a time)
within the layer.

**Conflict resolution (Phase 5)**: escalation-only. On path collision or
interface drift, surface to user; user re-plans, manually merges, or cancels.
Full protocol: `.claude/agents/cross-cutting/conflict-resolver.md`.
