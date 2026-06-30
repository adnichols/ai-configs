---
name: hermes-opencode-linear-build
description: Use this skill when wiring Hermes or any external orchestrator to run Linear issue builds through OpenCode over the OpenCode HTTP API. Trigger when the user asks how Hermes should launch, monitor, resume, or supervise `/cmd:linear-build-workspace`, OpenCode workspace-backed Linear builds, run ledgers, or external API control of OpenCode. This skill keeps Hermes as a thin supervisor and OpenCode as the build orchestrator.
---

# Hermes to OpenCode Linear Build Workflow

Use this skill to integrate an outside orchestrator, especially Hermes, with the deterministic OpenCode Linear issue build workflow.

The core rule: Hermes starts and monitors the job; OpenCode owns orchestration inside an OpenCode workspace.

## Architecture

Hermes should not decompose Linear issue work into ad hoc prompts like "make a plan," "run tests," "do PM review," or "fix blockers." That recreates the nondeterministic process this workflow is designed to avoid.

Hermes should instead:

- discover the OpenCode server
- create an OpenCode session in the target repo
- send one entrypoint command: `/cmd:linear-build-workspace <ISSUE_KEY> <BASE_REF>`
- monitor OpenCode workspace/session status and the run ledger
- report blocked states or final PR status to the operator

OpenCode is responsible for:

- creating/reusing the OpenCode workspace row
- creating the workspace-backed git worktree
- initializing `thoughts/runs/<issue-slug>.md`
- enforcing stage transitions through `linear_build_orchestrator.py`
- planning, review, implementation, validation, evidence, PR creation, and PR feedback loops

## Required OpenCode Side Components

The target OpenCode config must have:

- `~/.config/opencode/commands/cmd:linear-build-workspace.md`
- `~/.config/opencode/scripts/create_linear_workspace.py`
- `~/.config/opencode/scripts/linear_build_orchestrator.py`

After installing or changing these, long-lived OpenCode servers may need a safe restart before the command is available.

## Server Discovery

Prefer explicit configuration from Hermes:

```bash
OPENCODE_URL=http://127.0.0.1:63333
OPENCODE_DIRECTORY=/Users/anichols/code/heddle
```

If Hermes is launched by or near OpenCode, it can use `OPENCODE_SERVER_URL`, `OPENCODE_URL`, or discover the port from `OPENCODE_PID` with `lsof`. Avoid broad port scans.

If Basic auth is enabled, pass:

```bash
OPENCODE_SERVER_USERNAME=opencode
OPENCODE_SERVER_PASSWORD=<password>
```

HTTP examples below assume:

```bash
BASE_URL="${OPENCODE_URL:-http://127.0.0.1:63333}"
REPO_DIR="/Users/anichols/code/heddle"
ISSUE_KEY="NOD-123"
BASE_REF="origin/develop"
```

When auth is enabled, add:

```bash
AUTH=(-u "${OPENCODE_SERVER_USERNAME:-opencode}:${OPENCODE_SERVER_PASSWORD}")
```

Otherwise use `AUTH=()`.

## Launch Protocol

Known OpenCode 1.14 HTTP/API quirks from live use are summarized in `references/opencode-1-14-http-linear-build-quirks.md`; check it when session creation, `prompt_async`, or slash-command execution behaves unexpectedly.

### 1. Check OpenCode Health

Use a cheap route that resolves the project path:

```bash
curl -fsS "${BASE_URL}/path?directory=$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=""))' "${REPO_DIR}")"
```

If this fails, Hermes should report `OPENCODE_UNREACHABLE` and not start the build.

### 2. Create an OpenCode Session

Create the session in the repo directory. Use a descriptive title so the session is easy to find in OpenCode.

