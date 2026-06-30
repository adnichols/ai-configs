# Heddle release watcher auth and canonical-source incident

## Session-derived learning
A Hermes cron-supervised release watcher for `/Users/anichols/code/heddle-release` repeatedly failed at:

```text
git fetch origin main --tags
sign_and_send_pubkey: signing failed for ED25519 "/Users/anichols/.ssh/id_personal" from agent: communication with agent failed
git@github.com: Permission denied (publickey)
```

Interactive/API auth was healthy when run with Aaron's real HOME:

```bash
HOME=/Users/anichols zsh -lc 'gh auth status'
HOME=/Users/anichols zsh -lc 'git ls-remote https://github.com/Nodaste-Lab/heddle.git refs/heads/main'
```

The release checkout remote was SSH:

```text
git@github.com:Nodaste-Lab/heddle.git
```

So the root cause was not GitHub permission absence; it was cron/gateway noninteractive SSH signing through the macOS/1Password agent.

## Operational pattern
For release watchers and other cron jobs that need GitHub from Hermes:

1. Prefer HTTPS remotes backed by `gh` credentials or `GH_TOKEN`/`GITHUB_TOKEN`.
2. Verify with `HOME=/Users/anichols zsh -lc 'git ls-remote https://github.com/<owner>/<repo>.git refs/heads/main'`.
3. If using SSH anyway, test from the same noninteractive cron/gateway context, not only from a terminal.
4. Pause noisy cron jobs while fixing auth or watcher source:
   ```bash
   HOME=/Users/anichols HERMES_PROFILE=nerd hermes cron pause <job_id>
   ```
5. Resume only after a no-op poll succeeds.

## Canonical-source pitfall
The same incident showed the cron prompt was running a profile-local watcher:

```text
/Users/anichols/.hermes/profiles/nerd/scripts/heddle_release_watch.py
```

while the fixed implementation lived in the repo:

```text
/Users/anichols/code/heddle-release/scripts/release/main-release-watch.py
```

The profile copy was stale and still used `npm run release:local:minor -- --publish`, even after the repo watcher had been changed to `npm run release:local -- --publish` so it tags and publishes the version already merged to `main`. Future release watcher work must identify which script cron actually executes and keep that canonical path aligned with the reviewed repo-tracked implementation. If a profile-local compatibility path must remain, keep it as a thin wrapper that execs the repo-tracked watcher rather than duplicating release logic.
