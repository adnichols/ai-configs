#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SOURCE_DIR/.." && pwd)"

for bin_dir in "$HOME/.local/bin" /opt/homebrew/bin /usr/local/bin; do
  if [[ -d "$bin_dir" && ":$PATH:" != *":$bin_dir:"* ]]; then
    PATH="$bin_dir:$PATH"
  fi
done
export PATH

upsert_managed_block() {
  local path="$1"
  local name="$2"
  local body="$3"
  mkdir -p "$(dirname "$path")"
  touch "$path"
  python3 - "$path" "$name" "$body" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
name = sys.argv[2]
body = sys.argv[3].rstrip("\n")
start = f"# BEGIN ai-configs {name}"
end = f"# END ai-configs {name}"
block = f"{start}\n{body}\n{end}"
text = path.read_text()
if start in text:
    before, remainder = text.split(start, 1)
    if end not in remainder:
        raise SystemExit(f"managed block in {path} is missing {end!r}")
    _, after = remainder.split(end, 1)
    text = before.rstrip("\n") + "\n\n" + block + after
else:
    text = text.rstrip("\n") + ("\n\n" if text.strip() else "") + block + "\n"
path.write_text(text)
PY
}

ensure_clipssh_alias() {
  local name="$1"
  local target="$2"
  local alias_dir="$HOME/.clipssh"
  local alias_file="$alias_dir/aliases"
  mkdir -p "$alias_dir"
  touch "$alias_file"
  python3 - "$alias_file" "$name" "$target" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
name, target = sys.argv[2:]
lines = [line for line in path.read_text().splitlines() if not line.startswith(f"{name}=")]
lines.append(f"{name}={target}")
path.write_text("\n".join(lines) + "\n")
PY
}

configure_herdr_notifications() {
  local config="$HOME/.config/herdr/config.toml"
  [[ -f "$config" ]] || return 0

  python3 - "$config" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
text = path.read_text()
section = re.search(r"(?ms)^[ \t]*\[ui\.toast\][ \t]*$.*?(?=^[ \t]*\[|\Z)", text)
if section:
    current = section.group(0)
    if re.search(r"(?m)^\s*delivery\s*=", current):
        updated = re.sub(r'(?m)^\s*delivery\s*=.*$', 'delivery = "terminal"', current)
    else:
        updated = current.rstrip() + '\ndelivery = "terminal"\n\n'
    text = text[:section.start()] + updated + text[section.end():]
else:
    text = text.rstrip() + '\n\n[ui.toast]\ndelivery = "terminal"\n'
path.write_text(text)
PY

}

install_herdr_kitty_status() {
  command -v herdr >/dev/null 2>&1 || return 0
  [[ "${KITTY_WORKFLOW_SKIP_STATUS_PLUGIN:-0}" != 1 ]] || return 0

  # Keep the external integration immutable and auditable. The plugin is linked
  # from a commit-addressed cache instead of executing files from a mutable
  # upstream branch.
  local status_ref="${HERDR_KITTY_STATUS_REF:-2f250e23e6fc9d5b24ea036de3a00801004d5c3b}"
  [[ "$status_ref" =~ ^[0-9a-f]{40}$ ]] || {
    echo "Error: HERDR_KITTY_STATUS_REF must be a full Git commit SHA." >&2
    return 1
  }
  local cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/ai-configs/tools/herdr-kitty-status/$status_ref"
  local installer="$cache_dir/install.sh"

  if [[ ! -x "$installer" ]]; then
    command -v curl >/dev/null 2>&1 || {
      echo "Warning: curl is unavailable; Herdr Kitty status integration was not refreshed." >&2
      command -v herdr-kitty >/dev/null 2>&1 && return 0
      return 1
    }
    local temporary
    temporary="$(mktemp -d "${TMPDIR:-/tmp}/herdr-kitty-status.XXXXXX")"
    if ! curl -fsSL "https://github.com/adnichols/herdr-kitty-status/archive/$status_ref.tar.gz" | \
      tar --strip-components=1 -xz -C "$temporary"; then
      rm -rf "$temporary"
      echo "Warning: could not download pinned Herdr Kitty status commit $status_ref." >&2
      command -v herdr-kitty >/dev/null 2>&1 && return 0
      return 1
    fi
    mkdir -p "$(dirname "$cache_dir")"
    rm -rf "$cache_dir"
    mv "$temporary" "$cache_dir"
  fi

  local status=0
  if [[ "${KITTY_WORKFLOW_OS:-$(uname -s)}" == Darwin ]] && command -v kitty >/dev/null 2>&1; then
    bash "$installer" --local "$cache_dir" || status=$?
  else
    bash "$installer" --plugin-only --local "$cache_dir" || status=$?
  fi

  if (( status != 0 )); then
    echo "Warning: Herdr Kitty status integration refresh failed." >&2
    command -v herdr-kitty >/dev/null 2>&1 && return 0
    return "$status"
  fi
}

install_macos_kitty_workflow() {
  command -v kitty >/dev/null 2>&1 || {
    echo "Kitty is not installed; skipping local Kitty client files."
    return 0
  }

  if ! command -v pngpaste >/dev/null 2>&1; then
    if [[ "${KITTY_WORKFLOW_SKIP_PACKAGES:-0}" == 1 ]]; then
      echo "pngpaste is missing; package installation skipped by environment." >&2
    elif command -v brew >/dev/null 2>&1; then
      echo "Installing pngpaste..."
      brew install pngpaste
    else
      echo "Error: pngpaste is required and Homebrew is unavailable." >&2
      return 1
    fi
  fi

  mkdir -p "$HOME/.local/bin" "$HOME/.config/kitty" "$HOME/.config/ai-configs"
  install -m 0755 "$REPO_ROOT/scripts/clipssh" "$HOME/.local/bin/clipssh"
  install -m 0755 "$REPO_ROOT/scripts/kitty-paste-image-to-ssh" "$HOME/.local/bin/kitty-paste-image-to-ssh"
  install -m 0644 "$SOURCE_DIR/remote-workflow.conf" "$HOME/.config/kitty/ai-configs-remote-workflow.conf"
  install -m 0644 "$SOURCE_DIR/remote-workflow-ssh.conf" "$HOME/.config/kitty/ai-configs-remote-workflow-ssh.conf"
  install -m 0644 "$SOURCE_DIR/REMOTE-WORKFLOW.md" "$HOME/.config/kitty/REMOTE-WORKFLOW.md"
  install -m 0644 "$SOURCE_DIR/remote-workflow.zsh" "$HOME/.config/ai-configs/kitty-remote-workflow.zsh"

  upsert_managed_block "$HOME/.config/kitty/kitty.conf" "kitty remote workflow" \
    "include ai-configs-remote-workflow.conf"
  upsert_managed_block "$HOME/.config/kitty/ssh.conf" "kitty remote workflow" \
    "include ai-configs-remote-workflow-ssh.conf"
  upsert_managed_block "$HOME/.zshrc" "kitty remote workflow" \
    'source "$HOME/.config/ai-configs/kitty-remote-workflow.zsh"'

  ensure_clipssh_alias mbp anichols@mbp
  ensure_clipssh_alias dever anichols@dever
  echo "Kitty remote workflow installed locally."
}

configure_herdr_notifications
install_herdr_kitty_status
if [[ "${KITTY_WORKFLOW_OS:-$(uname -s)}" == Darwin ]]; then
  install_macos_kitty_workflow
fi
