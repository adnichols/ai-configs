---
name: herdr-reviewers
description: Run visible read-only Codex and Claude reviews as interactive agents in adjacent Herdr tabs in the same workspace and worktree. Use for required plan and implementation review legs while the legacy Pi review extensions are disabled.
---

# Herdr Reviewers

Use Herdr as the reviewer transport so the operator can watch, focus, inspect, and troubleshoot each review in a normal adjacent tab. The coordinating agent still owns review scope, verification, artifact writing, finding triage, and any fixes.

## Current policy

- In Pi, do not use `codex_review` or `claude_review`; those extensions are disabled.
- Do not launch required reviews through Pi subagents, `interactive_shell`, private tmux launchers, `codex exec`, or Claude print mode.
- Create reviewer tabs in the same Herdr workspace and exact worktree as the coordinating Pi session.
- Prefer one tab per reviewer over pane splits. The coordinating parent owns reviewer-tab lifecycle and cleanup; reviewers never close their own tabs.
- Reviewers are static and read-only. They must not edit files or execute tests, builds, linters, typechecks, benchmarks, or verification commands.

## Discover the parent topology

Use the Herdr CLI and parse returned JSON; IDs are opaque:

```bash
herdr agent list
herdr workspace get <workspace-id>
herdr tab list --workspace <workspace-id>
```

Identify the parent Pi pane by its exact cwd and active session. Do not guess IDs from ordering. If no reachable Herdr session contains the current worktree, report `REVIEW_INFRASTRUCTURE_FAILURE`; do not silently switch transports.

## Create visible reviewer tabs

Create tabs without stealing focus:

```bash
herdr tab create --workspace <workspace-id> --cwd <worktree> --label codex-review-<slug> --no-focus
herdr tab create --workspace <workspace-id> --cwd <worktree> --label claude-review-<slug> --no-focus
```

Record the returned `tab_id` and `root_pane.pane_id` immediately.

### Codex reviewer

Required-review pin:

```bash
herdr agent start <unique-name> --kind codex --pane <pane-id> --timeout 120000 -- \
  -m gpt-5.6-terra \
  -c 'model_reasoning_effort="high"' \
  -s read-only \
  -a never
```

Required review legs must use this exact Codex model/reasoning pair. A different pair requires an explicit operator instruction for that review and must be recorded in the review artifact. Keep `-s read-only -a never`.

Codex may display first-run update, hook-trust, MCP, authentication, or other startup UI after Herdr initially reports readiness. Read the visible screen before the first prompt. If a modal is present, classify it and either dismiss a non-blocking informational modal or leave an auth/trust decision blocked for the operator. Never auto-approve new hooks or permissions.

### Claude reviewer

Default required-review pin:

```bash
herdr agent start <unique-name> --kind claude --pane <pane-id> --timeout 120000 -- \
  --model claude-sonnet-5 \
  --effort xhigh \
  --permission-mode dontAsk \
  --tools Read,Grep,Glob
```

Claude receives no Bash or write-capable built-in tools. The coordinator must include the comparison summary/diff excerpts needed for review, while Claude may inspect named files through read-only tools. The prompt must still prohibit state-changing actions and verification execution. Required Claude review legs are pinned to the full `claude-sonnet-5` model ID at `xhigh`; do not use the `sonnet` alias, Opus, Fable, or any fallback model. A different model/effort pair requires an explicit operator instruction for that review and must be recorded without broadening the tool set.

## Shared parallel orchestration protocol

After creating and starting the visible targets above, run the installed fail-closed helper. Shared-skill installation places the canonical executable at `~/.agents/scripts/review_orchestration.py`; the invocation contract is `~/.agents/scripts/review_orchestration.py run --request <request.json> --output <receipt.json>`. Serial mode remains benchmark-only and the production `run` command is always parallel.

```bash
~/.agents/scripts/review_orchestration.py run \
  --request /absolute/path/review-request.json \
  --output /absolute/path/review-receipt.json
```

