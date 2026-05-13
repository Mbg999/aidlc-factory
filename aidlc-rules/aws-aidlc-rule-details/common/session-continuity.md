# Session Continuity

## Welcome Back Template
When user returns to existing project, present:
- Project name, current phase, current stage, last completed step, next step
- Options: A) Continue where left off, B) Review a previous stage

## MANDATORY: Session Resumption Rules

1. **Always read `aidlc-state.md` first** on resume
2. **Detect resumption mode** before loading artifacts:

| `aidlc-state.md` state | User message type | Mode |
|---|---|---|
| Stages in progress (not all `[x]`) | Any | **In-Progress Resume** → standard resume below |
| All stages `[x]` (complete) | New dev request (feature/fix/refactor) | **New Iteration** → return to `workspace-detection.md` Branch B — do NOT resume, do NOT skip workflow |
| All stages `[x]` (complete) | Question / review / no-dev request | **Review Mode** → present summary, offer options |

**CRITICAL**: A completed project receiving a new development request MUST go through the full workflow again (Requirements Analysis → ... → Build & Test). Silently skipping stages, skipping skill execution, or skipping artifact generation for a new request is a workflow violation.

3. **Load audit trail**: Read `aidlc-docs/audit.md`. If the Summary header lists archive files, load them when full timeline context is needed (phase transition verification, troubleshooting).
4. **Load artifacts by stage** before resuming (In-Progress Resume only):

| Current Stage | Load |
|--------------|------|
| Reverse Engineering | Workspace analysis |
| Requirements/Stories | RE artifacts + requirements |
| Design stages | Requirements + stories + architecture + design |
| Code stages | ALL artifacts + existing code |

5. **Validate state matches artifacts** — if mismatch, see [error-handling.md](error-handling.md)
6. Show specific next steps (not generic descriptions)
7. After loading, provide brief context summary to user
8. Log continuity prompt in audit.md
9. Questions go in `.md` files — never inline in chat
