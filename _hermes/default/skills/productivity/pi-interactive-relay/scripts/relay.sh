#!/bin/bash
# Pi interactive relay wrapper
# Handles line buffering issues for Discord/Gateway bidirectional chat

set -e

REPO="${1:-ccore}"
MODEL="${2:-gpt-5.4}"
CODE_DIR="${CODE_DIR:-$HOME/code}"
REPO_PATH="$CODE_DIR/$REPO"

if [ ! -d "$REPO_PATH" ]; then
    echo "Error: Repository not found at $REPO_PATH"
    exit 1
fi

cd "$REPO_PATH"

# Use stdbuf to force line buffering on stdout
# This helps output appear immediately in Discord/Gateway
exec stdbuf -oL pi --model "$MODEL" --thinking-level high
