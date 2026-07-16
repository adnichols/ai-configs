#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"; ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [ -L "$HOME/.pi" ]; then
  echo "Error: transactional Pi review-stack installation requires ~/.pi to be a real directory, not a symlink, so the complete snapshot boundary is truthful. Replace the symlink with a real directory before installing." >&2
  exit 1
fi
for MANAGED_PI_PATH in "$HOME/.pi/agent" "$HOME/.pi/agent/prompts" "$HOME/.pi/agent/agents" "$HOME/.pi/agent/extensions" "$HOME/.pi/agent/models.json" "$HOME/.pi/agent/README.md" "$HOME/.pi/agent/APPEND_SYSTEM.md"; do
  if [ -L "$MANAGED_PI_PATH" ]; then
    echo "Error: transactional Pi review-stack installation refuses symlinks at managed ~/.pi paths because external targets are outside the rollback boundary: $MANAGED_PI_PATH" >&2
    exit 1
  fi
done
SNAPSHOT="$(mktemp -d)"; chmod 700 "$SNAPSHOT"
SKILLS=(codex-review-partner pre-pr-implementation-review reviewed-html-plan run-plan)

manifest() {
  python3 - "$HOME" "$@" <<'PY'
import hashlib,json,os,stat,sys
home=sys.argv[1]; paths=sys.argv[2:]; out={}
for raw in paths:
 p=os.path.join(home,raw); rows=[]
 if not os.path.lexists(p): out[raw]={'absent':True}; continue
 for base,dirs,files in os.walk(p,followlinks=False):
  for name in ['.']+sorted(dirs+files):
   q=base if name=='.' else os.path.join(base,name); rel=os.path.relpath(q,p); st=os.lstat(q); item={'path':rel,'mode':stat.S_IMODE(st.st_mode),'type':'dir' if stat.S_ISDIR(st.st_mode) else 'link' if stat.S_ISLNK(st.st_mode) else 'file'}
   if item['type']=='file': item['sha256']=hashlib.sha256(open(q,'rb').read()).hexdigest()
   if item['type']=='link': item['target']=os.readlink(q)
   rows.append(item)
 out[raw]={'absent':False,'rows':rows}
print(json.dumps(out,sort_keys=True))
PY
}

PATHS=(.pi .agents/skills/codex-review-partner .agents/skills/pre-pr-implementation-review .agents/skills/reviewed-html-plan .agents/skills/run-plan)
PARENT_METADATA="$SNAPSHOT/parent-metadata.json"
python3 - "$PARENT_METADATA" "$HOME/.agents" "$HOME/.agents/skills" <<'PY'
import json,os,stat,sys
out={}
for raw in sys.argv[2:]:
 if os.path.isdir(raw):
  resolved=os.path.realpath(raw);value=os.stat(resolved);out[resolved]={'mode':stat.S_IMODE(value.st_mode),'atime_ns':value.st_atime_ns,'mtime_ns':value.st_mtime_ns}
json.dump(out,open(sys.argv[1],'w'))
PY
AGENTS_WAS_ABSENT=false; SKILLS_PARENT_WAS_ABSENT=false
[ -e "$HOME/.agents" ] || AGENTS_WAS_ABSENT=true
[ -e "$HOME/.agents/skills" ] || SKILLS_PARENT_WAS_ABSENT=true
BEFORE="$(manifest "${PATHS[@]}")"; printf '%s\n' "$BEFORE" >"$SNAPSHOT/manifest.json"
for rel in "${PATHS[@]}"; do
  if [ -e "$HOME/$rel" ] || [ -L "$HOME/$rel" ]; then mkdir -p "$SNAPSHOT/$(dirname "$rel")"; cp -a "$HOME/$rel" "$SNAPSHOT/$rel"; else mkdir -p "$SNAPSHOT/absent/$(dirname "$rel")"; : >"$SNAPSHOT/absent/$rel"; fi
done

