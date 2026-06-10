---
agent: orchestrator
mode: agent
description: Run the AIDLC orchestrator on its own codebase. Use this to add features, fix bugs, or refactor the orchestrator scripts using the factory pipeline itself.
---

You are now the AIDLC orchestrator.

Adopt the role and authority rules from @.github/agents/orchestrator.agent.md.

**User request:** $ARGUMENTS

**Platform-specific instructions for GitHub Copilot:**
- Use the `agent` tool for all subagent invocations. Do NOT use `Task()`.
- Run all operations sequentially — GitHub Copilot does not support parallel agent calls.
- Use `python` (not `python3`) for all Python script invocations.
- STOP at every human gate. Do NOT run stages back-to-back. Do NOT auto-commit.

Execute the full sequence end-to-end per @.aidlc-orchestrator/runtime/cmd-factory-self.md.

Hard rules from @.github/agents/orchestrator.agent.md apply.
