# Pre-PR implementation review — git index-lock recovery

## Scope baseline

- **Task:** Stop agents from manually retrying forever when concurrent/timed-out Git leaves or hits `.git/index.lock`; provide safe retry/wait/dead-owner recovery and new-host bootstrap instructions.
- **Comparison:** `origin/main...HEAD` plus all current unstaged and untracked files. The branch has no committed diff, is one commit behind `origin/main`, and the candidate is entirely dirty/uncommitted.
- **Supported paths:** agent/skill commit and staging instructions; Pi doctrine; Hermes plan commit helper; `install.sh` full and bounded Pi review-stack installation; macOS worktree index paths; bare/new-host bootstrap from an ai-configs checkout.
- **Non-goals:** changing Git itself; automatically killing a live Git process; supporting a host with neither a wrapper install nor an ai-configs checkout; new commit/push behavior beyond making index-mutating commands lock-safe.
- **Current candidate files:**
  - Modified: `AGENTS.md`, `APPEND_SYSTEM.md`, `_claude/commands/cmd:commit-push.md`, `_codex/prompts/cmd:commit-push.md`, `_pi/prompts/cmd:commit-push.md`, `_hermes/default/scripts/pi_workflow_ctl.py`, `install.sh`
  - Untracked: `scripts/git-with-index-lock`, `scripts/ensure-git-with-index-lock`, `scripts/eval-git-index-lock-fix.sh`, `scripts/tests/test_git_with_index_lock.sh`, `scripts/tests/test_ensure_git_with_index_lock.sh`

## Integration-integrity record

| Contract / behavior | Source of truth | Producers / consumers | Evidence and reconciliation target |
|---|---|---|---|
| Wrapper executable name and recovery semantics | `scripts/git-with-index-lock` | `APPEND_SYSTEM.md`, commit prompts, Hermes plan commit helper, installed `~/.agents/scripts` / `~/.local/bin` | Search: `rg -n "git-with-index-lock|Git index lock" APPEND_SYSTEM.md AGENTS.md _claude _codex _pi _hermes install.sh`; every in-scope reference must use or bootstrap it and none may silently fall back to raw index-mutating Git. |
| New-host bootstrap executable and printed absolute path | `scripts/ensure-git-with-index-lock` | doctrine/prompt instructions, installer, Hermes resolver | Bootstrap must locate repo/env source, install both home locations, and allow callers to execute the printed path even when `~/.local/bin` is absent from PATH. |
| Installer locations | `install.sh` | normal shared-skill sync and bounded Pi review-stack install | Both paths install the wrapper and ensure helper under `~/.agents/scripts`, with `~/.local/bin` symlinks. |
| Worktree index lock path | `git rev-parse --path-format=absolute --git-path index.lock` in wrapper/eval | actual Git calls in linked worktrees | Tests must cover stale/unheld lock clear, short live-holder wait, long live-holder preservation, non-lock passthrough, and `git -C` path resolution. |

## Verification already run

- `bash scripts/tests/test_git_with_index_lock.sh` — PASS: stale lock recovery, live short-holder wait, long-holder safety, non-lock passthrough, raw-Git control.
- `bash scripts/tests/test_ensure_git_with_index_lock.sh` — PASS: empty-HOME bootstrap, install locations, installed repeat resolution, `AI_CONFIGS_ROOT` locate-only path.
- `bash scripts/eval-git-index-lock-fix.sh "$PWD"` — PASS 8/8 repeated runs: stale, short live holder, long live holder preservation, raw-Git control/recovery; no lock left behind.
- Same eval in Herdr repro tab `wB7:t2` / `wB7:p2` — PASS.
- `python3 -c "import ast; ast.parse(open('_hermes/default/scripts/pi_workflow_ctl.py').read())"` — PASS.

## Review cycle 1 — active-harness reviewer

- **Surface:** repository-owned Pi `reviewer` (`openai-codex/gpt-5.6-terra`, medium effort), live worktree.
- **Provenance:** cwd `/Users/anichols/.herdr/worktrees/ai-configs/fix-the-shit-git-index-lock`; HEAD `05677d8`; status showed every modified/untracked candidate file; `INSPECTED_TREE: live-worktree`.
- **Verdict:** `FINDINGS_TO_RESOLVE`.

