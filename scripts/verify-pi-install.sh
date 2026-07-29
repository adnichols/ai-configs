#!/usr/bin/env bash

set -euo pipefail

VERIFY_RUNTIME_CACHE="$(mktemp -d)"
export PYTHONDONTWRITEBYTECODE=1 PYTHONPYCACHEPREFIX="$VERIFY_RUNTIME_CACHE/python" XDG_CACHE_HOME="$VERIFY_RUNTIME_CACHE/xdg"
trap 'rm -rf "$VERIFY_RUNTIME_CACHE"' EXIT

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PI_AGENT_DIR="${PI_AGENT_DIR:-${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}}"
PI_ROOT_DIR="${PI_ROOT_DIR:-$(dirname "$PI_AGENT_DIR")}"
PI_EXT_DIR="$PI_AGENT_DIR/extensions"
PI_LIB_DIR="$PI_AGENT_DIR/lib"
PI_WEB_SEARCH_PATH="$PI_ROOT_DIR/web-search.json"
PI_VCC_STABLE_PACKAGE="$PI_AGENT_DIR/local-packages/ai-configs/pi-vcc"
PI_DEFAULT_PROVIDER="openai-codex"
PI_DEFAULT_MODEL="gpt-5.6-terra"
PI_DEFAULT_MODEL_VALUE="${PI_DEFAULT_PROVIDER}/${PI_DEFAULT_MODEL}"
VERIFY_SCOPE="full"
CHECK_ONLY=false

