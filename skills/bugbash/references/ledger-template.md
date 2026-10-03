# Ledger template

`ledger.md` is the single file a compacted or restarted driver reads to
resume. Keep the status table current; the issue files hold the detail.
`scripts/dashboard.py` renders the dashboard from this file alone: the
`# Bugbash` heading, `Mode:`, the `## Status` table (columns are matched by
header name), `## Waiting on you`, and `## Operator decisions`. Republish it in
the same step as every edit here. `Ava space:`, `Dashboard:` and `Dashboard
folder:` are written by `dashboard.py` on first publish; `Listener:` is the
comment listener's service name, pid and log, written by the driver; `Heartbeat:`
is the 20-minute status pass.

```markdown
# Bugbash <YYYYMMDD>-<slug>

Mode: INTAKE | ORCHESTRATION | CONCLUDED
Started: <time>    Done signal: <time or pending>
Driver: cwd <path>, session <session file>, workspace <id>
Default target: <checkout path> @ <base branch>; labs: <lab system>, capacity <N or unknown>
Heartbeat: <id or none>
Ava space: <spc_... or none>
Dashboard: <web_url or none>
Dashboard folder: <folder id of Coding Work / Bug Bash, or none>
Listener: <service name, pid, log path, or none>
Approval rule: "approve BB-NN" authorizes merging that PR at the approved patch, then releasing its lab, removing its demos, and archiving its worktree.

## Status
| ID | Type | Title | Repo | State | Workspace / agent | PR | Waiting on |
|----|------|-------|------|-------|-------------------|----|------------|
| BB-01 | BUG | ... | ava | HANDED_OFF | ws_... / ag_... | — | worker |

## Waiting on you
Every ask made to the operator in chat appears here in the same step, one
`###` block each. Remove it when answered. Write it in technical-founder
language: concrete, short, symptom first, no unexplained internal jargon. The
title names the bug and the fix. `Decide:` may be a `- ` or `1.` list;
`Links:` holds the prototype, PR or lab URLs. Omit a field rather than pad it.

### BB-04: nav "+" cannot create folders → add an inline folder name field
Broken: Clicking "+" offers no way to create a folder, so a new folder needs a trip through a dialog.
Fix: Add an inline name field at the space root; no auto-expand.
Decide:
- Inline field or dialog?
- Labels "Folder" and "Document"?
Links: <prototype url>

## Operator decisions
Newest first; the dashboard shows the first eight.
- <time> | BB-NN | "<verbatim quote>" | <how it was applied>

## Cleanup
- BB-01: lab <released | retained: reason>, demos <removed | none>, workspace <archived>
```
