# Codex prompts

Prompts are installed globally into `~/.codex/prompts`. Use the active skill catalog for workflow details.

- `dev:plan`: create or update a local plan.
- `dev:reviewed-html-plan`: requested Doct publication and review.
- `cmd:execute-plan`: execute through the authorized boundary; defaults to local verification.
- `run-plan`: explicitly requested implementation-through-PR lifecycle.
- `review:change` and `review:change-integrate`: review a plan and integrate feedback.
- `cmd:create-pr`: create an authorized PR using the shared PR workflow.

The old Codex delivery command family, `cmd:debug`, `dev:debug`, and `dev:run` are retired. Ask for diagnosis in plain language, or request plan execution through local verification. Historical `--target dev:run` arguments remain execution-only; they never imply PR publication.

Use native Codex tools. Do not launch Pi or another agent client to satisfy an ordinary Codex command. Follow the target repository's branch policy; ai-configs works on main.

`_codex/install-prompts.py` synchronizes identified managed files and backs up replacements. It preserves custom prompts, edited legacy files, symlinks, and custom subdirectories. Start a fresh session after installation to refresh discovery.
