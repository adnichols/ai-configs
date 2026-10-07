# HTML inventory dashboard

The user-facing inventory is always a real HTML document. Local Markdown/JSON
ledgers and immutable receipts remain evidence, not the dashboard format.
Load the installed `ava` and `ava-design-system` skills before authoring or
editing. Do not copy or edit their managed payloads.

## At a glance

Lead with run status, last verified update time, run ID, lab/generation/build,
corpus partition and coverage limits. Put urgent decisions/blockers and highest
priority actionable findings first. Each finding shows stable ID, explicit
priority, status, confirmed/suspected/inconclusive classification, owner,
customer impact, evidence links and next action. Use text labels as well as
color. Keep confirmed defects, confirmed slow samples, inconclusive observations
and expected behavior distinct; architecture groups link child findings without
counting them again. Never infer a cause, speedup or complete coverage from a
summary count.

Keep current state prominent; move recovery history, old baselines and detailed
samples into native `<details><summary>` sections. Preserve all occurrences,
partition/endpoint limits, canonical image/blob links and the single-writer
notice. Show unassigned owners and unknown next actions honestly. Do not bury
active blockers in history.

Use semantic headings, wrapping cards or a horizontally scrollable table, Ava
CSS variables with fallbacks, and readable light/dark palettes. Keep meaningful
fields available at 320px; do not hide ownership, evidence or next actions on
narrow screens. No scripts or external font/style dependencies.

## Save and update safely

Keep `inventory.html` as the source artifact. Encode its bytes as `source` in a
JSON request with `title` and `source_format: "html"`; `document register --file`
expects that JSON, not a raw HTML file. Persist the exact payload/key before
registering. Save returned document ID, Space, revision and canonical `web_url`.
Draft is sufficient; submit or promote only under the existing workflow's
explicit authority. Describe draft synchronization as saved, not published. Publishing requires an explicit request.

For edits, read status and plan-source, confirm HTML and the expected owned
source, then use `document edit` with `--expected-revision` and a stable key.
Preserve the same document and session. Retry a lost response only with the same
key and identical payload; reconcile unknown outcomes before changing the key.
Conflict or another writer's content stops automatic edits until reconciled.
Keep comments and all source evidence. Existing text inventories are not safely
converted by replace-body: preserve their IDs/links and pending HTML, then use
only a supported, authorized migration; report a format blocker if unavailable.

After each save, read `document plan-source`, `document render` and status.
Require exact intended source, `source_format: html`, matching saved revision,
expected rendered content and understood/empty sanitizer warnings. Save those
receipts. Fix unintended removals through a guarded edit; do not mark sync
verified after failed readback.

At initial creation and after layout changes, use authorized native CUA to
inspect the actual Ava document in light/dark and narrow/wide views. Check the
summary, priority order, links, wrapping and collapsed history. Source checks or
a local screenshot alone do not prove the Ava render. Reuse only the assigned
session; coordinate with its owner and follow profile/foreground/capture consent
rules. If native verification is unavailable, record visual verification pending
and keep the saved/readback status separate; do not invent a pass or open another
agent's browser. A skill-authoring task does not itself authorize live inventory
publication or lab work.
