---
name: autobuild-pr-nudge-monitor
description: Reusable Hermes cron fixture for monitoring GitHub PRs linked to autobuild Linear issues, moving them to Rework on Codex feedback/conflicts, and merging after Codex approval.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [github, linear, cron, autobuild, codex, pull-requests]
---

# Autobuild PR nudge monitor

Use when Aaron asks to monitor GitHub PRs and nudge only PRs attached to `autobuild` Linear issues.

## Installed fixture

- Script: `~/.hermes/scripts/autobuild_pr_nudge_monitor.py`
- Primary live config: `~/.hermes/pr-nudge-monitors.json`
- Bundled fallback config for ai-configs installs: `~/.hermes/scripts/autobuild_pr_nudge_monitor.config.json`
- State: `~/.hermes/state/autobuild_pr_nudge_monitor.json`
- Log: `~/.hermes/logs/autobuild_pr_nudge_monitor.log`
- Docs: `~/.hermes/docs/autobuild-pr-nudge-monitor.md`
- Cron job in default profile: `Autobuild PR nudge monitor` (`8ae87f95f2e3` as of creation), every 10 minutes, script-only/no-agent, delivered to origin thread.

## Behavior

The monitor:
1. Lists GitHub open PRs for configured repos.
2. Extracts linked Linear issues from PR title, branch, explicit `Closes/Fixes/Resolves KEY-123` body text, and the first Linear linkback URL.
3. Loads Linear issues with the configured required label, default `autobuild`, in one batch via `ltui --format json --limit 250 issues list --label autobuild`.
4. Ignores PRs that are not linked to a required-label Linear issue.
5. Moves matching Linear issues to `Rework` and comments when there is current-head Codex feedback or a merge conflict.
6. If `merge_on_codex_ready` is true, merges/auto-merges matching PRs only after a real Codex thumbs-up/ready signal.
7. Prints only actionable output; empty stdout means no-op. Linear rate limits are logged and retried later quietly.

## Add another repo

Edit `~/.hermes/pr-nudge-monitors.json` and add a monitor object. If the monitor should travel with the ai-configs-managed Hermes bundle, mirror the same object into `~/.hermes/scripts/autobuild_pr_nudge_monitor.config.json`:

```json
{
  "name": "repo-name-autobuild-prs",
  "repo": "Org/repo",
  "repo_dir": "/absolute/path/to/local/repo-if-ltui-config-needed",
  "linear_team": "NOD",
  "linear_project": "optional-linear-project-id",
  "issue_key_prefix": "NOD",
  "required_label": "autobuild",
  "rework_state": "Rework",
  "merge_on_codex_ready": true,
  "enabled": true
}
```

`repo_dir` is optional for GitHub but useful when repo-local `ltui` auth/config is required.

## Verify

```bash
~/.hermes/scripts/autobuild_pr_nudge_monitor.py --list-config
DRY_RUN=1 ~/.hermes/scripts/autobuild_pr_nudge_monitor.py
hermes cron list
```

Do not use a broad regex over full Linear linkback markdown; it can include related issues. Use the fixture's extraction order instead.
