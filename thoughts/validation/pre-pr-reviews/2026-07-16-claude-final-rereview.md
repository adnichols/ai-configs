**One remaining in-plan blocker:**

**P2 — Signal-carrying launcher status is always reclassified as `CODEX_REVIEW_LAUNCHER_PROTOCOL_INVALID`.**

`skills/codex-review-partner/scripts/run-review.sh:87-99, 261-275` — The launcher's `write_status` Python heredoc receives the signal as a positional string arg and stores it as `codexSignal: signal or None`. For both `CODEX_REVIEW_INNER_TIMEOUT` (line 263) and `CODEX_REVIEW_CODEX_SIGNAL` (line 273), the launcher first computes `SIGNAL_NUMBER=$((CODEX_EXIT-128))` and passes e.g. `"9"` or `"15"` verbatim, so the persisted JSON records `codexSignal:"9"`.

`_pi/extensions/codex-review/runtime.ts:169-196` — `validLauncherProtocol` accepts `codexSignal` as string, but the string→number map only contains named keys (`HUP`, `SIGHUP`, `INT`, `SIGINT`, `TERM`, `SIGTERM`, `KILL`, `SIGKILL`). A numeric string like `"9"` maps to `undefined`, so `Number.isInteger(signalNumber)` is false. For every classification whose rule sets `signal: true` (both `CODEX_REVIEW_INNER_TIMEOUT` and `CODEX_REVIEW_CODEX_SIGNAL`), `signalAgrees` is false and the function returns false. `finishOnce` (line 302) then overrides the launcher's truthful classification with `CODEX_REVIEW_LAUNCHER_PROTOCOL_INVALID`.

**Failure scenario:** A real review runs past the 3600 s launcher timeout. The launcher's inner watchdog `SIGTERM/SIGKILL`s the Codex process group; the setsid supervisor's `kill_private_group` reraises `SIGKILL`, so `wait` returns `CODEX_EXIT=137`. The launcher writes a valid `CODEX_REVIEW_INNER_TIMEOUT` status with `codexSignal:"9"`, exits `124`. The runtime reads the status, `validLauncherProtocol` returns false because `map["9"]` is `undefined`, and the completion notification carries `CODEX_REVIEW_LAUNCHER_PROTOCOL_INVALID`. The coordinating workflow follows the "diagnose/repair the launcher protocol defect" branch of `outcomeGuidance` (line 95) instead of the timeout branch (line 99). This violates AC5's requirement to "truthfully distinguish… inner timeout, signal termination" and pushes the wrong retry/next-action guidance to the caller. The same misclassification hits any real Codex signal-death that the launcher would otherwise report as `CODEX_REVIEW_CODEX_SIGNAL`. The existing tests do not catch it: `production-topology.test.mjs`'s inner-timeout test parses the launcher status file directly rather than routing it through `validLauncherProtocol`, and the outer-timeout test bypasses the same validation because outer-timeout classification short-circuits before it.

Fix is small and in-scope (e.g., emit `int(signal)` in the Python heredoc, or accept numeric strings in the runtime map), and both surfaces already own the code paths.

VERDICT: FIX_IN_SCOPE_FINDINGS

---
CLAUDE_REVIEW_LAUNCHER_METADATA
socket=claude-review-claude-review-46e4acbf4889-3848400-653a7c22fdda
session=review
window=claude-review
model=claude-opus-4-7
effort=xhigh
transcript=/home/anichols/.herdr/worktrees/ai-configs/codex-review-plugin/thoughts/validation/pre-pr-reviews/2026-07-16-claude-final-rereview.md.transcript.txt
claude_session_id=040be204-8092-475b-a642-37b348325db6
session_record=/home/anichols/.claude/projects/-home-anichols--herdr-worktrees-ai-configs-codex-review-plugin/040be204-8092-475b-a642-37b348325db6.jsonl
readiness_regex=❯
clear_boundary=persisted Claude session JSONL after visible completion sentinel
history_limit=50000
capture_depth=50000
