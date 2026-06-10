# `/factory-build` — Phase 1 build

PRIORITY: P2

Construction phase. **Layer-parallel:** units are topologically sorted by
`depends_on`; each layer runs in parallel (≤ 4 concurrent); layers are
sequential. Locks (file-glob) acquired per-unit before spawn; AST symbol
drift detected post-spawn for Python files.

**1. Validate stage prerequisites (MANDATORY):**
   ```bash
   python3 aidlc-scripts/stage_gate.py check <run-id> code-generator
   ```
   Exit 0 → continue. Exit 1 → **HALT**. Do NOT proceed. Surface error to user
   with missing prerequisites list. This prevents agents from skipping mandatory
   stages (requirements-analyst, workflow-planner, etc.).

   Also read `manifest.yaml`. Refuse if missing or if `workflow-planner` hasn't
   completed with user approval.

**Construction Phase Entry Checkpoint** (run BEFORE first layer, per
core-workflow.md): verify audit.md has all Inception entries, state file
`Current Stage` is correct, `aidlc-docs/construction/plans/` exists, and
the execution plan is loaded.

## Pre-Build Step 0 — Skill Sync

Runs ONCE before any unit is spawned.

1. **Resolve techs** — intersect project tech_stack with autoskills supported techs:
   ```bash
   TECH=$(python3 aidlc-scripts/factory_skill_sync.py resolve-tech .aidlc-orchestrator/runs/<run-id>/manifest.yaml)
   ```
   This queries autoskills `--list-tech`, reads `manifest.workspace_state.tech_stack[]`,
   maps package names to tech IDs (e.g. `@angular/core` → `angular`), and outputs
   comma-separated matching techs. If output contains "no matching techs" or starts
   with "[", skip `--tech` — autoskills installs universal skills only.

2. **Sync** — install framework skills for the resolved techs:
   ```bash
   python3 aidlc-scripts/factory_skill_sync.py sync ${TECH:+--tech "$TECH"}
   ```
   Capture stdout → append `[Sync]` lines to audit.md under `[Skills]` prefix.
   On non-zero exit or Node.js missing: log warning, skip, continue. Skill sync
   never blocks build. If no `--tech` was passed, audit note:
   `[Skills] no matching techs — universal skills only`.

4. **Select** — resolve all installed skills for stage handoffs:
   ```bash
   python3 aidlc-scripts/factory_skill_sync.py select --output json
   ```
   Parse JSON → store in `manifest.yaml`:
   - `skill_paths_resolved` — all discovered skill paths (unfiltered)
   - `framework_skill_names` — framework skill names for `skills_required[]` injection

   When building per-stage handoffs in Step B.1, include ONLY the subset of
   `skill_paths_resolved[]` that matches `skills_required[]` for that stage agent,
   PLUS any conditional skills from [`project-profile.md`](project-profile.md) §65-78.

5. **Log** to audit.md:
   ```
   [Skills] resolved <N> skills: <name-list>
   [Skills] warnings: <list or "none">
   ```
   **Honesty rule:** if `[Sync]` was skipped but select's `warnings[]` doesn't
   mention it, append:
   ```
   [Skills] WARN: sync was skipped — see [Sync] block above
   ```
   Never emit `[Skills] warnings: none` while a sync skip sits above it.

## Pre-Build Step 0.5 — Prepare Token Bridge

Runs ONCE before any unit is spawned, when `manifest.project_profile.ui == true`.

1. **Resolve output directory** — use the per-run tokens directory:
   ```bash
   TOKENS_DIR=".aidlc-orchestrator/runs/<run-id>/tokens"
   ```

2. **Run Token Bridge prepare** — generates `tokens.css`, auto-detects Tailwind,
   copies `token-prompt.md`, and detects brownfield sources:
   ```bash
   python3 aidlc-scripts/factory_token_bridge.py prepare \
       --repo-root . \
       --output-dir "$TOKENS_DIR"
   ```
   The bridge handles these cases silently:
   - No `design-system/` exists → skip with warning (no tokens, no CSS)
   - Tailwind detected → also generates `tailwind.config.js`
   - Brownfield sources found → logs `design_system_source` in result JSON

