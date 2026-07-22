# Pre-PR Autoreview: review-herdr

- Date: 2026-07-22
- Branch: `review-herdr`
- Base: `origin/main`
- Plan: none; standalone operator-authorized review-transport migration
- Review surface: visible interactive Codex and Claude sessions in adjacent Herdr tabs
- Base freshness: current HEAD `2492f3060fbf6124573f081fa9fee719f085e063` is behind local `origin/main` (`b4ad1581bb59a07d9731252f2ef12194400e5f8e`); rebase/final verification remains a later PR-preparation concern

## Scope baseline

Replace required Pi Codex and Claude review transport with operator-visible interactive Herdr tabs in the same workspace and exact worktree. Disable—but preserve for rollback—the former managed Pi review extensions. Update full and bounded installers, verification, workflow skills, prompts, doctrine, tests, and architecture documentation.

Locked controls:

- Codex: `gpt-5.6-terra`, reasoning `high`, sandbox `read-only`, approvals `never`.
- Claude: full model ID `claude-sonnet-5`, effort `xhigh`, permission mode `dontAsk`, tools only `Read,Grep,Glob`; no alias, Opus, Fable, fallback, Bash, or write tools.
- Coordinator owns nonce generation, complete worktree fingerprinting, transcript capture, artifact writing, triage, fixes, and rereview.
- Missing boundaries/verdicts, non-settled state, provider/tool-only failures, or stale fingerprints cannot produce a clean result.

## Initial review cycle

Reviewers ran from the unchanged launch fingerprint:

- HEAD: `2492f3060fbf6124573f081fa9fee719f085e063`
- status hash: `ac32fe342a70cd59c88550f143b3dd545c02b27041ca6bd9465e173e6a813fce`
- staged diff hash: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- unstaged diff hash before fixes: `fd9153922dcfc70793d86e3587c41bb1815b0fd274c40e9c0dc98193ebc224fc`
- untracked manifest hash before fixes: `947757bacdd205d227ccf7ad5e8ef3350d9121a96a81fe26938dc9facf62bfaf`

The large change was split into two slices per reviewer: installer/disablement and workflow/safety.

### Codex

- Agent/tab: `autoreview-codex-review-herdr`, `w8B:t7` / `w8B:p7`
- Confirmed model: `gpt-5.6-terra high`
- Installer slice verdict: `FINDINGS_TO_RESOLVE`
- Workflow slice verdict: `FINDINGS_TO_RESOLVE`

### Claude Code

- Agent/tab: `claude-ar-84684747`, `w8B:t8` / `w8B:p8`
- Process argv confirmed: `claude --model claude-sonnet-5 --effort xhigh --permission-mode dontAsk --tools Read,Grep,Glob`
- Visible footer confirmed Sonnet 5; no Opus or Fable model was used
- Installer slice verdict: `FINDINGS_TO_RESOLVE`
- Workflow slice verdict: `FINDINGS_TO_RESOLVE`

## Triage

| Finding | Reviewer | Severity | Scope | Decision | Evidence |
|---|---|---:|---|---|---|
| Disabled extension registrations were no longer recognized as managed after moving source trees | Codex, Claude | P2 | REGRESSION_FROM_THIS_DIFF | Fixed | Cleanup derived names only from `_pi/extensions`; disabled names were absent |
| Full verifier printed disabled extensions as extras but still passed | Claude | P2 | IN_PLAN | Fixed | Full comparison failed only on missing entries; explicit absence check existed only in scoped mode |
| Worktree fingerprint omitted content changes to already-untracked files | Codex, Claude | P1/P2 | IN_PLAN | Fixed | Porcelain status records an untracked path, not its content; normal diffs omit untracked content |
| Herdr gates retained a legacy launcher-metadata requirement | Codex | P2 | IN_PLAN | Fixed | Disabled launchers no longer produce that metadata |
| Codex pin could be overridden by a workflow without operator instruction | Codex, Claude | P2/P3 | IN_PLAN | Fixed | Wording permitted workflow-selected model/reasoning overrides |

## Fixes

1. `remove_repo_managed_pi_extension_registrations` now includes `DISABLED_PI_EXTENSIONS` in its managed-name set.
2. The bounded review-stack installer invokes the same registration cleanup after removing disabled directories.
3. Full and scoped verification now fail for either installed disabled extension directory or an explicit live-path registration in `settings.json`.
4. Transaction tests cover relative and absolute registration cleanup plus full/scoped verifier failures.
5. The worktree fingerprint now requires HEAD, all-untracked porcelain status hash, staged/unstaged diff hashes, and a deterministic untracked manifest containing bytewise-sorted path, type/mode, content hash, or symlink target.
6. Herdr gate validity now uses nonce boundaries, exact verdict, settled state, non-empty content, and the complete fingerprint; legacy launcher metadata is not required.
7. Required Codex reviews are pinned to Terra/high; any alternate pair requires explicit operator instruction and recording.

## Verification after fixes

- `python3 -m unittest scripts.tests.test_install_pi_transaction scripts.tests.test_pi_agent_roster` — 19 tests passed.
- `bash -n install.sh scripts/install-pi-transactionally.sh scripts/verify-pi-install.sh` — passed.
- `python3 -m json.tool skills/install-matrix.json` — passed.
- `git diff --check` — passed.
- `./install.sh --pi` — passed.
- `bash scripts/verify-pi-install.sh` — passed.
- Installed `herdr-reviewers` skill matches repository source.
- Live `~/.pi/agent/extensions/claude-review` and `codex-review` directories are absent.

## Targeted rereview

Targeted rereview used the post-fix fingerprint:

- HEAD: `2492f3060fbf6124573f081fa9fee719f085e063`
- status hash: `ac32fe342a70cd59c88550f143b3dd545c02b27041ca6bd9465e173e6a813fce`
- staged diff hash: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- unstaged diff hash: `242b71a26427364712b6be242a407c3ed66d575b60d599defa1e5a3755cbae37`
- untracked manifest hash: `affdb68707929266e9faababb6054adf2fa5e87da21de7eddb428844f56fc46f`

The fingerprint matched after both reviewers settled.

- Codex targeted rereview: `CLEAN_FOR_PR`
- Claude Code targeted rereview: `CLEAN_FOR_PR`
- New blockers introduced by fixes: none

This artifact was written after reviewer settlement as review evidence and was not part of the implementation fingerprint reviewed above.

## Final gate

- Selected review surface: `Codex/Claude Code` via Herdr
- Codex verdict: `CLEAN_FOR_PR`
- Claude Code verdict: `CLEAN_FOR_PR`
- Remaining blocking P1/P2 findings: none
- Remaining non-blocking follow-ups: none from this gate
- Final result: `CLEAN_FOR_PR`
