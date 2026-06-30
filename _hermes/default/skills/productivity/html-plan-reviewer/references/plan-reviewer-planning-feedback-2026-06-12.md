# Plan-reviewer planning feedback — 2026-06-12

Session-derived guidance for future HTML plans that propose changes to `plan-reviewer` itself.

## Workflow corrections

- When Aaron says we are “just planning,” do not restart the plan-reviewer service without explicit permission. Keep working through the comment queue and plan artifact only.
- If a claimed comment was not acked/resolved due to a transient service/API issue, listen again and process the re-claimed comment instead of restarting the service by default.
- Treat browser comments on plan-reviewer UI mocks as authoritative product-design feedback. Apply the smallest plan change, ack, resolve, then restart the queue-backed listener.

## Mode framing

- Frame generalization as explicit review modes over shared infrastructure, not a separate “generic artifact reviewer” product.
- First modes:
  - Planning mode: plan-specific buttons, readiness/status metadata, format enforcement, comments iterate the plan.
  - Collaboration mode: document/agent conversation, document updates, no planning-specific top-bar buttons, no planning-format enforcement.
- Mode selection should be automatic at publish time based on document type/intent. Publishing agents choose the mode; operators or agents can change mode after publication.

## UI mock pitfalls

- Do not invent generic browser-card mockups. Inspect and match the live reviewer shell.
- Current shell structure to mirror:
  - dark top navigation with index link, title/status, compact action buttons, and purple comments badge;
  - persistent left sidebar of active plans/documents with selected cyan outline and status/progress metadata;
  - central document cards using the same dark rounded card system;
  - right-side slide-out comments drawer as a layout column, not a floating or overlapping popover.
- The comments drawer pushes/resizes document content. Model it as a third column (`sidebar | document | drawer`) rather than absolutely positioning it over the document.
- Drawer contents should look like the real system: `Comments` title, plan/document notes card, stacked comment cards with `#N status`, muted metadata, and screenshot links.
- Do not show the “Plan updated in the background. Finish or cancel this comment to refresh.” alert as default drawer chrome. It is conditional conflict/stale-active-comment UI; call out tests ensuring it appears only when that conflict exists.
- For topbar mocks, keep the design responsive: title/index row first, a separate status/mode row above the buttons, and a wrapping action row. Do not squeeze `Execution not ready` into a narrow title cell.

## Plan content additions that worked

- Add UI mocks directly in the plan so reviewers can comment on proposed screens.
- Add explicit acceptance criteria and test coverage for mode inference, mode changes, shared drawer behavior, and conflict-alert correctness.
- Keep an append-only decisions/deviations log for every browser-review correction.
