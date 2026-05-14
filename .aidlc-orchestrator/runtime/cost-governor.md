# Cost Governor

PRIORITY: P3

`factory_budget.py` owns `runs/<run-id>/budget.yaml`. Pre-flight gate
(exit 0=spawn, 1=minimal, 2=skip, 3=halt) + post-flight reconciliation (deduct).
Full semantics: [`spawn-loop.md`](spawn-loop.md) step 1/6.
- **Adaptive depth** at <30% remaining: requirements/workflow → `depth: minimal`;
  story/unit → skip.
- **Init**: `factory_budget.py init <run-id>` (idempotent).
- **Surface**: `factory_budget.py status <run-id>` in every completion message.
