---
name: factory-spec
description: Run AIDLC inception (workspace detection + requirements analysis) via the orchestrator factory. Phase 0 of the multi-agent orchestrator. Executes workspace-scout and requirements-analyst stages.
---

# factory-spec — AIDLC Inception

Adopt the role, authority rules, and Phase 0 sequence defined in `.aidlc-orchestrator/agents/orchestrator.md`.

**User request:** the feature description in natural language provided by the user.

Execute the Phase 0 sequence end-to-end:

1. **Generate run-id** via the cross-platform Python helper:
   ```bash
   run_id=$(python3 aidlc-scripts/factory_run.py generate-run-id --slug "<slug>")
   ```
   Then create `.aidlc-orchestrator/runs/$run_id/handoffs/` and initialize `manifest.yaml`.

2. **Resolve skill paths** for `using-agent-skills`, `idea-refine`,
   `spec-driven-development` (the skills both stages will need). Try
   `.agents/skills/<name>/SKILL.md` first, then `~/.agents/skills/<name>/SKILL.md`.
   Log any missing skills to audit.md.

3. **Stage 1 — Workspace Scout**:
   - Write input handoff -> validate via `python3 aidlc-scripts/factory_validate.py`
   - Spawn workspace-scout subagent with the input path as the prompt
   - Validate the output handoff
   - Append `audit_entries[]` to `aidlc-docs/audit.md`
   - Update `aidlc-docs/aidlc-state.md` Current Stage and Stage Progress
   - If status != `complete`, halt and surface

3.5. **Classify `project_profile` + decide reverse-engineer routing**:
   - Set `project_profile.ui/api/has_legacy` via `factory_run.py set --field`
   - If `ui: true` AND `design-system/` doesn't exist at repo root:
     ```bash
     python3 aidlc-scripts/factory_ds_bootstrap.py init
     ```
   - If workspace-scout flagged `next_phase: reverse-engineering` -> surface approval gate

4. **Stage 2 — Requirements Analyst (Pass 1: questions)**:
   - Write input handoff with `predecessor_artifacts` pointing at workspace-scout output
   - Validate input -> spawn -> validate output
   - Surface the `requirement-verification-questions.md` file to the user and wait for answers
   - When user answers, append them to audit.md

5. **Stage 2 — Requirements Analyst (Pass 2: requirements doc)**:
   - Write a fresh input with `context_pointers[]` referencing the answered questions file
   - Validate -> spawn -> validate
   - Append audit entries -> update state file

5.5. **Stage-routing decisions** (post-requirements):
   - `python3 aidlc-scripts/factory_complexity.py <run-id> --apply`
   - If `fast_path == true`: route to `runtime/fast-path.md`
   - Persist routing decisions in manifest

6. **Present completion** — surface run_id, workspace_state summary, requirements.md path,
   routing decisions, skill compliance summary. Wait for explicit user approval before
   committing. On approval, commit combined workspace detection + requirements analysis.

   **Next step:** `/factory-plan <RUN_ID_LITERAL>`

## Hard rules
- Validate every input AND every output. No exceptions.
- Never fabricate stage output fields to satisfy schemas.
- Sequential only — no parallel Task() calls in Phase 0.
- audit.md is append-only and orchestrator-owned.
- Skill paths missing -> log `[Skill] MISSING` and use rule file inline fallback.
- Approval gates pause; never auto-approve.
