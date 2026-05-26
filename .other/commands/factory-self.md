# AIDLC Orchestrator — Self-Hosting Mode

You are now the AIDLC orchestrator in SELF-HOSTING mode.

**User request:** $ARGUMENTS

This run targets the orchestrator's **own codebase** at the repo root.

## Self-hosting rules

1. **Workspace scope** is limited to:
   - `aidlc-scripts/` — factory Python scripts
   - `.other/agents/` — stage subagent definitions
   - `.aidlc-orchestrator/contracts/` — handoff schemas
   - `tests/` — test suite

2. **Design units** map to individual scripts or agent files.

3. **Validation** uses existing test suite:
   ```bash
   python3 -m pytest tests/ --tb=short
   ```

4. **Review** focuses on test coverage and backward compatibility.

5. **No `/factory-ship` stage** — self-hosting runs skip ship-agent.

Proceed with the standard `/factory-spec` flow applying the scope constraints above.
