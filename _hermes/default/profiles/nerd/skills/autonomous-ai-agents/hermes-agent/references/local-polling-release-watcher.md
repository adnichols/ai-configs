# Local polling release watcher pattern

Session-derived pattern for replacing GitHub Actions with a local Hermes-supervised release runner.

## Use when
- User wants releases triggered by merges to `main`, but does not want GitHub Actions.
- A clean local checkout can build/publish artifacts.
- Polling is acceptable and Hermes should notify only on release/failure.

## Architecture
- Dedicated clean checkout, separate from the active development repo.
- Repo-owned deterministic release command does the actual build/tag/publish work from the version already present in the checked-out commit.
- External watcher script only detects new `origin/main` SHAs, enforces single-flight locking, calls release command, records JSON state, and writes full logs. It must not invent, increment, or pass a release version unless the repo's current release process explicitly says to.
- Hermes cron runs the watcher and interprets JSON output; it stays quiet on `noop` / `locked` and sends Discord/Slack/etc. only on `released` or `failed`.

## Guardrails
1. Seed current `origin/main` as baseline on first run to avoid retroactive publishing.
2. Skip release commits (for example subjects starting `Release v`) to avoid recursive release loops.
3. Use a lock file before any mutating release step.
4. Preflight auth and required packaging env before build/tag/publish; do not make the watcher bump versions unless the repo's release docs require that current behavior.
5. Keep state and logs outside the repo, under the Hermes profile if profile-scoped behavior matters.
6. Cron prompt should be self-contained and explicitly forbid recursive job creation or repository fixes.
7. Cron delivery can be `local`; the task itself may use `send_message` only for non-noop outcomes.
8. Prefer an HTTPS GitHub remote for cron/gateway release checkouts when `gh` auth works; noninteractive SSH can fail when the key is backed by 1Password/macOS agent signing.
9. Cron should execute the repo-tracked watcher script, not a profile-local staging copy, after the watcher has moved into source control; stale profile copies can keep old release semantics.
10. When changing watcher auth/source, pause the cron job, update one thing at a time, run a controlled poll, inspect the new poll log for `exit=0`, then resume.
11. For persisted-version release repos, derive the expected tag from the merged commit before running build/publish. If that tag already exists for a different commit, mark the SHA seen and emit `noop` rather than incrementing to a new version; if the tag points at the merged commit, continue the repo release path so a failed GitHub-release upload can be repaired. The PR/version files are the source of truth.

## Auth and script-source pitfalls
- Symptom: repeated `git fetch origin main --tags` failures with `sign_and_send_pubkey: signing failed ... from agent` and `Permission denied (publickey)`.
- Root cause pattern: the release checkout remote is `git@github.com:...`, but Hermes cron/gateway cannot use the interactive SSH/1Password signing agent. If `HOME=/Users/<user> zsh -lc 'gh auth status'` and `git ls-remote https://github.com/<owner>/<repo>.git refs/heads/main` succeed, switch the release checkout's origin to HTTPS.
- Also check the cron prompt/script path. If the watcher was copied from a Hermes profile into the repo, update cron to call the repo script and pass any required auth-home env, for example `HOME=/Users/<user> HEDDLE_RELEASE_AUTH_HOME=/Users/<user> .../scripts/release/main-release-watch.py`.
8. Prefer HTTPS remotes with `gh`/token credentials for cron-supervised GitHub fetch/push. SSH remotes that depend on 1Password/macOS ssh-agent signing may work interactively but fail from Hermes cron/gateway with `sign_and_send_pubkey: signing failed ... communication with agent failed` or `agent refused operation`.
9. Ensure the cron job runs the canonical repo-tracked watcher, or deliberately keep any profile-local compatibility wrapper as a thin exec wrapper around it. A stale profile copy can keep old release semantics (for example `release:local:minor`) even after the repo watcher has been fixed to release the already-merged version with `release:local -- --publish`.

## Example layout
```text
~/code/<repo>-release/                         # clean release checkout
~/.hermes/profiles/<profile>/scripts/<watch>.py
~/.hermes/profiles/<profile>/state/<watch>.json
~/.hermes/profiles/<profile>/logs/<watch>/
```

## Example watcher output contract
```json
{"status":"noop","reason":"already_seen"}
{"status":"locked"}
{"status":"released","release_tag":"v0.2.0","trigger_sha":"...","released_main_sha":"...","log":"..."}
{"status":"failed","stage":"preflight","reason":"missing_env","log":"..."}
```

## Hermes cron prompt shape
```text
Run <watcher> with terminal. It prints JSON.
- status noop/locked: do not send a message; final answer NOOP.
- status released: send concise release notification with tag, SHAs, log; final answer SENT_RELEASE_NOTIFICATION.
- status failed: send concise failure notification with stage/reason/cmd/log; final answer SENT_FAILURE_NOTIFICATION.
Do not fix code, change schedules, create additional cron jobs, or ask questions.
```
