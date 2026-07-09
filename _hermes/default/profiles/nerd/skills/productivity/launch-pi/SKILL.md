---
name: launch-pi
description: Launch pi mono coding agent in a repository with a prompt. Simple, direct delegation without workflow overhead.
---

# Launch Pi

Quickly launch a pi coding agent in any repository with a prompt or issue context.

## Usage

```
/skill:launch-pi <REPO_NAME> [PROMPT_OR_ISSUE]
```

## Examples

**Basic - just launch in a repo:**
```
/skill:launch-pi doct-dev
```

**With a specific prompt:**
```
/skill:launch-pi ccore "Fix the auth middleware bug in src/auth.ts"
```

**With a Linear issue key:**
```
/skill:launch-pi doct-dev ENG-123
```

**Complex prompt (multi-word):**
```
/skill:launch-pi doct-dev "Refactor the database layer to use connection pooling. Look at src/db/connection.ts and improve error handling."
```

## How It Works

1. Changes to `~/code/<REPO_NAME>/`
2. ALWAYS launches inside tmux — no hidden/background/non-tmux fallback for Aaron's workflow
3. Prefers the attached `main-*` tmux session; otherwise uses another attached tmux session; otherwise creates a tmux session so the run is still visible and resumable
4. Creates a task window with pi on the left and a repo shell/controller pane on the right
5. Launches both panes through Aaron's login shell (for example `zsh -l -c '...'`) so dotenvx/auth variables from the user environment are available
6. Runs from the repo root so pi can pick up local context such as `AGENTS.md` if present
7. Launches pi with `--thinking high`, an explicit `gpt-5.6-sol` model, and an explicit provider resolved from the `openai-codex` family so starts are deterministic
8. Passes your prompt directly to the agent when provided

## Environment

- **Model selection**: deterministic by default. The launcher passes `--model gpt-5.6-sol` unless `PI_MODEL` is explicitly set.
- **Provider selection**: do not leave provider implicit. The launcher should constrain to the `openai-codex` family, resolve a concrete `openai-codex*` provider that exposes `gpt-5.6-sol`, and pass it explicitly. Use `PI_PROVIDER` for an exact override or `PI_PROVIDER_FAMILY` to change the family.
- **Code directory**: `~/code/` (override with `CODE_DIR` env var)

## Determinism rule

Do **not** launch pi with only `--thinking high` or only `--model gpt-5.6-sol`. Pi can otherwise reuse its last interactive model/provider or fall through provider resolution in surprising ways. For Aaron's workflow, both the model and the provider family must be explicit at launch time.

## Verification rule

After a real launch, inspect the live pi header in the pane. It must show `gpt-5.6-sol` and an active provider in the `openai-codex` family. If it does not, stop the run and repair the launcher before continuing.

## Prerequisites

- pi installed and available in PATH
- Repositories at `~/code/<REPO_NAME>/`
- Optional: `AGENTS.md` in repo root for conventions

## Notes

- The primary use case is direct natural-language delegation in a repo; Linear issue keys may still be passed as plain prompt text if useful
- Launching outside tmux is not acceptable for Aaron's workflow. If a proposed approach would start pi headlessly or via direct RPC-only startup, stop and use the tmux launcher instead.
- Prefer the currently attached `main-*` tmux session so Aaron can watch and so the same window can be reused for follow-up nudges like `continue`
- For autonomous supervision started from Discord/gateway, pair the pi pane with a Hermes CLI controller pane; the controller can use CLI-only plugin message injection to keep the workflow moving, while the gateway thread cannot self-inject follow-up turns
- If you later need to stop the launched workflow, do not broad-kill `pi` and do not kill tmux containers by guesswork. Resolve the exact worker pane/session/window/cwd and use `python3 ~/.hermes/scripts/tmux_scoped_kill_pi.py --pane <pane> --expected-session <session> --expected-window <window> --expected-cwd <cwd>` in dry-run mode before `--execute`.
- Use `~/.hermes/scripts/launch_pi_tmux.sh` (or the linked `scripts/launch.sh`) as the canonical launcher rather than improvising ad hoc shell commands
