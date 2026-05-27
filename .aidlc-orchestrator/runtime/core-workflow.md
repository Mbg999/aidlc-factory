# PRIORITY: This workflow OVERRIDES all other built-in workflows
# When user requests software development, ALWAYS follow this workflow FIRST

## Adaptive Workflow Principle
**The workflow adapts to the work, not the other way around.**
Assesses: user intent, codebase state, complexity, risk.

## MANDATORY: Auto-Commit on Approval ONLY
**CRITICAL**: Commits fire ONLY after an EXPLICIT user approval signal — never on stage completion alone, never on `status: complete` from an agent.

Approval signals are user messages containing: `approve`, `approved`, `go ahead`, `continue`, `next`, `lgtm`, `ship it`, `proceed`, `dale`, `sí`, or equivalent affirmative response to a `needs_human` gate. Silence or ambiguous responses are NOT approval.

When (and only when) an approval signal arrives:
```bash
git add -A && git commit -m "<type>(<scope>): <description>"
```
Types: `docs` (plans/requirements), `feat` (code), `build` (build/test).
Scope: command/stage in kebab-case (e.g. `requirements-analysis`, `workflow-planning`, `auth-unit`). If git fails, log warning and continue.

**Anti-pattern to reject**: committing on `status: complete` from an intermediate stage (e.g. `docs(story-writer): create user stories and personas` fired before the user has reviewed/approved the plan that consumes those stories). The plan-stage approval gate is the commit trigger — story-writer's output rides along inside that commit.

**Multi-stage commands**: `/factory-plan` may run story-writer → workflow-planner → unit-decomposer internally. ONE commit fires at command boundary after the user approves the workflow-planner plan, covering everything in the working tree.

---

# INCEPTION PHASE
Purpose: WHAT to build. Stages: Workspace Detection, Reverse Engineering (cond), Requirements Analysis, User Stories (cond), Workflow Planning, Application Design (cond), Units Generation (cond).

## Workspace Detection (ALWAYS)
Classify workspace → detect greenfield/brownfield → scan tech stack → determine next phase.

## Reverse Engineering (CONDITIONAL — brownfield, no prior artifacts)
Produce architecture docs, component inventory, API docs, tech stack from existing codebase.

## Requirements Analysis (ALWAYS — adaptive depth)
Analyze → ask questions → produce requirements doc → wait for approval.

## Workflow Planning (ALWAYS)
Plan phases → decompose tasks → produce execution plan → wait for approval.

---

# 🟢 CONSTRUCTION PHASE
Purpose: HOW to build.

## Entry Checkpoint
Before first Construction stage: verify audit.md has all Inception entries, state file is correct.

## Per-unit loop
Functional Design → NFR Requirements → NFR Design → Infrastructure Design → Code Generation.
Code Gen: plan → implement (TDD thin slices) → self-review → wait for approval.
Build & Test: run build → run tests → debug if failures → produce instructions → wait for approval.

---

# 🟡 OPERATIONS PHASE
Placeholder for deployment, monitoring, incident response.

## MANDATORY: State Tracking
- **Current Stage**: Update after EVERY stage completion. Never leave pointing to an earlier stage.
- **Stage Progress**: Mark `[x]` with date same interaction. MUST match audit.md.
- **Plan checkboxes**: Mark `[x]` same interaction as completion.
- Log all user input with ISO8601 in `audit.md`. Timestamps MUST be chronological.

Directory: `aidlc-docs/{inception,construction,operations}/`. App code stays in workspace root.

<!-- AIDLC-ORCHESTRATOR-POINTER -->
## AIDLC Orchestrator (multi-agent factory mode)

This project ships with the AIDLC orchestrator. To run the multi-agent factory, use the `/factory-*` slash commands:

- `/factory-onboarding` — guided tour of the orchestrator system
- `/factory-code-tour` — guided human tour of any codebase: architecture, key flows, conventions
- `/factory-help [command]` — quick command reference
- `/factory-state <run-id>` — current stage, next step, budget, timeline
- `/factory-self <task>` — run the orchestrator on its own codebase
- `/factory-spec <feature>` — workspace scout + requirements + plan
- `/factory-plan <run-id>` — decompose plan into per-unit specs
- `/factory-build <run-id>` — layer-parallel code generation with locks + AST checks
- `/factory-review <run-id>` — parallel reviewer pool (code, security, performance, simplifier)
- `/factory-ship <run-id>` — release notes, ADRs, CI/CD wiring, CHANGELOG, migration plan
- `/factory-resume <run-id>` — resume interrupted run (or adopt legacy `aidlc-docs/`)
- `/factory-replay <run-id> --from <stage>` — re-run from a specific stage

Roles, contracts, budgets, and parallelism rules: see `.claude/agents/orchestrator.md`,
`.aidlc-orchestrator/contracts/`, and `.aidlc-orchestrator/budgets/default.yaml`.
Design rationale and phase plan: `ORCHESTRATOR-PLAN.md` in the AIDLC source repo.
