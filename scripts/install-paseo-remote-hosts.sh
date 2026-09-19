#!/usr/bin/env bash
# Streams the tracked _paseo bundle to remote hosts and installs it there,
# without relying on remote ai-configs checkouts being clean or current.
# The local host is skipped: install.sh already ran _paseo/install.sh locally.
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE_HOSTS="${PASEO_REMOTE_HOSTS:-mbp dever thump}"
STRICT="${PASEO_CONFIG_STRICT_REMOTE:-0}"

while (($#)); do
  case "$1" in
    --strict) STRICT=1; shift ;;
    --best-effort) STRICT=0; shift ;;
    --hosts) [[ $# -ge 2 ]] || { echo "--hosts requires a space-separated host list" >&2; exit 2; }; REMOTE_HOSTS="$2"; shift 2 ;;
    --help|-h) echo "Usage: $0 [--strict|--best-effort] [--hosts <list>]"; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [[ "${PASEO_CONFIG_SKIP_REMOTE:-0}" == 1 ]]; then
  echo "Remote Paseo config deployment skipped by environment."
  exit 0
fi

LOCAL_HOSTS="$(hostname 2>/dev/null) $(hostname -s 2>/dev/null)"

is_local_host() {
  local candidate="$1" known
  for known in $LOCAL_HOSTS; do
    [[ "$candidate" == "$known" ]] && return 0
  done
  return 1
}

hosts=()
for raw_host in $REMOTE_HOSTS; do
  host="${raw_host#"${raw_host%%[![:space:]]*}"}"
  host="${host%"${host##*[![:space:]]}"}"
  [[ -n "$host" ]] || continue
  is_local_host "$host" && continue
  duplicate=false
  for existing in "${hosts[@]:-}"; do
    [[ "$existing" == "$host" ]] && duplicate=true
  done
  [[ "$duplicate" == true ]] || hosts+=("$host")
done

failures=()
for host in "${hosts[@]}"; do
  echo "Installing Paseo config on $host..."
  if COPYFILE_DISABLE=1 tar --no-xattrs -C "$REPO_ROOT" -cf - _paseo | \
    ssh -o BatchMode=yes -o ConnectTimeout=8 "$host" \
      'tmp=$(mktemp -d); trap '\''rm -rf "$tmp"'\'' EXIT; tar -xf - -C "$tmp"; bash "$tmp/_paseo/install.sh"'; then
    echo "  $host Paseo config is current."
  else
    exit_code=$?
    failures+=("$host")
    echo "  Warning: could not update Paseo config on $host (exit $exit_code); it may be offline or misconfigured." >&2
  fi
done

if (( ${#failures[@]} > 0 )); then
  printf 'Paseo config was not deployed to: %s\n' "${failures[*]}" >&2
  if [[ "$STRICT" == 1 ]]; then
    exit 1
  fi
fi
