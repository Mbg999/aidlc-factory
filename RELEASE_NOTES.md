# Release Notes — v0.3.0 (Proposed)

## Added

- **AI Architecture Cookbook integration** — 43 YAML architectural standards with MCP server, opt-in via `--with-architecture-cookbook` flag
- **Stage agent wiring** — Architecture Cookbook skill loaded in all 7 stage agents (workspace-scout through ship-agent)
- **MCP config generation** — Writes MCP server configuration to 5 targets: `.mcp.json`, `.cursor/mcp.json`, `opencode.json`, `codex.json`, `.vscode/mcp.json`
- **Health check** — `factory_validate.py --check-cookbook` validates cookbook MCP server health and schema compliance
- **JSON Schema contracts** — MCP output validation contracts for architecture cookbook queries
- **Call budget enforcement** — Architecture cookbook usage limited to ≤5 MCP calls per stage, ≤25 per run
- **Graceful degradation** — Inline YAML fallback when MCP server is unavailable; cookbook falls back to embedded standards
- **Cross-platform CI** — GitHub Actions matrix covering Ubuntu, Windows, and macOS for the cookbook MCP server build

## Changed

- **Installer (`install_aidlc.py`)** — Extended with `--with-architecture-cookbook`/`--without-architecture-cookbook` flags; `architecture_cookbook_enabled` feature flag in budget defaults to `false`
- **Node.js detection** — Installer validates Node.js presence before building the cookbook MCP server
- **Changelog discipline** — All releases now follow Keep-a-Changelog format

## Fixed

- **Cross-platform encoding** — MCP server source files handle UTF-8 BOM and CRLF on Windows; path separators normalized for cross-OS compatibility
- **Review findings (P1)** — Variable `node_ok` initialization in `install_aidlc.py:1808`; budget path guard when Node.js is absent
- **Review findings (P2)** — Standardized cookbook gating mechanism across agents; test isolation improvements in E2E tests
- **Review findings (P3)** — MCP target file key mapping documented; error messaging for missing agent files

## Deprecated

*(None in this release)*

## Removed

*(None in this release)*

## Security

- **Supply-chain hardening** — Cookbook repository clone now pinned to a specific commit hash (not `--depth 1` without pinning)
- **npm integrity** — MCP server build uses `npm ci` (enforces lockfile) with `--ignore-scripts`; `npm audit --audit-level=high` run post-install
- **Gitignore coverage** — `.ai-architecture-cookbook/mcp-server/node_modules/` and `dist/` explicitly gitignored to prevent build artifact leakage

---

**Full Changelog**: [v0.2.4...v0.3.0](https://github.com/awslabs/aidlc-workflows/compare/v0.2.4...v0.3.0)
