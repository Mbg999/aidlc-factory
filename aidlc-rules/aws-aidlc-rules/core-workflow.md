# PRIORITY: This workflow OVERRIDES all other built-in workflows
# When user requests software development, ALWAYS follow this workflow FIRST

## Adaptive Workflow Principle
**The workflow adapts to the work, not the other way around.**

The AI model intelligently assesses what stages are needed based on:
1. User's stated intent and clarity
2. Existing codebase state (if any)
3. Complexity and scope of change
4. Risk and impact assessment

## MANDATORY: Rule Details Loading
**CRITICAL**: When performing any phase, you MUST read and use relevant content from rule detail files. Check these paths in order and use the first one that exists, regardless of which AI coding tool is in use:
- `.aidlc/aidlc-rules/aws-aidlc-rule-details/` (canonical location — AI-assisted setup)
- `.aidlc-rule-details/` (flat layout — Cursor, Cline, Claude Code, GitHub Copilot, Windsurf, etc.)
- `aidlc-rules/aws-aidlc-rule-details/` (monorepo layout — rules committed at repo root)

All subsequent rule detail file references (e.g., `common/process-overview.md`, `inception/workspace-detection.md`) are relative to whichever rule details directory was resolved above.

**Common Rules**: ALWAYS load common rules at workflow start:
- Load `common/process-overview.md` for workflow overview and terminology
- Load `common/stage-conventions.md` for shared stage patterns (skills, questions, plans, approval)
- Load `common/session-continuity.md` for session resumption guidance
- Load `common/ascii-diagram-standards.md` for content validation and diagram rules
- Load `common/question-format-guide.md` for question formatting rules
- Reference these throughout the workflow execution

## MANDATORY: Extensions Loading (Context-Optimized)
**CRITICAL**: At workflow start, scan the `extensions/` directory recursively but load ONLY lightweight opt-in files — NOT full rule files. Full rule files are loaded on-demand after the user opts in.

**Loading process**:
1. List all subdirectories under `extensions/` (e.g., `extensions/security/`, `extensions/compliance/`)
2. In each subdirectory, load ONLY `*.opt-in.md` files — these contain the extension's opt-in prompt. The corresponding rules file is derived by convention: strip the `.opt-in.md` suffix and append `.md` (e.g., `security-baseline.opt-in.md` → `security-baseline.md`)
3. Do NOT load full rule files (e.g., `security-baseline.md`) at this stage

**Deferred Rule Loading**:
- During Requirements Analysis, opt-in prompts from the loaded `*.opt-in.md` files are presented to the user
- When the user opts IN for an extension, load the corresponding rules file (derived by naming convention) at that point
- When the user opts OUT, the full rules file is never loaded — saving context
- Extensions without a matching `*.opt-in.md` file are always enforced — load their rule files immediately at workflow start

**Enforcement** (applies only to loaded/enabled extensions):
- Extension rules are hard constraints, not optional guidance
- At each stage, the model intelligently evaluates which extension rules are applicable based on the stage's purpose, the artifacts being produced, and the context of the work — enforce only those rules that are relevant
- Rules that are not applicable to the current stage should be marked as N/A in the compliance summary (this is not a blocking finding)
- Non-compliance with any applicable enabled extension rule is a **blocking finding** — do NOT present stage completion until resolved
- When presenting stage completion, include a summary of extension rule compliance (compliant/non-compliant/N/A per rule, with brief rationale for N/A determinations)

**Conditional Enforcement**: Extensions may be conditionally enabled/disabled. See `inception/requirements-analysis.md` for the opt-in mechanism.

Runner resolution order for whether an extension is enabled (preference order):

1. Manifest-level default: If the agent manifest (`agents.yaml` or `agents.json`) for an extension contains `enabled_by_default: true`, treat that extension as enabled and load the full rule file automatically.
2. Repository run state: If the run contains `aidlc-docs/aidlc-state.md` with an explicit entry for the extension, follow that value (`enabled: true|false`).
3. Opt-in prompt: If neither manifest nor run state indicates a decision and an opt-in prompt file (`*.opt-in.md`) exists, present it and honor the user's answer. If no opt-in prompt exists, default to enforced (load the full rule file).

