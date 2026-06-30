#!/usr/bin/env bash
# Launch pi agent in tmux with optional prompt
# Usage: launch.sh <REPO_NAME> [PROMPT]

set -euo pipefail

REPO_NAME="${1:-}"
shift || true
PROMPT="$*"

if [ -z "$REPO_NAME" ]; then
  echo "Usage: $0 <REPO_NAME> [PROMPT]" >&2
  exit 1
fi

TMP_PROMPT=""
cleanup() {
  if [ -n "$TMP_PROMPT" ] && [ -f "$TMP_PROMPT" ]; then
    rm -f "$TMP_PROMPT"
  fi
}
trap cleanup EXIT

if [ -n "$PROMPT" ]; then
  TMP_PROMPT="$(mktemp)"
  {
    if [ -f "$HOME/code/$REPO_NAME/AGENTS.md" ]; then
      printf 'Follow AGENTS.md and any repo-local planning/testing/product-intent docs.\n\n'
    fi
    if [[ "$PROMPT" =~ ^[A-Z]+-[0-9]+$ ]]; then
      printf 'Work on Linear issue: %s\n' "$PROMPT"
    else
      printf '%s\n' "$PROMPT"
    fi
  } > "$TMP_PROMPT"
fi

WINDOW_NAME="$(printf '%s' "$REPO_NAME" | tr '/ ' '--')"
exec "$HOME/.hermes/scripts/launch_pi_tmux.sh" "$REPO_NAME" "$WINDOW_NAME" "$TMP_PROMPT"
