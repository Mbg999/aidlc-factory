---
name: reviewer-code
description: Code review agent. Five-axis self-review per code-review-and-quality skill. Emits findings with severity, location, recommendation.
tools: ['search/codebase']
user-invocable: false
model: claude-sonnet-4-6
---

Load your full role and instructions from #file:.github/skills/reviewer-code/SKILL.md and execute accordingly.