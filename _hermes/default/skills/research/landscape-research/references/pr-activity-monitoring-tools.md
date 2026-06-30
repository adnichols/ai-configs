# PR activity monitoring tools research notes

Use for future landscape scans around GitHub PR watchers, review-state monitors, stale PR alerts, and agent-review readiness workflows.

## User need pattern

A useful PR monitor for Aaron should run continuously on one or more Macs or as a quiet service, watch a configured set of repositories, and alert only on condition transitions such as:

- PR is ready to merge because a configured agent/bot has given approval or equivalent thumbs-up.
- PR is waiting on agent feedback beyond a threshold.
- Agent feedback exists but has not been addressed after a threshold.
- New commits landed after agent feedback, so re-review is needed.
- PR is ready but stale because it has not been merged after approval/checks passed.

## Categories and fit

### GitHub native search/API/building blocks

Good foundation for custom watchers.

- GitHub issue/PR search supports review-state filters: `review:none`, `review:required`, `review:approved`, `review:changes_requested`, `reviewed-by:USERNAME`, `review-requested:USERNAME`, and `updated:`.
- `gh search prs` supports repository/owner filters, review filters, reviewed-by filters, `--updated`, `--json`, etc.
- REST pull request review API exposes review `state`, including `APPROVED`.
- Webhooks can subscribe to `pull_request_review`, `pull_request`, issue/comment/review-comment events for event-driven implementations.

For Aaron’s exact agent-review workflow, a small watcher using `gh`/GraphQL/REST plus a state DB is likely the best fit unless the desired condition can be expressed entirely as GitHub branch protection + auto-merge.

### GitHub auto-merge / branch protection

Best when the desired "agent thumbs-up" can be represented as a normal required GitHub approval/status check. GitHub auto-merge merges once required reviews and required status checks pass. It does not satisfy "notify me but let me manually merge" by itself.

### PullNotifier

Slack/Microsoft Teams product focused on GitHub PR notifications. Public site advertises team channel PR event routing, daily stale PR notifications, and personal notifications when a PR is approved.

Fit: strongest off-the-shelf SaaS for stale/approved PR alerts.
Gap: Slack/Teams-centric; may not express custom semantic "agent thumbs-up" unless mapped to normal GitHub approval/label/status.

### CatLight

Mac/Windows/Linux desktop action-center/tray app. Monitors CI/CD pipelines, PRs, and issues; shows status in tray; sends notifications; can watch outgoing PRs.

Fit: best local desktop app candidate for always-running Mac notifications.
Gap: likely less suitable for complex custom agent-specific state machines without validation.

### Octobox

GitHub notification inbox with an archived/done state; archived notifications return to inbox when threads change. Filters by repository, organisation, type, action, state, CI status, reason, labels, author/assignee, bots.

Fit: good for triage and not losing PR notification state.
Gap: inbox, not condition watcher.

### Gitify

Open-source menu-bar GitHub notifications app for macOS/Windows/Linux.

Fit: lightweight menu-bar notification surface.
Gap: too generic for PR readiness/staleness rules.

### Mergify / merge automation / Prow Tide

Mergify offers rule-based merge workflow automation with conditions over reviews/checks/labels. Prow Tide retests and merges PRs matching configured criteria; Prow has `lgtm` and `approve` plugins.

Fit: strong when the objective is policy-driven merge automation.
Gap: heavier than a personal cross-repo watcher; more CI governance than quiet alerting.

### GitHub Actions stale/review reminder actions

`actions/stale` marks issues/PRs with no recent interaction. Marketplace has smaller review reminder actions.

Fit: repo-local labeling/commenting/digest reminders.
Gap: not a cross-repo personal monitor unless paired with notifications; can become noisy.

### Probot / custom GitHub App

Probot is a framework for GitHub Apps. Useful for event-driven bots subscribing to PR/review/comment events.

Fit: best custom webhook app path.
Gap: requires hosting; laptops/Macs are less reliable for inbound webhook delivery unless tunneled or supported by a stable endpoint.

## Recommended custom watcher shape

Implement `pr-watch` as a launchd job, Hermes cron, or small daemon:

1. Poll configured repos every 5–15 minutes with `gh search prs` + REST/GraphQL detail fetch, or receive GitHub webhooks if hosted reliably.
2. Normalize PR state into records: repo, number, draft/open/mergeable/checks, latest commits, latest configured-agent review/comment, unresolved review threads if needed.
3. Evaluate condition transitions:
   - ready_to_merge
   - waiting_on_agent
   - feedback_unaddressed
   - needs_rereview
   - ready_but_stale
4. Store last emitted state per PR in SQLite/JSON to avoid repeated alerts.
5. Notify via the target channel: Discord/Telegram/macOS notification/Slack.

Key design rule: distinguish normal GitHub approval (`APPROVED`) from semantic thumbs-up in comments/reactions/labels. Prefer making agents emit a durable machine-readable signal such as a GitHub review approval, status check, or label.