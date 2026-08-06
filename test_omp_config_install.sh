#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

TARGET_ROOT="$TMP_ROOT/home/.omp/agent"
mkdir -p "$TARGET_ROOT/agents"
printf 'old-config\n' > "$TARGET_ROOT/config.yml"
printf 'old-guidance\n' > "$TARGET_ROOT/AGENTS.md"
printf 'old-oracle\n' > "$TARGET_ROOT/agents/oracle.md"
printf 'user-owned\n' > "$TARGET_ROOT/agents/custom.md"

OMP_CONFIG_TARGET="$TARGET_ROOT" bash "$REPO_ROOT/_omp/install.sh" >/dev/null

cmp -s "$REPO_ROOT/_omp/config.yml" "$TARGET_ROOT/config.yml"
cmp -s "$REPO_ROOT/_omp/AGENTS.md" "$TARGET_ROOT/AGENTS.md"
cmp -s "$REPO_ROOT/_omp/agents/oracle.md" "$TARGET_ROOT/agents/oracle.md"
cmp -s "$REPO_ROOT/_omp/agents/reviewer.md" "$TARGET_ROOT/agents/reviewer.md"
grep -q '^model: "@Oracle"$' "$TARGET_ROOT/agents/oracle.md"
grep -q '^model: "@reviewer"$' "$TARGET_ROOT/agents/reviewer.md"
! grep -q '^thinking-level:' "$TARGET_ROOT/agents/oracle.md"
! grep -q '^thinking-level:' "$TARGET_ROOT/agents/reviewer.md"
grep -q 'old-config' "$TARGET_ROOT/config.yml.before-ai-configs"
grep -q 'old-guidance' "$TARGET_ROOT/AGENTS.md.before-ai-configs"
grep -q 'old-oracle' "$TARGET_ROOT/agents/oracle.md.before-ai-configs"
grep -q 'user-owned' "$TARGET_ROOT/agents/custom.md"

OMP_CONFIG_TARGET="$TARGET_ROOT" bash "$REPO_ROOT/_omp/install.sh" >/dev/null
grep -q 'old-config' "$TARGET_ROOT/config.yml.before-ai-configs"
grep -q 'old-guidance' "$TARGET_ROOT/AGENTS.md.before-ai-configs"
grep -q 'old-oracle' "$TARGET_ROOT/agents/oracle.md.before-ai-configs"

printf 'OMP config installer tests passed.\n'
