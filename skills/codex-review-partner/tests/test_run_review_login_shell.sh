#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LAUNCHER="$SCRIPT_DIR/../scripts/run-review.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p "$TMP_DIR/bin"
cat > "$TMP_DIR/zsh" <<'EOF'
#!/bin/bash
set -euo pipefail
printf '%s\n' "$@" > "$LOGIN_SHELL_ARGS_FILE"
[[ "${1:-}" == "-l" ]]
[[ "${2:-}" == "-c" ]]
command_string="${3:-}"
shift 3
exec /bin/bash -c "$command_string" "$@"
EOF
chmod +x "$TMP_DIR/zsh"

cat > "$TMP_DIR/bin/codex" <<'EOF'
#!/bin/bash
set -euo pipefail
printf '%s\n' "$@" > "$CODEX_ARGS_FILE"
cat > "$CODEX_STDIN_FILE"
printf '%s\n' 'VERDICT: PASS_SCOPED' 'Fake Codex review body'
EOF
chmod +x "$TMP_DIR/bin/codex"

printf '%s\n' 'Review this bounded packet.' > "$TMP_DIR/input.md"
PATH="$TMP_DIR/bin:/usr/bin:/bin" \
SHELL="$TMP_DIR/zsh" \
LOGIN_SHELL_ARGS_FILE="$TMP_DIR/login-shell.args" \
CODEX_ARGS_FILE="$TMP_DIR/codex.args" \
CODEX_STDIN_FILE="$TMP_DIR/codex.stdin" \
  "$LAUNCHER" --mode implementation-review --input "$TMP_DIR/input.md" --cwd "$TMP_DIR" --output "$TMP_DIR/output.md"

grep -Fx -- '-l' "$TMP_DIR/login-shell.args" >/dev/null
grep -Fx -- '-c' "$TMP_DIR/login-shell.args" >/dev/null
grep -Fx -- 'exec codex "$@"' "$TMP_DIR/login-shell.args" >/dev/null
grep -Fx -- 'codex' "$TMP_DIR/login-shell.args" >/dev/null
grep -Fx -- 'exec' "$TMP_DIR/codex.args" >/dev/null
grep -Fx -- '-m' "$TMP_DIR/codex.args" >/dev/null
grep -F -- 'You are performing an implementation review.' "$TMP_DIR/codex.stdin" >/dev/null
grep -F -- 'Review this bounded packet.' "$TMP_DIR/codex.stdin" >/dev/null
grep -F -- 'VERDICT: PASS_SCOPED' "$TMP_DIR/output.md" >/dev/null

cp "$TMP_DIR/zsh" "$TMP_DIR/tcsh"
if PATH="$TMP_DIR/bin:/usr/bin:/bin" SHELL="$TMP_DIR/tcsh" \
  "$LAUNCHER" --mode implementation-review --input "$TMP_DIR/input.md" --cwd "$TMP_DIR" >"$TMP_DIR/unsupported.stdout" 2>"$TMP_DIR/unsupported.stderr"; then
  echo "Expected unsupported tcsh-style login shell to fail" >&2
  exit 1
fi
grep -F -- 'Configured login shell is unsupported for review automation' "$TMP_DIR/unsupported.stderr" >/dev/null

printf '%s\n' 'PASS: Codex review runs through supported login shell and rejects unsupported shells clearly'
