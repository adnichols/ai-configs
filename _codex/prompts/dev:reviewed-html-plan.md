---
description: Create/register an HTML plan and run PM plus the configured reviewer-subagent plan review until execution-ready
argument-hint: '<plan description | slug | thoughts/plans/<slug>.html | issue key>'
---

# Reviewed HTML Plan

Invoke the installed `reviewed-html-plan` skill with exactly this argument:

```text
$ARGUMENTS
```

This wrapper is only the ergonomic `/dev:reviewed-html-plan` entry point. Follow the `reviewed-html-plan` skill so Doct registration, browser feedback, proportional planning evidence, PM review, active-harness reviewer-subagent review, plan updates, and readiness status all stay in the single source of truth. Do not launch a separate Codex or Claude Code review leg. Where this runtime lacks the configured reviewer subagent, stop with a review-infrastructure blocker instead of substituting an external reviewer.
