# `/factory-plan` — Phase 1 plan

PRIORITY: P2

Inception phase, post-requirements. Produces the execution plan and
(optional) decomposes into units.

Assume `<run-id>` points at an existing manifest. If missing, refuse
("run not found — start with `/factory-spec` first").

1. **Story Writer (conditional)** — skip when ANY of:
   - `manifest.skip_stages[]` contains `story-writer` (set by ComplexityGov)
   - `requirements-analyst` output's `request_classification.scope` ∉ `{Multiple Components, System-wide, Cross-system}`
   - The user request does not involve user-facing flows

   When skipping, follow complexity-gate skip enforcement. Otherwise execute
   `stage/story-writer.md` inline per the [post-execution loop](spawn-loop.md).
   Predecessor: requirements-analyst output.

   > **Cookbook**: The story-writer loads `ai-architecture-cookbook` (`search_standards`) to align user stories with relevant architecture standards before passing to the planner. Read `.aidlc-orchestrator/runs/<run-id>/cookbook-context.json` if present and pass its contents as `context` to cookbook MCP calls.

2. **Application Designer (conditional)** — skip when ANY of:
    - `manifest.skip_stages[]` contains `application-designer`
    - The request scope is single-component AND involves no new interfaces/components
    - The user explicitly provides an existing design

    When skipping, log `[Skip] application-designer` to audit. Otherwise execute
    `stage/application-designer.md` inline per the [post-execution loop](spawn-loop.md).

    > **Two-pass execution**: application-designer has an integrated two-pass flow
    > (Pass 1: questions → `needs_human` → wait for answers → Pass 2: generate
    > 5 design artifacts). This mirrors the requirements-analyst two-pass pattern
    > but is handled entirely within the agent — the orchestrator surfaces the
    > `needs_human` gate with `needs_user_input: true` and re-spawns on answer.

    Predecessors: requirements + (if present) stories + (if brownfield) reverse engineering.

3. **Workflow Planner (always)** — `model: opus`. Required. Execute
    `stage/workflow-planner.md` inline per the [post-execution loop](spawn-loop.md).
    Predecessors: requirements + (if present) stories + (if present) application-design artifacts. The planner emits
   `status: needs_human` after producing the plan; on user response, call
   `emit_audit_block` per [`audit-block.protocol.md` § workflow-planner gate](../contracts/audit-block.protocol.md).

   > **Cookbook**: The workflow-planner loads `ai-architecture-cookbook` (`recommend_workflow(mode: 'audit')`) to suggest architecture patterns the plan must cover, tagged with cookbook standard IDs. Read `.aidlc-orchestrator/runs/<run-id>/cookbook-context.json` if present and inject the `techStack`, `scale`, `compliance`, and `previous_decisions` fields as `context` to the `recommend_workflow` call.

3.5. **Pre-mortem visibility check (defensive guard)** — run after Workflow Planner output is received:
   - Locate the `skill_compliance[]` row for `requirements-intelligence` in `workflow-planner.output.yaml`.
     If MISSING → append `[PlanPreMortem] missing — workflow-planner contract violation: no requirements-intelligence row in skill_compliance` to `audit_entries[]` and continue (do NOT halt).
   - Locate any `audit_entries[]` bullet starting with `[PlanPreMortem]`.
     If the `skill_compliance[]` row is present but no `[PlanPreMortem]` bullet exists → append `[PlanPreMortem] orphan compliance row — workflow-planner emitted skill_compliance without matching audit_entry` to `audit_entries[]` and continue.
   - These guards exist because the workflow-planner contract requires DUAL emission (compliance row + matching audit bullet); the orchestrator must log any violation so it appears in `audit.md` instead of being silently swallowed.

4. **Unit Decomposer (conditional)** — skip when ANY of:
   - `manifest.skip_stages[]` contains `unit-decomposer` (set by ComplexityGov)
   - The approved plan enumerates < 2 units AND requirements do not call out distinct services/components

   When skipping due to ComplexityGov, follow complexity-gate skip enforcement.
   Otherwise execute `stage/unit-decomposer.md` inline per the [post-execution loop](spawn-loop.md).

   > **Cookbook**: The unit-decomposer loads `ai-architecture-cookbook` (`get_decision_tree`) to ensure decomposed units carry architecture-standard context for each domain they touch. Read `.aidlc-orchestrator/runs/<run-id>/cookbook-context.json` if present to incorporate the project's tech stack and previous decisions into the decomposition.

5. **Approval gate** — present the full set of artifacts produced:
   - Plan file path (show key sections)
   - Unit decomposition (if run): list of units with descriptions
   - Stories and personas (if run)
   - Application design artifacts (if run)
   - `Pre-mortem:` line from `workflow-planner.output.skill_compliance[].requirements-intelligence`:
     - `Pre-mortem: PASS — <N> plan-risk question(s)` (when status=PASS)
     - `Pre-mortem: N/A — <evidence>` (when status=N/A, e.g. trivial plan)
     - `Pre-mortem: MISSING — workflow-planner contract violation` (when row absent)
   - Skill compliance table

   Never omit the `Pre-mortem:` line. The user must see it.

   Wait for user response:
   - **Approve / LGTM / Continue** → proceed to Step 6 (auto-commit + suggest next command).
   - **Request changes** → re-run the relevant stage (workflow-planner or unit-decomposer) with revision context. Do NOT auto-commit until user approves.
   - **Cancel** → mark run as cancelled, stop.

6. **Auto-commit + present next**

   On approval:
   ```bash
   git add -A && git commit -m "docs(workflow-planning): complete workflow planning"
   ```
   Update state.

   Present completion + offer `/factory-build <run-id>` (MUST substitute the
   actual run_id for `<run-id>` — e.g. `/factory-build 2026-05-23T13-10-58Z-dragon-ball-z-app`).
   Do NOT auto-execute `/factory-build`.

> **Framework skills** are synced at `/factory-build` Pre-Build Step 0, not here.
> Plan stages use `.agents/custom-skills/` process skills only.
