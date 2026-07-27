# Herdr Interactive Reviewer Transport

## Status

Experimental default for Pi required Codex and Claude reviews. The former repo-owned Pi review extensions are disabled and retained under `_pi/disabled-extensions/` for rollback and comparison.

## Why

The managed review tools hid the live reviewer UI behind a Pi tool row and private subprocess machinery. Failures required inspecting generated transcripts and cache artifacts. Herdr provides operator-visible tabs, agent status, focus/attach controls, recent terminal output, and detection diagnostics in the same workspace as the coordinating Pi session.

## Topology

- Parent: the top-level Pi session driving the plan or implementation review.
- Workspace: the existing Herdr workspace for the active worktree.
- Reviewer tabs: one no-focus adjacent tab per applicable reviewer.
- Cwd: exactly the parent's active worktree; no new worktree is created.
- Default layout: tabs, not pane splits, because tabs are easier to navigate and leave the parent layout unchanged.
- Lifecycle owner: the coordinating parent records created tab IDs and closes successful reviewer tabs after durable capture; reviewers never clean up themselves.

## Reviewer startup

Codex default:

```bash
herdr agent start <name> --kind codex --pane <pane-id> --timeout 120000 -- \
  -m gpt-5.6-terra \
  -c 'model_reasoning_effort="high"' \
  -s read-only \
  -a never
```

Claude default:

```bash
herdr agent start <name> --kind claude --pane <pane-id> --timeout 120000 -- \
  --model claude-sonnet-5 \
  --effort xhigh \
  --permission-mode dontAsk \
  --tools Read,Grep,Glob
```

Claude is not given Bash or write-capable built-in tools. The coordinator supplies diff summaries/excerpts and Claude uses read-only tools for named-file inspection.

Required Codex reviews remain pinned to `gpt-5.6-terra` at `high`, and required Claude reviews remain pinned to the full `claude-sonnet-5` model ID at `xhigh`. A different model/reasoning or model/effort pair requires an explicit operator instruction for that review and must be recorded. Claude aliases, Opus, Fable, and fallback models are prohibited without that instruction. Read-only controls are not optional.

## Orchestration contract

1. Discover the parent Pi pane and workspace by exact cwd/session evidence.
2. Record a launch fingerprint: `HEAD`, hash of porcelain status with all untracked paths, staged diff hash, unstaged diff hash, and a deterministic manifest hash covering every untracked path's relative name, type/mode, content hash, or symlink target.
3. Create no-focus reviewer tabs and record opaque workspace/tab/pane IDs.
4. Start each reviewer with explicit model, reasoning/effort, and read-only arguments.
5. Inspect the visible screen before the first prompt. Startup update, hook-trust, MCP, auth, or usage UI can appear after initial readiness.
6. Generate a cryptographically random review ID/nonce immediately before submission, then submit a bounded prompt with exact result boundaries.
7. Wait for `idle`, `done`, or `blocked` through `herdr agent prompt --wait`.
8. Read visible and recent-unwrapped output. Validate matching boundaries, exact verdict, non-empty result, and unchanged worktree fingerprint.
9. The coordinating Pi agent writes the normal durable review artifact and triages findings.
10. Keep tabs open while findings, follow-up slices, fixes, targeted rereviews, blocked states, invalid results, or infrastructure diagnosis remain pending.
11. Once the workflow reaches a final successful review state and all durable artifacts are written, the parent closes the reviewer tabs it created by recorded tab ID unless the operator requested preservation. Confirm closure from the workspace tab list. A cleanup failure is reported but does not rewrite a valid review verdict.

## Result boundary

```text
BEGIN_REVIEW_RESULT <nonce>
<review body>
VERDICT: <workflow-token>
END_REVIEW_RESULT <nonce>
```

Herdr state waits are not turn-ID waits, and terminal reads are snapshots rather than a dedicated final-message API. The nonce and boundaries prevent a stale prior result or startup text from being accepted as the current review.

