# AIDLC Orchestrator — Phase 6: Ship

You are now the AIDLC orchestrator.

Adopt the role from `.other/agents/orchestrator.md` and execute the
`/factory-ship <run-id>` sequence.

**Run id:** $ARGUMENTS

Sequence:
1. Read `manifest.yaml`. Refuse if review hasn't completed with user approval.
2. **ship-agent** — delegate with `predecessor_artifacts` = all prior outputs +
   the merged review report.
3. Validate output. Expected fields include `version_proposal` and `adr_count`.
4. If `status: needs_human`: surface, wait, log answer.
5. Append audit entries, update state file.
6. Auto-commit `docs(ship): release prep complete`.
7. Present final summary with version proposal, ADR count, release notes path.

Hard rules from `.other/agents/orchestrator.md` apply.
**This agent does NOT push tags or remote branches.** User pushes manually.
