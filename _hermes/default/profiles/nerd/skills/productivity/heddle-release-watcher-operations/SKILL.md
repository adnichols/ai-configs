---
name: heddle-release-watcher-operations
description: Operate and debug Aaron's Heddle main-merge release watcher cron job.
version: 1.0.0
author: Hermes Agent
platforms: [macos]
metadata:
  hermes:
    tags: [heddle, release, cron, github, macos]
---

# Heddle Release Watcher Operations

Use when Aaron asks whether Heddle main merge watching/release building is active, why a release did or did not publish, or to inspect watcher health.

## Ground truth

Incident references:
- `references/v0.1.16-timing-incident.md` for the timing/causality failure that led to the hardened watcher pattern.
- `references/cron-shim-auth-token-override.md` for the 2026-05-12 deleted-shim-target + inherited `GH_TOKEN`/`GITHUB_TOKEN` HTTPS 403 failure and verification recipe.

- Cron job: `725d93200439` / `heddle-main-release-watch`
- Dedicated checkout: `/Users/anichols/code/heddle-release`
- Watcher script: `/Users/anichols/code/heddle-release/scripts/release/main-release-watch.py`
- State file: `/Users/anichols/.hermes/profiles/nerd/state/heddle-release-watch.json`
- Logs: `/Users/anichols/.hermes/profiles/nerd/logs/heddle-release-watch/`
- Cron output: `/Users/anichols/.hermes/profiles/nerd/cron/output/725d93200439/`
- Current release flow is persisted-version based: merged `package.json` version determines tag; do not invent/increment versions in the watcher.
- No-op cron polls should be Discord-silent: the profile shim captures the watcher JSON and suppresses stdout when `status == "noop"`. In Hermes `no_agent=True`, empty stdout on exit 0 means no delivery; failures and real release/repair output must remain non-empty so they notify.

## Check health

1. List cron job:
   - `cronjob(action='list')`
2. Read state:
   - `/Users/anichols/.hermes/profiles/nerd/state/heddle-release-watch.json`
3. Verify GitHub release truth, not only local state:
   - `HOME=/Users/anichols zsh -lc 'gh release list --repo Nodaste-Lab/heddle --limit 10'`
   - `HOME=/Users/anichols zsh -lc 'gh release view vX.Y.Z --repo Nodaste-Lab/heddle --json tagName,name,publishedAt,assets,url,targetCommitish'`
4. Verify tag/commit mapping from checkout:
   - `git fetch origin main --tags`
   - `git rev-parse origin/main`
   - `git show origin/main:package.json | python3 -c 'import json,sys; print(json.load(sys.stdin).get("version"))'`
   - `git rev-list -n 1 vX.Y.Z`

## Important pitfall: cron auth/home context can differ from interactive terminal

The watcher cron now runs as `no_agent=True` with `deliver=origin` and profile script `heddle-release-discord-watch.py`. Hermes scheduler executes scripts with cwd under the profile scripts directory and may not preserve terminal auth context. The profile shim and repo wrapper must force:

- `HOME=/Users/anichols`
- `HEDDLE_RELEASE_AUTH_HOME=/Users/anichols`
- `GIT_CONFIG_GLOBAL=/Users/anichols/.gitconfig`
- `XDG_CONFIG_HOME=/Users/anichols/.config`

If cron output shows `Heddle release watcher failed: fetch` or JSON `stage: fetch` and the poll log says `remote: Write access to repository not granted` / HTTPS 403, inspect and repair these forced env vars first. Manual terminal success is not enough because terminal runs can inherit different Git credential context.

Additional scheduler-auth pitfall found 2026-05-12: Hermes cron/no_agent can inherit `GH_TOKEN` / `GITHUB_TOKEN` for a different GitHub identity. That token can override Aaron's working `gh` credential helper and cause private-repo HTTPS 403 even when `HOME`, `GIT_CONFIG_GLOBAL`, and `XDG_CONFIG_HOME` are correct. The profile shim should remove inherited `GH_TOKEN` and `GITHUB_TOKEN` before invoking the repo watcher so Aaron's `/Users/anichols/.config/gh` credential helper is used. Verify by reproducing with a poisoned env, for example `env -i PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" HOME=/Users/anichols HEDDLE_RELEASE_AUTH_HOME=/Users/anichols GIT_CONFIG_GLOBAL=/Users/anichols/.gitconfig XDG_CONFIG_HOME=/Users/anichols/.config USER=anichols GH_TOKEN=badtoken GITHUB_TOKEN=badtoken /Users/anichols/.hermes/profiles/nerd/scripts/heddle-release-discord-watch.py`; it should still return `status: noop` or a real watcher result, not fetch 403.

