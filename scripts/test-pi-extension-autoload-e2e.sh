#!/usr/bin/env bash
# Launch a real fresh Pi TUI against a clean, installer-produced agent directory.
# This catches auto-loader regressions that source imports and file-parity tests miss.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PI_BIN="${PI_BIN:-$(command -v pi || true)}"

if [ -z "$PI_BIN" ] || [ ! -x "$PI_BIN" ]; then
  echo "FAIL: pi is not available" >&2
  exit 1
fi
if ! command -v expect >/dev/null 2>&1; then
  echo "FAIL: expect is required for the Pi extension auto-load E2E test" >&2
  exit 1
fi

sandbox="$(mktemp -d)"
expect_script="$sandbox/launch.expect"
transcript="$sandbox/pi-startup.log"
trap 'rm -rf "$sandbox"' EXIT

# Use the production --pi path, not a source copy or a narrower installer, so
# this covers stale-helper cleanup and the exact deployed runtime layout.
HOME="$sandbox/home" bash "$REPO_ROOT/install.sh" --pi >/dev/null
agent_dir="$sandbox/home/.pi/agent"
policy="$agent_dir/lib/grok-context-ceiling-policy.ts"
legacy_helper="$agent_dir/extensions/grok-context-ceiling-policy.ts"
extension="$agent_dir/extensions/percentage-compaction.ts"

[ -f "$policy" ] || { echo "FAIL: installer did not deploy Grok policy library" >&2; exit 1; }
[ ! -e "$legacy_helper" ] || { echo "FAIL: installer left Grok policy helper in auto-loaded extensions directory" >&2; exit 1; }
grep -Fq '../lib/grok-context-ceiling-policy' "$extension" || {
  echo "FAIL: installed percentage extension does not import the managed policy library" >&2
  exit 1
}

cat >"$expect_script" <<'EXPECT'
set timeout 25
set pi_bin [lindex $argv 0]
set home [lindex $argv 1]
set agent_dir [lindex $argv 2]
set work_dir [lindex $argv 3]
set transcript_path [lindex $argv 4]
log_user 0
log_file -noappend $transcript_path
cd $work_dir
spawn env HOME=$home PI_CODING_AGENT_DIR=$agent_dir TERM=xterm-256color PI_OFFLINE=1 $pi_bin --offline --no-session --no-skills --no-prompt-templates --no-context-files --model openai-codex/gpt-5.6-terra
expect {
  -re {gpt-5\.6-terra} {}
  -re {(factory export|default export).*grok-context-ceiling-policy} {
    puts stderr "FAIL: Pi auto-loader rejected the Grok policy helper"
    exit 1
  }
  eof {
    puts stderr "FAIL: Pi exited before opening its TUI"
    exit 1
  }
  timeout {
    puts stderr "FAIL: Pi startup timed out"
    exit 1
  }
}
send -- "\003"
expect eof
EXPECT

expect "$expect_script" "$PI_BIN" "$sandbox/home" "$agent_dir" "$sandbox" "$transcript"
echo "PASS: fresh Pi TUI auto-loaded the installed extension layout"
