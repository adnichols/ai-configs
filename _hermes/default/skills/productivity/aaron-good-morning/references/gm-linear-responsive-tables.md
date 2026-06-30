# GM Linear Responsive Tables

Session learning from the 2026-06-28 deterministic GM review.

## Problem

The Linear issue section originally used a two-row table layout with spacer/colspan-style cells: first row carried ID/title/state/requestor, second row carried assignee/project/updated. In the Plan Review iframe this caused column headers and values to visually drift, especially when titles, emails, or ISO timestamps wrapped.

Aaron's preference: Linear should be dense but aligned. Headers and values must stay in stable lanes, and redundant summaries like a separate "By priority" section should be removed when they duplicate the Aaron-assigned weekly view.

## Durable rendering pattern

Use one logical row per issue with stable columns:

1. linked ID
2. description/title
3. state badge
4. requestor/creator
5. assignee
6. project badge
7. compact updated date

Implementation notes:
- Prefer a CSS grid/table wrapper with explicit column sizing over spacer cells or colspan-based two-row rows.
- Set a wide enough `min-width` for desktop so dense columns do not collapse; allow horizontal scroll in the table wrapper when needed.
- Keep ID, state, project, requestor, assignee, and updated values `white-space: nowrap` on desktop; let only the description column wrap.
- Convert raw ISO updated timestamps to compact local display, e.g. `Jun 28 09:11 MDT`, to avoid timestamp-driven wrapping.
- On narrow screens, collapse each issue to a labeled card using `data-label` values so all fields remain readable without horizontal header alignment.
- Preserve accessibility roles (`role="table"`, `role="row"`, `role="columnheader"`, `role="cell"`) when using div/grid markup.

## Test expectations

Regression tests should assert:
- rendered issue IDs remain links, with fallback `https://linear.app/nodaste/issue/<identifier>` URLs when source data lacks a URL;
- the Linear table uses the grid/table classes and columnheader/cell roles;
- requestor, assignee, project/state badges, and updated fields are present as same-row cells with `data-label` metadata;
- full ISO timestamp strings are not emitted in the issue table;
- `issue-spacer` and `colspan` are absent;
- redundant `By priority` headings/priority-breakdown blocks are absent when Aaron only wants the prior-week Aaron-assigned view.

## Plan-review handling

When a Plan Review comment flags Linear formatting or redundancy:
1. Patch the deterministic renderer, not only the generated HTML.
2. Add/adjust renderer tests before rerendering the artifact.
3. Rerender the canonical DailyGM artifact from the deterministic checkpoints.
4. Confirm Plan Review sync and drain/resolve the comment queue.
5. Visually inspect the live Plan Review page when the issue is about legibility/alignment.
