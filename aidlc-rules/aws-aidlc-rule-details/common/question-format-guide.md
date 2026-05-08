# Question Format Guide

## MANDATORY: All Questions in Dedicated Files

**CRITICAL**: Never ask questions in chat. All questions go in `.md` files.

### File Format
- Naming: `{phase-name}-questions.md`
- Location: `aidlc-docs/`

### Question Template
```markdown
## Question [N]
[Clear, specific question]

A) [Option]
B) [Option]
X) Other (please describe after [Answer]: tag below)

[Answer]: 
```

**Rules**:
- "Other" MANDATORY as LAST option
- Only meaningful options (min 2 + Other, max 5 + Other)
- Options must be mutually exclusive and realistic

### User Response
Users fill letter after `[Answer]:` tag. If "Other", add description.

### Processing Responses
1. Wait for user to say "done"/"completed"
2. Read file, extract answers after `[Answer]:` tags
3. Validate all answered
4. Handle errors:
   - Missing answer → ask user to complete
   - Invalid letter → ask for valid choice
   - Explanation instead of letter → ask for letter or "Other"

## Contradiction & Ambiguity Detection

**MANDATORY** after reading responses: check for contradictions.

**Common contradictions**:
- Scope vs impact mismatch (e.g., "bug fix" but "entire codebase")
- Risk vs changes mismatch (e.g., "low risk" but "breaking changes")
- Timeline vs complexity mismatch

**If detected**: Create `{phase-name}-clarification-questions.md`:
1. State which answers conflict and why
2. Ask targeted resolution questions (same format)
3. Do NOT proceed until contradictions resolved
4. Re-validate after clarifications

## Workflow
1. Create question file → 2. Inform user → 3. Wait for completion → 4. Read & validate → 5. Check contradictions → 6. Proceed
