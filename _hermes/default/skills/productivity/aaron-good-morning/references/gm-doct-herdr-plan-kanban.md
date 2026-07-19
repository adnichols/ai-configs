# Doct + herdr Plan Kanban for Good Morning

Use this reference when adding or maintaining a deterministic portfolio view of Aaron's active Doct plans in `/gm`.

## Purpose

Render eligible plans from the Personal and Shared Doct workspaces as Backlog, Planning, and In Progress columns, then correlate them with herdr agent sessions. The daily path must remain script-first: no LLM classification and no automatic plan/session mutations.

## Authoritative inputs

- Doct: `doct-agent plans board list --base-url https://doct.nodaste.com --workspace-id <id> --json`
- Routed review work: `doct-agent plans queue list --base-url https://doct.nodaste.com --workspace-id <id> --all --json`
- herdr: `herdr pane list` and `herdr workspace list`
- Optional remote herdr inventory: use a bounded structured JSON probe. If unavailable, report `remote inventory unavailable`; never convert that into `no matching work`.

## Eligibility

Include registered plan artifacts only when:

- lifecycle is active; and
- board column is `backlog`, `planning`, or `in_progress`.

Exclude:

- archived lifecycle;
- `done` and `not_visible` columns;
- plain text/non-plan documents without plan metadata;
- routine Good Morning report artifacts;
- other recurring review/report documents that are not execution plans.

Record excluded lifecycle/board contradictions in collector diagnostics rather than silently treating them as active.

## Card contract

Each card should show:

- canonical linked title;
- Personal or Shared workspace;
- project/Linear/repository context when present;
- last updated time;
- comment/action state;
- execution readiness;
- Doct `workingStatus` (`active`, `wip`, `stale`, or unset);
- matched herdr session state;
- deterministic assessment with evidence;
- named inconsistency flags and suggested human action.

## Comment-state semantics

Doct comment/person colors encode identity, not pending/resolved status. Do not reuse author colors as workflow semantics.

Use explicit semantic treatment:

- red: queued or claimed agent action;
- amber: unresolved conversation comment when an exact unresolved count exists, or explicitly uncertain comment state;
- green: no unresolved or queued work known.

Current board payloads expose lifetime `commentCount` and `queuedCommentCount`, but lifetime comments are not evidence that comments remain unresolved. If exact unresolved ordinary-comment counts are unavailable, render `resolution unknown` rather than guessing. Prefer a future Doct board/API field such as `unresolvedCommentCount` over scraping plan HTML or comment UI.

## Deterministic Doct ↔ herdr matching

Store a score and evidence list. Suggested evidence weights:

- 100: exact Doct document ID or canonical URL in session launch context/transcript;
- 80: exact Linear key in both plan and session/worktree evidence, with compatible repo/project;
- 70: exact non-generic branch/worktree match;
- 60: plan source path beneath pane cwd;
- 35: repo plus unique normalized slug; candidate only.

Suggested thresholds:

- 70+: matched;
- 40–69: possible match, review required;
- below 40: no match.

Conflicting exact keys fail closed. Generic title similarity alone must never establish active work.

## Work-state assessment

- `actively_working`: high-confidence match + herdr `working`, or a current claimed Doct agent action.
- `paused_resumable`: high-confidence match + herdr `idle` and existing worktree.
- `likely_complete`: completion evidence such as merged PR/branch or Done plan, optionally supported by herdr `done`. `done` alone is insufficient.
- `started_unclear`: matched worktree/session exists but completion evidence is absent.
- `no_execution_evidence`: no high-confidence session, active claim, or Doct WIP/active marker.
- `unknown`: required herdr source unavailable.

## Explainable inconsistency rules

- Backlog + matched working/idle session or `workingStatus=wip|active` → `work_started_in_backlog`.
- Planning + `executionReady=true` → `ready_plan_still_in_planning`.
- In Progress + no execution evidence beyond threshold → `possibly_abandoned`.
- In Progress + merged/completed evidence → `likely_complete_not_moved`.
- Queued/claimed action → `review_action_pending`.
- Update age beyond configurable per-column threshold → `forgotten_candidate`.
- Multiple high-confidence sessions → `parallel_or_duplicate_work`.

Recommended initial age thresholds: 7 days In Progress, 14 days Planning, 21 days Backlog. Keep them configurable and show the threshold/evidence in output.

## Integration shape

- Add a bounded collector phase such as `plan_kanban` to the deterministic GM runner.
- Checkpoint normalized output under the date run directory (for example `plan_kanban.json`).
- Render stable section ID `plan-kanban` before the existing Coding Sessions section.
- Include collector health per workspace/host.
- Keep V1 read-only: recommend board changes, but do not move/archive plans, resolve comments, or stop sessions.

## Verification

1. Fixture-test inclusion/exclusion, source failures, matching scores, ambiguity, and each inconsistency rule.
2. Reconcile live plan counts against both Doct boards and queues.
3. Reconcile session matches against herdr inventory.
4. Verify unavailable remote inventory remains distinct from no match.
5. Verify the rendered HTML at desktop and narrow widths.
6. Confirm the run made no Doct or herdr mutations.
