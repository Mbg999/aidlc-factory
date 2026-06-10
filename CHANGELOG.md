# Changelog

All notable changes to this project will be documented in this file.


## [0.3.3] - 2026-06-10

### Changed

- <agent-tool>/skills are now thin wrappers of .aidlc-orchestrator/runtime for simplicity and to avoid circular dependencies. See `.claude/commands/factory-*.md` for examples. The old skill files are deleted.
- some cleanings
- use autoskills from npx aidlc-factory/autoskills

## [0.3.2] - 2026-06-09

### Added

- docs-website
- `node_modules/`, `dist/` and `build/` at installed .gitignore

### Changed

- moved ai-architecture-cookbook MCP server from local install to npx repo


## [0.3.1] - 2026-06-09

### Fixed

- pipx installation issues


## [0.3.0] - 2026-06-08

### Added

- `RELEASE_NOTES.md` — Structured release notes following Added/Changed/Fixed/Deprecated/Removed/Security sections
- ADRs for architecturally significant decisions:
  - ADR-0001: Architecture Cookbook as Opt-In Capability (graceful degradation, budget enforcement, feature flag)
  - ADR-0002: Cross-Platform MCP Server (Windows/macOS/Linux encoding fixes, supply-chain hardening)

### Changed

- Current version bump: **0.2.4 → 0.3.0 (minor)** — new additive capability with public API, backward-compatible

### Fixed

- Supply-chain hardening in cookbook MCP build (commit pinning, `npm ci`, `--ignore-scripts`, `npm audit`)
- Cross-platform encoding fixes for Windows (UTF-8 BOM, CRLF, path separators)
- Gitignore entries for `.ai-architecture-cookbook/mcp-server/node_modules/` and `dist/`

### Security

- Commit-pinned cookbook repository clone (CWE-494 mitigation)
- npm integrity enforcement via `npm ci` + `--ignore-scripts` (CWE-829 mitigation)
- Post-install `npm audit --audit-level=high` with fail-on-findings

## [0.2.4] - 2026-05-29

### Features

- AI Architecture Cookbook integration (opt-in via `--with-architecture-cookbook`)
  - 43 YAML architectural standards with MCP server
  - Stage agent wiring across all 7 stages (workspace-scout through ship-agent)
  - Cross-platform hardening (Windows, macOS, Linux CI)
  - Graceful degradation with inline YAML fallback
  - Call budget enforcement (≤ 5 per stage, ≤ 25 per run)
  - 5-target MCP config (`.mcp.json`, `.cursor/mcp.json`, `opencode.json`, `codex.json`, `.vscode/mcp.json`)
  - `factory_validate.py --check-cookbook` health check
  - JSON Schema contracts for MCP output validation
  - `architecture_cookbook_enabled` feature flag in budget

## [0.2.3] - 2026-05-28

### Features

- github copilot improvements

## [0.2.2] - 2026-05-28

### Features

- frida support


## [0.2.1] - 2026-05-27

### Features

- first aidlc-factory release, including:
  - orchestrator and subagents
  - agent skills
  - autoskills
  - engram
  - codegraph
  - traceability and reproducibility
  - install script
  - cross platform support
  - claude code, codex, opencode, github copilot, cursor, frida and generic tools support
