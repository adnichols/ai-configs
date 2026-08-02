#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
CONTRACT="$ROOT/scripts/pi_review_stack_contract.py"
MANIFEST="$ROOT/scripts/pi-review-stack-managed-surfaces.json"
SUMMARY_JSON=""
SUMMARY_WRITTEN=false
STARTED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
EARLY_CACHE="$(mktemp -d)"
export PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX="$EARLY_CACHE/python" XDG_CACHE_HOME="$EARLY_CACHE/xdg"

finish_transaction_process() {
  local status=$?
  trap - EXIT
  if [[ "$status" -ne 0 && -n "$SUMMARY_JSON" && "$SUMMARY_WRITTEN" != true ]]; then
    python3 "$CONTRACT" write-summary --output "$SUMMARY_JSON" --command transaction --mode pi-review-stack --status failed --started-at "$STARTED_AT" --cwd "$PWD" --repo-root "$ROOT" --transport-status not_run --rollback-status not_needed || true
  fi
  rm -rf "$EARLY_CACHE"
  exit "$status"
}
trap finish_transaction_process EXIT

while (($#)); do
  case "$1" in
    --summary-json) [[ $# -ge 2 ]] || { echo "--summary-json requires a path" >&2; exit 2; }; SUMMARY_JSON="$2"; shift 2 ;;
    --help|-h) echo "Usage: $0 [--summary-json <path>]"; exit 0 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

python3 "$CONTRACT" validate --manifest "$MANIFEST" --repo-root "$ROOT" >/dev/null
if [ -L "$HOME/.pi" ]; then
  echo "Error: transactional Pi review-stack installation requires ~/.pi to be a real directory, not a symlink, so the complete snapshot boundary is truthful. Replace the symlink with a real directory before installing." >&2
  exit 1
fi
while IFS=$'\t' read -r _id _kind _source destination _mode _preserve boundary _target _entries; do
  if [ "$_kind" = symlink ]; then
    link_path="$HOME/$destination"
    if [ -L "$link_path" ] && ! python3 - "$link_path" "$HOME/$_target" <<'PY'
import pathlib, sys
raise SystemExit(0 if pathlib.Path(sys.argv[1]).resolve() == pathlib.Path(sys.argv[2]).resolve() else 1)
PY
    then
      echo "Error: transactional Pi review-stack installation refuses foreign symlinks at managed rollback paths: $link_path" >&2
      exit 1
    fi
    destination="$(dirname "$destination")"
    boundary="$(dirname "$boundary")"
  fi
  for row in "$HOME/$destination" "$HOME/$boundary"; do
    while [[ "$row" == "$HOME"/* && "$row" != "$HOME" ]]; do
      if [ -L "$row" ]; then
        echo "Error: transactional Pi review-stack installation refuses symlinks at managed rollback paths: $row" >&2
        exit 1
      fi
      row="$(dirname "$row")"
    done
  done
done < <(python3 "$CONTRACT" list --manifest "$MANIFEST" --repo-root "$ROOT" --scope pi-review-stack)

PATHS=(.pi)
while IFS=$'\t' read -r _id _kind _source _destination _mode _preserve boundary _target _entries; do
  found=false
  for existing in "${PATHS[@]}"; do
    [[ "$boundary" == "$existing" || "$boundary" == "$existing"/* ]] && found=true
  done
  [[ "$found" == true ]] || PATHS+=("$boundary")
done < <(python3 "$CONTRACT" list --manifest "$MANIFEST" --repo-root "$ROOT" --scope pi-review-stack)

for rel in "${PATHS[@]}"; do
  [[ "$rel" == .pi ]] && continue
  if [ -L "$HOME/$rel" ]; then
    echo "Error: transactional Pi review-stack installation refuses symlinks at managed rollback boundaries: $HOME/$rel" >&2
    exit 1
  fi
done

SNAPSHOT="$(mktemp -d)"; chmod 700 "$SNAPSHOT"
INNER_SUMMARY="$SNAPSHOT/install-summary.json"
TRANSPORT_STATUS="not_run"
TRANSPORT_REASON=""
mkdir -p "$SNAPSHOT/runtime-cache/python" "$SNAPSHOT/runtime-cache/xdg"

manifest() {
  python3 - "$HOME" "$@" <<'PY'
import hashlib,json,os,stat,sys
home=sys.argv[1]; paths=sys.argv[2:]; out={}
for raw in paths:
 p=os.path.join(home,raw); rows=[]
 if not os.path.lexists(p): out[raw]={'absent':True}; continue
 roots=[p] if os.path.islink(p) or not os.path.isdir(p) else []
 if not roots:
  for base,dirs,files in os.walk(p,followlinks=False):
   roots.extend([base]+[os.path.join(base,n) for n in sorted(dirs+files)])
 for q in roots:
  rel=os.path.relpath(q,p); st=os.lstat(q); item={'path':rel,'mode':stat.S_IMODE(st.st_mode),'type':'dir' if stat.S_ISDIR(st.st_mode) else 'link' if stat.S_ISLNK(st.st_mode) else 'file'}
  if item['type']=='file': item['sha256']=hashlib.sha256(open(q,'rb').read()).hexdigest()
  if item['type']=='link': item['target']=os.readlink(q)
  rows.append(item)
 out[raw]={'absent':False,'rows':rows}
print(json.dumps(out,sort_keys=True))
PY
}

PARENT_METADATA="$SNAPSHOT/parent-metadata.json"
PARENT_STATE="$SNAPSHOT/parent-state.json"
python3 - "$PARENT_METADATA" "$PARENT_STATE" "$HOME/.agents" "$HOME/.agents/skills" "$HOME/.agents/scripts" "$HOME/.local" "$HOME/.local/bin" <<'PY'
import json,os,stat,sys
metadata={}; state={}
for raw in sys.argv[3:]:
 state[raw]=os.path.lexists(raw)
 if os.path.isdir(raw):
  resolved=os.path.realpath(raw); value=os.stat(resolved); metadata[resolved]={'mode':stat.S_IMODE(value.st_mode),'atime_ns':value.st_atime_ns,'mtime_ns':value.st_mtime_ns}
json.dump(metadata,open(sys.argv[1],'w')); json.dump(state,open(sys.argv[2],'w'))
PY

BEFORE="$(manifest "${PATHS[@]}")"; printf '%s\n' "$BEFORE" >"$SNAPSHOT/manifest.json"
for rel in "${PATHS[@]}"; do
  if [ -e "$HOME/$rel" ] || [ -L "$HOME/$rel" ]; then mkdir -p "$SNAPSHOT/$(dirname "$rel")"; cp -a "$HOME/$rel" "$SNAPSHOT/$rel"; else mkdir -p "$SNAPSHOT/absent/$(dirname "$rel")"; : >"$SNAPSHOT/absent/$rel"; fi
done

restore_parent_metadata() {
  python3 - "$PARENT_METADATA" "$PARENT_STATE" <<'PY'
import json,os,sys
for raw,value in json.load(open(sys.argv[1])).items():
 if os.path.isdir(raw): os.chmod(raw,value['mode']);os.utime(raw,ns=(value['atime_ns'],value['mtime_ns']))
state=json.load(open(sys.argv[2]))
for raw in reversed(list(state)):
 if not state[raw] and os.path.isdir(raw):
  try: os.rmdir(raw)
  except OSError: pass
PY
}

restore() {
  local rel after
  for rel in "${PATHS[@]}"; do
    rm -rf "$HOME/$rel"
    if [ -e "$SNAPSHOT/$rel" ] || [ -L "$SNAPSHOT/$rel" ]; then mkdir -p "$HOME/$(dirname "$rel")"; cp -a "$SNAPSHOT/$rel" "$HOME/$rel"; fi
  done
  restore_parent_metadata
  after="$(manifest "${PATHS[@]}")"
  [ "$after" = "$BEFORE" ] || { echo "Rollback manifest mismatch; snapshot retained at $SNAPSHOT" >&2; return 1; }
  restore_parent_metadata
  rm -rf "$SNAPSHOT"
}

load_inner_transport() {
  [[ -f "$INNER_SUMMARY" ]] || return 0
  IFS=$'\t' read -r TRANSPORT_STATUS TRANSPORT_REASON < <(python3 - "$INNER_SUMMARY" <<'PY'
import json,sys
probe=json.load(open(sys.argv[1]))["transportProbe"]
print(probe["status"], probe.get("reason") or "", sep="\t")
PY
)
}

write_summary() {
  local status="$1" rollback_status="$2" snapshot_path="${3:-}"
  [ -n "$SUMMARY_JSON" ] || return 0
  local args=(python3 "$CONTRACT" write-summary --output "$SUMMARY_JSON" --command transaction --mode pi-review-stack --status "$status" --started-at "$STARTED_AT" --cwd "$PWD" --repo-root "$ROOT" --transport-status "$TRANSPORT_STATUS")
  [[ -z "$TRANSPORT_REASON" ]] || args+=(--transport-reason "$TRANSPORT_REASON")
  if [[ "$rollback_status" != not_needed ]]; then args+=(--rollback-attempted --rollback-status "$rollback_status"); else args+=(--rollback-status not_needed); fi
  [[ -z "$snapshot_path" ]] || args+=(--snapshot-path "$snapshot_path")
  if "${args[@]}"; then
    SUMMARY_WRITTEN=true
  else
    return 1
  fi
}

failpoint() { [ "${PI_REVIEW_STACK_FAILPOINT:-}" != "$1" ] || { echo "Triggered failpoint: $1" >&2; return 1; }; }
on_error() {
  local status=$?
  trap - ERR INT TERM
  load_inner_transport || true
  if restore; then write_summary rolled_back succeeded || true; else write_summary rollback_failed failed "$SNAPSHOT" || true; fi
  exit "$status"
}
on_int() { trap - ERR INT TERM; load_inner_transport || true; if restore; then write_summary rolled_back succeeded || true; else write_summary rollback_failed failed "$SNAPSHOT" || true; fi; exit 130; }
on_term() { trap - ERR INT TERM; load_inner_transport || true; if restore; then write_summary rolled_back succeeded || true; else write_summary rollback_failed failed "$SNAPSHOT" || true; fi; exit 143; }
trap on_error ERR
trap on_int INT
trap on_term TERM

bash "$ROOT/install.sh" --pi-review-stack --summary-json "$INNER_SUMMARY"
load_inner_transport
if [ -n "${PI_REVIEW_STACK_TEST_PAUSE_MARKER:-}" ]; then
  : >"$PI_REVIEW_STACK_TEST_PAUSE_MARKER"
  while [ ! -e "${PI_REVIEW_STACK_TEST_RESUME_MARKER:-$SNAPSHOT/resume}" ]; do sleep 0.02; done
fi
failpoint after-install
bash "$ROOT/scripts/verify-pi-install.sh" --scope pi-review-stack --check-only
failpoint after-verify
python3 "$CONTRACT" verify --manifest "$MANIFEST" --repo-root "$ROOT" --home "$HOME" --scope pi-review-stack >/dev/null
failpoint after-parity

review_scripts="$HOME/.agents/skills/codex-review-partner/scripts"
helper="$review_scripts/process_identity.py"; supervisor="$review_scripts/review_supervisor.py"
python3 - "$helper" "$supervisor" <<'PY'
import os,stat,sys
for file in sys.argv[1:]:
 mode=stat.S_IMODE(os.stat(file).st_mode)
 if not mode & stat.S_IRUSR or not mode & stat.S_IXUSR: raise SystemExit(f"installed review helper is not owner-readable/executable: {file} mode={oct(mode)}")
PY
python3 "$helper" snapshot --pid $$ >/dev/null
python3 "$supervisor" --preflight >/dev/null
failpoint after-preflight
failpoint after-host
bash "$ROOT/scripts/verify-pi-install.sh" --scope pi-review-stack --check-only
trap - ERR INT TERM
restore_parent_metadata
rm -rf "$SNAPSHOT"
write_summary success not_needed
echo "Transactional Pi review-stack installation committed."
