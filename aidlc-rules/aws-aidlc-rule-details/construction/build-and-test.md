# Build and Test

**Purpose**: Build units and run tests to validate code generation output.

## Prerequisites
- Code generation complete for all units
- Project ready for build & testing

## Pre-Step Verification (MANDATORY — BLOCKING)
Before proceeding to Step 1, verify:
1. **Code gen plans exist**: `aidlc-docs/construction/plans/{unit-name}-code-generation-plan.md` for EACH unit, with all checkboxes `[x]`
2. **Audit completeness**: `aidlc-docs/audit.md` has entries for every completed Code Generation unit (plan approval + completion + skill compliance)
3. **Execution plan updated**: `aidlc-docs/inception/plans/` execution plan has `[x]` on all code-gen tasks
4. **State file current**: `aidlc-state.md` `Current Stage` reflects the last completed Code Generation unit

**If ANY verification fails, fix it before proceeding. Do NOT start Build & Test with incomplete tracking.**

## Agent Skills (MANDATORY — per stage-conventions.md protocol)
**You MUST load and follow these skills. Skipping is a workflow violation.**

- `debugging-and-error-recovery/SKILL.md` — Scientific debugging for build/test failures. **Key process**: reproduce → localize → reduce → fix → guard. Stop-the-line rule.
- `browser-testing-with-devtools/SKILL.md` *(UI projects only)* — DevTools visual/network/console testing. **Key process**: verify with live runtime data, not assumptions.
- `test-driven-development/SKILL.md` — Test pyramid 80/15/5, mutation testing, coverage thresholds. **Key process**: verify tests actually catch bugs (mutation), not just pass.

**Inline fallback** (if SKILL.md files not installed):
1. Run build — if fails, use 5-step triage: reproduce, localize, reduce, fix, guard
2. Run tests — coverage must meet thresholds (80% unit, 15% integration, 5% e2e)
3. For UI: verify in browser with DevTools (DOM, console, network)
4. Every fix must include a regression test that would have caught the bug

---

## Steps

### Step 1: Analyze Testing Requirements
Determine strategy per project needs:
- **Unit tests**: Already generated during code generation
- **Integration tests**: Cross-unit/service interactions
- **Performance tests**: Load, stress, scalability (if NFRs require)
- **Contract tests**: API contracts between services (microservices)
- **Security tests**: Vulnerability scanning, auth testing
- **E2E tests**: Complete user workflows

### Step 2: Generate Build Instructions
Create `aidlc-docs/construction/build-and-test/build-instructions.md`:
- Prerequisites (tool, deps, env vars, system reqs)
- Build steps (install deps → configure env → build all → verify success)
- Troubleshooting (dependency errors, compilation errors)

### Step 3: Generate Unit Test Instructions
Create `aidlc-docs/construction/build-and-test/unit-test-instructions.md`:
- Run command, expected results, coverage target, fix procedure for failures

### Step 4: Generate Integration Test Instructions
Create `aidlc-docs/construction/build-and-test/integration-test-instructions.md`:
- Test scenarios (unit interactions), env setup, execution, cleanup

### Step 5: Generate Performance Test Instructions (If Applicable)
Create `aidlc-docs/construction/build-and-test/performance-test-instructions.md`:
- Requirements (response time, throughput, concurrency, error rate)
- Load tests, stress tests, analysis, optimization steps

### Step 6: Generate Additional Tests (As Needed)
Based on project requirements, generate:
- Contract tests (microservices)
- Security tests
- E2E tests

### Step 7: Generate Test Summary
Create `aidlc-docs/construction/build-and-test/build-and-test-summary.md`:
- Build status + artifacts
- Results per test category (unit, integration, performance, contract, security, e2e)
- Overall status: ready for Operations?

### Step 8: Update State
Mark Build and Test complete in `aidlc-state.md`.

### Step 9: Present Completion (Per stage-conventions.md protocol, emoji: 🔨)

**Pre-completion verification (BLOCKING)**:
- Confirm `aidlc-docs/construction/build-and-test/` directory contains at minimum: `build-instructions.md`, `build-and-test-summary.md`
- Confirm `aidlc-docs/audit.md` has a Build and Test entry with build status, test status, and skill compliance
- Confirm `aidlc-state.md` `Current Stage` is updated to `CONSTRUCTION - Build and Test`

Summary includes: build status, test results by category, generated instruction files.
Next stage options: Request Changes / Approve & Continue to Operations

### Step 10: Log in audit.md (MANDATORY)
Format:
```markdown
## [timestamp] CONSTRUCTION - Build and Test COMPLETE
- Build status: PASS|FAIL
- Test status: {results by category}
- Files generated: {list}
- [Skill] Executed: debugging-and-error-recovery (Build & Test) — PASS|FAIL
- [Skill] Executed: test-driven-development (Build & Test) — PASS|FAIL
- [Skill] Executed: browser-testing-with-devtools (Build & Test) — PASS|FAIL|N/A
```
**If this step is skipped, it is a workflow violation.**
