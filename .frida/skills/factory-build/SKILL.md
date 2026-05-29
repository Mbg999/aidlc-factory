---
name: factory-build
description: Run AIDLC construction (per-unit code generation + build/test) for an existing run. Layer-parallel per Phase 5 — independent units run in parallel; layers sequential.
---

# factory-build — AIDLC Construction

Adopt the role from `.aidlc-orchestrator/agents/orchestrator.md` and execute the
`/factory-build <run-id>` sequence (layer-parallel per Phase 5).

**Run id:** the run-id provided by the user.

Key rules:
- You OWN `aidlc-docs/audit.md` and `aidlc-docs/aidlc-state.md` — stage agents do NOT modify these.
- Append audit entries after each stage and gate.
- Update `aidlc-docs/aidlc-state.md` Current Stage and Stage Progress after each stage.

Sequence:
1. Read `manifest.yaml`. Refuse if missing or if `workflow-planner` hasn't
   completed with user approval.
 2. **Construction Phase Entry Checkpoint** — verify audit.md has Inception entries;
    aidlc-state.md Current Stage correct; then create `aidlc-docs/construction/plans/`,
    `aidlc-docs/construction/design/`, `aidlc-docs/construction/build-and-test/`
    via `mkdir -p` (safe if already exist); execution plan loaded.
3. **Pre-Build Step 0 — Skill Sync** (once, before any unit is spawned):
   a. Determine tech stack from `manifest.yaml` -> `tech_stack[]` and `project_type`.
      Check `aidlc-docs/requirements/requirements.md` for explicitly named technologies.
   b. Build `--tech` argument from tech_stack package names.
   c. Run sync:
      ```bash
      python3 aidlc-scripts/factory_skill_sync.py sync${TECH_FLAGS:+ --tech "$TECH_FLAGS"}
      ```
      Capture stdout. Each `[Sync]` line goes verbatim into audit.md under `[Skills]` prefix.
   d. Run select:
      ```bash
      python3 aidlc-scripts/factory_skill_sync.py select --output json
      ```
      Parse JSON -> store `skill_paths_resolved` list in `manifest.yaml`.
   e. Log to audit.md — use actual data from select's JSON output:
      ```
      [Skills] resolved <N> skills: <name-list>
      [Skills] warnings: <each entry from result.warnings[] or "none">
      ```
      If sync was skipped and select's warnings don't mention it, append:
      `[Skills] WARN: sync was skipped — see [Sync] block above`.
4. **Topo-sort `manifest.units[]`** by `depends_on` into layers.
   Layer 0 = no deps; Layer N = deps all in layers < N. Monolith -> single virtual unit.
   Append audit block: `CONSTRUCTION - UNIT GRAPH` with layer summary.
5. **For each layer (sequential)**:
   a. **Pre-flight per unit (sequential, cheap)** — budget gate, lock acquire
      (`factory_conflict.py acquire`), AST snapshot (Python only), knowledge
      query, build+validate input handoff.
   b. **Three sub-stages, parallel per sub_stage** — `plan` -> `generated` -> `approved`:
      - Single message with N parallel `Task(subagent_type=code-generator, ...)` calls (N = active set, <= 4)
      - Wait for all
      - Per-unit post-processing: validate output with `--strict` (`factory_validate.py`),
        AST drift check (`factory_conflict.py check-symbols`), budget deduct,
        knowledge save, **audit append**
      - Surface any drift conflicts OR strict-validation failures BEFORE the approval gate
      - On user decision, log to audit:
        ```bash
        python3 aidlc-scripts/factory_run.py emit_audit_block <run-id> \
            --evt user_decision --stage code-generator --phase CONSTRUCTION \
            --label "User Decision (code-generator <sub_stage>)" \
            --field decision=<approve|reject|cancel> --field sub_stage=<plan|generated> \
            --field rejected_units="<csv>" \
            --bullet "[User] <summary per unit>"
        ```
      - Consolidated approval gate (plan + generated only)
   c. **Build & Test parallel** — single message with N parallel
      `Task(subagent_type=build-test-agent, ...)` calls; per-unit
      post-processing with audit append; consolidated approval gate.
      On user decision, log to audit:
      ```bash
      python3 aidlc-scripts/factory_run.py emit_audit_block <run-id> \
          --evt user_decision --stage build-test-agent --phase CONSTRUCTION \
          --label "User Decision (layer <n> build/test)" \
          --field decision=<approve|reject|amend> --field layer=<n> \
          --bullet "[User] <summary>"
      ```
   d. **Release locks** — `factory_conflict.py release` per unit. Always
      release, even on failure.
   e. **Per-unit commits** — only after the consolidated approval gate clears.
6. After all layers:
   - Update `aidlc-docs/aidlc-state.md`:
     - Set `Current Stage: CONSTRUCTION — Complete`
     - Mark all construction stages as completed in Stage Progress
   - Log construction completion to audit:
     ```bash
     python3 aidlc-scripts/factory_run.py emit_audit_block <run-id> \
         --evt orchestrator_note --phase CONSTRUCTION \
         --label "Construction Complete" \
         --field summary="All layers completed: <N> units generated, built, and tested" \
         --bullet "[Construction] <summary>"
     ```
7. **Offer next step:** Run `python3 aidlc-scripts/factory_run.py status <run-id> --next-cmd`
   to get the ready-to-paste command, OR format manually as
   `/factory-review <RUN_ID_LITERAL>` with the actual run_id.
   **Never present `<run-id>` literally to the user.**

**Concurrency cap: 4.** If a layer has > 4 units, batch them within the layer.

**Conflict resolution**: escalation-only. On path collision or interface drift,
surface to user; user re-plans, manually merges, or cancels.

Hard rules from `.aidlc-orchestrator/agents/orchestrator.md` apply.