restore() {
  local rel after
  for rel in "${PATHS[@]}"; do rm -rf "$HOME/$rel"; if [ -e "$SNAPSHOT/$rel" ] || [ -L "$SNAPSHOT/$rel" ]; then mkdir -p "$HOME/$(dirname "$rel")"; cp -a "$SNAPSHOT/$rel" "$HOME/$rel"; fi; done
  if [ "$SKILLS_PARENT_WAS_ABSENT" = true ]; then rmdir "$HOME/.agents/skills" 2>/dev/null || true; fi
  if [ "$AGENTS_WAS_ABSENT" = true ]; then rmdir "$HOME/.agents" 2>/dev/null || true; fi
  python3 - "$PARENT_METADATA" <<'PY'
import json,os,sys
for raw,value in json.load(open(sys.argv[1])).items():
 if os.path.isdir(raw): os.chmod(raw,value['mode']);os.utime(raw,ns=(value['atime_ns'],value['mtime_ns']))
PY
  after="$(manifest "${PATHS[@]}")"
  [ "$after" = "$BEFORE" ] || { echo "Rollback manifest mismatch; snapshot retained at $SNAPSHOT" >&2; return 1; }
  python3 - "$PARENT_METADATA" <<'PY'
import json,os,sys
for raw,value in json.load(open(sys.argv[1])).items():
 if os.path.isdir(raw): os.chmod(raw,value['mode']);os.utime(raw,ns=(value['atime_ns'],value['mtime_ns']))
PY
  rm -rf "$SNAPSHOT"
}
failpoint() { [ "${PI_REVIEW_STACK_FAILPOINT:-}" != "$1" ] || { echo "Triggered failpoint: $1" >&2; return 1; }; }
on_error() { status=$?; trap - ERR INT TERM; restore || true; exit "$status"; }
on_int() { trap - ERR INT TERM; restore || true; exit 130; }
on_term() { trap - ERR INT TERM; restore || true; exit 143; }
trap on_error ERR
trap on_int INT
trap on_term TERM

bash "$ROOT/install.sh" --pi-review-stack
if [ -n "${PI_REVIEW_STACK_TEST_PAUSE_MARKER:-}" ]; then
  : >"$PI_REVIEW_STACK_TEST_PAUSE_MARKER"
  while [ ! -e "${PI_REVIEW_STACK_TEST_RESUME_MARKER:-$SNAPSHOT/resume}" ]; do sleep 0.02; done
fi
failpoint after-install
bash "$ROOT/scripts/verify-pi-install.sh" --scope pi-review-stack --check-only
failpoint after-verify
diff -qr "$ROOT/_pi/extensions/codex-review" "$HOME/.pi/agent/extensions/codex-review" >/dev/null
for skill in "${SKILLS[@]}"; do diff -qr "$ROOT/skills/$skill" "$HOME/.agents/skills/$skill" >/dev/null; done
failpoint after-parity

launcher="$HOME/.agents/skills/codex-review-partner/scripts/run-review.sh"; cp "$launcher" "$SNAPSHOT/real-launcher"; cp "$ROOT/_pi/extensions/codex-review/tests/fixtures/fake_launcher.py" "$launcher"; chmod 755 "$launcher"
PI_REVIEW_STACK_TEST_HOME="$HOME" node --test "$ROOT/_pi/extensions/codex-review/tests/installed-host-notification.test.mjs"
cp "$SNAPSHOT/real-launcher" "$launcher"; chmod 755 "$launcher"
failpoint after-host
bash "$ROOT/scripts/verify-pi-install.sh" --scope pi-review-stack --check-only
trap - ERR INT TERM
python3 - "$PARENT_METADATA" <<'PY'
import json,os,sys
for raw,value in json.load(open(sys.argv[1])).items():
 if os.path.isdir(raw): os.chmod(raw,value['mode']);os.utime(raw,ns=(value['atime_ns'],value['mtime_ns']))
PY
rm -rf "$SNAPSHOT"
echo "Transactional Pi review-stack installation committed."
