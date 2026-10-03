# Ledger template

`ledger.md` is the single file a compacted or restarted driver reads to
resume. Keep the status table current; the issue files hold the detail.
`scripts/dashboard.py` renders the dashboard from this file alone: the
`# Bugbash` heading, `Mode:`, the `## Status` table (columns are matched by
header name), `## Waiting on you`, and `## Operator decisions`. Republish it in
the same step as every edit here. `Ava space:` and `Dashboard:` are written by
`dashboard.py` on first publish; `Heartbeat:` is the 20-minute status pass and
`Dashboard heartbeat:` the 10-minute comment reader.

```markdown
# Bugbash <YYYYMMDD>-<slug>

Mode: INTAKE | ORCHESTRATION | CONCLUDED
Started: <time>    Done signal: <time or pending>
Driver: cwd <path>, session <session file>, workspace <id>
Default target: <checkout path> @ <base branch>; labs: <lab system>, capacity <N or unknown>
Heartbeat: <id or none>
Ava space: <spc_... or none>
Dashboard: <web_url or none>
Dashboard heartbeat: <id or none>
Approval rule: "approve BB-NN" authorizes merging that PR at the approved patch, then releasing its lab, removing its demos, and archiving its worktree.

## Status
| ID | Type | Title | Repo | State | Workspace / agent | PR | Waiting on |
|----|------|-------|------|-------|-------------------|----|------------|
| BB-01 | BUG | ... | ava | HANDED_OFF | ws_... / ag_... | — | worker |

## Waiting on you
Every ask made to the operator in chat appears here in the same step, one
bullet each, with its links. Remove it when answered.
- BB-04 prototype review: <url>
- BB-09 question: <exact question>

## Operator decisions
- <time> | BB-NN | "<verbatim quote>" | <how it was applied>

## Cleanup
- BB-01: lab <released | retained: reason>, demos <removed | none>, workspace <archived>
```
