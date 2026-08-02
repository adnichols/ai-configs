#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SOURCE_DIR/.." && pwd)"

if [[ "${HSP_WORKFLOW_OS:-$(uname -s)}" != Darwin ]]; then
  echo "Hammerspoon image-paste workflow is macOS-only; skipping."
  exit 0
fi

if [[ ! -d /Applications/Hammerspoon.app && ! -d "$HOME/Applications/Hammerspoon.app" ]]; then
  if [[ "${HSP_WORKFLOW_SKIP_PACKAGES:-0}" == 1 ]]; then
    echo "Hammerspoon is not installed; package installation skipped by environment." >&2
  elif command -v brew >/dev/null 2>&1; then
    echo "Installing Hammerspoon..."
    brew install --cask hammerspoon
  else
    echo "Error: Hammerspoon is required and Homebrew is unavailable." >&2
    exit 1
  fi
fi

if ! command -v pngpaste >/dev/null 2>&1; then
  if [[ "${HSP_WORKFLOW_SKIP_PACKAGES:-0}" == 1 ]]; then
    echo "Error: pngpaste is required; package installation skipped by environment." >&2
    exit 1
  elif command -v brew >/dev/null 2>&1; then
    echo "Installing pngpaste..."
    brew install pngpaste
  else
    echo "Error: pngpaste is required and Homebrew is unavailable." >&2
    exit 1
  fi
fi

mkdir -p "$HOME/.local/bin" "$HOME/.hammerspoon"
install -m 0755 "$REPO_ROOT/scripts/remote-image-paste" "$HOME/.local/bin/remote-image-paste"

python3 - "$HOME/.hammerspoon/init.lua" "$SOURCE_DIR/init.lua" <<'PY'
from pathlib import Path
import sys

target = Path(sys.argv[1])
source = Path(sys.argv[2])
body = source.read_text().strip()
start = "-- BEGIN ai-configs remote image paste"
end = "-- END ai-configs remote image paste"
block = f"{start}\n{body}\n{end}"
text = target.read_text() if target.exists() else ""

legacy = text.strip()
legacy_signature = 'local remoteImagePaste = os.getenv("HOME") .. "/.local/bin/remote-image-paste"'
legacy_config = (
    legacy.startswith("-- Cmd+Shift+V uploads the current local clipboard image")
    and legacy_signature in legacy
    and legacy.endswith("remoteImagePasteTap:start()")
)

if start in text:
    before, remainder = text.split(start, 1)
    if end not in remainder:
        raise SystemExit(f"managed block in {target} is missing {end!r}")
    _, after = remainder.split(end, 1)
    text = before.rstrip() + "\n\n" + block + after
elif legacy == body or legacy_config:
    # Adopt the prior standalone configuration without creating duplicate taps.
    text = block + "\n"
else:
    text = text.rstrip() + ("\n\n" if text.strip() else "") + block + "\n"

target.write_text(text)
PY

echo "Hammerspoon terminal-only image-paste workflow installed locally."
