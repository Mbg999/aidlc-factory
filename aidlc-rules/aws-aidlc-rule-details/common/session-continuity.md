# Session Continuity

## Welcome Back Template
When user returns to existing project, present:
- Project name, current phase, current stage, last completed step, next step
- Options: A) Continue where left off, B) Review a previous stage

## MANDATORY: Session Resumption Rules

1. **Always read `aidlc-state.md` first** on resume
2. **Load artifacts by stage** before resuming:

| Current Stage | Load |
|--------------|------|
| Reverse Engineering | Workspace analysis |
| Requirements/Stories | RE artifacts + requirements |
| Design stages | Requirements + stories + architecture + design |
| Code stages | ALL artifacts + existing code |

3. **Validate state matches artifacts** — if mismatch, see [error-handling.md](error-handling.md)
4. Show specific next steps (not generic descriptions)
5. After loading, provide brief context summary to user
6. Log continuity prompt in audit.md
7. Questions go in `.md` files — never inline in chat
