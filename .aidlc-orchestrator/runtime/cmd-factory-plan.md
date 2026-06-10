# `/factory-plan` — Phase 1 plan

PRIORITY: P2

Inception phase, post-requirements. Produces the execution plan and
(optional) decomposes into units.

**1. Validate stage prerequisites (MANDATORY):**
   ```bash
   python3 aidlc-scripts/stage_gate.py check <run-id> workflow-planner
   ```
   Exit 0 → continue. Exit 1 → **HALT**. Do NOT proceed.

   Also read `manifest.yaml` for the run. Refuse if missing or if the run is not
   past `requirements-analyst`.

Assume `<run-id>` points at an existing manifest. If missing, refuse
("run not found — start with `/factory-spec` first").

1. **Story Writer (conditional)** — skip when ANY of:
   - `manifest.skip_stages[]` contains `story-writer` (set by ComplexityGov)
   - `requirements-analyst` output's `request_classification.scope` ∉ `{Multiple Components, System-wide, Cross-system}`
   - The user request does not involve user-facing flows

    When skipping, follow complexity-gate skip enforcement. Otherwise execute
    `stage/story-writer.md` inline per the [post-execution loop](spawn-loop.md).
    Predecessor: requirements-analyst output.

    **Context Injection**: Before spawning, generate the context snapshot:
    ```bash
    python3 aidlc-scripts/factory_context_builder.py <run-id> --depth auto --format compact --output .aidlc-orchestrator/runs/<run-id>/context-snapshot.yaml
    ```
    **Depth**: `auto` — with 2 completed stages (workspace-scout, requirements-analyst), this resolves to `standard` (~800 tokens). Includes requirements decisions and project profile.
    Inject into the story-writer input handoff under `context_snapshot:`.

    > **Cookbook**: The story-writer loads `ai-architecture-cookbook` (`search_standards`) to align user stories with relevant architecture standards before passing to the planner. Read `.aidlc-orchestrator/runs/<run-id>/cookbook-context.json` if present and pass its contents as `context` to cookbook MCP calls.

2. **Application Designer (conditional)** — skip when ANY of:
    - `manifest.skip_stages[]` contains `application-designer`
    - The request scope is single-component AND involves no new interfaces/components
    - The user explicitly provides an existing design

    When skipping, log `[Skip] application-designer` to audit. Otherwise execute
    `stage/application-designer.md` inline per the [post-execution loop](spawn-loop.md).

    **Context Injection**: Before spawning, regenerate the context snapshot:
    ```bash
    python3 aidlc-scripts/factory_context_builder.py <run-id> --depth auto --format compact --output .aidlc-orchestrator/runs/<run-id>/context-snapshot.yaml
    ```
    **Depth**: `auto` — resolves to `standard` or `comprehensive` based on completed stage count. Includes requirements, stories (if run), and any reverse-engineering artifacts.
    Inject into the application-designer input handoff under `context_snapshot:`.

    > **Two-pass execution**: application-designer has an integrated two-pass flow
    > (Pass 1: questions → `needs_human` → wait for answers → Pass 2: generate
    >  5 design artifacts). This mirrors the requirements-analyst two-pass pattern
    > but is handled entirely within the agent — the orchestrator surfaces the
    > `needs_human` gate with `needs_user_input: true` and re-spawns on answer.

    Predecessors: requirements + (if present) stories + (if brownfield) reverse engineering.

