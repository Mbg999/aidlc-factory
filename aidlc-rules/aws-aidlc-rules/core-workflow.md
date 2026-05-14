# PRIORITY: This workflow OVERRIDES all other built-in workflows
# When user requests software development, ALWAYS follow this workflow FIRST

## Adaptive Workflow Principle
**The workflow adapts to the work, not the other way around.**
Assesses: user intent, codebase state, complexity, risk.

## MANDATORY: Rule Details Loading
Load rule details from the first existing path:
- `.aidlc/aidlc-rules/aws-aidlc-rule-details/` (canonical)
- `.aidlc-rule-details/` (flat layout)
- `aidlc-rules/aws-aidlc-rule-details/` (monorepo)

Always load common rules at start: `common/process-overview.md`, `common/stage-conventions.md`, `common/session-continuity.md`, `common/ascii-diagram-standards.md`, `common/question-format-guide.md`.

## Extensions
Scan `extensions/` for opt-in files at workflow start. Deferred loading per
[`runtime/extension-loading.md`](.aidlc-orchestrator/runtime/extension-loading.md).

## Skills
Skills enforce quality. Each stage requires specific skills (LOAD/FOLLOW/CHECK/
VERIFY/LOG/BLOCK). Full protocol: [`runtime/skill-protocol.md`](.aidlc-orchestrator/runtime/skill-protocol.md).

## MANDATORY: Content Validation
Before creating files: validate Mermaid syntax, escape special chars, provide text alternatives.

## MANDATORY: Question File Format
Follow `common/question-format-guide.md` (MCQ, `[Answer]:` tags).

## MANDATORY: Welcome Message
Show once at start from `common/process-overview.md`.

## MANDATORY: Auto-Commit on Approval
**CRITICAL**: After EVERY user approval, plan approval, stage completion, or "continue"/"approve"/"go ahead", run:
```bash
git add -A && git commit -m "<type>(<scope>): <description>"
```
Types: `docs` (plans/requirements), `feat` (code), `build` (build/test).
Scope: stage/unit in kebab-case. If git fails, log warning and continue.

---

# INCEPTION PHASE
Purpose: WHAT to build. Stages: Workspace Detection, Reverse Engineering (cond), Requirements Analysis, User Stories (cond), Workflow Planning, Application Design (cond), Units Generation (cond).

## Workspace Detection (ALWAYS)
Log request → load `inception/workspace-detection.md` → scan code → decide brownfield/greenfield → log → proceed.

## Reverse Engineering (CONDITIONAL — brownfield, no prior artifacts)
Load `inception/reverse-engineering.md` → produce docs → wait for approval.

## Requirements Analysis (ALWAYS — adaptive depth)
Load `inception/requirements-analysis.md` → analyze → ask questions → produce requirements doc → wait for approval.

## Workflow Planning (ALWAYS)
Load `inception/workflow-planning.md` → plan phases → Mermaid diagram → decompose tasks → present plan → wait for approval.

---

# 🟢 CONSTRUCTION PHASE
Purpose: HOW to build.

## Entry Checkpoint
Before first Construction stage: verify audit.md has all Inception entries, state file is correct, `aidlc-docs/construction/plans/` exists.

## Per-unit loop
Functional Design → NFR Requirements → NFR Design → Infrastructure Design → Code Generation.
Code Gen: plan → implement (TDD thin slices) → self-review → wait for approval.
Build & Test: Red-Green-Refactor → debug if failures → produce instructions → wait for approval.

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

This project ships with the AIDLC orchestrator:
- `/factory-onboarding`, `/factory-help`, `/factory-state`
- `/factory-spec <feature>` — workspace scout + requirements + plan
- `/factory-plan <run-id>` — decompose plan into per-unit specs
- `/factory-build <run-id>` — layer-parallel code generation with locks + AST checks
- `/factory-review <run-id>` — parallel reviewer pool
- `/factory-ship <run-id>` — release notes, ADRs, CI/CD, CHANGELOG
- `/factory-resume <run-id>` — resume interrupted run (or adopt legacy `aidlc-docs/`)
- `/factory-replay <run-id> --from <stage>` — re-run from a specific stage

See `.claude/agents/orchestrator.md`, `.aidlc-orchestrator/runtime/index.md`, `.aidlc-orchestrator/contracts/`.
