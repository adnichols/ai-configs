#!/usr/bin/env bash
set -euo pipefail

# Apply the captured Pi scoped models (enabledModels) to local and remote hosts'
# ~/.pi/agent/settings.json, preserving every other settings key.
#
# The captured list lives in _pi/scoped-models.json. The normal ai-configs Pi
# install intentionally clears enabledModels so Pi shows the live catalog; this
# script is the explicit opt-in path to pin a managed scoped-model cycle (the
# set Ctrl+P cycles through) on this host and the remote hosts it deploys to.
#
# Deployment transport is SSH; each remote host merges the captured
# enabledModels into its own pi settings. Remote hosts are offline-safe by
# default (--best-effort); use --strict to fail on the first unreachable host.

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
CAPTURE="${PI_SCOPED_MODELS_CAPTURE:-$REPO_ROOT/_pi/scoped-models.json}"
REMOTE_HOSTS="${PI_SCOPED_MODELS_REMOTE_HOSTS:-mbp dever thump}"
STRICT="${PI_SCOPED_MODELS_STRICT_REMOTE:-0}"
SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=8)

while (($#)); do
  case "$1" in
    --strict) STRICT=1; shift ;;
    --best-effort) STRICT=0; shift ;;
    --hosts)
      [[ $# -ge 2 ]] || { echo "--hosts requires a space-separated host list" >&2; exit 2; }
      REMOTE_HOSTS="$2"; shift 2
      ;;
    --capture)
      [[ $# -ge 2 ]] || { echo "--capture requires a path to a capture file" >&2; exit 2; }
      CAPTURE="$2"; shift 2
      ;;
    --help|-h)
      echo "Usage: $0 [--strict|--best-effort] [--hosts <list>] [--capture <path>]"
      exit 0
      ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ -f "$CAPTURE" ]] || { echo "Capture file not found: $CAPTURE" >&2; exit 2; }

if [[ "${PI_SCOPED_MODELS_SKIP_REMOTE:-0}" == 1 ]]; then
  echo "Remote Pi scoped-models deployment skipped by environment."
  exit 0
fi

# Extract the enabledModels list from the capture file as a single-line JSON
# string so it can be passed to remote hosts via the environment without
# quoting issues.
models_json="$(python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1]))["enabledModels"]))' "$CAPTURE")"

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

LOCAL_FULL="$(hostname)"
LOCAL_SHORT="$(hostname -s 2>/dev/null || echo "$LOCAL_FULL")"

# Apply the captured enabledModels to a host's own pi settings. Inline so the
# local and remote branches share identical merge semantics. Creates the file
# if missing and preserves all other keys; a host whose enabledModels already
# match is left untouched.
apply_models() {
  PI_SCOPED_MODELS_JSON="$models_json" python3 - <<'PY'
import json, os
raw = os.environ["PI_SCOPED_MODELS_JSON"]
models = json.loads(raw)
path = os.path.expanduser("~/.pi/agent/settings.json")
data = json.load(open(path)) if os.path.exists(path) else {}
if data.get("enabledModels") == models:
    print("  enabledModels already current")
else:
    data["enabledModels"] = models
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(json.dumps(data, indent=2) + "\n")
    print("  updated enabledModels")
PY
}

is_local() {
  local host="$1" hname
  hname="$(ssh -G "$host" 2>/dev/null | awk '/^hostname /{print $2; exit}')"
  [[ -z "$hname" \
     || "$hname" == "$LOCAL_FULL" \
     || "$hname" == "$LOCAL_SHORT" \
     || "$hname" == "$LOCAL_SHORT.local" ]]
}

failures=()
for host in "${hosts[@]}"; do
  echo "Syncing Pi scoped models on $host..."
  if is_local "$host"; then
    if apply_models; then
      echo "  $host Pi scoped models current."
    else
      exit_code=$?
      failures+=("$host")
      echo "  Warning: could not update Pi scoped models on $host (exit $exit_code)." >&2
    fi
  else
    if ssh "${SSH_OPTS[@]}" "$host" "PI_SCOPED_MODELS_JSON='$models_json' python3 -" <<'PY'
import json, os
raw = os.environ["PI_SCOPED_MODELS_JSON"]
models = json.loads(raw)
path = os.path.expanduser("~/.pi/agent/settings.json")
data = json.load(open(path)) if os.path.exists(path) else {}
if data.get("enabledModels") == models:
    print("  enabledModels already current")
else:
    data["enabledModels"] = models
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(json.dumps(data, indent=2) + "\n")
    print("  updated enabledModels")
PY
    then
      echo "  $host Pi scoped models current."
    else
      exit_code=$?
      failures+=("$host")
      echo "  Warning: could not update Pi scoped models on $host (exit $exit_code); it may be offline or misconfigured." >&2
    fi
  fi
done

if (( ${#failures[@]} > 0 )); then
  printf 'Pi scoped models were not applied to: %s\n' "${failures[*]}" >&2
  if [[ "$STRICT" == 1 ]]; then
    exit 1
  fi
fi
