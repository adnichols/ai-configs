#!/usr/bin/env bash

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXTENSION_PATH="${EXTENSION_PATH:-$REPO_ROOT/_pi/extensions/thinking-shortcuts.ts}"
PI_BIN="${PI_BIN:-}"
if [ -z "$PI_BIN" ]; then
  PI_BIN="$(command -v pi || true)"
fi

if [ -z "$PI_BIN" ] || [ ! -x "$PI_BIN" ]; then
  echo "FAIL: pi is not available" >&2
  exit 1
fi
if ! command -v expect >/dev/null 2>&1; then
  echo "FAIL: expect is required for the Pi TUI shortcut test" >&2
  exit 1
fi
if [ ! -f "$EXTENSION_PATH" ]; then
  echo "FAIL: missing $EXTENSION_PATH" >&2
  exit 1
fi

expect_script="$(mktemp)"
transcript="$(mktemp)"
trap 'rm -f "$expect_script" "$transcript"' EXIT

cat >"$expect_script" <<'EXPECT'
set timeout 20
set pi_bin [lindex $argv 0]
set extension_path [lindex $argv 1]
set transcript_path [lindex $argv 2]
log_user 0
log_file -noappend $transcript_path
spawn env TERM=xterm-256color $pi_bin --offline --no-session --no-extensions --extension $extension_path --model openai-codex/gpt-5.6-terra --thinking medium
expect {
  -re {gpt-5\.6-terra} {}
  timeout { puts stderr "FAIL: Pi startup timed out"; exit 1 }
}
after 500
# Pi enables the Kitty keyboard protocol in TUI mode. Alt is modifier 3;
# period and comma are Unicode code points 46 and 44.
send -- "\033\[46;3u"
expect {
  -re {Thinking: high} {}
  timeout { puts stderr "FAIL: Alt+. did not increase thinking to high"; exit 2 }
}
send -- "\033\[44;3u"
expect {
  -re {Thinking: medium} {}
  timeout { puts stderr "FAIL: Alt+, did not decrease thinking to medium"; exit 3 }
}
send -- "\004"
expect eof
EXPECT

expect "$expect_script" "$PI_BIN" "$EXTENSION_PATH" "$transcript"
echo "PASS: Pi TUI handled Alt+. increase and Alt+, decrease"
