#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT

FAKE_HOME="$TMP_ROOT/firstmate"
mkdir -p "$FAKE_HOME/bin" "$FAKE_HOME/config" "$FAKE_HOME/data"
: > "$FAKE_HOME/bin/fm-spawn.sh"
chmod +x "$FAKE_HOME/bin/fm-spawn.sh"
printf 'old-harness\n' > "$FAKE_HOME/config/crew-harness"
printf 'old-captain\n' > "$FAKE_HOME/data/captain.md"
printf 'user-owned\n' > "$FAKE_HOME/data/extra.md"

FIRSTMATE_HOME="$FAKE_HOME" bash "$REPO_ROOT/_firstmate/install.sh" >/dev/null

cmp -s "$REPO_ROOT/_firstmate/config/crew-dispatch.json" "$FAKE_HOME/config/crew-dispatch.json"
cmp -s "$REPO_ROOT/_firstmate/config/crew-harness" "$FAKE_HOME/config/crew-harness"
cmp -s "$REPO_ROOT/_firstmate/data/captain.md" "$FAKE_HOME/data/captain.md"
cmp -s "$REPO_ROOT/_firstmate/data/captain-shared.md" "$FAKE_HOME/data/captain-shared.md"
grep -q 'old-harness' "$FAKE_HOME/config/crew-harness.before-ai-configs"
grep -q 'old-captain' "$FAKE_HOME/data/captain.md.before-ai-configs"
grep -q 'user-owned' "$FAKE_HOME/data/extra.md"

FIRSTMATE_HOME="$FAKE_HOME" bash "$REPO_ROOT/_firstmate/install.sh" >/dev/null

grep -q 'old-harness' "$FAKE_HOME/config/crew-harness.before-ai-configs"
grep -q 'old-captain' "$FAKE_HOME/data/captain.md.before-ai-configs"
grep -q 'user-owned' "$FAKE_HOME/data/extra.md"

if FIRSTMATE_HOME="$TMP_ROOT/missing" bash "$REPO_ROOT/_firstmate/install.sh" >/dev/null 2>&1; then
  echo "expected missing dest to fail" >&2
  exit 1
fi

NO_SPAWN="$TMP_ROOT/no-spawn"
mkdir -p "$NO_SPAWN"
if FIRSTMATE_HOME="$NO_SPAWN" bash "$REPO_ROOT/_firstmate/install.sh" >/dev/null 2>&1; then
  echo "expected missing fm-spawn.sh to fail" >&2
  exit 1
fi

printf 'Firstmate config installer tests passed.\n'