The JSON request has top-level `worktree` and a `reviewers` array. Each Codex-only or Codex-plus-Claude entry must contain `name`, already-started Herdr `target`, coordinator-recorded `tab_id`, required non-empty string `workspace_id`, `prompt_file`, `narrowed_retry_prompt_file`, `allowed_verdicts`, and `timeout_seconds`. Prompt paths may be absolute or relative to the coordinator process. Requests fail closed when `workspace_id` is missing, empty, or not a string.

The helper classifies all shared workflow verdicts into semantic outcomes: `pass`, `findings`, `blocked`, or `incomplete`. New workflow-specific tokens must declare a top-level `verdict_classes` object before launch, for example `{"CUSTOM_READY":"pass","CUSTOM_NEEDS_WORK":"findings"}`. Reject an unclassified allowed token before spending reviewer time; never wait until aggregation to discover that the helper lacks the workflow profile. Example reviewer entry:

```json
{"name":"codex","target":"review-codex-1414","tab_id":"w1:t2","workspace_id":"w1","prompt_file":"/tmp/codex-review.txt","narrowed_retry_prompt_file":"/tmp/codex-review-retry.txt","allowed_verdicts":["FINDINGS_TO_RESOLVE","PASS","BLOCKED_BY_QUESTION","REVIEW_INCOMPLETE_RERUN_NEEDED"],"timeout_seconds":600}
```

The helper verifies each target is already available and not working; it never creates a tab, launches a model, or uses private tmux. It computes the complete secret-excluding Git fingerprint, submits every prompt without wait, confirms all applicable prompts before the first wait, waits concurrently, reads `recent-unwrapped`, validates the nonce/verdict/fingerprint, and emits compact JSON containing result, events, and timing. Candidate-fingerprint computations are serialized through one per-adapter lock because each computation runs multiple Git commands; this lock covers only fingerprint computation and must not serialize reviewer waits. Cleanup validates exact tab membership in each recorded workspace for all legs before closing any tab, then confirms exact absence from that same workspace after each close; it never relies on an unscoped global tab list or substring matching. Deterministic tests inject the same command-runner boundary without launching Herdr.

`run` never closes tabs. After the coordinator writes the durable review artifact, cleanup is an explicit second command and requires the clean receipt plus caller confirmation:

```bash
~/.agents/scripts/review_orchestration.py cleanup \
  --request /absolute/path/review-request.json \
  --receipt /absolute/path/review-receipt.json \
  --artifact-written
```

Cleanup rejects non-pass, incomplete, mismatched, or structurally altered receipts. The receipt carries a canonical request digest plus the resolved worktree and each leg's reviewer name, target, tab ID, required workspace ID, accepted result nonce, and raw nonce-block digest; cleanup requires an exact request/receipt identity match, non-empty nonce and digest for every leg, exact recorded-workspace membership for every tab, and a validated pass-class verdict for every requested leg before closing anything. A pass-class verdict may be `PASS` (the green verdict emitted going forward), the legacy `CLEAN_FOR_PR`, `PASS_SCOPED`, `PASS_WITH_DOCUMENTED_OUT_OF_SCOPE_FOLLOW_UPS`, the plan-review `PLAN_EXECUTION_READY`, or a request-declared equivalent. Cleanup does not re-fingerprint after artifact writing, because the coordinator-owned receipt/artifact may itself be a new worktree path; the clean receipt already records the fingerprint validated before artifact creation.

This binding is a stable cleanup identity check, not cryptographic artifact authentication. The helper does not sign or MAC local receipts and does not claim to detect a local actor who can coherently rewrite the receipt and transcript evidence; that separate P4 artifact-authentication concern is outside this protocol.

For two applicable reviewers, prepare both tabs, capture one fingerprint, and submit/confirm both prompts before invoking either wait. Validation is per leg; aggregation occurs only after every applicable leg settles or reaches a truthful timeout/failure. A failed, incomplete, invalid-boundary, stale-fingerprint, timeout, provider/auth, or permission leg prevents a clean aggregate.

Keep transport validity, workflow outcome, and aggregate synthesis separate. A nonce- and fingerprint-valid per-leg result remains accepted even if a generic or stale helper cannot aggregate its workflow-specific token. That condition is an orchestrator profile mismatch, not reviewer failure or missing review coverage. Preserve the accepted per-leg receipt, classify the verdict under the workflow's declared semantics, and do not rerun the reviewer solely to satisfy an implementation-specific aggregate token. The durable artifact must disclose the profile mismatch until the helper configuration is corrected.

