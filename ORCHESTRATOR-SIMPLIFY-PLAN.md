# Orchestrator Simplification Plan

Based on risk analysis of the current orchestrator architecture.

---

## Problem A: God Agent

The orchestrator prompt is 1077 lines. It does everything: FSM, budget, locks, knowledge, approvals, recovery. This makes it unpredictable — LLMs don't reliably follow 1000+ line instructions.

### Goal
Reduce orchestrator to a **finite-state machine** with minimal reasoning. Move intelligence to policies, contracts, and specialized agents.

### Steps

1. **Extract shared spawn cycle into a script** (not a prompt section)
   - Create `aidlc-scripts/factory_spawn.py` that encapsulates the full cycle:
     ```python
     factory_spawn.py run <run-id> <stage> [--depth minimal]
     ```
     It calls: emit→budget_check→knowledge_query→validate_input→Task()→validate_output→budget_deduct→knowledge_save→append_audit→update_state
   - The orchestrator just calls `factory_spawn.py` and reads the exit code.
   - Removes ~200 lines of prompt bloat.

2. **Strip all "here's what to do for each exit code" from the prompt**
   - Replace: "exit 0 → ok, exit 1 → downshift, exit 2 → skip, exit 3 → halt"
   - With: "run `factory_spawn.py` — it returns the decision."

3. **Move budget/locks/knowledge orchestration into their respective scripts**
   - `factory_budget.py` already owns the gate.
   - `factory_conflict.py` already owns locks.
   - `factory_knowledge.py` (new) wraps engram MCP calls.
   - Orchestrator calls scripts; scripts decide.

4. **Target orchestrator prompt size: ≤300 lines**

### Guardrails
- Orchestrator must still OWN `aidlc-state.md` and `audit.md` — these are source-of-truth files, not script-owned.
- The FSM must still be readable by a human debugging a run.

---

## Problem B: Semantic Validation Beyond Schema

JSON Schema validates structure ("required fields, types"). It cannot validate:
- "the plan is coherent"
- "the review has quality"
- "the architecture makes sense"

### Goal
Add layered validation: schema → semantic → review.

### Steps

1. **Schema validation** (done) — `factory_validate.py --strict`
2. **Semantic validation** — new `factory_semantic.py` script that checks:
   - Plan coherence: task tree covers all ACs from requirements
   - Review quality: each P0/P1 finding has a recommendation
   - Architecture consistency: interfaces referenced in tests exist in code
   Uses heuristics + regex, no LLM.
3. **Secondary reviewer** for controversial outputs
   - When a reviewer flags P0 issues, automatically route the output to a second reviewer of the same type.
   - If both agree on a P0, it's real. If they disagree, flag for human.
   - This is the "review of the review" pattern.

### Non-goal
- Never use the orchestrator to make quality judgments. That's what stage agents are for.

---

## Problem C: Parallel Codegen Reality

Parallel code generation is the hardest problem in this system. The current approach (locks + AST drift) is correct but conservative.

### Goal
Get 80% of the value (parallel review, knowledge retrieval, resumability) without paying the 80% cost (parallel codegen complexity).

### Steps

1. **Parallel review only by default** — embarrassingly parallel, no lock conflicts, no drift detection needed. Already works.
2. **Sequential codegen as default** — one unit at a time. Slower but predictable.
3. **Parallel codegen gated behind explicit opt-in**:
   - Only for LARGE tier (score > 8) or user passes `--parallel`
   - Only after the user has seen a sequential run complete successfully
   - Warning printed: "Parallel codegen is experimental. Conflicts may require manual resolution."
4. **Simplify parallel codegen internals**:
   - Remove AST drift detection (Phase 5.5) — it's the most complex feature and its value is unproven without real usage data
   - Keep file-glob locks — they're simple and catch real conflicts
   - Remove tree-sitter dependency (complex install, Python-only AST diff covers the common case)
5. **Add `--sequential` flag to `/factory-build`** as escape hatch if parallel fails mid-run.

### What we keep
- ✅ Parallel review (4 reviewers, embarrassingly parallel)
- ✅ Sequential codegen with locks (safe, simple)
- ✅ Kill/resume (works regardless of parallel or sequential)
- ✅ Budget enforcement (sequential is cheaper to estimate)
- ✅ Knowledge retrieval (independent of spawn strategy)

### What we defer
- ❌ AST symbol drift (complex, unproven value)
- ❌ Tree-sitter TS/JS parsing (heavy dependency, marginal gain)
- ❌ Auto-resolve conflicts (humans decide until patterns emerge)

---

## Implementation Order

```
Week 1:   Problem A — factory_spawn.py, strip orchestrator prompt
Week 2:   Problem B — factory_semantic.py, secondary reviewer routing
Week 3:   Problem C — gate parallel codegen, remove tree-sitter, add --sequential
Week 4:   Polish — test all three, update docs, remove dead prompt sections
```

## Success Criteria

1. Orchestrator.md ≤ 300 lines (from 1077)
2. `factory_spawn.py` handles one full spawn cycle with one CLI call
3. All existing 69 tests pass without prompt changes
4. Sequential codegen is the default; parallel requires explicit `--parallel`
5. Tree-sitter dependency removed (one fewer `pip install` failure)