```bash
SESSION_JSON="$(curl -fsS "${AUTH[@]}" \
  -H 'Content-Type: application/json' \
  -X POST "${BASE_URL}/session?directory=$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=""))' "${REPO_DIR}")" \
  --data-binary "$(python3 - <<'PY'
import json, os
print(json.dumps({
  "title": f"Linear build {os.environ['ISSUE_KEY']}",
  "agent": "build",
  "permission": [
    {"permission": "edit", "action": "allow", "pattern": "*"},
    {"permission": "bash", "action": "allow", "pattern": "*"},
    {"permission": "webfetch", "action": "allow", "pattern": "*"},
  ],
}))
PY
)")"
SESSION_ID="$(python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])' <<<"${SESSION_JSON}")"
```

Do not create separate sessions for individual stages unless the run ledger explicitly reaches a blocked state and the operator asks to resume in a new session.

### 3. Send the Single Build Command

Use `/session/{sessionID}/message` for streaming clients, or `/session/{sessionID}/prompt_async` when Hermes wants fire-and-monitor behavior.

Preferred async launch:

```bash
curl -fsS "${AUTH[@]}" \
  -H 'Content-Type: application/json' \
  -X POST "${BASE_URL}/session/${SESSION_ID}/prompt_async?directory=$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=""))' "${REPO_DIR}")" \
  --data-binary "$(python3 - <<'PY'
import json, os
prompt = f"/cmd:linear-build-workspace {os.environ['ISSUE_KEY']} {os.environ.get('BASE_REF', 'origin/develop')}"
print(json.dumps({
  "parts": [{"type": "text", "text": prompt}],
  "agent": "build",
}))
PY
)"
```

Treat HTTP `204 No Content` from `prompt_async` as success. Do not then fall back to `/message`; that can duplicate the user prompt and create an extra delegated worker session.

If the OpenCode server version does not support `prompt_async` (for example a non-2xx/404 response), send the same payload to `/session/{sessionID}/message` and keep the connection open, or use `/session/{sessionID}/command` with `command` and `arguments` if your OpenCode build exposes command execution over HTTP.

The prompt should stay small. Do not include the issue body or a stage plan; the slash command fetches Linear metadata and initializes the ledger.

## Monitoring Protocol

Hermes should monitor three sources, in this order.

### 1. OpenCode Session Status

```bash
curl -fsS "${AUTH[@]}" "${BASE_URL}/session/status?directory=$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=""))' "${REPO_DIR}")"
```

Use this to determine whether the session is busy, retrying, or idle. Do not infer build success from idle status; idle can mean success, blocked, or waiting for the operator.

### 2. OpenCode Workspace Row

List workspaces for the repo:

```bash
curl -fsS "${AUTH[@]}" "${BASE_URL}/experimental/workspace?directory=$(python3 -c 'import urllib.parse,sys; print(urllib.parse.quote(sys.argv[1], safe=""))' "${REPO_DIR}")"
```

Expected workspace id format:

```text
wrk_<issue_key_lower_with_non_alphanumerics_as_underscores>
```

For `NOD-123`, expect `wrk_nod_123`.

Once the workspace row exists, Hermes may read its `directory` and `branch`. Use that workspace directory for ledger checks.

### 3. Run Ledger State

The source of truth is the ledger created inside the workspace:

```text
thoughts/runs/<issue-slug>.md
```

The Markdown ledger contains an embedded JSON block between:

```text
<!-- OPENCODE_LINEAR_BUILD_STATE_BEGIN -->
<!-- OPENCODE_LINEAR_BUILD_STATE_END -->
```

Hermes can parse this block directly, or ask the helper for status:

```bash
python3 ~/.config/opencode/scripts/linear_build_orchestrator.py status \
  --ledger /path/to/workspace/thoughts/runs/<issue-slug>.md
```

Prefer helper status if Hermes can run local commands on the same host; parse JSON directly when Hermes only has file access.

## State Machine Semantics

Important stages:

- `ISSUE_CAPTURE`
- `WORKSPACE_READY`
- `LEDGER_READY`
- `PLAN`
- `PLAN_GATES`
- `IMPLEMENTATION`
- `VALIDATION`
- `EVIDENCE`
- `CODE_REVIEW`
- `PM_REVIEW`
- `PR_READY`
- `PR_CREATED`
- `PR_FEEDBACK`
- `COMPLETE`

