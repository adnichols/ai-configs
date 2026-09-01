#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

TARGET_ROOT="$TMP_ROOT/home/.omp/agent"
SHARED_TARGET="$TMP_ROOT/home/.agents"
BIN_TARGET="$TMP_ROOT/home/.local/bin"
FAKE_BIN="$TMP_ROOT/bin"
PLUGIN_LOG="$TMP_ROOT/omp-plugin.log"
touch "$PLUGIN_LOG"
mkdir -p "$FAKE_BIN" "$TARGET_ROOT/agents" "$TARGET_ROOT/extensions" "$SHARED_TARGET/skills" "$BIN_TARGET"
cat > "$FAKE_BIN/omp" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$OMP_PLUGIN_LOG"
EOF
chmod +x "$FAKE_BIN/omp"
printf 'old-config\n' > "$TARGET_ROOT/config.yml"
printf 'old-guidance\n' > "$TARGET_ROOT/AGENTS.md"
printf 'old-oracle\n' > "$TARGET_ROOT/agents/oracle.md"
printf 'old-deepinfra\n' > "$TARGET_ROOT/extensions/deepinfra.ts"
printf 'user-owned\n' > "$TARGET_ROOT/agents/custom.md"
printf 'user-owned\n' > "$TARGET_ROOT/extensions/custom.ts"

OMP_CONFIG_TARGET="$TARGET_ROOT" OMP_SHARED_TARGET="$SHARED_TARGET" OMP_BIN_TARGET="$BIN_TARGET" \
  OMP_PLUGIN_LOG="$PLUGIN_LOG" PATH="$FAKE_BIN:$PATH" \
  bash "$REPO_ROOT/_omp/install.sh" >/dev/null

cmp -s "$REPO_ROOT/_omp/config.yml" "$TARGET_ROOT/config.yml"
cmp -s "$REPO_ROOT/_omp/models.yml" "$TARGET_ROOT/models.yml"
grep -q '^  - ~/.omp/agent/extensions/deepinfra.ts$' "$TARGET_ROOT/config.yml"
grep -q '^  - ~/.omp/agent/extensions/thinking-shortcuts.ts$' "$TARGET_ROOT/config.yml"
grep -q '^  - ~/.omp/agent/extensions/eval-no-file-writes.ts$' "$TARGET_ROOT/config.yml"
grep -q '^  - claude$' "$TARGET_ROOT/config.yml"
cmp -s "$REPO_ROOT/_omp/AGENTS.md" "$TARGET_ROOT/AGENTS.md"
cmp -s "$REPO_ROOT/_omp/agents/oracle.md" "$TARGET_ROOT/agents/oracle.md"
cmp -s "$REPO_ROOT/_omp/agents/reviewer.md" "$TARGET_ROOT/agents/reviewer.md"
cmp -s "$REPO_ROOT/_omp/agents/planner.md" "$TARGET_ROOT/agents/planner.md"
cmp -s "$REPO_ROOT/_omp/extensions/deepinfra.ts" "$TARGET_ROOT/extensions/deepinfra.ts"
cmp -s "$REPO_ROOT/_omp/extensions/herdr-omp-agent-state.ts" "$TARGET_ROOT/extensions/herdr-omp-agent-state.ts"
cmp -s "$REPO_ROOT/_omp/extensions/orca-agent-status.ts" "$TARGET_ROOT/extensions/orca-agent-status.ts"
cmp -s "$REPO_ROOT/_omp/extensions/orca-prefill.ts" "$TARGET_ROOT/extensions/orca-prefill.ts"
cmp -s "$REPO_ROOT/_omp/extensions/orca-titlebar-spinner.ts" "$TARGET_ROOT/extensions/orca-titlebar-spinner.ts"
cmp -s "$REPO_ROOT/_omp/extensions/thinking-shortcuts.ts" "$TARGET_ROOT/extensions/thinking-shortcuts.ts"
cmp -s "$REPO_ROOT/_omp/extensions/eval-no-file-writes.ts" "$TARGET_ROOT/extensions/eval-no-file-writes.ts"
grep -q '^model: "@Oracle"$' "$TARGET_ROOT/agents/oracle.md"
grep -q '^model: "@reviewer"$' "$TARGET_ROOT/agents/reviewer.md"
grep -q '^model: "@plan"$' "$TARGET_ROOT/agents/planner.md"
! grep -q '^thinking-level:' "$TARGET_ROOT/agents/oracle.md"
! grep -q '^thinking-level:' "$TARGET_ROOT/agents/reviewer.md"
! grep -q '^thinking-level:' "$TARGET_ROOT/agents/planner.md"
grep -q 'old-config' "$TARGET_ROOT/config.yml.before-ai-configs"
grep -q 'old-guidance' "$TARGET_ROOT/AGENTS.md.before-ai-configs"
grep -q 'old-oracle' "$TARGET_ROOT/agents/oracle.md.before-ai-configs"
grep -q 'old-deepinfra' "$TARGET_ROOT/extensions/deepinfra.ts.before-ai-configs"
grep -q 'user-owned' "$TARGET_ROOT/agents/custom.md"
grep -q 'user-owned' "$TARGET_ROOT/extensions/custom.ts"
if grep -q '@dietrichgebert/ponytail' "$REPO_ROOT/_omp/install.sh"; then
  printf 'installer still references ponytail\n' >&2
  exit 1
