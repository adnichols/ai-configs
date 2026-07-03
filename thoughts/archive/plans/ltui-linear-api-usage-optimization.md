# ltui Linear API Usage Optimization

Status: execution-ready

## Goal

Reduce Linear API request usage for `ltui` issue grooming workflows, especially large candidate scans, by making high-volume reads query-shaped, surfacing live rate-limit state, and updating agent workflows so they select narrowly before fetching expensive issue context.

## Why this plan exists

Recent Linear grooming runs are hitting request limits. The repo has already documented rate-limit guidance, but the implementation still has request-amplifying paths:

- `ltui issues list` fetches a page, then eagerly resolves related SDK objects for every row.
- `ltui issues list --search` performs an additional `client.issue(node.id)` lookup per search result.
- `ltui issues view` always probes attachments/comments for image guidance.
- `_opencode/commands/cmd:workplanner.md` lists up to 100 issues and filters some state locally before fetching full comments/history per candidate.

The research artifact at `thoughts/research/2026-05-04-linear-api-usage-and-ltui-grooming.md` establishes that the highest-impact fix is to make list queries select only the fields the caller requested and to make grooming workflows avoid broad local filtering and broad detail loops.

## Authority and inputs

- User request: manifest a plan from the Linear API usage research.
- Research artifact: `thoughts/research/2026-05-04-linear-api-usage-and-ltui-grooming.md`.
- Repo guidance: `AGENTS.md`.
- Planning doctrine: `planning-workflow` and `dev-plan` skills.
- Product workflow doctrine: `product-principles` skill.
- Implementation surfaces:
  - `tools/ltui/src/commands/issues.ts`
  - `tools/ltui/src/linear.ts`
  - `tools/ltui/src/client.ts`
  - `tools/ltui/src/options.ts`
  - `tools/ltui/src/format.ts`
  - `tools/ltui/src/test-utils/mockLinearClient.ts`
  - `tools/ltui/src/__tests__/cli-regression.test.ts`
  - `tools/ltui/src/__tests__/cli-args.test.ts`
  - `tools/ltui/src/__tests__/output.test.ts`
  - `tools/ltui/SPEC.md`
  - `tools/ltui/README.md`
  - `skills/linear/SKILL.md`
  - `_opencode/commands/cmd:workplanner.md`
  - `_pi/prompts/cmd:feeling-lucky-pr*.md`
  - `_opencode/commands/cmd:feeling-lucky-pr*.md`

Product-intent docs are absent (`thoughts/specs/product_intent.md` and `thoughts/plans/AGENTS.md` were not present), so this plan aligns to validated repo guidance, ltui docs, and the user’s API-budget goal.

## Current implementation reality

- `tools/ltui/src/commands/issues.ts` builds issue list filters, calls `client.issues(...)` or `client.searchIssues(...)`, then maps nodes through `mapIssueToRow(...)`.
- `mapIssueToRow(...)` awaits `issue.team`, `issue.state`, `issue.project`, `issue.assignee`, and `issue.labels(...)` regardless of the caller’s selected fields.
- `tools/ltui/src/format.ts` applies `--fields` after rows are mapped, so fields are currently output-only.
- The installed Linear SDK exposes `client.client.rawRequest(...)`, and the raw response type includes `headers`, so ltui can use custom GraphQL without adding a new HTTP stack.
- `tools/ltui/src/linear.ts` already contains one raw GraphQL lookup pattern for teams, which is a useful local precedent.
- `tools/ltui/src/test-utils/mockLinearClient.ts` does not currently expose `client.client.rawRequest(...)` or request-count assertions, so tests need a small mock upgrade before the implementation can prove API-request reductions.
- `tools/ltui/SPEC.md`, `tools/ltui/README.md`, and `skills/linear/SKILL.md` already warn that `--fields` saves tokens but not necessarily API requests; those warnings should change once the implementation makes `--fields` an API-efficiency control.

## Progress

- [x] P1 - Add request-shape test support and rate-header plumbing contracts.
- [x] P2 - Make `issues list` query-shaped by requested fields and remove N+1 row mapping.
- [x] P3 - Add multi-state filtering and API-budget controls for issue detail reads.
- [x] P4 - Update grooming workflows and docs to use the cheaper API paths.
- [x] P5 - Run full ltui verification and final consistency review.

## Resume instructions (agent)

