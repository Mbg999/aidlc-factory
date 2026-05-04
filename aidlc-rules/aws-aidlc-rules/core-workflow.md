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
- Load `common/process-overview.md` for workflow overview
- Load `common/session-continuity.md` for session resumption guidance
- Load `common/content-validation.md` for content validation requirements
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
`common/content-validation.md` and record validation results in
`aidlc-docs/audit.md` before relying on installed skill code.

## Custom Skills Integration

In addition to AutoSkills (which are discovered and installed per-project),
the workflow supports **custom skills** — pre-installed skill packages that
live in the user's home directory or the repository.

### What are custom skills?

Custom skills are SKILL.md files installed under well-known directories:
- `~/.agents/skills/<skill-name>/SKILL.md` — user-global skills (persist across workspaces)
- `<repo>/.agents/skills/<skill-name>/SKILL.md` — repo-local skills (shared with the team)

Each SKILL.md file contains domain-specific instructions, best practices, or
specialized behavior that an agent (or the AI assistant itself) can use during
any phase of the workflow.

### How custom skills are used

There are two complementary mechanisms:

**1. Skill injection into subagents (via `agents.yaml`).**
Each agent definition in `agents.yaml` has a `skills` list.  Skills named
there are loaded at execution time: the manager reads the SKILL.md content
and injects it into `context['skills'][<name>]`.  The subagent script then
has full access to the skill instructions as in-context guidance.

An agent may also set `skills: ["*"]` to request ALL installed skills be
discovered and injected (auto-discovery mode).

**2. Direct use by the AI coding assistant.**
The AI assistant running this workflow (Copilot, Cursor, Claude Code, etc.)
has its own installed skills visible in its system prompt.  During any AIDLC
phase, the assistant SHOULD proactively consult relevant skills:

| Phase / task              | Relevant skills (examples)                    |
|---------------------------|-----------------------------------------------|
| Code review               | `caveman-review`, security-related skills     |
| Commit messages           | `caveman-commit`                              |
| Infrastructure design     | `azure-observability`, cloud-specific skills  |
| Discovering new skills    | `find-skills`                                 |
| PR creation               | `create-pull-request`                         |
| Addressing PR feedback    | `address-pr-comments`                         |

The assistant does NOT need to wait for a subagent to use a skill.  If a
skill matches the current task, read it and apply its guidance directly.

### Relationship between AutoSkills and Custom Skills

| Aspect        | AutoSkills                           | Custom Skills                         |
|---------------|--------------------------------------|---------------------------------------|
| Source        | Discovered per-project               | Pre-installed by user or team         |
| Location      | `.agents/skills/` (workspace)        | `~/.agents/skills/` or repo-local    |
| Lock file     | `skills-lock.json`                   | None (filesystem presence is enough) |
| Installation  | Requires explicit approval           | Already installed                     |
| Injection     | `context['autoskills']`              | `context['skills']`                   |
| AI assistant  | Informational (reads lock file)      | Directly actionable (reads SKILL.md) |

Both can coexist.  When an agent has both autoskills artifacts AND custom
skills injected, it should use both — custom skills for domain guidance,
autoskills for project-specific context.

### Discovering installed skills

To list all custom skills currently available:

```bash
python3 scripts/subagents/mcp_bridge.py --list-skills
```

This scans `~/.agents/skills/` and `<repo>/.agents/skills/` and prints the
name and first line of each SKILL.md found.

## Tool Adapters (Optional)
AIDLC is tool-agnostic. Its rules are pure Markdown and work with any AI coding
assistant that can read files. Optional adapter files provide tool-specific
setup guidance (e.g., where to symlink rules, which config file to create).

Adapter files live in `aidlc-rules/adapters/`. Available adapters:
- `copilot.md` — GitHub Copilot (`.github/copilot-instructions.md`)
- `cursor.md` — Cursor (`.cursor/rules/`)
- `claude-code.md` — Claude Code (`.claude/CLAUDE.md`)
- `cline.md` — Cline (`.clinerules/`)
- `generic.md` — Any other agent (copy rules to agent context manually)

Adapters are informational only — no adapter changes AIDLC rule content.

