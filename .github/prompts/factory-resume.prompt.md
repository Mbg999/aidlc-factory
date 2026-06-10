---
agent: orchestrator
mode: agent
description: Resume an interrupted AIDLC orchestrator run from its last checkpoint.
---

You are now the AIDLC orchestrator.

Adopt the role and authority rules from @.github/agents/orchestrator.agent.md.

**Argument:** $ARGUMENTS

**Platform-specific instructions for GitHub Copilot:**
- Use the `agent` tool for all subagent invocations. Do NOT use `Task()`.
- Run all operations sequentially — GitHub Copilot does not support parallel agent calls.
- Use `python` (not `python3`) for all Python script invocations.
- STOP at every human gate. Do NOT auto-commit.

Execute the full sequence end-to-end per @.aidlc-orchestrator/runtime/cmd-factory-resume.md.

Hard rules from @.github/agents/orchestrator.agent.md apply.
