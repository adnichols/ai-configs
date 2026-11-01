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
printf '{"auth":{"token":"keep-me"},"daemon":{"relay":{"enabled":true},"agentProfiles":[{"name":"omp","provider":"omp","model":"user-overridden"},{"id":"host-sol-id","name":"orchestrator-sol","provider":"omp","model":"old","color":"teal"}]},"agents":{"providers":{"myprovider":{"enabled":true}}}}\n' > "$PASEO_HOME/config.json"
mkdir -p "$SKILLS_A/paseo"
printf 'locally tuned\n' > "$SKILLS_A/paseo/SKILL.md"
printf '{"files":{}}\n' > "$SKILLS_A/paseo/.paseo-managed-files.json"
printf 'stale extra\n' > "$SKILLS_A/paseo/EXTRA.md"
mkdir -p "$SKILLS_B/paseo.before-ai-configs"
printf 'legacy backup\n' > "$SKILLS_B/paseo.before-ai-configs/SKILL.md"

run_install

profile_get() {
  json_get "$PASEO_HOME/config.json" "next(p for p in d['daemon']['agentProfiles'] if p['name'] == '$1').get('$2')"
}

# Managed: skills.selection, the omp-with-advisor provider, and the two
# orchestrator profiles. Other host profiles, providers, and relay stay.
test "$(json_get "$PASEO_HOME/config.json" "d['agents']['skills']['selection']['mode']")" = "custom"
test "$(json_get "$PASEO_HOME/config.json" "d['agents']['skills']['selection']['skills']")" = "[]"
test "$(json_get "$PASEO_HOME/config.json" "d['daemon']['relay']['enabled']")" = "True"
test "$(profile_get omp model)" = "user-overridden"
test "$(profile_get omp provider)" = "omp"
test "$(json_get "$PASEO_HOME/config.json" "[p['name'] for p in d['daemon']['agentProfiles']]")" = "['orchestrator-sol', 'orchestrator-opus', 'omp']"
# An orchestrator profile the host already had moves to the advisor launch
# entry but keeps its host id and host-only fields.
test "$(profile_get orchestrator-sol provider)" = "omp-with-advisor"
test "$(profile_get orchestrator-sol model)" = "openai-codex/gpt-6.1-sol"
test "$(profile_get orchestrator-sol id)" = "host-sol-id"
test "$(profile_get orchestrator-sol color)" = "teal"
# A profile new to the host arrives whole, with the managed id Paseo requires.
test "$(profile_get orchestrator-opus provider)" = "omp-with-advisor"
test "$(profile_get orchestrator-opus id)" = "agent_profile_mufjcgq5_um9p8m92zp"
test "$(json_get "$PASEO_HOME/config.json" "d['agents']['providers']['omp-with-advisor']")" = "{'extends': 'omp', 'label': 'OMP (advisor on)', 'command': ['omp', '--advisor']}"
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
  test -z "$(find "$root" -mindepth 1 -maxdepth 1 -type d -name '*.before-ai-configs' -print -quit)"
done
test ! -e "$SKILLS_A/paseo/EXTRA.md"
grep -q 'locally tuned' "$TMP_ROOT/home/.agents/.paseo-skill-backups/paseo/SKILL.md"
grep -q 'stale extra' "$TMP_ROOT/home/.agents/.paseo-skill-backups/paseo/EXTRA.md"
grep -q 'legacy backup' "$TMP_ROOT/home/.claude/.paseo-skill-backups/paseo/SKILL.md"
# Bot skills are not installed on a host where paseo-bots has never run.
test ! -e "$PASEO_HOME/plugin-data"

# The vendored routing contract keeps semantic Paseo state off computer-use.
grep -q 'Use the `paseo` CLI first' "$REPO_ROOT/_paseo/skills/paseo/SKILL.md"
grep -q 'Never use CUA, computer-use, screenshots, or desktop automation to control or inspect Paseo' "$REPO_ROOT/_paseo/skills/paseo/SKILL.md"
grep -q 'Never use computer-use, CUA, screenshots, or desktop automation to control or inspect Paseo' "$REPO_ROOT/_paseo/skills/paseo-help/SKILL.md"
grep -q 'An error from Wrangler, a build, a test, or another command shown in a Paseo terminal is not a Paseo product problem' "$REPO_ROOT/_paseo/skills/paseo-help/SKILL.md"

# --- Second install still does not clobber a host profile edit ---
python3 - "$PASEO_HOME/config.json" <<'EOF'
import json, sys
path = sys.argv[1]
d = json.load(open(path))
d["daemon"]["agentProfiles"].append({"name": "local-only", "provider": "codex", "model": "gpt-5.6"})
next(p for p in d["daemon"]["agentProfiles"] if p["name"] == "omp")["model"] = "still-host-owned"
next(p for p in d["daemon"]["agentProfiles"] if p["name"] == "orchestrator-opus")["provider"] = "omp"
json.dump(d, open(path, "w"))
EOF

run_install

test "$(profile_get omp model)" = "still-host-owned"
test "$(profile_get orchestrator-opus provider)" = "omp-with-advisor"
test "$(json_get "$PASEO_HOME/config.json" "[p['name'] for p in d['daemon']['agentProfiles']]")" = "['orchestrator-sol', 'orchestrator-opus', 'omp', 'local-only']"

# --- Bot skills install into the paseo-bots library once the plugin has run ---
BOT_SKILL="$PASEO_HOME/plugin-data/paseo-bots/library/skills/pr-merge-gates"
mkdir -p "$BOT_SKILL" "$PASEO_HOME/plugin-data/paseo-bots/journal"
printf 'bot-edited\n' > "$BOT_SKILL/SKILL.md"
printf -- '- 2026-10-01 | q | "w" | transient: x\n' > "$PASEO_HOME/plugin-data/paseo-bots/journal/aaron-decisions.md"
run_install
for file in SKILL.md gate-check.py ruling-check.py; do
  cmp -s "$REPO_ROOT/_paseo/bots/skills/pr-merge-gates/$file" "$BOT_SKILL/$file"
done
test -x "$BOT_SKILL/ruling-check.py"
test -x "$BOT_SKILL/gate-check.py"
grep -q 'bot-edited' "$PASEO_HOME/plugin-data/paseo-bots/library/.paseo-skill-backups/pr-merge-gates/SKILL.md"
# The journal is bot runtime state; the installer never writes it.
grep -q 'transient: x' "$PASEO_HOME/plugin-data/paseo-bots/journal/aaron-decisions.md"
# The installed checker resolves the journal beside the library.
python3 "$BOT_SKILL/ruling-check.py" | grep -q '1 ruling(s), 0 not processed'

# --- Idempotent: second run reports current, original backup untouched ---
output="$(PASEO_CONFIG_TARGET="$PASEO_HOME" PASEO_SKILL_TARGETS="$SKILLS_A" PASEO_SKIP_RELOAD=1 bash "$REPO_ROOT/_paseo/install.sh")"
echo "$output" | grep -q "already current"
grep -q 'keep-me' "$PASEO_HOME/config.json.before-ai-configs"
test "$(find "$PASEO_HOME" -name 'config.json.before-ai-configs' | wc -l | tr -d ' ')" = "1"

printf 'Paseo config installer tests passed.\n'