Read this document fully, then start with the first unchecked item in `## Progress`. Keep edits scoped to the files named in the active phase unless implementation evidence shows a directly required adjacent file. After completing a phase, immediately mark that phase’s progress item complete and verify the completed marker is present in this file before moving on. Use `/skill:adn-dev-wf thoughts/plans/ltui-linear-api-usage-optimization.md` for the repo’s canonical reviewed-plan workflow if starting from the top.

Ask the user only if implementation evidence contradicts a locked decision below or if Linear SDK behavior makes a query-shaped list impossible without changing dependencies.

## Product intent alignment

The default agent workflow should be cheap and safe by default:

- Agents should be able to request a compact list without accidentally spending one request per row.
- `--fields` should mean “only fetch what is needed” for high-volume list paths, not just “hide extra output after fetching it.”
- Broad grooming should begin from server-side filters and small pages, then fetch expensive context only for a bounded candidate set.
- Rate-limit pressure should be visible in command output when requested, with agent-legible guidance about reset/backoff state.
- Routine API-budget awareness should live in ltui and workflow prompts, not in hidden operator folklore.

Fail-closed boundaries:

- Do not infer or mutate many issues unless a command has an explicit target set, preview, and bounded execution contract.
- Do not silently skip requested fields; unknown fields must keep producing a validation error.
- Do not remove attachment discovery entirely from normal single-issue viewing; make the API-saving path explicit with flags.

## Locked decisions

1. The first implementation target is `issues list`; it is the dominant request multiplier and already called out in `tools/ltui/SPEC.md`.
2. Use `@linear/sdk`’s existing `client.client.rawRequest(...)` for custom GraphQL instead of introducing another GraphQL or HTTP dependency.
3. `--fields` must shape the GraphQL selection set for `issues list`.
4. Preserve existing output field names and JSON envelope shape for compatible fields.
5. Keep default `issues list` output compatible enough for existing tests and users, but avoid N+1 by selecting all default output relations in one GraphQL query.
6. Do not add a general-purpose `ltui graphql` command in this plan; custom GraphQL remains internal to typed ltui commands.
7. Add repeatable `--state` for OR state filtering rather than a new state-set syntax.
8. Add an opt-out flag for expensive default attachment probing on `issues view`; do not remove existing attachment guidance by default.
9. Bulk mutation primitives are out of scope for this plan. The required grooming improvement is bounded reads and workflow guidance, not a new bulk mutation surface.
10. Rate-limit visibility uses a global opt-in flag named `--show-rate-limit`. In this plan it is required for raw GraphQL-backed `issues list` paths, including search. For JSON list output, include a `meta.rateLimit` object with `requests.limit`, `requests.remaining`, `requests.reset`, `complexity.limit`, and `complexity.remaining` string-or-null values. For TSV, table, and detail output, preserve normal stdout and emit one stderr line beginning `RATE_LIMIT` with stable `requestsLimit=`, `requestsRemaining=`, `requestsReset=`, `complexityLimit=`, and `complexityRemaining=` key/value pairs. Rate-limit failures should keep the existing `ERROR: api_error rate_limited` shape and append agent-readable reset/backoff guidance when headers are available.

## Acceptance criteria

1. `ltui issues list --fields id,identifier,title` does not fetch team, state, project, assignee, labels, comments, history, or attachments.
2. Default `ltui issues list` output remains compatible in field names and envelope shape while avoiding per-row SDK relation requests.
3. `ltui issues list --search ...` avoids per-result `client.issue(node.id)` lookups.
4. Repeated `--state` filters are supported and compiled into a Linear OR state filter.
5. Unknown or unsupported fields still fail with an actionable validation error before misleading output is emitted.
6. ltui can expose live rate-limit headers for raw GraphQL-backed commands when the user asks for them.
7. `issues view` has an API-budget-saving path that avoids default attachment/comment probing unless requested.
8. Grooming prompt/docs use narrow server-side filters and bounded detail reads instead of broad list plus local filtering.
9. Tests prove API request-shape behavior, not only output token shape.
10. `bun run test` passes in `tools/ltui`.

## BDD scenarios

### B1 - Scalar-only issue list

Given an authenticated ltui profile and several Linear issues
When an agent runs `ltui --format json --fields id,identifier,title issues list --team ENG --limit 10`
Then ltui returns only `id`, `identifier`, and `title` rows
And the underlying query does not request or resolve team, state, project, assignee, labels, comments, history, or attachments.

