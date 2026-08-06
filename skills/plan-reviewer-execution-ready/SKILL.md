---
name: plan-reviewer-execution-ready
description: Compatibility route for Doct's Request execution-ready review action. Use whenever an operator, Doct dispatch, or automation requests plan-reviewer-execution-ready; immediately continue the canonical reviewed-html-plan workflow at its execution-readiness gate.
---

# Execution-Ready Plan Review Compatibility Route

This skill preserves the routing name emitted by Doct. Immediately load and
follow the canonical `reviewed-html-plan` skill with the same plan, dispatch,
arguments, and claimed-work identifiers supplied to this invocation:

```text
/skill:reviewed-html-plan <same plan and event context, unchanged>
```

Treat this invocation as the explicit **Request execution-ready review** signal.
Do not wait for another readiness request. If this came from a listener-delivered
claim, process that existing claim; do not call `agent next` to claim it again.

Do not duplicate the readiness workflow here. The canonical skill owns plan
updates, delivery-ledger recording, PM review, independent planner review,
Doct acknowledgement and resolution, and the final readiness verdict.