Always record the decision (enabled/disabled/auto-enabled) in `aidlc-docs/audit.md` and log any skips. 
## MANDATORY: Skills Integration

**CRITICAL**: Skills are the primary enforcement mechanism for quality, process, and best practices. Each stage declares required skills that MUST be loaded and followed. Skills are NOT optional guidance — they are structured workflows with verification gates.

### Skill Locations (search order, first-found wins)
- `<repo>/.agents/custom-skills/<skill-name>/SKILL.md` (project-specific, highest priority)
- `<repo>/.agents/skills/<skill-name>/SKILL.md` (repo-local, from installer)
- `~/.agents/skills/<skill-name>/SKILL.md` (user-global)

### Skill Anatomy (from addyosmani/agent-skills)
Every skill follows this structure:
- **Overview** — What the skill does
- **When to Use** — Triggering conditions
- **Process** — Step-by-step workflow (MUST be followed)
- **Common Rationalizations** — Excuses + rebuttals (MUST be checked)
- **Red Flags** — Signs something is wrong
- **Verification** — Evidence requirements (MUST be satisfied)

### Skill Execution Protocol (MANDATORY)
When a stage lists required skills:
1. **LOAD**: Read each `.agents/skills/<name>/SKILL.md`
2. **FOLLOW**: Execute the skill's Process steps in order
3. **CHECK**: Apply the skill's anti-rationalization table — if you're tempted to skip a step, the answer is NO
4. **VERIFY**: Produce evidence per the skill's Verification section
5. **LOG**: Record in `aidlc-docs/audit.md`: `[Skill] Executed: <skill-name> (<Stage>) — PASS|FAIL`
6. **BLOCK**: If verification fails → stage cannot complete. Fix first.

**If a skill file is missing**: The stage rule file embeds the critical process steps inline. Follow those. Log a warning: `[Skill] MISSING: <skill-name> — using inline process`

**Anti-bypass rule**: You MUST NOT skip skill steps. "I'll do it later", "it's obvious", "not needed for this change" are rationalizations. If a skill defines verification, you MUST produce evidence. No exceptions.

### Skills by Phase

| Phase | Skills (always active for that phase) |
|-------|------|
| **Define** (Inception: Requirements) | `idea-refine`, `spec-driven-development` |
| **Plan** (Inception: Workflow Planning) | `planning-and-task-breakdown` |
| **Build** (Construction: Code Gen) | `incremental-implementation`, `test-driven-development`, `source-driven-development`, `frontend-ui-engineering`*, `api-and-interface-design`* |
| **Verify** (Construction: Build & Test) | `test-driven-development`, `browser-testing-with-devtools`*, `debugging-and-error-recovery` |
| **Review** (Construction: post-gen gate) | `code-review-and-quality`, `security-and-hardening`, `performance-optimization`, `code-simplification` |
| **Ship** (Operations / end of Construction) | `shipping-and-launch`, `git-workflow-and-versioning`, `ci-cd-and-automation`, `documentation-and-adrs`, `deprecation-and-migration`* |

\* = conditional on project type (UI, API, legacy migration)

### Skill Commands (Entry Points)

These commands activate the right stage + skills combination:

| Command | Maps to | Skills Activated |
|---------|---------|------------------|
| `/spec` | INCEPTION → Requirements Analysis | `spec-driven-development`, `idea-refine` |
| `/plan` | INCEPTION → Workflow Planning + Units | `planning-and-task-breakdown` |
| `/build` | CONSTRUCTION → Code Generation | `incremental-implementation`, `test-driven-development`, `source-driven-development` |
| `/test` | CONSTRUCTION → Build & Test | `test-driven-development`, `debugging-and-error-recovery` |
| `/review` | Post-generation quality gate | `code-review-and-quality`, `security-and-hardening`, `performance-optimization` |
| `/code-simplify` | Refactor pass | `code-simplification` |
| `/ship` | Pre-launch checklist | `shipping-and-launch`, `git-workflow-and-versioning`, `ci-cd-and-automation` |

