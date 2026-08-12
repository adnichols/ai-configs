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
PI_CURSOR_SDK_STABLE_PACKAGE="$PI_AGENT_DIR/local-packages/ai-configs/pi-cursor-sdk"
PI_PREWALK_STABLE_PACKAGE="$PI_AGENT_DIR/local-packages/ai-configs/pi-prewalk"
PI_DEFAULT_PROVIDER="deepinfra"
PI_DEFAULT_MODEL="deepseek-ai/DeepSeek-V4-Flash-0731"
PI_DEFAULT_MODEL_VALUE="${PI_DEFAULT_PROVIDER}/${PI_DEFAULT_MODEL}"
PI_WEB_SEARCH_SUMMARY_MODEL="openai-codex/gpt-5.6-terra"
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
  python3 "$REPO_ROOT/scripts/pi_review_stack_contract.py" verify \
    --manifest "$REPO_ROOT/scripts/pi-review-stack-managed-surfaces.json" \
    --repo-root "$REPO_ROOT" --home "$HOME" --scope pi-review-stack
  python3 "$REPO_ROOT/scripts/probe_pi_review_transport.py" \
    --agent-dir "$PI_AGENT_DIR" --target-checkout "$REPO_ROOT"
  echo "Pi review-stack verification passed (check-only)."
  exit 0
elif [ "$VERIFY_SCOPE" != "full" ]; then
  echo "Unknown verification scope: $VERIFY_SCOPE" >&2; exit 2
fi

EXPECTED_GIT_PACKAGES=()

