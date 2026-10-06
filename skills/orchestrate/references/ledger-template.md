# Ledger template

`ledger.md` is the single file a compacted or restarted orchestrator reads to
resume. Keep the status table current; the item files hold the detail.
`scripts/dashboard.py` renders the dashboard from this file alone: the `# `
heading (which becomes the Ava document title), `Mode:`, the `## Status` table
(columns are matched by header name), `## Waiting on you`, and `## Operator
decisions`. Republish it in the same step as every edit here. `Ava space:`,
`Dashboard:` and `Dashboard folder:` are written by `dashboard.py` on first
publish; `Listener:` is the comment listener's service name, pid and log,
written by the orchestrator; `Heartbeat:` is the 20-minute status pass.

The heading is the tracker title: the weekday and date the tracker started
(`Tuesday, October 6, 2026`), or the theme the operator gave for it
(`Signals polish — Tuesday, October 6, 2026`).

```markdown
# <tracker title>

Tracker: <YYYYMMDD>-<slug>
Mode: INTAKE | ORCHESTRATION | CONCLUDED
Started: <time>    Done signal: <time or pending>
Driver: cwd <path>, session <session file>, workspace <id>
Default target: <checkout path> @ <base branch>; labs: <lab system>, capacity <N or unknown>
Heartbeat: <id or none>
Ava space: <spc_... or none>
Dashboard: <web_url or none>
Dashboard folder: <folder id of Coding Work, or none>
Listener: <service name, pid, log path, or none>
Merge rule: the orchestrator merges each PR at its validated head once every gate passes and every operator decision on the item is answered, then releases its lab, removes its demos, and archives its worktree.

## Status
| ID | Kind | Title | Repo | State | Workspace / agent | PR | Waiting on |
|----|------|-------|------|-------|-------------------|----|------------|
| WI-01 | BUG | ... | ava | HANDED_OFF | ws_... / ag_... | — | worker |

## Waiting on you
Every ask made to the operator in chat appears here in the same step, one
`###` block each. Remove it when answered. Write it in technical-founder
language: concrete, short, problem first, no unexplained internal jargon. The
title names the problem and the change. `Decide:` may be a `- ` or `1.` list;
`Links:` holds the prototype, PR or lab URLs. Omit a field rather than pad it.

### WI-04: nav "+" cannot create folders → add an inline folder name field
Problem: Clicking "+" offers no way to create a folder, so a new folder needs a trip through a dialog.
Fix: Add an inline name field at the space root; no auto-expand.
Decide:
- Inline field or dialog?
- Labels "Folder" and "Document"?
Links: <prototype url>

## Operator decisions
Newest first; the dashboard shows the first eight.
- <time> | WI-NN | "<verbatim quote>" | <how it was applied>

## Cleanup
- WI-01: worktree-cleanup exit <0|4>; lab <released | retained: reason>, demos <removed | none>, workspace <archived>, branch <deleted | kept: reason>
```