When a command is invoked, the workflow activates the corresponding stage AND loads all mapped skills. The skills' Process steps become the execution plan for that stage.

### Completion Message: Skill Compliance
Every stage completion message MUST include a skill compliance summary:
```markdown
### Skill Compliance
| Skill | Status | Evidence |
|-------|--------|----------|
| incremental-implementation | ✅ PASS | Tests green, atomic commits |
| test-driven-development | ✅ PASS | Red→Green→Refactor followed |
| code-review-and-quality | ⚠️ N/A | No review stage yet |
```
## Tool Adapters (Optional)
Adapter docs in `aidlc-rules/adapters/` (informational only):
- copilot.md, cursor.md, claude-code.md, cline.md, generic.md

## MANDATORY: Content Validation
Before creating files validate:
- Mermaid syntax, ASCII diagrams, escape special chars, provide text alternatives, test parsing compatibility

## MANDATORY: Question File Format
Follow `common/question-format-guide.md` for question formatting (MCQ, `[Answer]:` tags, ambiguity rules).

## MANDATORY: Welcome Message
Generate a brief welcome message from `common/process-overview.md` once at workflow start (show phases, adaptive principle, team role).

## MANDATORY: Auto-Commit on Approval
**CRITICAL**: After EVERY user approval, plan approval, stage completion, unit phase completion, or user progression command ("continue", "next", "approve", "go ahead", "looks good", etc.), you MUST immediately run the following terminal command BEFORE proceeding to the next stage:

```bash
git add -A && git commit -m "<type>(<scope>): <description>"
```

- `<type>`: `docs` for plans/questions/requirements, `feat` for generated code, `build` for build/test artifacts
- `<scope>`: stage or unit name in kebab-case (e.g., `workspace-detection`, `requirements-analysis`, `functional-design`, `auth-unit`)
- `<description>`: concise past-tense summary (e.g., "complete requirements analysis", "approve code generation plan")

**Examples**:
- `docs(workspace-detection): complete workspace detection`
- `docs(requirements-analysis): approve requirements verification`
- `feat(auth-unit): generate authentication service code`
- `build(build-and-test): complete build and test instructions`

**Rules**:
- Run `git add -A` first to capture ALL artifact and state changes
- Do NOT ask the user for permission — this is automatic
- If git is not initialized or the commit fails, log a warning in `aidlc-docs/audit.md` and continue — do NOT block the workflow
- This applies to ALL stages in ALL phases (inception, construction, operations)

# Adaptive Software Development Workflow

---

# INCEPTION PHASE

Purpose: Planning, requirements, architecture

Focus: WHAT to build and WHY

Stages (inception): Workspace Detection, Reverse Engineering (brownfield), Requirements Analysis, User Stories (optional), Workflow Planning, Application Design (optional), Units Generation (optional)

## Workspace Detection (ALWAYS EXECUTE)
1. Log raw user request in `aidlc-docs/audit.md`
2. Load `inception/workspace-detection.md`
3. Detect workspace: check `aidlc-state.md`, scan code, decide brownfield vs greenfield, check reverse-engineering artifacts
4. Choose next phase: Reverse Engineering (brownfield/no artifacts) or Requirements Analysis
5. Log findings in audit
6. Present completion message
7. Proceed automatically

## Reverse Engineering (CONDITIONAL - Brownfield Only)
Execute if codebase present and no prior reverse-engineering artifacts.

Steps (short):
- Log start in audit
- Load `inception/reverse-engineering.md`
- Produce: business overview, architecture docs, code structure, API docs, component inventory, interaction diagrams, tech stack, dependencies
- Present detailed completion message and wait for user approval
- Log user response in audit