fi
if grep -qi 'ponytail' "$PLUGIN_LOG"; then
  printf 'plugin log still mentions ponytail\n' >&2
  cat "$PLUGIN_LOG" >&2
  exit 1
fi
cmp -s "$REPO_ROOT/_adn/manifest.json" "$SHARED_TARGET/adn/manifest.json"
cmp -s "$REPO_ROOT/_adn/agents/architect-grok.md" "$TARGET_ROOT/agents/architect-grok.md"
cmp -s "$REPO_ROOT/_adn/agents/architect-kimi.md" "$TARGET_ROOT/agents/architect-kimi.md"
cmp -s "$REPO_ROOT/_adn/agents/reviewer-kimi.md" "$TARGET_ROOT/agents/reviewer-kimi.md"
test ! -e "$TARGET_ROOT/extensions/adn-mode.ts"
test ! -e "$TARGET_ROOT/extensions/adn-mode.generated.ts"
test ! -e "$TARGET_ROOT/adn/generation.json"
test -f "$TARGET_ROOT/modelRoles.json"
grep -q '"architect-grok": "xai-oauth/grok-4.6:high"' "$TARGET_ROOT/modelRoles.json"
test -L "$TARGET_ROOT/skills/principle-laziness-protocol"
cat >> "$TARGET_ROOT/models.yml" <<'EOF'
  custom:
    auth: none
EOF
cp "$TARGET_ROOT/models.yml" "$TMP_ROOT/user-models.yml"

OMP_CONFIG_TARGET="$TARGET_ROOT" OMP_SHARED_TARGET="$SHARED_TARGET" OMP_BIN_TARGET="$BIN_TARGET" \
  OMP_PLUGIN_LOG="$PLUGIN_LOG" PATH="$FAKE_BIN:$PATH" \
  bash "$REPO_ROOT/_omp/install.sh" >/dev/null
grep -q 'old-config' "$TARGET_ROOT/config.yml.before-ai-configs"
grep -q 'old-guidance' "$TARGET_ROOT/AGENTS.md.before-ai-configs"
grep -q 'old-oracle' "$TARGET_ROOT/agents/oracle.md.before-ai-configs"
cmp -s "$TMP_ROOT/user-models.yml" "$TARGET_ROOT/models.yml"
if [[ -s "$PLUGIN_LOG" ]]; then
  printf 'expected empty plugin log\n' >&2
  cat "$PLUGIN_LOG" >&2
  exit 1
fi

printf 'OMP config installer tests passed.\n'
