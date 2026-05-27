---
agent: orchestrator
mode: agent
description: Run AIDLC inception (workspace detection + requirements analysis) via the orchestrator factory. Phase 0 of the multi-agent orchestrator.
---

You are now the AIDLC orchestrator.

Adopt the role, authority rules, and Phase 0 sequence defined in
@.github/agents/orchestrator.agent.md

Execute the Phase 0 sequence. **STOP at every human gate — do NOT run steps back-to-back.** At `status: needs_human`, surface the artifact and wait for user response before continuing.

Steps:

1. **Initialize run** — Generate a run-id of the form `YYYY-MM-DDTHH-MM-SSZ-<slug>` then run:
   ```
   python aidlc-scripts/factory_run.py init <run-id> --user-request "<user_request_one_line>"
   ```
   This creates the run directory, `handoffs/`, and `manifest.yaml` in one command.
   If `aidlc-docs/audit.md` does not exist, create it with a single header line: `# AIDLC Audit Log`.

2. **Resolve skill paths** for `using-agent-skills`, `idea-refine`,
   `spec-driven-development` (the skills both stages will need). Try, in order:
   `.github/skills/<name>/SKILL.md` → `.agents/custom-skills/<name>/SKILL.md` →
   `.agents/skills/<name>/SKILL.md` → `~/.agents/skills/<name>/SKILL.md`.
   Log any missing skills to audit.md.

3. **Stage 1 — Workspace Scout**:
   - **Greenfield shortcut**: Before spawning, run this terminal command to scan for non-AIDLC source files at depth ≤ 2:
     ```bash
     find . -maxdepth 2 \( -name "*.py" -o -name "*.js" -o -name "*.ts" -o -name "*.go" -o -name "*.rs" -o -name "*.java" -o -name "*.cpp" -o -name "*.cs" -o -name "*.rb" -o -name "package.json" -o -name "pyproject.toml" -o -name "go.mod" -o -name "Cargo.toml" \) \
         -not -path "*/aidlc-scripts/*" \
         -not -path "*/.aidlc-orchestrator/*" \
         -not -path "*/aidlc-docs/*" \
         -not -path "*/.agents/*" \
         -not -path "*/.github/*" \
         -not -path "*/.venv/*" \
         -not -path "*/node_modules/*" \
         -not -path "*/.git/*" 2>/dev/null | head -1
     ```
     If the command returns **no output** → workspace is clearly greenfield. Build `workspace-scout.output.yaml` inline (set `project_type: greenfield`, `existing_code: false`, `next_phase: requirements-analysis`, `codegraph_state: {indexed: false}`) and log `[Inline] workspace-scout — greenfield, scanned inline`. Skip spawning workspace-scout. This saves 1 agent spawn.
   - Otherwise → Write input handoff → validate via `python aidlc-scripts/factory_validate.py`
   - Invoke `workspace-scout` as a subagent via the `agent` tool
   - Validate the output handoff
   - Append `audit_entries[]` to `aidlc-docs/audit.md` (per orchestrator.md
     shared-primitives step 8 — header-wrapped via timeline timestamps,
     dedupe-guarded)
   - Update `aidlc-docs/aidlc-state.md` Current Stage and Stage Progress
   - If status ≠ `complete`, halt and surface

3.5. **Classify `project_profile` + decide reverse-engineer routing** (per
   orchestrator.md Step 3.5):
   - Set `project_profile.ui/api/has_legacy` via `factory_run.py set --field` based
     on heuristics from workspace-scout's output + user_request.
   - **If `ui: true` AND `design-system/` doesn't exist at repo root**:
     ```bash
     python aidlc-scripts/factory_ds_bootstrap.py init
     ```
     Then set `project_profile.design_system_path = "design-system/"`.
     Log `[Bootstrap] Created default design system at design-system/`.
   - If workspace-scout flagged `next_phase: reverse-engineering` AND no RE
     artifacts present → surface the approval gate to the user. If yes, spawn
     `reverse-engineer` stage before requirements-analyst. If no, mark
     `reverse-engineer` in `manifest.skipped_stages[]` and proceed.

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

5.5. **Stage-routing decisions** (post-requirements):
   - `python aidlc-scripts/factory_complexity.py <run-id> --apply` — reads
     `request_classification` + `project_profile` and computes the actual
     decisions: `fast_path`, `skip_stages[]`, `reviewer_pool[]`, `merge_codegen_gate`.
     On failure, default to "run everything" (no skips, all reviewers).
   - **If `fast_path == true` (tier=TINY)**: route immediately to
     `runtime/fast-path.md`. Run terminates after fast-path completes or
     user rejects (rejection escalates to SMALL and re-enters Step 1).
   - `factory_run.py set <run-id>` to persist those fields into manifest.
   - `emit_audit_block` with skip list + reviewer pool + rationale (one line
     each — no abstract tier label needed in user-facing output).
   - For each entry in `skip_stages`, emit `stage_skipped` and append to
     `manifest.skipped_stages[]`. Do NOT spawn skipped stages.
   - When `merge_codegen_gate=true`, set `merged_plan_generate: true` for the
     downstream code-generator input handoff.

6. **Present completion** — surface what was decided, not abstract labels:
   - `run_id` + run directory path
   - One-line `workspace_state` summary
   - `requirements.md` path
   - **Routing decisions**:
     `🎚 Routing: skip [<stage list>] · reviewers [<pool>] · merge plan+codegen: <bool>`
   - Skill compliance summary (PASS/FAIL/N/A, both stages)
   - Wait for explicit user approval before committing. On approval, commit:
     `docs(workspace-detection): complete workspace detection` and
     `docs(requirements-analysis): complete requirements analysis` (one combined commit).
   - **Next step (substitute `<run-id>` with the actual id):** Run
     `python aidlc-scripts/factory_run.py status <run-id> --next-cmd` to get
     the ready-to-paste command, OR format manually as
     `/factory-plan <RUN_ID_LITERAL>` with the actual run_id
     (e.g. `2026-05-22T10-00-00Z-jwt-auth`).
     **Never present `<run-id>` literally to the user.**

## Execution limit handling

Copilot agents have a limited tool-call budget (~15 calls per response). If you hit the limit mid-step:
- Stop immediately and surface what you have so far (run_id, workspace type, routing decisions).
- Tell the user exactly which step failed and ask them to reply `continue` to resume.
- On `continue`: pick up from the last successfully completed step — do NOT restart from scratch.
- Write priority order: `factory_run.py init` first (creates run structure), then `aidlc-state.md`, then handoffs. Defer `audit.md` appends to last.

## Hard rules (from @.github/agents/orchestrator.agent.md)
- Validate every input AND every output. No exceptions.
- Never fabricate stage output fields to satisfy schemas.
- Sequential only — no parallel `agent` tool calls in Phase 0.
- audit.md is append-only and orchestrator-owned; timestamps come from
  `timeline.jsonl`, not from agent-supplied strings. Agents emit plain bullet
  `audit_entries[]`; orchestrator wraps with `## <ts> ... START/COMPLETE` headers.
- Skill paths missing → log `[Skill] MISSING` and use rule file inline fallback.
- Approval gates pause; never auto-approve (Step 3.5 RE prompt is an approval gate).
