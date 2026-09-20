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

# --- Fresh install: skills fan out; host daemon config is preserved ---
mkdir -p "$PASEO_HOME"
printf '{"auth":{"token":"keep-me"},"daemon":{"relay":{"enabled":true},"agentProfiles":[{"name":"omp","provider":"omp","model":"user-overridden"}]},"agents":{"providers":{"myprovider":{"enabled":true}}}}\n' > "$PASEO_HOME/config.json"
mkdir -p "$SKILLS_A/paseo"
printf 'locally tuned\n' > "$SKILLS_A/paseo/SKILL.md"
printf '{"files":{}}\n' > "$SKILLS_A/paseo/.paseo-managed-files.json"
printf 'stale extra\n' > "$SKILLS_A/paseo/EXTRA.md"

run_install

# Only skills.selection is managed. Host profiles, providers, and relay stay.
test "$(json_get "$PASEO_HOME/config.json" "d['agents']['skills']['selection']['mode']")" = "custom"
test "$(json_get "$PASEO_HOME/config.json" "d['agents']['skills']['selection']['skills']")" = "[]"
test "$(json_get "$PASEO_HOME/config.json" "d['daemon']['relay']['enabled']")" = "True"
test "$(json_get "$PASEO_HOME/config.json" "d['daemon']['agentProfiles'][0]['name']")" = "omp"
test "$(json_get "$PASEO_HOME/config.json" "d['daemon']['agentProfiles'][0]['model']")" = "user-overridden"
test "$(json_get "$PASEO_HOME/config.json" "[p['name'] for p in d['daemon']['agentProfiles']]")" = "['omp']"
test "$(json_get "$PASEO_HOME/config.json" "d['agents']['providers']['myprovider']['enabled']")" = "True"
test "$(json_get "$PASEO_HOME/config.json" "'omp' in d['agents']['providers']")" = "False"
test "$(json_get "$PASEO_HOME/config.json" "d['auth']['token']")" = "keep-me"
test "$(python3 -c "import os; print(oct(os.stat(r'''$PASEO_HOME/config.json''').st_mode)[-3:])")" = "600"
grep -q 'keep-me' "$PASEO_HOME/config.json.before-ai-configs"
for root in "$SKILLS_A" "$SKILLS_B" "$SKILLS_C"; do
  for skill in paseo paseo-advisor paseo-committee paseo-handoff paseo-help paseo-plugin; do
    cmp -s "$REPO_ROOT/_paseo/skills/$skill/SKILL.md" "$root/$skill/SKILL.md"
    test ! -e "$root/$skill/.paseo-managed-files.json"
  done
done
test ! -e "$SKILLS_A/paseo/EXTRA.md"

# --- Second install still does not clobber a host profile edit ---
python3 - "$PASEO_HOME/config.json" <<'EOF'
import json, sys
path = sys.argv[1]
d = json.load(open(path))
d["daemon"]["agentProfiles"].append({"name": "local-only", "provider": "codex", "model": "gpt-5.6"})
d["daemon"]["agentProfiles"][0]["model"] = "still-host-owned"
json.dump(d, open(path, "w"))
EOF

run_install

test "$(json_get "$PASEO_HOME/config.json" "d['daemon']['agentProfiles'][0]['model']")" = "still-host-owned"
test "$(json_get "$PASEO_HOME/config.json" "[p['name'] for p in d['daemon']['agentProfiles']]")" = "['omp', 'local-only']"

# --- Idempotent: second run reports current, original backup untouched ---
output="$(PASEO_CONFIG_TARGET="$PASEO_HOME" PASEO_SKILL_TARGETS="$SKILLS_A" PASEO_SKIP_RELOAD=1 bash "$REPO_ROOT/_paseo/install.sh")"
echo "$output" | grep -q "already current"
grep -q 'keep-me' "$PASEO_HOME/config.json.before-ai-configs"
test "$(find "$PASEO_HOME" -name 'config.json.before-ai-configs' | wc -l | tr -d ' ')" = "1"

printf 'Paseo config installer tests passed.\n'
