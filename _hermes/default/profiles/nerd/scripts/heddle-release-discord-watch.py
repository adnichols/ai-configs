#!/usr/bin/env python3
import json
import os
import subprocess
import sys

SCRIPT = "/Users/anichols/code/heddle-release/scripts/release/main-release-watch.py"

env = os.environ.copy()
# Hermes scheduler runs script jobs with cwd at HERMES_HOME/scripts and may not
# pass terminal-like auth context. Force the operator home + git/gh config paths
# so HTTPS fetch/publish uses Aaron's keychain-backed GitHub credentials.
env["HOME"] = "/Users/anichols"
env["HEDDLE_RELEASE_AUTH_HOME"] = "/Users/anichols"
env["GIT_CONFIG_GLOBAL"] = "/Users/anichols/.gitconfig"
env["XDG_CONFIG_HOME"] = "/Users/anichols/.config"
env.setdefault("USER", "anichols")
env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:" + env.get("PATH", "")
# Prevent a scheduler-injected GitHub token for a different identity from
# overriding Aaron's gh/keychain-backed credential. `main-release-watch.py`
# will use gh's credential helper via Aaron's HOME/config.
env.pop("GH_TOKEN", None)
env.pop("GITHUB_TOKEN", None)

proc = subprocess.run(
    [SCRIPT],
    cwd="/Users/anichols/code/heddle-release",
    env=env,
    text=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
)

# Keep no-op polls truly quiet. In Hermes no_agent cron mode, empty stdout on
# exit 0 means no Discord delivery; non-empty stdout is delivered. Preserve all
# failure output and all release/repair output.
if proc.returncode == 0:
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        payload = {}
    if payload.get("status") == "noop":
        raise SystemExit(0)

if proc.stdout:
    sys.stdout.write(proc.stdout)
if proc.stderr:
    sys.stderr.write(proc.stderr)
raise SystemExit(proc.returncode)
