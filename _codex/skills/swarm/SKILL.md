---
name: swarm
description: "Fan out N parallel workers, drain them, and return one report. Use for /swarm, 'swarm this', or parallel coverage, races, gauntlets, and exploration."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Swarm

Partition independent read-only discovery or review into bounded tasks. State the done predicate, required coverage, expected report, and whether this is a coverage run or candidate comparison. Use native agents within available capacity; queue remaining slices.

Give each agent exact allowed files or sources, a distinct lens, output format, existing evidence, and stop condition. The driver performs implementation and repository operations. For artifact-producing analysis, assign disjoint caller-authorized output paths. Do not assume cloud isolation or automatic worktrees.

Collect required results and consolidate overlapping findings. Report PASS, ISSUES, or BLOCKED with evidence and explicit gaps. A dropout can reduce optional breadth but cannot satisfy missing required coverage. For a race, use the selection rule declared before launch.
