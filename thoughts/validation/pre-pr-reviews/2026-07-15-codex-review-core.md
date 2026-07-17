## 1. Scope checked

Reviewed the P1–P3 launcher/controller boundary against AC1–AC14:

- Canonical launcher, verdict grammar/profiles, status protocol, timeout behavior
- Managed extension lifecycle, persistence, publication, cleanup, reconciliation, notification delivery
- Runtime routing guard and targeted tests
- Non-Pi wrapper compatibility

## 2. Coverage table

| File/surface | Check performed | Result | Review coverage |
|---|---|---|---|
| `run-review.sh` | Launch policy, recursion, status, timeout, publication | Regression found | Complete |
| `runtime.ts` | Persistence, protocol validation, cleanup, reconciliation, delivery | Four lifecycle defects found | Complete |
| `index.ts` | Tool schema, shutdown and notification wiring | Wiring valid; runtime races remain | Complete |
| Policy scanner/guard | Positive signatures and replacement guidance | No additional top-five finding | Complete |
| Launcher tests | Profile, artifact, status, timeout coverage | Misses recursion regression | Complete |
| Extension tests | Protocol, restart, shutdown, exactly-once coverage | Material gaps identified below | Complete |

## 3. Findings

1. **[P1][REGRESSION_FROM_THIS_DIFF] The launcher no longer prevents nested Codex-review recursion.**

   File/line: `skills/codex-review-partner/scripts/run-review.sh:38-53`; `skills/codex-review-partner/SKILL.md:89-91`

   Evidence: The review contracts now begin only with “You are performing … review.” The prior active-review marker was removed, while the skill’s non-recursion rule still depends on the wrapper or prompt saying that review-partner invocation is already active. An inner Codex session therefore receives a prompt that triggers this same skill without the condition that prevents another review launch. `CODEX_REVIEW_PARTNER_ACTIVE=1` is only an environment variable and is not part of the model prompt.

   Why required: P1 preserves the wrapper as the canonical deterministic policy boundary. Recursive reviewer launches can consume the timeout budget and return no final artifact, defeating that boundary and regressing existing non-Pi behavior.

2. **[P1][IN_PLAN] Contradictory launcher status can still be promoted to a successful review.**

   File/line: `_pi/extensions/codex-review/runtime.ts:137-149`

   Evidence: The controller validates only protocol version and whether `outcome === "success"` agrees with exit code zero. It does not cross-check `classification`, `codexExitCode`, `codexSignal`, `timeout`, `matchedSource`, or `finalMessageValidation`. For example, exit zero plus `{outcome:"success", classification:"CODEX_REVIEW_INNER_TIMEOUT", finalMessageValidation:"invalid"}` and a valid staging artifact is published as `CODEX_REVIEW_SUCCEEDED`.

   The fake-launcher tests cover missing status but no contradictory status fields.

   Why required: AC5 and P2 explicitly require missing, malformed, or contradictory protocol to become `CODEX_REVIEW_LAUNCHER_PROTOCOL_INVALID`; clean success must never be inferred from exit code and artifact alone.

3. **[P1][IN_PLAN] Restart and timeout cleanup neither verifies the stored process group safely nor waits for it to be reaped.**

   File/line: `_pi/extensions/codex-review/runtime.ts:75-76`, `89-103`, `126-130`, `158`

   Evidence:

   - Reconciliation compares only the launcher PID’s `/proc` start time, then signals the separately persisted `pgid` without verifying that the PID still belongs to that group or checking the persisted job nonce.
   - A matching restart orphan receives only `SIGTERM`; there is no grace-period escalation, wait, or surviving-process check before reservation release and notification.
   - The outer watchdog schedules `SIGKILL` but calls `finish()` immediately, so terminal persistence and notification can occur while descendants remain alive.
   - `reap()` sends signals but never waits for the child’s `close` event.
   - `restart-reconciliation.test.mjs` only covers `starting` without a process, omitting matching, dead, mismatched/reused PID and hard-host-loss cases mandated by P2.

   Why required: AC8/S11 require identity-safe reconciliation, bounded TERM/KILL escalation, full reaping, and no live launcher/login-shell/Codex descendants before cleanup completes.

4. **[P2][IN_PLAN] Session shutdown can race an in-progress start and leave a newly launched review behind.**

   File/line: `_pi/extensions/codex-review/runtime.ts:107-124`, `162`

   Evidence: `start()` checks `shuttingDown` before awaiting cwd and prompt resolution. If shutdown occurs during either await, `shutdown()` sees no running job and returns; `start()` then continues through reservation, spawn, and accepted running-state persistence. Shutdown also filters only jobs already marked `running`.

   The installed shutdown test cancels an already accepted running job and does not exercise this race.

   Why required: AC6 and AC8 require graceful shutdown to leave no process and produce zero follow-up turns. The current race can leave a review running and later deliver a completion after shutdown.

5. **[P2][IN_PLAN] Exactly-once eligible completion is not durable across the persistence/delivery boundary.**

   File/line: `_pi/extensions/codex-review/runtime.ts:39`, `77`, `89-105`, `151-155`

   Evidence: `notified` is in-memory only and is explicitly omitted from persisted state. Terminal state is written before `onComplete`:

   - A host loss after terminal persistence but before delivery leaves a terminal record that startup loads without delivering, producing zero notifications.
   - During reconciliation, state-write failure is ignored and delivery still occurs. Because the persisted record remains `running`, the next startup reconciles and delivers it again.
   - Current tests prove exactly-once only within one uninterrupted process.

   Why required: AC6 and the P2 end state require every notification-eligible terminal path, including startup reconciliation and degraded persistence, to emit exactly one completion rather than zero or duplicates.

## 4. Remaining checks

None. The assigned review slice is complete. Fixes need targeted regression tests for nested-review suppression, contradictory protocol fields, real running-job reconciliation and escalation, shutdown/start interleaving, and crash boundaries around terminal persistence and completion delivery.

## 5. Final verdict

VERDICT: FIX_IN_SCOPE_FINDINGS