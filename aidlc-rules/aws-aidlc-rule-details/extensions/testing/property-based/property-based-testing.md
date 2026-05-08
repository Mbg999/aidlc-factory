# Property-Based Testing Rules

## Overview
Cross-cutting PBT constraints for AI-DLC phases. Ensures code with identifiable properties is tested using PBT, complementing (not replacing) example-based tests.

PBT defines invariants for all valid inputs → framework generates random inputs → searches for counterexamples → shrinks to minimal failing case.

**Enforcement**: Verify compliance before every stage completion message.

### Blocking Finding Behavior
1. List finding in completion message under "PBT Findings" with rule ID
2. Do NOT present "Continue to Next Stage" — only "Request Changes"
3. Log in `audit.md` with rule ID, description, stage context
4. N/A rules are not blocking

**Partial Enforcement**: If user selected Partial, only PBT-02, 03, 07, 08, 09 are blocking. Others advisory. Log mode in `aidlc-state.md`.

---

## PBT-01: Property Identification During Design
Every unit with business logic/transformations/algorithms MUST be analyzed for testable properties during Functional Design:

| Category | Test Shape | Example |
|----------|-----------|---------|
| Round-trip | `f_inv(f(x)) == x` | serialize/deserialize |
| Invariant | `measure(f(x)) == measure(x)` | sort preserves size+elements |
| Idempotence | `f(f(x)) == f(x)` | dedup, normalization |
| Commutativity | `f(g(x)) == g(f(x))` | arithmetic, set ops |
| Oracle | `f(x) == oracle(x)` | optimized vs brute-force |
| Induction | Property on `x` → property on `x+element` | recursive structures |
| Easy verification | `verify(solve(x)) == true` | solvers, optimizers |

Document in functional design artifacts; carry forward to code generation. Mark "No PBT properties" with rationale if none apply.

## PBT-02: Round-Trip Properties
Any operation with logical inverse MUST have PBT: serialize/deserialize, encode/decode, parse/format, encrypt/decrypt, write/read. Generate random valid inputs; assert `f_inv(f(x)) == x`. Document lossy transformations with acceptable tolerance.

## PBT-03: Invariant Properties
Functions with documented invariants MUST have PBT verifying them across generated inputs: size preservation, element preservation, ordering, range constraints, type preservation, business rule invariants. Generate wide range including boundaries.

## PBT-04: Idempotency Properties
Any idempotent operation MUST have PBT proving `f(f(x)) == f(x)`: PUT/DELETE endpoints, normalization, cache population, dedup, config application, at-least-once message processing.

## PBT-05: Oracle/Model-Based Testing
When reference implementation exists, PBT MUST compare system under test against oracle: optimized vs brute-force, refactored vs legacy, parallel vs sequential. Define equivalence precisely (exact, structural, or tolerance).

## PBT-06: Stateful Property Testing
Components managing mutable state MUST be evaluated for stateful PBT: caches, state machines, queues, session management, shopping carts. Define simplified model → generate random command sequences → execute against both → assert match after each command.

## PBT-07: Generator Quality
MUST use domain-specific generators (not raw primitives):
- Custom generators for domain objects respecting business constraints
- Constrained primitives (realistic ranges)
- Structured data (valid nested objects)
- Include boundary values (empty, zero, max, Unicode)
- Centralize reusable generators

## PBT-08: Shrinking and Reproducibility
- Shrinking enabled (don't disable framework's mechanism)
- Seed logged on failure for reproducibility
- CI: fixed seed or log random seed every run
- Flaky PBT failures investigated, not suppressed

## PBT-09: Framework Selection
Select framework supporting: custom generators, automatic shrinking, seed reproducibility, test runner integration.

| Language | Framework |
|----------|-----------|
| Python | Hypothesis |
| JS/TS | fast-check |
| Java | jqwik |
| Kotlin | Kotest Property Testing |
| Scala | ScalaCheck |
| Rust | proptest |
| Go | rapid |
| Haskell | QuickCheck |
| C#/.NET | FsCheck |
| Erlang/Elixir | PropEr / StreamData |

Document in tech stack; include as project dependency.

## PBT-10: Complementary Testing Strategy
PBT complements, doesn't replace, example-based tests:
- Critical business scenarios MUST have example-based tests even if PBT covers the property
- PBT MUST NOT be sole test for critical paths
- PBT-discovered failures → add as permanent regression example-based tests
- Clearly separate/label PBT vs example-based tests

---

## Enforcement Integration

| Stage | Rules | Focus |
|-------|-------|-------|
| Functional Design | PBT-01 | Property identification in design artifacts |
| NFR Requirements | PBT-09 | Framework in tech stack |
| Code Gen Planning | PBT-01–10 | PBT steps in generation plan |
| Code Gen Generation | PBT-02–08, 10 | PBT alongside example-based tests |
| Build and Test | PBT-08 | Seed logging and CI integration |

At each stage: evaluate → include "PBT Compliance" section (compliant/non-compliant/N/A) → block on non-compliance.