EXPECTED_NPM_PACKAGES=(
  "npm:@tintinweb/pi-subagents"
  "npm:@juicesharp/rpiv-todo"
  "npm:@aliou/pi-processes"
  "npm:@aliou/pi-synthetic"
  "npm:@narumitw/pi-goal"
  "npm:pi-web-access"
  "npm:pi-no-soft-cursor"
  "npm:@tmustier/pi-files-widget"
  "npm:@tmustier/pi-raw-paste"
  "npm:@pi-kaush/pi-inline-skill-identifier"
  "npm:@howaboua/pi-explore-subagents"
  "npm:pi-deepinfra"
  "npm:pi-updater"
  "npm:pi-extensible-workflows"
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

DEFAULT_PROVIDER = "deepinfra"
DEFAULT_MODEL = "deepseek-ai/DeepSeek-V4-Flash-0731"
DEFAULT_MODEL_VALUE = f"{DEFAULT_PROVIDER}/{DEFAULT_MODEL}"
WEB_SEARCH_SUMMARY_MODEL = "openai-codex/gpt-5.6-terra"
PICKER_ENABLED_MODELS = [
    f"{DEFAULT_MODEL_VALUE}:high",
    "openai-codex/gpt-5.6-terra:high",
    "openai-codex/gpt-5.6-luna:xhigh",
    "openai-codex/gpt-5.6-sol:medium",
    "xai/grok-4.5:high",
    "cursor/grok-4.5:high",
    "opencode/deepseek-v4-flash:high",
]

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
if models is not None and not isinstance(models, list):
    raise SystemExit("settings enabledModels must be a list when present")
settings["enabledModels"] = PICKER_ENABLED_MODELS
settings_path.parent.mkdir(parents=True, exist_ok=True)
settings_path.write_text(json.dumps(settings, indent=2) + "\n")

if web_search_path.exists():
    web_search = json.loads(web_search_path.read_text())
else:
    web_search = {}
if not isinstance(web_search, dict):
    raise SystemExit("web-search.json must be a JSON object")
web_search["summaryModel"] = WEB_SEARCH_SUMMARY_MODEL
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
EXPECTED_LOCAL_PACKAGES="$(printf '%s\n%s\n%s' "$PI_VCC_STABLE_PACKAGE" "$PI_CURSOR_SDK_STABLE_PACKAGE" "$PI_PREWALK_STABLE_PACKAGE")"
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

if ! PI_CODING_AGENT_DIR="$PI_AGENT_DIR" python3 "$REPO_ROOT/scripts/patch_pi_explore_subagents.py" --check >/dev/null; then
  note_failure "pi-explore-subagents is installed without complete Herdr child-environment isolation"
fi

if [ ! -f "$PI_PREWALK_STABLE_PACKAGE/package.json" ]; then
  note_failure "vendored pi-prewalk mirror is missing package.json: $PI_PREWALK_STABLE_PACKAGE"
elif [ "$(python3 - "$PI_PREWALK_STABLE_PACKAGE/package.json" <<'PY'
import json, sys
from pathlib import Path
try:
    print(json.loads(Path(sys.argv[1]).read_text()).get("name", ""))
except Exception:
    print("")
PY
)" != "@adnichols/pi-prewalk" ]; then
  note_failure "vendored pi-prewalk mirror has an unexpected package name"
elif ! grep -Fq 'deepseek-ai/DeepSeek-V4-Flash-0731' "$PI_PREWALK_STABLE_PACKAGE/profiles.json" 2>/dev/null; then
  note_failure "vendored pi-prewalk profiles.json is missing the DeepSeek Flash default"
elif ! grep -Fq 'defaultProfile' "$PI_PREWALK_STABLE_PACKAGE/profiles.json" 2>/dev/null; then
  note_failure "vendored pi-prewalk profiles.json is missing defaultProfile"
elif ! grep -Fq 'mergePrewalkConfigs' "$PI_PREWALK_STABLE_PACKAGE/extensions/prewalk.ts" 2>/dev/null; then
  note_failure "vendored pi-prewalk extension is missing named-profile support"
else
  echo "  stable pi-prewalk mirror: present with named profiles"
fi

PI_PREWALK_REGISTERED="$(printf '%s\n' "$INSTALLED_PI_PACKAGES" | grep 'pi-prewalk' || true)"
PI_PREWALK_COUNT="$(printf '%s\n' "$PI_PREWALK_REGISTERED" | sed '/^$/d' | wc -l | tr -d ' ')"
if [ "$PI_PREWALK_COUNT" != "1" ]; then
  note_failure "expected exactly one registered pi-prewalk package, found $PI_PREWALK_COUNT"
elif ! printf '%s\n' "$PI_PREWALK_REGISTERED" | grep -Fq "local-packages/ai-configs/pi-prewalk"; then
  note_failure "registered pi-prewalk path is not the stable mirror: $PI_PREWALK_REGISTERED"
fi
if printf '%s\n' "$INSTALLED_PI_PACKAGES" | grep -Fq 'npm:pi-prewalk'; then
  note_failure "npm:pi-prewalk is still registered; expected vendored local package only"
fi

if [ ! -f "$PI_CURSOR_SDK_STABLE_PACKAGE/package.json" ]; then
  note_failure "vendored pi-cursor-sdk mirror is missing package.json: $PI_CURSOR_SDK_STABLE_PACKAGE"
elif [ "$(python3 - "$PI_CURSOR_SDK_STABLE_PACKAGE/package.json" <<'PY'
import json, sys
from pathlib import Path
try:
    print(json.loads(Path(sys.argv[1]).read_text()).get("name", ""))
except Exception:
    print("")
PY
)" != "pi-cursor-sdk" ]; then
  note_failure "vendored pi-cursor-sdk mirror has an unexpected package name"
fi
if [ ! -f "$PI_CURSOR_SDK_STABLE_PACKAGE/node_modules/@cursor/sdk/package.json" ]; then
  note_failure "vendored pi-cursor-sdk mirror is missing production dependencies"
fi
if ! grep -Fq 'return parseEnvBoolean(env[CURSOR_ASK_QUESTION_ENV], false);' "$PI_CURSOR_SDK_STABLE_PACKAGE/src/cursor-question-tool.ts" 2>/dev/null; then
  note_failure "vendored pi-cursor-sdk has its interactive question bridge enabled by default"
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
    expected_models = [
        f"{default_model_value}:high",
        "openai-codex/gpt-5.6-terra:high",
        "openai-codex/gpt-5.6-luna:xhigh",
        "openai-codex/gpt-5.6-sol:medium",
        "xai/grok-4.5:high",
        "cursor/grok-4.5:high",
        "opencode/deepseek-v4-flash:high",
    ]
    if enabled != expected_models:
        errors.append(f"enabledModels={enabled!r}; expected exactly {expected_models!r}")
    retired_scoped = re.compile(r"^(?:glm-5\.2|opencode/glm-5\.2)$")
    if any(isinstance(model, str) and retired_scoped.fullmatch(model) for model in enabled):
        errors.append("enabledModels still contains retired GLM-5.2 Pi routes")
    if any(isinstance(model, str) and "gpt-5.3-codex-spark" in model for model in enabled):
        errors.append("enabledModels still contains gpt-5.3-codex-spark")
    stale_grok_routes = {"openai-codex/grok-4.5", "grok/grok-4.5", "grok-4.5"}
    if any(
        isinstance(model, str)
        and (model in stale_grok_routes or model.startswith("grok/") or model.startswith("grok-"))
        for model in enabled
    ):
        errors.append("enabledModels still contains retired Grok routes")
    retired_pi = re.compile(r"^(?:gpt-5\.4(?:-mini)?|openai-codex(?:-[^/]*)?/gpt-5\.4(?:-mini)?)$")
    if any(isinstance(model, str) and retired_pi.fullmatch(model) for model in enabled):
        errors.append("enabledModels still contains retired GPT-5.4 Pi routes")
print("ok" if not errors else "; ".join(errors))
PY
)"
  if [ "$PI_MODEL_STATUS" = "ok" ]; then
    echo "  Pi default execution model: $PI_DEFAULT_MODEL_VALUE"
    echo "  Pi scoped reasoning: DeepSeek Flash high; Terra high; Luna xhigh; Sol medium; xAI Grok high; Cursor Grok high; Kimi K3 high"
    echo "  Pi Codex goal token budgets: disabled"
  else
    note_failure "Pi default execution model settings are not DeepSeek Flash: $PI_MODEL_STATUS"
  fi
