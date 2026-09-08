---
name: setup-adn
description: "Configure Codex ADN role models using the available native models; preserve the driving model."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Configure ADN for Codex

Read the role defaults at ../adn-mode/references/codex-models.json and the actual native spawn tool's supported models and efforts. Preserve the driving session model. Do not configure Cursor rules or OMP role settings.

For requested role changes, inspect `$CODEX_HOME/adn-models.json`, normally `~/.codex/adn-models.json`, if it exists. Use the shape of codex-models.json: a role maps to model and reasoning_effort. Valid roles are scout, planner, reviewer, and oracle. Write only model and effort values actually exposed in the current client, merging the user's requested changes and preserving other valid role entries. Explain any unavailable requested model before choosing a substitute.

This JSON configures the parallel skills' role choices; it does not register native named agent types or change an already running agent. New delegations read it through the runtime contract. Use `audit-adn` to check the installed parallel package. Do not reinstall another runtime as a setup side effect.
