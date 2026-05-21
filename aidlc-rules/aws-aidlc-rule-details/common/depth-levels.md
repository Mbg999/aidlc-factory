# Adaptive Depth

## Core Principle
When a stage executes, create all defined artifacts. "Depth" = detail level; adapts to problem complexity.

- **Stage selection** (binary): Workflow Planning decides EXECUTE or SKIP
- **Detail level** (adaptive): Model decides based on problem characteristics

## Factors Influencing Detail
1. Request clarity/completeness
2. Problem complexity
3. Scope (single file → system-wide)
4. Risk level (impact of errors)
5. Available context (greenfield vs brownfield)
6. User preferences (brevity vs thoroughness)

## Examples

| Stage | Simple (e.g., bug fix) | Complex (e.g., migration) |
|-------|----------------------|--------------------------|
| **Requirements** | Concise functional req; minimal sections | Full functional + NFR; traceability; acceptance criteria |
| **App Design** | Basic component description; key methods | Detailed responsibilities; method signatures; patterns |

## Guiding Principle
*"Create exactly the detail needed — no more, no less."*
Don't inflate simple problems. Don't shortchange complex ones.

---

## Token Efficiency: Silent vs. Spoken Steps

**Goal**: Minimize tokens consumed on internal analysis. Speak only when user input or review is required.

### Silent Steps (NO chat output — execute internally)
These steps MUST be performed but MUST NOT produce chat messages:

| Step | What to do silently |
|------|---------------------|
| Loading rule files | Read files; apply rules. Do not narrate "I am now loading..." |
| Loading prior artifacts | Read requirements, plans, design docs. Do not summarize back what was just written. |
| Workspace scanning | Detect file types, build system, project structure. No verbose listing. |
| Stage selection logic | Decide EXECUTE/SKIP per unit. No step-by-step explanation in chat. |
| Skill file loading | Read SKILL.md files. Do not narrate "I am now reading incremental-implementation skill..." |
| Extension opt-in scan | Scan extensions/ directory. No directory listing in chat. |
| Checkpoint verifications | Audit completeness, state checks (from stage-conventions.md). Silent pass/fail only. |
| Plan checkbox updates | Mark `[x]` in plan files. Do not announce each checkbox individually. |
| `aidlc-state.md` updates | Write state updates. Do not produce a separate chat message. |
| Git commits | Execute `git add -A && git commit`. One-line confirmation only if successful. |

### Spoken Steps (PRODUCE chat output)
Only these steps produce messages to the user:

| Step | Output type |
|------|-------------|
| Clarifying questions | Question file + brief chat prompt to review |
| Plan presentation | Full plan for approval |
| Stage completion messages | Per `stage-conventions.md` Completion Message Protocol |
| Blocking errors | Brief error + specific action needed |
| Skill compliance summary | Table in completion message only |
| Session resumption | Welcome back summary (max 5 bullets) |

### Compression Rules for Spoken Output
- **Analysis summaries**: Max 5 bullets. No prose paragraphs for internal reasoning.
- **Skipped stages**: One line only — `Stage X: SKIP — [one-phrase reason]`. Do not explain in multiple sentences.
- **Skill loading**: Do not narrate loading. Only surface skill results in the completion message compliance table.
- **Context recap**: When resuming, max 3-line context recap before proceeding. Do not re-summarize every artifact.
- **Loading confirmations**: No "I have read X, Y, Z files" messages. Just proceed.
