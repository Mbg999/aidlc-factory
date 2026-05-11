# AI-DLC (AI-Driven Development Life Cycle)

**Fork maintenance note:** para mantener esto privado pero actualizado con respecto al repo original, hay que ejecutar lo siguiente en local y despues pushearlo al origin:

```bash
git remote add upstream https://github.com/awslabs/aidlc-workflows
git fetch upstream
git merge upstream/main
git push
```

> [!IMPORTANT]
> Generative AI can make mistakes. Review all AI-generated output and associated costs before acting on them.

AI-DLC is an intelligent software development workflow that adapts to your needs, maintains quality standards, and keeps you in control of the process.

## Table of Contents

- [Common](#common)
- [Platform-Specific Setup](#kiro)
- [Usage](#usage)
- [Advanced Features (This Fork)](#advanced-features-this-fork)
  - [Skills-Only Architecture](#skills-only-architecture)
  - [Automatic Git Commits on Approvals](#automatic-git-commits-on-approvals)
  - [Multi-Agent Orchestrator (Claude Code)](#multi-agent-orchestrator-claude-code)
  - [Tool Adapters](#tool-adapters)
- [Three-Phase Adaptive Workflow](#three-phase-adaptive-workflow)
- [Key Features](#key-features)
- [Extensions](#extensions)
- [Tenets](#tenets)
- [Prerequisites](#prerequisites)
- [Troubleshooting](#troubleshooting)
- [Version Control Recommendations](#version-control-recommendations)
- [Additional Resources](#additional-resources)
- [Generated aidlc-docs/ Reference](#generated-aidlc-docs-reference)
- [Experimental: AI-Assisted Setup (Release Download)](#experimental-ai-assisted-setup-release-download)
- [Contributing](#contributing)
- [Roadmap](#roadmap)
- [License](#license)

---

## Common

1. Download the latest release zip file named `ai-dlc-rules-v<release-number>.zip` from the [Releases page](../../releases/latest) to a folder **outside** your project directory (e.g., `~/Downloads`).
2. Extract the zip. It contains an `aidlc-rules/` folder with two subdirectories:
   - `aws-aidlc-rules/` — the core AI-DLC workflow rules
   - `aws-aidlc-rule-details/` — detailed rules conditionally referenced by the core rules
3. Follow the setup instructions for your coding agent and platform below.

## What's in This Fork

This repository extends the upstream AWS AI-DLC with additional capabilities. All extensions are **opt-in** and copy-paste ready — take only what you need.

| Feature                    | What it is                                                                         | Requires                      |
| -------------------------- | ---------------------------------------------------------------------------------- | ----------------------------- |
| **Mandatory Skills**       | Engineering process skills (SKILL.md) are enforced at every stage                  | `.agents/skills/` (installer writes here) |
| **Tool adapters**          | Setup guides for Copilot, Cursor, Claude Code, Cline                               | None                          |
| **Multi-cloud security**   | Security rules with AWS + Azure examples                                           | None                          |
| **Auto-commit on approvals** | Automatically create a git commit when the user approves plans, stages, units, or progresses | Git initialized in workspace |
| **Multi-agent orchestrator** | A second workflow that executes the same AI-DLC rules across 13 specialized Claude Code subagents. Adds contract validation, parallel reviewer pool, file-glob locks + AST symbol drift, project-scoped knowledge store, budget enforcement, kill/resume, legacy adoption. | Claude Code (uses `Task()` spawning). Other tools fall back to the legacy single-agent flow automatically. |
| **Evaluation framework**   | Automated scoring and reporting pipeline                                           | Docker                        |

Core rules (`aidlc-rules/`) are identical in structure to upstream. Fork-specific additions live in `scripts/executors/`, `aidlc-rules/adapters/`, `.claude/agents/` (orchestrator + subagents), `.aidlc-orchestrator/contracts/` (handoff schemas), and `scripts/factory_*.py` (runtime).

## Persistent Memory (how it works)

This fork includes a simple, pluggable persistent memory system used by developer tools. It is designed for cross-session, multi-developer usage with offline resilience and an optional central backend (Engram).

- Default location: repository root `.aidlc-memory/` (per-developer subfolders). The directory is local by default and is added to `.gitignore` to avoid leaking private notes.
- Local storage layout:
  - `developers/<developer_id>/profile.json` — developer profile and preferences
  - `developers/<developer_id>/episodic.jsonl` — append-only event log (episodic memories)
  - `developers/<developer_id>/semantic.json` — keyed JSON knowledge store (semantic/procedural memories)
  - `shared/semantic.json` and `shared/decisions.jsonl` — project-scoped shared knowledge and decisions

- Concurrency: file-level advisory locks (POSIX `flock`) ensure safe concurrent access by multiple agents/processes.

- Backends supported:
  - Local file-backed (default)
  - Engram HTTP backend (optional): rich FTS-backed store; configured via `MemoryStore.with_engram(...)` or environment variables (see examples below)

- Read/write semantics:
  - Writes are "write-through": entries are always written locally; if Engram is configured, the system will also attempt to save to Engram (best-effort).
  - Reads prefer Engram (full-text search) and fall back to the local store on error.

- Memory types mapping to Engram: `SEMANTIC → decision`, `EPISODIC → discovery`, `PROCEDURAL → pattern`.

- Developer isolation: entries include a `tool_name` like `aidlc-memory:<developer_id>` so observations are scoped per-developer in Engram.

- Memory actions: `remember`, `recall`, `context`, `forget`, `compact`, `share`, `profile`, `list_devs`.

Quick usage examples

Python (local):

```python
from memory import MemoryStore, MemoryEntry, MemoryType

store = MemoryStore('.aidlc-memory')
store.remember('alice', 'API uses FastAPI', memory_type=MemoryType.SEMANTIC, tags=['arch'])
results = store.recall('alice', tags=['arch'])
```

Enable Engram (optional):

```python
store = MemoryStore.with_engram('.aidlc-memory', engram_url='http://127.0.0.1:7437', project='aidlc')
```

Environment variables (used by memory integrations):

```bash
export AIDLC_MEMORY_BACKEND=engram
export AIDLC_ENGRAM_URL="http://127.0.0.1:7437"
export AIDLC_ENGRAM_PROJECT="aidlc"
```

Realtime sharing notes (for small teams)

For live sharing across a small team (e.g., 5 people), run a central Engram instance and add a small broadcast bridge (WebSocket or Server-Sent Events). Options:

- Simple webhook/HTTP events from the manager
- Redis Pub/Sub + WS bridge (recommended for reliability)
- Polling Engram `/search` (simpler, higher latency)

This repo contains the local primitives and the Engram client. A bridge and client UI/CLI are recommended next steps for realtime updates.

Autonomous Memory Workflow

AI-DLC wires the persistent memory into the orchestration so tools can both
consume and produce persistent knowledge.

- Injection (read): before each stage, a best-effort load from the local memory
  (`.aidlc-memory/`) provides prior context.

- Emission (write): observations can be persisted via `MemoryStore.remember()`
  for the active `developer_id` so the knowledge is available for future sessions.

Pipeline behavior

- The workflow uses a skills-only architecture. Each stage references mandatory
  skills from `.agents/skills/<name>/SKILL.md`. If skill files are not installed,
  inline fallback processes embedded in stage rule files are used instead.

Privacy and safety

- Local-first: by default the `.aidlc-memory/` folder lives in the repo root and
  is git-ignored. Use Engram only when you intentionally enable a central
  backend (`AIDLC_MEMORY_BACKEND=engram`).
- Sensitive keys (password, token, private, aws, etc.) are redacted from audit records.

Quick run examples

Install AI-DLC for your tool and run skills-driven development:

```bash
python scripts/install_aidlc.py --tool copilot --with-agent-skills
```

- [Kiro](#kiro)
- [Amazon Q Developer](#amazon-q-developer-ide-pluginextension)
- [Cursor IDE](#cursor-ide)
- [Cline](#cline)
- [Claude Code](#claude-code)
- [GitHub Copilot](#github-copilot)
- [Other Agents](#other-agents)

---

### Kiro

AI-DLC uses [Kiro Steering Files](https://kiro.dev/docs/cli/steering/) within your project workspace.  

The commands below assume you extracted the zip to your `Downloads` folder. If you used a different location, replace `Downloads` with your actual folder path.

On macOS/Linux:

```bash
mkdir -p .kiro/steering
cp -R ~/Downloads/aidlc-rules/aws-aidlc-rules .kiro/steering/
cp -R ~/Downloads/aidlc-rules/aws-aidlc-rule-details .kiro/
```

On Windows (PowerShell):

```powershell
New-Item -ItemType Directory -Force -Path ".kiro\steering"
Copy-Item -Recurse "$env:USERPROFILE\Downloads\aidlc-rules\aws-aidlc-rules" ".kiro\steering\"
Copy-Item -Recurse "$env:USERPROFILE\Downloads\aidlc-rules\aws-aidlc-rule-details" ".kiro\"
```

On Windows (CMD):

```cmd
mkdir .kiro\steering
xcopy %USERPROFILE%\Downloads\aidlc-rules\aws-aidlc-rules .kiro\steering\aws-aidlc-rules\ /E /I
xcopy %USERPROFILE%\Downloads\aidlc-rules\aws-aidlc-rule-details .kiro\aws-aidlc-rule-details\ /E /I
```

Your project should look like:

```text
<project-root>/
    ├── .kiro/
    │     ├── steering/
    │     │      ├── aws-aidlc-rules/
    │     ├── aws-aidlc-rule-details/
```

To verify the rules are loaded:

#### Verify in Kiro IDE

Open the steering files panel and confirm you see an entry for `core-workflow` under `Workspace` as shown in the screenshot below.

<img src="./assets/images/kiro-ide-aidlc-rules-loaded.png?raw=true" alt="AI-DLC Rules in Kiro IDE" width="700" height="450">

We use Kiro IDE in Vibe mode to run the AI-DLC workflow. This ensures that AI-DLC workflow guides the development workflow in Kiro. At times, Kiro may nudge you to switch to spec mode. Select `No` to such prompts to stay in Vibe mode.

<img src="./assets/images/kiro-sdd-nudge.png?raw=true" alt="Staying in Kiro Vibe mode" width="500" height="175">

#### Verify in Kiro CLI

Run `kiro-cli`, then `/context show`, and confirm entries for `.kiro/steering/aws-aidlc-rules`.

<img src="./assets/images/kiro-cli-aidlc-rules-loaded.png?raw=true" alt="AI-DLC Rules in Kiro CLI" width="700" height="660">

---

### Amazon Q Developer IDE Plugin/Extension

AI-DLC uses [Amazon Q Rules](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/context-project-rules.html) within your project workspace.

The commands below assume you extracted the zip to your `Downloads` folder. If you used a different location, replace `Downloads` with your actual folder path.

On macOS/Linux:

```bash
mkdir -p .amazonq/rules
cp -R ~/Downloads/aidlc-rules/aws-aidlc-rules .amazonq/rules/
cp -R ~/Downloads/aidlc-rules/aws-aidlc-rule-details .amazonq/
```

On Windows (PowerShell):

```powershell
New-Item -ItemType Directory -Force -Path ".amazonq\rules"
Copy-Item -Recurse "$env:USERPROFILE\Downloads\aidlc-rules\aws-aidlc-rules" ".amazonq\rules\"
Copy-Item -Recurse "$env:USERPROFILE\Downloads\aidlc-rules\aws-aidlc-rule-details" ".amazonq\"
```

On Windows (CMD):

```cmd
mkdir .amazonq\rules
xcopy %USERPROFILE%\Downloads\aidlc-rules\aws-aidlc-rules .amazonq\rules\aws-aidlc-rules\ /E /I
xcopy %USERPROFILE%\Downloads\aidlc-rules\aws-aidlc-rule-details .amazonq\aws-aidlc-rule-details\ /E /I
```

Your project should look like:

```text
<project-root>/
    ├── .amazonq/
    │     ├── rules/
    │     │     ├── aws-aidlc-rules/
    │     ├── aws-aidlc-rule-details/
```

To verify the rules are loaded:

1. In the Amazon Q Chat window, click the `Rules` button in the lower right corner.
2. Confirm you see entries for `.amazonq/rules/aws-aidlc-rules`.

<img src="./assets/images/q-ide-aidlc-rules-loaded.png?raw=true" alt="AI-DLC Rules in Q Developer IDE plugin" width="700" height="400">

---

### Cursor IDE

AI-DLC uses [Cursor Rules](https://cursor.com/docs/context/rules) to implement its intelligent workflow.

The commands below assume you extracted the zip to your `Downloads` folder. If you used a different location, replace `Downloads` with your actual folder path.

#### Option 1: Project Rules (Recommended)

**Unix/Linux/macOS:**

```bash
mkdir -p .cursor/rules

cat > .cursor/rules/ai-dlc-workflow.mdc << 'EOF'
---
description: "AI-DLC (AI-Driven Development Life Cycle) adaptive workflow for software development"
alwaysApply: true
---

EOF
cat ~/Downloads/aidlc-rules/aws-aidlc-rules/core-workflow.md >> .cursor/rules/ai-dlc-workflow.mdc

mkdir -p .aidlc-rule-details
cp -R ~/Downloads/aidlc-rules/aws-aidlc-rule-details/* .aidlc-rule-details/
```

**Windows PowerShell:**

```powershell
New-Item -ItemType Directory -Force -Path ".cursor\rules"

$frontmatter = @"
---
description: "AI-DLC (AI-Driven Development Life Cycle) adaptive workflow for software development"
alwaysApply: true
---

"@
$frontmatter | Out-File -FilePath ".cursor\rules\ai-dlc-workflow.mdc" -Encoding utf8

Get-Content "$env:USERPROFILE\Downloads\aidlc-rules\aws-aidlc-rules\core-workflow.md" | Add-Content ".cursor\rules\ai-dlc-workflow.mdc"

New-Item -ItemType Directory -Force -Path ".aidlc-rule-details"
Copy-Item "$env:USERPROFILE\Downloads\aidlc-rules\aws-aidlc-rule-details\*" ".aidlc-rule-details\" -Recurse
```

**Windows CMD:**

```cmd
mkdir .cursor\rules

(
echo ---
echo description: "AI-DLC (AI-Driven Development Life Cycle) adaptive workflow for software development"
echo alwaysApply: true
echo ---
echo.
) > .cursor\rules\ai-dlc-workflow.mdc

type "%USERPROFILE%\Downloads\aidlc-rules\aws-aidlc-rules\core-workflow.md" >> .cursor\rules\ai-dlc-workflow.mdc

mkdir .aidlc-rule-details
xcopy "%USERPROFILE%\Downloads\aidlc-rules\aws-aidlc-rule-details" ".aidlc-rule-details\" /E /I
```

#### Option 2: AGENTS.md (Simple Alternative)

**Unix/Linux/macOS:**

```bash
cp ~/Downloads/aidlc-rules/aws-aidlc-rules/core-workflow.md ./AGENTS.md
mkdir -p .aidlc-rule-details
cp -R ~/Downloads/aidlc-rules/aws-aidlc-rule-details/* .aidlc-rule-details/
```

**Windows PowerShell:**

```powershell
Copy-Item "$env:USERPROFILE\Downloads\aidlc-rules\aws-aidlc-rules\core-workflow.md" ".\AGENTS.md"
New-Item -ItemType Directory -Force -Path ".aidlc-rule-details"
Copy-Item "$env:USERPROFILE\Downloads\aidlc-rules\aws-aidlc-rule-details\*" ".aidlc-rule-details\" -Recurse
```

**Windows CMD:**

```cmd
copy "%USERPROFILE%\Downloads\aidlc-rules\aws-aidlc-rules\core-workflow.md" ".\AGENTS.md"
mkdir .aidlc-rule-details
xcopy "%USERPROFILE%\Downloads\aidlc-rules\aws-aidlc-rule-details" ".aidlc-rule-details\" /E /I
```

**Verify Setup:**

1. Open **Cursor Settings → Rules, Commands**
2. Under **Project Rules**, you should see `ai-dlc-workflow` listed
3. For `AGENTS.md`, it will be automatically detected and applied

![AI-DLC Rules in Cursor](./assets/images/cursor-ide-aidlc-rules-loaded.png?raw=true "AI-DLC Rules in Cursor")

**Directory Structure (Option 1):**

```text
<my-project>/
├── .cursor/
│   └── rules/
│       └── ai-dlc-workflow.mdc
└── .aidlc-rule-details/
    ├── common/
    ├── inception/
    ├── construction/
    ├── extensions/
    └── operations/
```

---

### Cline

AI-DLC uses Cline Rules to implement its intelligent workflow.

The commands below assume you extracted the zip to your `Downloads` folder. If you used a different location, replace `Downloads` with your actual folder path.

#### Option 1: .clinerules Directory (Recommended)

**Unix/Linux/macOS:**

```bash
mkdir -p .clinerules
cp ~/Downloads/aidlc-rules/aws-aidlc-rules/core-workflow.md .clinerules/
mkdir -p .aidlc-rule-details
cp -R ~/Downloads/aidlc-rules/aws-aidlc-rule-details/* .aidlc-rule-details/
```

**Windows PowerShell:**

```powershell
New-Item -ItemType Directory -Force -Path ".clinerules"
Copy-Item "$env:USERPROFILE\Downloads\aidlc-rules\aws-aidlc-rules\core-workflow.md" ".clinerules\"
New-Item -ItemType Directory -Force -Path ".aidlc-rule-details"
Copy-Item "$env:USERPROFILE\Downloads\aidlc-rules\aws-aidlc-rule-details\*" ".aidlc-rule-details\" -Recurse
```

**Windows CMD:**

```cmd
mkdir .clinerules
copy "%USERPROFILE%\Downloads\aidlc-rules\aws-aidlc-rules\core-workflow.md" ".clinerules\"
mkdir .aidlc-rule-details
xcopy "%USERPROFILE%\Downloads\aidlc-rules\aws-aidlc-rule-details" ".aidlc-rule-details\" /E /I
```

#### Option 2: AGENTS.md (Alternative)

**Unix/Linux/macOS:**

```bash
cp ~/Downloads/aidlc-rules/aws-aidlc-rules/core-workflow.md ./AGENTS.md
mkdir -p .aidlc-rule-details
cp -R ~/Downloads/aidlc-rules/aws-aidlc-rule-details/* .aidlc-rule-details/
```

**Windows PowerShell:**

```powershell
Copy-Item "$env:USERPROFILE\Downloads\aidlc-rules\aws-aidlc-rules\core-workflow.md" ".\AGENTS.md"
New-Item -ItemType Directory -Force -Path ".aidlc-rule-details"
Copy-Item "$env:USERPROFILE\Downloads\aidlc-rules\aws-aidlc-rule-details\*" ".aidlc-rule-details\" -Recurse
```

**Windows CMD:**

```cmd
copy "%USERPROFILE%\Downloads\aidlc-rules\aws-aidlc-rules\core-workflow.md" ".\AGENTS.md"
mkdir .aidlc-rule-details
xcopy "%USERPROFILE%\Downloads\aidlc-rules\aws-aidlc-rule-details" ".aidlc-rule-details\" /E /I
```

**Verify Setup:**

1. In Cline's chat interface, look for the Rules popover under the chat input field
2. Verify that `core-workflow.md` is listed and active
3. You can toggle the rule file on/off as needed

![AI-DLC Rules in Cline](./assets/images/cline-ide-aidlc-rules-loaded.png?raw=true "AI-DLC Rules in Cline")

**Directory Structure (Option 1):**

```text
<my-project>/
├── .clinerules/
│   └── core-workflow.md
├── .aidlc-rule-details/
│   ├── common/
│   ├── inception/
│   ├── construction/
│   ├── extensions/
│   └── operations/
└── scripts/
    └── executors/
```

---

### Install script

You can use the bundled installer script to copy the AI-DLC rules and (optionally) agent skills into a project. The script lives at `scripts/install_aidlc.py` and supports dry-run and non-interactive modes.

Examples:

```bash
# Dry-run (shows planned actions, no files written)
python scripts/install_aidlc.py --tool cursor --dry-run

# Install into a specific destination non-interactively
python scripts/install_aidlc.py --tool cursor --dest /path/to/project --yes

# Install with agent skills (RECOMMENDED for full workflow enforcement)
python scripts/install_aidlc.py --tool copilot --dest /path/to/project --yes --with-agent-skills
```

Key options:

- `--tool`: target agent (one of `kiro`, `amazonq`, `cursor`, `cline`, `claude`, `copilot`, `other`)
- `--dest`: destination path to install rules into (defaults to current directory; interactive prompt if omitted)
- `--dry-run`: show planned changes without performing them
- `--yes`: assume yes for confirmation prompts (useful for scripting / CI)
- `--with-agent-skills`: install SKILL.md files from github.com/addyosmani/agent-skills
- `--agent-skills-path`: use a local clone instead of fetching from GitHub
- `--source`: optional path to a local `aidlc-rules` folder to use instead of the packaged rules

Note: when using `--with-agent-skills`, the installer will install agent skills into the destination project's `.agents/skills/` directory (the canonical location used by the workflow). Without skills installed, the workflow uses inline fallback processes embedded in each stage rule file.

After running the installer, verify the created files for your target tool (for example: `.cursor/rules/ai-dlc-workflow.mdc` for Cursor, `.github/copilot-instructions.md` for Copilot, or `.kiro/steering/aws-aidlc-rules/` for Kiro).

---

### Claude Code

AI-DLC uses Claude Code's project memory file (`CLAUDE.md`) to implement its intelligent workflow.

The commands below assume you extracted the zip to your `Downloads` folder. If you used a different location, replace `Downloads` with your actual folder path.

#### Option 1: Project Root (Recommended)

**Unix/Linux/macOS:**

```bash
cp ~/Downloads/aidlc-rules/aws-aidlc-rules/core-workflow.md ./CLAUDE.md
mkdir -p .aidlc-rule-details
cp -R ~/Downloads/aidlc-rules/aws-aidlc-rule-details/* .aidlc-rule-details/
```

**Windows PowerShell:**

```powershell
Copy-Item "$env:USERPROFILE\Downloads\aidlc-rules\aws-aidlc-rules\core-workflow.md" ".\CLAUDE.md"
New-Item -ItemType Directory -Force -Path ".aidlc-rule-details"
Copy-Item "$env:USERPROFILE\Downloads\aidlc-rules\aws-aidlc-rule-details\*" ".aidlc-rule-details\" -Recurse
```

**Windows CMD:**

```cmd
copy "%USERPROFILE%\Downloads\aidlc-rules\aws-aidlc-rules\core-workflow.md" ".\CLAUDE.md"
mkdir .aidlc-rule-details
xcopy "%USERPROFILE%\Downloads\aidlc-rules\aws-aidlc-rule-details" ".aidlc-rule-details\" /E /I
```

#### Option 2: .claude Directory

**Unix/Linux/macOS:**

```bash
mkdir -p .claude
cp ~/Downloads/aidlc-rules/aws-aidlc-rules/core-workflow.md .claude/CLAUDE.md
mkdir -p .aidlc-rule-details
cp -R ~/Downloads/aidlc-rules/aws-aidlc-rule-details/* .aidlc-rule-details/
```

**Windows PowerShell:**

```powershell
New-Item -ItemType Directory -Force -Path ".claude"
Copy-Item "$env:USERPROFILE\Downloads\aidlc-rules\aws-aidlc-rules\core-workflow.md" ".claude\CLAUDE.md"
New-Item -ItemType Directory -Force -Path ".aidlc-rule-details"
Copy-Item "$env:USERPROFILE\Downloads\aidlc-rules\aws-aidlc-rule-details\*" ".aidlc-rule-details\" -Recurse
```

**Windows CMD:**

```cmd
mkdir .claude
copy "%USERPROFILE%\Downloads\aidlc-rules\aws-aidlc-rules\core-workflow.md" ".claude\CLAUDE.md"
mkdir .aidlc-rule-details
xcopy "%USERPROFILE%\Downloads\aidlc-rules\aws-aidlc-rule-details" ".aidlc-rule-details\" /E /I
```

**Verify Setup:**

1. Start Claude Code in your project directory (CLI: `claude` or VS Code extension)
2. Use the `/config` command to view current configuration
3. Ask Claude: "What instructions are currently active in this project?"

**Directory Structure (Option 1):**

```text
<my-project>/
├── CLAUDE.md
└── .aidlc-rule-details/
    ├── common/
    ├── inception/
    ├── construction/
    ├── extensions/
    └── operations/
```

---

### GitHub Copilot

AI-DLC uses [GitHub Copilot custom instructions](https://code.visualstudio.com/docs/copilot/customization/custom-instructions) to implement its intelligent workflow. The `.github/copilot-instructions.md` file is automatically detected and applied to all chat requests in the workspace.

The commands below assume you extracted the zip to your `Downloads` folder. If you used a different location, replace `Downloads` with your actual folder path.

**Unix/Linux/macOS:**

```bash
mkdir -p .github
cp ~/Downloads/aidlc-rules/aws-aidlc-rules/core-workflow.md .github/copilot-instructions.md
mkdir -p .aidlc-rule-details
cp -R ~/Downloads/aidlc-rules/aws-aidlc-rule-details/* .aidlc-rule-details/
```

**Windows PowerShell:**

```powershell
New-Item -ItemType Directory -Force -Path ".github"
Copy-Item "$env:USERPROFILE\Downloads\aidlc-rules\aws-aidlc-rules\core-workflow.md" ".github\copilot-instructions.md"
New-Item -ItemType Directory -Force -Path ".aidlc-rule-details"
Copy-Item "$env:USERPROFILE\Downloads\aidlc-rules\aws-aidlc-rule-details\*" ".aidlc-rule-details\" -Recurse
```

**Windows CMD:**

```cmd
mkdir .github
copy "%USERPROFILE%\Downloads\aidlc-rules\aws-aidlc-rules\core-workflow.md" ".github\copilot-instructions.md"
mkdir .aidlc-rule-details
xcopy "%USERPROFILE%\Downloads\aidlc-rules\aws-aidlc-rule-details" ".aidlc-rule-details\" /E /I
```

**Verify Setup:**

1. Open VS Code with your project folder
2. Open the Copilot Chat panel (Cmd/Ctrl+Shift+I)
3. Select **Configure Chat** (gear icon) > **Chat Instructions** and verify that `copilot-instructions` is listed
4. Alternatively, type `/instructions` in the chat input to view active instructions

**Directory Structure:**

```text
<my-project>/
├── .github/
│   └── copilot-instructions.md
└── .aidlc-rule-details/
    ├── common/
    ├── inception/
    ├── construction/
    ├── extensions/
    └── operations/
```

---

### Other Agents

AI-DLC works with any coding agent that supports project-level rules or steering files. The general approach:

1. Place `aws-aidlc-rules/` wherever your agent reads project rules from (consult your agent's documentation).
2. Place `aws-aidlc-rule-details/` at a sibling level so the rules can reference it.

If your agent has no convention for rules files, place both folders at your project root and point the agent to `aws-aidlc-rules/` as its rules directory.

See `aidlc-rules/adapters/generic.md` for a template you can adapt to any tool.

---

## Advanced Features (This Fork)

### Skills-Only Architecture

This fork uses a **skills-only** architecture. There are no scripted subagents or external agent personas. Instead, every workflow stage references mandatory engineering process skills from `.agents/skills/<name>/SKILL.md`.

**Where skills are resolved** (in order):

1. `<project>/.agents/skills/<skill-name>/SKILL.md` (installer writes here)
2. `~/.agents/skills/<skill-name>/SKILL.md` (user-global fallback)

**Installing skills:**

```bash
python scripts/install_aidlc.py --tool copilot --with-agent-skills
```

If skills are not installed, each stage rule file contains an **inline fallback process** so the workflow is never bypassed — it always enforces the skill's steps.

**Skills by workflow phase:**

| Phase | Skills |
|-------|--------|
| Inception | spec-driven-development, planning-and-task-breakdown, idea-refine, source-driven-development |
| Construction | incremental-implementation, test-driven-development, code-review-and-quality, debugging-and-error-recovery, security-and-hardening, performance-optimization |
| Operations | ci-cd-and-automation, shipping-and-launch, documentation-and-adrs |

### Automatic Git Commits on Approvals

When you explicitly approve a plan, a stage completion, a unit construction phase, or ask the workflow to "continue"/"next"/"approve", AI-DLC will automatically stage changes and create a git commit to record the approved artifacts.

- What it does: runs `git add -A && git commit -m "<type>(<scope>): <description>"` to capture all generated artifacts and state updates.
- Commit format:
  - `<type>`: `docs` for plans/questions, `feat` for generated code, `build` for build/test artifacts
  - `<scope>`: stage or unit name in kebab-case (e.g., `requirements-analysis`, `functional-design`)
  - `<description>`: concise summary (e.g., "approve requirements analysis", "complete auth unit codegen")
- Non-blocking: If `git` is not available, the repository is not initialized, or there is nothing to commit, AI-DLC logs a warning to `aidlc-docs/audit.md` and continues.

This behavior is controlled by the Approval Protocol in `aidlc-rules/aws-aidlc-rule-details/common/stage-conventions.md`.

---

### Multi-Agent Orchestrator (Claude Code)

The orchestrator is a **second execution model** for the AI-DLC workflow. It runs the same rule files (`aidlc-rules/aws-aidlc-rule-details/inception/workspace-detection.md`, `requirements-analysis.md`, `code-generation.md`, …) but through 13 specialized Claude Code subagents instead of a single role-switching agent. The two workflows coexist by design — pick whichever fits the task.

| | Legacy single-agent (`/spec`, `/plan`, …) | Multi-agent orchestrator (`/factory-spec`, …) |
|---|---|---|
| Driver | `CLAUDE.md` (= `core-workflow.md`) | `.claude/agents/orchestrator.md` + 13 stage subagents |
| Tooling support | Copilot / Cursor / Cline / Amazon Q / Kiro / Claude Code | Claude Code only (uses `Task()` spawning) |
| Execution | One agent, role-switches per stage | One subagent per stage, parallel where possible |
| State | `aidlc-docs/` (committed) | `aidlc-docs/` + `.aidlc-orchestrator/runs/<run-id>/` (gitignored runtime: manifest, budget, timeline, locks, handoffs) |
| Reviewer pool | Sequential | Parallel fan-out (code / security / performance / simplifier) |
| Conflict handling | Manual | File-glob lock registry + Python/TS AST symbol-drift detection |
| Budget enforcement | None | Pre-flight gate (ok / downshift / skip / halt) + post-flight reconciliation |
| Knowledge persistence | Implicit (rule files) | engram-backed, project-scoped (`aidlc/<project>/<kind>/<slug>`) |
| Crash recovery | Re-run | `/factory-resume <run-id>` (kill-and-resume preserves work) |
| Legacy `aidlc-docs/` projects | Continue as-is | `/factory-resume` (no args) adopts them as a synthetic run |

Both workflows read the **same rule files** — the rule corpus is the single source of truth. Each subagent's system prompt explicitly says "Follow the rule file: `aidlc-rules/aws-aidlc-rule-details/inception/<stage>.md`" and executes its declared steps. Skills (`.agents/skills/<name>/SKILL.md`) are mandatory in both paths.

**When to use which:**

- **Legacy** — small features, single-file changes, doc edits, non-Claude tools, or when you want minimum ceremony.
- **Orchestrator** — multi-component features (parallel code-gen across units), brownfield refactors (where reverse-engineer adds value), runs that need budget caps, runs you want to resume after a crash, or any time you want a stricter audit trail.

**Slash commands** (Claude Code, after install):

| Command | Stage(s) | Notes |
|---|---|---|
| `/factory-spec <feature>` | workspace-scout + (reverse-engineer ask) + requirements-analyst | Phase 0 entrypoint |
| `/factory-plan <run-id>` | workflow-planner + (optional) unit-decomposer + (optional) story-writer | Phase 1 |
| `/factory-build <run-id>` | code-generator × N + build-test-agent × N (layer-parallel with locks + AST drift checks) | Phase 5 parallel construction |
| `/factory-review <run-id>` | reviewer-{code, security, performance, simplifier} in parallel | Phase 4 reviewer pool |
| `/factory-ship <run-id>` | ship-agent | Release notes, ADRs, CHANGELOG, CI/CD wiring |
| `/factory-resume <run-id>` | resumes from last checkpoint; with no run-id, adopts legacy `aidlc-docs/` | Phase 6 |
| `/factory-replay <run-id> --from <stage>` | re-runs from a chosen stage; archives prior outputs as `*.replay-<ts>.yaml` | Phase 6 |

**Installation:** the orchestrator artifacts ship with the installer. Use the `--with-orchestrator` flag (default yes when interactive):

```bash
python scripts/install_aidlc.py --tool claude --with-orchestrator
```

This copies:

- `.claude/agents/` — orchestrator + 13 stage subagents + 3 cross-cutting agents (knowledge / conflict-resolver / cost-governor)
- `.claude/commands/factory-*.md` — 7 slash commands
- `.aidlc-orchestrator/contracts/` — 20 JSON Schema handoff contracts
- `.aidlc-orchestrator/budgets/default.yaml` — Cost Governor policy
- `scripts/factory_{validate,budget,merge_reviews,conflict,run}.py` — runtime
- `.gitignore` entries for `.aidlc-orchestrator/runs/` and `.aidlc-orchestrator/knowledge/`
- A pointer block appended to `CLAUDE.md` listing the `/factory-*` commands

For non-Claude tools, the installer still copies the contracts and scripts (they're useful for manual validation) but skips the subagents — those tools run in degraded single-agent mode per `aidlc-rules/adapters/<tool>.md`.

**Design doc:** [`ORCHESTRATOR-PLAN.md`](ORCHESTRATOR-PLAN.md) — phases 0-6, decisions, file layout, run lifecycle, and acceptance criteria. Live integration test findings: [`ORCHESTRATOR-LIVE-TEST-FINDINGS.md`](ORCHESTRATOR-LIVE-TEST-FINDINGS.md).

---

### Tool Adapters

Adapter files explain how to wire AI-DLC rules into each agentic coding tool. They live in `aidlc-rules/adapters/` and are informational only — the core rules stay unchanged.

| File                                                              | Tool            |
| ----------------------------------------------------------------- | --------------- |
| [`adapters/copilot.md`](aidlc-rules/adapters/copilot.md)          | GitHub Copilot  |
| [`adapters/cursor.md`](aidlc-rules/adapters/cursor.md)            | Cursor          |
| [`adapters/claude-code.md`](aidlc-rules/adapters/claude-code.md)  | Claude Code     |
| [`adapters/cline.md`](aidlc-rules/adapters/cline.md)              | Cline           |
| [`adapters/generic.md`](aidlc-rules/adapters/generic.md)          | Any other agent |

## Usage

There are two entry points; both run the same AI-DLC rules and produce artifacts under `aidlc-docs/`.

### Legacy single-agent workflow (all tools)

1. Start any software development project by stating your intent starting with the phrase **"Using AI-DLC, ..."** in the chat
2. AI-DLC workflow automatically activates and guides you from there
3. Answer structured questions that AI-DLC asks you
4. Carefully review every plan that AI generates. Provide your oversight and validation
5. Review the execution plan to see which stages will run
6. Carefully review the artifacts and approve each stage to maintain control
7. All the artifacts will be generated in the `aidlc-docs/` directory

### Multi-agent orchestrator (Claude Code only)

Requires installing with `--with-orchestrator` (see [Multi-Agent Orchestrator](#multi-agent-orchestrator-claude-code) above). Then in a Claude Code session at the project root:

1. Invoke `/factory-spec <feature description>` — runs workspace-scout, asks whether to run reverse-engineer (brownfield-with-no-RE-artifacts only), then requirements-analyst (Pass 1 surfaces questions; you answer; Pass 2 writes `requirements.md`).
2. Invoke `/factory-plan <run-id>` to produce the execution plan and (optionally) decompose into parallel units.
3. Invoke `/factory-build <run-id>` to run code-generator + build-test-agent layer-parallel under file-glob locks with AST symbol-drift detection.
4. Invoke `/factory-review <run-id>` to fan out all four reviewers in parallel and merge their findings.
5. Invoke `/factory-ship <run-id>` for release notes, ADRs, CHANGELOG, optional CI/CD wiring.

If a run crashes mid-flight, `/factory-resume <run-id>` picks up from the last checkpoint. Used without an argument it adopts an existing legacy `aidlc-docs/` project as a synthetic run.

The run-scoped state (manifest, budget, timeline, locks, knowledge-side handoffs) lives in `.aidlc-orchestrator/runs/<run-id>/` and is gitignored. The `aidlc-docs/` artifacts are committed exactly as in the legacy flow.

---

## Three-Phase Adaptive Workflow

AI-DLC follows a structured three-phase approach that adapts to your project's complexity:

### 🔵 INCEPTION PHASE

Determines **WHAT** to build and **WHY**

- Requirements analysis and validation
- User story creation (when applicable)
- Application Design and creating units of work for parallel development
- Risk assessment and complexity evaluation

### 🟢 CONSTRUCTION PHASE

Determines **HOW** to build it

- Detailed component design
- Code generation and implementation
- Build configuration and testing strategies
- Quality assurance and validation

### 🟡 OPERATIONS PHASE

Deployment and monitoring (future)

- Deployment automation and infrastructure
- Monitoring and observability setup
- Production readiness validation

---

## Key Features

| Feature                   | Description                                                                                               |
| ------------------------- | --------------------------------------------------------------------------------------------------------- |
| **Adaptive Intelligence** | Only executes stages that add value to your specific request                                              |
| **Context-Aware**         | Analyzes existing codebase and complexity requirements                                                    |
| **Risk-Based**            | Complex changes get comprehensive treatment, simple changes stay efficient                                |
| **Question-Driven**       | Structured multiple-choice questions in files, not chat                                                   |
| **Always in Control**     | Review execution plans and approve each phase                                                             |
| **Extensible**            | Layer custom rules e.g. security, compliance, and organization-specific rules on top of the core workflow |

---

## Extensions

AI-DLC supports an extension system that lets you layer additional rules on top of the core workflow. Extensions are markdown files organized under `aws-aidlc-rule-details/extensions/` and grouped by category (e.g., `security/`, `testing/`).

### How Extensions Work

Each extension consists of two files placed in the same directory:

- A **rules file** (e.g., `security-baseline.md`) containing the extension's rules.
- An **opt-in file** (e.g., `security-baseline.opt-in.md`) containing a structured multiple-choice question presented to the user during Requirements Analysis.

At workflow start, AI-DLC scans the `extensions/` directory and loads only `*.opt-in.md` files. During Requirements Analysis, it presents each opt-in prompt to the user. When the user opts in, the corresponding rules file is loaded (derived by naming convention: strip `.opt-in.md`, append `.md`). When the user opts out, the rules file is never loaded. Extensions without a matching `*.opt-in.md` file are always enforced.

Once enabled, extension rules are blocking constraints — at each stage, the model verifies compliance before allowing the stage to proceed.

### Built-in Extensions

The `extensions/` directory ships with the following (new extensions may be added over time):

```text
aws-aidlc-rule-details/
└── extensions/
    ├── security/                      # Extension category
    │   └── baseline/
    │       ├── security-baseline.md          # Baseline security rules
    │       └── security-baseline.opt-in.md   # Opt-in prompt
    └── testing/                       # Extension category
        └── property-based/
            ├── property-based-testing.md          # Property-based testing rules
            └── property-based-testing.opt-in.md   # Opt-in prompt
```

> [!IMPORTANT]
> The security extension rules are provided as a directional reference for building effective security rules within AI-DLC workflows. Each organization should build, customize, and thoroughly test their own security rules before deploying in production workflows.

### Adding Your Own Extensions

You can extend an existing category or create an entirely new one.

1. Create a directory under `extensions/` (e.g., `security/compliance/` or `performance/baseline/`).
2. Add a **rules file** (e.g., `compliance.md`). Follow the same structure as `security-baseline.md`:
   - Define each rule as a heading in the format `## Rule <PREFIX-NN>: <Title>` where the prefix is a short category identifier and NN is a sequential number (e.g., `COMPLIANCE-01`, `COMPLIANCE-02`). These IDs are referenced in audit logs and compliance summaries, so they must be unique across all loaded extensions.
   - Include a **Rule** section describing the requirement.
   - Include a **Verification** section with concrete checks the model should evaluate.
3. Add a matching **opt-in file** using the naming convention `<name>.opt-in.md` (e.g., `compliance.opt-in.md`). See `security-baseline.opt-in.md` for the expected format. Omitting this file means the extension is always enforced with no user opt-out.
4. Rules are blocking by default — if verification criteria are not met, the stage cannot proceed until the finding is resolved.

---

## Tenets

These are our core principles to guide our decision making.

- **No duplication**. The source of truth lives in one place. If we add support for new tools or formats that require specific files, we generate them from the source rather than maintaining separate copies.

- **Methodology first**. AI-DLC is fundamentally a methodology, not a tool. Users shouldn't need to install anything to get started. That said, we're open to convenience tooling (scripts, CLIs) down the road if it helps users adopt or extend the methodology.

- **Reproducible**. Rules should be clear enough that different models produce similar outcomes. We know models behave differently, but the methodology should minimize variance through explicit guidance.

- **Agnostic**. The methodology works with any IDE, agent, or model. We don't tie ourselves to specific tools or vendors.

- **Human in the loop**. Critical decisions require explicit user confirmation. The agent proposes, the human approves.

---

## Prerequisites

Have one of our supported platforms/tools for Assisted AI Coding installed:

| Platform                      | Installation Link                                                                                                                                               |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Kiro                          | [Install](https://kiro.dev/)                                                                                                                                    |
| Kiro CLI                      | [Install](https://kiro.dev/cli/)                                                                                                                                |
| Amazon Q Developer IDE Plugin | [Install](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/q-in-IDE.html)                                                                               |
| Cursor IDE                    | [Install](https://cursor.com/)                                                                                                                                  |
| Cline VS Code Extension       | [Install](https://marketplace.visualstudio.com/items?itemName=saoudrizwan.claude-dev)                                                                           |
| Claude Code CLI               | [Install](https://github.com/anthropics/claude-code)                                                                                                            |
| GitHub Copilot                | [Install](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot) + [Chat](https://marketplace.visualstudio.com/items?itemName=GitHub.copilot-chat) |

---

## Troubleshooting

### General Issues

| Problem                      | Solution                                                    |
| ---------------------------- | ----------------------------------------------------------- |
| Rules not loading            | Check file exists in the correct location for your platform |
| File encoding issues         | Ensure files are UTF-8 encoded                              |
| Rules not applied in session | Start a new chat session after file changes                 |
| Rule details not loading     | Verify `.aidlc-rule-details/` exists with subdirectories    |

### Platform-Specific Issues

#### Kiro

- Use `/context show` in Kiro CLI to verify rules are loaded
- Check `.kiro/steering/` directory structure
- Note: Kiro uses `aws-aidlc-rule-details` (not `.aidlc-rule-details/`) under the `.kiro/` directory

#### Amazon Q Developer

- Check `.amazonq/rules/` directory structure
- Verify rules are listed in the Amazon Q Chat Rules panel
- Note: Amazon Q uses `aws-aidlc-rule-details` (not `.aidlc-rule-details/`) under the `.amazonq/` directory

#### Cursor

- For "Apply Intelligently", ensure a description is defined in frontmatter
- Check **Cursor Settings → Rules** to ensure the rule is enabled
- If rule is too large (>500 lines), split into multiple focused rules

#### Cline

- Check the Rules popover under the chat input field
- Toggle rule files on/off as needed using the popover UI

#### Claude Code

- Use `/config` command to view current configuration
- Ask "What instructions are currently active in this project?"

#### GitHub Copilot

- Select **Configure Chat** (gear icon) > **Chat Instructions** to verify instructions are loaded
- Type `/instructions` in the chat input to view active instruction files
- Check that `.github/copilot-instructions.md` exists in your workspace root

### File Path Issues on Windows

- Use forward slashes `/` in file paths within markdown files
- Windows paths with backslashes may not work correctly

---

## Version Control Recommendations

**Commit to repository:**

```gitignore
# These should be version controlled
CLAUDE.md
AGENTS.md
.amazonq/rules/
.amazonq/aws-aidlc-rule-details/
.kiro/steering/
.kiro/aws-aidlc-rule-details/
.cursor/rules/
.clinerules/
.github/copilot-instructions.md
.aidlc-rule-details/
```

**Commit to repository (orchestrator, if installed):**

```gitignore
# Orchestrator definitions are committed (source-of-truth)
.claude/agents/
.claude/commands/factory-*.md
.aidlc-orchestrator/contracts/
.aidlc-orchestrator/budgets/default.yaml
scripts/factory_*.py
```

**Optional - Add to `.gitignore` (if needed):**

```gitignore
# Local-only settings
.claude/settings.local.json

# Orchestrator runtime state (per-run; never commit)
.aidlc-orchestrator/runs/
.aidlc-orchestrator/knowledge/
```

The installer adds the runtime-state lines to your project's `.gitignore` automatically when you use `--with-orchestrator`.

---

## Generated aidlc-docs/ Reference

For the complete reference of all documentation artifacts generated by the AI-DLC workflow, see [docs/GENERATED_DOCS_REFERENCE.md](docs/GENERATED_DOCS_REFERENCE.md).

---

## Experimental: AI-Assisted Setup (Release Download)

> Instead of manually copying files, let your AI agent handle the setup. This is an experimental workflow — currently validated with Kiro, Claude code, Cursor, Antigravity.
>
> **Note:** This approach requires your agent to have shell access (e.g., Kiro, Claude Code, Cline). For agents without shell access, follow the [Common](#common) setup above.

Paste this prompt into your AI agent:

```text
Set up AI-DLC in this project by doing the following:

1. Download the latest AI-DLC release:
   - Use the GitHub API to find the latest release asset URL:
     curl -sL https://api.github.com/repos/awslabs/aidlc-workflows/releases/latest \
       | grep -o '"browser_download_url": *"[^"]*"' \
       | head -1 \
       | cut -d'"' -f4
   - Download the zip from that URL to /tmp/aidlc-rules.zip
   - Extract it: unzip -o /tmp/aidlc-rules.zip -d /tmp/aidlc-release
   - Copy the aidlc-rules/ folder from the extracted contents into .aidlc at the project root
   - Clean up: rm -rf /tmp/aidlc-rules.zip /tmp/aidlc-release

2. Create the appropriate rules/steering file for your IDE using the options below.
   Pick the one that matches the agent you are running in:

   - Kiro IDE or Kiro CLI     → create `.kiro/steering/ai-dlc.md`
   - Amazon Q Developer       → create `.amazonq/rules/ai-dlc.md`
   - Antigravity              → create `.agent/rules/ai-dlc.md`
   - Cursor                   → create `.cursor/rules/ai-dlc.mdc` with frontmatter:
                                  ---
                                  description: "AI-DLC workflow"
                                  alwaysApply: true
                                  ---
   - Cline                    → create `.clinerules/ai-dlc.md`
   - Claude Code              → create `CLAUDE.md`
   - GitHub Copilot           → create `.github/copilot-instructions.md`
   - Any other agent          → create `AGENTS.md`

3. The file content should be:
   When the user invokes AI-DLC, read and follow
   `.aidlc/aidlc-rules/aws-aidlc-rules/core-workflow.md` to start the workflow.

4. Add `.aidlc` to `.gitignore` unless I explicitly ask you not to.

5. Confirm what file you created and that `.aidlc` is gitignored.
```

The agent will download the latest release, create the correct config file for your IDE, and gitignore the `.aidlc` directory automatically.

**Updating AI-DLC** — Re-run the prompt above. The agent will download the latest release and overwrite the existing `.aidlc/` folder.

---

## Additional Resources

<!-- TODO: Replace this Amplify URL with a permanent/stable URL when available -->
| Resource                                            | Link                                                                                                                          |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| AI-DLC Method Definition Paper                      | [Paper](https://prod.d13rzhkk8cj2z0.amplifyapp.com/)                                                                          |
| AI-DLC Methodology Blog                             | [AWS Blog](https://aws.amazon.com/blogs/devops/ai-driven-development-life-cycle/)                                             |
| AI-DLC Open-source Launch Blog                      | [AWS Blog](https://aws.amazon.com/blogs/devops/open-sourcing-adaptive-workflows-for-ai-driven-development-life-cycle-ai-dlc/) |
| AI-DLC Example Walkthrough Blog                     | [AWS Blog](https://aws.amazon.com/blogs/devops/building-with-ai-dlc-using-amazon-q-developer/)                                |
| Amazon Q Developer Documentation                    | [Docs](https://docs.aws.amazon.com/amazonq/latest/qdeveloper-ug/q-in-IDE.html)                                                |
| Kiro CLI Documentation                              | [Docs](https://kiro.dev/docs/cli/steering/)                                                                                   |
| Cursor Rules Documentation                          | [Docs](https://cursor.com/docs/context/rules)                                                                                 |
| Claude Code Documentation                           | [GitHub](https://github.com/anthropics/claude-code)                                                                           |
| GitHub Copilot Documentation                        | [Docs](https://docs.github.com/en/copilot)                                                                                    |
| Working with AI-DLC (interaction patterns and tips) | [docs/WORKING-WITH-AIDLC.md](docs/WORKING-WITH-AIDLC.md)                                                                      |
| Contributing Guidelines                             | [CONTRIBUTING.md](CONTRIBUTING.md)                                                                                            |
| Code of Conduct                                     | [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)                                                                                      |

---

## Contributing

See [CONTRIBUTING](CONTRIBUTING.md#security-issue-notifications) for more information.

## Secure Executor & Allowlist (Advanced)

The manager delegates script execution to `scripts/executors/runner.py`. By default it
allows paths under `scripts/`, `bin/`, and `.venv/bin/`. To allow additional base paths,
edit `scripts/executors/allowlist.txt` (one path per line, relative to repo root) or
export `EXECUTOR_ALLOW_BASES` as a colon-separated list.

```text
# allowlist.txt — relative to repo root
runs
packages
packages/*/workspace
```

```bash
export EXECUTOR_ALLOW_BASES="custom_tools:tools/bin"
```

The manager writes audit records to `runs/<run>/`. Review these and
`aidlc-docs/` before approving any changes that involve script execution in your workspace.

To auto-enable extensions during evaluation:

```bash
python3 scripts/aidlc-evaluator/scripts/run_evaluation.py \
    --scenario sci-calc --auto-enable-extensions
```

This writes an opt-in state file at `runs/<run>/aidlc-docs/aidlc-state.yaml`.

## Roadmap

- [X] Implement skills-only architecture with mandatory enforcement
- [X] Persistent memory across sessions and users
- [X] Multi-agent orchestrator (Claude Code): 13 stage subagents + 3 cross-cutting agents, JSON Schema handoff contracts, parallel reviewer pool, file-glob locks + Python/TS AST drift detection, project-scoped engram knowledge store, Cost Governor (ok/downshift/skip/halt), kill-and-resume, legacy `aidlc-docs/` adoption
- [ ] Live e2e Phases 1-6 (continue beyond Phase 0 spec → plan → build → review → ship)
- [ ] Deep TS type-system drift (generics narrowing, conditional types) — needs `tsc --noEmit` or LSP integration
- [ ] Auto-merge conflict resolution (currently escalation-only)
- [ ] Mid-flight cancellation for budget-overshoot stages (blocked on Claude Code SDK Task() atomicity)
- [ ] Probably shared memory in real time
- [ ] Try to reduce tokens usage

## License

This library is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.
