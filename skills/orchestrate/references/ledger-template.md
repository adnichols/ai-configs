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

**Status table order.** `dashboard.py` shows the table in three tiers, by explicit Priority then ID
within each tier: waiting on the operator (a Needs you state, or `Waiting on`
starting with `operator`), then in progress or blocked, then done. Keep the
ledger's table in the same order whenever you edit it, so the ledger and the
dashboard read alike. A done state stays in the bottom tier even if `Waiting
on` still says operator.

**PR column.** Write every PR as its full URL
(`https://github.com/<owner>/<repo>/pull/<n>`), never `#N` or `repo#N`, so the
dashboard renders each one as a link. Several PRs are comma-separated; a note
such as `→ <merge sha>` may follow. `dashboard.py` refuses to render a PR
number without its URL.

The heading is the tracker title: the weekday and date the tracker started
(`Tuesday, October 6, 2026`), or the theme the operator gave for it
(`Signals polish — Tuesday, October 6, 2026`).

**Waiting on you.** Every ask made to the operator in chat appears in `## Waiting on you` in the same step, one
`###` card each, and is removed when answered. Nothing else goes in this
section: no bullet asks, no bold. `dashboard.py` exits 2 on either, and on a
card with no `Problem:` or no `Decide:`.

Post a card only for a product behavior decision or an irreversible action
reserved to the operator, and say in `Problem:` why it is one.

- The heading names the problem and the change: `### <ID>: <problem> → <change>`.
- `Problem:` explains the issue in plain technical-founder language: what goes
  wrong or is missing, one sentence on the cause, no unexplained internal jargon.
- `Decide:` says exactly what the operator needs to do or choose. Use a `- ` or
  `1.` list for options and recommend one.
- `Fix:` (the proposed change) and `Links:` (prototype, PR or lab URLs) are
  optional; omit a field rather than pad it.

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
Dashboard folder: <folder id of Coding Work (Archive / Coding Work once concluded), or none>
Listener: <service name, pid, log path, or none>
Merge rule: the orchestrator merges each PR at its validated head once every gate passes and every operator decision on the item is answered, then releases its lab, removes its demos, and archives its worktree.

## Status
| ID | Kind | Title | Repo | State | Workspace / agent | PR | Waiting on | Priority |
|----|------|-------|------|-------|-------------------|----|------------|----------|
| WI-01 | BUG | ... | ava | HANDED_OFF | ws_... / ag_... | — | worker | P1 |

## Waiting on you
### WI-04: nav "+" cannot create folders → add an inline folder name field
Problem: Clicking "+" offers no way to create a folder, so making one takes a trip through a separate dialog. The menu only has a Document entry.
Fix: Add an inline name field at the space root, with no auto-expand.
Decide:
- Choose inline field or dialog. I recommend the inline field.
- Confirm the menu labels "Folder" and "Document".
Links: <prototype url>

## Operator decisions
Newest first; the dashboard shows the first eight.
- <time> | WI-NN | "<verbatim quote>" | <how it was applied>

## Cleanup
- WI-01: worktree-cleanup exit <0|4>; lab <released | retained: reason>, demos <removed | none>, workspace <archived>, branch <deleted | kept: reason>
```
