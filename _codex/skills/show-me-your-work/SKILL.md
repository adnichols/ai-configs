---
name: show-me-your-work
description: "Keep a decision and evidence record for long-running work or later review."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Keep a decision trail

For a long or unattended task, keep a small reviewable log at the caller's named artifact or a scoped file under thoughts/validation. Record significant decisions as they happen: time, question, evidence, chosen action, rejected alternative, and result. Do not log secrets or unrelated conversation content.

Update the trail when evidence changes a decision. Distinguish planned, attempted, verified, and blocked actions. Link actual commands and artifacts; a claim in the log is not proof of the result.

Before handoff, check the log against the active task history and outputs. When available and useful, request a fresh bounded read-only reviewer to identify unsupported claims or unresolved risks. Report the actual model; independent GPT review is not cross-family review. Missing history limits the audit and must be disclosed.

Return the artifact link and the issues that need the user's attention. Commit the trail only when committing is part of the task. Do not create an extra review gate for trivial work.