## MANDATORY: Subagent Execution During Construction
**CRITICAL**: The AI coding assistant MUST always **execute** the subagent scripts during the Construction phase — not simulate their behavior or generate their output artifacts manually. Subagents are **always enabled** (no opt-in required). If `scripts/subagents/` exists in the workspace, subagent execution is mandatory.

### How to Execute Subagents

Subagents are executed via terminal commands. The AI assistant MUST run these commands in the user's terminal (shell tool / run_in_terminal / bash / etc.) — never just describe what they would do.

**Single agent execution:**
```bash
python scripts/subagents/manager.py <agent-id> '{"run_folder": "<workspace-or-run-path>"}'
```

**Full pipeline execution (recommended for construction phase):**
```bash
python scripts/subagents/pipeline.py construction-full '{"run_folder": "<workspace-or-run-path>"}'
```

### When to Execute

The execution points are defined by each agent's `enforce_in_phases` field in `agents.yaml`:

| Agent | Phase(s) | Artifacts Produced |
|-------|----------|-------------------|
| `planner` | construction | `aidlc-docs/construction-plan.md` |
| `builder` | construction, build-and-test | `aidlc-docs/build-report.md` |
| `code-reviewer` | construction, build-and-test | `aidlc-docs/reporting/` |
| `construction-reviewer` | construction, build-and-test | `aidlc-docs/construction-review.md` |

**Construction Phase — recommended execution flow:**

1. **Before Code Generation starts** → Run the `planner` agent (or the `construction-full` pipeline which runs planner first). The planner reads the workspace, detects manifest files, and writes `construction-plan.md` with concrete install/test/lint/build steps.

2. **After Code Generation completes (per unit or after all units)** → Run `builder` + `code-reviewer` (they run in parallel in the `construction-full` pipeline). Builder produces `build-report.md` with suggested commands. Code reviewer produces lint/security findings.

3. **Before Build and Test completion** → Run `construction-reviewer`. It scans for TODOs, secrets, style issues and writes `construction-review.md`.

**Alternatively**, run the entire pipeline at once after Code Generation:
```bash
python scripts/subagents/pipeline.py construction-full '{"run_folder": "."}'
```

### Execution Rules

- **MUST execute via terminal**: Use the shell/terminal tool available in your coding assistant. Do NOT try to import or call Python functions directly — use `python scripts/subagents/manager.py` or `python scripts/subagents/pipeline.py` as subprocess commands.
- **MUST pass run_folder**: Always include `run_folder` in the JSON context so audit logs and output artifacts land in the correct location.
- **MUST read and present results**: After execution, read the output artifacts (e.g., `aidlc-docs/construction-plan.md`) and present key findings to the user.
- **MUST respect errors**: If an agent returns an error, report it to the user and do NOT proceed as if the stage completed successfully.
- **MUST NOT simulate**: Do not generate `construction-plan.md`, `build-report.md`, or `construction-review.md` manually when the corresponding agent is enabled. The real agent script produces these files.
- **MCP calls**: If agent output contains `mcp_calls`, present each tool call to the user for approval before proceeding.

### Fallback When Scripts Are Unavailable

If `scripts/subagents/manager.py` or `scripts/subagents/pipeline.py` does not exist in the workspace (e.g., the user only copied rules but not scripts), fall back to generating the artifacts manually as the AI assistant — but inform the user that subagent execution was skipped because the scripts are not present. This is the **only** valid reason to skip subagent execution.

## MANDATORY: Content Validation
**CRITICAL**: Before creating ANY file, you MUST validate content according to `common/content-validation.md` rules:
- Validate Mermaid diagram syntax
- Validate ASCII art diagrams (see `common/ascii-diagram-standards.md`)
- Escape special characters properly
- Provide text alternatives for complex visual content
- Test content parsing compatibility

## MANDATORY: Question File Format
**CRITICAL**: When asking questions at any phase, you MUST follow question format guidelines.

**See `common/question-format-guide.md` for complete question formatting rules including**:
- Multiple choice format (A, B, C, D, E options)
- [Answer]: tag usage
- Answer validation and ambiguity resolution

## MANDATORY: Custom Welcome Message
**CRITICAL**: When starting ANY software development request, you MUST display the welcome message.

