# Code Generation

## Overview
Generate code per unit in two parts:
- **Part 1 — Planning**: Create step-by-step code generation plan
- **Part 2 — Generation**: Execute approved plan to produce code, tests, artifacts

**Brownfield**: Modify existing files in-place; never create duplicates.

## Prerequisites
- Unit Design Generation complete; NFR Implementation (if executed) complete
- All unit design artifacts available

## Agent Skills (MANDATORY — per stage-conventions.md protocol)
**You MUST load and follow these skills. Skipping is a workflow violation.**

- `environment-detection/SKILL.md` — Detect-before-install discipline for language runtimes and package managers. **Key process**: `command -v <tool>` → USE existing if compatible → prefer fast version managers (nvm / asdf / mise) over brew. **Runs FIRST**, before any install command. Avoids 180s `brew install` source-build timeouts when the tool is already on `$PATH`.
- `incremental-implementation/SKILL.md` — Thin vertical slices: implement → test → verify → commit. **Key process**: one slice at a time, verify before moving to next.
- `test-driven-development/SKILL.md` — Red-Green-Refactor; test pyramid 80/15/5. **Key process**: write failing test FIRST, then implement, then refactor.
- `design-system-composer/SKILL.md` *(UI projects only)* — Design-system-driven composition from INDEX.md primitives with token enforcement. **Key process**: never invent primitives, snap to tokens, Figma resilience.
- `frontend-ui-engineering/SKILL.md` *(UI projects only)* — Component architecture, WCAG 2.1 AA. **Key process**: design system tokens, accessibility from the start.
- `source-driven-development/SKILL.md` *(frameworks only)* — Base decisions on official docs. **Key process**: cite source for every framework API used, flag unverified patterns.
- `git-workflow-and-versioning/SKILL.md` — Trunk-based, atomic commits ~100 lines. **Key process**: commit after each slice, meaningful messages.
- `code-review-and-quality/SKILL.md` — Five-axis self-review, change sizing. **Key process**: before presenting to user, self-review on correctness, readability, architecture, security, performance.

**Inline fallback** (if SKILL.md files not installed):
1. For each code step: write test → implement → run tests → commit (TDD cycle)
2. Keep changes under ~100 lines per commit
3. Verify each slice works before starting next
4. Self-review before presenting: check correctness, readability, security
5. Cite official docs for framework patterns used
- `code-review-and-quality/SKILL.md` — Five-axis self-review, change sizing

---

# PART 1: PLANNING

1. **Analyze Unit Context**: Read design artifacts, story map, identify dependencies
2. **Create Code Generation Plan** (`aidlc-docs/construction/plans/<run-id>-{unit-name}-code-generation-plan.md`):
   - Read workspace root from `aidlc-state.md`; determine code location per Critical Rules
   - Brownfield: review reverse-engineering notes for target files
   - Numbered steps with `[ ]` checkboxes covering:
     - Project structure setup (greenfield only)
     - Business Logic + Unit Tests + Summary
     - API Layer + Unit Tests + Summary
     - Repository Layer + Unit Tests + Summary
     - Frontend Components + Unit Tests (if applicable)
     - Database migrations (if data models exist)
     - Documentation, deployment artifacts
   - Include story traceability and unit dependency context
3. **Summarize Plan**: Present to user with step count and coverage
4. **Get Approval**: Log prompt in audit.md → wait for explicit approval → log response
5. **Update State**: Mark Part 1 complete in `aidlc-state.md`

---

# PART 2: GENERATION

6. **Load Plan**: Read plan → find first `[ ]` → load unit context
7. **Execute Step**:
   - Verify target directory (never aidlc-docs/ for app code)
   - Brownfield: check if file exists → modify in-place (NEVER create `*_modified.*`)
   - Greenfield: create new file
   - Write locations: app code → workspace root; docs → `aidlc-docs/construction/{unit-name}/code/`
   - **`data-testid` (MANDATORY for UI)**: Add `data-testid` to ALL interactive elements (buttons, links, inputs, form controls). Naming: `{component}-{element-role}` (e.g., `pagination-prev-button`, `pokemon-card-link`). Stable across renders. This is NOT optional — omitting `data-testid` is a generation defect.