Hermes should treat stage verdicts as authoritative.

Continue waiting when:

- session is busy/retry
- ledger `currentStage` changes recently
- latest stage verdict is passing and not terminal

Notify the operator when:

- any verdict starts with `BLOCKED_`
- `VALIDATION_FAILED`
- `PM_NOT_ACCEPTABLE`
- `CODE_REVIEW_BLOCKED`
- manual evidence status is `blocked`, `failed`, or `pending` after OpenCode reports it cannot improve it
- the same stage remains unchanged past the configured timeout and session is idle

Report success when:

- `PR_CREATED` has a passing verdict and PR URL is present, or
- `COMPLETE` has a passing verdict

## Resume Protocol

If OpenCode service restarts or the session is interrupted, Hermes should not reconstruct stages itself.

Resume by sending a small continuation prompt to the existing session if possible:

```text
continue the Linear build from the run ledger; do not skip helper guards
```

If a new session is required, create it in the workspace directory and include:

```text
Resume the deterministic Linear build from <ledger-path>. Read the embedded JSON state, run linear_build_orchestrator.py guard before the next stage, and continue only from the first incomplete or blocked-remediable stage.
```

Do not send raw instructions like "now validate" unless the ledger says validation is the next allowed stage.

## PR Feedback Protocol

After PR creation, Hermes may poll GitHub or receive webhook events. For unresolved review threads, send one scoped continuation prompt to the OpenCode session:

```text
PR feedback is available for <PR_URL>. Continue the deterministic Linear build from <ledger-path>. Enter PR_FEEDBACK only through linear_build_orchestrator.py, address in-scope review findings, rerun impacted validation, and update the ledger.
```

Hermes should not summarize review threads into implementation orders unless it also includes the PR URL and tells OpenCode to classify findings against the plan.

## Timeout Policy

Hermes can impose watchdogs, but it must not mark validation acceptable because a command timed out. If a watchdog fires:

1. Check `/session/status`.
2. Check latest ledger `currentStage`, command log, and blockers.
3. If session is busy, keep waiting or ask operator.
4. If idle and ledger did not advance, send one continuation prompt asking OpenCode to reconcile the ledger.
5. If still idle/no progress, notify the operator as `HERMES_WATCHDOG_STALLED` with session id, workspace id, current stage, and ledger path.

## Anti-Patterns

Avoid these patterns from Hermes:

- Running `create_linear_workspace.py` and then issuing bespoke plan/build prompts instead of `/cmd:linear-build-workspace`.
- Creating one OpenCode session per stage.
- Treating chat text as the source of truth instead of the ledger.
- Treating synthetic DOM events as native evidence.
- Treating `npm test` timeout as acceptable because a focused test passed.
- Force-pushing, rebasing, or merging from Hermes while OpenCode owns the workspace.
- Editing files directly from Hermes during the run.

## Minimal Hermes Implementation Checklist

Implement these functions in Hermes:

- `discoverOpenCodeServer()`
- `createOpenCodeSession(repoDir, title)`
- `sendPromptAsync(sessionId, repoDir, prompt)`
- `listWorkspaces(repoDir)`
- `findWorkspace(issueKey)`
- `readRunLedger(workspaceDir)`
- `parseLedgerState(markdown)`
- `pollSessionStatus(repoDir)`
- `classifyOutcome(ledgerState, sessionStatus)`
- `resumeSession(sessionId, ledgerPath)`

Keep the orchestration loop simple: launch once, poll, surface blocked/complete states.

## Example Outcome Report

When reporting to the operator, use this shape:

```text
Linear build NOD-123
Workspace: wrk_nod_123
Directory: /.../opencode/worktree/.../<name>
Session: ses_...
Current stage: VALIDATION
Verdict: VALIDATION_FAILED
Ledger: thoughts/runs/nod-123-<slug>.md
Blocker: npm test timed out in session-context.behavior.test.tsx
Next action: OpenCode should remediate test timeout or operator should decide whether to stop.
```

Keep Hermes output factual and derived from the ledger.
