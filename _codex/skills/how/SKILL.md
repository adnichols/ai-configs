---
name: how
description: "Use for \"how does X work\", code walkthroughs before changing something, and placement / ownership / layering questions (\"where should this live\", \"which package owns this\", \"is this the right layer\"). Explains subsystem architecture, runtime flow, onboarding mental models. Can critique architecture. Use why for motivation."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# How

Trace the relevant code before explaining or critiquing it. Start with the question and name the entrypoint, data model, call path, and owner boundaries. Read actual callers and callees. A filename list is not a runtime explanation.

For a narrow question, explore and synthesize in the driving session. For a cross-cutting question with independent evidence sources, request bounded read-only scout agents, each with a distinct slice and an evidence format. Continue tracing the shared entrypoint while they work. Collect all required findings and verify any contradiction against source.

Explain the mechanism, key concepts, ownership, and surprising behavior. Link exact files or primary sources. Keep the explanation proportional to the question; references/explainer-prompt.md supplies an optional presentation rubric.

When critique is requested, explain first, then obtain an independent planner or reviewer pass against the traced model and references/critique-rubric.md. Judge findings as act on, consider, noted, or dismissed with evidence. Do not implement fixes from an explanatory request.
