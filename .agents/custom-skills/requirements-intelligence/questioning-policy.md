# Questioning Policy — Routing Matrix

Authoritative routing rules that decide which elicitation techniques fire on a
given request. Referenced by `SKILL.md` Step 3.

## Inputs to the router

| Input | Source | Domain |
|---|---|---|
| `clarity` | Step 2 classification | Clear / Vague / Incomplete |
| `risk` | derived: reversibility × blast radius | low / medium / high |
| `novelty` | derived: greenfield → high, brownfield reuse → low | low / medium / high |
| `stakes` | derived from request: "prototype" / "internal" / "production" / "MVP" → maps to enum | prototype / internal / prod |
| `ambiguity_count` | `ambiguity-detection.md` lexicon scan | integer |

## Derivation rules

- `risk = high` when scope is `System-wide` or `Cross-system`, or when the request mentions migration / data backfill / breaking change.
- `risk = medium` when scope is `Multiple Components` or the request touches auth / billing / data integrity.
- `risk = low` for all other cases.
- `novelty = high` when greenfield OR brownfield + unfamiliar stack referenced in the request.
- `stakes = prod` when the request uses "production", "customers", "users will see", "launch", or a deployment target is specified.
- `stakes = prototype` when the request uses "PoC", "prototype", "demo", "experiment", "playing with".
- `stakes = internal` otherwise.

## Routing matrix

| Technique | Triggered when |
|---|---|
| `coverage-map` | always |
| `ambiguity-detection` | `ambiguity_count ≥ 3` |
| `socratic` | `clarity == Vague` |
| `assumption-mining` | `novelty == high` |
| `pre-mortem` | `stakes == prod` AND `risk ∈ {medium, high}` |

## Question budget

| | Min questions | Max questions | Drop priority (when above max) |
|---|---|---|---|
| All requests | 18 | 30 | Unknowns → Context → Limits → Risks → Expectations → Acceptance → Needs → Purpose |

Drop priority is read left-to-right: Unknowns drops first, Purpose never drops.

### Per-axis minimum questions

| Axis | Minimum |
|---|---|
| Purpose | 2 |
| Needs | 3 |
| Expectations | 2 |
| Acceptance | 2 |
| Limits | 2 |
| Context | 2 |
| Risks | 2 |
| Unknowns | 1 |

Below per-axis min → regain coverage by re-running the relevant technique (Socratic for Purpose, ambiguity-detection for Expectations, pre-mortem for Risks, etc.). Log the re-run: `[CoverageRecovery] <axis>: re-ran <technique> — <n> questions added`.

## Below-min recovery

If after dedupe the question count is below 18:

1. Re-run any triggered technique that produced zero candidates.
2. If still below min, set `status: needs_human` with `[RedFlag] requirements-intelligence: cannot reach minimum coverage at comprehensive depth — request likely too underspecified for MCQ format`.

## Special cases

### Trivial + Clear + Single File
- `request_classification.complexity == Trivial` AND `clarity == Clear` AND `scope == Single File`.
- The existing rule (`requirements-analyst.md` line 138) allows skipping the questions phase.
- Even when skipped, this skill MUST still emit `audit_entries[]` proving:
  - Rule file was read (`[SkillRead]`)
  - Signal scoring was done (`[SignalScore]`)
  - Coverage map was evaluated and all axes mapped to evidence from the request itself (`[CoverageMap]` with status `inferred-from-request`)
- The `[QuestionBudget]` entry shows `0/30 — Trivial+Clear+SingleFile skip path`.

### Brownfield with reverse-engineering present
- Skip Context axis questions that workspace-scout / reverse-engineer already answered.
- Quote the RE artifact as the answer: `[CoverageMap] Context: covered by reverse-engineering/technology-stack.md L<n>`.

### User typed answers in chat, not in the file
- Do NOT proceed.
- Re-prompt with the missing-answer template from `question-format-guide.md`.
- Log `[Compliance] question-format-guide.md: re-prompt sent because user answered in chat`.

## Plan-stage variant

When invoked by `workflow-planner`:

- Only `pre-mortem` triggers, regardless of signal scores.
- `pre-mortem` operates on the *plan artifact*, not the original user request.
- Question cap: 3.
- Output appended to plan approval — not a separate questions file.
