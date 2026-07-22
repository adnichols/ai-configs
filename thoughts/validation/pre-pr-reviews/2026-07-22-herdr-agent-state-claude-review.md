# Claude implementation review — Herdr Pi agent state

- Date: 2026-07-22
- Reviewer: Claude Code `claude-sonnet-5`, `xhigh`, read-only (`Read,Grep,Glob`)
- Transport: visible adjacent Herdr tab `w8G:t3`, agent `herdrstate-claude-0722`
- Review ID: `herdr-state-2fa4e4d69fe2`
- Nonce: `2fa4e4d69fe2ec5a5dd81bbbb79d8c8b`
- Base: `4e40025b41fbbc14d491086296ca3fadb0fe94b3`
- Verdict: `APPROVED`

## Scope reviewed

- `_pi/extensions/herdr-agent-state.ts`
- `_pi/README.md`
- `tests/test_herdr_agent_state.mjs`

The review checked the `agent_end`/`agent_settled` boundary, retry grace and blocked-state preservation, all-except-ignore background-process policy, Doct listener exclusions, environment overrides, process bookkeeping, report ordering, shutdown, documentation, and test fidelity.

## Findings

None. Claude found no P1, P2, or P3 defect on the requested behavior paths.

Claude confirmed that:

- `agent_end` no longer causes a false Idle transition;
- `agent_settled` is the foreground-idle boundary;
- retry holds survive settlement and become blocked after grace;
- reconciliation no longer clears provider-failure state;
- arbitrary tracked background jobs count as working by default;
- built-in and configured passive-process ignores still win in `all` mode;
- Doct `plans listen` and blocking `plans agent next --wait` are ignored while `--no-wait` remains working;
- legacy process-count aliases and explicit `none|finite|all` overrides remain intact.

## Verification assessment

The reviewer accepted the supplied passing evidence:

- `node --check tests/test_herdr_agent_state.mjs`
- `node --check _pi/extensions/herdr-agent-state.ts`
- `node tests/test_herdr_agent_state.mjs`
- `git diff --check`

It noted one non-blocking coverage gap: the deterministic test disables the periodic reconciliation and heartbeat timers, so those safety-net paths are supported by static review rather than direct automated execution. The reviewer concluded this did not make the requested behavior incomplete or the evidence misleading.

The broader `test_install_shared_skills.sh` run reported 19 passing and 7 failing tests. The failures include stale, unrelated repository-baseline expectations around the active agent roster and skill parity. Static review found no evidence that this Herdr patch caused the installer-test failure carrying the Herdr-related test name.

## Fingerprint validation

The worktree fingerprint was unchanged from launch through result capture:

- status hash: `d8f52883868f68f52cfd8f782d97e9da9e56905c05926b736f27de914cf5213b`
- staged diff hash: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- unstaged diff hash: `4319de3289d1e4d549770f84f2900ee758e90dae7faaec30873832477aea915b`
- untracked manifest hash: `3c8171c74dcee3328d02720593648b1afe643b4aca0b6b40c15b71b34a9da4fc`

The exact nonce-delimited result was captured from the reviewer transcript and ended with `VERDICT: APPROVED`.
