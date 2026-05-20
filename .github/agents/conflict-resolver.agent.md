---
name: conflict-resolver
description: Owns the file-glob lock registry and Python AST symbol-drift detection. Detects conflicts when parallel agents touch overlapping paths.
tools: ['search/codebase', 'read/terminalLastCommand']
user-invocable: false
model: claude-sonnet-4-6
---

Load your full role and instructions from #file:.github/skills/conflict-resolver/SKILL.md and execute accordingly.