### B2 - Default list compatibility without N+1

Given an agent runs `ltui issues list --team ENG`
When ltui produces default TSV output
Then the output still includes the documented default list columns
And relation fields needed for default output are fetched in one shaped GraphQL operation rather than through per-row lazy SDK calls.

### B3 - Search results stay bounded

Given an agent searches issues with `ltui --fields identifier,title issues list --search login --limit 10`
When Linear returns matching issue nodes
Then ltui maps the search result fields directly from the shaped query
And does not call `client.issue(...)` once per result.

### B4 - Multi-state grooming filter

Given a grooming command only needs `Backlog` and `Needs Feedback`
When it runs `ltui --fields identifier,title,state,updatedAt issues list --project <project> --label "Feeling Lucky" --state Backlog --state "Needs Feedback"`
Then Linear receives an OR state filter
And the command does not fetch unrelated state rows for local filtering.

### B5 - Rate-limit header visibility

Given Linear returns request and complexity rate-limit headers
When an agent runs a supported command with the rate-limit display flag
Then ltui emits those header values in a stable agent-readable form
And rate-limit errors include reset/backoff guidance when available.

### B5b - Rate-limit failure guidance

Given Linear rejects a raw GraphQL-backed list request because a request or complexity budget is exhausted
When ltui receives rate-limit headers with reset or remaining values
Then it exits non-zero with `ERROR: api_error rate_limited`
And the error output includes reset/backoff guidance using the captured header values.

### B6 - Cheap issue view path

Given an agent needs only title/state/url for a candidate issue
When it runs `ltui --format json --fields identifier,title,state,url issues view ENG-1 --no-attachment-probe`
Then ltui does not scan attachments or comments for image guidance
And the returned fields remain parseable JSON.

### B7 - Grooming workflow bounded detail fetch

Given the workplanner needs to groom many issues
When it selects candidates
Then it uses server-side state filters, smaller pages, and cheap fields first
And it fetches comments/history only for the next bounded candidate that needs full review.

## Phase-by-phase execution plan

## Phase 1: Add request-shape test support and rate-header plumbing contracts

### End State

The test harness can prove whether a command used raw GraphQL, which fields were selected, and whether relation resolvers were invoked. Rate-limit metadata has a small internal representation ready for command output in later phases.

### Tests first

Add failing tests that demonstrate the desired contract before implementation:

- A harness-level test proves relation resolver calls for team/state/project/assignee/labels are counted when a mock issue row resolves them.
- A harness-level test proves `client.issue(...)` calls are counted when the mock resolves an issue by id or key.
- A unit or regression test confirms mock raw GraphQL responses can carry rate-limit headers.
- A unit or regression test confirms the mock can surface a raw GraphQL rate-limit failure with captured headers.

### Expected files

- `tools/ltui/src/test-utils/mockLinearClient.ts`
- `tools/ltui/src/__tests__/cli-regression.test.ts`
- `tools/ltui/src/__tests__/output.test.ts`
- likely `tools/ltui/src/linear.ts`
- optional new helper file under `tools/ltui/src/`

### Work

- Extend the mock Linear client with a `client.rawRequest(...)` or `client.client.rawRequest(...)` surface matching the installed SDK shape.
- Add mock request accounting for high-risk calls:
  - raw GraphQL requests
  - `client.issue(...)`
  - per-issue relation access for team/state/project/assignee/labels
  - attachments/comments/history probes where useful
- Provide deterministic mock raw GraphQL responses for `issues` and `searchIssues` query shapes used by later phases.
- Add a small internal type/helper for rate-limit headers, including:
  - `x-ratelimit-requests-limit`
  - `x-ratelimit-requests-remaining`
  - `x-ratelimit-requests-reset`
  - `x-ratelimit-complexity-limit`
  - `x-ratelimit-complexity-remaining`
- Add a small formatter contract for `--show-rate-limit` metadata so Phase 2 can attach it to list output without inventing the output shape during implementation.
- Keep this phase focused on tests and plumbing; product behavior can still fail until Phase 2.

### Verify

```bash
cd tools/ltui && bun run test
```

Expected before implementation in this phase: newly added tests fail for missing raw request/accounting behavior. Expected after implementation: the harness-level tests pass, while later behavior tests may still be pending.

## Phase 2: Make `issues list` query-shaped by requested fields