3. **Workflow Planner (always)** — `model: opus`. Required. Execute
    `stage/workflow-planner.md` inline per the [post-execution loop](spawn-loop.md).
    Predecessors: requirements + (if present) stories + (if present) application-design artifacts. The planner emits
   `status: needs_human` after producing the plan; on user response, call
    `emit_audit_block` per [`audit-block.protocol.md` § workflow-planner gate](../contracts/audit-block.protocol.md).

    **Context Injection**: Before spawning, regenerate the context snapshot:
    ```bash
    python3 aidlc-scripts/factory_context_builder.py <run-id> --depth auto --format compact --output .aidlc-orchestrator/runs/<run-id>/context-snapshot.yaml
    ```
    **Depth**: `auto` — typically resolves to `standard` or `comprehensive` for workflow planning. Includes all prior decisions, requirements, and design artifacts.
    Inject into the workflow-planner input handoff under `context_snapshot:`.

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

   **Context Injection**: Before spawning, regenerate the context snapshot:
   ```bash
   python3 aidlc-scripts/factory_context_builder.py <run-id> --depth auto --format compact --output .aidlc-orchestrator/runs/<run-id>/context-snapshot.yaml
   ```
   **Depth**: `auto` — typically resolves to `standard` or `comprehensive`. Includes approved plan, requirements, and design artifacts.
   Inject into the unit-decomposer input handoff under `context_snapshot:`.

   > **Cookbook**: The unit-decomposer loads `ai-architecture-cookbook` (`get_decision_tree`) to ensure decomposed units carry architecture-standard context for each domain they touch. Read `.aidlc-orchestrator/runs/<run-id>/cookbook-context.json` if present to incorporate the project's tech stack and previous decisions into the decomposition.

5. **Approval gate (structured contract)** — before presenting, build the approval handoff:

   1. **Construct** `.aidlc-orchestrator/runs/<run-id>/handoffs/approval.input.yaml` from the stage outputs:
      ```yaml
      stage: workflow-planner
      run_id: <run-id>
      title: "Execution Plan — Approval Gate"
      units:
        - label: "Execution Plan"
          tasks:
            - id: "PLAN"
              description: "Complete workflow plan with task breakdown and acceptance criteria"
              status: complete
        - label: "Unit Decomposition"
          tasks:
            - id: "DECOMP"
              description: "Per-unit specs with dependency matrix"
              status: complete
      artifacts:
        - path: "aidlc-docs/inception/plans/<run-id>-execution-plan.md"
          kind: plan
          description: "Execution plan with task breakdown"
      skill_compliance:
        - skill: "requirements-intelligence"
          status: "<PASS|N/A|MISSING>"
          evidence: "Pre-mortem: <result>"
        - skill: "planning-and-task-breakdown"
          status: PASS
      resolution:
        options: [approve, request_changes, cancel]
        note_prompt: "Describe what changes are needed"
      next_command:
        command: "/factory-build <run-id>"
        description: "Generate code and run tests"
      context: "<pre-mortem line + skill compliance summary>"
      ```
      Include optional artifacts (stories, personas, design artifacts) if they were produced.

   2. **Validate** against `.aidlc-orchestrator/contracts/approval.input.v1.json`. Do NOT skip validation.

   3. **Present** using the Structured Approval Format. Never omit the `Pre-mortem:` line.
   
   **Explicitly ask the user for approval.** Do NOT proceed without an explicit approval signal.

   Wait for user response:
   - **Approve / LGTM / Continue** → proceed to Step 6 (auto-commit + suggest next command).
   - **Request changes** → re-run the relevant stage (workflow-planner or unit-decomposer) with revision context. Do NOT auto-commit until user approves.
   - **Cancel** → mark run as cancelled, stop.

6. **Auto-commit + present next**

   **On EXPLICIT user approval only:**
   ```bash
   git add -A && git commit -m "docs(workflow-planning): complete workflow planning"
   ```
   Update state.

   2. **Record** `approval.output.yaml` with decision, timestamp, and commit_sha. Validate against `.aidlc-orchestrator/contracts/approval.output.v1.json`.

   **If the user did not approve, do NOT run this step. Do NOT commit.**

   Present completion with the **literal next command** (substitute the actual run_id, never output `<run-id>` as placeholder text):
   ```
   Run complete: <run-id>

   Next command: /factory-build <run-id>
   ```
   Do NOT auto-execute `/factory-build`.

> **Framework skills** are synced at `/factory-build` Pre-Build Step 0, not here.
> Plan stages use `.agents/custom-skills/` process skills only.

---

## Hard rules

- Hard rules from the orchestrator apply.
