#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

PASEO_HOME="$TMP_ROOT/home/.paseo"
SKILLS_A="$TMP_ROOT/home/.agents/skills"
SKILLS_B="$TMP_ROOT/home/.claude/skills"
SKILLS_C="$TMP_ROOT/home/.codex/skills"

run_install() {
  PASEO_CONFIG_TARGET="$PASEO_HOME" \
  PASEO_SKILL_TARGETS="$SKILLS_A $SKILLS_B $SKILLS_C" \
  PASEO_SKIP_RELOAD=1 \
    bash "$REPO_ROOT/_paseo/install.sh" >/dev/null
}

json_get() {
  python3 -c "import json,sys; d=json.load(open('$1')); print(eval(sys.argv[1]))" "$2"
}

# --- Fresh install: managed config lands, skills fan out to all roots ---
mkdir -p "$PASEO_HOME"
printf '{"auth":{"token":"keep-me"},"daemon":{"relay":{"enabled":true}},"agents":{"providers":{"myprovider":{"enabled":true}}}}\n' > "$PASEO_HOME/config.json"
mkdir -p "$SKILLS_A/paseo"
printf 'locally tuned\n' > "$SKILLS_A/paseo/SKILL.md"
printf '{"files":{}}\n' > "$SKILLS_A/paseo/.paseo-managed-files.json"
printf 'stale extra\n' > "$SKILLS_A/paseo/EXTRA.md"

run_install

# Managed keys applied
test "$(json_get "$PASEO_HOME/config.json" "d['daemon']['relay']['enabled']")" = "False"
test "$(json_get "$PASEO_HOME/config.json" "d['daemon']['agentProfiles'][0]['name']")" = "omp"
test "$(json_get "$PASEO_HOME/config.json" "d['agents']['providers']['omp']['additionalModels'][0]['isDefault']")" = "True"
test "$(json_get "$PASEO_HOME/config.json" "d['agents']['skills']['selection']['mode']")" = "custom"
# Unmanaged keys preserved
test "$(json_get "$PASEO_HOME/config.json" "d['auth']['token']")" = "keep-me"
test "$(json_get "$PASEO_HOME/config.json" "d['agents']['providers']['myprovider']['enabled']")" = "True"
# Config is private
test "$(stat -c '%a' "$PASEO_HOME/config.json")" = "600"
# First differing config backed up
grep -q 'keep-me' "$PASEO_HOME/config.json.before-ai-configs"

# Skills installed to every runtime root, tuned content wins, marker and
# stale files removed
for root in "$SKILLS_A" "$SKILLS_B" "$SKILLS_C"; do
  for skill in paseo paseo-advisor paseo-committee paseo-handoff paseo-help paseo-plugin; do
    cmp -s "$REPO_ROOT/_paseo/skills/$skill/SKILL.md" "$root/$skill/SKILL.md"
    test ! -e "$root/$skill/.paseo-managed-files.json"
  done
done
test ! -e "$SKILLS_A/paseo/EXTRA.md"

# --- Profile merge: local profiles survive, managed profiles update in place ---
python3 - "$PASEO_HOME/config.json" <<'EOF'
import json, sys
path = sys.argv[1]
d = json.load(open(path))
d["daemon"]["agentProfiles"].append({"name": "local-only", "provider": "codex", "model": "gpt-5.6"})
d["daemon"]["agentProfiles"][0]["model"] = "user-overridden"
json.dump(d, open(path, "w"))
EOF

run_install

test "$(json_get "$PASEO_HOME/config.json" "d['daemon']['agentProfiles'][0]['model']")" = "devin/swe-2"
test "$(json_get "$PASEO_HOME/config.json" "[p['name'] for p in d['daemon']['agentProfiles']]")" = "['omp', 'Devin', 'local-only']"

# --- Idempotent: second run reports current, original backup untouched ---
output="$(PASEO_CONFIG_TARGET="$PASEO_HOME" PASEO_SKILL_TARGETS="$SKILLS_A" PASEO_SKIP_RELOAD=1 bash "$REPO_ROOT/_paseo/install.sh")"
echo "$output" | grep -q "already current"
grep -q 'keep-me' "$PASEO_HOME/config.json.before-ai-configs"
test "$(find "$PASEO_HOME" -name 'config.json.before-ai-configs' | wc -l)" = "1"

printf 'Paseo config installer tests passed.\n'