### End State

`ltui issues list` uses explicit GraphQL selection sets derived from the requested output fields. Scalar-only field requests avoid relation fetching, default list output remains compatible, and search no longer performs one issue lookup per result.

### Tests first

Add or complete failing tests for these outcomes:

- `--fields id,identifier,title` produces the same rows as before but records no relation resolver calls.
- Default TSV output includes `id`, `key`, `identifier`, `title`, `state`, `priority`, `assignee`, `labels`, `project`, and `updatedAt`.
- `--fields labels` selects labels, while omitting `labels` does not select labels.
- `--search` with cheap fields uses one raw search/list query and no per-result `client.issue(...)` calls.
- Unknown fields still fail with `ERROR: validation_error Unknown field(s): ...`.
- `--show-rate-limit` on `issues list` emits the locked JSON `meta.rateLimit` shape and, for non-JSON formats, the locked stderr `RATE_LIMIT ...` line.
- A raw GraphQL rate-limit failure preserves `ERROR: api_error rate_limited` and includes reset/backoff guidance when headers are present.

### Expected files

- `tools/ltui/src/commands/issues.ts`
- `tools/ltui/src/linear.ts`
- `tools/ltui/src/cli.ts`
- `tools/ltui/src/options.ts`
- `tools/ltui/src/format.ts`
- `tools/ltui/src/__tests__/cli-regression.test.ts`
- `tools/ltui/src/__tests__/cli-args.test.ts`
- `tools/ltui/src/__tests__/output.test.ts`
- `tools/ltui/src/test-utils/mockLinearClient.ts`

### Work

- Introduce a field registry for issue list output fields. Each field should define:
  - output key/header
  - GraphQL selection requirements
  - row extraction from raw GraphQL data
- Build GraphQL selection sets from `globalOpts.fields`; if no fields are specified, select the existing default columns in one query.
- Preserve the existing JSON envelope shape from `renderPaginatedList`.
- Replace the current list data path with raw GraphQL for both normal issue list and search list.
- Keep the existing `buildIssueFilter(...)` behavior, but pass the filter variables to the shaped GraphQL query.
- Remove or bypass `mapIssueToRow(...)` for list commands once raw rows are available.
- Ensure selected relation fields are fetched as nested GraphQL fields, not as SDK lazy promises.
- Add global `--show-rate-limit` parsing and apply it to raw GraphQL-backed `issues list` output:
  - JSON: add `meta.rateLimit` with the locked shape from decision 10.
  - TSV/table/detail: preserve stdout and emit the locked `RATE_LIMIT ...` stderr line.
  - Rate-limit errors: preserve `ERROR: api_error rate_limited` while appending reset/backoff guidance when headers are present.
- Keep detail/create/update/comment/link/relationship commands on existing SDK paths unless directly required for compatibility.

### Verify

```bash
cd tools/ltui && bun run test
```

Manual spot checks with the mock client:

```bash
cd tools/ltui
tmp_config=$(mktemp -d)
export LTUI_CONFIG_DIR="$tmp_config"
export LINEAR_API_KEY=lin_api_test
export LTUI_TEST_CLIENT_MODULE="$PWD/dist/test-utils/mockLinearClient.js"
node bin/ltui --format json --fields id,identifier,title issues list --team ENG
node bin/ltui --format json --fields identifier,title issues list --search login --limit 5
node bin/ltui --format json --show-rate-limit --fields id,identifier,title issues list --team ENG
node bin/ltui issues list --team ENG --limit 5
rm -rf "$tmp_config"
```

## Phase 3: Add multi-state filtering and API-budget controls for issue detail reads

### End State

Grooming commands can express multiple wanted states server-side, and `issues view` has a cheap path that avoids default attachment/comment probing when agents only need selected issue fields.

### Tests first

Add failing tests for:

- Repeatable `--state` appears in `issues list --help`.
- Multiple states compile into an OR state filter and return only matching mock issues.
- `issues view --no-attachment-probe` omits attachment probe work while preserving selected JSON/detail output.
- `issues view` without `--no-attachment-probe` preserves existing attachment guidance behavior.

### Expected files

- `tools/ltui/src/commands/issues.ts`
- `tools/ltui/src/options.ts`
- `tools/ltui/src/__tests__/cli-args.test.ts`
- `tools/ltui/src/__tests__/cli-regression.test.ts`
- `tools/ltui/src/test-utils/mockLinearClient.ts`
- `tools/ltui/SPEC.md`

