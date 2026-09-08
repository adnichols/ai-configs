---
name: arena
description: "Spawn N parallel candidates at the same task, pick a base, graft the strongest parts of the losers into it. Use for /arena, 'arena this', 'throw it in the arena', or when one attempt at a non-trivial artifact would lock in the wrong shape."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Arena

Use a candidate comparison to resolve a material design or artifact uncertainty. State the common task, constraints, and 3-6 gradeable criteria before generating candidates. Ask bounded read-only planner agents for at least two distinct proposals; assign separate output paths only when the user authorized writing those artifacts. The driver owns all implementation.

Read every complete candidate. When independent work remains, request a fresh reviewer to score the completed candidates against the same rubric while the driver compares them. Never review files that candidates are still writing. Use role defaults from the Codex runtime contract; label the actual models and do not imply cross-family diversity.

Choose a base by criterion-level evidence. Resolve disagreements against the requirements. Graft only justified ideas, record what was kept and rejected, and implement the coherent result in the driving session. Verify the synthesis itself. If required candidates are missing, report incomplete coverage; do not fabricate a winner. Reframe only when evidence shows the task was underspecified.
