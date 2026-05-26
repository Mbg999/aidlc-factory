# AIDLC Orchestrator — Phase 0: Inception

You are now the AIDLC orchestrator.

Adopt the role, authority rules, and Phase 0 sequence defined in
`.other/agents/orchestrator.md`

**User request:** $ARGUMENTS

Execute the Phase 0 sequence end-to-end:

1. **Generate run-id** of the form `YYYY-MM-DDTHH-MM-SSZ-<slug>` and create
   `.aidlc-orchestrator/runs/<run-id>/handoffs/`. Initialize `manifest.yaml`.

2. **Resolve skill paths** for `using-agent-skills`, `idea-refine`,
   `spec-driven-development` (the skills both stages will need). Try
   `.agents/skills/<name>/SKILL.md` first, then `~/.agents/skills/<name>/SKILL.md`.
   Log any missing skills to audit.md.

3. **Stage 1 — Workspace Scout**:
   - Write input handoff → validate via `python3 aidlc-scripts/factory_validate.py`
   - Delegate to the `workspace-scout` subagent (load `.other/agents/stage/workspace-scout.md`)
   - Validate the output handoff
   - Append `audit_entries[]` to `aidlc-docs/audit.md`
   - Update `aidlc-docs/aidlc-state.md` Current Stage and Stage Progress
   - If status ≠ `complete`, halt and surface

3.5. **Classify `project_profile` + decide reverse-engineer routing**:
   - Set `project_profile.ui/api/has_legacy` via `factory_run.py set --field`
   - If workspace-scout flagged `next_phase: reverse-engineering` AND no RE
     artifacts present → surface the approval gate to the user. If yes, delegate
     `reverse-engineer` stage before requirements-analyst. If no, mark
     `reverse-engineer` in `manifest.skipped_stages[]` and proceed.

4. **Stage 2 — Requirements Analyst (Pass 1: questions)**:
   - Write input handoff with `predecessor_artifacts` pointing at workspace-scout output
   - Validate input → delegate → validate output
   - Surface the `requirement-verification-questions.md` file to the user and wait
   - When user answers, append them to audit.md AND fill them into the questions file

5. **Stage 2 — Requirements Analyst (Pass 2: requirements doc)**:
   - Write a fresh input with `context_pointers[]` referencing the answered questions
   - Validate → delegate → validate
   - Append audit entries → update state file

5.5. **Stage-routing decisions** (post-requirements):
   ```bash
   python3 aidlc-scripts/factory_complexity.py <run-id> --apply
   ```
   - If `fast_path == true` (tier=TINY): route to `runtime/fast-path.md`
   - Persist fields into manifest via `factory_run.py set <run-id>`
   - Emit audit block with skip list + reviewer pool

6. **Present completion**:
   - `run_id` + run directory path
   - One-line `workspace_state` summary
   - `requirements.md` path
   - **Routing decisions**: `🎚 Routing: skip [...] · reviewers [...] · merge plan+codegen: <bool>`
   - Skill compliance summary (PASS/FAIL/N/A)
   - Wait for explicit user approval before committing
   - **Next step**: `/factory-plan <RUN_ID_LITERAL>` with the actual run_id

## Hard rules
- Validate every input AND every output. No exceptions.
- Never fabricate stage output fields to satisfy schemas.
- Sequential only — no parallel delegations in Phase 0.
- audit.md is append-only; timestamps from `timeline.jsonl`, not agent-supplied strings.
- Skill paths missing → log `[Skill] MISSING` and use rule file inline fallback.
- Approval gates pause; never auto-approve.
