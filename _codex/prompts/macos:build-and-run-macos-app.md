---
description: Build and run a local macOS app with a stable project script
argument-hint: "[scheme/workspace/project/product options or mode hints]"
---

# Build and Run macOS App

Use the imported macOS build skills to detect the project shape, create or update a project-local `script/build_and_run.sh`, then build and run through that script.

Arguments: $ARGUMENTS

## Workflow

1. Detect whether the repo is an Xcode workspace, Xcode project, or SwiftPM package.
2. Resolve the runnable target and process name.
3. Create or update `script/build_and_run.sh` so the default path is always: stop existing app/process, build, run.
4. For SwiftPM GUI apps, stage and launch a project-local `.app` bundle with `/usr/bin/open -n` instead of raw executable launch.
5. Support `--debug`, `--logs`, `--telemetry`, and `--verify` modes only when the user asks for them.
6. Run the script in the requested mode and summarize the top blocker if build or launch fails.

## Guardrails

- Do not initialize a nested git repo.
- Do not add `.codex/environments/environment.toml` unless the user explicitly asks for Codex Run-button support too.
- Keep the no-flag script path simple: kill, build, run.
- Prefer one stable project script over one-off command chains.
