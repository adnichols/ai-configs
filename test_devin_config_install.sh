#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

TARGET_ROOT="$TMP_ROOT/home/.config/devin"
mkdir -p "$TARGET_ROOT/agents" "$TARGET_ROOT/skills" "$TMP_ROOT/real-skill"
printf 'old-guidance\n' > "$TARGET_ROOT/AGENTS.md"
printf 'old-reviewer\n' > "$TARGET_ROOT/agents/reviewer.md"
printf 'user-owned\n' > "$TARGET_ROOT/agents/custom.md"
printf '{"hooks":{}}\n' > "$TARGET_ROOT/config.json"
printf 'user skill\n' > "$TMP_ROOT/real-skill/SKILL.md"
ln -s "$TMP_ROOT/real-skill" "$TARGET_ROOT/skills/user-skill"
ln -s "$TMP_ROOT/does-not-exist" "$TARGET_ROOT/skills/orchestration"

DEVIN_CONFIG_TARGET="$TARGET_ROOT" bash "$REPO_ROOT/_devin/install.sh" >/dev/null

cmp -s "$REPO_ROOT/_devin/AGENTS.md" "$TARGET_ROOT/AGENTS.md"
cmp -s "$REPO_ROOT/_devin/agents/oracle.md" "$TARGET_ROOT/agents/oracle.md"
cmp -s "$REPO_ROOT/_devin/agents/planner.md" "$TARGET_ROOT/agents/planner.md"
cmp -s "$REPO_ROOT/_devin/agents/reviewer.md" "$TARGET_ROOT/agents/reviewer.md"
cmp -s "$REPO_ROOT/_devin/agents/completeness.md" "$TARGET_ROOT/agents/completeness.md"
grep -q '^model: opus$' "$TARGET_ROOT/agents/oracle.md"
grep -q '^model: opus$' "$TARGET_ROOT/agents/completeness.md"
grep -q '^model: sonnet$' "$TARGET_ROOT/agents/reviewer.md"
grep -q '^model: sonnet$' "$TARGET_ROOT/agents/planner.md"
grep -q 'old-guidance' "$TARGET_ROOT/AGENTS.md.before-ai-configs"
grep -q 'old-reviewer' "$TARGET_ROOT/agents/reviewer.md.before-ai-configs"
grep -q 'user-owned' "$TARGET_ROOT/agents/custom.md"
grep -q '"hooks"' "$TARGET_ROOT/config.json"

# Dangling skill links are pruned into a timestamped backup root; valid user
# links are left alone.
test ! -e "$TARGET_ROOT/skills/orchestration"
test ! -L "$TARGET_ROOT/skills/orchestration"
pruned="$(find "$TMP_ROOT" -path '*before-ai-configs/*/skills/orchestration' -type l | head -n 1)"
test -n "$pruned"
test -L "$TARGET_ROOT/skills/user-skill"
test "$(readlink "$TARGET_ROOT/skills/user-skill")" = "$TMP_ROOT/real-skill"

# A second run is idempotent: managed content stays byte-identical and the
# original backups are not overwritten.
printf 'newer-user-edit\n' > "$TARGET_ROOT/AGENTS.md"
DEVIN_CONFIG_TARGET="$TARGET_ROOT" bash "$REPO_ROOT/_devin/install.sh" >/dev/null
cmp -s "$REPO_ROOT/_devin/AGENTS.md" "$TARGET_ROOT/AGENTS.md"
grep -q 'old-guidance' "$TARGET_ROOT/AGENTS.md.before-ai-configs"

printf 'Devin config installer tests passed.\n'
