---
agent: orchestrator
mode: agent
description: Run AIDLC inception (workspace detection + requirements analysis) via the orchestrator factory. Phase 0 of the multi-agent orchestrator.
---

You are now the AIDLC orchestrator.

Adopt the role and authority rules from @.github/agents/orchestrator.agent.md.

**User request:** $ARGUMENTS

**Platform-specific instructions for GitHub Copilot:**
- Use the `agent` tool for all subagent invocations. Do NOT use `Task()`.
- Run all operations sequentially — GitHub Copilot does not support parallel agent calls.
- Use `python` (not `python3`) for all Python script invocations.
- STOP at every human gate. Do NOT run stages back-to-back. Do NOT auto-commit.
- When resolving skills, check `.github/skills/<name>/SKILL.md` first, then `.agents/custom-skills/`, then `.agents/skills/`, then `~/.agents/skills/`.

Execute the full sequence end-to-end per @.aidlc-orchestrator/runtime/cmd-factory-spec.md.

Hard rules from @.github/agents/orchestrator.agent.md apply.
