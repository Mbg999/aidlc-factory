# Agency Agents — opt-in

Do you want AI-DLC to integrate specialist agent personas from
[The Agency](https://github.com/msitarzewski/agency-agents) during workflow phases?

When enabled, the AI assistant will consult relevant specialist agent personas
as additional context during each AIDLC phase (e.g., Code Reviewer during review,
Security Engineer during security analysis, Backend Architect during design).

Choose one option:

A) Yes — Activate relevant agency-agents personas during applicable phases
B) No  — Do not use agency-agents personas (standard AIDLC behavior only)

[Answer]:

Notes:
- Agency-agents must be installed first (use `--with-agency-agents` during install).
- Agent persona files are expected in the tool-specific location:
  - GitHub Copilot: `.github/agents/`
  - Claude Code: `.claude/agents/`
  - Cursor: `.cursor/rules/` (as .mdc files)
  - Cline: `.clinerules/agents/`
  - Generic: `.agents/`
- Personas provide specialist expertise and personality-driven guidance.
- They do NOT replace AIDLC subagents (code-reviewer, planner, builder, etc.).
- They ADD domain-specific context the AI assistant can use when generating artifacts.
