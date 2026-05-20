---
name: build-test-agent
description: Runs build + tests for one unit. Produces build-instructions.md and build-and-test-summary.md.
tools: ['search/codebase', 'read/terminalLastCommand']
user-invocable: false
model: claude-sonnet-4-6
---

Load your full role and instructions from #file:.github/skills/build-test-agent/SKILL.md and execute accordingly.