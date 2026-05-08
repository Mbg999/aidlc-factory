# PRIORITY: This workflow OVERRIDES all other built-in workflows
# When user requests software development, ALWAYS follow this workflow FIRST

## Adaptive Workflow Principle
**The workflow adapts to the work, not the other way around.**

The AI model intelligently assesses what stages are needed based on:
1. User's stated intent and clarity
2. Existing codebase state (if any)
3. Complexity and scope of change
4. Risk and impact assessment

## MANDATORY: Rule Details Loading
**CRITICAL**: When performing any phase, you MUST read and use relevant content from rule detail files. Check these paths in order and use the first one that exists, regardless of which AI coding tool is in use:
- `.aidlc/aidlc-rules/aws-aidlc-rule-details/` (canonical location — AI-assisted setup)
- `.aidlc-rule-details/` (flat layout — Cursor, Cline, Claude Code, GitHub Copilot, Windsurf, etc.)
- `aidlc-rules/aws-aidlc-rule-details/` (monorepo layout — rules committed at repo root)

All subsequent rule detail file references (e.g., `common/process-overview.md`, `inception/workspace-detection.md`) are relative to whichever rule details directory was resolved above.

**Common Rules**: ALWAYS load common rules at workflow start:
- Load `common/process-overview.md` for workflow overview and terminology
- Load `common/stage-conventions.md` for shared stage patterns (skills, questions, plans, approval)
- Load `common/session-continuity.md` for session resumption guidance
- Load `common/ascii-diagram-standards.md` for content validation and diagram rules
- Load `common/question-format-guide.md` for question formatting rules
- Reference these throughout the workflow execution

## MANDATORY: Extensions Loading (Context-Optimized)
**CRITICAL**: At workflow start, scan the `extensions/` directory recursively but load ONLY lightweight opt-in files — NOT full rule files. Full rule files are loaded on-demand after the user opts in.

**Loading process**:
1. List all subdirectories under `extensions/` (e.g., `extensions/security/`, `extensions/compliance/`)
2. In each subdirectory, load ONLY `*.opt-in.md` files — these contain the extension's opt-in prompt. The corresponding rules file is derived by convention: strip the `.opt-in.md` suffix and append `.md` (e.g., `security-baseline.opt-in.md` → `security-baseline.md`)
3. Do NOT load full rule files (e.g., `security-baseline.md`) at this stage

**Deferred Rule Loading**:
- During Requirements Analysis, opt-in prompts from the loaded `*.opt-in.md` files are presented to the user
- When the user opts IN for an extension, load the corresponding rules file (derived by naming convention) at that point
- When the user opts OUT, the full rules file is never loaded — saving context
- Extensions without a matching `*.opt-in.md` file are always enforced — load their rule files immediately at workflow start

**Enforcement** (applies only to loaded/enabled extensions):
- Extension rules are hard constraints, not optional guidance
- At each stage, the model intelligently evaluates which extension rules are applicable based on the stage's purpose, the artifacts being produced, and the context of the work — enforce only those rules that are relevant
- Rules that are not applicable to the current stage should be marked as N/A in the compliance summary (this is not a blocking finding)
- Non-compliance with any applicable enabled extension rule is a **blocking finding** — do NOT present stage completion until resolved
- When presenting stage completion, include a summary of extension rule compliance (compliant/non-compliant/N/A per rule, with brief rationale for N/A determinations)

**Conditional Enforcement**: Extensions may be conditionally enabled/disabled. See `inception/requirements-analysis.md` for the opt-in mechanism.

Runner resolution order for whether an extension is enabled (preference order):

1. Manifest-level default: If the agent manifest (`agents.yaml` or `agents.json`) for an extension contains `enabled_by_default: true`, treat that extension as enabled and load the full rule file automatically.
2. Repository run state: If the run contains `aidlc-docs/aidlc-state.md` with an explicit entry for the extension, follow that value (`enabled: true|false`).
3. Opt-in prompt: If neither manifest nor run state indicates a decision and an opt-in prompt file (`*.opt-in.md`) exists, present it and honor the user's answer. If no opt-in prompt exists, default to enforced (load the full rule file).

