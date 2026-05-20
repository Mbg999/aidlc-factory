---
name: ship-agent
description: Final stage. Produces release notes, ADRs, CI/CD wiring, CHANGELOG updates, and migration plans.
tools: ['search/codebase', 'edit']
user-invocable: false
model: claude-sonnet-4-6
---

Load your full role and instructions from #file:.github/skills/ship-agent/SKILL.md and execute accordingly.