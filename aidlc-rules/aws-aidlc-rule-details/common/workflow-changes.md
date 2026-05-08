# Mid-Workflow Changes

## Change Types Quick Reference

| Change | Handling | Key Rule |
|--------|----------|----------|
| **Add skipped stage** | Check prerequisites → add to plan → execute normally | Log in audit.md |
| **Skip planned stage** | Warn about impact → get explicit confirmation → mark SKIPPED | May break downstream deps |
| **Restart current stage** | Offer modify vs restart → archive existing → reset → re-execute | Always archive first |
| **Restart previous stage** | Assess cascade → warn about ALL dependent stages → archive all → reset chain | Full cascade reset required |
| **Change depth** | Update plan → adjust approach → inform timeline change | See depth-levels.md |
| **Pause workflow** | Complete current step → update checkboxes → update state → log | Provide resume instructions |
| **Change architecture** | Assess progress → cascade impact depends on how far along → restart from Application Design | Earlier = less impact |
| **Add/remove units** | Assess completed designs → update unit artifacts → reset affected units | Redistribute functionality if removing |

## General Guidelines

### Before Changes
1. Understand the request (ask clarifying questions)
2. Assess impact (all affected stages, artifacts, dependencies)
3. Explain consequences (what must be redone, timeline impact)
4. Offer alternatives (modification vs restart)
5. Get explicit confirmation

### During Changes
1. Archive existing work before destructive changes
2. Keep `aidlc-state.md`, plan files, `audit.md` in sync
3. Validate changes are consistent across artifacts

### After Changes
1. Verify consistency across all artifacts
2. Update all references
3. Log change history in `audit.md`
4. Confirm with user

## Decision Tree
```
Change request →
  Current stage? → Modify or restart current stage
  Completed stage? → Low impact: modify + update dependents / High impact: restart from that stage
  Adding skipped stage? → Check prerequisites, add, execute
  Skipping planned stage? → Warn, confirm, skip
  Changing depth? → Update plan, adjust approach
```

## Logging Format
```markdown
## Change Request - [Stage]
**Timestamp**: [ISO] | **Request**: [what] | **Impact**: [affected stages/artifacts]
**Confirmation**: [user response] | **Action**: [what was done]
```
