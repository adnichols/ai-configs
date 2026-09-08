---
name: recall
description: "Reconstruct your recent working context from your own chat history, live state, and the shared record (user reports, prior fixes, incidents), then hand back a tight current-state brief. Use for 'recall my work on X', 'catch me up', 'what have I been working on', 'where did I leave off', before starting or resuming work."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Recall

Reconstruct work for the user's named topic, project, and time window. A supplied current-state handoff can be enough; do not mine history unnecessarily. For a single-task handoff use adn-mode's session-pickup playbook.

Use available Codex task/history tools first. Search only authorized tasks in the named project. If those tools are unavailable, use supplied handoffs, this conversation, and Git history; state which evidence is missing. Do not infer a transcript filesystem layout or read unrelated projects.

For a large corpus, delegate bounded read-only source slices while the driver verifies branches and artifacts. Record the goal, decisions, rejected approaches, corrections, remaining work, and artifact links. If the question needs issue or incident history, use `why` for relevant connected sources, without sending messages.

Check current Git and PR state before calling historical work complete. Return a compact capsule, status per workstream, recurring unresolved problems, and the next concrete action. Distinguish planned, implemented, verified, published, and merged states. Cite only history and artifacts actually read.
