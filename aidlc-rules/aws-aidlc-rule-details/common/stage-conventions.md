# Stage Conventions

**Purpose**: Shared patterns for ALL stages. Each stage file inherits these; do NOT repeat them.

## Agent Skills Protocol (MANDATORY — NOT OPTIONAL)

**Skills are the primary enforcement layer for quality and process.**

When a stage lists required skills:
1. **LOAD**: Read each `.agents/skills/<name>/SKILL.md` from repo-local or user-global location
2. **EXECUTE**: Follow the skill's **Process** section step-by-step — these are instructions, not suggestions
3. **ANTI-RATIONALIZE**: Check the skill's **Common Rationalizations** table — if you're tempted to skip a step, the table tells you why you must not
4. **VERIFY**: Satisfy the skill's **Verification** section — produce concrete evidence (test output, build logs, metrics)
5. **LOG**: Record in `aidlc-docs/audit.md`: `[Skill] Executed: <skill-name> (<Stage-Name>) — PASS|FAIL`
6. **BLOCK on failure**: If verification criteria not met → stage CANNOT complete. Fix first, then re-verify.

**If skill file is missing**:
- The stage rule file embeds critical process steps inline — follow those
- Log warning: `[Skill] MISSING: <skill-name> — using inline fallback process`
- Do NOT skip the process just because the file is absent

**Anti-bypass rules** (HARD CONSTRAINTS):
- "I'll add tests later" → NO. TDD means tests first.
- "It's a simple change" → NO. Simple changes still follow the skill process.
- "Not needed for this project" → NO. If the stage lists the skill, it's needed.
- "I already know this is correct" → NO. Verification requires evidence, not confidence.
- Skipping skill steps without explicit user override is a workflow violation.

## Question Generation Protocol

Every stage that generates questions MUST follow:

1. **DIRECTIVE**: Analyze context artifacts to find ALL areas needing clarification. Ask proactively.
2. **CRITICAL**: If ANY ambiguity or missing detail could affect the stage output, ask rather than assume.
3. **Format**: Use `[Answer]:` tag format per `common/question-format-guide.md`
4. **Principle**: When in doubt, ask the question — overconfidence leads to poor outcomes.
5. **Coverage**: Evaluate ALL listed question categories; don't skip without justification.
6. **MANDATORY follow-up**: After collecting answers, review ALL for vagueness (watch for "depends", "maybe", "not sure", "mix of", "somewhere between"). Create follow-ups for ANY unclear response. Do NOT proceed with ambiguity.

## Plan Creation Protocol

When a stage creates a plan:
- Generate plan with checkboxes `[ ]` for each step
- Save to `aidlc-docs/{phase}/plans/{name}-plan.md`
- Include all `[Answer]:` tags for user input
- Wait for user to fill answers before proceeding

## Completion Message Protocol

Every stage ends with:

```markdown
# [emoji] [Stage Name] Complete - [unit-name if applicable]

[AI Summary: bullet-point list of what was produced. Factual only — no workflow instructions.]

### Skill Compliance
| Skill | Status | Evidence |
|-------|--------|----------|
| <skill-name> | ✅ PASS / ❌ FAIL / ⚠️ N/A | <brief evidence> |

> **📋 <u>**REVIEW REQUIRED:**</u>**  
> Please examine artifacts at: `[artifact-path]`

> **🚀 <u>**WHAT'S NEXT?**</u>**
>
> **You may:**
>
> 🔧 **Request Changes** - Ask for modifications based on your review  
> ✅ **Continue to Next Stage** - Approve and proceed to **[next-stage-name]**
```

## Approval Protocol

1. Wait for explicit, unambiguous user approval
2. If changes requested → update artifacts, repeat approval
3. Log approval + timestamp in `aidlc-docs/audit.md`
4. Mark stage complete in `aidlc-docs/aidlc-state.md`
5. **Auto-commit**: After updating state, run `git add -A && git commit -m "<type>(<scope>): <description>"` where:
   - `<type>` = `docs` for plans/questions, `feat` for code generation, `build` for build & test artifacts
   - `<scope>` = stage name in kebab-case (e.g., `requirements-analysis`, `functional-design`)
   - `<description>` = concise summary of what was approved (e.g., "complete requirements analysis", "approve unit-auth code generation plan")
   - If the commit fails (nothing to commit, git not initialized), log warning in `audit.md` and continue — do NOT block workflow

## Auto-Commit Triggers

**MANDATORY**: A git commit MUST be created automatically (no user prompt) whenever:
- A **plan is approved** by the user (commit the plan + any generated questions)
- A **stage completes** and user approves to continue (commit all stage artifacts)
- A **unit construction phase** finishes (commit unit artifacts)
- **Code generation** completes a step or unit (commit generated code + updated plan checkboxes)
- The user says **"continue"**, **"next"**, **"approve"**, or any equivalent progression

**Commit format**: `<type>(<scope>): <description>`
**Always stage all changes**: `git add -A` before committing to capture all artifact updates
