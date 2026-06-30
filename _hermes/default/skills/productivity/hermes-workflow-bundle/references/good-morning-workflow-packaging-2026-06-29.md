# Good Morning workflow packaging review — 2026-06-29

## Trigger

Aaron asked how to package the Good Morning scripts/templates for reuse. The correct framing is Hermes-first workflow packaging, not renderer ownership or app-layer redesign.

## Core lesson

When packaging a Hermes workflow that includes code and templates:

- Treat the Hermes skill as the behavioral entry point.
- Put runnable workflow code under the exported skill's `scripts/` directory, or a documented workflow subtree if it must install into a vault-local location.
- Put reusable templates under `templates/`.
- Put session-specific implementation notes and operational pitfalls under `references/`.
- Export sanitized config fragments only; never raw `~/.hermes/config.yaml`.
- Export managed memory import blocks, not wholesale memory files.
- Include a manifest with hashes and a verify/import/export tool.
- Package tests and smoke checks so an importing Hermes can verify the workflow.

## Good Morning-specific target shape

Recommended export inside the existing shared bundle:

```text
bundle/skills/productivity/aaron-good-morning/
├── SKILL.md
├── references/
├── scripts/
│   ├── gm_deterministic.py
│   └── gm/
├── templates/
├── tests/
└── assets/
```

Source assets to consider exporting from Aaron's Obsidian workspace:

```text
/Users/anichols/Obsidian/.agents/scripts/gm_deterministic.py
/Users/anichols/Obsidian/.agents/scripts/gm/
/Users/anichols/Obsidian/.agents/commands/gm.md
/Users/anichols/Obsidian/.agents/gm-calendars.yaml
/Users/anichols/Obsidian/.agents/tests/test_gm_deterministic.py
```

## Style / premise discipline

Do not answer packaging questions by introducing an unasked ownership premise, such as "Markdoc should own the rendering layer" or "do not make X own Y," unless the user actually raised that tradeoff. Start from the user’s stated need: package the code/templates/workflow for Hermes. If you need to state an assumption, label it as an assumption.

## Review plan artifact

A review plan was posted to plan-review as `plan_nE0vj4DbYwdi` with source path:

```text
/Users/anichols/Obsidian/adn_vault/thoughts/plans/good-morning-hermes-workflow-packaging.html
```

Do not store this as a durable workflow fact in memory; it is session detail for this packaging reference only.