The deterministic fixture benchmark reports candidate-wall samples from first submission start through aggregate completion. Because its reviewers are pre-created in memory, reviewer startup is explicitly `not_applicable`; do not fabricate tab-start timing. Report cleanup samples plus median/p75/p90, per-run cleanup success, complete-run count, cleanup coverage/status, and overall result coverage/status. Any incomplete cleanup fails benchmark admission.

## Prompt contract

Before prompting, run `herdr agent get <target>`. Parse and retain that exact leg's nonnegative integer `result.agent.state_change_seq`; a missing or malformed sequence is a transport failure and the prompt must not be treated as safely accepted. Never submit a new review while the target is `working`.

Each prompt must include:

- a cryptographically random unique review ID and nonce generated by the coordinator immediately before submission;
- read-only and no-verification instructions;
- plan/scope and base/comparison range;
- changed files and relevant excerpts or named surfaces;
- caller-supplied verification evidence;
- failure families and severity/scope vocabulary;
- exact output structure and allowed verdicts;
- a bounded final-answer marker:

```text
BEGIN_REVIEW_RESULT <nonce>
...
VERDICT: <allowed-token>
END_REVIEW_RESULT <nonce>
```

Submit each applicable initial prompt without `--wait`, confirm that Herdr accepted it, and only after every applicable prompt is accepted begin independent waits:

```bash
herdr agent prompt <codex-target> "$(cat <codex-prompt-file>)"
herdr agent prompt <claude-target> "$(cat <claude-prompt-file>)"
# only after both commands report prompt acceptance:
herdr agent wait <codex-target> --until idle --until done --until blocked --timeout 600000
herdr agent wait <claude-target> --until idle --until done --until blocked --timeout 600000
```

The shared helper schedules the waits concurrently where practical; the commands above illustrate the acceptance-before-wait boundary, not a license to serialize the waits. Herdr waits on agent state, not a turn ID. Before any settled-state wait or transcript read, each concurrent leg must observe its own `state_change_seq` become strictly newer than the retained pre-submit value. Allow at most 5 seconds for that first transition (or the shorter reviewer timeout), using read-only `herdr agent get` polling. Do not accept an already-settled state while its sequence is unchanged. After a newer sequence is observed, read immediately if the state is already `idle`, `done`, or `blocked`; if it is `working`, wait for settlement with only the remaining reviewer timeout. Missing, malformed, or decreasing sequence data fails closed as a prompt/transport failure. A non-advancing sequence may use only the exact visible-prompt recovery below; without that proof, or if the recovered transition also fails, it likewise fails as transport rather than unusable reviewer output. The nonce and final markers are mandatory correlation evidence and must appear only in output produced after the corresponding prompt submission. Candidate wall timing starts immediately before the first submission call, not at prompt acceptance, and each leg retains the exact first-action observation timestamp from transition confirmation or result waiting.

If `agent prompt` reports `agent_prompt_stalled`, inspect the visible screen for that exact target. Also inspect that same target when `agent prompt` returned success but the bounded first-transition poll observed no strictly newer sequence. Only when the adapter proves the exact full rendered prompt for the current submission is visibly present but unsubmitted may it send one `Enter` with `herdr agent send-keys <target> Enter`, then poll once more under the normal bounded transition rule using only the remaining reviewer timeout. Track the one-Enter allowance per submission and reset it for a narrowed retry submission. In an initial multi-leg batch, mark a reported stall pending and dispatch every remaining initial prompt before polling any pending transition; result-wait recovery occurs only after all initial prompts have already been dispatched and must not reset or serialize sibling budgets. Begin result waits only after every initial prompt is accepted. Any dispatch or confirmation failure aborts the whole batch with zero result waits and preserves all tabs. Serial benchmark mode and a narrowed single-leg retry may confirm synchronously. Never recover on provider/auth/permission failure, visible mismatch, unreadable visible output, missing or malformed state, a decreasing sequence, or absent exact proof. Never resubmit the prompt, press Enter blindly, send a second Enter for the same submission, or send a recovery key to the sibling leg.

