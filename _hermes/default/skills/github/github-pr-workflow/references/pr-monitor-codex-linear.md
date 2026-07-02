# PR Monitor Pattern: GitHub + Codex + Linear

Session-derived pattern for recurring PR monitors that move external tracker state and notify only on actionable readiness.

## Use case

Monitor open PRs, identify linked Linear issues, restrict to issues with an `autobuild` label, and keep each issue moving until the PR has a current Codex thumbs-up and no merge conflict.

## Data sources

- `gh pr list --repo OWNER/REPO --state open --json number,title,url,headRefName,body,headRefOid,mergeStateStatus,reviewDecision`
- `gh api repos/OWNER/REPO/pulls/NUMBER` for authoritative `mergeable` / `mergeable_state`
- `gh api repos/OWNER/REPO/pulls/NUMBER/reviews --paginate`
- `gh api repos/OWNER/REPO/pulls/NUMBER/comments --paginate`
- `gh api repos/OWNER/REPO/issues/NUMBER/comments --paginate`
- Linear via repo-local `ltui` when available

## Core algorithm

1. Extract Linear identifiers from PR title, branch, and body with `\b[A-Z][A-Z0-9]+-\d+\b`.
2. Load all relevant Linear issues in one batch, e.g. `ltui --format json --limit 250 issues list --team TEAM --label autobuild`, then key rows by identifier.
3. For each PR/issue pair:
   - If `mergeable_state == dirty` or `mergeable is False`, move Linear to `Rework` and comment that the merge conflict must be resolved.
   - If Codex has current-head review feedback, move Linear to `Rework` and comment with the Codex discussion URL.
   - If Codex has a distinct thumbs-up/approval and the PR is not merge-conflicted, emit one notification with the PR link.
4. Persist a state file keyed by event type + Linear issue + PR number + head SHA + source IDs, so the monitor is idempotent across cron ticks.
5. In script-only cron mode, print only user-facing notifications to stdout. Write operational logs to a log file. Empty stdout should mean silent/no-op.

## Codex ready-signal guardrails

Do not treat these boilerplate snippets as approval:

- `otherwise it will react with 👍`
- `Useful? React with 👍 / 👎`

Valid ready signals are explicit Codex approval/no-issues text, a direct Codex-authored thumbs-up comment, or a `+1` reaction authored by the Codex bot. Inline Codex review comments on the current head are feedback even if they include the boilerplate emoji text.

## Rate-limit behavior

For Linear-backed monitors, avoid per-PR `ltui issues list --search ...` loops. Batch the label/team lookup once per tick. If Linear returns `rate_limited`, cron scripts should log and exit `0` quietly so the user does not receive repeated failure alerts during the reset window. Do not mark the event as completed when the Linear update or comment is rate-limited; leave the idempotency key absent so the next cron tick retries after reset.

## Linear ID extraction pitfalls

When parsing PRs that include Linear linkback comments, do not scrape every `NOD-123`-shaped token from the full linkback markdown. The linkback body can include the issue description and related issue references, so a naive regex can move unrelated Linear issues to Rework.

Safer extraction order:
1. Extract the tracking issue from PR title and branch name.
2. Extract from PR body only for explicit closing phrases such as `Closes NOD-123`, `Fixes NOD-123`, or `Resolves NOD-123`.
3. For GitHub issue comments from `linear[bot]`, use only the first `linear.app/.../issue/NOD-123` URL in the linkback comment; later URLs may be related issues mentioned in the issue body.
4. For Heddle/Nodaste projects, treat `SCN-018`-style strings as product scenario identifiers, not Linear issue keys; constrain issue-key regexes to the actual team prefix when known, e.g. `\bNOD-\d+\b`.

## Cron/script operational pitfalls

- For `cronjob(no_agent=True, script=...)`, the script path must be relative to `~/.hermes/scripts/` (for example `heddle_pr_codex_linear_watch.py`), not an absolute path.
- Dry-run validation of an idempotent monitor should not write completion fingerprints to the real state file. Either skip state writes in dry-run or point `STATE_FILE` at a temporary path.
- If a first manual run partially succeeds before a rate limit, verify actual Linear state for at least one changed issue and rely on missing fingerprints to retry pending issues later.