Always record the decision (enabled/disabled/auto-enabled) in `aidlc-docs/audit.md` and log any skips. 
## AutoSkills Integration

**RECOMMENDED**: When a run workspace contains AutoSkills artifacts, the
evaluation runner will detect them and include details in the subagent
`context` under the `autoskills` key so subagents can consult the data and
adapt behavior.

What is detected (check these locations under the run `workspace`):
- `skills-lock.json` — canonical lock file produced by AutoSkills
- `.agents/skills/<skill-directory>/` — per-skill directories containing installed/generated skill files (e.g., `.agents/skills/<skill_name>/`)

What is added to subagent context:

- `context['autoskills']` — mapping with:
   - `skills_lock_path`: path to `skills-lock.json` or `null`
   - `skills_lock`: parsed JSON content of the lock file or `null`
   - `autoskills_dir`: path to `.agents/skills/` (contains per-skill subdirectories) or `null`

Behavior and safety:

- Subagents MAY consult `context['autoskills']` and optionally alter
   recommendations or behavior based on installed skills.
- By default the workflow does NOT automatically install or enable skills.
   Installation is an explicit step and must be approved by the user or CI
   policy.
- To attempt installation manually run the recommended command written in
   `aidlc-docs/autoskills-recommendations.md` (or use the helper below):

```bash
python3 scripts/subagents/manager.py midudev-autoskills '{"path":"<workspace>","install":true}'
```

- The evaluation runner exposes a helper `auto_install_autoskills(run_folder)`
   (in `scripts/aidlc-evaluator/scripts/run_evaluation.py`) which programmatically
   invokes the `midudev-autoskills` subagent with `install=true` and writes an
   installation report to `aidlc-docs/autoskills-installation.md`.

- The evaluation runner can optionally perform automatic installation of
   recommended AutoSkills during evaluation. Control this behavior with the CLI
   flags:
   - `--auto-install-autoskills` (enabled by default)
   - `--no-auto-install-autoskills` (disable automatic installation)
   Use this option in CI only after auditing the recommended skills.

- The evaluation runner can also optionally *apply* installed skills by
   executing a well-known apply script inside each skill directory under
   `.agents/skills/<skill>/`. Supported entrypoints (checked in order) are:
   `apply.py`, `install.py`, `entrypoint.py`, `run.py`, `main.py`, `apply.sh`,
   `install.sh`. Control this behavior with the CLI flag `--apply-autoskills`.

   When `--apply-autoskills` is enabled the runner will attempt to execute
   these scripts (one per skill) and record per-skill results under the run
   folder (e.g. `autoskills-apply-results.yaml`). This is an opt-in action and
   must only be used after auditing the installed skill files.

Security note: Always validate any files created by AutoSkills per
`common/ascii-diagram-standards.md` and record validation results in
`aidlc-docs/audit.md` before relying on installed skill code.

## Custom Skills Integration

In addition to AutoSkills (which are discovered and installed per-project),
the workflow supports **custom skills** — pre-installed skill packages that
live in the user's home directory or the repository.

### What are custom skills?

Custom skills are SKILL.md files installed under well-known directories:
## Tool Adapters (Optional)
# PRIORITY: This workflow OVERRIDES all other built-in workflows
# When user requests software development, ALWAYS follow this workflow FIRST

## Adaptive Workflow Principle
**The workflow adapts to the work, not the other way around.**

Decide stages by:
1. User intent clarity
2. Existing codebase
3. Complexity & scope
4. Risk & impact

## MANDATORY: Rule Details Loading
**CRITICAL**: Always read rule-detail files. Check these paths (use first existing):
- `.aidlc/aidlc-rules/aws-aidlc-rule-details/`
- `.aidlc-rule-details/`
- `aidlc-rules/aws-aidlc-rule-details/`

Subsequent rule refs (e.g., `common/process-overview.md`) are relative to chosen rules dir.

**Common Rules** to load at start:
- `common/process-overview.md`
- `common/stage-conventions.md`
- `common/session-continuity.md`
- `common/ascii-diagram-standards.md`
- `common/question-format-guide.md`

