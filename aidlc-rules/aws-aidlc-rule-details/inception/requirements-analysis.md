# Requirements Analysis (Adaptive)

**Role**: Product owner

Always executes. Depth adapts to complexity (see [depth-levels.md](../common/depth-levels.md)).

## Prerequisites
- Workspace Detection complete
- Reverse Engineering complete (if brownfield)

## Agent Skills (MANDATORY — per stage-conventions.md protocol)
**You MUST load and follow these skills. Skipping is a workflow violation.**

- `idea-refine/SKILL.md` — Divergent→convergent thinking to explore problem space. **Key process**: explore multiple approaches before converging on one; follow Process steps; check Rationalizations table.
- `spec-driven-development/SKILL.md` — Write spec (PRD): objectives, scope, constraints, boundaries. **Key process**: produce structured spec covering all areas; follow verification exit criteria.

**Inline fallback** (if SKILL.md files not installed):
1. Explore the problem space: list ≥3 possible approaches before choosing one
2. Write a structured spec: objectives, core features, constraints, boundaries, testing strategy
3. Verify: spec covers all areas identified in completeness analysis
4. Do NOT proceed to next stage without a written, reviewable spec artifact

## Steps

### Step 1: Load Reverse Engineering Context (if brownfield)
- Load architecture.md, component-inventory.md, technology-stack.md from `aidlc-docs/inception/reverse-engineering/`

### Step 2: Analyze User Request

**Classify**:
- **Clarity**: Clear / Vague / Incomplete
- **Type**: New Feature | Bug Fix | Refactoring | Upgrade | Migration | Enhancement | New Project
- **Scope**: Single File | Single Component | Multiple Components | System-wide | Cross-system
- **Complexity**: Trivial | Simple | Moderate | Complex

### Step 3: Determine Depth
- **Minimal**: request clear & simple
- **Standard**: needs clarification, normal complexity
- **Comprehensive**: complex, high-risk, many stakeholders

### Step 4: Assess Current Requirements
- Intent statements (logged in audit.md)
- Existing requirements docs (search workspace)
- Pasted content or file references
- Convert non-markdown to markdown as needed

### Step 5: Completeness Analysis

Evaluate ALL areas:
- Functional requirements
- Non-functional (performance, security, scalability, usability)
- User scenarios (use cases, journeys, edge cases)
- Business context (goals, constraints, success criteria)
- Technical context (integrations, data needs, boundaries)
- Quality attributes (reliability, maintainability, testability, accessibility)

### Step 5.1: Extension Opt-In Prompts

Scan loaded `*.opt-in.md` files → add their `## Opt-In Prompt` question to the questions file (Step 6).

After answers, record in `aidlc-docs/aidlc-state.md`:
```markdown
## Extension Configuration
| Extension | Enabled | Decided At |
|---|---|---|
| [Name] | [Yes/No] | Requirements Analysis |
```
For opted-IN: load full rules (strip `.opt-in.md` → `.md`). For opted-OUT: never load.

### Step 6: Generate Clarifying Questions
- ALWAYS create `aidlc-docs/inception/requirements/requirement-verification-questions.md` unless exceptionally clear
- Cover functional, non-functional, user scenarios, business context
- Use `[Answer]:` tag format; multiple-choice with X) Other
- Wait for user answers; analyze; follow up if needed

### ⛔ GATE: Await User Answers
Do NOT proceed until all questions answered and validated.

### Step 7: Generate Requirements Document
- Create `aidlc-docs/inception/requirements/requirements.md`
- Include: intent analysis, functional + non-functional reqs, user answers incorporated

### Step 8: Update State
Mark Requirements Analysis complete in `aidlc-docs/aidlc-state.md`.

### Step 9: Present Completion (emoji: 🔍)
Artifact path: `aidlc-docs/inception/requirements/`
- Log approval with timestamp in audit.md