**How to Display Welcome Message**:
1. Load the welcome message from `common/welcome-message.md` (in the resolved rule details directory)
2. Display the complete message to the user
3. This should only be done ONCE at the start of a new workflow
4. Do NOT load this file in subsequent interactions to save context space

# Adaptive Software Development Workflow

---

# INCEPTION PHASE

**Purpose**: Planning, requirements gathering, and architectural decisions

**Focus**: Determine WHAT to build and WHY

**Stages in INCEPTION PHASE**:
- Workspace Detection (ALWAYS)
- Reverse Engineering (CONDITIONAL - Brownfield only)
- Requirements Analysis (ALWAYS - Adaptive depth)
- User Stories (CONDITIONAL)
- Workflow Planning (ALWAYS)
- Application Design (CONDITIONAL)
- Units Generation (CONDITIONAL)

---

## Workspace Detection (ALWAYS EXECUTE)

1. **MANDATORY**: Log initial user request in audit.md with complete raw input
2. Load all steps from `inception/workspace-detection.md`
3. Execute workspace detection:
   - Check for existing aidlc-state.md (resume if found)
   - Scan workspace for existing code
   - Determine if brownfield or greenfield
   - Check for existing reverse engineering artifacts
4. Determine next phase: Reverse Engineering (if brownfield and no artifacts) OR Requirements Analysis
5. **MANDATORY**: Log findings in audit.md
6. Present completion message to user (see workspace-detection.md for message formats)
7. Automatically proceed to next phase

## Reverse Engineering (CONDITIONAL - Brownfield Only)

**Execute IF**:
- Existing codebase detected
- No previous reverse engineering artifacts found

**Skip IF**:
- Greenfield project
- Previous reverse engineering artifacts exist

**Execution**:
1. **MANDATORY**: Log start of reverse engineering in audit.md
2. Load all steps from `inception/reverse-engineering.md`
3. Execute reverse engineering:
   - Analyze all packages and components
   - Generate a business overview of the whole system covering the business transactions
   - Generate architecture documentation
   - Generate code structure documentation
   - Generate API documentation
   - Generate component inventory
   - Generate Interaction Diagrams depicting how business transactions are implemented across components
   - Generate technology stack documentation
   - Generate dependencies documentation

4. **AutoSkills (conditional)**: If the AutoSkills extension is enabled, run the `midudev-autoskills` subagent to discover recommended skills for this brownfield project (see `reverse-engineering.md` Step 11). Write results to `aidlc-docs/autoskills-recommendations.md`.
5. **Wait for Explicit Approval**: Present detailed completion message (see reverse-engineering.md for message format) - DO NOT PROCEED until user confirms
6. **MANDATORY**: Log user's response in audit.md with complete raw input

## Requirements Analysis (ALWAYS EXECUTE - Adaptive Depth)

**Always executes** but depth varies based on request clarity and complexity:
- **Minimal**: Simple, clear request - just document intent analysis
- **Standard**: Normal complexity - gather functional and non-functional requirements
- **Comprehensive**: Complex, high-risk - detailed requirements with traceability

**Execution**:
1. **MANDATORY**: Log any user input during this phase in audit.md
2. Load all steps from `inception/requirements-analysis.md`
3. Execute requirements analysis:
   - Load reverse engineering artifacts (if brownfield)
   - Analyze user request (intent analysis)
   - Determine requirements depth needed
   - Assess current requirements
   - Ask clarifying questions (if needed)
   - Generate requirements document
4. Execute at appropriate depth (minimal/standard/comprehensive)
5. **Wait for Explicit Approval**: Follow approval format from requirements-analysis.md detailed steps - DO NOT PROCEED until user confirms
6. **MANDATORY**: Log user's response in audit.md with complete raw input

## User Stories (CONDITIONAL)

**INTELLIGENT ASSESSMENT**: Use multi-factor analysis to determine if user stories add value:

**ALWAYS Execute IF** (High Priority Indicators):
- New user-facing features or functionality
- Changes affecting user workflows or interactions
- Multiple user types or personas involved
- Complex business requirements with acceptance criteria needs
- Cross-functional team collaboration required
- Customer-facing API or service changes
- New product capabilities or enhancements

