# Operations

**Purpose**: Placeholder for future operational phases (deployment, monitoring, maintenance)

**Status**: This phase is currently a placeholder and will be expanded in future versions.

## Agent Skills

**MANDATORY** (when this phase is active): Load and follow these skill workflows from `.agents/skills/` (if installed):

- **`git-workflow-and-versioning/SKILL.md`** — Enforce release tagging, semantic versioning, and CHANGELOG generation.
- **`ci-cd-and-automation/SKILL.md`** — Apply Shift Left testing, feature flags, quality gate pipeline, and progressive rollout patterns.
- **`shipping-and-launch/SKILL.md`** — Apply pre-flight readiness checklists, post-deploy smoke tests, and launch coordination.
- **`documentation-and-adrs/SKILL.md`** — Record architectural decisions, maintain living docs, and link code to design rationale.
- **`deprecation-and-migration/SKILL.md`** — Apply structured deprecation flow: announce → migrate → remove. Never surprise-remove.

If a skill directory does not exist, skip silently and proceed with standard behavior.
Log skill application in `aidlc-docs/audit.md`: `[Agent-Skill] Applied: <skill-name> (Operations)`

## Future Scope

The Operations phase will eventually include:
- Deployment planning and execution
- Monitoring and observability setup
- Incident response procedures
- Maintenance and support workflows
- Production readiness checklists

## Current State

All build and test activities have been moved to the CONSTRUCTION phase.
The AI-DLC workflow currently ends after the Build and Test phase in CONSTRUCTION.