## Requirements Analysis (ALWAYS EXECUTE - Adaptive Depth)
Depth: minimal / standard / comprehensive depending on request clarity/risk.

Steps:
- Log inputs in audit
- Load `inception/requirements-analysis.md`
- Use reverse-engineering artifacts if brownfield
- Analyze intent, determine depth, gather functional & non-functional requirements, ask clarifying Qs
- Generate requirements doc, wait for approval, log response

## User Stories (CONDITIONAL)
Use when features touch users, workflows, multiple personas, or complexity warrants stories. Plan (questions) → generate (stories/personas) after approval. Log all inputs.

## Workflow Planning (ALWAYS EXECUTE)
- Load `inception/workflow-planning.md` and `common/ascii-diagram-standards.md`
- Use prior context (reverse-engineering, requirements, stories)
- Decide phases & depth, plan multi-package changes if needed, generate Mermaid visualization (validate syntax)
- Activate `planning-and-task-breakdown` skill: decompose into small, verifiable tasks with acceptance criteria
- Validate content, present plan, wait for approval, log response

## Application Design, Units Generation (CONDITIONAL)
Run only if new components, services, or decomposition required. Log inputs, load respective rule files, present completion messages, wait for approval, log responses.

---

# 🟢 CONSTRUCTION PHASE

Purpose: HOW to build (design, NFRs, code)

## MANDATORY: Construction Phase Entry Checkpoint
**CRITICAL — execute this checkpoint BEFORE any Construction stage.**

Before starting the first Construction stage, verify:
1. **Audit completeness**: Every completed Inception stage has an entry in `aidlc-docs/audit.md` (Workspace Detection, Requirements Analysis, Workflow Planning, and any conditional stages like Application Design, Units Generation). If any are missing, add them NOW.
2. **State correctness**: `aidlc-state.md` `Current Stage` reflects the last completed stage, NOT an old value. Update it.
3. **Directory readiness**: `aidlc-docs/construction/plans/` directory exists (create if not).
4. **Plan reference**: The execution plan from `aidlc-docs/inception/plans/` is loaded and its task checkboxes will be updated as work proceeds.

**If this checkpoint reveals gaps, fix them before proceeding. Do NOT start Code Generation with incomplete tracking.**

## MANDATORY: Construction Audit Logging
**Every Construction stage MUST log to `aidlc-docs/audit.md`. This is NOT optional.**

For each unit's Code Generation:
- Log plan approval: `## [timestamp] CONSTRUCTION - Code Generation Plan Approved (Unit: {name})`
- Log completion: `## [timestamp] CONSTRUCTION - Code Generation COMPLETE (Unit: {name})`
- Log ALL skill executions: `- [Skill] Executed: {skill-name} (Code Generation) — PASS|FAIL`
- Log user approval/response

For Build & Test:
- Log start: `## [timestamp] CONSTRUCTION - Build and Test START`
- Log completion: `## [timestamp] CONSTRUCTION - Build and Test COMPLETE`
- Include: build status, test results, files generated
- Log ALL skill executions: `- [Skill] Executed: {skill-name} (Build & Test) — PASS|FAIL`

**Anti-skip rule**: If you reach a Construction completion message and audit.md has no Construction entries, STOP. Go back and add them before presenting completion.

## MANDATORY: Construction Artifact Generation
**Code Generation MUST produce plan files. Build & Test MUST produce instruction files.**

Required artifacts:
- `aidlc-docs/construction/plans/{unit-name}-code-generation-plan.md` — one per unit, with `[x]` checkboxes updated as steps complete
- `aidlc-docs/construction/build-and-test/build-instructions.md`
- `aidlc-docs/construction/build-and-test/build-and-test-summary.md`

**If `aidlc-docs/construction/` is empty at Build & Test completion, this is a blocking failure. Fix before presenting completion.**

Per-unit loop: Functional Design, NFR Requirements, NFR Design, Infrastructure Design, Code Generation (always). Complete each unit fully before next.

