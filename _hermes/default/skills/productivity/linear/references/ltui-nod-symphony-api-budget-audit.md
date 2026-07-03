# ltui / nod-symphony Linear API budget audit

Use this reference when investigating recurring Linear API rate limits involving Aaron's `ltui` CLI and `nod-symphony` daemons.

## What to inspect

### `ltui`

Repository surfaces seen in the audit:

- `src/commands/issues.ts`
- `src/linear.ts`
- `src/cache.ts`
- `src/options.ts`

High-yield checks:

1. Confirm `issues list` is still using shaped raw GraphQL via `executeRawGraphQL`, with selection derived from `--fields`.
2. Confirm `issues list --search` does not perform per-result `client.issue(...)` lookups.
3. Check expensive defaults:
   - `issues view` may still probe attachments/comments by default unless `--no-attachment-probe` is used.
   - `issues attachments` may scan comments by default unless disabled/bounded.
4. Check mutation paths for lookup + mutation + full refetch patterns. Common examples: `issues create`, `issues update`, `issues comment`, `issues link`, relation commands.
5. Check metadata cache TTLs. Teams/projects/states/labels/users are stable enough to cache longer than a few minutes when rate limits are a problem.

Useful reduction ideas:

- Make agent-mode `issues view` cheap by default; require opt-in for attachment/comment probing.
- Make comment scanning in `issues attachments` explicit or bounded.
- Use raw GraphQL mutations that return exactly requested fields instead of SDK lookup + refetch.
- Increase stable metadata cache TTLs and keep an explicit cache-clear command.
- Persist rate-limit headers in a shared budget/backoff file so standalone CLI invocations can coordinate.

### `nod-symphony`

Repository surfaces seen in the audit:

- `lib/nod_symphony/linear_client.ex`
- `lib/nod_symphony/orchestrator.ex`
- `lib/nod_symphony/config.ex`
- `lib/nod_symphony/codex/dynamic_tool.ex`
- project `WORKFLOW.md` frontmatter
- local `~/.config/nod_symphony/config.yml`
- service logs under `~/.local/state/nod_symphony/<profile>/log/`

High-yield checks:

1. Compare configured profile count and intervals. Multiple daemons can share the same Linear API key and compete for one budget.
2. Estimate scheduled calls/hour:
   - candidate polling: `3600 / polling.interval_seconds`
   - issue summary refresh: `3600 / issue_summary_interval_seconds`
   - tracker state reconcile: roughly candidate polling rate while issues are running
   - review polling: `3600 / review_polling.interval_seconds` when enabled
3. Inspect `LinearClient` query shapes. In the observed version, candidate, project-summary, and by-id/state-reconcile paths selected full issue context including comments and attachments.
4. Inspect logs for which path is rate-limited: `candidate_fetch`, `issue_summary_refresh`, `tracker_state_reconcile`, `review_poll`, `linear_graphql`.
5. Inspect dashboard state (`/api/v1/state`) for running/review/open/completed counts. Large completed/project summaries can drive expensive full-project refreshes.

Useful reduction ideas:

- Raise polling intervals first when safe: e.g. 5s -> 15–30s; review 30s -> 60–120s; summary 5m -> 30–60m.
- Split candidate polling into cheap scan + per-dispatch hydration.
- Push `required_labels` into the Linear GraphQL filter instead of filtering labels locally after fetch.
- Add a true state-only query for running/review reconciliation (`id`, `identifier`, `state`, `updatedAt`) instead of using a full issue query.
- Add a summary-specific query for dashboard/open/pending-release summaries rather than reusing full project issue hydration.
- Parse Linear rate-limit headers/errors and use shared jittered backoff across daemon profiles.
- Restrict or guide raw `linear_graphql` dynamic-tool usage: prompt-provided issue context first; typed tools for common workpad/state/comment operations; broad GraphQL only as explicit fallback.

## Evidence pattern from the originating audit

The live system had two `nod_symphony` LaunchAgent profiles (`heddle`, `doct`) running with the same local Linear key. Both workflows used `polling.interval_ms: 5000`, review polling enabled, and default issue summary interval. Logs showed actual `RATELIMITED` failures from candidate fetch, issue summary refresh, and tracker state reconciliation. The rough scheduled baseline was already a large fraction of Linear's hourly request budget before agent `linear_graphql`, `ltui`, retries, and pagination.

Do not save these exact counts as durable truth; recompute from live config/logs each time. The durable lesson is the audit sequence and the query-shape/polling fixes above.