## MANDATORY: Extensions Loading (Context-Optimized)
**CRITICAL**: Scan `extensions/` but load only `*.opt-in.md` files (defer full rule files until user opts in).

Loading process (short):
1. List `extensions/*` dirs
2. In each, load `*.opt-in.md` only; derive full rule file by replacing `.opt-in.md` → `.md`
3. Do not load full rules yet

Deferred loading:
- Present opt-in prompts during Requirements Analysis
- If user opts IN, load corresponding rule file
- If opts OUT, never load full rule file
- Extensions without an opt-in file are enforced immediately

Enforcement rules:
- Loaded/enabled extension rules are hard constraints
- Mark irrelevant rules as N/A in compliance summary
- Non-compliance = blocking finding; include compliance summary when completing stages

Runner order to decide if extension enabled:
1. Manifest-level default (`enabled_by_default: true`)
2. `aidlc-docs/aidlc-state.md` run state
3. Opt-in prompt answer (if present); otherwise enforced

Record decisions in `aidlc-docs/audit.md`.

## AutoSkills Integration
If workspace has AutoSkills artifacts, runner adds `context['autoskills']` with:
- `skills_lock_path`, `skills_lock`, `autoskills_dir`

Detected files:
- `skills-lock.json`
- `.agents/skills/<skill>/`

Behavior summary:
- Subagents may consult `context['autoskills']`
- Installation/apply of autoskills requires explicit approval
- Runner helper and flags: `--auto-install-autoskills`, `--no-auto-install-autoskills`, `--apply-autoskills`

Run helper example:
```bash
python3 scripts/subagents/manager.py midudev-autoskills '{"path":"<workspace>","install":true}'
```

Validate any autoskill-generated files per `common/ascii-diagram-standards.md` before use.

## Custom Skills Integration
Custom skills live at:
- `~/.agents/skills/<skill>/SKILL.md` (user-global)
- `<repo>/.agents/skills/<skill>/SKILL.md` (repo-local)

Usage modes:
1. Skill injection via `agents.yaml` (`context['skills'][name]`)
2. Direct read-by-assistant (phase rule files list required skills)

Both AutoSkills and Custom Skills can be used together.

Discover custom skills:
```bash
python3 scripts/subagents/mcp_bridge.py --list-skills
```

## Tool Adapters (Optional)
Adapter docs in `aidlc-rules/adapters/` (informational only):
- copilot.md, cursor.md, claude-code.md, cline.md, generic.md

## Agency-Agents Integration (Optional)
When enabled, assistant can consult persona files (agency agents) for phase-specific expertise.

## MANDATORY: Subagent Execution
**CRITICAL**: If `scripts/subagents/` exists, execute subagent scripts (do not simulate). Use terminal commands.

Single agent example:
```bash
python scripts/subagents/manager.py <agent-id> '{"run_folder": "<workspace-or-run-path>"}'
```

Full pipeline example:
```bash
python scripts/subagents/pipeline.py construction-full '{"run_folder": "<workspace-or-run-path>"}'
```

Agent outputs to watch: planner → `aidlc-docs/construction-plan.md`; builder → `aidlc-docs/build-report.md`; code-reviewer → `aidlc-docs/reporting/`; construction-reviewer → `aidlc-docs/construction-review.md`; memory → `.aidlc-memory/` and `aidlc-docs/`.

Fallback: If manager/pipeline scripts missing, AI may generate artifacts manually but must inform user and log reason.

## MANDATORY: Content Validation
Before creating files validate:
- Mermaid syntax, ASCII diagrams, escape special chars, provide text alternatives, test parsing compatibility

## MANDATORY: Question File Format
Follow `common/question-format-guide.md` for question formatting (MCQ, `[Answer]:` tags, ambiguity rules).

## MANDATORY: Welcome Message
Generate a brief welcome message from `common/process-overview.md` once at workflow start (show phases, adaptive principle, team role).

# Adaptive Software Development Workflow

---

# INCEPTION PHASE

Purpose: Planning, requirements, architecture

Focus: WHAT to build and WHY

