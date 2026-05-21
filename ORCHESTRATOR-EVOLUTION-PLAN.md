# Orchestrator Evolution Plan

Two independent tracks: **model routing** (cost optimization) and **cross-tool portability** (beyond Claude Code).

---

## Track A: Per-Stage Model Routing

### Problem

Claude Code auto-switches between sonnet and opus based on perceived complexity.
The orchestrator has no control over which model runs each stage. Result:
- Simple stages (scout, build-test, ship) burn opus tokens unnecessarily
- Cost is unpredictable — a run that starts on sonnet can silently upgrade to opus
- No way to say "code-gen on opus, everything else on sonnet"

### Solution

Add a `model` field to each stage budget in `budgets/default.yaml`:

```yaml
per_stage:
  workspace-scout:
    tokens: 50_000
    wall_min: 5
    model: "sonnet"          # cheap — just scanning files
  requirements-analyst:
    tokens: 800_000
    wall_min: 30
    model: "opus"            # needs reasoning, worth the cost
  code-generator:
    tokens: 500_000
    wall_min: 30
    model: "opus"            # code quality matters
  build-test-agent:
    tokens: 300_000
    wall_min: 20
    model: "sonnet"          # running tests, not creating
  reviewer-*:
    tokens: 200_000
    wall_min: 15
    model: "sonnet"          # pattern matching, not creation
  ship-agent:
    tokens: 300_000
    wall_min: 20
    model: "sonnet"          # template filling, low risk
```

### Mechanism

The orchestrator reads `budgets/default.yaml.per_stage[<stage>].model` and
injects it into the input handoff as `model_override`. The sub-agent preamble
reads this and routes to the specified model.

For Claude Code `Task()` spawns, the model override can be passed as:
```
Task(subagent_type="code-generator", model_override="opus", prompt=...)
```

### Fallback

If no model is specified for a stage, use the tool's default (current behavior).
This ensures backward compatibility and works with tools that don't support
model overrides.

### Stages × Model matrix

| Stage | Model | Rationale |
|-------|-------|-----------|
| workspace-scout | sonnet | File scanning, classification. Cheap work. |
| reverse-engineer | sonnet | Documentation generation from existing code. |
| requirements-analyst | opus | Spec writing, ambiguity resolution. High reasoning need. |
| story-writer | sonnet | Template-based, structured output. |
| workflow-planner | opus | Complex planning, dependency resolution. |
| unit-decomposer | sonnet | Mechanical decomposition from plan. |
| code-generator | opus | Code quality directly impacts product. |
| build-test-agent | sonnet | Running tests, interpreting output, fixing failures. |
| reviewer-* | sonnet | Pattern matching against checklists. |
| ship-agent | sonnet | Release notes, ADRs, CHANGELOG. Template filling. |

### Cost impact estimate

Assuming typical run: 3 cheap stages + 3 expensive stages.
- Without routing: all 6 on opus — ~2M tokens at opus rate
- With routing: 3 cheap on sonnet, 3 expensive on opus — ~40% cost reduction

### Implementation

1. Add `model` field to `per_stage` in `budgets/default.yaml`
2. Create `aidlc-scripts/factory_model.py` that reads budget + stage → returns model name
3. Add `model_override` field to code-generator and requirements-analyst input contracts
4. Update orchestrator.md to inject model_override from budget config
5. Update sub-agent prompts to respect `model_override`

---

## Track B: Cross-Tool Portability

### Problem

The orchestrator only works on Claude Code because it uses `Task()` spawning,
which is Claude-specific. OpenCode, Codex CLI, Cursor, and Cline can't run it.

### Solution: Three-tier architecture

```
┌─────────────────────────────────────────────┐
│                 Orchestrator                 │  ← Same prompt, same FSM
│  (reads manifest, emits timeline, calls      │
│   factory_*.py scripts)                      │
├─────────────────────────────────────────────┤
│           Spawn Adapter Layer                │  ← One per tool
├──────────────────┬──────────────────────────┤
│  Claude Code     │  OpenCode / Codex / etc   │
│  Task() spawning │  Sequential agent calls   │
│  Parallel stages │  Single-agent loop        │
└──────────────────┴──────────────────────────┘
```

