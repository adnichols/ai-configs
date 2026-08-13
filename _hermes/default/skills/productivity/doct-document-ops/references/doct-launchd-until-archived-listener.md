# Durable macOS Doct listener until archival

Use this pattern when Aaron asks to keep a listener active for one existing Doct HTML document until that document is archived.

## Architecture

Use a document-scoped Python dispatcher managed by a macOS LaunchAgent:

1. Read the document with `doct-agent documents get --id <document-id> --json` before every claim wait.
2. Treat either `archivedAt != null` or `status == "archived"` as the terminal condition.
3. While active, wait for one routed item with:
   ```bash
   doct-agent plans agent next \
     --base-url https://doct.nodaste.com \
     --workspace-id <workspace-id> \
     --document-id <document-id> \
     --wait --timeout 60 --json
   ```
4. For each claim, dispatch a bounded Hermes worker that loads `doct-document-ops`, reads the claim and current plan, applies the smallest grounded change, replies, then acks and resolves. Release the claim on timeout or a safety blocker.
5. After each worker, return to the lifecycle check and one-claim wait.

## LaunchAgent contract

Use `RunAtLoad=true` and:

```xml
<key>KeepAlive</key>
<dict>
  <key>SuccessfulExit</key>
  <false/>
</dict>
```

This distinction matters:

- listener crash/nonzero exit → launchd restarts it;
- document archived → listener exits `0`, so launchd leaves it stopped.

Set `ThrottleInterval` to avoid restart storms. Store stdout/stderr and a small state JSON under `~/.hermes/state/doct-document-listeners/<document-id>/`.

## PATH discipline

LaunchAgents receive a minimal environment. Resolve executable paths during setup and place absolute paths for `doct-agent` and `hermes` in the dispatcher or LaunchAgent. Do not assume the interactive shell PATH is present.

This is a deployment rule, not a claim that either executable is unavailable.

## Scope and routing

- Scope every queue/claim command to exactly one workspace and document.
- Ordinary conversation comments do not wake the agent queue. Only comments/actions routed with the agent submit action produce claims.
- Do not substitute `plans watch`; it synchronizes source and is not the comment listener.
- Do not use an unbounded `agent next --wait`; use bounded waits so archival is rechecked regularly.

## Verification

Before reporting completion, verify all of the following with real output:

1. `documents get` reports the expected document, workspace, current status, and no archival timestamp.
2. `plans queue list` succeeds for the exact document.
3. The dispatcher script passes `python -m py_compile`.
4. The plist passes `plutil -lint`.
5. `launchctl print gui/$(id -u)/<label>` reports `state = running` and a PID.
6. The listener state JSON reports lifecycle `active`.
7. A child `doct-agent plans agent next ... --wait` process is observable.
8. Listener stdout/stderr contain no startup error.

## Worker safety

The worker prompt should explicitly require:

- current-plan read before editing;
- repository/canonical-source update first when the source is identifiable;
- no invented repository facts when it is not identifiable;
- version-aware `plans update` and conflict reconciliation;
- visible reply, ack, and resolve;
- release on timeout or inability to act safely;
- no cron creation from inside the worker.
