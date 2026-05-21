# Post-Update Compression Guide

**Purpose**: After pulling official upstream updates into `aidlc-rules/aws-aidlc-rule-details/`, run this procedure to re-compress files and maintain the ~59% token reduction.

## Constraints

- **NEVER** modify `*.original.md` files — these are backups of the uncompressed originals.
- Preserve all `Agent Skills Protocol` references and `SKILL.md` paths.
- Preserve all extension opt-in semantics and blocking enforcement behavior.
- Keep `common/stage-conventions.md` as the single source of truth for shared patterns.

## Pre-Compression Checklist

```bash
# 1. Baseline word count
find . -name "*.md" ! -name "*.original*" -exec cat {} + | wc -w

# 2. Back up any NEW files that don't have .original.md yet
for f in $(find . -name "*.md" ! -name "*.original*"); do
  [[ ! -f "${f%.md}.md.original.md" ]] && cp "$f" "${f%.md}.md.original.md"
done

# 3. Check for broken references
grep -rn "content-validation\|overconfidence-prevention\|welcome-message\|terminology\.md" . --include="*.md" | grep -v ".original"
```

## Compression Tiers (apply in order)

### Tier 1 — Dead-Weight Removal & Merges

1. **Identify duplicated content** across files (grep for repeated paragraphs).
2. **Merge** any new standalone terminology/glossary files into `common/process-overview.md`.
3. **Merge** any new content-validation rules into `common/ascii-diagram-standards.md`.
4. **Delete** files that are now redundant (update references first).

### Tier 2 — Stage File Compression

For each stage file (`inception/*.md`, `construction/*.md`):

1. **Remove** any inline protocol text that duplicates `common/stage-conventions.md`:
   - Question Generation Protocol
   - Plan Creation Protocol
   - Completion Message templates
   - Approval Protocol
   - Agent Skills Protocol (the *process* — keep the *skills list*)
2. **Replace** with a single reference line: `> Follows protocols in `common/stage-conventions.md``
3. **Keep** stage-specific content: purpose, inputs/outputs, skill paths, question categories, unique rules.
4. **Compress prose** → bullet points. Remove filler words, redundant examples, repeated warnings.

### Tier 3 — Reference File Compression

For files under `common/`:

1. Convert long explanatory paragraphs to terse bullet lists.
2. Collapse multi-paragraph examples into single-line patterns.
3. Remove "why" explanations — keep only "what" and "how".
4. Deduplicate any content already covered by `stage-conventions.md`.

### Tier 4 — Extension Rule Compression

For files under `extensions/`:

1. Preserve opt-in semantics and blocking enforcement behavior.
2. Compress checklists: merge similar items, remove verbose descriptions.
3. Keep all tool/command references intact.
4. Reduce examples to minimal illustrative patterns.

## Post-Compression Verification

```bash
# 1. Final word count (target: ≤12,000 words)
find . -name "*.md" ! -name "*.original*" -exec cat {} + | wc -w

# 2. Per-file sizes (flag anything >1500 words for further compression)
find . -name "*.md" ! -name "*.original*" -exec wc -w {} + | sort -n

# 3. Broken references check
grep -rn "content-validation\|overconfidence-prevention\|welcome-message\|terminology\.md" . --include="*.md" | grep -v ".original"

# 4. Agent Skills presence (must find matches)
grep -rn "SKILL\.md\|Agent.Skill" . --include="*.md" | grep -v ".original"

# 5. Extension opt-in semantics preserved
grep -rn "opt-in\|ENABLED_EXTENSIONS\|blocking" . --include="*.md" | grep -v ".original"
```

## Key Architecture Decisions

| Decision | Rationale |
|----------|-----------|
| `stage-conventions.md` centralizes shared protocols | Eliminates ~200 words repeated per stage file |
| Stage files keep only: purpose, I/O, skills, questions, unique rules | Maximum compression without losing enforcement |
| `.original.md` backups never touched | Safe rollback path; diff source for upstream merges |
| Extensions keep opt-in + blocking semantics | Core workflow correctness depends on these |
| `process-overview.md` holds glossary + overview | Single load for welcome message generation |

## Upstream Merge Workflow

1. Pull upstream changes into a branch.
2. For each changed file, diff against its `.original.md` to identify **new content**.
3. Update the `.original.md` backup: `cp updated-file.md updated-file.md.original.md`.
4. Apply compression tiers above to the new content only.
5. Run the full verification suite.
6. Commit with message: `chore: compress upstream update [date]`.