**LIKELY Execute IF** (Medium Priority - Assess Complexity):
- Modifications to existing user-facing features
- Backend changes that indirectly affect user experience
- Integration work that impacts user workflows
- Performance improvements with user-visible benefits
- Security enhancements affecting user interactions
- Data model changes affecting user data or reports

**COMPLEXITY-BASED ASSESSMENT**: For medium priority cases, execute user stories if:
- Request involves multiple components or services
- Changes span multiple user touchpoints
- Business logic is complex or has multiple scenarios
- Requirements have ambiguity that stories could clarify
- Implementation affects multiple user journeys
- Change has significant business impact or risk

**SKIP ONLY IF** (Low Priority - Simple Cases):
- Pure internal refactoring with zero user impact
- Simple bug fixes with clear, isolated scope
- Infrastructure changes with no user-facing effects
- Technical debt cleanup with no functional changes
- Developer tooling or build process improvements
- Documentation-only updates

**ASSESSMENT CRITERIA**: When in doubt, favor inclusion of user stories for:
- Requests with business stakeholder involvement
- Changes requiring user acceptance testing
- Features with multiple implementation approaches
- Work that benefits from shared team understanding
- Projects where requirements clarity is valuable

**ASSESSMENT PROCESS**: 
1. Analyze request complexity and scope
2. Identify user impact (direct or indirect)
3. Evaluate business context and stakeholder needs
4. Consider team collaboration benefits
5. Default to inclusion for borderline cases

**Note**: If Requirements Analysis executed, Stories can reference and build upon those requirements.

**User Stories has two parts within one stage**:
1. **Part 1 - Planning**: Create story plan with questions, collect answers, analyze for ambiguities, get approval
2. **Part 2 - Generation**: Execute approved plan to generate stories and personas

**Execution**:
1. **MANDATORY**: Log any user input during this phase in audit.md
2. Load all steps from `inception/user-stories.md`
3. **MANDATORY**: Perform intelligent assessment (Step 1 in user-stories.md) to validate user stories are needed
4. Load reverse engineering artifacts (if brownfield)
5. If Requirements exist, reference them when creating stories
6. Execute at appropriate depth (minimal/standard/comprehensive)
7. **PART 1 - Planning**: Create story plan with questions, wait for user answers, analyze for ambiguities, get approval
8. **PART 2 - Generation**: Execute approved plan to generate stories and personas
9. **Wait for Explicit Approval**: Follow approval format from user-stories.md detailed steps - DO NOT PROCEED until user confirms
10. **MANDATORY**: Log user's response in audit.md with complete raw input

## Workflow Planning (ALWAYS EXECUTE)

1. **MANDATORY**: Log any user input during this phase in audit.md
2. Load all steps from `inception/workflow-planning.md`
3. **MANDATORY**: Load content validation rules from `common/content-validation.md`
4. Load all prior context:
   - Reverse engineering artifacts (if brownfield)
   - Intent analysis
   - Requirements (if executed)
   - User stories (if executed)
5. Execute workflow planning:
   - Determine which phases to execute
   - Determine depth level for each phase
   - Create multi-package change sequence (if brownfield)
   - Generate workflow visualization (VALIDATE Mermaid syntax before writing)
6. **AutoSkills (conditional — greenfield only)**: If the AutoSkills extension is enabled AND this is a greenfield project (Reverse Engineering was not executed), run the `midudev-autoskills` subagent (see `workflow-planning.md` Step 9). Write results to `aidlc-docs/autoskills-recommendations.md`.
7. **MANDATORY**: Validate all content before file creation per content-validation.md rules
8. **Wait for Explicit Approval**: Present recommendations using language from workflow-planning.md Step 10, emphasizing user control to override recommendations - DO NOT PROCEED until user confirms
9. **MANDATORY**: Log user's response in audit.md with complete raw input

## Application Design (CONDITIONAL)

**Execute IF**:
- New components or services needed
- Component methods and business rules need definition
- Service layer design required
- Component dependencies need clarification

**Skip IF**:
- Changes within existing component boundaries
- No new components or methods
- Pure implementation changes

**Execution**:
1. **MANDATORY**: Log any user input during this phase in audit.md
2. Load all steps from `inception/application-design.md`
3. Load reverse engineering artifacts (if brownfield)
4. Execute at appropriate depth (minimal/standard/comprehensive)
5. **Wait for Explicit Approval**: Present detailed completion message (see application-design.md for message format) - DO NOT PROCEED until user confirms
6. **MANDATORY**: Log user's response in audit.md with complete raw input

