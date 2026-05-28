---
name: factory-self
description: Run the AIDLC orchestrator on its own codebase. Use to add features, fix bugs, or refactor the orchestrator scripts using the factory pipeline itself.
---

# factory-self — AIDLC Self-Hosting

Adopt the role from `.aidlc-orchestrator/agents/orchestrator.md` in SELF-HOSTING mode.

**User request:** the feature description provided by the user.

This run targets the orchestrator's **own codebase** at the repo root.
Treat `aidlc-scripts/`, `.aidlc-orchestrator/agents/`, and `tests/` as the workspace.

## Self-hosting rules

1. **Workspace scope** is limited to these directories:
   - `aidlc-scripts/` — factory Python scripts
   - `.aidlc-orchestrator/agents/` — stage subagent definitions
   - `.aidlc-orchestrator/contracts/` — handoff schemas
   - `.agents/skills/` — factory command skills
   - `tests/` — test suite

2. **Design units** map to individual scripts or agent files.

3. **Validation** uses existing test suite:
   ```
   python3 -m pytest tests/ --tb=short
   ```

4. **Review** focuses on test coverage and backward compatibility.

5. **The commit** includes the update to `docs/TROUBLESHOOTING.md` if the change
   introduces a new failure mode.

6. **No ship stage** — self-hosting runs skip ship-agent. The
   changelog entry is written directly.

Proceed with the standard flow (triage -> stages -> review -> commit)
applying the scope constraints above.
