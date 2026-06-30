# Plan-reviewer UI mock guidance

Session-derived guidance for HTML plans that mock the plan-reviewer UI itself.

## Live shell design language

Before adding UI mocks, inspect the live reviewer page and comments drawer. The current shell is a dark, compact, operational UI:

- Top nav spans the page with `← Plan index`, title/status text, compact action buttons, and a `Comments` button with a purple count badge.
- Left sidebar is persistent with `ACTIVE PLANS`, compact plan cards, blue selected outline, yellow/orange status pill, progress count, pending count, and timestamp metadata.
- Main document sits in the remaining center column, using rounded dark cards, subtle blue-gray borders, large white headings, muted body text, and inline code chips.
- Comments open in a right-side drawer column. The drawer pushes/resizes the document area; it is not a floating overlay and should not overlap document content.
- Drawer styling: dark navy background, left border, large `Comments` heading, notes card, textarea-like note input, optional cyan/blue update alert, stacked comment cards, numbered status headers like `#1 resolved`, muted context metadata, and screenshot links.

## Mocking review modes

When proposing multiple modes such as planning and collaboration:

- Keep the same top nav + left sidebar + center document + right drawer shell across modes.
- Planning mode should show plan-specific actions and state: execution-ready review, Build Plan, Defer plan, Archive plan, execution-readiness/status metadata, and format/readiness affordances.
- Collaboration mode should preserve the shell but replace planning-only actions with document/agent actions such as Watch comments, Update document, Archive document, Comments, and Change mode.
- Mode should be shown as an auto-selected status/chip where appropriate, with a `Change mode` correction path.

## Pitfalls

- Do not use generic browser-window chrome with red/yellow/green dots unless that exists in the real app.
- Do not model comments as popovers over the document. Use the right-side drawer column.
- Do not invent a bright marketing-style design system; preserve the existing dark developer-tool style.
- Do not make collaboration mode look like a separate product; it is the same review shell with different mode policy and actions.
