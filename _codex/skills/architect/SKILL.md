---
name: architect
description: "Sketch types, signatures, and module structure before code, then stay in the loop while implementation fills in. Use for /architect, 'architect this', 'design this', or non-trivial work where jumping to code would lock in the wrong shape."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Architect

Ground the affected system with `how`, and use `why` when existing ownership or compatibility decisions constrain the change. Write the caller's usage first, then derive data types, signatures, module ownership, and failure behavior. Use references/rationale-template.md and references/design-red-flags.md for the design package and screening rubric.

For a material unresolved design choice, ask two bounded read-only planner agents for structurally different alternatives. Give both the same requirements and constraints, with distinct design questions, and require rationale. Keep proposals in their returned results or explicitly named artifacts. The driver compares interface depth, hidden complexity, migration cost, and verification against the actual task. Use `arena` only when a deliberate candidate comparison would answer the uncertainty.

For a settled or mechanical shape, sketch directly and state why alternatives would add no useful evidence. Do not spawn implementation workers or publish broken scaffolding as a completed phase.

Proceed with authorized implementation after choosing the shape, unless the user requested a checkpoint. The driver writes the code and tests. Record material deviations; repeated friction in the same boundary is evidence to revisit the shape, not permission for unrelated redesign. Verify the finished behavior against the original requirements.
