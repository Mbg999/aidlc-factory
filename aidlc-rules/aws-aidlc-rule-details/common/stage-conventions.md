# Stage Conventions

**Purpose**: Shared patterns for ALL stages. Each stage file inherits these; do NOT repeat them.

## Agent Skills Protocol

When a stage lists skills:
1. Load each listed `.agents/skills/<name>/SKILL.md` IF the directory exists
2. If directory missing → skip silently, proceed with standard behavior
3. Log in `aidlc-docs/audit.md`: `[Agent-Skill] Applied: <skill-name> (<Stage-Name>)`

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
