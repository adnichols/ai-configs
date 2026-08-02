#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
REMOTE_HOSTS="${KITTY_REMOTE_HOSTS:-mbp dever}"
STRICT="${KITTY_WORKFLOW_STRICT_REMOTE:-0}"
SUMMARY_JSON=""
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

while (($#)); do
  case "$1" in
    --strict) STRICT=1; shift ;;
    --summary-json) [[ $# -ge 2 ]] || { echo "--summary-json requires a path" >&2; exit 2; }; SUMMARY_JSON="$2"; shift 2 ;;
    --hosts) [[ $# -ge 2 ]] || { echo "--hosts requires a space-separated host list" >&2; exit 2; }; REMOTE_HOSTS="$2"; shift 2 ;;
    --help|-h) echo "Usage: $0 [--strict] [--hosts <list>] [--summary-json <path>]"; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

host_results=()
hosts=()
for raw_host in $REMOTE_HOSTS; do
  host="${raw_host#"${raw_host%%[![:space:]]*}"}"; host="${host%"${host##*[![:space:]]}"}"
  [[ -n "$host" ]] || continue
  duplicate=false
  for existing in "${hosts[@]:-}"; do [[ "$existing" == "$host" ]] && duplicate=true; done
  [[ "$duplicate" == true ]] || hosts+=("$host")
done
write_summary() {
  local status="$1" transport="$2" args hosts_json
  [[ -n "$SUMMARY_JSON" ]] || return 0
  hosts_json="$(printf '%s\n' "${host_results[@]}" | python3 -c 'import json,sys
rows=[]
for line in sys.stdin:
 line=line.rstrip("\n")
 if not line: continue
 host,status,cwd,exit_code,warning=line.split("|",4)
 rows.append({"host":host,"status":status,"cwd":cwd or None,"exitCode":None if exit_code=="" else int(exit_code),"warning":warning or None})
print(json.dumps(rows,separators=(",",":")))')"
  args=(python3 "$REPO_ROOT/scripts/pi_review_stack_contract.py" write-summary --output "$SUMMARY_JSON" --command remote-hosts --mode remote-kitty --status "$status" --started-at "$STARTED_AT" --cwd "$PWD" --repo-root "$REPO_ROOT" --rollback-status not_needed --transport-status "$transport" --hosts-json "$hosts_json")
  "${args[@]}"
}

if [[ "${KITTY_WORKFLOW_SKIP_REMOTE:-0}" == 1 ]]; then
  for host in "${hosts[@]}"; do host_results+=("$host|skipped|||deployment skipped by environment"); done
  write_summary success not_run
  echo "Remote Kitty workflow deployment skipped by environment."
  exit 0
fi

failures=()
for host in "${hosts[@]}"; do
  echo "Installing Kitty/Herdr remote workflow on $host..."
  remote_output=""
  if remote_output="$(COPYFILE_DISABLE=1 tar --no-xattrs -C "$REPO_ROOT" -cf - \
      herdr \
      kitty \
      _pi/agents \
      scripts/clipssh \
      scripts/kitty-paste-image-to-ssh \
      scripts/probe_pi_review_transport.py | \
    ssh -o BatchMode=yes -o ConnectTimeout=8 "$host" \
      'tmp=$(mktemp -d); trap '\''rm -rf "$tmp"'\'' EXIT; echo "__DEPLOY_CWD__=$tmp"; tar -xf - -C "$tmp"; cd "$tmp"; python3 scripts/probe_pi_review_transport.py --agent-dir "$HOME/.pi/agent" --agent-source-dir _pi/agents --target-checkout "$tmp" && bash herdr/install.sh && bash kitty/install.sh')"; then
    remote_cwd="$(printf '%s\n' "$remote_output" | awk -F= '/^__DEPLOY_CWD__=/{print substr($0,index($0,"=")+1); exit}')"
    printf '%s\n' "$remote_output" | grep -v '^__DEPLOY_CWD__=' || true
    host_results+=("$host|success|$remote_cwd|0|")
    echo "  $host is current (cwd $remote_cwd)."
  else
    exit_code=$?
    failures+=("$host")
    host_results+=("$host|failed||$exit_code|install or transport probe failed")
    echo "  Warning: could not update or probe $host; it may be offline or misconfigured." >&2
  fi
done

if (( ${#failures[@]} > 0 )); then
  printf 'Kitty remote workflow was not deployed to: %s\n' "${failures[*]}" >&2
  if [[ "$STRICT" == 1 ]]; then
    write_summary failed fail
    exit 1
  fi
  write_summary partial fail
  exit 0
fi
write_summary success pass