## Inspect and capture

After settlement:

```bash
herdr agent get <target>
herdr agent read <target> --source visible --lines 200
herdr agent read <target> --source recent-unwrapped --lines 400
```

The coordinating agent extracts the text between the matching markers and writes the normal durable review artifact. The reviewer does not write the artifact. `recent-unwrapped` may add a provider presentation prefix to each assistant line: the accepted known prefixes are Codex `• ` and Claude `⏺ `, optionally preceded by whitespace. For boundary and verdict parsing only, remove leading whitespace and at most one of those exact prefixes from the start of each line. Unknown prefixes, markers embedded after prose, duplicate boundaries, and quoted or otherwise non-leading boundary tokens remain invalid. Require an allowed workflow verdict as the final non-empty normalized line inside the marker block, then classify that token by semantic outcome rather than assuming every successful workflow says `PASS` (or a legacy green token such as `CLEAN_FOR_PR`).

Mechanical validation protects provenance; it does not override a clearly accepted substantive result. Presentation normalization is limited to the leading whitespace and single known Codex `• ` or Claude `⏺ ` prefix described above. Unknown prefixes, malformed or duplicate boundaries, and invalid final-verdict syntax remain unusable output. Once the helper has mechanically accepted the current turn, nonce block, candidate fingerprint, settled state, non-empty content, and allowed verdict, an aggregate-profile mismatch may be normalized by the coordinating LLM and recorded as a protocol warning. Never use this tolerance for unknown provenance, a stale candidate, provider/auth/permission failure, empty or tool-only output, truncated/incomplete coverage, or a body that substantively contradicts its verdict.

The helper retains the nonce that was actually accepted (the initial nonce or, when used, the narrowed-retry nonce) and hashes only the exact raw line span from that matching `BEGIN_REVIEW_RESULT` line through its `END_REVIEW_RESULT` line inclusive. Provider markers, indentation, content bytes, and line endings inside that span remain raw and digest-significant; normalization is only for marker/verdict matching. Volatile TUI content before or after the block—status footers, counters, prompts, or later presentation material—is not part of the digest and may change without invalidating cleanup. Cleanup re-reads `recent-unwrapped`, requires exactly one ordered block for the recorded nonce, hashes that raw block span, and compares it before any tab is closed.

Before accepting the review, compare the current review fingerprint with the launch fingerprint. Parallel leg settlement may request these checks concurrently, but the adapter serializes only the Git fingerprint computations; reviewer waits remain concurrent:

```text
HEAD commit
+ hash of `git status --porcelain=v1 -uall`
+ hash of the staged diff
+ hash of the unstaged diff
+ deterministic manifest hash for every untracked path
```

The untracked manifest must sort paths bytewise and include each relative path, file type/mode, and content hash; for symlinks include the link target. Do not rely on porcelain status alone because it does not detect content changes to an already-untracked file. Ignored files remain outside review scope unless the review packet explicitly includes them.

If any fingerprint component changed while the review was running, mark every result tied to the launch fingerprint stale. Do not mix a valid old-candidate sibling result with a new-candidate rerun; begin a new cycle from one newly captured complete fingerprint.

The helper records `candidate_fingerprint_captured`, `tab_ready`, `prompt_accepted`, optional `first_action`, `settled`, `result_accepted`, `validation_complete`, and, after the artifact-safe cleanup gate, `cleanup_complete`. Preserve per-leg elapsed time, candidate wall time, and `all_prompts_submitted_before_first_wait` in the review receipt.

## Acknowledge consumed results

Herdr currently has no non-focusing acknowledge command. After the parent has validated a reviewer's complete nonce-delimited result, accepted its fingerprint, and written its durable artifact, immediately use the skill helper to mark that reviewer seen:

```bash
python3 "$HOME/.agents/skills/herdr-reviewers/scripts/acknowledge_reviewer.py" <reviewer-name-or-pane-id>
```

