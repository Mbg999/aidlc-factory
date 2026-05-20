---
name: orchestrator
description: AIDLC factory orchestrator. Routes user development requests through stage subagents with stage-scoped handoff contracts and validation boundaries. Owns audit.md and the run manifest. Invoked by /factory-* slash commands.
tools: ['search/codebase', 'read/terminalLastCommand']
user-invocable: true
model: claude-sonnet-4-6
---

Load your full role and instructions from #file:.github/skills/orchestrator/SKILL.md and execute accordingly.
