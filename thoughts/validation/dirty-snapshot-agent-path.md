# Dirty Snapshot Agent Path Repro

> Historical, redacted coordinator record. The temporary marker fixture and raw subagent transcripts were not retained, so the two recorded rounds below are not independently auditable from this file alone.

Parent HEAD: `1aa56fd`
Parent working tree marker: `DIRTY_FIXED_NEW` / `fixed-in-working-tree-only`
Parent committed marker: `COMMITTED_OLD` / `still-broken-on-purpose`

## Round 1

| Mode | MARKER_STATE | BUG_LINE | STATUS |
|------|--------------|----------|--------|
| isolated (`isolation: "worktree"`) | COMMITTED_OLD | still-broken-on-purpose | EMPTY |
| live (no isolation) | DIRTY_FIXED_NEW | fixed-in-working-tree-only | dirty present |

## Round 2

| Mode | MARKER_STATE | BUG_LINE | STATUS |
|------|--------------|----------|--------|
| isolated (`isolation: "worktree"`) | COMMITTED_OLD | still-broken-on-purpose | EMPTY |
| live (no isolation) | DIRTY_FIXED_NEW | fixed-in-working-tree-only | dirty present |

## Recorded result

- isolated outcomes recorded `COMMITTED_OLD` (2/2)
- live outcomes recorded `DIRTY_FIXED_NEW` (2/2)

The recorded observation is that `isolation: "worktree"` reviewer agents saw committed HEAD only, while live reviewers in the parent worktree saw the dirty working-tree content.

Machine-local absolute paths are redacted in the companion JSON (`cwd` is `<repo-root>` or `<tmpdir>/pi-agent-*`).