Run this per reviewer as soon as its result is durably consumed, including while another parallel reviewer is still working. The helper requires `done` (or treats an already `idle` reviewer as a no-op), snapshots the currently focused tab, focuses the reviewer so Herdr marks it seen, restores the exact prior tab, and verifies the reviewer becomes `idle`. This prevents an already-consumed reviewer completion from overriding active work in the workspace aggregate.

Do not acknowledge raw completion before the result boundary, verdict, fingerprint, and artifact are accepted. Do not acknowledge `working`, `blocked`, or `unknown` reviewers, invalid/stale results, infrastructure failures, or a tab awaiting operator takeover. An acknowledgment failure leaves the reviewer available for attention; report it and do not loop focus operations. Acknowledgment records consumption only—it does not authorize closing a tab or change the review verdict.

## Failure diagnosis

On timeout, prompt stall, missing markers, invalid verdict, `unknown`, or unexpected settlement:

```bash
herdr agent get <target>
herdr agent read <target> --source recent-unwrapped --lines 400
herdr agent explain <target> --verbose
herdr pane process-info --pane <pane-id>
```

Classify at least:

- startup/update modal;
- authentication or usage limit;
- permission or hook-trust block;
- prompt stall;
- timeout while still working;
- blocked reviewer needing input;
- unknown/misdetected agent state;
- provider/MCP failure;
- missing or truncated result boundary;
- invalid workflow verdict;
- stale worktree fingerprint.

Preserve the tab on any failure so the operator can inspect or take over. Do not switch to the disabled plugins or another model provider as an unreported fallback. Exactly one narrowed retry is allowed only when settled output is unusable (for example missing/duplicate nonce boundaries, empty content, or an unclassifiable final verdict), only for that affected leg, and only after proving the launch fingerprint is unchanged. Provider/auth/permission failures, timeout, stale fingerprint, a valid incomplete verdict, and an already accepted per-leg result accompanied only by an aggregate-profile mismatch are not unusable-output retries.

## Reuse and cleanup

The coordinating parent owns cleanup. A reviewer must never close its own tab or terminate its own session.

Reuse a reviewer tab only when it is settled, its prior result was captured, it still points at the exact worktree, and another review or targeted rereview is pending. Use unique agent names per worktree/review cycle.

After the workflow reaches its final successful review state, the parent closes every reviewer tab that workflow created by default. Close a tab only after all of these are true:

1. the reviewer is settled;
2. the complete nonce-delimited result has been captured and validated;
3. the worktree fingerprint has been accepted;
4. the durable review artifact has been written successfully; and
5. no finding triage, follow-up slice, targeted rereview, or operator takeover is pending.

Before any close, preflight every leg: `herdr agent get <target>` must expose a supported non-empty `tab_id` equal to the coordinator-recorded tab ID, the scoped workspace tab list must contain that exact ID, and the accepted nonce/result digest must still match. Missing, malformed, or mismatched target/tab binding, any workspace-list mismatch, or any other leg preflight failure preserves all tabs.

Close by recorded opaque tab ID, then confirm it is absent from the workspace tab list:

```bash
herdr tab close <tab-id>
herdr tab list --workspace <workspace-id>
```

Preserve reviewer tabs when the verdict is `FINDINGS_TO_RESOLVE`, `BLOCKED_BY_QUESTION`, or `REVIEW_INCOMPLETE_RERUN_NEEDED`; when result validation or infrastructure fails; while a fix/rereview cycle remains pending; or when the operator explicitly asks to keep the tabs open. Preserve any tab whose creation ownership is unknown, because coordinators must not close tabs they did not create.

A cleanup-command failure does not change an otherwise valid review verdict. Report the failed tab ID and leave it available for operator cleanup instead of retrying destructively or claiming it closed.

Report each reviewer's acknowledgment result alongside final tab cleanup. A successfully acknowledged tab may remain open as `idle` when preservation rules apply; a clean final gate should still close owned reviewer tabs normally.

## Current limitations

Herdr visibility replaces opaque subprocess inspection, but this initial approach does not yet reproduce the old plugins' detached-job survival, exact-once completion delivery, automatic Pi continuation, or persisted job ledger. If the parent Pi session exits, the interactive reviewer can remain visible, but a later coordinator must rediscover the tab, inspect its transcript, validate the nonce/fingerprint, and resume manually.
