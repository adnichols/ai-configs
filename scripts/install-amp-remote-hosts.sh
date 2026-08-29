#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE_HOSTS="${AMP_REMOTE_HOSTS:-${KITTY_REMOTE_HOSTS:-mbp dever thump}}"
STRICT="${AMP_CONFIG_STRICT_REMOTE:-${KITTY_WORKFLOW_STRICT_REMOTE:-0}}"

while (($#)); do
  case "$1" in
    --strict) STRICT=1; shift ;;
    --hosts) [[ $# -ge 2 ]] || { echo "--hosts requires a space-separated host list" >&2; exit 2; }; REMOTE_HOSTS="$2"; shift 2 ;;
    --help|-h) echo "Usage: $0 [--strict] [--hosts <list>]"; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ "${AMP_CONFIG_SKIP_REMOTE:-0}" == 1 ]]; then
  echo "Remote Amp config deployment skipped by environment."
  exit 0
fi

hosts=()
for raw_host in $REMOTE_HOSTS; do
  host="${raw_host#"${raw_host%%[![:space:]]*}"}"
  host="${host%"${host##*[![:space:]]}"}"
  [[ -n "$host" ]] || continue
  duplicate=false
  for existing in "${hosts[@]:-}"; do
    [[ "$existing" == "$host" ]] && duplicate=true
  done
  [[ "$duplicate" == true ]] || hosts+=("$host")
done

failures=()
for host in "${hosts[@]}"; do
  echo "Installing Amp config on $host..."
  if COPYFILE_DISABLE=1 tar --no-xattrs -C "$REPO_ROOT" -cf - amp | \
    ssh -o BatchMode=yes -o ConnectTimeout=8 "$host" \
      'tmp=$(mktemp -d); trap '\''rm -rf "$tmp"'\'' EXIT; tar -xf - -C "$tmp"; bash "$tmp/amp/install.sh"'; then
    echo "  $host Amp config is current."
  else
    exit_code=$?
    failures+=("$host")
    echo "  Warning: could not update Amp config on $host (exit $exit_code); it may be offline or misconfigured." >&2
  fi
done

if (( ${#failures[@]} > 0 )); then
  printf 'Amp config was not deployed to: %s\n' "${failures[*]}" >&2
  if [[ "$STRICT" == 1 ]]; then
    exit 1
  fi
fi
