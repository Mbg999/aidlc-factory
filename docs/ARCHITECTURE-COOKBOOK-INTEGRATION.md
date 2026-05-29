# AI Architecture Cookbook Integration

The AIDLC Factory integrates the [AI Architecture Cookbook](https://github.com/Mbg999/AI-Architecture-Cookbook) — 43 machine-readable YAML standards covering authentication, API design, infrastructure, security, and more — as an opt-in, additive capability.

## What it does

The Cookbook provides architectural pattern recommendations, decision trees, verification checklists, and implementation guidance to AIDLC stage agents via an MCP (Model Context Protocol) server. Each stage agent can query the Cookbook for domain-specific standards, then apply them during workspace scouting, requirements analysis, code generation, and review.

## How to install

```bash
# From an AIDLC project root:
python aidlc-scripts/install_aidlc.py --tool opencode --with-architecture-cookbook

# Or with pipx:
pipx run aidlc-factory-installer --tool claude --with-architecture-cookbook --dest ./my-project
```

The installer:
1. Copies the Cookbook repo to `./.ai-architecture-cookbook/`
2. Builds the MCP server (`npm install && npm run build`)
3. Writes MCP config to 5 files (`.mcp.json`, `.cursor/mcp.json`, `opencode.json`, `codex.json`, `.vscode/mcp.json`)
4. Registers the skill at `.agents/custom-skills/ai-architecture-cookbook/SKILL.md`
5. Sets `architecture_cookbook_enabled: true` in `.aidlc-orchestrator/budgets/default.yaml`

## Requirements

- **Node.js >= 18** for MCP server (optional — Cookbook YAML standards can be read directly without Node.js)
- **Git** for cloning the Cookbook repo

If Node.js is not available, the installer logs a warning and registers the skill for inline YAML fallback only. The MCP server is skipped but the integration continues in degraded mode.

## Stage mapping

| Stage | Cookbook Tool | When |
|-------|--------------|------|
| `workspace-scout` | `recommend_pattern` | When project has auth, enterprise scale |
| `requirements-analyst` | `search_standards` | User mentions architectural domains |
| `code-generator` | `get_decision_tree` → `query_standard` → `get_checklist` | Before code generation in relevant domains |
| `reviewer-code` | `get_checklist(severity: high)` | During five-axis review |
| `reviewer-security` | `get_checklist(severity: critical)` | During OWASP scan |
| `reviewer-performance` | `query_standard(performance-optimization)` | During hot-path analysis |
| `ship-agent` | `query_standard(compliance-data-privacy)` + `query_standard(secure-sdlc)` | Compliance section of release notes |

## MCP tools

The Cookbook MCP server exposes 5 core tools:

| Tool | Description |
|------|-------------|
| `query_standard` | Full YAML content for a specific architectural standard |
| `search_standards` | Search by tags, categories, or free-text query |
| `get_checklist` | Verification checklist, filterable by severity |
| `get_decision_tree` | Decision tree and context inputs for a domain |
| `recommend_pattern` | Structured context → pattern recommendations |

## Graceful degradation

If the MCP server is unreachable, agents fall back to reading YAML standards directly from disk at `./.ai-architecture-cookbook/standards/<category>/<domain>/<domain>.yaml`. This provides equivalent functionality without the MCP server.

## Call budgets

Per stage invocation: ≤ 5 Cookbook calls. Per run: ≤ 25 total calls. Agents skip Cookbook for trivial tasks (single-file changes, typo fixes).

## Disabling

```bash
# Remove the feature flag:
# Set in .aidlc-orchestrator/budgets/default.yaml:
#   architecture_cookbook_enabled: false

# Or via environment variable:
export AIDLC_FEATURE_ARCHITECTURE_COOKBOOK_ENABLED=false
```

## Troubleshooting

| Symptom | Cause | Fix |
|---------|-------|-----|
| "MCP unreachable" in agent output | MCP server not built or not running | Re-run installer with `--with-architecture-cookbook` |
| Empty recommendations | No relevant context inputs | Provide more context in the request |
| Skill not found | Installer didn't complete | Check `.agents/custom-skills/ai-architecture-cookbook/SKILL.md` exists |
| Budget flag not set | Budget file wasn't updated | Set `architecture_cookbook_enabled: true` manually |

## Verification

```bash
# Check Cookbook health:
python aidlc-scripts/factory_validate.py --check-cookbook

# Output:
#   AI Architecture Cookbook: HEALTHY
#     MCP server: .ai-architecture-cookbook/mcp-server/dist/server.js (available)
#     YAML standards: available at .ai-architecture-cookbook/standards
#     Validation schemas: 2 found
#     Node.js: available (MCP server ready)
```

## Standards catalog

43 YAML standards across 5 categories:

| Category | Count | Key domains |
|----------|-------|------------|
| Foundational | 11 | auth, api-design, error-handling, logging, data-persistence |
| Application Architecture | 9 | layered-architecture, service-architecture, DDD, state-management |
| Infrastructure | 7 | containerization, orchestration, ci-cd, IaC, cloud-architecture |
| Security & Quality | 10 | encryption, rate-limiting, testing-strategies, code-quality |
| Integration & Data | 6 | third-party-integration, webhooks, file-storage, search |
