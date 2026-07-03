---
description: Run focused macOS tests and classify failures
argument-hint: "[scheme/target/filter/configuration hints]"
---

# Test macOS App

Run the smallest meaningful macOS test scope first, then explain failures by category.

Arguments: $ARGUMENTS

## Workflow

1. Detect whether the repo uses `xcodebuild test` or `swift test`.
2. Prefer focused execution when a target or filter is provided.
3. Classify failures as compile, assertion, crash, env/setup, or flake.
4. Summarize the top blocker and the narrowest sensible next step.

## Guardrails

- Avoid rerunning the full suite if a focused rerun is possible.
- Distinguish build failures from actual failing tests.
- Note when host-app setup or simulator-only assumptions leak into a macOS run.
