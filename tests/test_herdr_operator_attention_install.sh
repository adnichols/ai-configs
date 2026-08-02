#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP_ROOT="$(mktemp -d)"
trap 'rm -rf "$TMP_ROOT"' EXIT
mkdir -p "$TMP_ROOT/home" "$TMP_ROOT/bin"

# Shared-skill installation may invoke npx for package-backed skills. The helper
# install itself is repo-local, so keep this contract test offline and deterministic.
cat >"$TMP_ROOT/bin/npx" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
capture=false
for arg in "$@"; do
  if [[ "$arg" == "--skill" ]]; then capture=true; continue; fi
  if [[ "$arg" == "-y" ]]; then capture=false; continue; fi
  if [[ "$capture" == true ]]; then
    mkdir -p "$HOME/.agents/skills/$arg"
    printf -- '---\nname: %s\ndescription: test fixture\n---\n' "$arg" >"$HOME/.agents/skills/$arg/SKILL.md"
  fi
done
exit 0
SH
chmod +x "$TMP_ROOT/bin/npx"

HOME="$TMP_ROOT/home" PATH="$TMP_ROOT/bin:$PATH" bash "$ROOT/install.sh" --skills >/dev/null

script="$TMP_ROOT/home/.agents/scripts/herdr-operator-attention"
link="$TMP_ROOT/home/.local/bin/herdr-operator-attention"
[[ -x "$script" ]]
[[ -x "$link" ]]
[[ -L "$link" ]]
[[ "$(readlink "$link")" == "$script" ]]
"$link" status --pane install-test | grep -Fxq '{"active":false}'

echo "ok - Herdr operator attention install"
