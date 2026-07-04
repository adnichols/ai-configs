# Good Morning Doct publish/listener migration notes — 2026-07-03

Session-specific lessons from migrating `/gm` away from the legacy local `plan-review` service and into Doct-backed plan documents.

## Durable lessons

- Treat same-date GM dry-runs as stateful. The deterministic runner writes `runs/YYYY-MM-DD/manifest.json`, `publish.json`, and the generated HTML even in dry-run mode. Do not validate current-day publish behavior with `--dry-run` after a real publish unless you intend to overwrite run metadata and rerender the artifact.
- `doct-agent plans register` / `show` can put the canonical review URL and version under `plan.listenerInstructions`. Normalization must inspect nested `listenerInstructions.reviewUrl`, `workspaceId`, `documentId`, and `htmlVersionId` rather than assuming top-level fields.
- For `doct-agent plans update`, `--expected-version` is the Doct document integer version (`document.version`, e.g. `2`), not the UUID-like `htmlVersionId`. Passing the UUID fails validation. If needed, get the integer version from `doct-agent plans show --json` or the update response's `document.version`.
- A Doct listener based on `doct-agent plans agent next --wait --json` may exit non-zero with a timeout message when no routed comment arrives. That is idle/no-work, not an alert condition. Supervisors should stay quiet for that specific timeout and only log/report real errors.
- When replacing a legacy GM review URL with a Doct URL, update all three surfaces together: the generated HTML, the Doct document, and `~/.hermes/state/gm-plan-maintainer/active-plans.json`. Also complete or supersede the old Todoist review task so the next calendar/task collection does not reintroduce the legacy URL into the report.
- If a mistaken duplicate Doct GM document is created during publish/recovery, archive the duplicate through `doct-agent plans lifecycle --state archived` and leave the active registry entry pointing only at the canonical Doct document.

## Verification checklist

1. Unit tests: `python3 adn_vault/_agents/tests/test_gm_deterministic.py -v`.
2. Syntax check modified GM and listener scripts with `python3 -m py_compile ...`.
3. Verify no new GM workflow references to `html-plan-reviewer`, `plan-review agent`, `plan-review register`, or the local `mbp.braid-python.ts.net:4317` URL in active scripts.
4. Verify current Doct queue: `doct-agent plans queue list --base-url https://doct.nodaste.com --workspace-id <workspace-id> --document-id <document-id> --json`.
5. Verify listener process/pid only for active registry items with `routine: good_morning` and Doct `document_id`/`workspace_id`.
6. Export and verify Hermes config after installed skill/script/cron changes: `python3 scripts/hermes_config_sync.py export && python3 scripts/hermes_config_sync.py verify` from `~/code/ai-configs`.
