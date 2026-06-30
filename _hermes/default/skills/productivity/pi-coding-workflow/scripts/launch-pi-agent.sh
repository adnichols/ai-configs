#!/usr/bin/env bash
# Launch pi in tmux for repo workflow tasks with optional prompt file.
# Usage: launch-pi-agent.sh <REPO_NAME> [PROMPT_FILE]

set -euo pipefail

REPO_NAME="${1:-}"
PROMPT_FILE="${2:-}"

if [ -z "$REPO_NAME" ]; then
  echo "Usage: $0 <REPO_NAME> [PROMPT_FILE]" >&2
  exit 1
fi

if [ -n "$PROMPT_FILE" ] && [ ! -f "$PROMPT_FILE" ]; then
  echo "Error: prompt file not found: $PROMPT_FILE" >&2
  exit 1
fi

WINDOW_NAME="$(printf '%s' "$REPO_NAME" | tr '/ ' '--')"
exec "$HOME/.hermes/scripts/launch_pi_tmux.sh" "$REPO_NAME" "$WINDOW_NAME" "$PROMPT_FILE"