### Work

- Change `issues list --state` to be collectable/repeatable while preserving compatibility for a single state.
- Update `IssueListCommandOptions`, saved query merging, and `buildIssueFilter(...)` to support state arrays.
- Compile multiple states into a Linear OR filter. Preserve ID matching for UUID state refs.
- Add `--no-attachment-probe` to `issues view`.
- When attachment probing is disabled, do not call `probeIssueAssets(...)`; set attachment guidance fields to absent or omit them consistently for JSON/detail according to the existing output style.
- Make sure `--include-comments` and `--include-history` still explicitly fetch those sections even when attachment probing is disabled.
- Keep error messages actionable if a state filter is malformed or an unknown field is requested.

### Verify

```bash
cd tools/ltui && bun run test
```

Manual spot checks with the mock client:

```bash
cd tools/ltui
tmp_config=$(mktemp -d)
export LTUI_CONFIG_DIR="$tmp_config"
export LINEAR_API_KEY=lin_api_test
export LTUI_TEST_CLIENT_MODULE="$PWD/dist/test-utils/mockLinearClient.js"
node bin/ltui issues list --help | rg -- '--state'
node bin/ltui --format json --fields identifier,title,state issues list --state Todo --state "In Progress"
node bin/ltui --format json --fields identifier,title,state,url issues view ENG-1 --no-attachment-probe
rm -rf "$tmp_config"
```

## Phase 4: Update grooming workflows and docs to use the cheaper API paths

### End State

Repo guidance and grooming prompts teach agents to use server-side filters, cheap fields, bounded pages, and cheap issue views before expensive comment/history fetches. Warnings that `--fields` is output-only are replaced or narrowed to reflect the new implementation.

### Tests first

Use static checks to define the desired documentation and prompt contract before editing:

- Existing docs still mention live Linear rate headers.
- Docs and help mention `--show-rate-limit` and describe the JSON `meta.rateLimit` plus stderr `RATE_LIMIT` forms.
- Workplanner no longer relies on a broad 100-row query plus local state filtering.
- Agent guidance no longer says `--fields` is token-only for `issues list` after implementation.

### Expected files

- `tools/ltui/SPEC.md`
- `tools/ltui/README.md`
- `skills/linear/SKILL.md`
- `skills/linear/references/ltui-command-reference.md`
- `_opencode/commands/cmd:workplanner.md`
- likely `_pi/prompts/cmd:feeling-lucky-pr*.md`
- likely `_opencode/commands/cmd:feeling-lucky-pr*.md`
- optional `CHANGELOG.md`

### Work

- Update ltui docs to state that `issues list --fields` now shapes API requests for supported fields.
- Preserve guidance that other commands may still use SDK convenience paths unless explicitly optimized.
- Update examples to put global options before subcommands, matching existing repo guidance.
- Update the Linear skill to recommend cheap list fields for grooming:
  - `id,identifier,title,state,updatedAt`
  - include `project`, `assignee`, or `labels` only when needed for output.
- Update `_opencode/commands/cmd:workplanner.md` to:
  - use repeated `--state` filters for `Backlog` and `Needs Feedback`
  - reduce initial page size unless a larger limit is explicitly justified
  - avoid local state filtering as the primary selector
  - use `issues view --no-attachment-probe` for cheap metadata checks where full attachment guidance is not needed
  - fetch comments/history only for the next candidate being actively reviewed
- Update Feeling Lucky prompts that list ready issues so they use cheap fields and avoid unnecessary project/state fields in issue view unless needed.
- Add a changelog entry if this repo’s convention expects one for ltui behavior changes.

### Verify

```bash
rg -n -- '--fields|--show-rate-limit|rate-limit|RATE_LIMIT|x-ratelimit|--state|no-attachment-probe|issues list' tools/ltui/SPEC.md tools/ltui/README.md skills/linear/SKILL.md skills/linear/references/ltui-command-reference.md _opencode/commands/cmd:workplanner.md _pi/prompts _opencode/commands
```

```bash
rg -n "fields.*tokens|output only|not necessarily API|local state|allowed_states|--limit 100" tools/ltui/README.md skills/linear/SKILL.md _opencode/commands/cmd:workplanner.md
```

Review any matches from the second command and confirm they are either removed, intentionally scoped to non-optimized commands, or still accurate.

