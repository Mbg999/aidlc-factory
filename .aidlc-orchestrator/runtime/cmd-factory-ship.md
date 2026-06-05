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
- **Auto-commit**: `docs(ship): release prep complete`.
- **Final state**: `Current Stage: OPERATIONS` (or `CONSTRUCTION - Complete` if user opts not to deploy).
- Present completion + summary of all stages.
