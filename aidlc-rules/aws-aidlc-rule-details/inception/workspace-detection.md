# Workspace Detection

**Purpose**: Detect workspace state; find AI-DLC projects

## Step 1: Check for Existing AI-DLC Project

Check if `aidlc-docs/aidlc-state.md` exists:
- **If not exists**: Start new assessment (greenfield or brownfield scan)
- **If exists**: Read `Current Stage` and `Stage Progress` — then branch:

### Branch A — Project In-Progress
`Current Stage` is NOT `CONSTRUCTION - Complete` and NOT `OPERATIONS`:
→ Load context and proceed to **Session Continuity** (`common/session-continuity.md`).

### Branch B — Project Complete + New Request Detected
ALL Construction/Operations stages are marked `[x]` in Stage Progress AND the user's current message contains a new development request (new feature, change, bug fix, refactor):
→ **This is a new iteration on a completed project.** Do NOT enter session-continuity.
→ Treat as **brownfield** — source code exists and was produced by a prior AI-DLC run.
→ Set `brownfield = true`; skip Reverse Engineering (prior artifacts exist in `aidlc-docs/`).
→ Proceed directly to **Requirements Analysis** with full brownfield context loaded.
→ Log in `aidlc-docs/audit.md`:
```
## [timestamp] WORKSPACE DETECTION - New Iteration
- Prior project complete. New request detected.
- Treating as brownfield. Skipping Reverse Engineering (prior artifacts current).
- Proceeding to Requirements Analysis.
```
→ Update `aidlc-state.md`: append a new Stage Progress block for this iteration; reset `Current Stage` to `INCEPTION - Requirements Analysis`.

### Branch C — Project Complete, No New Request
ALL stages complete AND the user is asking a question, requesting a review, or navigating previous artifacts (not new development work):
→ Enter **Session Continuity** (`common/session-continuity.md`) in read-only/review mode.
→ Present the project summary and offer: A) Start new iteration, B) Review artifacts.

## Step 2: Scan Workspace for Existing Code

**Determine if workspace has existing code:**
- Scan for source files: .java, .py, .js, .ts, .go, .rs, .cpp, .cs, .php
- Look for build files: pom.xml, package.json, build.gradle
- Detect project structure
- Identify workspace root (NOT aidlc-docs/)

**Record findings:**
```markdown
## Workspace State
- **Existing Code**: [Yes/No]
- **Programming Languages**: [List if found]
- **Build System**: [Maven/Gradle/npm/etc. if found]
- **Project Structure**: [Monolith/Microservices/Library/Empty]
- **Workspace Root**: [Absolute path]
```

## Step 2.5: Workspace Discovery

Identify all workspace directories (monorepo support). Run the following to find
directories containing a manifest file at depth ≤ 4:

```bash
find . \( -name "package.json" -o -name "pyproject.toml" -o -name "Cargo.toml" -o -name "go.mod" \) \
    -not -path "*/node_modules/*" \
    -not -path "*/.git/*" \
    -not -path "*/dist/*" \
    -not -path "*/build/*" \
    -not -path "*/.venv/*" \
    -not -path "*/target/*" \
    -not -path "*/.agents/*" \
    -not -path "*/aidlc-docs/*" \
    -maxdepth 4 \
    -exec dirname {} \; | sort -u
```

Record the resulting list as workspace directories. If only the root is found,
record `["."]`. Emit:
```
[Workspaces] N workspace(s) detected: ., backend/, frontend/
```

## Step 2.6: Skill Activation (if Python and Node.js ≥ 22.6.0 available)

Run autoskills across all detected workspaces and install framework skills:

```bash
python3 aidlc-scripts/factory_skill_sync.py sync
```

If the script is absent or Node.js < 22.6.0: skip silently and log a warning.
Universal process skills in `.agents/custom-skills/` always apply regardless.

On completion, emit:
```
[Skills] N framework skills installed/updated
```

For any technology detected by autoskills that has no matching skill, surface
the warning inline:
> ⚠ No autoskills skill found for `<technology>`. Universal skills will apply.

## Step 3: Determine Next Phase

**IF workspace is empty (no existing code)**:
- Set flag: `brownfield = false`
- Next phase: Requirements Analysis

**IF workspace has existing code**:
- Set flag: `brownfield = true`
- Check for reverse engineering artifacts in `aidlc-docs/inception/reverse-engineering/`
- **IF artifacts exist**:
    - Check staleness (artifact timestamps vs code changes)
    - **IF current**: Load → skip to Requirements Analysis
    - **IF stale**: Next: Reverse Engineering (refresh)
    - **IF user requests rerun**: Reverse Engineering
- **IF no artifacts**: Next: Reverse Engineering

## Step 4: Create Initial State File

Create `aidlc-docs/aidlc-state.md`:

```markdown
# AI-DLC State Tracking

## Project Information
- **Project Type**: [Greenfield/Brownfield]
- **Start Date**: [ISO timestamp]
- **Current Stage**: INCEPTION - Workspace Detection

## Workspace State
- **Existing Code**: [Yes/No]
- **Reverse Engineering Needed**: [Yes/No]
- **Workspace Root**: [Absolute path]

## Code Location Rules
- **Application Code**: Workspace root (NEVER in aidlc-docs/)
- **Documentation**: aidlc-docs/ only
- **Structure patterns**: See code-generation.md Critical Rules

## Stage Progress
[Will be populated as workflow progresses]
```

## Step 5: Present Completion Message

**For Brownfield Projects:**
```markdown
# 🔍 Workspace Detection Complete

Workspace analysis findings:
• **Project Type**: Brownfield project
• [AI-generated summary of workspace findings in bullet points]
• **Next Step**: Proceeding to **Reverse Engineering** to analyze existing codebase...
```

**For Greenfield Projects:**
```markdown
# 🔍 Workspace Detection Complete

Workspace analysis findings:
• **Project Type**: Greenfield project
• **Next Step**: Proceeding to **Requirements Analysis**...
```

## Step 6: Automatically Proceed

- **No user approval required** - informational only
- Automatically proceed to next phase:
  - **Brownfield**: Reverse Engineering (if no existing artifacts) or Requirements Analysis (if artifacts exist)
  - **Greenfield**: Requirements Analysis
