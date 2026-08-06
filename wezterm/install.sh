#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SOURCE_DIR/.." && pwd)"
# Keep these fixed paths aligned with the loader added to ~/.wezterm.lua and
# with the existing Kitty workflow's shell-fragment location.
CONFIG_DIR="$HOME/.config/wezterm"
ROOT_CONFIG="$HOME/.wezterm.lua"
MODULE_PATH="$CONFIG_DIR/ai-configs-remote-workflow.lua"
SHELL_FRAGMENT="$HOME/.config/ai-configs/wezterm-remote-workflow.zsh"

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

install_root_loader() {
  local loader
  loader=$(cat <<'LUA'
-- BEGIN ai-configs wezterm remote workflow
local ai_configs_wezterm = dofile(
  wezterm.home_dir .. '/.config/wezterm/ai-configs-remote-workflow.lua'
)
ai_configs_wezterm.apply(config, wezterm)
-- END ai-configs wezterm remote workflow
LUA
)

  if [[ ! -e "$ROOT_CONFIG" ]]; then
    cat > "$ROOT_CONFIG" <<LUA
local wezterm = require 'wezterm'
local config = wezterm.config_builder()

$loader

return config
LUA
    return
  fi

  python3 - "$ROOT_CONFIG" "$loader" <<'PY'
from pathlib import Path
import re
import sys

path = Path(sys.argv[1])
loader = sys.argv[2].rstrip("\n")
text = path.read_text()
start = "-- BEGIN ai-configs wezterm remote workflow"
end = "-- END ai-configs wezterm remote workflow"
if start in text:
    if end not in text.split(start, 1)[1]:
        raise SystemExit(f"managed block in {path} is missing {end!r}")
    before, remainder = text.split(start, 1)
    _, after = remainder.split(end, 1)
    path.write_text(before.rstrip() + "\n\n" + loader + after)
    raise SystemExit(0)

returns = list(re.finditer(r"(?m)^return\s+config\s*$", text))
if len(returns) != 1:
    raise SystemExit(
        f"Refusing to modify {path}: expected exactly one top-level `return config`. "
        "Add the ai-configs WezTerm loader immediately before the return statement."
    )
match = returns[0]
updated = text[:match.start()].rstrip() + "\n\n" + loader + "\n\n" + text[match.start():]
path.write_text(updated)
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

mkdir -p "$CONFIG_DIR" "$(dirname "$SHELL_FRAGMENT")" "$HOME/.local/bin"
install -m 0644 "$SOURCE_DIR/remote-workflow.lua" "$MODULE_PATH"
install -m 0644 "$SOURCE_DIR/remote-workflow.zsh" "$SHELL_FRAGMENT"
install -m 0755 "$SOURCE_DIR/wezterm-paste-image-to-ssh" "$HOME/.local/bin/wezterm-paste-image-to-ssh"
install -m 0755 "$REPO_ROOT/scripts/clipssh" "$HOME/.local/bin/clipssh"
install_root_loader
upsert_managed_block "$HOME/.zshrc" "wezterm remote workflow" \
  'source "$HOME/.config/ai-configs/wezterm-remote-workflow.zsh"'

ensure_clipssh_alias mbp anichols@mbp
ensure_clipssh_alias dever anichols@dever
ensure_clipssh_alias mbp14 anichols@mbp14
ensure_clipssh_alias mbp14-2 anichols@mbp14-2

echo "WezTerm remote workflow installed locally."
