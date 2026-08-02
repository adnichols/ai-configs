# Autoreview — Fix Untitled Plan titles in delivery workflow

**Reviewer:** active-harness reviewer (gpt-5.6-terra medium)
**Rounds:** 2

## Round 1 — CHANGES_REQUESTED
1. P2: docs claimed `plans update --title` (unsupported)
2. P2: PLAN_TITLE claimed Doct drift while only storing content-derived title

## Round 2 — fixes
1. Title contract: register-only `--title`; `plans update` body-only; retitle via update-metadata/rename
2. `delivery set --doct-title` with `doctTitleSource=doct` for real Doct drift checks; content uses `planContentTitle`

## Round 3 — residual docs heading fixed
Heading scoped to register; always-pass --title no longer applies to plans update.

**VERDICT:** CLEAN_FOR_PR (pending this final rereview confirmation)
