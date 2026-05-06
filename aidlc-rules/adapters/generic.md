# Generic Agent Adapter for AI-DLC

This adapter covers any AI coding assistant not listed in the other adapters
(Windsurf, Aider, Continue, custom agents, etc.).

## Setup

Point your agent at the core workflow file:

```
aidlc-rules/aws-aidlc-rules/core-workflow.md
```

And the rule details root:

```
aidlc-rules/aws-aidlc-rule-details/
```

Most agents support one of these mechanisms:
- **System prompt / instructions file**: Paste or reference the core-workflow content
- **Context file injection**: Include `aidlc-rules/aws-aidlc-rules/core-workflow.md` as a context file at session start
- **RAG / embedding**: Index `aidlc-rules/` into your agent's retrieval system

## Subagents & Skills

Invoke the pipeline from the terminal (works with any agent that can run shell commands):

```bash
# Run a single agent
python scripts/subagents/manager.py planner '{"run_folder":"runs/current"}'

# Run a full pipeline (sequential + parallel)
python scripts/subagents/pipeline.py construction-full '{"run_folder":"runs/current"}'

# List available pipelines
python scripts/subagents/pipeline.py --list

# List MCP tools available to an agent
python scripts/subagents/mcp_bridge.py --list-tools --agent code-reviewer
```

## Agency-Agents Integration

When installed with `--with-agency-agents`, specialist persona files from
[The Agency](https://github.com/msitarzewski/agency-agents) are placed in
`.agents/`. These are Markdown persona files that the AI assistant reads
as additional context during AIDLC phases.

- Files follow the naming pattern: `<division>-<slug>.md`
  (e.g., `engineering-backend-architect.md`)
- AIDLC automatically consults relevant personas when the agency-agents
  extension is enabled (see `extensions/agency-agents/agency-agents.md`).
- To install:
  ```bash
  python scripts/install_aidlc.py --tool other --with-agency-agents --dest .
  ```
- To install only specific divisions:
  ```bash
  python scripts/install_aidlc.py --tool other --with-agency-agents --agency-divisions engineering,testing --dest .
  ```

## Key Paths

| Purpose | Path |
|---------|------|
| Core workflow | `aidlc-rules/aws-aidlc-rules/core-workflow.md` |
| Rule details | `aidlc-rules/aws-aidlc-rule-details/` |
| Extensions | `aidlc-rules/aws-aidlc-rule-details/extensions/` |
| Agent definitions | `aidlc-rules/aws-aidlc-rule-details/extensions/subagents/agents.yaml` |
| Agency-agents personas | `.agents/` |
| State file | `aidlc-docs/aidlc-state.md` |
| Run outputs | `aidlc-docs/` |
| Audit logs | `runs/<run>/subagents-logs/` |

## Verification

Ask your agent: "What phase are we in according to AI-DLC?" — it should respond
with the current phase from `aidlc-docs/aidlc-state.md`.
