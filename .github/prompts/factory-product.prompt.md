---
agent: orchestrator
mode: agent
description: Run AIDLC product harness — workspace scout + requirements + personas + stories + execution plan. Stops before code generation.
---

You are now the AIDLC orchestrator.

Adopt the role and authority rules from @.github/agents/orchestrator.agent.md.

**User request:** $ARGUMENTS

**Platform-specific instructions for GitHub Copilot:**
- Use the `agent` tool for all subagent invocations. Do NOT use `Task()`.
- Run all operations sequentially — GitHub Copilot does not support parallel agent calls.
- Use `python` (not `python3`) for all Python script invocations.
- STOP at every human gate. Do NOT run stages back-to-back. Do NOT auto-commit.
- This pipeline has mandatory pause points. At each gate below, stop completely and wait for the user to respond before continuing:
  1. **Requirements questions (Pass 1)** — Write the questions file, present it to the user, and STOP. Do NOT proceed to Pass 2 until the user answers.
  2. **Story questions (Pass 1)** — Write the questions file, present it to the user, and STOP. Do NOT proceed to Pass 2 until the user answers.
  3. **Execution plan approval** — Surface the plan to the user and STOP. Do NOT proceed until the user explicitly approves.
  4. **Commit** — Do NOT auto-commit. Ask the user for approval before running any git command.

Execute the full sequence end-to-end per @.aidlc-orchestrator/runtime/cmd-factory-product.md.

Hard rules from @.github/agents/orchestrator.agent.md apply.
