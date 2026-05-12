# AIDLC Orchestrator — Contract Schemas Reference

> This document is a human-readable reference for all handoff contract schemas
> used by the AIDLC orchestrator. Each entry lists the schema file, the stage
> that produces it and the stage that consumes it, plus the key fields.

---

## Stage Contracts

| Schema | Produced by | Consumed by | Key fields |
|--------|-------------|-------------|------------|
| `workspace-scout.input.v1.json` | orchestrator | workspace-scout | `user_request`, `repo_root`, `skill_paths` |
| `workspace-scout.output.v1.json` | workspace-scout | orchestrator, requirements-analyst | `workspace_state`, `project_profile`, `next_phase` |
| `reverse-engineer.input.v1.json` | orchestrator | reverse-engineer | `workspace_state`, `user_request`, `artifact_paths` |
| `reverse-engineer.output.v1.json` | reverse-engineer | orchestrator, requirements-analyst | `legacy_artifacts`, `architecture_summary`, `gap_analysis` |
| `requirements-analyst.input.v1.json` | orchestrator | requirements-analyst | `user_request`, `predecessor_artifacts`, `depth` |
| `requirements-analyst.output.v1.json` | requirements-analyst | orchestrator, workflow-planner | `prd_artifact_path`, `requirements_md_path`, `complexity_tier` |
| `story-writer.input.v1.json` | orchestrator | story-writer | `requirements_path`, `format` |
| `story-writer.output.v1.json` | story-writer | orchestrator, workflow-planner | `stories_path`, `acceptance_criteria` |
| `workflow-planner.input.v1.json` | orchestrator | workflow-planner | `requirements_path`, `stories_path`, `depth` |
| `workflow-planner.output.v1.json` | workflow-planner | orchestrator, unit-decomposer | `workflow_path`, `design_units` |
| `unit-decomposer.input.v1.json` | orchestrator | unit-decomposer | `workflow_path`, `design_units` |
| `unit-decomposer.output.v1.json` | unit-decomposer | orchestrator | `unit_specs[]`, `unit_waves[]`, `parallel_plan` |
| `code-generator.input.v1.json` | orchestrator | code-generator | `user_request`, `unit_spec`, `locks_required`, `fast_path` |
| `code-generator.output.v1.json` | code-generator | orchestrator, build-test-agent | `files_changed[]`, `tests_added`, `commits_made` |
| `build-test-agent.input.v1.json` | orchestrator | build-test-agent | `unit_spec`, `test_strategy`, `code_paths` |
| `build-test-agent.output.v1.json` | build-test-agent | orchestrator | `test_results`, `coverage`, `build_success` |
| `reviewer.input.v1.json` | orchestrator | reviewer-* | `code_paths`, `review_focus`, `standards` |
| `reviewer.output.v1.json` | reviewer-* | orchestrator, merge-reviews | `findings[]`, `findings_summary`, `skill_compliance` |
| `ship-agent.input.v1.json` | orchestrator | ship-agent | `run_summary`, `artifacts[]`, `release_notes` |
| `ship-agent.output.v1.json` | ship-agent | orchestrator | `changelog_path`, `adrs[]`, `release_tag` |

---

## Supporting Contracts

| Schema | Purpose | Consumed by |
|--------|---------|-------------|
| `approval.input.v1.json` | Structured approval gate presentation | orchestrator (user-facing) |
| `shared/` | Common types reused across schemas | all contracts |

---

## Common fields across all output schemas

| Field | Type | Description |
|-------|------|-------------|
| `status` | enum | `complete`, `blocked`, `failed`, `needs_human` |
| `audit_entries[]` | string[] | Chronological audit trail from the agent |
| `emitted_knowledge[]` | object[] | Knowledge artifacts (patterns, ADRs, lessons) |
| `cost` | object | Token/wall-clock usage: `{tokens_in, tokens_out}` |
| `skill_compliance[]` | object[] | Per-skill PASS/FAIL/N/A with evidence |

---

## Status meanings

| Status | Meaning |
|--------|---------|
| `complete` | Stage finished successfully |
| `blocked` | Stage could not proceed (missing input, external dependency) |
| `failed` | Stage errored irrecoverably |
| `needs_human` | Stage produced output requiring human approval before proceeding |

---

## Schema version history

| Version | Date | Changes |
|---------|------|---------|
| 1 | 2026-05 | Initial contract set for all 13 stages |

---

## File locations

All schemas live in `.aidlc-orchestrator/contracts/`. The orchestrator validates
every input and output handoff against the corresponding schema using
`scripts/factory_validate.py` before spawning or consuming.