3. **Store artifacts in manifest** — parse the JSON result and persist:
   ```bash
   python3 aidlc-scripts/factory_run.py set <run-id> \
       --field token_bridge_result=<result-json>
   ```

4. **Log to audit.md:**
   ```
   [TokenBridge] Prepared <N> artifact(s): <type-list>
   [TokenBridge] Tailwind: <detected|not-detected>
   [TokenBridge] Design source: <brownfield|greenfield|figma|stitch|none>
   ```

5. **Fallback**: if `prepare` returns empty artifacts (no tokens dir), log a
   warning and continue — the build proceeds without token enforcement.
   Token Bridge failure never blocks a build.

## Pre-Build Step 0.6 — Cookbook context load

**Cookbook**: Read `.aidlc-orchestrator/runs/<run-id>/cookbook-context.json` if present. For each unit's code-generator input handoff, inject the context's `techStack[]` so the code-generator's `recommend_workflow` and `query_standard` calls filter patterns to the project's tech stack (e.g., Prisma-specific repository patterns vs sqlx). Log: `[Cookbook] Context injected into <N> unit handoffs` or `[Cookbook] No context file found — tech stack filtering disabled`.

---

## Step A — Compute unit dependency waves

`factory_graph.py compute <run-id> --apply` (Kahn's algorithm over
`units_decomposed[].dependencies`; writes `manifest.unit_waves`,
`unit_wave_count`, `unit_max_parallelism`).

- Exit 1 (cycle) → log error, fall back to single sequential wave.
- No `unit-decomposer` output → synthesize `unit_waves: [["__monolith__"]]`.
- Validate against `shared/unit-graph.schema.json` (non-blocking warn only).

Emit `CONSTRUCTION - UNIT GRAPH` audit block. "Layer" = "wave".

## Step B — Per-layer execution

For each layer in order:

### B.1 — Sequential per-unit pre-flight (all before spawn)
1. **Budget gate**: `factory_run.py budget_gate <run-id> code-generator:<unit>`. Checks: ok / downshift / skip / halt.
2. Lock acquire: `factory_conflict.py acquire <run-id> code-generator:<unit> <locks>`. Default: `src/<unit>/**`, `tests/<unit>/**`. exit 1 = drop.
2. AST snapshot (Python): `factory_conflict.py snapshot <run-id> code-generator:<unit> <files>`.
3. Knowledge query: `mem_search` with unit tags; inject top-5 into `context_pointers[]`.
4. Build input handoff `code-generator.<unit>.input.yaml`:
   - Read `manifest.skill_paths_resolved` (full discovered set).
    - Apply conditional skill injection from [`project-profile.md`](project-profile.md) §65-78:
      read `manifest.project_profile`, add matching skills (e.g. `frontend-ui-engineering`
      when `ui: true`) to `skills_required[]`, resolve paths → merge into
      `skill_paths_resolved[]`.
    - **Framework skill injection**: add ALL entries from `manifest.framework_skill_names`
      to `skills_required[]` so framework skills (e.g. `react-best-practices`,
      `typescript-advanced-types`) are loaded by the code-generator.
    - **Cookbook integration**: when `architecture_cookbook_enabled` in manifest features
      is not explicitly `false` (defaults to `true`), add `ai-architecture-cookbook` to
      `skills_required[]` and merge its resolved path from `skill_paths_resolved[]`.
    - **Filter**: include only paths for skills referenced in `skills_required[]` plus
      context-enrichment skills (`codegraph-aware-exploration`, `context-engineering`).
      Discard paths for skills irrelevant to this stage.
    - **Inception plan tracking**: set `inception_plan_path` to
      `aidlc-docs/inception/plans/<run-id>-execution-plan.md` and set
      `inception_task_ids[]` to the list of task IDs from that plan whose `unit`
      field matches this unit (e.g. `["ING-T4", "ING-T5"]`). Parse the markdown
      task list — each task line has the form `- [ ] **<ID>** — <title>` with the
      unit either in a section header above it or inline as `(unit: <name>)`.
    - **Token Bridge artifacts**: when `manifest.project_profile.ui == true`, read
      `manifest.token_bridge_result.artifacts` and inject as `token_bridge_artifacts[]`
      in the handoff. This gives the code-generator direct paths to `tokens.css`,
      `tailwind.config.js` (if applicable), and `token-prompt.md`.
    - Validate against JSON Schema contract (`code-generator.input.v1.json`).

