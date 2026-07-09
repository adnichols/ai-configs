#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF' >&2
Usage: launch_pi_tmux.sh <repo-or-path> [window-name] [prompt-file]

Launch interactive pi in tmux so Aaron can always watch it live.
- Resolves bare repo names under ~/code/
- Pins to exact tmux session main-0 when it exists (for iTerm control-mode compatibility)
- Creates/replaces a named task window with pi on the left and a shell on the right
- Starts pi deterministically with explicit model/provider from the openai-codex family
EOF
}

if [ $# -lt 1 ]; then
  usage
  exit 1
fi

REPO_INPUT="$1"
WINDOW_NAME="${2:-}"
PROMPT_FILE="${3:-}"
CODE_DIR="${CODE_DIR:-$HOME/code}"
MODEL="${PI_MODEL:-gpt-5.6-sol}"
THINKING="${PI_THINKING:-high}"
PROVIDER_FAMILY="${PI_PROVIDER_FAMILY:-openai-codex}"
EXPLICIT_PROVIDER="${PI_PROVIDER:-}"

resolve_repo_path() {
  local input="$1"
  if [ -d "$input" ]; then
    python3 - <<'PY' "$input"
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve())
PY
    return
  fi
  if [ -d "$CODE_DIR/$input" ]; then
    python3 - <<'PY' "$CODE_DIR/$input"
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve())
PY
    return
  fi
  python3 - <<'PY' "$input"
from pathlib import Path
import sys
print(Path(sys.argv[1]).expanduser().resolve())
PY
}

resolve_tmux_session() {
  if tmux has-session -t '=main-0' 2>/dev/null; then
    printf 'main-0\n'
    return
  fi
  if tmux has-session -t '=main' 2>/dev/null; then
    printf 'main\n'
    return
  fi
  local session
  session="$(tmux list-sessions -F '#{session_name} #{session_attached}' 2>/dev/null | awk '$2 != 0 {print $1; exit}')"
  if [ -n "$session" ]; then
    printf '%s\n' "$session"
    return
  fi
  if ! tmux has-session -t '=pi-main' 2>/dev/null; then
    tmux new-session -d -s pi-main -n shell "zsh -l"
  fi
  printf 'pi-main\n'
}

resolve_provider() {
  if [ -n "$EXPLICIT_PROVIDER" ]; then
    printf '%s\n' "$EXPLICIT_PROVIDER"
    return
  fi
  local provider
  provider="$(zsh -l -c "pi --list-models $(printf '%q' "$MODEL") 2>&1" | awk -v family="$PROVIDER_FAMILY" 'NR > 1 && index($1, family) == 1 {print $1; exit}')"
  if [ -z "$provider" ]; then
    echo "Could not resolve a $PROVIDER_FAMILY provider for model $MODEL" >&2
    exit 1
  fi
  printf '%s\n' "$provider"
}

sanitize_window_name() {
  local raw="$1"
  raw="${raw//[^A-Za-z0-9._-]/-}"
  raw="${raw#-}"
  raw="${raw%-}"
  if [ -z "$raw" ]; then
    raw="pi-task"
  fi
  printf '%s\n' "${raw:0:48}"
}

REPO_PATH="$(resolve_repo_path "$REPO_INPUT")"
if [ ! -d "$REPO_PATH" ]; then
  echo "Repository path does not exist: $REPO_PATH" >&2
  exit 1
fi
if ! command -v tmux >/dev/null 2>&1; then
  echo "tmux is required for this launcher" >&2
  exit 1
fi
if ! command -v pi >/dev/null 2>&1; then
  echo "pi is required for this launcher" >&2
  exit 1
fi
if [ -n "$PROMPT_FILE" ] && [ ! -f "$PROMPT_FILE" ]; then
  echo "Prompt file not found: $PROMPT_FILE" >&2
  exit 1
fi

SESSION_NAME="$(resolve_tmux_session)"
DEFAULT_WINDOW="$(basename "$REPO_PATH")"
WINDOW_NAME="$(sanitize_window_name "${WINDOW_NAME:-$DEFAULT_WINDOW}")"
PROVIDER="$(resolve_provider)"

if tmux list-windows -t "$SESSION_NAME" -F '#{window_name}' | grep -qx "$WINDOW_NAME"; then
  tmux kill-window -t "$SESSION_NAME:$WINDOW_NAME"
fi

LEFT_PANE="$(tmux new-window -P -F '#{pane_id}' -t "$SESSION_NAME" -n "$WINDOW_NAME" "zsh -l")"
RIGHT_PANE="$(tmux split-window -h -P -F '#{pane_id}' -t "$LEFT_PANE" "zsh -l")"
tmux select-layout -t "$SESSION_NAME:$WINDOW_NAME" even-horizontal >/dev/null

PI_CMD="cd $(printf '%q' "$REPO_PATH") && pi --provider $(printf '%q' "$PROVIDER") --model $(printf '%q' "$MODEL") --thinking $(printf '%q' "$THINKING")"
tmux send-keys -t "$LEFT_PANE" "$PI_CMD" C-m

RIGHT_CMD="cd $(printf '%q' "$REPO_PATH") && printf 'repo=%s\nwindow=%s:%s\n' $(printf '%q' "$REPO_PATH") $(printf '%q' "$SESSION_NAME") $(printf '%q' "$WINDOW_NAME") && git status --short --branch || true"
tmux send-keys -t "$RIGHT_PANE" "$RIGHT_CMD" C-m

if [ -n "$PROMPT_FILE" ]; then
  sleep 4
  tmux load-buffer -b hermes-pi-launch "$PROMPT_FILE"
  tmux paste-buffer -b hermes-pi-launch -t "$LEFT_PANE"
  tmux send-keys -t "$LEFT_PANE" C-m
  tmux delete-buffer -b hermes-pi-launch >/dev/null 2>&1 || true
fi

HEADER=""
for _ in 1 2 3 4 5 6 7 8; do
  sleep 2
  HEADER="$(tmux capture-pane -p -S -120 -t "$LEFT_PANE" | tail -60)"
  if printf '%s' "$HEADER" | grep -q "$MODEL"; then
    break
  fi
done
VERIFIED_MODEL=0
VERIFIED_PROVIDER=0
if printf '%s' "$HEADER" | grep -q "$MODEL"; then
  VERIFIED_MODEL=1
fi
if printf '%s' "$HEADER" | grep -Eq "$PROVIDER_FAMILY|$PROVIDER"; then
  VERIFIED_PROVIDER=1
fi

cat <<EOF
SESSION=$SESSION_NAME
WINDOW=$SESSION_NAME:$WINDOW_NAME
LEFT_PANE=$LEFT_PANE
RIGHT_PANE=$RIGHT_PANE
REPO_PATH=$REPO_PATH
MODEL=$MODEL
PROVIDER=$PROVIDER
PROMPT_FILE=${PROMPT_FILE:-}
VERIFIED_MODEL=$VERIFIED_MODEL
VERIFIED_PROVIDER=$VERIFIED_PROVIDER
EOF

if [ "$VERIFIED_MODEL" != "1" ] || [ "$VERIFIED_PROVIDER" != "1" ]; then
  echo "WARNING: could not verify model/provider from the live tmux pane yet; inspect $SESSION_NAME:$WINDOW_NAME manually." >&2
fi
