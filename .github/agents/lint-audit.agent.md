---
name: lint-audit
description: Runs linter on the codebase and reports all violations. Use for post-codegen quality checks.
tools: ['search/codebase', 'read/terminalLastCommand']
user-invocable: false
model: claude-sonnet-4-6
---

Load your full role and instructions from #file:.github/skills/lint-audit/SKILL.md and execute accordingly.