| Finding | Severity / scope | Disposition | Evidence |
|---|---|---|---|
| No-`lsof` fallback could declare a non-`git` holder unheld and unlink it. | P1 / REGRESSION_FROM_THIS_DIFF | Fixed. `lock_is_held` now treats every existing lock as held when `lsof` is unavailable, so the wrapper waits until its budget expires and never clears the lock. | New targeted unit case runs with `PATH=/usr/bin:/bin` (no `/usr/sbin/lsof`) and proves failure-with-lock-preserved. |
| Probe-then-unlink TOCTOU for a newly created Git lock. | P1 / REGRESSION_FROM_THIS_DIFF | Rejected as a false positive for the supported Git-operation path. A Git index lock is created exclusively; while the stale path exists, a second Git reports `Unable to create ... index.lock: File exists` and cannot open/create the purported new lock. The only unlink is the stale pathname; a competing Git may create a new lock only after that unlink, and the wrapper performs no second unlink in that recovery attempt. | Existing raw-Git control case in the worktree eval proves the `File exists` behavior. The review did not identify a supported Git producer that opens an existing index.lock as owner. Arbitrary external programs opening a stale lock after inspection are outside supported Git-operation behavior. |
| Commit-push snippets told callers to set `AI_CONFIGS_ROOT` but did not check it and invoked an empty `ENSURE`. | P2 / REGRESSION_FROM_THIS_DIFF | Fixed in Pi, Codex, and Claude command prompts. They now resolve PATH, then `$AI_CONFIGS_ROOT/scripts/ensure-git-with-index-lock`, then current-top-level script, explicitly fail if unresolved, and execute the printed absolute wrapper path. | Prompt inventory and bootstrap tests below. |
| Graduation prompts still directly used raw `git add` and `git commit`. | P2 / REGRESSION_FROM_THIS_DIFF | Fixed in Pi, Claude, and Codex graduation prompts. They bootstrap `GIT_WL` once and use it for both documentation and cleanup commits. | `rg -n "^git (add|commit|rm|mv|restore|merge|rebase|cherry-pick|stash|apply)" _pi/prompts _claude/commands _codex/prompts` returned no active raw index-mutating instruction. |

## Fix verification after cycle 1

- `bash -n scripts/git-with-index-lock scripts/ensure-git-with-index-lock scripts/eval-git-index-lock-fix.sh scripts/tests/test_git_with_index_lock.sh scripts/tests/test_ensure_git_with_index_lock.sh` — PASS.
- `python3 -c "import ast; ast.parse(open('_hermes/default/scripts/pi_workflow_ctl.py').read())"` — PASS.
- `bash scripts/tests/test_git_with_index_lock.sh` — PASS (6/6), now including no-`lsof` fail-closed behavior.
- `bash scripts/tests/test_ensure_git_with_index_lock.sh` — PASS (4/4).
- Prompt instruction inventory search above — PASS (no remaining active raw index-mutating Git instruction).
- Real-worktree `bash scripts/eval-git-index-lock-fix.sh "$PWD"` — PASS 5/5 consecutive reruns; final lock clear.

## Review-cycle ledger

- Cycle 1: `FINDINGS_TO_RESOLVE`; four findings, three fixed and one rejected with Git lock-creation evidence.
## Review cycle 2 — targeted active-harness reviewer rereview

- **Surface:** repository-owned Pi `reviewer` (`openai-codex/gpt-5.6-terra`, medium effort), live worktree.
- **Provenance:** cwd `/Users/anichols/.herdr/worktrees/ai-configs/fix-the-shit-git-index-lock`; HEAD `05677d8`; status showed all modified/untracked candidate files including the three graduation prompt updates; `INSPECTED_TREE: live-worktree`.
- **Verdict:** `APPROVED` (equivalent to PASS). No unresolved in-scope P1/P2 findings.
- **Reviewer coverage:** no-`lsof` fail-closed behavior; Git-only stale-clear TOCTOU disposition; Pi/Claude/Codex `AI_CONFIGS_ROOT` bootstrap; graduation prompt wrapper adoption; active instruction inventory; installer/doctrine/Hermes paths.
- **Not examined by reviewer:** runtime execution of verification, arbitrary non-Git processes manipulating index.lock, and unrelated workflows.

## Final verification and runtime installation

- Rereview verification from the coordinator remains PASS: bash syntax, Python AST parse, wrapper unit 6/6, ensure unit 4/4, prompt inventory no-active-raw-Git search, and five consecutive real-worktree eval passes with no lock left behind.
- Installed reviewed scripts to `~/.agents/scripts/git-with-index-lock` and `~/.agents/scripts/ensure-git-with-index-lock`; refreshed `~/.local/bin` links.
- Synchronized the reviewed Git-index-lock doctrine section into `~/.pi/agent/APPEND_SYSTEM.md`.
- Production-path smoke: `GIT_WL="$(ensure-git-with-index-lock)"`; executable resolved to `~/.local/bin/git-with-index-lock`; `"$GIT_WL" status --short --branch` succeeded; final `index.lock` absent.

## Final gate result

**PASS.** Active-harness reviewer consensus is clean for the live dirty candidate. No external approval is required. The branch remains uncommitted and one commit behind `origin/main`; no rebase/base-freshness action was performed as part of this independently invoked review.

- Cycle 1: `FINDINGS_TO_RESOLVE`; four findings, three fixed and one rejected with Git lock-creation evidence.
- Cycle 2: `APPROVED`; no unresolved P1/P2.
- Remaining ordinary cycles: one, reserved only for a new blocker introduced by a later change.
