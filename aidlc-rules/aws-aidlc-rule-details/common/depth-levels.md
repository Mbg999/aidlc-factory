# Adaptive Depth

## Core Principle
When a stage executes, create all defined artifacts. "Depth" = detail level; adapts to problem complexity.

- **Stage selection** (binary): Workflow Planning decides EXECUTE or SKIP
- **Detail level** (adaptive): Model decides based on problem characteristics

## Factors Influencing Detail
1. Request clarity/completeness
2. Problem complexity
3. Scope (single file → system-wide)
4. Risk level (impact of errors)
5. Available context (greenfield vs brownfield)
6. User preferences (brevity vs thoroughness)

## Examples

| Stage | Simple (e.g., bug fix) | Complex (e.g., migration) |
|-------|----------------------|--------------------------|
| **Requirements** | Concise functional req; minimal sections | Full functional + NFR; traceability; acceptance criteria |
| **App Design** | Basic component description; key methods | Detailed responsibilities; method signatures; patterns |

## Guiding Principle
*"Create exactly the detail needed — no more, no less."*
Don't inflate simple problems. Don't shortchange complex ones.
