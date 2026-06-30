# Cron shim auth token override incident — 2026-05-12

## Symptom

Heddle release watcher cron job `725d93200439` reported `last_status: error`. Recent cron outputs showed two failures:

1. The profile shim called a deleted repo script:
   - Missing: `/Users/anichols/code/heddle-release/scripts/release/discord-release-watch.py`
   - Actual: `/Users/anichols/code/heddle-release/scripts/release/main-release-watch.py`

2. After pointing the shim at `main-release-watch.py`, cron/no_agent still failed during fetch:

```text
remote: Write access to repository not granted.
fatal: unable to access 'https://github.com/Nodaste-Lab/heddle.git/': The requested URL returned error: 403
```

Manual terminal runs with Aaron's normal environment succeeded, so terminal success alone did not reproduce the scheduler context.

## Root cause

Hermes cron/no_agent can inherit `GH_TOKEN` / `GITHUB_TOKEN` from a different identity. GitHub CLI and git credential helper may then use that inherited token ahead of Aaron's keychain-backed `gh` credentials. For a private Heddle repo, the wrong token produced HTTPS 403.

## Fix shape

In `/Users/anichols/.hermes/profiles/nerd/scripts/heddle-release-discord-watch.py`:

- Point `SCRIPT` at `/Users/anichols/code/heddle-release/scripts/release/main-release-watch.py`.
- Force operator auth/config env:
  - `HOME=/Users/anichols`
  - `HEDDLE_RELEASE_AUTH_HOME=/Users/anichols`
  - `GIT_CONFIG_GLOBAL=/Users/anichols/.gitconfig`
  - `XDG_CONFIG_HOME=/Users/anichols/.config`
  - PATH including `/opt/homebrew/bin`
- Remove inherited scheduler GitHub tokens before invoking the watcher:

```python
env.pop("GH_TOKEN", None)
env.pop("GITHUB_TOKEN", None)
```

Do **not** blindly set `GH_TOKEN=$(gh auth token)` in the shim: when inherited `GH_TOKEN` is bad, `gh auth token` can echo/use the bad inherited token rather than the configured keychain credential.

## Verification

1. Reproduce a poisoned scheduler-like env and ensure the shim still works:

```bash
env -i PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin" \
  HOME=/Users/anichols \
  HEDDLE_RELEASE_AUTH_HOME=/Users/anichols \
  GIT_CONFIG_GLOBAL=/Users/anichols/.gitconfig \
  XDG_CONFIG_HOME=/Users/anichols/.config \
  USER=anichols \
  GH_TOKEN=badtoken GITHUB_TOKEN=badtoken \
  /Users/anichols/.hermes/profiles/nerd/scripts/heddle-release-discord-watch.py
```

Expected: JSON `status: noop` / `already_seen` or a real watcher result; not fetch 403.

2. Trigger the cron job and inspect latest output:

```text
cronjob(action='run', job_id='725d93200439')
```

Then read latest file under:

```text
/Users/anichols/.hermes/profiles/nerd/cron/output/725d93200439/
```

Expected output includes a clean watcher JSON block and job `last_status: ok`.

3. Verify GitHub release truth independently:

```bash
HOME=/Users/anichols GIT_CONFIG_GLOBAL=/Users/anichols/.gitconfig XDG_CONFIG_HOME=/Users/anichols/.config \
  zsh -lc 'git rev-parse origin/main && git tag --points-at origin/main && gh release view vX.Y.Z --repo Nodaste-Lab/heddle --json tagName,publishedAt,assets,url'
```

Confirm expected installer asset exists, e.g. `Heddle-vX.Y.Z-installer.pkg`.
