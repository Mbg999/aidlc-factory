# Coverage Map — Requirements Axes

The requirements analyst MUST cover all 8 axes via questions. Every axis is
required at all times. If an axis has zero questions covering it, generation
HALTS until a question is added.

## The 8 axes

### 1. Purpose
**Why is this being built?** What user/business outcome does it produce? What
problem does it solve that was not solved before?

- **Question pattern**: anchor against the status quo. "If this ships and works perfectly, what specifically changes for the user?"
- **Bad question**: "What is the goal of this project?" (too abstract, invites prose)
- **Good question**:
  ```
  ## Question
  If this ships and works perfectly, what specifically changes?

  A) Reduces a manual step the user does today
  B) Replaces an existing tool they are unhappy with
  C) Enables a new behavior they could not do before
  D) Internal tool / not user-facing
  E) Other (please describe after [Answer]: tag below)

  [Answer]:
  ```

### 2. Needs
**What does it functionally do?** Inputs, outputs, key behaviors, integrations.

- **Question pattern**: split must-have from nice-to-have. For each capability mentioned in the request, probe input source, output destination, trigger.
- **Example**:
  ```
  ## Question
  Which of these are must-haves vs nice-to-haves for the chat app?

  A) Real-time message delivery (must-have)
  B) Multi-room support (must-have)
  C) Message history / persistence (must-have)
  D) Typing indicators (nice-to-have)
  E) File uploads (nice-to-have)
  F) Other (please describe after [Answer]: tag below)

  [Answer]:
  ```

### 3. Limits
**What does it explicitly NOT do?** Out-of-scope items, hard NO-GO behaviors,
boundary constraints.

- **Question pattern**: enumerate adjacent features and ask which are out of scope.
- **Why this matters**: implicit scope creep destroys plans. Explicit limits stop it.
- **Example**:
  ```
  ## Question
  Which adjacent features are out of scope for this version?

  A) User authentication / login
  B) Direct messages (1:1 private chat)
  C) Voice / video calls
  D) Mobile app
  E) None of the above — all are in scope
  F) Other (please describe after [Answer]: tag below)

  [Answer]:
  ```

### 4. Expectations
**What does "done" feel like?** Performance bar, UX feel, quality threshold.
Every adjective from the ambiguity-detection sweep maps to a question here.

- **Question pattern**: convert every quality adjective in the request into a quantified target.
- **Example**:
  ```
  ## Question
  The request said "fast". What latency target counts as fast for message delivery?

  A) <100 ms — sub-perceptible
  B) <500 ms — feels instant
  C) <1 s — acceptable for chat
  D) Not perf-critical
  E) Other (please describe after [Answer]: tag below)

  [Answer]:
  ```

### 5. Context
**Where does this live?** Stack, dependencies, deployment target,
brownfield/greenfield, team conventions.

- **Question pattern**: surface constraints the existing system imposes.
- **Skip when**: workspace-scout already classified greenfield AND request explicitly states stack — quote the source instead of asking.

### 6. Risks
**What could go wrong?** Failure modes, edge cases, security, compliance, data loss.

- **Question pattern**: from `pre-mortem.md` — *"If this fails publicly in 90 days, what broke?"*
- **Example**: see `pre-mortem.md` for full templates.

### 7. Acceptance
**How do we know it works?** Measurable criteria, demo path, the one-thing test.

- **Question pattern**: "What's the one thing that, if true, means this is done?"
- **Example**:
  ```
  ## Question
  What's the demo that proves this works?

  A) Two browser tabs open, one sends, the other receives in real-time
  B) Above + reload preserves history
  C) Above + 100 concurrent connections do not degrade
  D) Above + recovers from network blips
  E) Other (please describe after [Answer]: tag below)

  [Answer]:
  ```

### 8. Unknowns
**What does the user explicitly not know yet?** Open decisions, blocking
research, items to revisit later.

- **Question pattern**: invite the user to flag unresolved items for later.
- **Example**:
  ```
  ## Question
  Which decisions are you NOT sure about and want flagged for later?

  A) Hosting / deployment target
  B) Whether to add auth later
  C) Persistence strategy if scale demands it
  D) Scaling beyond MVP
  E) Nothing is unknown — all decisions are made
  F) Other (please describe after [Answer]: tag below)

  [Answer]:
  ```

All 8 axes are required at all times. No depth gating — every axis must be covered.

## Enforcement

SKILL.md Step 4 emits a coverage table built from this taxonomy. SKILL.md Step 7
verification gate refuses any cell `status != covered`. This is non-negotiable.

### Per-axis minimum questions

Each axis has a MINIMUM question count (defined in `questioning-policy.md`).
The agent MUST generate enough questions to reach the per-axis minimum before proceeding. Log
re-runs with `[CoverageRecovery] <axis>: re-ran <technique> — <n> questions added`.

## Skipping axes (legitimate cases)

- **Context skipped** when workspace-scout output answers all context questions. Quote workspace-scout's output as the evidence (`[CoverageMap] Context: covered by workspace-scout L<n>`).
- **Limits skipped** when the request explicitly defines all boundaries. Quote the request as evidence (`[CoverageMap] Limits: covered by request <L<n>>`).
- **Risks skipped** for Trivial+Clear+Single File requests with `stakes != prod`. Quote the classification as evidence.
- **Unknowns skipped** when the user explicitly states no unknowns remain.
- Never skip Purpose, Needs, Expectations, or Acceptance. They are universal gates.