else
  note_failure "Pi settings file is missing: $PI_AGENT_DIR/settings.json"
fi

if [ -f "$PI_AGENT_DIR/models.json" ]; then
  PI_RETIRED_MODEL_STATUS="$(python3 - "$PI_AGENT_DIR/models.json" <<'PY'
import json, sys
models = json.load(open(sys.argv[1])).get("providers", {}).get("openai-codex", {}).get("models", [])
retired = {"gpt-5.4", "gpt-5.4-mini"}
print("ok" if not any(isinstance(model, dict) and model.get("id") in retired for model in models) else "retired GPT-5.4 managed model remains")
PY
)"
  if [ "$PI_RETIRED_MODEL_STATUS" = "ok" ]; then
    echo "  Retired Pi GPT-5.4 managed models: absent"
  else
    note_failure "$PI_RETIRED_MODEL_STATUS"
  fi
else
  note_failure "Pi models file is missing: $PI_AGENT_DIR/models.json"
fi

if [ -f "$PI_AGENT_DIR/models.json" ]; then
  PI_GROK_PROXY_STATUS="$(python3 - "$PI_AGENT_DIR/models.json" <<'PY'
import json
import sys

providers = json.load(open(sys.argv[1])).get("providers", {})
xai = providers.get("xai")
expected_ids = {
    "grok-4.5", "grok-4.3", "grok-build-0.1",
    "grok-4.20-0309-reasoning", "grok-4.20-0309-non-reasoning",
    "grok-4.20-multi-agent-0309", "grok-3-mini", "grok-3-mini-fast",
    "grok-composer-2.5-fast", "grok-imagine-image",
    "grok-imagine-image-quality", "grok-imagine-video",
    "grok-imagine-video-1.5-preview",
}
expected_headers = {
    "User-Agent": "codex-tui/0.142.5 (Linux; x86_64)",
    "Originator": "codex-tui",
}
models = xai.get("models", []) if isinstance(xai, dict) else []
model_ids = {model.get("id") for model in models if isinstance(model, dict)}
if isinstance(xai, dict) and (
    xai.get("baseUrl") == "http://127.0.0.1:8318/v1"
    and xai.get("api") == "openai-responses"
    and xai.get("apiKey") == "local-cliproxyapi"
    and xai.get("headers") == expected_headers
    and model_ids == expected_ids
):
    print("managed CLIProxyAPI xAI provider remains")
else:
    print("ok")
PY
)"
  if [ "$PI_GROK_PROXY_STATUS" = "ok" ]; then
    echo "  Managed CLIProxyAPI xAI provider: absent"
  else
    note_failure "Pi retains a managed CLIProxyAPI xAI provider: $PI_GROK_PROXY_STATUS"
  fi
fi

if [ -f "$PI_WEB_SEARCH_PATH" ]; then
  PI_WEB_SEARCH_STATUS="$(PI_WEB_SEARCH_SUMMARY_MODEL="$PI_WEB_SEARCH_SUMMARY_MODEL" python3 - "$PI_WEB_SEARCH_PATH" <<'PY'
import json
import os
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text())
summary = data.get("summaryModel")
expected = os.environ["PI_WEB_SEARCH_SUMMARY_MODEL"]
print("ok" if summary == expected else repr(summary))
PY
)"
  if [ "$PI_WEB_SEARCH_STATUS" = "ok" ]; then
    echo "  Pi web-search summary model: $PI_WEB_SEARCH_SUMMARY_MODEL"
  else
    note_failure "Pi web-search summaryModel is not local Codex GPT-5.6 Terra: $PI_WEB_SEARCH_STATUS"
  fi
else
  note_failure "Pi web-search config is missing: $PI_WEB_SEARCH_PATH"
fi

if command -v pi >/dev/null 2>&1; then
  if pi --list-models openai-codex 2>/dev/null | grep -Eq '^[[:space:]]*openai-codex[[:space:]]+gpt-5\.6-terra([[:space:]]|$)'; then
    echo "  Pi reviewer GPT model route: $PI_WEB_SEARCH_SUMMARY_MODEL"
  else
    note_failure "Pi cannot resolve reviewer GPT model route $PI_WEB_SEARCH_SUMMARY_MODEL"
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

if printf '%s\n' "$INSTALLED_PI_PACKAGES" | grep -Fq 'pi-powerline-footer'; then
  note_failure "retired pi-powerline-footer package is still registered"
else
  echo "  pi-powerline-footer registration: absent"
fi

if printf '%s\n' "$INSTALLED_PI_PACKAGES" | grep -Fq '@fnnm/pi-ast-grep'; then
  note_failure "retired @fnnm/pi-ast-grep package is still registered"
else
  echo "  @fnnm/pi-ast-grep registration: absent"
fi

if printf '%s\n' "$INSTALLED_PI_PACKAGES" | grep -Fq 'pi-service-tier'; then
  note_failure "retired pi-service-tier package is still registered"
else
  echo "  pi-service-tier registration: absent"
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