**Claude Code** — keeps parallel `Task()` spawning (current behavior).
All stages in a wave spawn simultaneously.

**Other tools** — sequential mode. Orchestrator runs stages one at a time:
1. Write input handoff
2. Present it to the agent as its next task
3. Agent executes and returns
4. Validate output
5. Repeat for next stage

### How sequential mode works

Instead of `Task(subagent_type="code-generator", prompt=...)`, the orchestrator
writes the input handoff to a known path and tells the agent:

```
Read .aidlc-orchestrator/current-task.yaml and execute the stage described
there. Follow the stage rules from aidlc-rules/aws-aidlc-rule-details/.
Write output to .aidlc-orchestrator/current-output.yaml.
```

This is how the legacy single-agent AIDLC workflow already works — it just
needs a structured handoff contract between orchestrator and agent.

### What changes per tool

| Tool | Current blocker | Fix |
|------|----------------|------|
| **Claude Code** | Nothing — works | Keep as-is |
| **OpenCode** | `Task()` API exists but untested | Add sequential fallback, test Task() |
| **Codex CLI** | No `Task()` API | Sequential mode only |
| **Cursor** | No `Task()` API | Sequential mode only; commands via `.cursor/rules/` |
| **Cline** | No `Task()` API | Sequential mode only; commands via `.clinerules/` |

### Detection

The orchestrator detects its runtime and picks the right adapter:

```python
# aidlc-scripts/factory_platform.py
def detect_tool() -> str:
    if "CLAUDE_CODE" in os.environ:
        return "claude"
    if "OPENCODE" in os.environ:
        return "opencode"
    # ... etc
    return "unknown"
```

Each tool's slash command file sets the tool name as an env var before calling
the orchestrator.

### Shared vs tool-specific files

| File | Scope |
|------|-------|
| `.claude/agents/orchestrator.md` | Claude-specific (uses Task()) |
| `.claude/agents/stage/*.md` | **Shared** — stage rules are tool-agnostic |
| `.claude/commands/factory-*.md` | Claude-specific (slash commands) |
| `.aidlc-orchestrator/contracts/*.json` | **Shared** — schemas are tool-agnostic |
| `aidlc-scripts/factory_*.py` | **Shared** — scripts are tool-agnostic |
| `aidlc-rules/aws-aidlc-rule-details/*` | **Shared** — rules are tool-agnostic |

The stage agent prompts and contract schemas are already tool-agnostic.
Only the orchestrator prompt and command files are Claude-specific.

### Minimal viable port

Phase 1: Make the orchestrator work sequentially on OpenCode.
Phase 2: Port to Codex CLI (sequential only).
Phase 3: Port to Cursor (sequential only, commands via rules).

### What sequential loses

| Feature | Parallel (Claude) | Sequential (all tools) |
|---------|-------------------|----------------------|
| Code-gen speed | N units at once | 1 unit at a time |
| Reviewer pool | 4 in parallel | 1 at a time |
| Cost | Higher peak tokens | Lower peak, same total |
| Lock conflicts | Possible (needs detection) | Impossible (serial) |
| Complexity | High | Low |

### What sequential keeps

- ✅ Budget enforcement
- ✅ Crash recovery (`/factory-resume`)
- ✅ Knowledge retrieval
- ✅ Contract validation
- ✅ Approval gates
- ✅ Audit trail
- ✅ Review quality (same 4 reviewers, just not parallel)

---

## Implementation Order

```
Sprint 1:  Model routing — budgets.yaml, factory_model.py, orchestrator.md update
Sprint 2:  Sequential adapter — OpenCode command files, env detection
Sprint 3:  Test OpenCode end-to-end, fix gaps
Sprint 4:  Port to Codex CLI + Cursor (sequential adapter re-used)
```

## Success Criteria

1. Model routing reduces token cost by ≥30% on multi-stage runs
2. OpenCode can run `/factory-spec" → "/factory-plan" → "/factory-build"` sequentially
3. All 69 existing tests still pass
4. No changes to stage agent prompts (they're already tool-agnostic)
5. `--model` flag on `/factory-spec` to force a specific model for the whole run
