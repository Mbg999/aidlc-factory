# OpenCode Orchestrator Port Plan

OpenCode supports the same `Task()` subagent spawning pattern as Claude Code.
The orchestrator **can** work on OpenCode with targeted adaptations.

---

## Current State

| Aspect | Claude Code | OpenCode |
|--------|------------|----------|
| Subagent spawning | ✅ `Task()` via `.claude/agents/` | ✅ `Task()` via `.opencode/agents/` |
| Agent files | 16 files in `.claude/agents/` | ❌ `.opencode/agents/` doesn't exist |
| Frontmatter format | `name:`, `model: sonnet` | `mode: subagent`, model is `provider:model-id` |
| Permission rules | None (implicit allow) | Required for tool access (`read`, `edit`, `bash`, `task`) |
| Commands | 12 in `.claude/commands/` | 12 in `.opencode/commands/` (copied but paths wrong) |
| Agent paths in commands | `@.claude/agents/orchestrator.md` | ❌ Still points to `.claude/` |
| `Task()` model parameter | `model="opus"` | ❌ Different model ID format |
| Installer adaptation | Copies as-is | ❌ No frontmatter/path conversion |

---

## Gaps to Close

### 1. Agent Frontmatter Format

All 16 agent files need their YAML frontmatter converted:

**Claude Code format (current):**
```yaml
---
name: code-generator
description: Per-unit construction agent
model: sonnet
---
```

**OpenCode format (required):**
```yaml
---
description: Per-unit construction agent
mode: subagent
model: anthropic/claude-sonnet-4-20250514
permission:
  read: allow
  edit: allow
  bash: allow
  glob: allow
  grep: allow
  list: allow
---
```

### 2. Mode assignment per agent

| Agent | Mode |
|-------|------|
| orchestrator | `mode: primary` |
| workspace-scout | `mode: subagent` |
| reverse-engineer | `mode: subagent` |
| requirements-analyst | `mode: subagent` |
| story-writer | `mode: subagent` |
| workflow-planner | `mode: subagent` |
| unit-decomposer | `mode: subagent` |
| code-generator | `mode: subagent` |
| build-test-agent | `mode: subagent` |
| reviewer-* | `mode: subagent` |
| ship-agent | `mode: subagent` |
| knowledge-agent | `mode: hidden` (reference doc, not a Task) |
| conflict-resolver | `mode: hidden` |
| cost-governor | `mode: hidden` |

### 3. Permission rules per role

**Orchestrator** (needs to spawn subagents + ask user):
```yaml
permission:
  read: allow
  edit: allow
  bash: allow
  glob: allow
  grep: allow
  list: allow
  task: allow
  question: allow
```

**Code-gen / Build / Ship** (needs to create files):
```yaml
permission:
  read: allow
  edit: allow
  bash: allow
  glob: allow
  grep: allow
  list: allow
```

**Reviewers** (read-only, no file writes):
```yaml
permission:
  read: allow
  edit: deny
  bash: allow
  glob: allow
  grep: allow
  list: allow
```

### 4. Model name mapping

```
Claude short name  →  OpenCode provider:model-id
─────────────────────────────────────────────────
haiku              →  anthropic/claude-haiku-4-20250514
sonnet             →  anthropic/claude-sonnet-4-20250514
opus               →  anthropic/claude-opus-4-20250514
```

But model IDs should be configurable — different OpenCode setups use different providers (Zen, BYOK, etc.). The safest approach: use a **model alias** system that maps short names to whatever the user's provider uses.

### 5. Command file path references

Every command file references `@.claude/agents/orchestrator.md`. For OpenCode:
```
@.claude/agents/orchestrator.md  →  @.opencode/agents/orchestrator.md
```

Additionally, all `Task()` calls in the orchestrator and commands use `subagent_type` which is Claude-specific:
```
Task(subagent_type="code-generator", ...)
```
In OpenCode, the agent name comes from the **filename**, not `name:` frontmatter. The `subagent_type` parameter maps to the filename stem.

### 6. Installer adaptation

The installer (`install_aidlc.py`) must convert agent files when `--tool opencode` is used:

- Remove `name:` frontmatter field
- Convert `model:` short names to provider-qualified
- Add `mode:` field (subagent/primary/hidden)
- Add `permission:` block
- Convert `@.claude/` paths to `@.opencode/` in command files

---

## Implementation Plan

### Phase 1: Agent files (2h)

Create `.opencode/agents/` with all 16 adapted agent files:

1. Copy `.claude/agents/` → `.opencode/agents/`
2. Convert frontmatter for every file:
   - Remove `name:` field
   - Add `mode:` (primary/subagent/hidden)
   - Convert model short names
   - Add permission block per role
3. Test: OpenCode can `@mention` any stage agent

### Phase 2: Command files (1h)

Adapt the 12 `.opencode/commands/` files:

1. Replace `@.claude/agents/` → `@.opencode/agents/`
2. Update `Task()` syntax references to be tool-agnostic:
   - "Spawn the subagent" instead of hardcoding `Task(subagent_type=...)`
3. Remove Claude-specific model references in Task calls
   - Model routing should go through `factory_model.py`, not inline in prompts

### Phase 3: Orchestrator prompt (2h)

Adapt `.opencode/agents/orchestrator.md`:

1. Update all file paths from `.claude/` to `.opencode/`
2. Replace hardcoded `Task(subagent_type="...", ...)` patterns with:
   - "Spawn the `<agent>` subagent" pattern that works on both tools
3. Keep the shared primitives (steps 0-13) — they're tool-agnostic
4. Keep the model resolution step (step 2.5) — it uses `factory_model.py` script

### Phase 4: Installer adaptation (3h)

Update `install_aidlc.py` to convert files when `--tool opencode`:

1. Add `_convert_frontmatter()` function that transforms Claude → OpenCode format
2. Add `_convert_paths()` function that replaces `.claude/` → `.opencode/` in content
3. Apply both conversions to all copied agent and command files
4. Add OpenCode model aliases to the conversion

### Phase 5: Testing (2h)

1. Manual test: `python scripts/install_aidlc.py --tool opencode --dest /tmp/test-opencode`
2. Verify files exist and frontmatter is correct
3. `@orchestrator` mention works in OpenCode
4. `/factory-spec` triggers workspace-scout subagent

---

## Key Design Decisions

### A. Source of truth vs generated files

Keep `.claude/agents/` as the **canonical source**. Generate `.opencode/agents/` via:

- **Development**: run a sync script (or the installer) to regenerate
- **Installation**: the installer converts at copy time

No manual editing of `.opencode/agents/` — they're always generated from `.claude/agents/`.

### B. Model aliases

Don't hardcode model IDs. Use a mapping file or env vars:

```bash
# .env or opencode config
AIDLC_MODEL_HAIKU="anthropic/claude-haiku-4-20250514"
AIDLC_MODEL_SONNET="anthropic/claude-sonnet-4-20250514"
AIDLC_MODEL_OPUS="anthropic/claude-opus-4-20250514"
```

The installer reads these and substitutes them into agent frontmatter.

### C. Permission templates

Define reusable permission templates in the installer:

```python
PERMISSION_TEMPLATES = {
    "orchestrator": {"read": "allow", "edit": "allow", "bash": "allow", ..., "task": "allow"},
    "builder": {"read": "allow", "edit": "allow", "bash": "allow", ...},
    "reviewer": {"read": "allow", "edit": "deny", "bash": "allow", ...},
    "hidden": {},  # no permission needed for reference docs
}
```

### D. Parallel spawning

OpenCode supports parallel `Task()` calls (same as Claude Code). The parallel
code-gen and parallel reviewer pool should work identically after the
agent files are adapted. No need for sequential fallback.

---

## Success Criteria

1. `python scripts/install_aidlc.py --tool opencode --dest /tmp/test` creates valid `.opencode/agents/` files
2. OpenCode can resolve `@orchestrator` and all stage agents from `.opencode/agents/`
3. `/factory-spec "add healthz"` runs workspace-scout as a subagent and returns results
4. `/factory-review` fans out all 4 reviewers in parallel
5. 77 existing tests still pass (no changes to non-OpenCode code paths)
6. Claude Code installation remains unaffected (`--tool claude` still works)
