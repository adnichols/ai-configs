---
name: audit-adn
description: "Audit the Codex-only ADN installation, file integrity, and precedence over shared skills."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Audit the Codex skill installation

Audit `$CODEX_HOME/ai-configs-skills.json`, normally `~/.codex/ai-configs-skills.json`. This manifest lists installed skills and SHA-256 values for their files. Use Python's pathlib, json, hashlib, and tomllib to compare each installed file against the recorded hash and identify missing or changed files. Do not modify files during an audit.

For each listed skill, check its Codex SKILL.md exists and its frontmatter name matches the folder. Inspect only skill configuration entries in config.toml. Confirm the corresponding `~/.agents/skills/<name>/SKILL.md` and resolved symlink path are disabled, and the Codex copy is enabled. Do not print unrelated configuration or credentials.

When the native app-server skills/list endpoint is available, confirm each expected name has one enabled entry pointing to the Codex copy. A file-level check alone does not prove discovery. Report PASS only for the checks actually completed, with limitations for unavailable discovery evidence. This is an integrity audit, not a session-usage count or permission to refresh the upstream pin.
