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

2. **Workflow Planner (always)** — `model: opus`. Required. Execute
   `stage/workflow-planner.md` inline per the [post-execution loop](spawn-loop.md).
   Predecessors: requirements + (if present) stories. The planner emits
   `status: needs_human` after producing the plan; on user response, call
   `emit_audit_block` per [`audit-block.protocol.md` § workflow-planner gate](../contracts/audit-block.protocol.md).

   > **Cookbook**: The workflow-planner loads `ai-architecture-cookbook` (`recommend_workflow(mode: 'audit')`) to suggest architecture patterns the plan must cover, tagged with cookbook standard IDs. Read `.aidlc-orchestrator/runs/<run-id>/cookbook-context.json` if present and inject the `techStack`, `scale`, `compliance`, and `previous_decisions` fields as `context` to the `recommend_workflow` call.

3. **Unit Decomposer (conditional)** — skip when ANY of:
   - `manifest.skip_stages[]` contains `unit-decomposer` (set by ComplexityGov)
   - The approved plan enumerates < 2 units AND requirements do not call out distinct services/components

   When skipping due to ComplexityGov, follow complexity-gate skip enforcement.
   Otherwise execute `stage/unit-decomposer.md` inline per the [post-execution loop](spawn-loop.md).

   > **Cookbook**: The unit-decomposer loads `ai-architecture-cookbook` (`get_decision_tree`) to ensure decomposed units carry architecture-standard context for each domain they touch. Read `.aidlc-orchestrator/runs/<run-id>/cookbook-context.json` if present to incorporate the project's tech stack and previous decisions into the decomposition.

4. Auto-commit `docs(workflow-planning): complete workflow planning` and update
   state. Present completion + offer `/factory-build <run-id>` (MUST substitute the
   actual run_id for `<run-id>` — e.g. `/factory-build 2026-05-23T13-10-58Z-dragon-ball-z-app`).
   Also show the plan file path so the user can inspect it before approving.

> **Framework skills** are synced at `/factory-build` Pre-Build Step 0, not here.
> Plan stages use `.agents/custom-skills/` process skills only.
