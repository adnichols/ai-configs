---
name: reflect
description: Spawn three parallel review subagents over the active transcript, surface learnings, and route each to a concrete edit on an existing skill. Use when the user says reflect.
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Reflect

Review the active task's decisions and outcomes. Establish the authorized transcript or task-history source with native Codex tools. If unavailable, use current context and supplied artifacts, explicitly limiting the review to that evidence.

Request three bounded read-only reviews when the task merits independent analysis: tooling and execution, technical judgment, and alternative approaches. Name the allowed task/history scope and ask for concrete moments, effects, and actionable lessons. Use the scout, reviewer, and planner role defaults from the runtime contract. A review may be returned in-chat; no reviewer edits configuration or skills.

Compare the findings against actual tool results and artifacts. Discard advice that merely adds ceremony or expands the user's scope. Return a short account of what worked, what failed, and which structural change would prevent a repeated mistake. Apply durable changes only when the user's request includes them. Do not automatically mine other projects or create an improvement PR.
