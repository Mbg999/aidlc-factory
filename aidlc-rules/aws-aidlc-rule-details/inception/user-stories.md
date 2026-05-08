# User Stories

## Purpose
Convert requirements into user-centered stories with acceptance criteria and personas.

## Prerequisites
- Workspace Detection complete
- Requirements Analysis recommended
- Workflow Planning shows this stage

## Agent Skills
- `spec-driven-development/SKILL.md` — Enforce spec-before-code; ensure stories have objectives, boundaries, success criteria.

## Assessment: When to Execute

**ALWAYS execute** for: user-facing features, UX/workflow changes, multi-persona systems, customer-facing APIs, complex business logic, cross-team projects.

**Assess complexity** for: backend changes with user impact, performance improvements with visible benefit, integration work affecting workflows, data/reporting changes, security/auth improvements.
- Execute if ANY: scope across components, ambiguous requirements, high business risk, multiple stakeholders, UAT needed, multiple valid implementations.

**Skip ONLY for**: pure refactoring, small bug fixes, infrastructure-only, dev tooling, docs-only.

**Default**: When in doubt, include user stories.

---

## PART 1: PLANNING

### Step 1: Validate Need
- Document assessment in `aidlc-docs/inception/plans/user-stories-assessment.md`
- Reference: request analysis, user impact, complexity, stakeholders, criteria met, decision + reasoning

### Step 2: Create Story Plan
- Act as product owner; produce checkboxed plan
- Save to `aidlc-docs/inception/plans/story-generation-plan.md`

### Step 3: Generate Questions

**Question categories**:
- **User Personas** — who uses this, roles, needs
- **Story Granularity** — level of detail, story size
- **Story Format** — format preferences, conventions
- **Breakdown Approach** — journey-based, feature-based, persona-based, domain-based, epic-based
- **Acceptance Criteria** — testing approach, definition of done
- **User Journeys** — workflows, touchpoints, entry/exit points
- **Business Context** — goals, constraints, priorities
- **Technical Constraints** — limitations affecting stories

### Step 4: Mandatory Artifacts (include in plan)
- [ ] `stories.md` — INVEST-compliant stories with acceptance criteria
- [ ] `personas.md` — user archetypes mapped to stories

### Step 5: Collect Answers and Resolve Ambiguities
*(Per stage-conventions.md protocol)*

### Step 6: Get Plan Approval
- Do NOT proceed to generation without explicit approval

---

## PART 2: GENERATION

### Step 7: Execute Plan
- Read plan, find next unchecked step
- Execute exactly; generate artifacts per approved methodology
- Mark `[x]` after each step

### Step 8: Verify Completion
- All plan steps `[x]`
- stories.md + personas.md generated
- Stories are INVEST-compliant with acceptance criteria

### Step 9: Present Completion (emoji: 📚)
Artifact path: `aidlc-docs/inception/user-stories/`

---

## Critical Rules
- Context-appropriate questions only; analyze answers for ambiguity
- Explicit approval before generation; follow plan exactly; update checkboxes
- No implementation details (no sprint planning, no technical tasks)
