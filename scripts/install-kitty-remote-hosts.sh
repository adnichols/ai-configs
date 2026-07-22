#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE_HOSTS="${KITTY_REMOTE_HOSTS:-mbp dever}"

if [[ "${KITTY_WORKFLOW_SKIP_REMOTE:-0}" == 1 ]]; then
  echo "Remote Kitty workflow deployment skipped by environment."
  exit 0
fi

failures=()
for host in $REMOTE_HOSTS; do
  echo "Installing Kitty/Herdr remote workflow on $host..."
  if COPYFILE_DISABLE=1 tar --no-xattrs -C "$REPO_ROOT" -cf - \
      herdr \
      kitty \
      scripts/clipssh \
      scripts/kitty-paste-image-to-ssh | \
    ssh -o BatchMode=yes -o ConnectTimeout=8 "$host" \
      'tmp=$(mktemp -d); trap '\''rm -rf "$tmp"'\'' EXIT; tar -xf - -C "$tmp"; bash "$tmp/herdr/install.sh" && bash "$tmp/kitty/install.sh"'; then
    echo "  $host is current."
  else
    failures+=("$host")
    echo "  Warning: could not update $host; it may be offline." >&2
  fi
done

if (( ${#failures[@]} > 0 )); then
  printf 'Kitty remote workflow was not deployed to: %s\n' "${failures[*]}" >&2
  if [[ "${KITTY_WORKFLOW_STRICT_REMOTE:-0}" == 1 ]]; then
    exit 1
  fi
fi