## Phase 5: Run full ltui verification and final consistency review

### End State

All tests pass, high-volume issue-list behavior is measurably request-shaped in tests, and docs/prompts consistently steer agents toward API-efficient grooming.

### Tests first

No new RED tests are expected in this phase. If a behavior or docs gap is found during verification, add the smallest regression test or static check that would have caught it, then fix the gap.

### Expected files

- Any files touched in Phases 1 through 4.
- This plan file, with completed checkboxes as phases finish.

### Work

- Run the full ltui test suite.
- Run targeted static searches for stale guidance.
- Inspect the final diff for consistency across CLI help, README, skill docs, SPEC, and grooming prompts.
- Confirm no unrelated dirty worktree changes were modified or reverted.
- Update this plan’s progress checkboxes and append to the decisions/deviations log only if execution diverged from locked decisions.

### Verify

```bash
cd tools/ltui && bun run test
```

```bash
git diff -- tools/ltui/src tools/ltui/README.md tools/ltui/SPEC.md skills/linear _opencode/commands/cmd:workplanner.md _pi/prompts _opencode/commands thoughts/plans/ltui-linear-api-usage-optimization.md
```

```bash
rg -n "fields.*tokens|output only|not necessarily API|broad polling|--limit 100|allowed_states" tools/ltui/README.md tools/ltui/SPEC.md skills/linear _opencode/commands/cmd:workplanner.md _pi/prompts _opencode/commands
```

## Verification strategy

- Unit and CLI regression tests prove output compatibility and request-shape behavior.
- Mock request accounting proves the API usage reduction directly instead of relying on token output as a proxy.
- CLI help tests prove new flags are discoverable.
- Static docs/prompt checks catch stale guidance that would cause agents to keep expensive grooming habits.
- Final `bun run test` in `tools/ltui` is the primary implementation gate.

## Delivery order

1. Add test/mock observability for request shape.
2. Implement query-shaped `issues list`.
3. Add multi-state filters and cheap detail-read controls.
4. Update grooming prompts and docs.
5. Run tests and consistency review.

## Non-goals

- Adding a generic GraphQL CLI.
- Adding a new dependency for GraphQL or HTTP.
- Implementing bulk mutation commands.
- Rewriting all ltui commands to raw GraphQL.
- Changing Linear authentication or API-key storage.
- Removing default attachment guidance from normal single-issue views.
- Solving Linear rate limits by rotating API keys; Linear request limits apply to the authenticated user and are shared across that user’s keys/tools.

## Test coverage matrix

| Acceptance / scenario | Planned evidence |
| --- | --- |
| AC1, B1 | CLI regression with mock request accounting for scalar-only `issues list` |
| AC2, B2 | Existing and updated output tests for default TSV/JSON list shape plus no per-row relation calls |
| AC3, B3 | Search regression proving no per-result `client.issue(...)` calls |
| AC4, B4 | CLI args and regression tests for repeatable `--state` and OR filter behavior |
| AC5 | Unknown-field regression against shaped field registry |
| AC6, B5, B5b | Rate-header helper/unit test, CLI regression for `--show-rate-limit` requested display, and raw GraphQL rate-limit failure guidance |
| AC7, B6 | `issues view --no-attachment-probe` regression with attachment/comment probe accounting |
| AC8, B7 | Static prompt/doc checks for server-side state filters and bounded detail fetch |
| AC9 | Mock accounting assertions in cli regression tests |
| AC10 | `cd tools/ltui && bun run test` |

## Decisions / Deviations log

- 2026-05-04: Plan locks `issues list` raw GraphQL as the primary implementation path because the installed SDK exposes `client.client.rawRequest(...)` with headers and the repo already uses a raw GraphQL team lookup pattern.
- 2026-05-04: Plan excludes bulk mutation primitives to keep scope focused on the observed grooming request pressure. Bulk work remains a future explicit feature with preview/backoff requirements.
- 2026-05-04: Integrated read-only Codex and Claude plan review feedback by locking the `--show-rate-limit` flag and output contract, adding rate-limit failure guidance coverage, fixing mock-backed manual verification commands, and restoring the cited research artifact in this worktree.
- 2026-05-04: Integrated second Codex plan review feedback by keeping Phase 1 limited to mock/accounting/header harness tests and moving end-to-end request-shape behavior tests into Phase 2.