## Units Generation (CONDITIONAL)

**Execute IF**:
- System needs decomposition into multiple units of work
- Multiple services or modules required
- Complex system requiring structured breakdown

**Skip IF**:
- Single simple unit
- No decomposition needed
- Straightforward single-component implementation

**Execution**:
1. **MANDATORY**: Log any user input during this phase in audit.md
2. Load all steps from `inception/units-generation.md`
3. Load reverse engineering artifacts (if brownfield)
4. Execute at appropriate depth (minimal/standard/comprehensive)
5. **Wait for Explicit Approval**: Present detailed completion message (see units-generation.md for message format) - DO NOT PROCEED until user confirms
6. **MANDATORY**: Log user's response in audit.md with complete raw input

---

# 🟢 CONSTRUCTION PHASE

**Purpose**: Detailed design, NFR implementation, and code generation

**Focus**: Determine HOW to build it

**Stages in CONSTRUCTION PHASE**:
- Per-Unit Loop (executes for each unit):
  - Functional Design (CONDITIONAL, per-unit)
  - NFR Requirements (CONDITIONAL, per-unit)
  - NFR Design (CONDITIONAL, per-unit)
  - Infrastructure Design (CONDITIONAL, per-unit)
  - Code Generation (ALWAYS, per-unit)
- Build and Test (ALWAYS - after all units complete)

**Note**: Each unit is completed fully (design + code) before moving to the next unit.

---

## Per-Unit Loop (Executes for Each Unit)

**For each unit of work, execute the following stages in sequence:**

### Functional Design (CONDITIONAL, per-unit)

**Execute IF**:
- New data models or schemas
- Complex business logic
- Business rules need detailed design

**Skip IF**:
- Simple logic changes
- No new business logic

**Execution**:
1. **MANDATORY**: Log any user input during this stage in audit.md
2. Load all steps from `construction/functional-design.md`
3. Execute functional design for this unit
4. **MANDATORY**: Present standardized 2-option completion message as defined in functional-design.md - DO NOT use emergent 3-option behavior
5. **Wait for Explicit Approval**: User must choose between "Request Changes" or "Continue to Next Stage" - DO NOT PROCEED until user confirms
6. **MANDATORY**: Log user's response in audit.md with complete raw input

### NFR Requirements (CONDITIONAL, per-unit)

**Execute IF**:
- Performance requirements exist
- Security considerations needed
- Scalability concerns present
- Tech stack selection required

**Skip IF**:
- No NFR requirements
- Tech stack already determined

**Execution**:
1. **MANDATORY**: Log any user input during this stage in audit.md
2. Load all steps from `construction/nfr-requirements.md`
3. Execute NFR assessment for this unit
4. **MANDATORY**: Present standardized 2-option completion message as defined in nfr-requirements.md - DO NOT use emergent behavior
5. **Wait for Explicit Approval**: User must choose between "Request Changes" or "Continue to Next Stage" - DO NOT PROCEED until user confirms
6. **MANDATORY**: Log user's response in audit.md with complete raw input

### NFR Design (CONDITIONAL, per-unit)

**Execute IF**:
- NFR Requirements was executed
- NFR patterns need to be incorporated

**Skip IF**:
- No NFR requirements
- NFR Requirements was skipped

**Execution**:
1. **MANDATORY**: Log any user input during this stage in audit.md
2. Load all steps from `construction/nfr-design.md`
3. Execute NFR design for this unit
4. **MANDATORY**: Present standardized 2-option completion message as defined in nfr-design.md - DO NOT use emergent behavior
5. **Wait for Explicit Approval**: User must choose between "Request Changes" or "Continue to Next Stage" - DO NOT PROCEED until user confirms
6. **MANDATORY**: Log user's response in audit.md with complete raw input

### Infrastructure Design (CONDITIONAL, per-unit)

**Execute IF**:
- Infrastructure services need mapping
- Deployment architecture required
- Cloud resources need specification

**Skip IF**:
- No infrastructure changes
- Infrastructure already defined

