# Cookbook Demo: First Integration Run

This walkthrough demonstrates the AI Architecture Cookbook integration end-to-end.

## Prerequisites

- AIDLC Factory installed with `--with-architecture-cookbook`
- Node.js >= 18 (for MCP server)
- A target project directory (greenfield or brownfield)

## Step 1: Install with Cookbook

```bash
cd my-project
python ../aidlc-factory/aidlc-scripts/install_aidlc.py \
  --tool opencode \
  --yes \
  --with-architecture-cookbook \
  --dest .
```

Expected output:
```
--- Installing AI Architecture Cookbook ---
  Node.js: v22.16.0 -- OK
  Copying Cookbook from ...
  Building Cookbook MCP server (npm install)...
  Building Cookbook MCP server (npm run build)...
  Cookbook MCP server built successfully.
  Cookbook MCP -> .mcp.json
  Cookbook MCP -> .cursor/mcp.json
  Cookbook MCP -> opencode.json
  Cookbook MCP -> codex.json
  Cookbook MCP -> .vscode/mcp.json
  Cookbook skill -> .agents/custom-skills/ai-architecture-cookbook/SKILL.md
  Budget flag: architecture_cookbook_enabled: true
  Cookbook installation complete.
```

## Step 2: Verify installation

```bash
python aidlc-scripts/factory_validate.py --check-cookbook
```

Expected output:
```
AI Architecture Cookbook: HEALTHY
  MCP server: .ai-architecture-cookbook/mcp-server/dist/server.js (available)
  YAML standards: available at .ai-architecture-cookbook/standards
  Validation schemas: 2 found
  Node.js: available (MCP server ready)
```

## Step 3: Run a factory spec

Execute a spec that triggers Cookbook calls:
```
/factory-spec "build a REST API with authentication and rate limiting"
```

During the requirements analysis phase, the agent should:
1. Load the `ai-architecture-cookbook` skill
2. Call `search_standards` for "authentication", "api-design", "rate-limiting"
3. Include Cookbook standard IDs in the requirements output

Verify by inspecting the audit entries in `aidlc-docs/audit.md` for `[Skill] ai-architecture-cookbook:` entries.

## Step 4: Run a factory build

```
/factory-build <run-id>
```

During code generation, the agent should:
1. Call `get_decision_tree` for relevant domains
2. Call `query_standard` for implementation details
3. Call `get_checklist` to self-verify
4. Include recommended patterns in the code-generation plan

## Step 5: Run a factory review

```
/factory-review <run-id>
```

During review, the reviewer agents should:
1. `reviewer-code` calls `get_checklist(severity: high)`
2. `reviewer-security` calls `get_checklist(severity: critical)`
3. `reviewer-performance` calls `query_standard(performance-optimization)`

Check the review reports for Cookbook standard ID citations.

## Step 6: Degradation test

1. Move the MCP server binary: `mv .ai-architecture-cookbook/mcp-server/dist/server.js /tmp/`
2. Re-run any factory command
3. Verify agents fall back to inline YAML without crashing
4. Check audit entries for `[Skill] ai-architecture-cookbook: YAML-fallback used — MCP unreachable`
5. Restore the server: `mv /tmp/server.js .ai-architecture-cookbook/mcp-server/dist/`

## Expected outcomes

After completing this walkthrough:
- All 7 AIDLC stages can reference Cookbook standards
- MCP server provides fast, structured access to 43 standards
- Graceful degradation works when MCP is unavailable
- Call budget is respected (≤ 5 per stage, ≤ 25 per run)
- Audit trail contains Cookbook citations
