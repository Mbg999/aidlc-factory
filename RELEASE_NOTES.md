# Release Notes — v0.3.3 (2026-06-10)

### Changed

- <agent-tool>/skills are now thin wrappers of .aidlc-orchestrator/runtime for simplicity and to avoid circular dependencies. See `.claude/commands/factory-*.md` for examples. The old skill files are deleted.
- some cleanings
- use autoskills from npx aidlc-factory/autoskills