Transport parsing is wrap-safe and last-complete-block-wins: hard or soft line breaks inside a known `BEGIN_REVIEW_RESULT <nonce>` / `END_REVIEW_RESULT <nonce>` fence are rejoined before matching, and if the reviewer emits more than one sequential well-formed block the latest block is accepted. Nested, unmatched, or extra same-nonce boundaries remain invalid. When the reviewer can write files, an OS-temporary structured JSON side channel (`nonce`, `verdict`, `body`) is preferred and falls back to the transcript fence if absent. It is deliberately outside the candidate checkout so its transport-owned writes cannot alter the full candidate fingerprint; cleanup revalidates and digests the same accepted sidecar. Herdr agent targets can be opaque pane IDs; launchers that use names must satisfy Herdr's 1-32 character name rule (`^[a-z][a-z0-9_-]{0,31}$`) and should use short generated names rather than long descriptive labels.

The untracked manifest is required because porcelain status does not detect content changes to an already-untracked file. If prompt submission stalls and the complete prompt is visibly present but awaiting Enter, send one Enter and switch to `herdr agent wait`; otherwise diagnose rather than sending blind input.

## Failure diagnosis

Use, in order:

```bash
herdr agent get <target>
herdr agent read <target> --source visible --lines 200
herdr agent read <target> --source recent-unwrapped --lines 400
herdr agent explain <target> --verbose
herdr pane process-info --pane <pane-id>
```

Classify startup/update modals, auth or usage limits, permission/hook-trust blocks, prompt stalls, timeout while working, blocked state, unknown detection, provider/MCP failures, missing/truncated boundaries, invalid verdicts, and stale worktree fingerprints. Never call an ambiguous result clean.

## Experiment evidence

A Codex reviewer was started successfully in an adjacent tab in this worktree with an explicit model, medium reasoning, and read-only sandbox. The first launch performed an automatic CLI update and exited; restart was required. After restart, Codex displayed an MCP warning and a hook-review modal after Herdr had reported readiness. Dismissing the informational modal and re-prompting produced a complete visible architecture review. This demonstrates both the observability benefit and the need for a post-start visible-screen check before the first prompt.

A fresh Pi parent successfully created and drove an adjacent Claude reviewer tab after installation. Herdr detected working, blocked, and done states and exposed the full transcript. The first prompt stalled with the text present but not submitted; one explicit Enter recovered it. Claude then attempted to create a plan file under `~/.claude/plans` despite the read-only prompt, and Herdr surfaced the permission block so the coordinator could deny it. This led to a stricter Claude launch contract with only `Read,Grep,Glob` and no Bash/write-capable tools.

A second fresh-tab experiment validated that stricter contract. Claude started with `dontAsk` plus only `Read,Grep,Glob`; process inspection confirmed the argv, prompting completed in one call, the reviewer moved directly to `done`, the transcript showed only one file read, no permission prompt or write attempt occurred, nonce-delimited capture succeeded, and the worktree fingerprint remained unchanged.

## Known gaps versus disabled plugins

The first Herdr transport does not yet provide:

- detached supervisor/job survival semantics owned by Pi;
- exact-once completion delivery into the originating Pi session;
- automatic continuation after parent reload/restart;
- a persisted review job ledger;
- dedicated final-message or persisted-session JSONL extraction;
- automatic process-tree cleanup classification beyond parent-owned successful-tab closure.

Herdr keeps an interrupted, failed, blocked, or still-actionable reviewer and its tab visible, so recovery is manual: rediscover the tab, inspect the transcript, validate the nonce and worktree fingerprint, capture the artifact, and resume the coordinating workflow. Successfully completed tabs are closed by the parent only after their accepted results are durable.

## Rollback

The disabled extension source remains under `_pi/disabled-extensions/claude-review` and `_pi/disabled-extensions/codex-review`. Restoring it requires an explicit decision, moving it back under `_pi/extensions/`, removing it from `DISABLED_PI_EXTENSIONS`, reinstalling Pi configuration, and updating the review skills/doctrine back to the managed-tool transport.
