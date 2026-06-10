# `/factory-product` — Product Harness

PRIORITY: P2

Produces product artifacts only. Pipeline: workspace-scout → requirements-analyst → story-writer → workflow-planner → **stop**. No complexity routing, no code-gen, no build, no review.

**Output artifacts:**
- `aidlc-docs/inception/requirements/<run-id>-requirements.md`
- `aidlc-docs/inception/user-stories/<run-id>-personas.md`
- `aidlc-docs/inception/user-stories/<run-id>-stories.md`
- `aidlc-docs/inception/plans/<run-id>-execution-plan.md`

---

## Step 1 — Init run dir + audit.md

```
run_id = YYYY-MM-DDTHH-MM-SSZ-<slug>   # UTC; slug = first 3-4 words, hyphenated
mkdir -p .aidlc-orchestrator/runs/<run-id>/handoffs
```

Ensure `aidlc-docs/` exists:
```bash
mkdir -p aidlc-docs
```
`aidlc-docs/audit.md` is auto-created on first append by `spawn-loop.md` step 7 (via `factory_run.py emit_audit_block`).

Create `manifest.yaml`:
```yaml
run_id: <run-id>
started_at: <ISO>
user_request: <verbatim>
harness: product
current_stage: workspace-scout
completed_stages: []
skipped_stages: [complexity-routing, unit-decomposer, build-test, reviewer-pool, ship]
```

## Step 2 — Resolve skill paths

Find each SKILL.md: `.agents/custom-skills/<name>/SKILL.md` → `.agents/skills/<name>/SKILL.md` → `~/.agents/skills/<name>/SKILL.md`. Store in `manifest.skill_paths`. Log `[Skill] MISSING: <name>` if absent.

Skills needed: `using-agent-skills`, `idea-refine`, `spec-driven-development`, `requirements-intelligence`.

## Step 3 — Workspace Scout (inline)

Execute `stage/workspace-scout.md` inline per [post-execution loop](spawn-loop.md).

- **skills_required**: `[using-agent-skills]`
- **predecessor_artifacts**: none
- **approval gate**: none — auto-proceeds on `status: complete`
- **state on success**: `Current Stage: PRODUCT - Workspace Detection (complete)`; manifest `current_stage: requirements-analyst`

## Step 3.5 — Classify `project_profile`

Set `project_profile.ui/api/has_legacy` via `factory_run.py set --field` based on workspace-scout output + user_request.

Skip reverse-engineer routing — product harness does not run RE. Log `[Skipped] reverse-engineer: product harness`.

## Step 4 — Requirements Analyst (two-pass, inline) + approval

Execute `stage/requirements-analyst.md` inline per [post-execution loop](spawn-loop.md).

**Two-pass**: Pass 1 emits questions → **SURFACE the questions file path** (from `questions_artifact_path`) to the user → user responds → Pass 2.

After Pass 2, surface the requirements artifact path (e.g. `aidlc-docs/inception/requirements/<run-id>-requirements.md`) and wait for approval:
- **Approve / LGTM / Continue** → proceed to Step 5.
- **Request changes** → re-run requirements-analyst Pass 2 with revision context.
- **Cancel** → mark run as cancelled, stop.

- **skills_required**: `[using-agent-skills, idea-refine, spec-driven-development, requirements-intelligence]`
- **predecessor_artifacts**: workspace-scout output; copy `workspace_state` block
- **depth_override**: none — analyst determines depth normally
- **state on Pass 2 success**:
  1. `Current Stage: PRODUCT - Requirements Analysis (complete)`
  2. `Stage Progress`: mark `[x] Requirements Analysis — <ISO date>`

## Step 5 — Story Writer (always, two-pass, inline) + approval

**Always run** — not gated on scope or complexity (product harness always needs personas + stories).

Execute `stage/story-writer.md` inline per [post-execution loop](spawn-loop.md).

**Two-pass**: Pass 1 emits questions → **SURFACE the questions file path** (from `questions_artifact_path`) to the user → user responds → Pass 2.

After Pass 2, surface the personas and stories artifact paths and wait for approval:
- **Approve / LGTM / Continue** → proceed to Step 6.
- **Request changes** → re-run story-writer Pass 2 with revision context.
- **Cancel** → mark run as cancelled, stop.

- **skills_required**: `[using-agent-skills, spec-driven-development]`
- **predecessor_artifacts**: requirements-analyst Pass 2 output
- **state on Pass 2 success**: `Current Stage: PRODUCT - Story Writing (complete)`; manifest `current_stage: workflow-planner`

## Step 6 — Workflow Planner (inline, opus, minimal depth)

Execute `stage/workflow-planner.md` inline per [post-execution loop](spawn-loop.md).

- **model**: opus
- **skills_required**: `[using-agent-skills, planning-and-task-breakdown]`
- **predecessor_artifacts**: requirements + stories (both Pass 2 outputs)
- **depth_override**: `minimal` — product harness; plan is for discovery, not construction
- **units**: planner may emit units but unit-decomposer does NOT run
- **approval gate**: surface the plan file (with actual run_id — e.g. `aidlc-docs/inception/plans/2026-05-23T13-10-58Z-dragon-ball-z-app-execution-plan.md`) to user, wait for approval. Log answer to audit. Re-run planner if user requests changes.
- **state on approval**: `Current Stage: PRODUCT - Execution Plan (complete)`; manifest `current_stage: complete`

## Step 7 — Auto-commit + completion

On workflow-planner approval:
```bash
git add -A && git commit -m "docs(product-harness): complete product discovery for <run-id>"
```

Surface to user (MUST substitute actual run_id for every `<run-id>` below — do NOT output the literal text `<run-id>`):
```
run_id:           <run-id>
harness:          product

Artifacts:
  requirements:   aidlc-docs/inception/requirements/<run-id>-requirements.md
  personas:       aidlc-docs/inception/user-stories/<run-id>-personas.md
  stories:        aidlc-docs/inception/user-stories/<run-id>-stories.md
  execution-plan: aidlc-docs/inception/plans/<run-id>-execution-plan.md

Skill compliance: <table>
```

**Do NOT offer `/factory-build`** — product harness terminates here. If user wants to proceed to construction, they start a new run with `/factory-spec`.

---

## Hard rules

- Validate every input AND output. No exceptions.
- Sequential only — no parallel Task() calls.
- audit.md is append-only, orchestrator-owned.
- story-writer ALWAYS runs in product harness — no scope/complexity gate.
- workflow-planner depth is always `minimal` in product harness.
- No complexity routing — `factory_complexity.py` is NOT called.
- No unit-decomposer, no build, no review, no ship.
- Approval gates pause; never auto-approve.