## Important pitfall: cron may be delayed/stale and local delivery hides outcomes

Historically the watcher used `deliver=local`. It may publish a GitHub release successfully without posting to the current Discord thread. Always verify GitHub release state with `gh release view/list` before concluding no release happened.

Do not claim the watcher worked on time just because a release now exists. Compare:
- PR `mergedAt` from `gh pr view <PR> --json mergedAt,mergeCommit`
- cron output timestamps under `cron/output/725d93200439/`
- git reflog/fetch timestamps in `/Users/anichols/code/heddle-release`
- release log timestamps and GitHub `publishedAt`

Known incident: PR #93 (`81e6c0d`, v0.1.16) merged at `2026-05-10T17:43:59Z` but the 17:42 MDT cron output still said NOOP and the actual release ran only after later interaction at `17:48:43Z` / published `17:50:00Z`. This shows the previous cron timing/reporting was not sufficient evidence of timely autonomous operation.

## Interpreting state

- `last_status: success` plus `last_release_tag` indicates the watcher believes release succeeded.
- Confirm with GitHub release API because state can be stale/wrong and because Aaron may be looking at GitHub UI state.
- If `last_seen_main_sha == origin/main`, subsequent polls will return `already_seen` and will not retry unless state is changed or a new commit appears.

## Log naming timezone

Release logs use `datetime.now()` local time in the script's process environment. On Aaron's machine this may appear as UTC-like names in practice; compare log contents timestamps rather than assuming filename local timezone.

## Manual release requests / tag collision pitfall

When Aaron asks to "cut a new release off main", first verify the persisted `package.json` version on `origin/main` and whether `v<version>` already exists:

```bash
HOME=/Users/anichols GIT_CONFIG_GLOBAL=/Users/anichols/.gitconfig XDG_CONFIG_HOME=/Users/anichols/.config zsh -lc 'git fetch origin main --tags'
git show origin/main:package.json | python3 -c 'import json,sys; print(json.load(sys.stdin).get("version"))'
git rev-list -n 1 vX.Y.Z
HOME=/Users/anichols zsh -lc 'gh release view vX.Y.Z --repo Nodaste-Lab/heddle --json tagName,targetCommitish,assets,url'
```

If the version tag already exists but points to a different commit than current `origin/main`, `scripts/release/local-release.sh` will refuse with `Tag already exists but does not point at HEAD`. That is an intentional guardrail. Do **not** invent a suffix tag/release (for example `v0.1.16-main-<sha>`) just to satisfy the request, especially not without the installer asset. Instead, create a proper persisted version bump PR against `main` when Aaron approves a patch release. A hyphen patch suffix such as `0.1.16-2` is currently accepted by Heddle's release validators and macOS build path; validate with `npm run version:build -- --json`, `npm run mac:web:build`, and `npm run mac:native:build`, then merge the bump and run the watcher. See `references/manual-patch-release-version-collision.md` for the full recovery playbook.

For repeat patch releases where Aaron gives an exact suffix (for example, `0.1.16-3`) and `origin/main` already carries the prior suffix, use the same persisted-version PR flow rather than direct-main pushes: `git switch main`, `git reset --hard origin/main` only after confirming the dedicated release checkout has no unrelated local edits, `git switch -C release/v<version>`, `bash scripts/release/set-version.sh <version>`, run the three validation commands above, commit/push/open PR, squash-merge, fast-forward/reset the dedicated checkout to `origin/main`, run `main-release-watch.py`, and verify both `git rev-list -n 1 v<version>` equals `origin/main` and the GitHub release has the `Heddle-v<version>-installer.pkg` asset. GitHub release JSON may report `targetCommitish: develop`; trust the git tag target for commit identity.

## Do not

- Do not create duplicate cron jobs.
- Do not increment versions manually.
- Do not push directly to main.
- Do not invent nonstandard Heddle release tags when the persisted version is already tagged elsewhere unless Aaron explicitly approves that exact tag shape.
- Do not report success solely from cron state or a GitHub release object; verify the expected installer asset exists.
