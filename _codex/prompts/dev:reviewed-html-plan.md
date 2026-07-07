---
description: Create/register an HTML plan and run PM plus Codex/applicable Claude Code plan reviews until execution-ready
argument-hint: '<plan description | slug | thoughts/plans/<slug>.html | issue key>'
---

# Reviewed HTML Plan

Invoke the installed `reviewed-html-plan` skill with exactly this argument:

```text
$ARGUMENTS
```

This wrapper is only the ergonomic `/dev:reviewed-html-plan` entry point. Follow the `reviewed-html-plan` skill so Doct registration, browser feedback, PM review, Codex review, applicable Claude Code review, plan updates, and readiness status all stay in the single source of truth. In Codex, run the Codex review leg as a subagent/native review task when available; run Claude Code through the canonical `claude-code-review` launcher only when the high-risk second-reviewer trigger or explicit override applies. Do not delegate the whole gate back to Pi.
