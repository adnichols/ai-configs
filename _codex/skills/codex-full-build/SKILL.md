---
name: codex-full-build
description: "Carry a scoped issue or plan through the requested native Codex planning and implementation lifecycle."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Build from a scoped issue or plan

Resolve the user's issue, repository, current branch policy, and acceptance criteria with the installed issue-tracker and planning skills. If planning is requested, use `planning-workflow` or `reviewed-html-plan` for the requested artifact. If a reviewed plan is ready and implementation through a PR is requested, use the parallel `run-plan` skill.

The current Codex session owns discovery, implementation, tests, and Git. Independent native agents provide bounded review. Do not launch another Codex CLI, Pi, or Claude client to take over implementation. Respect an explicit planning-only or execution-only boundary. An issue reference alone does not authorize posting messages, changing issue state, or merging a PR.