8. **Update Progress**: Mark `[x]` in plan; mark stories `[x]` when done; update state
9. **Loop**: More steps → go to 6. All done → present completion.
10. **Log in audit.md (MANDATORY per unit)**:
    - `## [timestamp] CONSTRUCTION - Code Generation COMPLETE (Unit: {unit-name})`
    - List all files created/modified
    - Skill compliance entries: `- [Skill] Executed: {skill-name} (Code Generation) — PASS|FAIL`
    - Log user approval prompt and response
    - **If this step is skipped, it is a workflow violation.**

## Completion (Per stage-conventions.md protocol, emoji: 💻)

**Pre-completion verification (BLOCKING)**:
- Confirm `aidlc-docs/construction/plans/<run-id>-{unit-name}-code-generation-plan.md` exists and all checkboxes are `[x]`
- Confirm `aidlc-docs/audit.md` has Construction entries for this unit
- Confirm all interactive UI elements have `data-testid` attributes
- Confirm execution plan in `aidlc-docs/inception/plans/` has updated checkboxes for completed tasks

Include in summary:
- Brownfield: distinguish modified vs created files
- Greenfield: list created files with paths
- List tests, documentation, deployment artifacts

Next stage options: Request Changes / Continue to Next Unit or Build & Test

---

## Critical Rules

### Code Location
- **App code**: Workspace root only (NEVER `aidlc-docs/`)
- **Documentation**: `aidlc-docs/` only
- **Structure by project type**:
  - Brownfield: use existing structure
  - Greenfield single: `src/`, `tests/`, `config/`
  - Greenfield multi (microservices): `{unit-name}/src/`
  - Greenfield multi (monolith): `src/{unit-name}/`

### Brownfield Rules
- Check file exists before generating → if exists: modify in-place → verify no duplicates

### Generation Rules
- **NO HARDCODED LOGIC**: Only execute what's in the plan
- **FOLLOW PLAN EXACTLY**: No deviations from step sequence
- **UPDATE CHECKBOXES (BLOCKING)**: Mark `[x]` in the plan file in the SAME response that completes the step. Do NOT move to the next step with any unchecked `[ ]` behind you. If you realize checkboxes were not updated, stop and update them before continuing.
- **RESPECT DEPENDENCIES**: Only implement when dependencies satisfied
- **END-OF-UNIT CHECKBOX AUDIT**: Before presenting the unit completion message, scan the plan file for any remaining `[ ]` items in this unit. If any are found, mark them `[x]` or explain why they were skipped. A completion message MUST NOT be presented with open `[ ]` items.

### Design System Compliance (UI projects)
- Every UI element MUST map to a primitive from `design-system/INDEX.md`
- Padding, margin, gap MUST use `spacing.*` tokens (4/8/12/16/24/32)
- Border-radius MUST use `radius.*` tokens (0/3/6/12/9999)
- Font-size MUST use `font-size.*` tokens (12/14/16/20/24/32/40)
- Colors MUST use `color.*` semantic tokens, never raw hex
- Shadows MUST use `elevation.*` tokens
- NO Tailwind arbitrary values (`px-[13px]`, `rounded-[5px]`, `gap-[7px]`)
- NO inline style padding/margin/radius/font-size values

**Violation handling**: Each deviation is autocorrected by `ui-constraint-validator`.
If >3 deviations per code-generation slice: halt with `status: blocked`.

### Automation-Friendly UI Code
- Add `data-testid` to ALL interactive elements — this is a **mandatory generation requirement**, not a suggestion
- Naming: `{component}-{element-role}` (e.g., `login-form-submit-button`, `pagination-next-button`)
- Stable IDs across renders; only change when element purpose changes
- **Verification**: Before presenting unit completion, grep generated files for interactive elements (buttons, links, inputs, selects) and confirm each has a `data-testid`
