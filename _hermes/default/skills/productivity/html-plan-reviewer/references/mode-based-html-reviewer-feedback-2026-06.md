# Mode-based HTML reviewer feedback pattern — 2026-06

## Context

During a browser-reviewed HTML plan for evolving `plan-reviewer`, Aaron used DOM-anchored comments to reshape the product direction. The useful reusable lesson is not the specific plan ID; it is how to handle review comments that change the product framing and require UI evidence inside the plan.

## Product-framing correction

Initial framing was too narrow: “turn plan-reviewer into a generic Hermes HTML artifact reviewer.” Aaron corrected it to a mode-based model:

- The product should support multiple **review modes** for different activities.
- **Planning mode** is one mode, preserving reviewed-plan behavior.
- **Collaboration mode** is another mode, optimized for conversing with an agent through document comments.
- Modes should share infrastructure rather than duplicate implementations.

## Required plan response

When a reviewer makes this kind of correction:

1. Update the top-level title/goal/solution narrative, not just an isolated acceptance criterion.
2. Add a dedicated section for the new product concept (`Review modes`, `Interaction modes`, etc.).
3. Update acceptance criteria, BDD scenarios, test matrix, phase plan, delivery order, non-goals, and decisions/deviations log so the new framing is consistent throughout the plan.
4. Ack/resolve the browser comment only after the plan actually reflects the correction across all relevant sections.
5. Restart the queue-backed listener after ack/resolve if more feedback is expected.

## Mode model details captured from feedback

Planning mode:

- Each comment iterates on the plan.
- Supports threaded conversations.
- Keeps plan-specific buttons at the top of the screen.
- Enforces planning-specific document format.
- Preserves execution-readiness metadata and plan index behavior.

Collaboration mode:

- Each comment is a conversation with an agent.
- Agent responses are visible in the document thread.
- Comments can drive document updates.
- No planning buttons at the top of the screen.
- No planning-specific document format enforcement.
- Collaboration-specific buttons may be added later, after the basic conversation/update loop works.

Shared infrastructure across modes:

- DOM/text/image selection.
- Comment markers.
- Threaded conversations.
- Durable storage.
- Pub/sub or queue-backed comment delivery.
- Source sync.
- Safe rendering.
- Agent delivery/routing.

## UI mock requirement

If a plan proposes new screens, modes, toolbar behavior, or review interactions, include plan-level wireframes/mockups directly in the HTML plan. This lets the reviewer comment on the proposed UI shape. The mockups do not need to be final visual design; they should show:

- Mode label or status.
- Top-bar actions for each mode.
- What is removed or hidden in each mode.
- Where comments/threads appear.
- How agent replies are represented.
- How mode correction/change is exposed.

In the session, the plan added two mock figures:

- Planning mode mock: readiness status, PM/plan review actions, register-ready action, change-mode action, plan-status sidebar, format/readiness indicators.
- Collaboration mode mock: agent selector/status, watch comments, update document, change-mode action, conversation sidebar, no plan readiness or format controls.

## Automatic mode selection

Aaron clarified that mode selection should be automatic at publish time:

- The publishing agent selects the appropriate mode based on document type and intent.
- Reviewed implementation plans default to planning mode.
- General documents, drafts, mockups, briefs, or collaboration artifacts default to collaboration mode.
- Operators and agents must be able to change a document's mode after publication.

Plans for mode-based review products should make the mode inference policy explicit in locked decisions, acceptance criteria, BDD scenarios, and phase tests.
