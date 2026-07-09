---
description: Run any command file dynamically using Kimi K2.5
argument-hint: '<command-name | @path/to/command.md> [arguments...]'
subtask: true
model: fireworks-ai/accounts/fireworks/models/kimi-k2p5
reasoningEffort: high
---

# Dynamic Command Wrapper

Execute another command file by reading it fresh from disk at invocation time.

Input: `$ARGUMENTS`

## Goal

Use this wrapper to bypass cached slash-command discovery for command bodies.

This is useful when:

- a command file was edited after OpenCode started
- a new command file exists on disk but has not been picked up by native slash-command discovery
- you want to force execution under this wrapper's model

## Input Format

`$ARGUMENTS` must contain:

- first token: target command name or `@path/to/command.md`
- remaining text: passthrough arguments for the wrapped command

Examples:

- `dev:plan worktree-cleanup`
- `review:change <plan_path>`
- `@.opencode/commands/my-new-command.md some args here`

## Resolution Rules

Resolve the target command in this order:

1. If the first token starts with `@`, strip the `@` and treat it as a workspace-relative file path.
2. Otherwise check `.opencode/commands/<command-name>.md` in the current workspace.
3. If not found, check `~/.config/opencode/commands/<command-name>.md`.

If no file is found:

- stop
- report the target name
- report each path tried

## Safety Rules

- Reject recursive wrapping. Do not wrap `cmd:wrap`, `cmd:wrap-gpt`, `cmd:wrap-opus`, `cmd:wrap-k2.5`, or any target file whose basename starts with `cmd:wrap`.
- Treat the loaded command file as the authoritative instruction body for this invocation.
- Preserve the wrapped arguments exactly as the wrapped command's `$ARGUMENTS`.
- Frontmatter in the loaded file is informational only for this invocation. This wrapper's `model` and `reasoningEffort` stay in effect.
- If the loaded file conflicts with this wrapper, follow the loaded file unless doing so would create recursion or violate higher-priority instructions.

## Process

1. Parse the first token from `$ARGUMENTS` as `target`.
2. Parse the remaining text as `wrapped_arguments`, preserving it verbatim.
3. Resolve the target command path using the rules above.
4. Use `Read` to load the target command file from disk.
5. State which command file was loaded.
6. Execute the loaded command as if it had been invoked directly, using `wrapped_arguments` as that command's `$ARGUMENTS`.

Important:

- Do not summarize the loaded command and stop.
- After loading it, actually follow the loaded command.
- If the loaded command tells you to inspect files, use tools, run commands, or ask a targeted question, do that work normally.

## Failure Cases

Stop with a clear explanation if:

- no target command was provided
- the resolved file does not exist
- the target is another wrap command
- the target file cannot be read