**Execution**:
1. **MANDATORY**: Log any user input during this stage in audit.md
2. Load all steps from `construction/infrastructure-design.md`
3. Execute infrastructure design for this unit
4. **MANDATORY**: Present standardized 2-option completion message as defined in infrastructure-design.md - DO NOT use emergent behavior
5. **Wait for Explicit Approval**: User must choose between "Request Changes" or "Continue to Next Stage" - DO NOT PROCEED until user confirms
6. **MANDATORY**: Log user's response in audit.md with complete raw input

### Code Generation (ALWAYS EXECUTE, per-unit)

**Always executes for each unit**

**Code Generation has two parts within one stage**:
1. **Part 1 - Planning**: Create detailed code generation plan with explicit steps
2. **Part 2 - Generation**: Execute approved plan to generate code, tests, and artifacts

**Execution**:
1. **MANDATORY**: Log any user input during this stage in audit.md
2. Load all steps from `construction/code-generation.md`
3. **SUBAGENT — Planner (ALWAYS)**: Execute the `planner` subagent BEFORE planning code generation:
   ```bash
   python scripts/subagents/manager.py planner '{"run_folder": "."}'
   ```
   Read `aidlc-docs/construction-plan.md` and incorporate its install/test/lint/build steps into the code generation plan.
4. **PART 1 - Planning**: Create code generation plan with checkboxes, get user approval
5. **PART 2 - Generation**: Execute approved plan to generate code for this unit
6. **SUBAGENT — Code Review (ALWAYS)**: Execute the `code-reviewer` subagent AFTER code generation completes for this unit:
   ```bash
   python scripts/subagents/manager.py code-reviewer '{"run_folder": "."}'
   ```
   Present lint/security findings to the user. Blocking findings must be resolved before proceeding.
7. **MANDATORY**: Present standardized 2-option completion message as defined in code-generation.md - DO NOT use emergent behavior
8. **Wait for Explicit Approval**: User must choose between "Request Changes" or "Continue to Next Stage" - DO NOT PROCEED until user confirms
9. **MANDATORY**: Log user's response in audit.md with complete raw input

---

## Build and Test (ALWAYS EXECUTE)

1. **MANDATORY**: Log any user input during this phase in audit.md
2. Load all steps from `construction/build-and-test.md`
3. **SUBAGENT — Full Pipeline (ALWAYS)**: Execute the full construction pipeline. This runs all agents in the correct order (planner → [builder + code-reviewer] → construction-reviewer → memory):
   ```bash
   python scripts/subagents/pipeline.py construction-full '{"run_folder": "."}'
   ```
   Read the generated artifacts (`aidlc-docs/construction-plan.md`, `aidlc-docs/build-report.md`, `aidlc-docs/construction-review.md`) and present findings to the user.
   
   **Alternative — Run agents individually**: If the pipeline fails or you need granular control, run agents one by one:
   ```bash
   python scripts/subagents/manager.py builder '{"run_folder": "."}'
   python scripts/subagents/manager.py construction-reviewer '{"run_folder": "."}'
   ```
4. Generate comprehensive build and test instructions:
   - Build instructions for all units
   - Unit test execution instructions
   - Integration test instructions (test interactions between units)
   - Performance test instructions (if applicable)
   - Additional test instructions as needed (contract tests, security tests, e2e tests)
5. Create instruction files in build-and-test/ subdirectory: build-instructions.md, unit-test-instructions.md, integration-test-instructions.md, performance-test-instructions.md, build-and-test-summary.md
6. **Wait for Explicit Approval**: Ask: "**Build and test instructions complete. Ready to proceed to Operations stage?**" - DO NOT PROCEED until user confirms
7. **MANDATORY**: Log user's response in audit.md with complete raw input

---

# 🟡 OPERATIONS PHASE

**Purpose**: Placeholder for future deployment and monitoring workflows

**Focus**: How to DEPLOY and RUN it (future expansion)

**Stages in OPERATIONS PHASE**:
- Operations (PLACEHOLDER)

---

## Operations (PLACEHOLDER)

**Status**: This stage is currently a placeholder for future expansion.

The Operations stage will eventually include:
- Deployment planning and execution
- Monitoring and observability setup
- Incident response procedures
- Maintenance and support workflows
- Production readiness checklists

