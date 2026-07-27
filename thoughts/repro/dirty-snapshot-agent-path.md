# Dirty Snapshot Agent Path Repro

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

## Result

- `isolated_all_old`: true (2/2)
- `live_all_new`: true (2/2)
- `repro_confirmed`: true

`isolation: "worktree"` reviewer agents see committed HEAD only, not uncommitted dirty fixes. Live reviewers in the parent worktree see the dirty working-tree content.