while (($#)); do
  case "$1" in
    --scope) VERIFY_SCOPE="${2:-}"; shift 2 ;;
    --check-only) CHECK_ONLY=true; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if [ "$VERIFY_SCOPE" = "pi-review-stack" ]; then
  [ "$CHECK_ONLY" = true ] || { echo "pi-review-stack verification requires --check-only" >&2; exit 2; }
  failures=0
  check_tree_entries() {
    local source="$1" target="$2" entry base
    [ -d "$target" ] || { echo "FAIL: missing $target" >&2; failures=$((failures+1)); return; }
    shopt -s nullglob
    for entry in "$source"/*; do
      base="$(basename "$entry")"
      if ! diff -qr "$entry" "$target/$base" >/dev/null 2>&1; then echo "FAIL: installed parity $target/$base" >&2; failures=$((failures+1)); fi
    done
    shopt -u nullglob
  }
  check_exact_filename_set() {
    local source="$1" target="$2" expected actual
    expected="$(find "$source" -mindepth 1 -maxdepth 1 -exec basename {} \; | sort)"
    actual="$(find "$target" -mindepth 1 -maxdepth 1 -exec basename {} \; 2>/dev/null | sort)"
    if [ "$expected" != "$actual" ]; then
      echo "FAIL: installed exact filename set $target" >&2
      echo "Expected:" >&2; printf '%s\n' "$expected" >&2
      echo "Actual:" >&2; printf '%s\n' "$actual" >&2
      failures=$((failures+1))
    fi
  }
  check_tree_entries "$REPO_ROOT/_pi/prompts" "$PI_AGENT_DIR/prompts"
  check_exact_filename_set "$REPO_ROOT/_pi/agents" "$PI_AGENT_DIR/agents"
  check_tree_entries "$REPO_ROOT/_pi/agents" "$PI_AGENT_DIR/agents"
  check_tree_entries "$REPO_ROOT/_pi/extensions" "$PI_AGENT_DIR/extensions"
  check_tree_entries "$REPO_ROOT/_pi/lib" "$PI_AGENT_DIR/lib"
  [ ! -e "$PI_AGENT_DIR/extensions/grok-context-ceiling-policy.ts" ] || { echo "FAIL: Grok policy helper must not be auto-loaded from extensions" >&2; failures=$((failures+1)); }
  for disabled_extension in claude-review codex-review; do
    if [ -e "$PI_AGENT_DIR/extensions/$disabled_extension" ]; then echo "FAIL: disabled Pi extension is still installed: $disabled_extension" >&2; failures=$((failures+1)); fi
  done
  if ! python3 - "$PI_AGENT_DIR/settings.json" "$PI_AGENT_DIR/extensions" <<'PY'
import json, os, sys
from pathlib import Path
settings, live = Path(sys.argv[1]), os.path.realpath(sys.argv[2])
if not settings.exists(): raise SystemExit(0)
try: data = json.loads(settings.read_text())
except Exception: raise SystemExit(0)
disabled = {"claude-review", "codex-review"}
for item in data.get("extensions", []) if isinstance(data, dict) else []:
    source = item if isinstance(item, str) else item.get("source") if isinstance(item, dict) else None
    if not isinstance(source, str): continue
    expanded = os.path.expanduser(source)
    normalized = os.path.normpath(expanded).replace(os.sep, "/")
    if os.path.basename(normalized) not in disabled: continue
    if normalized == f".pi/agent/extensions/{os.path.basename(normalized)}" or (os.path.isabs(expanded) and os.path.dirname(os.path.realpath(expanded)) == live):
        raise SystemExit(1)
PY
  then echo "FAIL: disabled Pi extension remains explicitly registered in settings.json" >&2; failures=$((failures+1)); fi
  for pair in "$REPO_ROOT/_pi/README.md:$PI_AGENT_DIR/README.md"; do
    left="${pair%%:*}"; right="${pair#*:}"; cmp -s "$left" "$right" || { echo "FAIL: installed parity $right" >&2; failures=$((failures+1)); }
  done
  if ! python3 - "$REPO_ROOT/_pi/models.json" "$PI_AGENT_DIR/models.json" "$PI_AGENT_DIR/settings.json" <<'PY'
import json, re, sys
source, installed = (json.load(open(value)) for value in sys.argv[1:3])
source_providers = source.get("providers", {})
installed_providers = installed.get("providers", {})
for provider_id, provider in source_providers.items():
    target = installed_providers.get(provider_id)
    if not isinstance(target, dict): raise SystemExit(1)
    source_models = provider.get("models", [])
    target_models = {model.get("id"): model for model in target.get("models", []) if isinstance(model, dict)}
    for model in source_models:
        if model.get("id") not in target_models: raise SystemExit(1)
        if provider_id == "openai-codex":
            def contains(actual, expected):
                return all(key in actual and (contains(actual[key], value) if isinstance(value, dict) else actual[key] == value) for key, value in expected.items())
            if not contains(target_models[model["id"]], model): raise SystemExit(1)
retired = {"gpt-5.4", "gpt-5.4-mini", "gpt-5.6-sol"}
managed = installed_providers.get("openai-codex", {})
if any(isinstance(model, dict) and model.get("id") in retired for model in managed.get("models", [])):
    raise SystemExit(1)
for provider_id in ("opencode", "opencode-go", "opencode-zen"):
    provider = installed_providers.get(provider_id, {})
    overrides = provider.get("modelOverrides", {}) if isinstance(provider, dict) else {}
    if isinstance(overrides, dict) and "glm-5.2" in overrides:
        raise SystemExit(1)
settings_path = sys.argv[3]
try:
    settings = json.load(open(settings_path))
except FileNotFoundError:
    settings = {}
enabled = settings.get("enabledModels", []) if isinstance(settings, dict) else []
if not isinstance(enabled, list):
    raise SystemExit(1)
for value in enabled:
    if not isinstance(value, str):
        continue
    if value in retired or re.fullmatch(r"openai-codex(?:-[^/]*)?/gpt-5\.4(?:-mini)?", value):
        raise SystemExit(1)
PY
  then echo "FAIL: installed merged model contract $PI_AGENT_DIR/models.json" >&2; failures=$((failures+1)); fi
  if ! python3 - "$REPO_ROOT" "$REPO_ROOT/APPEND_SYSTEM.md" "$PI_AGENT_DIR/APPEND_SYSTEM.md" <<'PY'
import re, subprocess, sys
from pathlib import Path
repo, source_path, installed_path = map(Path, sys.argv[1:])
token = "{{AI_CONFIGS_VERSION}}"
source = source_path.read_text()
installed = installed_path.read_text()
if source.count(token) != 1 or token in installed:
    raise SystemExit(1)
prefix, suffix = source.split(token)
if not installed.startswith(prefix) or not installed.endswith(suffix):
    raise SystemExit(1)
version = installed[len(prefix):len(installed) - len(suffix) if suffix else None]
commit = subprocess.run(["git", "-C", str(repo), "rev-parse", "--short=8", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
relative = source_path.resolve().relative_to(repo.resolve()).as_posix()
committed = subprocess.run(["git", "-C", str(repo), "show", f"HEAD:{relative}"], check=True, capture_output=True).stdout
dirty = source_path.read_bytes() != committed
expected = rf"\d{{4}}-\d{{2}}-\d{{2}}\+{re.escape(commit)}{'-dirty' if dirty else ''}"
if not re.fullmatch(expected, version):
    raise SystemExit(1)
PY
  then
    echo "FAIL: installed rendered APPEND_SYSTEM.md" >&2; failures=$((failures+1))
  fi
  for skill in autoreview claude-code-review codex-review-partner pre-pr-implementation-review reviewed-html-plan run-plan; do
    if ! diff -qr "$REPO_ROOT/skills/$skill" "$HOME/.agents/skills/$skill" >/dev/null 2>&1; then echo "FAIL: installed skill parity $skill" >&2; failures=$((failures+1)); fi
  done
  review_runtime="$HOME/.agents/scripts/review_orchestration.py"
  if ! cmp -s "$REPO_ROOT/scripts/review_orchestration.py" "$review_runtime"; then
    echo "FAIL: installed review runtime parity $review_runtime" >&2
    failures=$((failures+1))
  fi
  if ! python3 - "$review_runtime" <<'PY'
import stat, sys
try:
    mode = stat.S_IMODE(__import__("os").stat(sys.argv[1]).st_mode)
except OSError:
    raise SystemExit(1)
raise SystemExit(0 if mode == 0o755 else 1)
PY
  then echo "FAIL: installed review runtime must have exact mode 0755: $review_runtime" >&2; failures=$((failures+1)); fi
  if [ -x "$review_runtime" ] && ! "$review_runtime" --help >/dev/null 2>&1; then
    echo "FAIL: installed review runtime --help failed: $review_runtime" >&2
    failures=$((failures+1))
  elif [ ! -x "$review_runtime" ]; then
    echo "FAIL: installed review runtime is not executable: $review_runtime" >&2
    failures=$((failures+1))
  fi
  for helper in process_identity.py review_supervisor.py; do
    installed="$HOME/.agents/skills/codex-review-partner/scripts/$helper"
    if ! python3 - "$installed" <<'PY'
import os, stat, sys
try:
    mode = os.stat(sys.argv[1]).st_mode
except OSError:
    raise SystemExit(1)
raise SystemExit(0 if mode & stat.S_IRUSR and mode & stat.S_IXUSR else 1)
PY
    then echo "FAIL: installed review helper must be owner-readable and executable: $installed" >&2; failures=$((failures+1)); fi
  done
  if ((failures)); then echo "Pi review-stack verification failed with $failures issue(s)." >&2; exit 1; fi
  echo "Pi review-stack verification passed (check-only)."
  exit 0
elif [ "$VERIFY_SCOPE" != "full" ]; then
  echo "Unknown verification scope: $VERIFY_SCOPE" >&2; exit 2
fi

EXPECTED_GIT_PACKAGES=()

EXPECTED_NPM_PACKAGES=(
  "npm:@tintinweb/pi-subagents"
  "npm:@tintinweb/pi-tasks"
  "npm:@aliou/pi-processes"
  "npm:@narumitw/pi-goal"
  "npm:pi-web-access"
  "npm:@fnnm/pi-ast-grep"
  "npm:pi-updater"
  "npm:pi-powerline-footer"
  "npm:pi-no-soft-cursor"
  "npm:@tmustier/pi-files-widget"
  "npm:@tmustier/pi-raw-paste"
  "npm:@pi-kaush/pi-inline-skill-identifier"
  "npm:@howaboua/pi-explore-subagents"
  "npm:pi-service-tier"
  "npm:pi-cursor-sdk"
)

FAILURES=0

print_section() {
  echo
  echo "$1"
}

note_failure() {
  local message="$1"
  FAILURES=$((FAILURES + 1))
  echo "  FAIL: $message"
}

repair_pi_model_defaults() {
  python3 - "$PI_AGENT_DIR/settings.json" "$PI_WEB_SEARCH_PATH" <<'PY'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
web_search_path = Path(sys.argv[2])

DEFAULT_PROVIDER = "openai-codex"
DEFAULT_MODEL = "gpt-5.6-terra"
DEFAULT_MODEL_VALUE = f"{DEFAULT_PROVIDER}/{DEFAULT_MODEL}"
RETIRED_PI_MODEL_IDS = {"gpt-5.6-sol", "glm-5.2"}
SPARK_MODEL = "gpt-5.3-codex-spark"
RETIRED_GROK_MODEL_PREFIXES = ("grok/",)
# Bare legacy IDs only; opencode/grok-4.5 is supported and not retired.
RETIRED_GROK_MODEL_IDS = {
    "grok-4.5",
    "grok-build-0.1",
    "grok-4.3",
    "grok-4.20-0309-reasoning",
    "grok-4.20-0309-non-reasoning",
    "grok-4.20-multi-agent-0309",
    "grok-3-mini",
    "grok-3-mini-fast",
    "grok-composer-2.5-fast",
}

if settings_path.exists():
    settings = json.loads(settings_path.read_text())
else:
    settings = {}
if not isinstance(settings, dict):
    raise SystemExit("settings.json must be a JSON object")

settings["defaultProvider"] = DEFAULT_PROVIDER
settings["defaultModel"] = DEFAULT_MODEL
settings.pop("piCodexGoal", None)

models = settings.get("enabledModels")
if models is None:
    models = []
elif not isinstance(models, list):
    raise SystemExit("settings enabledModels must be a list when present")

normalized = []
for model in models:
    if not isinstance(model, str):
        normalized.append(model)
        continue
    if model == SPARK_MODEL or model.endswith(f"/{SPARK_MODEL}"):
        continue
    if model in RETIRED_PI_MODEL_IDS or model == "opencode/glm-5.2":
        continue
    if "/" in model:
        provider_id, model_id = model.split("/", 1)
        if model_id in RETIRED_PI_MODEL_IDS and (provider_id == "openai-codex" or provider_id.startswith("openai-codex-")):
            continue
    if model.startswith(RETIRED_GROK_MODEL_PREFIXES) or model in RETIRED_GROK_MODEL_IDS:
        continue
    if model.startswith("openai-codex-") and model.endswith(f"/{DEFAULT_MODEL}"):
        model = DEFAULT_MODEL_VALUE
    if model not in normalized:
        normalized.append(model)
normalized = [model for model in normalized if model != DEFAULT_MODEL_VALUE]
normalized.insert(0, DEFAULT_MODEL_VALUE)
settings["enabledModels"] = normalized
settings_path.parent.mkdir(parents=True, exist_ok=True)
settings_path.write_text(json.dumps(settings, indent=2) + "\n")

if web_search_path.exists():
    web_search = json.loads(web_search_path.read_text())
else:
    web_search = {}
if not isinstance(web_search, dict):
    raise SystemExit("web-search.json must be a JSON object")
web_search["summaryModel"] = DEFAULT_MODEL_VALUE
web_search_path.parent.mkdir(parents=True, exist_ok=True)
web_search_path.write_text(json.dumps(web_search, indent=2) + "\n")
PY
}

list_find_entries() {
  local dir="$1"
  if [ -d "$dir" ]; then
    find "$dir" -mindepth 1 -maxdepth 1 -exec basename {} \; | sort
  fi
}

print_list() {
  local prefix="$1"
  local lines="${2:-}"

  if [ -z "$(printf '%s' "$lines" | tr -d '[:space:]')" ]; then
    echo "  (none)"
    return
  fi

  while IFS= read -r item; do
    [ -n "$item" ] || continue
    echo "  ${prefix}${item}"
  done <<EOF
$lines
EOF
}

report_expected_vs_actual() {
  local label="$1"
  local expected_lines="$2"
  local actual_lines="$3"
  local fail_on_missing="$4"

  local expected_file actual_file
  expected_file="$(mktemp)"
  actual_file="$(mktemp)"

  printf '%s\n' "$expected_lines" | sed '/^$/d' | sort -u > "$expected_file"
  printf '%s\n' "$actual_lines" | sed '/^$/d' | sort -u > "$actual_file"

  local missing extra
  missing="$(comm -23 "$expected_file" "$actual_file")"
  extra="$(comm -13 "$expected_file" "$actual_file")"

  echo "$label"
  if [ -z "$missing" ]; then
    echo "  Missing: none"
  else
    echo "  Missing:"
    while IFS= read -r item; do
      [ -n "$item" ] || continue
      echo "    - $item"
    done <<EOF
$missing
EOF
    if [ "$fail_on_missing" = true ]; then
      note_failure "$label is missing expected entries"
    fi
  fi

  if [ -z "$extra" ]; then
    echo "  Extra: none"
  else
    echo "  Extra:"
    while IFS= read -r item; do
      [ -n "$item" ] || continue
      echo "    - $item"
    done <<EOF
$extra
EOF
  fi

  rm -f "$expected_file" "$actual_file"
}

EXPECTED_REPO_EXTENSIONS="$(cd "$REPO_ROOT" && list_find_entries "_pi/extensions")"
EXPECTED_REPO_LIBRARIES="$(cd "$REPO_ROOT" && list_find_entries "_pi/lib")"
EXPECTED_REPO_AGENTS="$(cd "$REPO_ROOT" && list_find_entries "_pi/agents")"
INSTALLED_REPO_AGENTS="$(list_find_entries "$PI_AGENT_DIR/agents")"
EXPECTED_LOCAL_PACKAGES="$PI_VCC_STABLE_PACKAGE"
INSTALLED_REPO_EXTENSIONS="$(list_find_entries "$PI_EXT_DIR")"
INSTALLED_REPO_LIBRARIES="$(list_find_entries "$PI_LIB_DIR")"
INSTALLED_PI_PACKAGES=""

if command -v pi >/dev/null 2>&1; then
  INSTALLED_PI_PACKAGES="$({
    pi list 2>/dev/null |
      sed -n 's/^  \([^[:space:]].*\)$/\1/p' |
      sed -E 's#^(git:[^@[:space:]]+)@.*#\1#' |
      while IFS= read -r source; do
        [ -n "$source" ] || continue
        if [[ "$source" == npm:* || "$source" == git:* ]]; then
          printf '%s\n' "$source"
        else
          python3 -c 'import os, sys; source = sys.argv[1]; base = sys.argv[2]; print(os.path.realpath(source if os.path.isabs(source) else os.path.join(base, source)))' "$source" "$PI_AGENT_DIR"
        fi
      done |
      sort -u
  } || true)"
else
  note_failure "pi command is not available in PATH"
fi

echo "Pi install verification"
echo "Repo root: $REPO_ROOT"
echo "Pi agent dir: $PI_AGENT_DIR"

print_section "1) Repo-managed Pi extensions (copied into ~/.pi/agent/extensions; these do NOT appear in 'pi list')"
print_list "expected: " "$EXPECTED_REPO_EXTENSIONS"
print_list "installed: " "$INSTALLED_REPO_EXTENSIONS"
report_expected_vs_actual "  Comparison:" "$EXPECTED_REPO_EXTENSIONS" "$INSTALLED_REPO_EXTENSIONS" true
for disabled_extension in claude-review codex-review; do
  if [ -e "$PI_EXT_DIR/$disabled_extension" ]; then note_failure "disabled Pi extension is still installed: $disabled_extension"; fi
done
if [ -e "$PI_EXT_DIR/grok-context-ceiling-policy.ts" ]; then note_failure "Grok policy helper must not be auto-loaded from extensions"; fi

print_section "1b) Repo-managed Pi libraries (copied outside extensions so Pi does not auto-load helpers)"
print_list "expected: " "$EXPECTED_REPO_LIBRARIES"
print_list "installed: " "$INSTALLED_REPO_LIBRARIES"
report_expected_vs_actual "  Comparison:" "$EXPECTED_REPO_LIBRARIES" "$INSTALLED_REPO_LIBRARIES" true
while IFS= read -r library_entry; do
  [ -n "$library_entry" ] || continue
  if ! diff -qr "$REPO_ROOT/_pi/lib/$library_entry" "$PI_LIB_DIR/$library_entry" >/dev/null 2>&1; then
    note_failure "installed Pi library parity failed for $library_entry"
  fi
done <<EOF
$EXPECTED_REPO_LIBRARIES
EOF

if ! python3 - "$PI_AGENT_DIR/settings.json" "$PI_EXT_DIR" <<'PY'
import json, os, sys
from pathlib import Path
settings, live = Path(sys.argv[1]), os.path.realpath(sys.argv[2])
if not settings.exists(): raise SystemExit(0)
try: data = json.loads(settings.read_text())
except Exception: raise SystemExit(0)
disabled = {"claude-review", "codex-review"}
for item in data.get("extensions", []) if isinstance(data, dict) else []:
    source = item if isinstance(item, str) else item.get("source") if isinstance(item, dict) else None
    if not isinstance(source, str): continue
    expanded = os.path.expanduser(source)
    normalized = os.path.normpath(expanded).replace(os.sep, "/")
    if os.path.basename(normalized) not in disabled: continue
    if normalized == f".pi/agent/extensions/{os.path.basename(normalized)}" or (os.path.isabs(expanded) and os.path.dirname(os.path.realpath(expanded)) == live):
        raise SystemExit(1)
PY
then note_failure "disabled Pi extension remains explicitly registered in settings.json"; fi

print_section "2) Repo-managed Pi agents (installed as an exact filename set)"
print_list "expected: " "$EXPECTED_REPO_AGENTS"
print_list "installed: " "$INSTALLED_REPO_AGENTS"
if [ "$EXPECTED_REPO_AGENTS" != "$INSTALLED_REPO_AGENTS" ]; then
  note_failure "installed Pi agent directory does not exactly match the repository roster"
fi
while IFS= read -r agent_entry; do
  [ -n "$agent_entry" ] || continue
  if ! diff -qr "$REPO_ROOT/_pi/agents/$agent_entry" "$PI_AGENT_DIR/agents/$agent_entry" >/dev/null 2>&1; then
    note_failure "installed Pi agent parity failed for $agent_entry"
  fi
done <<EOF
$EXPECTED_REPO_AGENTS
EOF

print_section "3) Package-managed Pi installs (registered via 'pi install'; these DO appear in 'pi list')"
EXPECTED_GIT_PACKAGE_LINES=""
if ((${#EXPECTED_GIT_PACKAGES[@]} > 0)); then
  EXPECTED_GIT_PACKAGE_LINES="$(printf '%s\n' "${EXPECTED_GIT_PACKAGES[@]}")"
fi
print_list "expected git: " "$EXPECTED_GIT_PACKAGE_LINES"
print_list "expected npm: " "$(printf '%s\n' "${EXPECTED_NPM_PACKAGES[@]}")"
print_list "expected local: " "$EXPECTED_LOCAL_PACKAGES"
print_list "registered: " "$INSTALLED_PI_PACKAGES"
ALL_EXPECTED_PACKAGES="$(printf '%s\n%s\n' "$EXPECTED_GIT_PACKAGE_LINES" "$(printf '%s\n' "${EXPECTED_NPM_PACKAGES[@]}")")"
ALL_EXPECTED_PACKAGES="$(printf '%s\n%s\n' "$ALL_EXPECTED_PACKAGES" "$EXPECTED_LOCAL_PACKAGES")"
report_expected_vs_actual "  Comparison:" "$ALL_EXPECTED_PACKAGES" "$INSTALLED_PI_PACKAGES" true

PI_SERVICE_TIER_SHARED="$PI_AGENT_DIR/npm/node_modules/pi-service-tier/shared.ts"
if [ -f "$PI_SERVICE_TIER_SHARED" ] && ! grep -Fq 'const usesCLIProxyAPIResponses =' "$PI_SERVICE_TIER_SHARED"; then
  note_failure "pi-service-tier is installed without the CLIProxyAPI openai-responses compatibility patch"
fi

if ! PI_CODING_AGENT_DIR="$PI_AGENT_DIR" python3 "$REPO_ROOT/scripts/patch_pi_explore_subagents.py" --check >/dev/null; then
  note_failure "pi-explore-subagents is installed without complete Herdr child-environment isolation"
fi

print_section "4) Quick checks"
echo "  Repo-managed extensions: find ~/.pi/agent/extensions -mindepth 1 -maxdepth 1 -exec basename {} \\; | sort"
echo "  Package-managed installs: pi list"

if [ "$CHECK_ONLY" = true ]; then
  echo "  Pi local Codex defaults repair: skipped (--check-only)"
elif repair_pi_model_defaults; then
  echo "  Pi local Codex defaults repair: applied"
else
  note_failure "unable to repair Pi local Codex defaults"
fi

if [ -f "$PI_AGENT_DIR/settings.json" ]; then
  PI_MODEL_STATUS="$(PI_DEFAULT_PROVIDER="$PI_DEFAULT_PROVIDER" PI_DEFAULT_MODEL="$PI_DEFAULT_MODEL" PI_DEFAULT_MODEL_VALUE="$PI_DEFAULT_MODEL_VALUE" python3 - "$PI_AGENT_DIR/settings.json" <<'PY'
import json
import os
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
default_provider = os.environ["PI_DEFAULT_PROVIDER"]
default_model = os.environ["PI_DEFAULT_MODEL"]
default_model_value = os.environ["PI_DEFAULT_MODEL_VALUE"]
errors = []
if data.get("defaultProvider") != default_provider:
    errors.append(f"defaultProvider={data.get('defaultProvider')!r}")
if data.get("defaultModel") != default_model:
    errors.append(f"defaultModel={data.get('defaultModel')!r}")
if "piCodexGoal" in data:
    errors.append("retired piCodexGoal settings remain")
enabled = data.get("enabledModels", [])
if not isinstance(enabled, list):
    errors.append("enabledModels is not a list")
else:
    if default_model_value not in enabled:
        errors.append(f"enabledModels missing {default_model_value}")
    retired_scoped = re.compile(r"^(?:gpt-5\.6-sol|glm-5\.2|opencode/glm-5\.2|openai-codex(?:-[^/]*)?/gpt-5\.6-sol)$")
    if any(isinstance(model, str) and retired_scoped.fullmatch(model) for model in enabled):
        errors.append("enabledModels still contains retired GPT-5.6 Sol or GLM-5.2 Pi routes")
    if any(isinstance(model, str) and "gpt-5.3-codex-spark" in model for model in enabled):
        errors.append("enabledModels still contains gpt-5.3-codex-spark")
    if any(
        isinstance(model, str)
        and (model.startswith("grok/") or model.startswith("grok-"))
        for model in enabled
    ):
        errors.append("enabledModels still contains retired grok models")
    retired_pi = re.compile(r"^(?:gpt-5\.4(?:-mini)?|openai-codex(?:-[^/]*)?/gpt-5\.4(?:-mini)?)$")
    if any(isinstance(model, str) and retired_pi.fullmatch(model) for model in enabled):
        errors.append("enabledModels still contains retired GPT-5.4 Pi routes")
print("ok" if not errors else "; ".join(errors))
PY
)"
  if [ "$PI_MODEL_STATUS" = "ok" ]; then
    echo "  Pi default model: $PI_DEFAULT_MODEL_VALUE"
    echo "  Pi scoped Sol and GLM routes: absent"
    echo "  Pi Codex goal token budgets: disabled"
  else
    note_failure "Pi default model settings are not GPT-5.6 Terra: $PI_MODEL_STATUS"
  fi
else
  note_failure "Pi settings file is missing: $PI_AGENT_DIR/settings.json"
fi

if [ -f "$PI_AGENT_DIR/models.json" ]; then
  PI_RETIRED_MODEL_STATUS="$(python3 - "$PI_AGENT_DIR/models.json" <<'PY'
import json, sys
models = json.load(open(sys.argv[1])).get("providers", {}).get("openai-codex", {}).get("models", [])
retired = {"gpt-5.4", "gpt-5.4-mini"}
print("ok" if not any(isinstance(model, dict) and model.get("id") in retired for model in models) else "retired GPT-5.4 or GPT-5.6 Sol managed model remains")
PY
)"
  if [ "$PI_RETIRED_MODEL_STATUS" = "ok" ]; then
    echo "  Retired Pi GPT-5.4 and GPT-5.6 Sol managed models: absent"
  else
    note_failure "$PI_RETIRED_MODEL_STATUS"
  fi
else
  note_failure "Pi models file is missing: $PI_AGENT_DIR/models.json"
fi

if [ -f "$PI_WEB_SEARCH_PATH" ]; then
  PI_WEB_SEARCH_STATUS="$(PI_DEFAULT_MODEL_VALUE="$PI_DEFAULT_MODEL_VALUE" python3 - "$PI_WEB_SEARCH_PATH" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
summary = data.get("summaryModel")
default_model_value = os.environ["PI_DEFAULT_MODEL_VALUE"]
print("ok" if summary == default_model_value else repr(summary))
PY
)"
  if [ "$PI_WEB_SEARCH_STATUS" = "ok" ]; then
    echo "  Pi web-search summary model: $PI_DEFAULT_MODEL_VALUE"
  else
    note_failure "Pi web-search summaryModel is not local Codex GPT-5.6 Terra: $PI_WEB_SEARCH_STATUS"
  fi
else
  note_failure "Pi web-search config is missing: $PI_WEB_SEARCH_PATH"
fi

if command -v pi >/dev/null 2>&1; then
  if pi --list-models "$PI_DEFAULT_MODEL_VALUE" 2>/dev/null | grep -Eq '^[[:space:]]*openai-codex[[:space:]]+gpt-5\.6-terra([[:space:]]|$)'; then
    echo "  Pi reviewer GPT model route: $PI_DEFAULT_MODEL_VALUE"
  else
    note_failure "Pi cannot resolve reviewer GPT model route $PI_DEFAULT_MODEL_VALUE"
  fi

fi

if printf '%s\n' "$INSTALLED_PI_PACKAGES" | grep -Fq 'pi-multi-pass'; then
  note_failure "pi-multi-pass is still registered; local openai-codex should be the only Codex route"
else
  echo "  pi-multi-pass registration: absent"
fi

if printf '%s\n' "$INSTALLED_PI_PACKAGES" | grep -Fq 'pi-codex-goal'; then
  note_failure "retired pi-codex-goal package is still registered"
else
  echo "  pi-codex-goal registration: absent"
fi

if printf '%s\n' "$INSTALLED_PI_PACKAGES" | grep -Fq '@howaboua/pi-codex-conversion'; then
  note_failure "retired @howaboua/pi-codex-conversion package is still registered"
else
  echo "  @howaboua/pi-codex-conversion registration: absent"
fi

if printf '%s\n' "$INSTALLED_PI_PACKAGES" | grep -Fq '@ff-labs/pi-fff'; then
  note_failure "retired @ff-labs/pi-fff package is still registered"
else
  echo "  @ff-labs/pi-fff registration: absent"
fi

if printf '%s\n' "$INSTALLED_PI_PACKAGES" | grep -Fq 'npm:pi-side-agents'; then
  note_failure "retired pi-side-agents package is still registered"
else
  echo "  pi-side-agents registration: absent"
fi

if printf '%s\n' "$INSTALLED_PI_PACKAGES" | grep -Fq 'pi-interactive-shell'; then
  note_failure "retired pi-interactive-shell package is still registered"
else
  echo "  pi-interactive-shell registration: absent"
fi

PI_VCC_REGISTERED="$(printf '%s\n' "$INSTALLED_PI_PACKAGES" | grep 'pi-vcc' || true)"
PI_VCC_COUNT="$(printf '%s\n' "$PI_VCC_REGISTERED" | sed '/^$/d' | wc -l | tr -d '[:space:]')"
if [ "$PI_VCC_COUNT" != "1" ]; then
  note_failure "expected exactly one registered pi-vcc package, found $PI_VCC_COUNT"
elif [ "$PI_VCC_REGISTERED" != "$PI_VCC_STABLE_PACKAGE" ]; then
  note_failure "registered pi-vcc path is not the stable mirror: $PI_VCC_REGISTERED"
fi

if [ -d "$PI_VCC_STABLE_PACKAGE" ]; then
  echo "  stable pi-vcc mirror: present"
else
  note_failure "stable pi-vcc mirror is missing: $PI_VCC_STABLE_PACKAGE"
fi

if [ -f "$PI_VCC_STABLE_PACKAGE/package.json" ]; then
  PI_VCC_PACKAGE_NAME="$(python3 - "$PI_VCC_STABLE_PACKAGE/package.json" <<'PY'
import json
import sys
from pathlib import Path
try:
    print(json.loads(Path(sys.argv[1]).read_text()).get("name", ""))
except Exception:
    print("")
PY
)"
  if [ "$PI_VCC_PACKAGE_NAME" = "@adnichols/pi-vcc" ]; then
    echo "  stable pi-vcc package name: @adnichols/pi-vcc"
  else
    note_failure "stable pi-vcc package.json has unexpected name: ${PI_VCC_PACKAGE_NAME:-missing}"
  fi
else
  note_failure "stable pi-vcc package.json is missing"
fi

if [ -f "$REPO_ROOT/_pi/packages/pi-vcc/src/commands/pi-vcc.ts" ]; then
  echo "  vendored pi-vcc command source: present"
else
  echo "  vendored pi-vcc command source: missing"
fi

if [ "$FAILURES" -gt 0 ]; then
  echo
  echo "Verification failed with $FAILURES issue(s)."
  exit 1
fi

echo

echo "Verification passed."
