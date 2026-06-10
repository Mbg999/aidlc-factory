# `/factory-ship` — Phase 1 ship

PRIORITY: P2

Final stage. Execute `stage/ship-agent.md` inline per the
[post-execution loop](spawn-loop.md).

> **Framework skills** are available here if `/factory-build` ran first (stored in
> `manifest.skill_paths_resolved`). Ship agent inherits this list from the manifest.

Stage-specific knobs:
- **skills_required**: `[shipping-and-launch, git-workflow-and-versioning, ci-cd-and-automation, documentation-and-adrs]`. Add `deprecation-and-migration` if `manifest.project_profile.has_legacy == true`.
- **Design system**: if `manifest.project_profile.ui == true` AND `manifest.project_profile.design_system_path` is set, inject `design_system_path` into ship-agent input so UI example capture and INDEX.md update-index run.
- **Output artifacts**: `RELEASE_NOTES.md`, `aidlc-docs/operations/adrs/`, CI/CD files, updated `CHANGELOG.md`, (conditional) updated `design-system/INDEX.md` usage stats.

## Approval gate

After ship-agent completes, surface the produced artifacts:
- `RELEASE_NOTES.md`: summary of key changes
- ADRs created
- CI/CD files changed
- `CHANGELOG.md` updates
- Version proposal

Wait for user response:
- **Approve / LGTM / Continue** → proceed to auto-commit + present completion.
- **Request changes** → re-run ship-agent with revision context.
- **Cancel** → mark run as cancelled, stop.

## Auto-commit + present completion

On approval:
```bash
git add -A && git commit -m "docs(ship): release prep complete"
```

Update state to `Current Stage: OPERATIONS` (or `CONSTRUCTION - Complete` if user opts not to deploy).

Present completion + summary of all stages:
```
Run complete: <run-id>

Artifacts:
  RELEASE_NOTES.md
  ADRs: <N> created
  CHANGELOG.md updated
  CI/CD: <files>

Full pipeline complete. The full audit trail is in aidlc-docs/audit.md.
```

The run is complete. No further commands to suggest (this is the final stage).
Remind the user to manually push tags and remote branches after reviewing the commits.

**Safety rule**: This stage does NOT push tags or remote branches. The user pushes manually after reviewing the commits.