**Current State**: All build and test activities are handled in the CONSTRUCTION phase.

## Key Principles

- **Adaptive Execution**: Only execute stages that add value
- **Transparent Planning**: Always show execution plan before starting
- **User Control**: User can request stage inclusion/exclusion
- **Progress Tracking**: Update aidlc-state.md with executed and skipped stages
- **Complete Audit Trail**: Log ALL user inputs and AI responses in audit.md with timestamps
  - **CRITICAL**: Capture user's COMPLETE RAW INPUT exactly as provided
  - **CRITICAL**: Never summarize or paraphrase user input in audit log
  - **CRITICAL**: Log every interaction, not just approvals
- **Quality Focus**: Complex changes get full treatment, simple changes stay efficient
- **Content Validation**: Always validate content before file creation per content-validation.md rules
- **NO EMERGENT BEHAVIOR**: Construction phases MUST use standardized 2-option completion messages as defined in their respective rule files. DO NOT create 3-option menus or other emergent navigation patterns.

## MANDATORY: Plan-Level Checkbox Enforcement

### MANDATORY RULES FOR PLAN EXECUTION
1. **NEVER complete any work without updating plan checkboxes**
2. **IMMEDIATELY after completing ANY step described in a plan file, mark that step [x]**
3. **This must happen in the SAME interaction where the work is completed**
4. **NO EXCEPTIONS**: Every plan step completion MUST be tracked with checkbox updates

### Two-Level Checkbox Tracking System
- **Plan-Level**: Track detailed execution progress within each stage
- **Stage-Level**: Track overall workflow progress in aidlc-state.md
- **Update immediately**: All progress updates in SAME interaction where work is completed

## Prompts Logging Requirements
- **MANDATORY**: Log EVERY user input (prompts, questions, responses) with timestamp in audit.md
- **MANDATORY**: Capture user's COMPLETE RAW INPUT exactly as provided (never summarize)
- **MANDATORY**: Log every approval prompt with timestamp before asking the user
- **MANDATORY**: Record every user response with timestamp after receiving it
- **CRITICAL**: ALWAYS append changes to EDIT audit.md file, NEVER use tools and commands that completely overwrite its contents
- **CRITICAL**: NEVER use file writing tools and commands that overwrite the entire contents of audit.md, as this causes duplication
- Use ISO 8601 format for timestamps (YYYY-MM-DDTHH:MM:SSZ)
- Include stage context for each entry

### Audit Log Format:
```markdown
## [Stage Name or Interaction Type]
**Timestamp**: [ISO timestamp]
**User Input**: "[Complete raw user input - never summarized]"
**AI Response**: "[AI's response or action taken]"
**Context**: [Stage, action, or decision made]

---
```

### Correct Tool Usage for audit.md

✅ CORRECT:

1. Read the audit.md file
2. Append/Edit the file to make changes

❌ WRONG:

1. Read the audit.md file
2. Completely overwrite the audit.md with the contents of what you read, plus the new changes you want to add to it

## Directory Structure

```text
<WORKSPACE-ROOT>/                   # ⚠️ APPLICATION CODE HERE
├── [project-specific structure]    # Varies by project (see code-generation.md)
│
├── aidlc-docs/                     # 📄 DOCUMENTATION ONLY
│   ├── inception/                  # 🔵 INCEPTION PHASE
│   │   ├── plans/
│   │   ├── reverse-engineering/    # Brownfield only
│   │   ├── requirements/
│   │   ├── user-stories/
│   │   └── application-design/
│   ├── construction/               # 🟢 CONSTRUCTION PHASE
│   │   ├── plans/
│   │   ├── {unit-name}/
│   │   │   ├── functional-design/
│   │   │   ├── nfr-requirements/
│   │   │   ├── nfr-design/
│   │   │   ├── infrastructure-design/
│   │   │   └── code/               # Markdown summaries only
│   │   └── build-and-test/
│   ├── operations/                 # 🟡 OPERATIONS PHASE (placeholder)
│   ├── aidlc-state.md
│   └── audit.md
```

**CRITICAL RULE**:
- Application code: Workspace root (NEVER in aidlc-docs/)
- Documentation: aidlc-docs/ only
- Project structure: See code-generation.md for patterns by project type
