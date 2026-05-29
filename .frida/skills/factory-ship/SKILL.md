---
name: factory-ship
description: Run AIDLC ship stage — release notes, ADRs, CHANGELOG, version proposal, optional CI/CD wiring and migration plan. Final stage of the orchestrator.
---

# factory-ship — AIDLC Ship

Adopt the role from `.aidlc-orchestrator/agents/orchestrator.md` and execute the
`/factory-ship <run-id>` sequence.

**Run id:** the run-id provided by the user.

Sequence:
1. Read `manifest.yaml`. Refuse if review hasn't completed with user approval.
2. **ship-agent** — spawn with `predecessor_artifacts` = all prior outputs +
   the merged review report. Pass `manifest.project_profile` so the agent
   knows whether to load `deprecation-and-migration*` (when `has_legacy: true`).
3. Validate output. Expected fields include `version_proposal` and `adr_count`.
4. If `status: needs_human` (version bump or release plan needs user OK):
   surface, wait, log answer to audit:
   ```bash
   python3 aidlc-scripts/factory_run.py emit_audit_block <run-id> \
       --evt user_decision --stage ship-agent --phase OPERATIONS \
       --label "User Decision (ship-agent)" \
       --field decision=<approve|reject|amend> \
       --bullet "[User] <summary>"
   ```
5. Log completion to audit:
   ```bash
   python3 aidlc-scripts/factory_run.py emit_audit_block <run-id> \
       --evt orchestrator_note --phase OPERATIONS \
       --label "Ship Complete" \
       --field summary="Version <X.Y.Z> proposed · <N> ADRs written · release notes ready" \
       --bullet "[Ship] <summary>"
   ```
   Update state file to `Current Stage: OPERATIONS`
   (or `CONSTRUCTION - Complete` if user opts not to deploy).
6. Auto-commit `docs(ship): release prep complete`.
7. Present final summary:
   - All stages with skill-compliance recap
   - Version proposal + ADR count
   - Release notes path
   - "Ready to push: review the commits before `git push`"

Hard rules from `.aidlc-orchestrator/agents/orchestrator.md` apply.
**This agent does NOT push tags or remote branches.** User pushes manually.