Active set = units that passed all gates.

### B.1.5 — Wave collision pre-flight (active set ≥ 2 only)
`factory_conflict.py check-wave <run-id> --wave-idx <N>`. `safe: true` → continue.
`safe: false` → drop colliding units to next wave. If wave empties → halt.

### B.2 — Code generator (three sub-stages, parallel per sub_stage)

**Context Injection (per unit, before each sub-stage)**:

For each unit, regenerate the context snapshot with `comprehensive` depth before building the input handoff:

```bash
python3 aidlc-scripts/factory_context_builder.py <run-id> --depth comprehensive --format compact --output .aidlc-orchestrator/runs/<run-id>/context-snapshot.yaml
```

**Depth**: `comprehensive` (~2000 tokens) — code-generator needs full timeline, handoff summaries, and all prior decisions to avoid contradicting earlier design.

Inject the snapshot into each unit's `code-generator.<unit>.input.yaml` under `context_snapshot:`. The code-generator MUST read this before planning to understand:
- What units have already been built (to avoid duplication)
- What decisions were made in requirements/design (to respect constraints)
- What skills are active (to apply correct patterns)

Code-generator runs `plan` → `generated` → `approved`. For each sub_stage:
1. Parallel `Task(subagent_type="code-generator", ...)` in ONE message (≤ 4).
2. Wait for all returns. Per-unit post-processing (any order):
    - **Validate output (strict)** — for every returned output handoff:
      ```bash
      python3 aidlc-scripts/factory_validate.py \
          .aidlc-orchestrator/contracts/code-generator.output.v1.json \
          <output-handoff-path> --strict
      ```
       `--strict` is MANDATORY: it enforces that any non-fast_path output with
       `sub_stage` in {`plan`, `generated`} declares a `kind: plan` artifact AND
       that the plan file exists on disk AND that the plan file has ZERO remaining
       unchecked `[ ]` checkboxes. This catches both the silent-skip failure
       where an agent claims `generated` without writing the plan, and the partial
       failure where an agent leaves tasks incomplete. On exit≠0: mark unit
       `blocked`, log stderr to audit.md, DO NOT advance the unit, surface BEFORE
       the gate.
     - AST drift check → budget deduct → knowledge save → audit append.
3. If AST drift conflict OR strict-validation failure written, surface BEFORE approval gate.
 4. **Approval gate (structured contract) — code-generator:**
    
    1. **Construct** `.aidlc-orchestrator/runs/<run-id>/handoffs/approval.code-generator.input.yaml` per unit:
       ```yaml
       stage: code-generator
       run_id: <run-id>
       title: "Code Generation — <unit-name> Approval"
       units:
         - label: "<unit-name>"
           tasks:
             - id: "GEN"
               description: "Generated code for <unit-name>"
               status: complete
       artifacts:
         - path: "src/<unit-name>/..."
           kind: source
           description: "Generated source files"
         - path: "tests/<unit-name>/..."
           kind: test
           description: "Generated tests"
       resolution:
         options: [approve, request_changes, cancel]
         note_prompt: "Describe what changes are needed"
       next_command:
         command: "/factory-build <run-id>"
         description: "Continue to build & test for this unit"
       context: "<AST drift check results + strict validation summary>"
       ```
    
    2. **Validate** against `.aidlc-orchestrator/contracts/approval.input.v1.json`. Do NOT skip validation.
    
    3. **Surface** ALL units using the Structured Approval Format. **Explicitly ask the user for approval.** Do NOT proceed without an explicit approval signal. User can approve all, reject specific units (re-plan with revised context), or cancel layer.

