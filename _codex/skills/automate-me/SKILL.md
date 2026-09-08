---
name: automate-me
description: "Use for \"automate me\", \"create/update/refresh my -mode skill\", \"turn/capture my preferences or working style into a skill\", or wanting agents to follow how the user works. Drafts or revises a personal -mode skill via create-skill + unslop, optionally pulling fresh evidence from recent transcripts."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Capture a personal working style

Use the user's stated preferences and authorized task history to create or update a personal mode skill. First locate an existing matching mode in the active skill catalog. Preserve its location and policy unless the user requests a change.

Read only the relevant project's supplied history or native Codex task records. Identify repeated corrections, delegation preferences, desired evidence, writing style, and stopping conditions. Distinguish explicit preferences from your inference. Missing history is not permission to scan unrelated conversations.

Use the active Codex `skill-creator` guidance to author the result. Put Codex-only skills under `$CODEX_HOME/skills`, normally `~/.codex/skills`, or the repository's maintained source when requested. Keep examples and runtime choices scoped; reference supporting ADN skills instead of copying all their rules.

Validate naming, frontmatter, references, and realistic positive and negative triggers. Preserve the default invocation policy unless the user requests explicit-only behavior. Report the changes and the observations supporting them. Do not alter other clients' model rules or install locations.