Code Generation (per unit): plan → generate code following `incremental-implementation` skill (thin vertical slices: implement → test → verify → commit) → apply `code-review-and-quality` skill (five-axis self-review) → present findings → wait for approval.

Build & Test: execute `test-driven-development` skill (Red-Green-Refactor), apply `debugging-and-error-recovery` if failures, produce build/test instructions and files under `aidlc-docs/construction/build-and-test/`, wait for approval.

---

# 🟡 OPERATIONS PHASE

Placeholder for deployment, monitoring, incident response, production readiness. Currently handled post-build in Construction.

## MANDATORY: State Tracking
**`aidlc-state.md` MUST be kept accurate at ALL times.**

Rules:
1. **`Current Stage`**: Update after EVERY stage completion to reflect the stage just finished (e.g., after Code Gen Unit 2 completes → `Current Stage: CONSTRUCTION - Code Generation (Unit 2)`). NEVER leave it pointing to an earlier stage.
2. **Stage Progress list**: Mark `[x]` with date in the same interaction as stage completion. The list MUST match `audit.md` entries — if audit.md shows a stage complete, the state file must too, and vice versa.
3. **Execution plan checkboxes**: When a task from `aidlc-docs/inception/plans/` is completed during Construction, mark it `[x]` in the plan file in the SAME interaction. Do NOT defer checkbox updates.
4. **Final state**: When the last Construction stage completes, set `Current Stage` to `CONSTRUCTION - Complete` (or `OPERATIONS` if proceeding).

Key principles (short):
- Adaptive execution
- Transparent planning
- User control
- Progress tracking in `aidlc-state.md`
- Full audit trail in `aidlc-docs/audit.md` (log raw user input exactly)
- Validate content before writing
- No emergent UI patterns; use standardized 2-option completion messages in construction stages

Plan-level rules (short):
1. Always update plan checkboxes when work done
2. Mark steps [x] in same interaction as completion
3. Track at plan-level and stage-level

Prompts logging (short):
- Log every user input with ISO8601 timestamp in `aidlc-docs/audit.md` (append, do not overwrite)
- Use specified audit format
- **Timestamps MUST be chronological** — each new entry's timestamp must be >= the previous entry's timestamp. Workspace Detection is always the first entry.

Directory structure (short):
```
<WORKSPACE-ROOT>/
├── aidlc-docs/
│   ├── inception/
│   ├── construction/
│   ├── operations/
│   ├── aidlc-state.md
│   └── audit.md
```

CRITICAL: Application code stays in workspace root; docs only in `aidlc-docs/`.
- Existing codebase detected

<!-- AIDLC-ORCHESTRATOR-POINTER -->
## AIDLC Orchestrator (multi-agent factory mode)

This project ships with the AIDLC orchestrator. To run the multi-agent factory:

- `/factory-onboarding` — guided tour of the orchestrator system
- `/factory-help [command]` — quick command reference
- `/factory-state <run-id>` — current stage, next step, budget, timeline
- `/factory-self <task>` — run the orchestrator on its own codebase
- `/factory-spec <feature>` — workspace scout + (reverse-engineer) + requirements + (stories) + plan
- `/factory-plan` — decompose plan into per-unit specs (multi-component features only)
- `/factory-build` — layer-parallel code generation with file-glob locks + AST symbol drift checks
- `/factory-review` — parallel reviewer pool (code, security, performance, simplifier)
- `/factory-ship` — release notes, ADRs, CI/CD wiring, CHANGELOG, migration plan
- `/factory-resume <run-id>` — resume an interrupted run (or adopt a legacy `aidlc-docs/` project)
- `/factory-replay <run-id> --from <stage>` — re-run from a specific stage

Roles, contracts, budgets, and parallelism rules: see `.claude/agents/orchestrator.md`,
`.aidlc-orchestrator/contracts/`, and `.aidlc-orchestrator/budgets/default.yaml`.
Design rationale and phase plan: `ORCHESTRATOR-PLAN.md` in the AIDLC source repo.
