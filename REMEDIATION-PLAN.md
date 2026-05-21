# Remediation Plan — Workflow Enforcement Gaps

**Date**: 2026-05-08
**Source**: Post-usage audit of `pruebaaidlcv2` (Pokédex greenfield project)
**Goal**: Reinforce rule files so agents cannot skip Construction-phase logging, artifacts, state updates, or UI automation attributes.

---

## Findings Summary

| # | Severity | Finding | Root Cause |
|---|----------|---------|------------|
| 1 | Critical | Construction phase absent from `audit.md` | No reinforcement/reminder at Construction entry point |
| 2 | Critical | Audit timestamps wrong / out-of-order | No explicit ordering rule in audit format |
| 3 | Moderate | Empty `aidlc-docs/construction/` — no plans or build-test artifacts | Agent skipped artifact generation steps |
| 4 | Moderate | `aidlc-state.md` Current Stage stuck on old value | No rule enforcing Current Stage field update |
| 5 | Minor | Execution plan checkboxes never marked `[x]` | Checkpoint update rule exists but was not followed |
| 6 | Minor | No `data-testid` on interactive elements | Rule buried at bottom of code-generation.md |
| 7 | Minor | Application Design / Units Generation missing from audit | Same as #1 — agent fatigue after Inception |

---

## Remediation Steps

### Step 1 — `core-workflow.md`: Add Construction Entry Checkpoint
**File**: `aidlc-rules/aws-aidlc-rules/core-workflow.md`
**What**: Add a `## MANDATORY: Construction Phase Entry Checkpoint` block before the Construction section. This checkpoint verifies:
- All Inception stages have audit entries
- `aidlc-state.md` Current Stage is updated
- `aidlc-docs/construction/` directory exists
- Remind that every unit's code-gen plan must be written to `aidlc-docs/construction/plans/`

Also add explicit Construction audit logging requirements inline (per-unit skill compliance, plan approval, code gen completion, build & test completion).

**Status**: [x] — Added `MANDATORY: Construction Phase Entry Checkpoint`, `MANDATORY: Construction Audit Logging`, `MANDATORY: Construction Artifact Generation`, and `MANDATORY: State Tracking` sections. Also added chronological timestamp rule and fixed `aidlc-docs/build-and-test/` → `aidlc-docs/construction/build-and-test/` path.

### Step 2 — `stage-conventions.md`: Add Anti-Fatigue Checkpoint & Timestamp Rule
**File**: `aidlc-rules/aws-aidlc-rule-details/common/stage-conventions.md`
**What**:
- Add a `## Phase Transition Checkpoint` section: before starting a new phase, the agent MUST verify audit completeness for the previous phase.
- Add a `## Audit Timestamp Rules` section: entries must be chronological, Workspace Detection is always first, timestamps must reflect actual sequence.
- Strengthen `Current Stage` update in the Approval Protocol: agent MUST update `Current Stage` in `aidlc-state.md` to reflect the stage just completed.

**Status**: [x] — Added step 5 (`Update Current Stage`) to Approval Protocol, new `Phase Transition Checkpoint (MANDATORY)` section, and new `Audit Timestamp Rules` section.

### Step 3 — `code-generation.md`: Elevate `data-testid` & Strengthen Audit
**File**: `aidlc-rules/aws-aidlc-rule-details/construction/code-generation.md`
**What**:
- Move `data-testid` from "Critical Rules" footer to a mandatory checklist item in PART 2 Step 7 (the generation step).
- Add explicit audit logging step after each unit's code generation completion (not just plan approval).
- Add a "Construction Artifacts Verification" gate: before presenting completion, verify that `aidlc-docs/construction/plans/{unit-name}-code-generation-plan.md` exists and has checkboxes updated.

**Status**: [x] — `data-testid` elevated to mandatory inline in Step 7, added Step 10 for per-unit audit logging, added pre-completion verification gate with 4 blocking checks.

### Step 4 — `build-and-test.md`: Strengthen Artifact Verification
**File**: `aidlc-rules/aws-aidlc-rule-details/construction/build-and-test.md`
**What**:
- Add a pre-step verification: confirm all unit code-gen plans have `[x]` checkboxes.
- Strengthen Step 10 (audit logging): make it a mandatory gate with explicit format showing build status, test status, skill compliance.
- Add verification that `aidlc-docs/construction/build-and-test/` directory has the required files before presenting completion.

**Status**: [x] — Added Pre-Step Verification (4 blocking checks), strengthened Step 9 with pre-completion verification, and added explicit audit format template in Step 10.

### Step 5 — `core-workflow.md`: Strengthen `aidlc-state.md` Update Rules
**File**: `aidlc-rules/aws-aidlc-rules/core-workflow.md`
**What**:
- Add a `## MANDATORY: State Tracking` section near the top, specifying:
  - `Current Stage` MUST be updated after EVERY stage completion
  - Execution plan checkboxes MUST be marked `[x]` as tasks complete
  - Stage Progress list MUST match audit.md entries

**Status**: [x] — Merged into Step 1 (`core-workflow.md` MANDATORY: State Tracking section).

### Step 6 — Validate Changes
**What**: Diff all modified files against originals to confirm changes are clean and non-breaking.

**Status**: [x] — 4 files modified, 113 insertions, 6 deletions. No lint/parse errors. All diffs verified.
