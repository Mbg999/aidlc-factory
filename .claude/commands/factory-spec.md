---
description: Run AIDLC inception (workspace detection + requirements analysis) via the orchestrator factory. Phase 0 of the multi-agent orchestrator.
argument-hint: <feature description in natural language>
---

You are now the AIDLC orchestrator.

Adopt the role, authority rules, and Phase 0 sequence defined in
@.claude/agents/orchestrator.md

**User request:** $ARGUMENTS

Execute the Phase 0 sequence end-to-end:

1. **Generate run-id** of the form `YYYY-MM-DD-<slug>` and create
   `.aidlc-orchestrator/runs/<run-id>/handoffs/`. Initialize `manifest.yaml`.

2. **Resolve skill paths** for `using-agent-skills`, `idea-refine`,
   `spec-driven-development` (the skills both stages will need). Try
   `.agents/skills/<name>/SKILL.md` first, then `~/.agents/skills/<name>/SKILL.md`.
   Log any missing skills to audit.md.

3. **Stage 1 — Workspace Scout**:
   - Write input handoff → validate via `python3 scripts/factory_validate.py`
   - Spawn `workspace-scout` subagent via Task() with the input path as the prompt
   - Validate the output handoff
   - Append `audit_entries[]` to `aidlc-docs/audit.md`
   - Update `aidlc-docs/aidlc-state.md` Current Stage and Stage Progress
   - Auto-commit (`docs(workspace-detection): complete workspace detection`)
   - If status ≠ `complete`, halt and surface

4. **Stage 2 — Requirements Analyst (Pass 1: questions)**:
   - Write input handoff with `predecessor_artifacts` pointing at workspace-scout
     output, and `workspace_state` copied from it
   - Validate input → spawn → validate output
   - Surface the `requirement-verification-questions.md` file to the user and wait
     for their answers
   - When user answers, append them to audit.md AND fill them into the questions
     file in the `[Answer]:` slots

5. **Stage 2 — Requirements Analyst (Pass 2: requirements doc)**:
   - Write a fresh input with `context_pointers[]` referencing the answered
     questions file
   - Validate → spawn → validate
   - Append audit entries → update state file
   - Auto-commit (`docs(requirements-analysis): complete requirements analysis`)

6. **Present completion**:
   - Show run_id, run directory path
   - Show `workspace_state` summary (one line)
   - Show `requirements.md` path
   - Show skill compliance summary (PASS/FAIL/N/A per skill, both stages)
   - Offer next step: `/factory-plan <run-id>` (wired in Phase 1; for now,
     remind the user that Phase 0 stops here)

## Hard rules (from @.claude/agents/orchestrator.md)
- Validate every input AND every output. No exceptions.
- Never fabricate stage output fields to satisfy schemas.
- Sequential only — no parallel Task() calls in Phase 0.
- audit.md is append-only; ISO8601 chronological timestamps.
- Skill paths missing → log `[Skill] MISSING` and use rule file inline fallback.
- Approval gates pause; never auto-approve.
