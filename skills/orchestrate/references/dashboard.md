# Dashboard details

Read when creating a dashboard, changing its layout, or applying dashboard
feedback. Card rules, the listener, and the every-change rule stay in SKILL.md
§ Dashboard.

**Runs.** Title = ledger `# ` heading. The first run registers the document,
moves it into its folder, and writes `Ava space:`, `Dashboard:`, and
`Dashboard folder:` into the ledger header. Later runs edit in place with the
current revision guard and read back source, render, and warnings to confirm
the saved HTML. Draft standing suffices; submit/promote only when the
workflow separately authorizes it. A run with no ledger change prints
`unchanged`.

**Location.** Development Space (`spc_16ef6d824e21402b9a42560b13436034`) is
the default. Open trackers sit directly in its root folder "Coding Work";
concluded ones move to `Archive / Coding Work` (chosen from the ledger's
`Mode:`). Folder lookup order:

1. the folder id in `dashboard.json` or the ledger's `Dashboard folder:`, if
   still a folder at that exact path;
2. otherwise the path by title via `ava document tree`, from the root;
3. missing levels are created under the right parent. Reruns reuse what they
   find, never creating a folder twice.

Each run confirms the document is in the folder and moves it back if not.
`--space` uses another Space (same folders resolved or created there).
`--folder-path` overrides `Coding Work` (a concluded tracker then goes to
`Archive/<that path>`); it exists for tests.

**Visual check at creation and after layout changes.** Inspect the actual Ava
render with authorized native CUA on the assigned session, light and dark,
narrow and wide: priority order, summary, links, wrapping, collapsible
history. Never operate another agent's browser or bypass foreground/capture
consent. If CUA is unavailable, record visual verification as pending,
separately from successful source readback; never report a visual pass. Do
not start live publication during skill validation.

**Listener restart.** `listener.json` holds `last_poll` and `last_error`.
After a compaction or restart, read it: pid dead or `last_poll` older than two
minutes → restart with the same command. It refuses to start twice, skips
comments it already handled, and retries one whose relay failed. The
dashboard header tells the operator a listener is watching.

**Feedback on the dashboard** (content or format), both in the same step:

1. Apply it live. Layout, wording, styling →
   `<tracker-dir>/dashboard-template.html` (copy
   `references/dashboard-template.html` there first; the script prefers it).
   Changes the template cannot express (a new column, a different grouping)
   → a copy of `scripts/dashboard.py` in the tracker dir, with `ledger.py`
   and `reconcile.py` (which it imports), run from there. Save and confirm
   with the operator.
2. Log a skill follow-up: its own `WI-NN` (repo ai-configs, target
   `skills/orchestrate`) with the operator's words verbatim and what you
   changed live, so a worker folds it into `references/dashboard-template.html`
   or `scripts/dashboard.py` and the next tracker starts with it. Never edit
   the skill from the orchestrator session.

**Standard format.** `references/dashboard-template.html` owns the layout:
top status/mode, updated time and tracker identity, counts, urgent decisions,
then prioritized items. Priority lives in the ledger's Status table; the
dashboard shows ID and priority, item, state, waiting on, and PR; ledger
columns it does not render are ignored. Distinguish confirmed from suspected
or inconclusive findings. Tiers: operator-needed, then active/blocked, then
completed; within a tier by explicit priority, then ID. Completed items and
decision history collapse. Keep evidence URLs and original occurrences in the
ledger and item files. Every field stays reachable at narrow widths (overflow
scroll, never hidden columns). A legacy tracker-local template the renderer
rejects is reconciled with the maintained template, keeping its
customizations; never delete the live tracker or start a replacement session.
Use Ava theme variables with fallbacks; no OS-only dark-mode media query or
fixed theme overrides inside Ava. Update script and template together.

**Weft styling.** Corner radii are the Weft tokens (`@nodaste-lab/weft`
`css/weft.css`), declared in the template's `:root`:
`--weft-radius-chip: 2px` (state chips, state pills, inline `code`) and
`--weft-radius-card: 4px` (cards). Never `--weft-radius-pill` (`999px`, kept
for oblong controls such as switches and progress tracks) or an invented
radius (`8px`, `12px`) on a status label; Weft's own `.weft-badge` (incl.
`.is-status`) uses the chip radius. Take new values from `css/weft.css`,
never memory.
