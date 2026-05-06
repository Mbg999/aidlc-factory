# Agency Agents Integration

Purpose: Integrate specialist AI agent personas from
[The Agency](https://github.com/msitarzewski/agency-agents) into the AIDLC workflow,
providing domain-specific expertise at each phase.

## Overview

Agency-agents are specialist persona files (Markdown with YAML frontmatter) that define
deep domain expertise, personality, workflows, and deliverables. When this extension is
enabled, the AI assistant MUST consult relevant agency-agent personas during applicable
AIDLC phases to enrich its outputs with specialist knowledge.

## Agent Discovery

The AI assistant discovers installed agency-agents by scanning the tool-specific directory:

| Tool            | Agent directory                     |
|-----------------|-------------------------------------|
| GitHub Copilot  | `.github/agents/`                   |
| Claude Code     | `.claude/agents/`                   |
| Cursor          | `.cursor/rules/` (`.mdc` files)     |
| Cline           | `.clinerules/agents/`               |
| Generic         | `.agents/`                          |

Each agent file has a filename pattern: `<division>-<slug>.md` (e.g.,
`engineering-code-reviewer.md`, `testing-performance-benchmarker.md`).

At the start of the workflow (or when this extension is first loaded), the assistant
SHOULD list the available agency-agent files to know what specialists are available.

## Phase-to-Agent Mapping

The AI assistant MUST consult the following agency-agent personas (if installed)
during the corresponding AIDLC phases:

### INCEPTION PHASE

| Stage                    | Relevant Agency-Agents                                           |
|--------------------------|------------------------------------------------------------------|
| Reverse Engineering      | `engineering-codebase-onboarding-engineer`, `engineering-software-architect` |
| Requirements Analysis    | `product-product-manager`, `design-ux-researcher`                |
| User Stories             | `product-product-manager`, `design-ux-researcher`                |
| Workflow Planning        | `project-management-senior-project-manager`, `engineering-devops-automator` |
| Application Design      | `engineering-backend-architect`, `engineering-software-architect`, `engineering-frontend-developer` |
| Units Generation         | `project-management-senior-project-manager`                      |

### CONSTRUCTION PHASE

| Stage                    | Relevant Agency-Agents                                           |
|--------------------------|------------------------------------------------------------------|
| Functional Design        | `engineering-backend-architect`, `engineering-software-architect` |
| NFR Requirements         | `engineering-backend-architect`, `testing-performance-benchmarker` |
| NFR Design               | `engineering-backend-architect`, `engineering-security-engineer`  |
| Infrastructure Design    | `engineering-devops-automator`, `engineering-backend-architect`   |
| Code Generation          | `engineering-frontend-developer`, `engineering-backend-architect`, `engineering-mobile-app-builder`, `engineering-ai-engineer` |
| Build and Test           | `engineering-devops-automator`, `testing-performance-benchmarker`, `engineering-code-reviewer` |

### Cross-cutting (any phase)

| Concern                  | Relevant Agency-Agents                                           |
|--------------------------|------------------------------------------------------------------|
| Security                 | `engineering-security-engineer`                                  |
| Accessibility            | `testing-accessibility-auditor`                                  |
| Code review              | `engineering-code-reviewer`                                      |
| Database design          | `engineering-database-optimizer`                                 |
| Git workflow             | `engineering-git-workflow-master`                                 |
| Documentation            | `engineering-technical-writer`                                   |

## How to Consult an Agency-Agent

When the AI assistant enters a phase where agency-agents are mapped:

1. **Check if the file exists** in the tool-specific agent directory.
2. **Read the agent file** to load its persona, workflows, and deliverables.
3. **Apply the specialist's perspective** when generating artifacts for that phase:
   - Use their domain expertise to inform decisions.
   - Apply their success metrics as quality criteria.
   - Follow their workflow patterns when relevant.
   - Adopt their communication style for relevant outputs (optional).
4. **Do NOT replace AIDLC rules** — agency-agent guidance supplements AIDLC rules.
   If there's a conflict, AIDLC rules always win.
5. **Log consultation** in `aidlc-docs/audit.md`:
   ```
   [Agency-Agent] Consulted: engineering-backend-architect (Application Design stage)
   ```

## Fallback Behavior

- If a mapped agency-agent file is not installed, skip it silently — do not error.
- If NO agency-agent files are found at all, log a warning and proceed with standard
  AIDLC behavior.
- The AI assistant may also consult agency-agents NOT in the mapping table if the user
  explicitly requests a specialist (e.g., "use the Security Engineer agent for this").

## Integration with AIDLC Subagents

Agency-agents (persona files) are COMPLEMENTARY to AIDLC subagents (Python scripts):

| Aspect           | AIDLC Subagents                       | Agency-Agents                          |
|------------------|---------------------------------------|----------------------------------------|
| Type             | Python scripts (`scripts/subagents/`) | Markdown persona files (`.md`)         |
| Execution        | Via `manager.py` in terminal          | Read by AI assistant as context        |
| Output           | Structured artifacts in `aidlc-docs/` | Influences AI assistant behavior       |
| Mandatory        | Yes (when enforce_in_phases matches)  | Yes (when extension enabled + mapped)  |
| Replaces other   | No                                    | No                                     |

**Order of operations in a phase:**
1. Load and consult relevant agency-agent personas (for context/guidance).
2. Execute AIDLC subagents via terminal (for structured artifacts).
3. Apply both inputs when generating phase outputs.

## Custom Agent Selection

The user may override the default phase-to-agent mapping by specifying custom mappings
in `aidlc-docs/agency-agents-config.md`:

```markdown
## Custom Agency-Agent Mapping

### Code Generation
- engineering-frontend-developer
- engineering-rapid-prototyper

### Requirements Analysis
- product-product-manager
- design-ux-researcher
- specialized-workflow-architect
```

If this file exists, its mappings OVERRIDE the defaults in this rule for the specified
stages. Stages not mentioned in the custom file still use the defaults.

## Enforcement

- When enabled, consulting mapped agency-agents is MANDATORY at each applicable phase.
- Failure to consult available agents is a non-blocking finding (logged in audit.md).
- Conflicting guidance between agency-agents is resolved by the AI assistant using
  judgment — log the resolution rationale in audit.md.
- Agency-agent guidance NEVER overrides AIDLC core rules, security baseline,
  property-based testing rules, or other enabled extension rules.