### B.3 — Build & test (parallel per unit, after all reach `approved`)

**Context Injection (per unit)**:

For each unit, regenerate the context snapshot:

```bash
python3 aidlc-scripts/factory_context_builder.py <run-id> --depth comprehensive --format compact --output .aidlc-orchestrator/runs/<run-id>/context-snapshot.yaml
```

**Depth**: `comprehensive` — build-test-agent needs full context to understand what was generated and what constraints apply.

Inject the snapshot into each unit's `build-test-agent.<unit>.input.yaml` under `context_snapshot:`.

Parallel `Task(subagent_type="build-test-agent", ...)` in ONE message (≤ 4).
Build input handoffs per B.1 Step 4 guidelines (filter to BTA-relevant skills only).
If `manifest.project_profile.ui == true`: add `browser-testing-with-devtools` to
`skills_required[]` and set `design_system_path` from `manifest.project_profile.design_system_path`
(mirrors code-generator Step B.1 pattern — see [`project-profile.md`](project-profile.md) §65-78).

Per-unit post-processing same as B.2.

**Approval gate (structured contract) — build-test-agent:**

1. **Construct** `.aidlc-orchestrator/runs/<run-id>/handoffs/approval.build-test.input.yaml` per unit:
   ```yaml
   stage: build-test-agent
   run_id: <run-id>
   title: "Build & Test — <unit-name> Approval"
   units:
     - label: "<unit-name>"
       tasks:
         - id: "BUILD"
           description: "Build and test completed for <unit-name>"
           status: complete
   artifacts:
     - path: "tests/<unit-name>/..."
       kind: test
       description: "Test results"
   resolution:
     options: [approve, request_changes, cancel]
     note_prompt: "Describe what changes are needed"
   next_command:
     command: "/factory-build <run-id>"
     description: "Continue to next layer or review"
   context: "<build_status> | <tests_passing>/<tests_total> tests | <coverage>% coverage"
   ```

2. **Validate** against `.aidlc-orchestrator/contracts/approval.input.v1.json`. Do NOT skip validation.

3. **Surface** all summaries. **Explicitly ask the user for approval.** Do NOT proceed without an explicit approval signal.

### B.4 — Release locks (always — leaks block future runs)
```bash
python3 aidlc-scripts/factory_conflict.py release <run-id> code-generator:<unit>
```

### B.5 — Per-unit commits (on explicit approval only)
After the build-test approval gate (B.3) accepts a unit:
```bash
git add -A && git commit -m "feat(<unit-name>): generate <unit> code"
git add -A && git commit -m "build(<unit-name>): complete build and test"
```
If any commit fails, log warning and continue.

For each approved unit, **record** `approval.output.yaml` with decision, timestamp, and commit_sha. Validate against `.aidlc-orchestrator/contracts/approval.output.v1.json`.

**If the user did not approve, do NOT run this step. Do NOT commit.**

## Step C — After all layers
- Set `Current Stage: CONSTRUCTION - Complete`.
- Present per-unit summary with key metrics (files changed, tests passing, coverage).
- Present the **literal next command** (substitute the actual run_id, never output `<run-id>` as placeholder text):
  ```
  Next command: /factory-review <run-id>
  ```
- Do NOT auto-execute `/factory-review`. Wait for the user to run it explicitly.

## Concurrency cap
Phase 5 honors cap of 4. Batch >4 units within a layer; lock acquire+release per batch.

---

## Hard rules

- Hard rules from the orchestrator apply.
- **Conflict resolution (Phase 5)**: escalation-only. On path collision or interface drift, surface to user; user re-plans, manually merges, or cancels. Full protocol: see the orchestrator's conflict-resolver agent.