Stages (inception): Workspace Detection, Reverse Engineering (brownfield), Requirements Analysis, User Stories (optional), Workflow Planning, Application Design (optional), Units Generation (optional)

## Workspace Detection (ALWAYS EXECUTE)
1. Log raw user request in `aidlc-docs/audit.md`
2. Load `inception/workspace-detection.md`
3. Detect workspace: check `aidlc-state.md`, scan code, decide brownfield vs greenfield, check reverse-engineering artifacts
4. Choose next phase: Reverse Engineering (brownfield/no artifacts) or Requirements Analysis
5. Log findings in audit
6. Present completion message
7. Proceed automatically

## Reverse Engineering (CONDITIONAL - Brownfield Only)
Execute if codebase present and no prior reverse-engineering artifacts.

Steps (short):
- Log start in audit
- Load `inception/reverse-engineering.md`
- Produce: business overview, architecture docs, code structure, API docs, component inventory, interaction diagrams, tech stack, dependencies
- If AutoSkills enabled: run `midudev-autoskills` and read `aidlc-docs/autoskills-recommendations.md`
- Always run `memory` subagent to persist facts
- Present detailed completion message and wait for user approval
- Log user response in audit

## Requirements Analysis (ALWAYS EXECUTE - Adaptive Depth)
Depth: minimal / standard / comprehensive depending on request clarity/risk.

Steps:
- Log inputs in audit
- Load `inception/requirements-analysis.md`
- Use reverse-engineering artifacts if brownfield
- Analyze intent, determine depth, gather functional & non-functional requirements, ask clarifying Qs
- Generate requirements doc, wait for approval, log response

## User Stories (CONDITIONAL)
Use when features touch users, workflows, multiple personas, or complexity warrants stories. Plan (questions) → generate (stories/personas) after approval. Log all inputs.

## Workflow Planning (ALWAYS EXECUTE)
- Load `inception/workflow-planning.md` and `common/ascii-diagram-standards.md`
- Use prior context (reverse-engineering, requirements, stories)
- Decide phases & depth, plan multi-package changes if needed, generate Mermaid visualization (validate syntax)
- If greenfield + AutoSkills: run `midudev-autoskills` (write results)
- Validate content, present plan, wait for approval, log response

## Application Design, Units Generation (CONDITIONAL)
Run only if new components, services, or decomposition required. Log inputs, load respective rule files, present completion messages, wait for approval, log responses.

---

# 🟢 CONSTRUCTION PHASE

Purpose: HOW to build (design, NFRs, code)

Per-unit loop: Functional Design, NFR Requirements, NFR Design, Infrastructure Design, Code Generation (always). Complete each unit fully before next.

Code Generation (per unit): plan → generate → run `planner` subagent (writes `aidlc-docs/construction-plan.md`) → generate code → run `code-reviewer` → present findings → wait for approval.

Build & Test: run full pipeline `python scripts/subagents/pipeline.py construction-full '{"run_folder": "."}'` (or run agents individually), produce build/test instructions and files under `aidlc-docs/build-and-test/`, wait for approval.

---

# 🟡 OPERATIONS PHASE

Placeholder for deployment, monitoring, incident response, production readiness. Currently handled post-build in Construction.

Key principles (short):
- Adaptive execution
- Transparent planning
- User control
- Progress tracking in `aidlc-state.md`
- Full audit trail in `aidlc-docs/audit.md` (log raw user input exactly)
- Validate content before writing
- No emergent UI patterns; use standardized 2-option completion messages in construction stages

Plan-level rules (short):
1. Always update plan checkboxes when work done
2. Mark steps [x] in same interaction as completion
3. Track at plan-level and stage-level

Prompts logging (short):
- Log every user input with ISO8601 timestamp in `aidlc-docs/audit.md` (append, do not overwrite)
- Use specified audit format

Directory structure (short):
```
<WORKSPACE-ROOT>/
├── aidlc-docs/
│   ├── inception/
│   ├── construction/
│   ├── operations/
│   ├── aidlc-state.md
│   └── audit.md
```

CRITICAL: Application code stays in workspace root; docs only in `aidlc-docs/`.
- Existing codebase detected
