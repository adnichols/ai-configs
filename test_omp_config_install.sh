#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

TARGET_ROOT="$TMP_ROOT/home/.omp/agent"
FAKE_BIN="$TMP_ROOT/bin"
PLUGIN_LOG="$TMP_ROOT/omp-plugin.log"
mkdir -p "$FAKE_BIN" "$TARGET_ROOT/agents" "$TARGET_ROOT/extensions"
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

OMP_CONFIG_TARGET="$TARGET_ROOT" OMP_PLUGIN_LOG="$PLUGIN_LOG" PATH="$FAKE_BIN:$PATH" \
  bash "$REPO_ROOT/_omp/install.sh" >/dev/null

cmp -s "$REPO_ROOT/_omp/config.yml" "$TARGET_ROOT/config.yml"
grep -q '^  - ~/.omp/agent/extensions/deepinfra.ts$' "$TARGET_ROOT/config.yml"
grep -q '^  - ~/.omp/agent/extensions/thinking-shortcuts.ts$' "$TARGET_ROOT/config.yml"
grep -q '^  - claude$' "$TARGET_ROOT/config.yml"
cmp -s "$REPO_ROOT/_omp/AGENTS.md" "$TARGET_ROOT/AGENTS.md"
cmp -s "$REPO_ROOT/_omp/agents/oracle.md" "$TARGET_ROOT/agents/oracle.md"
cmp -s "$REPO_ROOT/_omp/agents/reviewer.md" "$TARGET_ROOT/agents/reviewer.md"
cmp -s "$REPO_ROOT/_omp/extensions/deepinfra.ts" "$TARGET_ROOT/extensions/deepinfra.ts"
cmp -s "$REPO_ROOT/_omp/extensions/herdr-omp-agent-state.ts" "$TARGET_ROOT/extensions/herdr-omp-agent-state.ts"
cmp -s "$REPO_ROOT/_omp/extensions/orca-agent-status.ts" "$TARGET_ROOT/extensions/orca-agent-status.ts"
cmp -s "$REPO_ROOT/_omp/extensions/orca-prefill.ts" "$TARGET_ROOT/extensions/orca-prefill.ts"
cmp -s "$REPO_ROOT/_omp/extensions/orca-titlebar-spinner.ts" "$TARGET_ROOT/extensions/orca-titlebar-spinner.ts"
cmp -s "$REPO_ROOT/_omp/extensions/thinking-shortcuts.ts" "$TARGET_ROOT/extensions/thinking-shortcuts.ts"
grep -q '^model: "@Oracle"$' "$TARGET_ROOT/agents/oracle.md"
grep -q '^model: "@reviewer"$' "$TARGET_ROOT/agents/reviewer.md"
! grep -q '^thinking-level:' "$TARGET_ROOT/agents/oracle.md"
! grep -q '^thinking-level:' "$TARGET_ROOT/agents/reviewer.md"
grep -q 'old-config' "$TARGET_ROOT/config.yml.before-ai-configs"
grep -q 'old-guidance' "$TARGET_ROOT/AGENTS.md.before-ai-configs"
grep -q 'old-oracle' "$TARGET_ROOT/agents/oracle.md.before-ai-configs"
grep -q 'old-deepinfra' "$TARGET_ROOT/extensions/deepinfra.ts.before-ai-configs"
grep -q 'user-owned' "$TARGET_ROOT/agents/custom.md"
grep -q 'user-owned' "$TARGET_ROOT/extensions/custom.ts"
grep -q '^plugin install @dietrichgebert/ponytail$' "$PLUGIN_LOG"

OMP_CONFIG_TARGET="$TARGET_ROOT" OMP_PLUGIN_LOG="$PLUGIN_LOG" PATH="$FAKE_BIN:$PATH" \
  bash "$REPO_ROOT/_omp/install.sh" >/dev/null
grep -q 'old-config' "$TARGET_ROOT/config.yml.before-ai-configs"
grep -q 'old-guidance' "$TARGET_ROOT/AGENTS.md.before-ai-configs"
grep -q 'old-oracle' "$TARGET_ROOT/agents/oracle.md.before-ai-configs"
[[ "$(wc -l < "$PLUGIN_LOG")" -eq 2 ]]

printf 'OMP config installer tests passed.\n'
