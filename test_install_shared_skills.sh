#!/bin/bash

set -u
set -o pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly INSTALLER="$SCRIPT_DIR/install.sh"

TESTS_RUN=0
TESTS_PASSED=0
TESTS_FAILED=0
TMP_DIRS=()

pass() {
  printf 'PASS %s\n' "$1"
  TESTS_PASSED=$((TESTS_PASSED + 1))
}

fail() {
  printf 'FAIL %s\n' "$1" >&2
  TESTS_FAILED=$((TESTS_FAILED + 1))
}

run_test() {
  local name="$1"
  TESTS_RUN=$((TESTS_RUN + 1))
  if "$name"; then
    pass "$name"
  else
    fail "$name"
  fi
}

cleanup() {
  local dir
  for dir in "${TMP_DIRS[@]:-}"; do
    if [[ -n "$dir" && -e "$dir" ]]; then
      rm -rf "$dir"
    fi
  done
  if [[ -n "${TMP_ROOT:-}" && -d "$TMP_ROOT" ]]; then
    rm -rf "$TMP_ROOT"
  fi
}

trap cleanup EXIT

TMP_ROOT="$(mktemp -d)"

new_tmp_dir() {
  mktemp -d "$TMP_ROOT/case.XXXXXX"
}

create_fake_tool_bin() {
  local home="$1"
  local bin_dir="$home/test-bin"

  mkdir -p "$bin_dir"
  cat > "$bin_dir/pi" <<'EOF'
#!/bin/bash
set -eu

settings_path="$HOME/.pi/agent/settings.json"

case "${1:-}" in
  --list-models)
    case "${2:-}" in
      openai-codex/gpt-5.6-sol)
        printf 'openai-codex gpt-5.6-sol\n'
        ;;
      opencode/glm-5.2)
        printf 'opencode glm-5.2\n'
        ;;
    esac
    exit 0
    ;;
  list)
    if [[ "${AI_CONFIGS_FAKE_PI_LIST_FAILS:-}" == "1" ]]; then
      exit 1
    fi
    if [[ -f "$settings_path" ]]; then
      python3 - "$settings_path" <<'PY'
import json
import os
import sys
from pathlib import Path
settings_path = Path(sys.argv[1])
try:
    data = json.loads(settings_path.read_text())
except Exception:
    data = {}
for item in data.get("packages", []) if isinstance(data.get("packages"), list) else []:
    source = item.get("source") if isinstance(item, dict) else item if isinstance(item, str) else None
    if isinstance(source, str):
        rendered_source = source
        print(f"  {rendered_source}")
        print(f"    /fake/{source.replace('/', '_')}")
PY
    fi
    exit 0
    ;;
  install)
    shift
    source="${1:-}"
    python3 - "$settings_path" "$source" <<'PY'
import json
import os
import sys
from pathlib import Path
settings_path = Path(sys.argv[1])
source = sys.argv[2]
if source and not source.startswith(("npm:", "git:")):
    source = os.path.relpath(Path(source).resolve(), settings_path.parent)
try:
    data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
except Exception:
    data = {}
if not isinstance(data, dict):
    data = {}
packages = data.get("packages")
if not isinstance(packages, list):
    packages = []
if source and source not in packages:
    packages.append(source)
data["packages"] = packages
settings_path.parent.mkdir(parents=True, exist_ok=True)
settings_path.write_text(json.dumps(data, indent=2) + "\n")
PY
    if [[ "$source" == "npm:@tintinweb/pi-subagents" ]]; then
      package="$HOME/.pi/agent/npm/node_modules/@tintinweb/pi-subagents"
      mkdir -p "$package/src" "$package/dist"
      printf '%s\n' 'isolation: agentConfig?.isolation ?? params.isolation,' >"$package/src/invocation-config.ts"
      printf '%s\n' 'isolation: agentConfig?.isolation ?? params.isolation,' >"$package/dist/invocation-config.js"
      printf '%s\n' 'export type IsolationMode = "worktree";' >"$package/src/types.ts"
      printf '%s\n' 'export type IsolationMode = "worktree";' >"$package/dist/types.d.ts"
      printf '%s\n' 'isolation: fm.isolation === "worktree" ? "worktree" : undefined,' >"$package/src/custom-agents.ts"
      printf '%s\n' 'isolation: fm.isolation === "worktree" ? "worktree" : undefined,' >"$package/dist/custom-agents.js"
    fi
    exit 0
    ;;
  update)
    exit 0
    ;;
  remove)
    shift
    source="${1:-}"
    python3 - "$settings_path" "$source" <<'PY'
import json
import sys
from pathlib import Path
settings_path = Path(sys.argv[1])
source = sys.argv[2]
try:
    data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
except Exception:
    data = {}
packages = data.get("packages")
if not isinstance(packages, list):
    packages = []
data["packages"] = [item for item in packages if item != source]
settings_path.parent.mkdir(parents=True, exist_ok=True)
settings_path.write_text(json.dumps(data, indent=2) + "\n")
PY
    exit 0
    ;;
  *)
    exit 0
    ;;
esac
EOF
  chmod +x "$bin_dir/pi"

  cat > "$bin_dir/bun" <<'EOF'
#!/bin/bash
set -eu

echo "stub bun $*" >/dev/null
exit 0
EOF
  chmod +x "$bin_dir/bun"

  cat > "$bin_dir/npm" <<'EOF'
#!/bin/bash
set -eu

# The vendored pi-cursor-sdk installer uses `npm ci --omit=dev`; emulate the
# production dependency sentinel without reaching the network.
if [[ "${1:-}" == "ci" ]]; then
  mkdir -p node_modules/@cursor/sdk
  printf '{"name":"@cursor/sdk"}\n' > node_modules/@cursor/sdk/package.json
  exit 0
fi
if [[ "${1:-}" == "install" ]]; then
  shift
  prefix=""
  while [[ $# -gt 0 ]]; do
    if [[ "$1" == "--prefix" ]]; then prefix="$2"; shift 2; else shift; fi
  done
  if [[ -n "$prefix" ]]; then
    package="$prefix/node_modules/@tintinweb/pi-subagents"
    mkdir -p "$package/src" "$package/dist"
    printf '%s\n' 'isolation: agentConfig?.isolation ?? params.isolation,' >"$package/src/invocation-config.ts"
    printf '%s\n' 'isolation: agentConfig?.isolation ?? params.isolation,' >"$package/dist/invocation-config.js"
    printf '%s\n' 'export type IsolationMode = "worktree";' >"$package/src/types.ts"
    printf '%s\n' 'export type IsolationMode = "worktree";' >"$package/dist/types.d.ts"
    printf '%s\n' 'isolation: fm.isolation === "worktree" ? "worktree" : undefined,' >"$package/src/custom-agents.ts"
    printf '%s\n' 'isolation: fm.isolation === "worktree" ? "worktree" : undefined,' >"$package/dist/custom-agents.js"
  fi
fi
exit 0
EOF
  chmod +x "$bin_dir/npm"

  cat > "$bin_dir/npx" <<'EOF'
#!/bin/bash
set -eu

if [[ "${1:-}" != "skills" ]]; then
  echo "stub npx only supports 'skills'" >&2
  exit 1
fi
shift

command="${1:-}"
shift || true

case "$command" in
  add)
    package="${1:-}"
    shift || true
    skills=()

    while [[ $# -gt 0 ]]; do
      case "$1" in
        --skill|-s)
          shift
          while [[ $# -gt 0 ]]; do
            case "$1" in
              -*)
                break
                ;;
              *)
                skills+=("$1")
                shift
                ;;
            esac
          done
          ;;
        --global|-g|--yes|-y)
          shift
          ;;
        *)
          shift
          ;;
      esac
    done

    mkdir -p "$HOME/.agents/skills"
    touch "$HOME/.agents/fake-npx-skills.log"
    for skill in "${skills[@]}"; do
      mkdir -p "$HOME/.agents/skills/$skill"
      printf 'external package=%s skill=%s\n' "$package" "$skill" > "$HOME/.agents/skills/$skill/SKILL.md"
      printf '%s\t%s\n' "$package" "$skill" >> "$HOME/.agents/fake-npx-skills.log"
    done
    ;;
  update)
    mkdir -p "$HOME/.agents"
    printf 'update %s\n' "$*" >> "$HOME/.agents/fake-npx-skills-update.log"

    if [[ "${AI_CONFIGS_FAKE_SKILLS_UPDATE_MUTATES:-}" == "linear" ]]; then
      mkdir -p "$HOME/.agents/skills/linear"
      rm -f "$HOME/.agents/skills/linear/.ai-configs-managed.json"
      printf 'skills.sh-updated-linear\n' > "$HOME/.agents/skills/linear/SKILL.md"
    fi
    ;;
  *)
    exit 0
    ;;
esac
EOF
  chmod +x "$bin_dir/npx"

  cat > "$bin_dir/herdr" <<'EOF'
#!/bin/bash
set -eu

if [[ "${1:-}" == "plugin" && "${2:-}" == "install" ]]; then
  mkdir -p "$HOME/.config/herdr"
  printf '%s\n' "$*" >> "$HOME/.config/herdr/fake-plugin-installs.log"
  exit 0
fi

exit 0
EOF
  chmod +x "$bin_dir/herdr"

  printf '%s\n' "$bin_dir"
}

seed_phase_two_home() {
  local home="$1"
  # Split the retired skill name so stale-name greps can still guard active surfaces.
  local old_skill="scoped""-plan-run"
  local skill
  local retired_skills=(
    adn-dev-wf
    cmd-debug
    cmd-research
    cmd-start-linear-issue
    cmd-start-linear-issue-branch
    opencode-safe-restart
    plan-reviewer-build
    plan-reviewer-execution-ready
    review-change
    review-change-integrate
    herdr-reviewers
  )

  mkdir -p \
    "$home/.claude/skills/custom-local" \
    "$home/.pi/agent/skills" \
    "$home/.agents/skills/external-skill" \
    "$home/.agents/skills/linear" \
    "$home/.agents/skills/$old_skill" \
    "$home/.agents/skills/algorithmic-art" \
    "$home/.agents/skills/omp-review-partner" \
    "$home/.claude/skills/linear" \
    "$home/.claude/skills/algorithmic-art" \
    "$home/.config/opencode/skills"

  printf 'external\n' > "$home/.agents/skills/external-skill/SKILL.md"
  printf 'foreign-linear\n' > "$home/.agents/skills/linear/SKILL.md"
  printf 'old-%s\n' "$old_skill" > "$home/.agents/skills/$old_skill/SKILL.md"
  printf '{"repo":"ai-configs","source":"skills/%s","managed":true}\n' "$old_skill" > "$home/.agents/skills/$old_skill/.ai-configs-managed.json"
  printf 'old-optional-algorithmic-art\n' > "$home/.agents/skills/algorithmic-art/SKILL.md"
  printf '{"repo":"ai-configs","source":"external-package:anthropics/skills#algorithmic-art","managed":true}\n' > "$home/.agents/skills/algorithmic-art/.ai-configs-managed.json"
  printf 'retired omp review partner\n' > "$home/.agents/skills/omp-review-partner/SKILL.md"
  printf '{"repo":"ai-configs","source":"skills/omp-review-partner","managed":true}\n' > "$home/.agents/skills/omp-review-partner/.ai-configs-managed.json"
  ln -s "$home/.agents/skills/algorithmic-art" "$home/.claude/skills/algorithmic-art"
  ln -s "$home/.agents/skills/omp-review-partner" "$home/.claude/skills/omp-review-partner"
  ln -s "$home/.agents/skills/omp-review-partner" "$home/.config/opencode/skills/omp-review-partner"
  printf 'old-claude-linear\n' > "$home/.claude/skills/linear/SKILL.md"
  ln -s "$home/.agents/skills/$old_skill" "$home/.claude/skills/$old_skill"
  ln -s "$home/.agents/skills/$old_skill" "$home/.pi/agent/skills/$old_skill"

  for skill in "${retired_skills[@]}"; do
    mkdir -p "$home/.agents/skills/$skill"
    printf 'retired %s\n' "$skill" > "$home/.agents/skills/$skill/SKILL.md"
    printf '{"repo":"ai-configs","source":"skills/%s","managed":true}\n' "$skill" > "$home/.agents/skills/$skill/.ai-configs-managed.json"
    ln -s "$home/.agents/skills/$skill" "$home/.claude/skills/$skill"
    ln -s "$home/.agents/skills/$skill" "$home/.pi/agent/skills/$skill"
  done

  python3 - "$home/.agents/.skill-lock.json" "$old_skill" "${retired_skills[@]}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
names = sys.argv[2:]
skills = {name: {"source": "old"} for name in names}
skills.update({"linear": {"source": "old"}, "omp-review-partner": {"source": "old"}})
path.write_text(json.dumps({"skills": skills}) + "\n")
PY
}

assert_file_contains() {
  local path="$1"
  local expected="$2"
  [[ -f "$path" ]] || return 1
  grep -Fq -- "$expected" "$path"
}

assert_file_not_contains() {
  local path="$1"
  local unexpected="$2"
  [[ -f "$path" ]] || return 1
  ! grep -Fq -- "$unexpected" "$path"
}

assert_symlink_target() {
  local path="$1"
  local expected="$2"
  [[ -L "$path" ]] || return 1
  [[ "$(readlink "$path")" == "$expected" ]]
}

assert_no_dangling_symlinks() {
  local root="$1"
  local dangling

  dangling="$(find "$root" -maxdepth 1 -type l ! -exec test -e {} \; -print)"
  [[ -z "$dangling" ]]
}

assert_command_output_contains() {
  local output="$1"
  local expected="$2"
  grep -Fq "$expected" <<<"$output"
}

assert_command_output_not_contains() {
  local output="$1"
  local unexpected="$2"
  ! grep -Fq "$unexpected" <<<"$output"
}

find_backup_dir() {
  local home="$1"
  local skill="$2"
  find "$home/.agents/skill-backups/ai-configs" -mindepth 2 -maxdepth 2 -type d -name "$skill" 2>/dev/null | sort | head -n 1
}

find_consumer_backup_dir() {
  local home="$1"
  local consumer="$2"
  local skill="$3"
  find "$home/.agents/skill-backups/ai-configs" -path "*/consumers/$consumer/$skill" -type d 2>/dev/null | sort | head -n 1
}

find_optional_backup_dir() {
  local home="$1"
  local profile="$2"
  local skill="$3"
  find "$home/.agents/skill-backups/ai-configs" -path "*/optional/$profile/$skill" -type d 2>/dev/null | sort | head -n 1
}

count_backup_dirs() {
  local home="$1"
  find "$home/.agents/skill-backups/ai-configs" -mindepth 2 -type d 2>/dev/null | wc -l | tr -d ' '
}

assert_shared_skill_install_state() {
  local home="$1"
  local backup_dir
  local claude_backup_dir
  local skill
  # Split the retired skill name so stale-name greps can still guard active surfaces.
  local old_skill="scoped""-plan-run"
  local retired_skills=(
    adn-dev-wf
    cmd-debug
    cmd-research
    cmd-start-linear-issue
    cmd-start-linear-issue-branch
    opencode-safe-restart
    plan-reviewer-build
    plan-reviewer-execution-ready
    review-change
    review-change-integrate
    herdr-reviewers
  )

  [[ -d "$home/.agents/skills" ]] || return 1
  [[ -f "$home/.agents/skills/external-skill/SKILL.md" ]] || return 1
  assert_file_contains "$home/.agents/skills/external-skill/SKILL.md" 'external' || return 1

  backup_dir="$(find_backup_dir "$home" linear)"
  [[ -n "$backup_dir" ]] || return 1
  [[ -f "$backup_dir/SKILL.md" ]] || return 1
  assert_file_contains "$backup_dir/SKILL.md" 'foreign-linear' || return 1

  [[ -f "$home/.agents/skills/linear/.ai-configs-managed.json" ]] || return 1
  assert_file_contains "$home/.agents/skills/linear/.ai-configs-managed.json" '"repo": "ai-configs"' || return 1
  assert_file_contains "$home/.agents/skills/linear/.ai-configs-managed.json" '"source": "skills/linear"' || return 1
  assert_file_contains "$home/.agents/skills/linear/.ai-configs-managed.json" '"managed": true' || return 1

  for skill in "${retired_skills[@]}"; do
    [[ ! -e "$home/.agents/skills/$skill" ]] || return 1
    [[ ! -e "$home/.claude/skills/$skill" ]] || return 1
    [[ ! -e "$home/.pi/agent/skills/$skill" ]] || return 1
    assert_file_not_contains "$home/.agents/.skill-lock.json" "\"$skill\"" || return 1
  done

  [[ -f "$home/.agents/skills/run-plan/SKILL.md" ]] || return 1
  [[ -f "$home/.agents/skills/run-plan/.ai-configs-managed.json" ]] || return 1
  assert_file_contains "$home/.agents/skills/run-plan/SKILL.md" 'name: run-plan' || return 1
  assert_file_contains "$home/.agents/skills/run-plan/.ai-configs-managed.json" '"repo": "ai-configs"' || return 1
  assert_file_contains "$home/.agents/skills/run-plan/.ai-configs-managed.json" '"source": "skills/run-plan"' || return 1
  assert_file_contains "$home/.agents/skills/run-plan/.ai-configs-managed.json" '"managed": true' || return 1
  [[ ! -e "$home/.agents/skills/$old_skill" ]] || return 1
  [[ ! -e "$home/.claude/skills/$old_skill" ]] || return 1
  [[ ! -e "$home/.pi/agent/skills/$old_skill" ]] || return 1
  [[ ! -e "$home/.agents/skills/omp-review-partner" ]] || return 1
  [[ ! -e "$home/.claude/skills/omp-review-partner" ]] || return 1
  [[ ! -e "$home/.config/opencode/skills/omp-review-partner" ]] || return 1
  assert_file_not_contains "$home/.agents/.skill-lock.json" "$old_skill" || return 1
  assert_file_not_contains "$home/.agents/.skill-lock.json" 'omp-review-partner' || return 1

  [[ ! -e "$home/.agents/skills/algorithmic-art" ]] || return 1
  [[ ! -e "$home/.claude/skills/algorithmic-art" ]] || return 1
  backup_dir="$(find_optional_backup_dir "$home" creative-content algorithmic-art)"
  [[ -n "$backup_dir" ]] || return 1
  assert_file_contains "$backup_dir/SKILL.md" 'old-optional-algorithmic-art' || return 1
  if [[ -f "$home/.agents/fake-npx-skills.log" ]]; then
    assert_file_not_contains "$home/.agents/fake-npx-skills.log" 'algorithmic-art' || return 1
  fi

  [[ -f "$home/.agents/skills/design-skill/SKILL.md" ]] || return 1
  assert_file_contains "$home/.agents/skills/design-skill/SKILL.md" 'name: design' || return 1
  [[ -f "$home/.agents/skills/design-skill/.ai-configs-managed.json" ]] || return 1
  assert_file_contains "$home/.agents/skills/design-skill/.ai-configs-managed.json" '"source": "skills/design-skill"' || return 1

  [[ -f "$home/.agents/skills/herdr/SKILL.md" ]] || return 1
  assert_file_contains "$home/.agents/skills/herdr/SKILL.md" 'Do not gate use on `HERDR_ENV=1`' || return 1
  assert_file_contains "$home/.agents/skills/herdr/SKILL.md" 'or an ordinary terminal' || return 1
  [[ -f "$home/.agents/skills/herdr/.ai-configs-managed.json" ]] || return 1
  assert_file_contains "$home/.agents/skills/herdr/.ai-configs-managed.json" '"source": "skills/herdr"' || return 1
  if [[ -f "$home/.agents/fake-npx-skills.log" ]]; then
    assert_file_not_contains "$home/.agents/fake-npx-skills.log" $'ogulcancelik/herdr\therdr' || return 1
  fi

  [[ -d "$home/.claude/skills/custom-local" ]] || return 1

  claude_backup_dir="$(find_consumer_backup_dir "$home" claude linear)"
  [[ -n "$claude_backup_dir" ]] || return 1
  assert_file_contains "$claude_backup_dir/SKILL.md" 'old-claude-linear' || return 1

  assert_symlink_target "$home/.claude/skills/linear" "$home/.agents/skills/linear" || return 1
  assert_symlink_target "$home/.claude/skills/run-plan" "$home/.agents/skills/run-plan" || return 1
  assert_symlink_target "$home/.claude/skills/design-skill" "$home/.agents/skills/design-skill" || return 1
  assert_symlink_target "$home/.claude/skills/herdr" "$home/.agents/skills/herdr" || return 1

  [[ ! -e "$home/.claude/skills/cmd-debug" ]] || return 1
  [[ ! -e "$home/.pi/agent/skills/linear" ]] || return 1
  [[ ! -e "$home/.pi/agent/skills/cmd-debug" ]] || return 1
}

run_installer() {
  local home="$1"
  shift
  local fake_bin
  fake_bin="$(create_fake_tool_bin "$home")"
  HOME="$home" PATH="$fake_bin:$PATH" bash "$INSTALLER" "$@"
}

run_installer_capture() {
  local home="$1"
  local output_file="$2"
  shift 2
  local fake_bin
  fake_bin="$(create_fake_tool_bin "$home")"
  HOME="$home" PATH="$fake_bin:$PATH" bash "$INSTALLER" "$@" >"$output_file" 2>&1
}

test_skills_mode_installs_additively_and_is_idempotent() {
  local home
  local backup_count_before
  local backup_count_after

  home="$(new_tmp_dir)"
  seed_phase_two_home "$home"

  run_installer "$home" --skills || return 1
  assert_shared_skill_install_state "$home" || return 1

  backup_count_before="$(count_backup_dirs "$home")"
  run_installer "$home" --skills || return 1
  assert_shared_skill_install_state "$home" || return 1
  backup_count_after="$(count_backup_dirs "$home")"
  [[ "$backup_count_before" == "$backup_count_after" ]]
}

test_skills_mode_does_not_update_skills_sh_by_default() {
  local home

  home="$(new_tmp_dir)"
  seed_phase_two_home "$home"

  run_installer "$home" --skills || return 1
  [[ ! -f "$home/.agents/fake-npx-skills-update.log" ]]
}

test_update_modifier_runs_skills_sh_update_before_sync() {
  local home

  home="$(new_tmp_dir)"
  seed_phase_two_home "$home"

  run_installer "$home" --skills --update || return 1
  assert_file_contains "$home/.agents/fake-npx-skills-update.log" 'update -g -y' || return 1
  assert_shared_skill_install_state "$home" || return 1
}

test_update_modifier_normalizes_skills_sh_mutated_managed_skills() {
  local home

  home="$(new_tmp_dir)"
  seed_phase_two_home "$home"

  run_installer "$home" --skills || return 1
  assert_shared_skill_install_state "$home" || return 1

  AI_CONFIGS_FAKE_SKILLS_UPDATE_MUTATES=linear run_installer "$home" --skills --update || return 1
  assert_file_contains "$home/.agents/fake-npx-skills-update.log" 'update -g -y' || return 1
  assert_file_not_contains "$home/.agents/skills/linear/SKILL.md" 'skills.sh-updated-linear' || return 1
  assert_file_contains "$home/.agents/skills/linear/.ai-configs-managed.json" '"source": "skills/linear"' || return 1
  assert_symlink_target "$home/.claude/skills/linear" "$home/.agents/skills/linear" || return 1
}

test_update_modifier_syncs_skills_for_modes_without_normal_skill_sync() {
  local home

  home="$(new_tmp_dir)"
  seed_phase_two_home "$home"

  run_installer "$home" --tools --update || return 1
  assert_file_contains "$home/.agents/fake-npx-skills-update.log" 'update -g -y' || return 1
  assert_file_contains "$home/.agents/skills/linear/.ai-configs-managed.json" '"source": "skills/linear"' || return 1
}

test_default_mode_reuses_shared_sync_without_mutating_repo_root() {
  local home
  local target
  local backup_count_before
  local backup_count_after

  home="$(new_tmp_dir)"
  target="$(new_tmp_dir)"
  seed_phase_two_home "$home"

  run_installer "$home" --skills || return 1
  backup_count_before="$(count_backup_dirs "$home")"

  run_installer "$home" --default "$target" || return 1
  assert_shared_skill_install_state "$home" || return 1
  backup_count_after="$(count_backup_dirs "$home")"
  [[ "$backup_count_before" == "$backup_count_after" ]] || return 1

  [[ -d "$target/.claude" ]] || return 1
  [[ ! -e "$target/.codex" ]] || return 1
  [[ -d "$home/.codex/prompts" ]] || return 1
  [[ ! -e "$target/.gemini" ]] || return 1
}

test_single_surface_modes_reuse_shared_sync() {
  local home
  local target

  home="$(new_tmp_dir)"
  target="$(new_tmp_dir)"
  seed_phase_two_home "$home"
  run_installer "$home" --claude "$target" || return 1
  [[ -d "$home/.agents/skills" ]] || return 1
  assert_symlink_target "$home/.claude/skills/linear" "$home/.agents/skills/linear" || return 1

  home="$(new_tmp_dir)"
  seed_phase_two_home "$home"
  run_installer "$home" --codex || return 1
  [[ -d "$home/.agents/skills" ]] || return 1
  [[ -d "$home/.codex/prompts" ]] || return 1

  home="$(new_tmp_dir)"
  seed_phase_two_home "$home"
  run_installer "$home" --pi || return 1
  [[ -d "$home/.agents/skills" ]] || return 1
  [[ ! -e "$home/.pi/agent/skills/linear" ]] || return 1
  [[ ! -e "$home/.pi/agent/skills/cmd-debug" ]] || return 1
}

test_project_local_central_skill_overrides_are_removed() {
  local home
  local target
  local skill

  home="$(new_tmp_dir)"
  target="$(new_tmp_dir)"
  seed_phase_two_home "$home"

  mkdir -p "$target/.agents/skills/keep-local"
  printf 'keep local\n' > "$target/.agents/skills/keep-local/SKILL.md"

  for skill in ccore todoist-cli; do
    mkdir -p "$target/.agents/skills/$skill" "$home/.agents/skills/$skill"
    printf 'project local %s\n' "$skill" > "$target/.agents/skills/$skill/SKILL.md"
    printf 'central %s\n' "$skill" > "$home/.agents/skills/$skill/SKILL.md"
  done

  run_installer "$home" --default "$target" || return 1

  for skill in ccore todoist-cli; do
    [[ ! -e "$target/.agents/skills/$skill" ]] || return 1
    [[ -f "$home/.agents/skills/$skill/SKILL.md" ]] || return 1
  done

  assert_file_contains "$target/.agents/skills/keep-local/SKILL.md" 'keep local' || return 1

  [[ -n "$(find "$home/.agents/skill-backups/ai-configs" -path '*/project-local/*/ccore/SKILL.md' -print -quit 2>/dev/null)" ]] || return 1
  [[ -n "$(find "$home/.agents/skill-backups/ai-configs" -path '*/project-local/*/todoist-cli/SKILL.md' -print -quit 2>/dev/null)" ]] || return 1
}

test_non_managed_retired_skill_is_preserved() {
  local home
  home="$(new_tmp_dir)"
  mkdir -p "$home/.agents/skills/omp-review-partner" "$home/.agents"
  printf 'user-owned skill\n' > "$home/.agents/skills/omp-review-partner/SKILL.md"
  printf '{"skills":{"omp-review-partner":{"source":"user"}}}\n' > "$home/.agents/.skill-lock.json"

  run_installer "$home" --skills || return 1
  assert_file_contains "$home/.agents/skills/omp-review-partner/SKILL.md" 'user-owned skill' || return 1
  assert_file_contains "$home/.agents/.skill-lock.json" 'omp-review-partner' || return 1
}

test_failpoint_after_backup_keeps_destination_recoverable() {
  local home
  local output_file
  local backup_dir

  home="$(new_tmp_dir)"
  output_file="$(new_tmp_dir)/install.log"
  seed_phase_two_home "$home"

  if AI_CONFIGS_FAILPOINT='after-backup:linear' run_installer_capture "$home" "$output_file" --skills; then
    return 1
  fi

  backup_dir="$(find_backup_dir "$home" linear)"
  [[ -n "$backup_dir" ]] || return 1
  assert_file_contains "$home/.agents/skills/linear/SKILL.md" 'foreign-linear' || return 1
  assert_file_contains "$output_file" 'after-backup:linear' || return 1
  assert_file_contains "$output_file" 'Restore the affected skill from' || return 1
  assert_file_contains "$output_file" '.agents/skill-backups/ai-configs' || return 1
}

test_agent_extension_installs_preserve_or_manage_herdr_extensions() {
  local home
  local output_file
  home="$(new_tmp_dir)"

  mkdir -p \
    "$home/.pi/agent/agents" \
    "$home/.pi/agent/extensions/pi-plan-mode" \
    "$home/.pi/agent/extensions/pi-prd-mode" \
    "$home/.omp/agent/extensions/aplan" \
    "$home/.omp/agent/extensions/foreign" \
    "$home/.config/opencode/commands" \
    "$home/.config/opencode/custom" \
    "$home/.gemini/commands" \
    "$home/.gemini/custom"
  printf 'stale-glm-reviewer\n' > "$home/.pi/agent/agents/quality-reviewer-glm.md"
  printf 'stale-glm-reviewer\n' > "$home/.pi/agent/agents/glm5.2-high.md"
  printf 'stale-glm-reviewer\n' > "$home/.pi/agent/agents/glm5.2-xhigh.md"
  printf 'stale-glm-agent\n' > "$home/.pi/agent/agents/developer-glm.md"
  printf 'stale-glm-agent\n' > "$home/.pi/agent/agents/orchestrator-glm.md"
  printf 'stale-kimi-agent\n' > "$home/.pi/agent/agents/context-builder.md"
  printf 'stale-kimi-agent\n' > "$home/.pi/agent/agents/plan-k2.5.md"
  printf 'stale-kimi-agent\n' > "$home/.pi/agent/agents/prd-researcher.md"
  printf 'pi-herdr-sentinel\n' > "$home/.pi/agent/extensions/herdr-agent-state.ts"
  printf 'legacy-todo-extension\n' > "$home/.pi/agent/extensions/todo.ts"
  printf 'stale-plan-mode\n' > "$home/.pi/agent/extensions/pi-plan-mode/index.ts"
  printf 'stale-prd-mode\n' > "$home/.pi/agent/extensions/pi-prd-mode/index.ts"
  printf 'stale-aplan\n' > "$home/.omp/agent/extensions/aplan/index.ts"
  printf 'foreign-omp\n' > "$home/.omp/agent/extensions/foreign/index.ts"
  printf 'stale-opencode\n' > "$home/.config/opencode/commands/stale.md"
  printf 'custom-opencode\n' > "$home/.config/opencode/custom/keep.txt"
  printf 'stale-gemini\n' > "$home/.gemini/commands/cmd:debug.toml"
  printf 'custom-gemini-command\n' > "$home/.gemini/commands/custom.toml"
  printf 'custom-gemini\n' > "$home/.gemini/custom/keep.txt"
  cat > "$home/.pi/agent/models.json" <<'EOF'
{"providers":{"ollama":{"baseUrl":"https://ollama.com/v1","api":"openai-completions","apiKey":"local-test-key","models":[{"id":"gemma4:latest"},{"id":"kimi-k2.5:cloud"}]},"grok":{"name":"Grok (local CLI Proxy API)","baseUrl":"http://127.0.0.1:8318/v1","api":"openai-completions","apiKey":"local-cliproxyapi","models":[{"id":"grok-4.5","name":"Grok 4.5 (CLI Proxy API)"}]}}}
EOF
  cat > "$home/.pi/agent/settings.json" <<'EOF'
{"defaultProvider":"grok","defaultModel":"grok-composer-2.5-fast","enabledModels":["grok/grok-4.5","grok/grok-composer-2.5-fast","openai-codex/gpt-5.6-sol"],"extensions":[".pi/agent/extensions/pi-prd-mode","npm:caller-owned"],"packages":["npm:@tintinweb/pi-tasks"]}
EOF
  printf '{"taskScope":"session"}\n' > "$home/.pi/agent/tasks-config.json"

  output_file="$home/pi-install.log"
  run_installer_capture "$home" "$output_file" --pi || {
    cat "$output_file" >&2
    return 1
  }
  assert_file_contains "$home/.pi/agent/extensions/herdr-agent-state.ts" 'HERDR_INTEGRATION_ID=pi' || return 1
  assert_file_contains "$home/.pi/agent/extensions/herdr-agent-state.ts" 'managed by ai-configs' || return 1
  assert_file_contains "$home/.pi/agent/extensions/vent.ts" 'join(homedir(), ".pi")' || return 1
  assert_file_contains "$home/.pi/agent/extensions/vent.ts" '~/.pi/VENT.md' || return 1
  [[ ! -e "$home/.pi/agent/extensions/todo.ts" ]] || return 1
  [[ ! -e "$home/.pi/agent/extensions/pi-prd-mode" ]] || return 1
  [[ ! -e "$home/.pi/agent/agents/general-glm.md" ]] || return 1
  [[ ! -e "$home/.pi/agent/agents/ui-design-glm.md" ]] || return 1
  [[ ! -e "$home/.pi/agent/agents/quality-reviewer-k2.5.md" ]] || return 1
  [[ -f "$home/.pi/agent/agents/reviewer.md" ]] || return 1
  assert_file_contains "$home/.pi/agent/agents/reviewer.md" 'name: reviewer' || return 1
  assert_file_contains "$home/.pi/agent/agents/reviewer.md" 'model: openai-codex/gpt-5.6-terra' || return 1
  [[ ! -e "$home/.pi/agent/agents/reviewer-kimi.md" ]] || return 1
  [[ ! -e "$home/.pi/agent/agents/reviewer-plan-kimi.md" ]] || return 1
  [[ ! -e "$home/.pi/agent/agents/reviewer-prd-bdd-flows.md" ]] || return 1
  [[ ! -e "$home/.pi/agent/agents/reviewer-prd-no-stubs.md" ]] || return 1
  [[ ! -e "$home/.pi/agent/agents/review-explore.md" ]] || return 1
  [[ ! -e "$home/.pi/agent/agents/context-builder.md" ]] || return 1
  [[ ! -e "$home/.pi/agent/agents/plan-k2.5.md" ]] || return 1
  [[ ! -e "$home/.pi/agent/agents/prd-researcher.md" ]] || return 1
  [[ ! -e "$home/.pi/agent/agents/researcher.md" ]] || return 1
  [[ -f "$home/.pi/agent/agents/planner.md" ]] || return 1
  assert_file_contains "$home/.pi/agent/agents/planner.md" 'name: planner' || return 1
  assert_file_contains "$home/.pi/agent/agents/planner.md" 'model: openai-codex/gpt-5.6-sol' || return 1
  assert_file_contains "$home/.pi/agent/agents/planner.md" 'reasoningEffort: medium' || return 1
  assert_file_contains "$home/.pi/agent/agents/planner.md" 'independently review an existing plan' || return 1
  assert_file_contains "$home/.pi/agent/agents/scout.md" 'model: openai-codex/gpt-5.6-terra' || return 1
  assert_file_contains "$home/.pi/agent/agents/scout.md" 'reasoningEffort: low' || return 1
  assert_file_contains "$home/.pi/agent/models.json" 'gemma4:latest' || return 1
  assert_file_not_contains "$home/.pi/agent/models.json" 'kimi-k2.5:cloud' || return 1
  assert_file_not_contains "$home/.pi/agent/models.json" '"grok"' || return 1
  assert_file_contains "$home/.pi/agent/models.json" '"grok-4.5"' || return 1
  assert_file_contains "$home/.pi/agent/models.json" '"contextWindow": 200000' || return 1
  assert_file_not_contains "$home/.pi/agent/settings.json" 'grok/' || return 1
  assert_file_not_contains "$home/.pi/agent/settings.json" 'grok-composer-2.5-fast' || return 1
  assert_file_not_contains "$home/.pi/agent/settings.json" 'pi-prd-mode' || return 1
  assert_file_contains "$home/.pi/agent/settings.json" 'npm:caller-owned' || return 1
  assert_file_contains "$home/.pi/agent/settings.json" '"defaultProvider": "openai-codex"' || return 1
  assert_file_contains "$home/.pi/agent/settings.json" '"defaultModel": "gpt-5.6-terra"' || return 1
  [[ ! -e "$home/.pi/agent/tasks-config.json" ]] || return 1
  [[ -f "$home/.pi/agent/agents/Explore.md" ]] || return 1
  [[ "$(cat "$home/.pi/agent/agents/Explore.md")" == $'---\nenabled: false\n---' ]] || return 1
  [[ -z "$(find "$home/.pi/agent/agents" -maxdepth 1 -type f -name 'explore.md' -print -quit)" ]] || return 1
  [[ ! -e "$home/.pi/agent/agents/quality-reviewer-glm.md" ]] || return 1
  [[ ! -e "$home/.pi/agent/agents/glm5.2-high.md" ]] || return 1
  [[ ! -e "$home/.pi/agent/agents/glm5.2-xhigh.md" ]] || return 1
  [[ ! -e "$home/.pi/agent/agents/developer-glm.md" ]] || return 1
  [[ ! -e "$home/.pi/agent/agents/orchestrator-glm.md" ]] || return 1
  assert_file_contains "$home/.pi/agent/extensions/pi-plan-mode/index.ts" 'stale-plan-mode' || return 1
  assert_file_contains "$home/.omp/agent/extensions/aplan/index.ts" 'stale-aplan' || return 1
  assert_file_contains "$home/.omp/agent/extensions/foreign/index.ts" 'foreign-omp' || return 1
  assert_file_contains "$home/.config/opencode/commands/stale.md" 'stale-opencode' || return 1
  assert_file_contains "$home/.config/opencode/custom/keep.txt" 'custom-opencode' || return 1
  assert_file_contains "$home/.gemini/commands/cmd:debug.toml" 'stale-gemini' || return 1
  assert_file_contains "$home/.gemini/commands/custom.toml" 'custom-gemini-command' || return 1
  assert_file_contains "$home/.gemini/custom/keep.txt" 'custom-gemini' || return 1
  assert_file_not_contains "$home/.pi/agent/settings.json" 'pi-codex-goal' || return 1
  assert_file_not_contains "$home/.pi/agent/settings.json" 'piCodexGoal' || return 1
  assert_file_contains "$home/.pi/agent/settings.json" 'npm:@narumitw/pi-goal' || return 1
  assert_file_not_contains "$home/.pi/agent/settings.json" 'npm:@tintinweb/pi-tasks' || return 1
  assert_file_contains "$home/.pi/agent/settings.json" 'npm:@juicesharp/rpiv-todo' || return 1
  assert_file_not_contains "$home/.pi/agent/settings.json" 'npm:pi-cursor-sdk' || return 1
  assert_file_contains "$home/.pi/agent/settings.json" 'local-packages/ai-configs/pi-cursor-sdk' || return 1
  assert_file_contains "$home/.pi/agent/local-packages/ai-configs/pi-cursor-sdk/src/index.ts" 'runtimeIsCurrent = false' || return 1
  assert_file_contains "$home/.pi/agent/local-packages/ai-configs/pi-cursor-sdk/src/cursor-question-tool.ts" 'parseEnvBoolean(env[CURSOR_ASK_QUESTION_ENV], false)' || return 1
  [[ -f "$home/.pi/agent/local-packages/ai-configs/pi-cursor-sdk/node_modules/@cursor/sdk/package.json" ]] || return 1
}

test_pi_install_removes_retired_packages() {
  local home output_file settings_path
  home="$(new_tmp_dir)"
  output_file="$home/pi-install.log"
  settings_path="$home/.pi/agent/settings.json"

  mkdir -p "$(dirname "$settings_path")"
  cat > "$settings_path" <<'JSON'
{
  "piCodexGoal": {"disableTokenBudgets": true},
  "packages": [
    "npm:pi-codex-goal",
    "git:github.com/adnichols/pi-codex-goal",
    "npm:@howaboua/pi-codex-conversion",
    "npm:@howaboua/pi-vent",
    "npm:@ff-labs/pi-fff",
    "npm:pi-side-agents",
    "npm:@fnnm/pi-ast-grep",
    "npm:pi-service-tier",
    "npm:pi-updater"
  ]
}
JSON

  run_installer_capture "$home" "$output_file" --pi || {
    cat "$output_file" >&2
    return 1
  }

  assert_file_contains "$output_file" 'Removing retired Pi goal package npm:pi-codex-goal' || return 1
  assert_file_contains "$output_file" 'Removing retired Pi goal package git:github.com/adnichols/pi-codex-goal' || return 1
  assert_file_contains "$output_file" 'Removing deprecated Pi package @howaboua/pi-codex-conversion' || return 1
  assert_file_contains "$output_file" 'Removing deprecated Pi package @howaboua/pi-vent' || return 1
  assert_file_contains "$output_file" 'Removing deprecated Pi package @ff-labs/pi-fff' || return 1
  assert_file_contains "$output_file" 'Removing deprecated Pi package pi-side-agents' || return 1
  assert_file_contains "$output_file" 'Removing deprecated Pi package @fnnm/pi-ast-grep' || return 1
  assert_file_contains "$output_file" 'Removing deprecated Pi package pi-service-tier' || return 1
  assert_file_contains "$output_file" 'Removing deprecated Pi package pi-updater' || return 1
  assert_file_not_contains "$settings_path" 'pi-codex-goal' || return 1
  assert_file_not_contains "$settings_path" 'piCodexGoal' || return 1
  assert_file_not_contains "$settings_path" '@howaboua/pi-codex-conversion' || return 1
  assert_file_not_contains "$settings_path" '@howaboua/pi-vent' || return 1
  assert_file_not_contains "$settings_path" '@ff-labs/pi-fff' || return 1
  assert_file_not_contains "$settings_path" 'pi-side-agents' || return 1
  assert_file_not_contains "$settings_path" '@fnnm/pi-ast-grep' || return 1
  assert_file_not_contains "$settings_path" 'pi-service-tier' || return 1
  assert_file_not_contains "$settings_path" 'pi-updater' || return 1
}

test_pi_install_replaces_gpt_config_packages() {
  local home output_file settings_path
  home="$(new_tmp_dir)"
  output_file="$home/pi-install.log"
  settings_path="$home/.pi/agent/settings.json"

  mkdir -p "$(dirname "$settings_path")"
  cat > "$settings_path" <<'JSON'
{
  "packages": [
    "git:github.com/edxeth/pi-gpt-config",
    "npm:@howaboua/pi-dynamic-tools"
  ]
}
JSON

  run_installer_capture "$home" "$output_file" --pi || {
    cat "$output_file" >&2
    return 1
  }

  assert_file_contains "$output_file" 'Removing deprecated Pi package git:github.com/edxeth/pi-gpt-config' || return 1
  assert_file_contains "$output_file" 'Removing deprecated Pi package @howaboua/pi-dynamic-tools' || return 1
  assert_file_not_contains "$settings_path" 'git:github.com/edxeth/pi-gpt-config' || return 1
  assert_file_not_contains "$settings_path" 'npm:@howaboua/pi-dynamic-tools' || return 1
  assert_file_contains "$settings_path" 'npm:@howaboua/pi-explore-subagents' || return 1
}

test_verify_pi_install_reports_stale_goal_package() {
  local home fake_bin output_file settings_path
  home="$(new_tmp_dir)"
  fake_bin="$(create_fake_tool_bin "$home")"
  output_file="$home/verify.log"
  settings_path="$home/.pi/agent/settings.json"
  mkdir -p "$home/.pi/agent/extensions" "$(dirname "$settings_path")" "$home/.pi/agent/local-packages/ai-configs/pi-vcc" "$home/.pi/agent/local-packages/ai-configs/pi-cursor-sdk/src" "$home/.pi/agent/local-packages/ai-configs/pi-cursor-sdk/node_modules/@cursor/sdk"
  cp -R "$SCRIPT_DIR/_pi/extensions/." "$home/.pi/agent/extensions/"
  printf '{"name":"@adnichols/pi-vcc"}\n' > "$home/.pi/agent/local-packages/ai-configs/pi-vcc/package.json"
  printf '{"name":"pi-cursor-sdk"}\n' > "$home/.pi/agent/local-packages/ai-configs/pi-cursor-sdk/package.json"
  printf '{"name":"@cursor/sdk"}\n' > "$home/.pi/agent/local-packages/ai-configs/pi-cursor-sdk/node_modules/@cursor/sdk/package.json"
  printf 'return parseEnvBoolean(env[CURSOR_ASK_QUESTION_ENV], false);\n' > "$home/.pi/agent/local-packages/ai-configs/pi-cursor-sdk/src/cursor-question-tool.ts"

  python3 - "$settings_path" "$home/.pi/agent/local-packages/ai-configs/pi-vcc" "$home/.pi/agent/local-packages/ai-configs/pi-cursor-sdk" <<'PY'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
pi_vcc = sys.argv[2]
pi_cursor_sdk = sys.argv[3]
packages = [
    "npm:@tintinweb/pi-subagents",
    "npm:@aliou/pi-processes",
    "npm:@narumitw/pi-goal",
    "npm:pi-web-access",
    "npm:pi-no-soft-cursor",
    "npm:@tmustier/pi-files-widget",
    "npm:@tmustier/pi-raw-paste",
    "npm:@ff-labs/pi-fff",
    "npm:pi-side-agents",
    "npm:@pi-kaush/pi-inline-skill-identifier",
    "npm:@howaboua/pi-vent",
    "npm:@howaboua/pi-codex-conversion",
    "npm:@howaboua/pi-explore-subagents",
    "npm:pi-codex-goal",
    pi_vcc,
    pi_cursor_sdk,
]
packages.append("git:github.com/adnichols/pi-interactive-shell")
settings_path.write_text(json.dumps({"packages": packages}, indent=2) + "\n")
PY

  if HOME="$home" PATH="$fake_bin:$PATH" PI_AGENT_DIR="$home/.pi/agent" bash "$SCRIPT_DIR/scripts/verify-pi-install.sh" >"$output_file" 2>&1; then
    cat "$output_file" >&2
    return 1
  fi
  if ! grep -Fq 'retired pi-codex-goal package is still registered' "$output_file" ||
    ! grep -Fq 'retired @howaboua/pi-codex-conversion package is still registered' "$output_file" ||
    ! grep -Fq 'retired @ff-labs/pi-fff package is still registered' "$output_file" ||
    ! grep -Fq 'retired pi-side-agents package is still registered' "$output_file" ||
    ! grep -Fq 'retired pi-interactive-shell package is still registered' "$output_file"; then
    cat "$output_file" >&2
    return 1
  fi
}

test_pi_install_removes_retired_interactive_shell_when_pi_list_fails() {
  local home output_file settings_path stale_local
  home="$(new_tmp_dir)"
  output_file="$home/pi-install.log"
  settings_path="$home/.pi/agent/settings.json"
  stale_local="$(new_tmp_dir)/pi-interactive-shell"

  mkdir -p "$stale_local" "$(dirname "$settings_path")"
  cat > "$settings_path" <<JSON
{
  "packages": [
    "git:github.com/adnichols/pi-interactive-shell",
    { "source": "$stale_local" }
  ]
}
JSON

  AI_CONFIGS_FAKE_PI_LIST_FAILS=1 run_installer_capture "$home" "$output_file" --pi || {
    cat "$output_file" >&2
    return 1
  }

  assert_file_contains "$output_file" 'Removing retired pi-interactive-shell package git:github.com/adnichols/pi-interactive-shell' || return 1
  assert_file_contains "$output_file" "Removing retired pi-interactive-shell package $stale_local" || return 1
  assert_file_not_contains "$settings_path" 'pi-interactive-shell' || return 1
}

test_pi_doctrine_renderer_tracks_exact_git_state() {
  local repo non_git source target commit expected
  repo="$(new_tmp_dir)/repo"
  non_git="$(new_tmp_dir)/non-git"
  source="$repo/APPEND_SYSTEM.md"
  target="$repo/rendered.md"
  mkdir -p "$repo" "$non_git"

  printf 'Doctrine-Version: {{AI_CONFIGS_VERSION}}\n' > "$source"
  printf 'unrelated\n' > "$repo/unrelated.txt"
  git -C "$repo" init -q
  git -C "$repo" config user.name 'ai-configs test'
  git -C "$repo" config user.email 'ai-configs-test@example.invalid'
  git -C "$repo" add APPEND_SYSTEM.md unrelated.txt
  git -C "$repo" commit -q -m 'test doctrine source'
  commit="$(git -C "$repo" rev-parse --short=8 HEAD)"
  expected="2026-07-13+$commit"

  python3 scripts/render_pi_append_system.py --repo "$repo" --source "$source" --target "$target" --date 2026-07-13 >/dev/null || return 1
  [[ "$(head -n 1 "$target")" == "Doctrine-Version: $expected" ]] || return 1

  printf 'changed unrelated\n' > "$repo/unrelated.txt"
  python3 scripts/render_pi_append_system.py --repo "$repo" --source "$source" --target "$target" --date 2026-07-13 >/dev/null || return 1
  [[ "$(head -n 1 "$target")" == "Doctrine-Version: $expected" ]] || return 1

  printf '\nchanged doctrine\n' >> "$source"
  python3 scripts/render_pi_append_system.py --repo "$repo" --source "$source" --target "$target" --date 2026-07-13 >/dev/null || return 1
  [[ "$(head -n 1 "$target")" == "Doctrine-Version: $expected-dirty" ]] || return 1

  git -C "$repo" update-index --assume-unchanged APPEND_SYSTEM.md
  python3 scripts/render_pi_append_system.py --repo "$repo" --source "$source" --target "$target" --date 2026-07-13 >/dev/null || return 1
  [[ "$(head -n 1 "$target")" == "Doctrine-Version: $expected-dirty" ]] || return 1
  git -C "$repo" update-index --no-assume-unchanged APPEND_SYSTEM.md

  git -C "$repo" update-index --skip-worktree APPEND_SYSTEM.md
  python3 scripts/render_pi_append_system.py --repo "$repo" --source "$source" --target "$target" --date 2026-07-13 >/dev/null || return 1
  [[ "$(head -n 1 "$target")" == "Doctrine-Version: $expected-dirty" ]] || return 1
  git -C "$repo" update-index --no-skip-worktree APPEND_SYSTEM.md

  printf 'Doctrine-Version: {{AI_CONFIGS_VERSION}}\n' > "$non_git/APPEND_SYSTEM.md"
  if python3 scripts/render_pi_append_system.py --repo "$non_git" --source "$non_git/APPEND_SYSTEM.md" --target "$non_git/rendered.md" --date 2026-07-13 >/dev/null 2>&1; then
    return 1
  fi
}

test_pi_interaction_doctrine_is_versioned_and_read_only_by_default() {
  local home output_file installed_doctrine expected_version
  home="$(new_tmp_dir)"
  output_file="$home/pi-install.log"
  installed_doctrine="$home/.pi/agent/APPEND_SYSTEM.md"

  run_installer_capture "$home" "$output_file" --pi || {
    cat "$output_file" >&2
    return 1
  }

  [[ -f "$installed_doctrine" ]] || return 1
  expected_version="$(date +%F)+$(git rev-parse --short=8 HEAD)"
  if ! git diff --quiet HEAD -- APPEND_SYSTEM.md; then
    expected_version="$expected_version-dirty"
  fi
  [[ "$(head -n 1 "$installed_doctrine")" == "Doctrine-Version: $expected_version" ]] || return 1
  assert_file_not_contains "$installed_doctrine" '{{AI_CONFIGS_VERSION}}' || return 1
  assert_file_contains "$installed_doctrine" 'do not by themselves authorize implementation' || return 1
  assert_file_contains "$installed_doctrine" 'Do not edit files, run state-changing commands, create execution todos' || return 1
  assert_file_contains "$installed_doctrine" 'does not broaden the set of authorized actions' || return 1

  assert_file_contains "APPEND_SYSTEM.md" 'Doctrine-Version: {{AI_CONFIGS_VERSION}}' || return 1
  assert_file_not_contains "APPEND_SYSTEM.md" 'assume they want you to act' || return 1
  [[ ! -e "_pi/extensions/todo.ts" ]] || return 1
  assert_file_contains "_pi/README.md" 'Task tracking is provided exclusively' || return 1
  assert_file_contains "AGENTS.md" 'Interaction authority boundary' || return 1
  assert_file_contains "README.md" 'request-type-first' || return 1
  assert_file_contains "_pi/README.md" 'request-type-first' || return 1
}

test_integration_integrity_is_common_and_portable() {
  local home output_file installed_doctrine
  home="$(new_tmp_dir)"
  output_file="$home/pi-install.log"
  installed_doctrine="$home/.pi/agent/APPEND_SYSTEM.md"

  run_installer_capture "$home" "$output_file" --pi || {
    cat "$output_file" >&2
    return 1
  }

  for path in \
    "APPEND_SYSTEM.md" \
    "$installed_doctrine" \
    "skills/repo-agents-bootstrap/SKILL.md" \
    "skills/repo-agents-bootstrap/references/root_agents_template.md"; do
    assert_file_contains "$path" 'Integration integrity' || return 1
    assert_file_contains "$path" 'source of truth' || return 1
    assert_file_contains "$path" 'dependent' || return 1
    assert_file_contains "$path" 'cross-boundary' || return 1
    assert_file_contains "$path" 'production-path' || return 1
  done

  assert_file_contains "APPEND_SYSTEM.md" 'If neither trigger applies' || return 1
  assert_file_contains "APPEND_SYSTEM.md" 'After changing a shared contract' || return 1
  assert_file_contains "APPEND_SYSTEM.md" 'after compaction, handoff, or resume' || return 1
  assert_file_contains "APPEND_SYSTEM.md" 'event-existence test' || return 1
  assert_file_contains "skills/repo-agents-bootstrap/references/root_agents_template.md" 'not only plan execution' || return 1
  assert_file_contains "skills/repo-agents-bootstrap/references/root_agents_template.md" 'arbitrary external repositories that have not adopted the template' || return 1
}

test_integration_integrity_materializes_across_workflows() {
  python3 - <<'PY'
from pathlib import Path


def section(path, start, end):
    text = Path(path).read_text()
    try:
        return text[text.index(start):text.index(end, text.index(start) + len(start))]
    except ValueError as exc:
        raise SystemExit(f'{path} missing required section boundary: {exc}')

planning = section(
    'skills/planning-workflow/SKILL.md',
    '## Integration-integrity planning contract',
    '## Canonical plan contract',
).lower()
for phrase in [
    'exact contract',
    'distributed',
    'contract and distributed-integration inventory',
    'source of truth',
    'producer',
    'consumer',
    'cross-boundary',
    'exhaustive-by-site',
    'exhaustive-by-family',
    'justified representative',
    'helper, middleware, wrapper, or event-existence assertion',
    'actual parser',
    'none identified, based on <source search>',
]:
    if phrase not in planning:
        raise SystemExit(f'planning integration contract missing: {phrase}')

execution = section(
    'skills/run-plan/SKILL.md',
    '## Integration-integrity record',
    '## Scope Classification',
).lower()
for phrase in [
    'base execution doctrine governs direct work',
    'coverage ledger',
    'source of truth',
    'producers and consumers',
    'dependent documentation/examples',
    'after compaction, handoff, resume, rebase',
    'readers, writers, importers, string references',
    'named remediation work',
    'actual parser',
]:
    if phrase not in execution:
        raise SystemExit(f'run-plan integration record missing: {phrase}')

for path in [
    'skills/run-plan/SKILL.md',
    '_hermes/default/skills/software-development/run-plan/SKILL.md',
]:
    text = Path(path).read_text().lower()
    for phrase in [
        'integration-integrity evidence (when triggered)',
        'source of truth; producer/consumer or source-derived inventory',
        'coverage declaration',
        'reconciliation state',
        'real boundary or production-dispatch proof',
        'stale-reference search result',
        'actual-parser proof',
        'helper-only, wrapper-only, middleware-only, or event-existence-only evidence',
        'prior runtime-native review may satisfy this gate only',
    ]:
        if phrase not in text:
            raise SystemExit(f'{path} reviewer packet misses integration evidence: {phrase}')

review = Path('skills/autoreview/SKILL.md').read_text().lower()
for phrase in [
    "executor's **integration-integrity record**",
    'source-search-backed operation inventory',
    'reviewer validates the supplied evidence',
    'exact-contract evidence',
    'distributed-behavior evidence',
    'event-existence tests are not completion proof',
]:
    if phrase not in review:
        raise SystemExit(f'autoreview packet contract missing: {phrase}')

reviewed_plan = Path('skills/reviewed-html-plan/SKILL.md').read_text().lower()
for phrase in [
    'contract and distributed-integration inventory',
    'none identified, based on <source search>',
    'justified-representative coverage declaration',
    'actual parser',
    'reject helper-only, wrapper-only, middleware-only, or event-existence-only completion claims',
]:
    if phrase not in reviewed_plan:
        raise SystemExit(f'reviewed-plan contract missing: {phrase}')

for path in ['skills/dev-plan/SKILL.md', '_pi/prompts/dev:plan.md']:
    text = Path(path).read_text().lower()
    if 'canonical `planning-workflow` integration-integrity planning contract' not in text:
        raise SystemExit(f'{path} does not delegate to the canonical integration contract')
    if 'none identified, based on <source search>' not in text:
        raise SystemExit(f'{path} does not preserve the no-trigger record')

reviewer = Path('_pi/agents/reviewer.md').read_text().lower()
for forbidden in ['integration-integrity record', 'contract and distributed-integration inventory']:
    if forbidden in reviewer:
        raise SystemExit(f'generic reviewer must not own workflow-specific integration rule: {forbidden}')
PY
}

test_tdd_test_writer_is_direct_and_distributed() {
  local home
  home="$(new_tmp_dir)"
  mkdir -p "$home/.claude/skills"

  python3 - <<'PY'
import json
from pathlib import Path

skill = Path('skills/tdd-test-writer/SKILL.md')
if not skill.is_file():
    raise SystemExit('missing repo-owned tdd-test-writer source')
text = skill.read_text().lower()
for phrase in [
    'name: tdd-test-writer',
    'driving agent writes and runs the red tests directly',
    'do not delegate test authoring',
    'do not modify production code during red',
    'expected behavioral reason',
    'cross-boundary',
    'production-dispatch',
    'actual parser',
    'do not weaken, delete, or bypass the red test',
]:
    if phrase not in text:
        raise SystemExit(f'tdd-test-writer missing direct-authoring contract: {phrase}')
for forbidden in ['tdd_test_writer', 'spawn a subagent', 'delegate test authoring to']:
    if forbidden in text:
        raise SystemExit(f'tdd-test-writer retains forbidden delegation: {forbidden}')

entry = json.loads(Path('skills/install-matrix.json').read_text())['installableSkills'].get('tdd-test-writer')
if entry is None:
    raise SystemExit('install matrix is missing tdd-test-writer')
expected = {
    'class': 'universal-installable',
    'canonicalSource': 'skills/tdd-test-writer',
    'sourceType': 'repo',
    'allowedConsumers': ['codex', 'claude', 'pi'],
}
for key, value in expected.items():
    if entry.get(key) != value:
        raise SystemExit(f'tdd-test-writer matrix {key}={entry.get(key)!r}, expected {value!r}')
PY

  run_installer "$home" --skills || return 1
  cmp "skills/tdd-test-writer/SKILL.md" "$home/.agents/skills/tdd-test-writer/SKILL.md" || return 1
  assert_file_contains "$home/.agents/skills/tdd-test-writer/.ai-configs-managed.json" '"source": "skills/tdd-test-writer"' || return 1
  assert_symlink_target "$home/.claude/skills/tdd-test-writer" "$home/.agents/skills/tdd-test-writer" || return 1
}

test_hermes_integration_integrity_mirrors_are_reconciled() {
  python3 - <<'PY'
from pathlib import Path

required = {
    '_hermes/default/skills/software-development/planning-workflow/SKILL.md': [
        'Integration-integrity planning contract', 'source of truth', 'actual parser',
    ],
    '_hermes/default/skills/software-development/writing-plans/SKILL.md': [
        'Integration-integrity planning contract', 'source of truth', 'actual parser',
    ],
    '_hermes/default/skills/software-development/plan/SKILL.md': [
        'integration-integrity planning contract', 'None identified, based on <source search>',
    ],
    '_hermes/default/skills/software-development/dev-plan/SKILL.md': [
        'integration-integrity planning contract', 'None identified, based on <source search>',
    ],
    '_hermes/default/profiles/nerd/skills/software-development/plan/SKILL.md': [
        'integration-integrity planning contract', 'None identified, based on <source search>',
    ],
    '_hermes/default/profiles/nerd/skills/software-development/writing-plans/SKILL.md': [
        'integration-integrity planning contract', 'None identified, based on <source search>',
    ],
    '_hermes/default/skills/software-development/reviewed-html-plan/SKILL.md': [
        'Contract and distributed-integration inventory', 'actual parser', 'event-existence-only',
    ],
    '_hermes/default/skills/software-development/run-plan/SKILL.md': [
        'Integration-integrity record', 'after compaction, handoff, resume, rebase', 'named remediation task',
    ],
    '_hermes/default/skills/software-development/test-driven-development/SKILL.md': [
        'Contract and distributed-behavior RED tests', 'driving agent', 'production-dispatch', 'actual parser',
    ],
    '_hermes/default/profiles/nerd/skills/software-development/test-driven-development/SKILL.md': [
        'Contract and distributed-behavior RED tests', 'driving agent', 'production-dispatch', 'actual parser',
    ],
}
for raw_path, phrases in required.items():
    path = Path(raw_path)
    text = path.read_text()
    missing = [phrase for phrase in phrases if phrase not in text]
    if missing:
        raise SystemExit(f'{path} missing reconciled integration guidance: {missing}')
PY
}

test_phase_three_docs_use_canonical_shared_skill_paths() {
  assert_file_contains "AGENTS.md" '"skills": ["skills"]' || return 1
  assert_file_not_contains "AGENTS.md" '"skills": [".agents/skills", "opencode/skills"]' || return 1
  assert_file_contains "README.md" 'skills/install-matrix.json' || return 1
  assert_file_contains "_pi/README.md" 'skills/install-matrix.json' || return 1

  assert_file_contains "_pi/prompts/cmd:send-plan-to-doct.md" 'doct-agent plans register' || return 1
  assert_file_contains "_codex/prompts/cmd:send-plan-to-doct.md" 'doct-agent plans register' || return 1
  assert_file_not_contains "_pi/prompts/cmd:send-plan-to-doct.md" 'publish-coding-plan.sh' || return 1
  assert_file_not_contains "_codex/prompts/cmd:send-plan-to-doct.md" 'publish-coding-plan.sh' || return 1

  assert_file_contains "skills/install-matrix.json" '"playwright-skill"' || return 1
  assert_file_contains "skills/install-matrix.json" '"packageSource": "lackeyjb/playwright-skill"' || return 1

}

test_phase_three_duplicate_skill_trees_are_removed() {
  [[ ! -d ".agents/skills/dependency-selection" ]] || return 1
  [[ ! -d "_pi/skills" ]] || return 1
  [[ ! -d "_opencode" ]] || return 1
  [[ ! -d "_omp" ]] || return 1
  [[ ! -d "_gemini" ]] || return 1
  [[ ! -d "_pi/extensions/pi-plan-mode" ]] || return 1

  [[ ! -d "skills/algorithmic-art" ]] || return 1
  [[ ! -d "skills/brand-guidelines" ]] || return 1
  [[ ! -d "skills/canvas-design" ]] || return 1
  [[ -d "skills/design-skill" ]] || return 1
  [[ ! -d "skills/doc-coauthoring" ]] || return 1
  [[ ! -d "skills/docx" ]] || return 1
  [[ ! -d "skills/frontend-design" ]] || return 1
  [[ ! -d "skills/internal-comms" ]] || return 1
  [[ ! -d "skills/mcp-builder" ]] || return 1
  [[ ! -d "skills/pdf" ]] || return 1
  [[ ! -d "skills/playwright-skill" ]] || return 1
  [[ ! -d "skills/pptx" ]] || return 1
  [[ ! -d "skills/rust-engineer" ]] || return 1
  [[ ! -d "skills/skill-creator" ]] || return 1
  [[ ! -d "skills/slack-gif-creator" ]] || return 1
  [[ ! -d "skills/theme-factory" ]] || return 1
  [[ ! -d "skills/vercel-react-best-practices" ]] || return 1
  [[ ! -d "skills/web-artifacts-builder" ]] || return 1
  [[ ! -d "skills/web-design-guidelines" ]] || return 1
  [[ ! -d "skills/webapp-testing" ]] || return 1
  [[ ! -d "skills/xlsx" ]] || return 1

}


test_plan_authoring_contract_is_product_owner_friendly() {
  python3 - <<'PY'
from pathlib import Path

canonical = [
    Path('skills/planning-workflow/SKILL.md'),
    Path('skills/reviewed-html-plan/SKILL.md'),
    Path('skills/dev-plan/SKILL.md'),
]
hermes_authoring_surfaces = [
    Path('_hermes/default/skills/software-development/planning-workflow/SKILL.md'),
    Path('_hermes/default/skills/software-development/reviewed-html-plan/SKILL.md'),
    Path('_hermes/default/skills/software-development/dev-plan/SKILL.md'),
    Path('_hermes/default/skills/software-development/plan/SKILL.md'),
    Path('_hermes/default/skills/software-development/writing-plans/SKILL.md'),
    Path('_hermes/default/profiles/nerd/skills/software-development/plan/SKILL.md'),
    Path('_hermes/default/profiles/nerd/skills/software-development/writing-plans/SKILL.md'),
]
required_impacts = [
    'Customers',
    'Runtime product behavior',
    'Security / permissions',
    'Testing / release confidence',
    'Deployment / migration',
]
for path in canonical + hermes_authoring_surfaces:
    text = path.read_text()
    missing = [label for label in required_impacts if label not in text]
    if missing:
        raise SystemExit(f'{path} missing product-owner impact dimensions: {missing}')
    lowered = text.lower()
    for phrase in ['product-owner context', 'needed now', 'stale test']:
        if phrase not in lowered:
            raise SystemExit(f'{path} missing product-owner contract phrase: {phrase}')
    if 'lightweight plans must' not in lowered and 'a lightweight plan must' not in lowered:
        raise SystemExit(f'{path} must require concise product-owner context for lightweight plans')

universal_context_surfaces = [
    Path('skills/planning-workflow/SKILL.md'),
    Path('skills/dev-plan/SKILL.md'),
    Path('_hermes/default/skills/software-development/planning-workflow/SKILL.md'),
    Path('_hermes/default/skills/software-development/writing-plans/SKILL.md'),
    Path('_hermes/default/skills/software-development/dev-plan/SKILL.md'),
    Path('_hermes/default/skills/software-development/plan/SKILL.md'),
    Path('_hermes/default/profiles/nerd/skills/software-development/plan/SKILL.md'),
    Path('_hermes/default/profiles/nerd/skills/software-development/writing-plans/SKILL.md'),
]
for path in universal_context_surfaces:
    if 'every implementation plan' not in path.read_text().lower():
        raise SystemExit(f'{path} scopes product-owner context too narrowly')

prompt_and_workflow_surfaces = [
    Path('_pi/prompts/dev:plan.md'),
    Path('_codex/prompts/dev:plan.md'),
    Path('_claude/commands/dev:plan.md'),
    Path('_pi/prompts/dev:plan-from-prd.md'),
    Path('_codex/prompts/dev:plan-from-prd.md'),
    Path('_pi/prompts/cmd:start-linear-issue-branch.md'),
    Path('_codex/prompts/cmd:start-linear-issue-branch.md'),
    Path('_claude/commands/cmd:start-linear-issue-branch.md'),
]
prompt_impact_phrases = {
    'Customers': ['customers'],
    'Runtime product behavior': ['runtime product behavior'],
    'Security / permissions': ['security / permissions', 'security or permissions'],
    'Testing / release confidence': ['testing / release confidence', 'testing or release confidence'],
    'Deployment / migration': ['deployment / migration', 'deployment or migration'],
}
for path in prompt_and_workflow_surfaces:
    lowered = path.read_text().lower()
    for phrase in ['product-owner context', 'needed now', 'stale test']:
        if phrase not in lowered:
            raise SystemExit(f'{path} missing product-owner prompt contract: {phrase}')
    if 'must use' not in lowered or 'concise labeled prose' not in lowered:
        raise SystemExit(f'{path} must require concise product-owner context for lightweight plans')
    for label, alternatives in prompt_impact_phrases.items():
        if not any(phrase in lowered for phrase in alternatives):
            raise SystemExit(f'{path} missing product-owner impact dimension: {label}')

planning = canonical[0].read_text()
if planning.index('Product-owner context (situation') > planning.index('Current implementation reality'):
    raise SystemExit('planning-workflow must place product-owner context before technical reality')
if planning.index('Product-owner context (situation') > planning.index('Decision Attention / Low-confidence Areas'):
    raise SystemExit('planning-workflow must place product-owner context before Decision Attention')

reviewed = canonical[1].read_text()
if reviewed.index('standalone `Product-owner context`') > reviewed.index('a near-top `Decision Attention'):
    raise SystemExit('reviewed-html-plan must put product-owner context before Decision Attention')
for phrase in ['dark-mode theme', 'full-width single-column', 'listenerInstructions', 'BDD scenarios']:
    if phrase not in reviewed:
        raise SystemExit(f'reviewed-html-plan lost preserved contract: {phrase}')

# Extended What's new contract coverage.
from pathlib import Path

planning_path = Path('skills/planning-workflow/SKILL.md')
planning = planning_path.read_text()
planning_lower = planning.lower()

# The complete semantic contract is canonical in planning-workflow and structurally
# ordered after Product-owner context and before Goal.
contract_heading = "### What's new contract"
if planning.count(contract_heading) != 1:
    raise SystemExit('planning-workflow must define exactly one standalone What\'s new contract')
required_details = [
    'behavior-focused headline',
    'one-sentence promise',
    'concrete audience-visible changes',
    'before/after workflow',
    'observable result',
    'preserved guarantees',
]
contract_start = planning.index(contract_heading)
contract_end = planning.index('\nRequired sections for new plans', contract_start + len(contract_heading))
contract = planning[contract_start:contract_end].lower()
for phrase in required_details:
    if phrase not in contract:
        raise SystemExit(f'canonical What\'s new contract missing semantic requirement: {phrase}')
for forbidden in ['must not restate goal', 'rationale', 'phases', 'acceptance criteria']:
    if forbidden not in contract:
        raise SystemExit(f'canonical What\'s new contract missing non-restatement guard: {forbidden}')
if 'only work already exempt from a full execution plan' not in contract:
    raise SystemExit('canonical What\'s new contract must preserve the existing trivial-work exemption boundary')

required_section_lines = [
    '3. Product-owner context (situation, why now, key conclusion, and impact breakdown)',
    "4. What's new (standalone product change and preserved guarantees)",
    '5. Goal',
]
positions = []
for line in required_section_lines:
    if line not in planning:
        raise SystemExit(f'planning-workflow required-section list missing: {line}')
    positions.append(planning.index(line))
if positions != sorted(positions):
    raise SystemExit("planning-workflow must order Product-owner context -> What's new -> Goal")
if contract_start < planning.index('### Product-owner context contract'):
    raise SystemExit("canonical What's new contract must follow Product-owner context contract")
if "missing, late, vague, or duplicative" not in planning_lower:
    raise SystemExit("planning-workflow ready bar must reject missing, late, vague, or duplicative What's new content")

# Active authoring routes must delegate to the canonical contract rather than
# silently relying on a heading or copying the full semantic definition.
authoring_surfaces = [
    Path('skills/dev-plan/SKILL.md'),
    Path('_pi/agents/planner.md'),
    Path('_pi/prompts/dev:plan.md'),
    Path('_pi/prompts/dev:plan-from-prd.md'),
    Path('_pi/prompts/cmd:start-linear-issue-branch.md'),
    Path('_codex/prompts/dev:plan.md'),
    Path('_codex/prompts/dev:plan-from-prd.md'),
    Path('_codex/prompts/cmd:start-linear-issue-branch.md'),
    Path('_claude/commands/dev:plan.md'),
    Path('_claude/commands/cmd:start-linear-issue-branch.md'),
]
for path in authoring_surfaces:
    lowered = path.read_text().lower()
    if "what's new" not in lowered or 'planning-workflow' not in lowered:
        raise SystemExit(f'{path} must delegate active authoring to the canonical What\'s new contract')
    if 'after product-owner context and before goal' not in lowered:
        raise SystemExit(f'{path} must preserve the canonical early section order')
    if all(phrase in lowered for phrase in required_details):
        raise SystemExit(f'{path} duplicates the full canonical semantic contract instead of referencing it')

# Reviewed-plan and PM packets must assess semantic sufficiency and refuse an
# execution-ready verdict for structural or content failures.
review_surfaces = [
    Path('skills/reviewed-html-plan/SKILL.md'),
    Path('_pi/prompts/dev:pm-review.md'),
    Path('_codex/prompts/dev:pm-review.md'),
]
for path in review_surfaces:
    lowered = path.read_text().lower()
    for phrase in ["what's new", 'missing', 'late', 'vague', 'duplicative', 'execution-ready']:
        if phrase not in lowered:
            raise SystemExit(f'{path} missing reviewed-plan blocker instruction: {phrase}')
    if 'do not' not in lowered or 'verdict' not in lowered:
        raise SystemExit(f'{path} must explicitly withhold an execution-ready verdict')
    if 'heading alone' not in lowered and 'mere heading' not in lowered:
        raise SystemExit(f'{path} must reject heading-only compliance')

# Product doctrine and bootstrap surfaces point to the canonical rule; adopting
# repos are told to enforce its semantics in their own templates/validators.
for path in [
    Path('skills/product-principles/SKILL.md'),
    Path('skills/repo-agents-bootstrap/SKILL.md'),
    Path('skills/repo-agents-bootstrap/references/plan_agents_template.md'),
]:
    lowered = path.read_text().lower()
    if "what's new" not in lowered or 'planning-workflow' not in lowered:
        raise SystemExit(f'{path} must reference the canonical planning-workflow What\'s new contract')
for path in [
    Path('skills/repo-agents-bootstrap/SKILL.md'),
    Path('skills/repo-agents-bootstrap/references/plan_agents_template.md'),
]:
    lowered = path.read_text().lower()
    if 'template' not in lowered or 'validator' not in lowered or 'canonical semantics' not in lowered:
        raise SystemExit(f'{path} must tell adopting repos to map canonical semantics into local templates/validators')

# Managed Hermes guidance is intentionally workflow-specific. Its two full
# authoring contracts must carry the canonical semantics inside the What's new
# section itself; placing these words elsewhere in the file must not satisfy this check.
hermes_contract_surfaces = [
    Path('_hermes/default/skills/software-development/planning-workflow/SKILL.md'),
    Path('_hermes/default/skills/software-development/writing-plans/SKILL.md'),
]
hermes_required_details = [
    'behavior-focused headline',
    'one-sentence product promise',
    'concrete audience-visible changes',
    'before/after workflow',
    'observable result',
    'preserved guarantees',
]
hermes_non_restatements = ['goal', 'rationale', 'phases', 'acceptance criteria']
for path in hermes_contract_surfaces:
    text = path.read_text()
    heading = "### What's new contract"
    if text.count(heading) != 1:
        raise SystemExit(f'{path} must define exactly one managed Hermes What\'s new contract')
    start = text.index(heading)
    end = text.index('\nRequired sections for new plans', start + len(heading))
    contract = text[start:end].lower()
    if 'after product-owner context and before goal' not in contract:
        raise SystemExit(f'{path} missing managed Hermes What\'s new ordering equivalence in its contract section')
    for phrase in hermes_required_details:
        if phrase not in contract:
            raise SystemExit(f'{path} managed Hermes What\'s new contract missing semantic requirement: {phrase}')
    if 'must not restate' not in contract:
        raise SystemExit(f'{path} managed Hermes What\'s new contract must explicitly prohibit restatement')
    for phrase in hermes_non_restatements:
        if phrase not in contract:
            raise SystemExit(f'{path} managed Hermes What\'s new contract missing non-restatement target: {phrase}')

# Other managed Hermes routes keep their workflow-specific delegation wording.
hermes_delegating_surfaces = [
    Path('_hermes/default/skills/software-development/dev-plan/SKILL.md'),
    Path('_hermes/default/skills/software-development/plan/SKILL.md'),
    Path('_hermes/default/profiles/nerd/skills/software-development/plan/SKILL.md'),
    Path('_hermes/default/profiles/nerd/skills/software-development/writing-plans/SKILL.md'),
]
for path in hermes_delegating_surfaces:
    lowered = path.read_text().lower()
    if "what's new" not in lowered or 'after product-owner context and before goal' not in lowered:
        raise SystemExit(f'{path} missing managed Hermes What\'s new ordering equivalence')

# The independent GPT reviewer's required concern list must carry this gate.
# PM-only wording or wording elsewhere in reviewed-html-plan must not pass.
hermes_reviewed_path = Path('_hermes/default/skills/software-development/reviewed-html-plan/SKILL.md')
hermes_reviewed = hermes_reviewed_path.read_text()
gpt_section_start = hermes_reviewed.index('### 6. Active-harness plan review')
gpt_section_end = hermes_reviewed.index('### 7. Integrate and iterate to execution-ready', gpt_section_start)
gpt_section = hermes_reviewed[gpt_section_start:gpt_section_end]
concerns_start = gpt_section.index('For the single plan-review pass, stay limited to readiness concerns, including at least:')
concerns_end = gpt_section.index('\nFor every reviewer, use bounded scope rather than parent-side turn caps.', concerns_start)
gpt_concerns = gpt_section[concerns_start:concerns_end].lower()
for phrase in [
    "what's new",
    'present immediately after product-owner context and before goal',
    'behavior-focused headline',
    'one-sentence product promise',
    'concrete audience-visible changes',
    'before/after workflow',
    'observable result',
    'preserved guarantees',
    'does not restate goal, rationale, phases, or acceptance criteria',
]:
    if phrase not in gpt_concerns:
        raise SystemExit(f'managed Hermes independent GPT concern list missing What\'s new requirement: {phrase}')

# The current architecture must not regain dependencies on retired specialist
# planner/reviewer agents.
retired = sorted(Path('_pi/agents').glob('plan-*.md')) + sorted(Path('_pi/agents').glob('reviewer-plan-*.md'))
if retired:
    raise SystemExit(f'retired specialist plan agents must remain absent: {retired}')
for path in authoring_surfaces + review_surfaces:
    lowered = path.read_text().lower()
    if 'reviewer-plan-' in lowered or '_pi/agents/plan-' in lowered:
        raise SystemExit(f'{path} depends on retired specialist plan-agent paths')

reviewed = Path('skills/reviewed-html-plan/SKILL.md').read_text()
for phrase in ['dark-mode theme', 'full-width single-column', 'listenerInstructions', 'BDD scenarios']:
    if phrase not in reviewed:
        raise SystemExit(f'reviewed-html-plan lost preserved contract: {phrase}')
PY
}

test_codex_pi_skill_and_prompt_parity() {
  python3 - <<'PY'
import json
from pathlib import Path

matrix = json.loads(Path('skills/install-matrix.json').read_text())['installableSkills']
missing_codex = [
    name
    for name, meta in sorted(matrix.items())
    if 'pi' in meta.get('allowedConsumers', [])
    and 'codex' not in meta.get('allowedConsumers', [])
]
if missing_codex:
    raise SystemExit(f"Pi skills missing Codex parity: {missing_codex}")

pi_prompts = {path.name for path in Path('_pi/prompts').glob('*.md')}
codex_prompts = {path.name for path in Path('_codex/prompts').glob('*.md') if path.name != 'README.md'}
missing_prompts = sorted(pi_prompts - codex_prompts)
if missing_prompts:
    raise SystemExit(f"Pi prompts missing Codex parity: {missing_prompts}")

pi_delegated = [
    'cmd:feeling-lucky-pr.md',
    'cmd:feeling-lucky-pr-os.md',
    'prd:clarify-round.md',
    'review:change-claude-code.md',
    'review:change-opus.md',
    'review:plan.md',
    'review:plan-adversarial.md',
    'review:prd.md',
]
for prompt in pi_delegated:
    text = Path('_codex/prompts', prompt).read_text()
    if 'pi -p --approve' not in text:
        raise SystemExit(f"Codex prompt {prompt} must delegate to Pi")

codex_specific_prompts = {
    'cmd:debug.md',
    'dev:plan.md',
    'dev:reviewed-html-plan.md',
    'review:change-gpt.md',
    'run-plan.md',
    'test:run-playwright.md',
    'test:run-playwright:all.md',
}

# Pi and Codex prompts may differ where their native reviewer-subagent routes differ.
# Template presence and explicit Pi-delegation contracts above are the supported parity boundary.

for skill in [
    'autoreview',
    'reviewed-html-plan',
    'run-plan',
]:
    text = Path('skills', skill, 'SKILL.md').read_text()
    if 'Codex' not in text or 'Pi' not in text:
        raise SystemExit(f"Skill {skill} must document Codex and Pi routing")

PY
}

test_parallel_review_protocol_installs_with_source_parity() {
  local home

  home="$(new_tmp_dir)"
  run_installer "$home" --skills || return 1

  cmp "skills/autoreview/SKILL.md" "$home/.agents/skills/autoreview/SKILL.md" || return 1
  [[ ! -e "$home/.agents/skills/herdr-reviewers" ]] || return 1
  cmp "scripts/review_orchestration.py" "$home/.agents/scripts/review_orchestration.py" || return 1
  [[ -x "$home/.agents/scripts/review_orchestration.py" ]] || return 1
  HOME="$home" "$home/.agents/scripts/review_orchestration.py" --help >/dev/null || return 1

  assert_file_contains "skills/autoreview/SKILL.md" 'active harness' || return 1
  assert_file_contains "$home/.agents/skills/autoreview/SKILL.md" 'at most one narrowed follow-up' || return 1
}


test_phase_four_validation_proves_final_alignment() {
  local home
  local target
  local claude_symlinks
  local stale_tree_refs
  local stale_install_instructions

  home="$(new_tmp_dir)"
  target="$(new_tmp_dir)"
  seed_phase_two_home "$home"

  run_installer "$home" --skills || return 1
  run_installer "$home" --all "$target" || return 1

  [[ -f "$home/.agents/skills/external-skill/SKILL.md" ]] || return 1
  [[ -f "$home/.agents/skills/linear/SKILL.md" ]] || return 1
  [[ -f "$home/.agents/skills/doct-document-ops/SKILL.md" ]] || return 1
  [[ ! -e "$home/.agents/skills/plan-reviewer-execution-ready" ]] || return 1
  [[ ! -e "$home/.agents/skills/plan-reviewer-build" ]] || return 1
  [[ -f "$home/.agents/skills/run-plan/SKILL.md" ]] || return 1
  [[ -f "$home/.agents/skills/autoreview/SKILL.md" ]] || return 1
  [[ -f "$home/.agents/skills/pre-pr-implementation-review/SKILL.md" ]] || return 1
  assert_file_contains "$home/.agents/skills/autoreview/SKILL.md" 'name: autoreview' || return 1
  assert_file_contains "$home/.agents/skills/pre-pr-implementation-review/SKILL.md" 'indefinite compatibility alias' || return 1
  assert_file_contains "$home/.agents/skills/pre-pr-implementation-review/SKILL.md" '/skill:autoreview <same arguments, unchanged>' || return 1
  [[ ! -e "$home/.agents/skills/scoped""-plan-run" ]] || return 1
  [[ ! -e "$home/.agents/skills/algorithmic-art" ]] || return 1
  [[ ! -e "$home/.agents/skills/brave-cdp" ]] || return 1

  claude_symlinks="$(find "$home/.claude/skills" -mindepth 1 -maxdepth 1 -type l | sort)"
  assert_command_output_contains "$claude_symlinks" "$home/.claude/skills/linear" || return 1
  assert_command_output_contains "$claude_symlinks" "$home/.claude/skills/run-plan" || return 1
  assert_command_output_not_contains "$claude_symlinks" "$home/.claude/skills/cmd-debug" || return 1
  assert_command_output_not_contains "$claude_symlinks" "$home/.claude/skills/algorithmic-art" || return 1

  assert_no_dangling_symlinks "$home/.claude/skills" || return 1
  [[ ! -e "$home/.config/opencode/skills/omp-review-partner" ]] || return 1
  assert_file_contains "$home/.config/herdr/fake-plugin-installs.log" 'plugin install persiyanov/herdr-reviewr --yes' || return 1

  [[ ! -e "$home/.pi/agent/skills/linear" ]] || return 1
  [[ ! -e "$home/.pi/agent/skills/doct-document-ops" ]] || return 1
  [[ ! -e "$home/.pi/agent/skills/cmd-debug" ]] || return 1

  assert_file_contains "$home/.agents/skills/doct-document-ops/SKILL.md" 'doct-agent plans register' || return 1
  assert_file_not_contains "$home/.agents/skills/doct-document-ops/SKILL.md" 'publish-coding-plan.sh' || return 1

  stale_tree_refs="$(git grep -n '_pi/skills/' README.md SETUP.md AGENTS.md _pi skills install.sh || true)"
  assert_command_output_not_contains "$stale_tree_refs" '$HOME/.pi/agent/skills/doct-document-ops/scripts/publish-coding-plan.sh' || return 1

  stale_install_instructions="$(git grep -n 'cp -r .*skills' README.md SETUP.md AGENTS.md _pi skills install.sh || true)"
  [[ -z "$stale_install_instructions" ]] || return 1

  assert_file_not_contains "README.md" 'install to `~/.claude/skills`' || return 1
  assert_file_not_contains "README.md" 'install to `~/.pi/agent/skills`' || return 1

  assert_file_contains "thoughts/archive/plans/skill-consolidation-to-agents.md" '- [x] P4 - Validate migration behavior, preservation rules, consumer compatibility wiring, and final repo alignment.' || return 1
  assert_file_contains "thoughts/archive/plans/skill-consolidation-to-agents.md" '2026-04-02 (P4): Ran the final temp-home validation flow' || return 1
}

test_review_guidance_is_bounded_and_scope_safe() {
  local prompt
  local hermes_run_plan

  for prompt in _codex/prompts/dev:run.md _pi/prompts/dev:run.md; do
    assert_file_contains "$prompt" 'Read-only review of phase N' || return 1
    assert_file_contains "$prompt" 'After three total rounds, the ordinary local review budget is exhausted.' || return 1
    assert_file_contains "$prompt" "whether or not a PR exists" || return 1
    assert_file_contains "$prompt" "configured consult/council surface" || return 1
    assert_file_contains "$prompt" "fixed artifact/range/fingerprint" || return 1
    assert_file_contains "$prompt" 'stable `REVIEW_ESCAPE` identifier' || return 1
    assert_file_contains "$prompt" 'The consultation is advisory only: it may not edit or apply fixes, become implementation authority, or reroute implementation through another persona.' || return 1
    assert_file_contains "$prompt" 'never repeat consultation for the same unresolved identifier' || return 1
    assert_file_contains "$prompt" 'materially separate later failure-family/scope identifier may receive its own one consultation whether discovered pre-PR, during an authorized adversarial pass, or from later PR feedback' || return 1
    assert_file_not_contains "$prompt" 'materially separate later PR-feedback failure family' || return 1
    assert_file_contains "$prompt" 'Verified reject/reclassify evidence clears that family and permits the phase to continue without an adversarial pass' || return 1
    assert_file_contains "$prompt" 'Revert/narrow/defer follows its stated path' || return 1
    assert_file_contains "$prompt" 'A user/product/scope disposition stops for that decision' || return 1
    assert_file_contains "$prompt" 'Only `authorize one further bounded adversarial fix/review pass` starts the pass' || return 1
    assert_file_contains "$prompt" 'If disposition evidence cannot be verified or its stated path cannot be completed within current authority, report that specific unresolved blocker' || return 1
    assert_file_contains "$prompt" 'audit the fixed candidate branch/diff for sibling instances in the named family' || return 1
    assert_file_contains "$prompt" 'one bounded fix attempt for in-scope findings' || return 1
    assert_file_contains "$prompt" 'run the same reviewer pass once after fixes' || return 1
    assert_file_contains "$prompt" 'This route has no PR prerequisite' || return 1
    assert_file_not_contains "$prompt" "repeat consultation until clean" || return 1
    assert_file_not_contains "$prompt" "rereview until clean" || return 1
    assert_file_contains "$prompt" 'speculative future scale' || return 1
    assert_file_not_contains "$prompt" 'Fix every non-low-risk issue directly' || return 1
    assert_file_not_contains "$prompt" 'No issues found.' || return 1
  done

  assert_file_contains "_pi/prompts/dev:run.md" 'Use the existing read-only `reviewer` for the adversarial pass at every risk level' || return 1
  assert_file_not_contains "_pi/prompts/dev:run.md" 'claude-code-review' || return 1
  assert_file_contains "_codex/prompts/dev:run.md" 'Use the active-harness read-only `reviewer` subagent as the sole adversarial leg' || return 1
  assert_file_not_contains "_codex/prompts/dev:run.md" 'claude-code-review' || return 1

  assert_file_contains "skills/planning-workflow/SKILL.md" 'Plan complete promised slices, not skeletons.' || return 1
  assert_file_contains "skills/run-plan/SKILL.md" 'Complete the PR-reviewable promised slice before claiming local merge readiness' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'you are not required to fix optional polish merely because it is cheap' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'run one targeted rereview' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'three total review cycles' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'exactly one bounded, read-only, independent external consultation' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'whether or not a PR exists' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" "configured consult/council surface" || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'fixed artifact, comparison range, and complete fingerprint' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'before or after PR creation' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'a PR URL or PR feedback is never required' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'stable consultation identifier' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'never consult again for the same unresolved identifier' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'materially separate later failure-family/scope identifier may receive its own one consultation whether discovered pre-PR, during an authorized adversarial pass, or from later PR feedback' || return 1
  assert_file_not_contains "skills/autoreview/SKILL.md" 'materially separate failure family first exposed by later PR feedback' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'A verified rejection or reclassification clears that escaped finding/failure family' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'Only an explicit `authorize one further bounded adversarial fix/review pass` disposition starts the adversarial pass' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'A revert, narrow, or defer disposition follows that stated path' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'A user/product/scope-decision disposition stops for that decision' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'If proposed rejection/reclassification evidence cannot be verified, the stated revert/narrow/defer cannot be completed within authority, or a requested decision remains unanswered, report that specific unresolved blocker' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'pre-review scope baseline' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'triggering input' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'reachable path' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'observable impact' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'diff relationship' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'existing ownership boundary' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'stop-before protocol' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'protocol, configuration surface, storage format, migration, public API or contract, release process, ownership move, or unrelated refactor' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'all known in-scope P1/P2 failure families in the initial pass' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'overflow count' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'five detailed findings' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'clean source review does not replace required behavioral verification' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'authoritative documentation' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'Release freeze discipline' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'beta/stable promotion, hotfix, backport, signing, packaging, deployment, or release-infrastructure work' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'valid, schema-conformant input' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'shared primitive' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'you are not required to add implementation or tests solely to prove a scenario is out of scope' || return 1
  assert_file_contains "skills/autoreview/SKILL.md" 'OUT_OF_SCOPE_FOLLOW_UP' || return 1
  assert_file_not_contains "skills/autoreview/SKILL.md" 'rereview until clean' || return 1
  assert_file_not_contains "skills/autoreview/SKILL.md" 'repeat consultation until clean' || return 1
  assert_file_not_contains "skills/autoreview/SKILL.md" 'loop until every reviewer is clean' || return 1
  assert_file_not_contains "skills/autoreview/SKILL.md" 'fix every finding' || return 1
  assert_file_contains "skills/pre-pr-implementation-review/SKILL.md" 'indefinite compatibility alias' || return 1
  assert_file_contains "skills/pre-pr-implementation-review/SKILL.md" '/skill:autoreview <same arguments, unchanged>' || return 1
  assert_file_contains "skills/pre-pr-implementation-review/SKILL.md" 'OPEN_PR_READY' || return 1
  assert_file_not_contains "skills/pre-pr-implementation-review/SKILL.md" 'claude_review({' || return 1
  assert_file_not_contains "skills/pre-pr-implementation-review/SKILL.md" 'Severity: P1' || return 1
  assert_file_contains "skills/install-matrix.json" '"autoreview"' || return 1
  assert_file_contains "skills/install-matrix.json" 'Indefinite compatibility alias for autoreview' || return 1
  assert_file_contains "skills/run-plan/SKILL.md" '$autoreview <plan path>' || return 1
  assert_file_not_contains "skills/run-plan/SKILL.md" 'pre-pr-implementation-review' || return 1
  assert_file_contains "_hermes/default/skills/software-development/run-plan/SKILL.md" '$autoreview <plan path>' || return 1
  assert_file_not_contains "_hermes/default/skills/software-development/run-plan/SKILL.md" 'pre-pr-implementation-review' || return 1
  assert_file_contains "_hermes/default/cron/jobs.json" '/skill:autoreview' || return 1
  assert_file_not_contains "_hermes/default/cron/jobs.json" '/skill:pre-pr-implementation-review' || return 1
  assert_file_contains "AGENTS.md" '/skill:autoreview thoughts/plans/<plan>.html' || return 1
  assert_file_contains "_pi/README.md" '/skill:autoreview thoughts/plans/my-plan.html' || return 1
  assert_file_contains "skills/run-plan/SKILL.md" 'Run a third total review cycle only when' || return 1
  assert_file_contains "skills/run-plan/SKILL.md" 'When the ordinary three-cycle budget is exhausted, route the stable `REVIEW_ESCAPE` failure-family/scope identifier through the one-per-family consultation section before reporting convergence.' || return 1
  assert_file_contains "skills/run-plan/SKILL.md" 'No fourth or renamed pass is allowed except the single explicitly consultation-authorized bounded pass and its existing one pass-after-fixes allowance.' || return 1
  assert_file_not_contains "skills/run-plan/SKILL.md" 'Run the adversarial escalation loop below only if a review cycle remains' || return 1
  assert_file_contains "skills/run-plan/SKILL.md" 'Do not report the convergence blocker yet solely because no PR exists.' || return 1
  assert_file_contains "skills/run-plan/SKILL.md" 'Review Escape Consultation and Adversarial Escalation Loop' || return 1
  assert_file_contains "skills/run-plan/SKILL.md" 'configured consult/council surface' || return 1
  assert_file_contains "skills/run-plan/SKILL.md" 'A PR URL or PR feedback is not required' || return 1
  assert_file_contains "skills/run-plan/SKILL.md" 'one consultation per distinct failure-family/scope identifier' || return 1
  assert_file_contains "skills/run-plan/SKILL.md" 'Never repeat consultation for the same unresolved family/scope identifier' || return 1
  assert_file_contains "skills/run-plan/SKILL.md" 'materially separate later failure-family/scope identifier may receive its own one consultation whether discovered pre-PR, during an authorized adversarial pass, or from later PR feedback' || return 1
  assert_file_contains "skills/run-plan/SKILL.md" 'Verified rejection or reclassification clears that escaped finding/failure family' || return 1
  assert_file_contains "skills/run-plan/SKILL.md" 'Revert, narrow, or defer follows the stated path under the normal scope rules' || return 1
  assert_file_contains "skills/run-plan/SKILL.md" 'A user/product/scope-decision disposition stops for that decision' || return 1
  assert_file_contains "skills/run-plan/SKILL.md" 'Only an explicit authorization starts the bounded adversarial pass' || return 1
  assert_file_contains "skills/run-plan/SKILL.md" 'If disposition evidence cannot be verified or its stated path cannot be completed within current authority, report that specific unresolved blocker' || return 1
  assert_file_not_contains "skills/run-plan/SKILL.md" 'repeat consultation until clean' || return 1
  assert_file_not_contains "skills/run-plan/SKILL.md" 'loop until every reviewer is clean' || return 1
  assert_file_contains "AGENTS.md" 'exactly one bounded, read-only, advisory external consultation' || return 1
  assert_file_contains "AGENTS.md" 'whether or not a PR exists' || return 1
  for prompt in skills/repo-agents-bootstrap/SKILL.md skills/repo-agents-bootstrap/references/root_agents_template.md; do
    assert_file_contains "$prompt" 'whether or not a PR exists' || return 1
    assert_file_contains "$prompt" 'configured consult/council surface' || return 1
    assert_file_contains "$prompt" 'stable, distinct `REVIEW_ESCAPE` family+scope identifier' || return 1
    assert_file_contains "$prompt" 'no edit, fix, or implementation authority' || return 1
    assert_file_contains "$prompt" 'never rename, reword, or reconsult the same family+scope' || return 1
    assert_file_contains "$prompt" 'each materially separate later family+scope may receive its own one consultation before or after PR creation' || return 1
    assert_file_contains "$prompt" 'verified reject/reclassify' || return 1
    assert_file_contains "$prompt" 'authorized bounded pass' || return 1
    assert_file_contains "$prompt" 'revert/narrow/defer' || return 1
    assert_file_contains "$prompt" 'user/product/scope decision' || return 1
  done
  assert_file_contains "skills/repo-agents-bootstrap/SKILL.md" 'Report specifically any unresolved disposition evidence or path that current authority cannot complete.' || return 1
  assert_file_contains "skills/repo-agents-bootstrap/references/root_agents_template.md" 'report specifically unresolved evidence or any path current authority cannot complete' || return 1
  assert_file_contains "_pi/README.md" 'does not require a PR URL or PR feedback' || return 1
  assert_file_not_contains "skills/run-plan/SKILL.md" 'Repeat Review Loop' || return 1
  assert_file_not_contains "AGENTS.md" 'keep the review/fix loop running until' || return 1
  assert_file_not_contains "skills/repo-agents-bootstrap/SKILL.md" 'Phase advancement only when the latest review returns' || return 1
  assert_file_contains "skills/run-plan/agents/openai.yaml" 'active-harness reviewer-subagent pre-PR review' || return 1
  assert_file_contains "skills/install-matrix.json" 'active-harness reviewer-subagent pre-PR review' || return 1
  assert_file_contains "_pi/README.md" 'plan-required, verification-required, or regression-caused P3 findings remain blocking' || return 1
  assert_file_not_contains "skills/run-plan/agents/openai.yaml" 'full P1/P2/P3 consensus' || return 1
  assert_file_not_contains "skills/install-matrix.json" 'full P1/P2/P3 consensus' || return 1
  assert_file_not_contains "_pi/README.md" 'all in-scope P1/P2/P3 findings' || return 1

  hermes_run_plan="_hermes/default/skills/software-development/run-plan/SKILL.md"
  assert_file_contains "$hermes_run_plan" 'Complete the PR-reviewable promised slice before claiming local merge readiness' || return 1
  assert_file_contains "$hermes_run_plan" 'Run a third total review cycle only when' || return 1
  assert_file_contains "$hermes_run_plan" 'When the ordinary three-cycle budget is exhausted, route the stable `REVIEW_ESCAPE` failure-family/scope identifier through the one-per-family consultation section before reporting convergence' || return 1
  assert_file_contains "$hermes_run_plan" 'No fourth or renamed pass is allowed except the single explicitly consultation-authorized bounded pass' || return 1
  assert_file_not_contains "$hermes_run_plan" 'For each `REVIEW_ESCAPE`, run the adversarial escalation loop below' || return 1
  assert_file_contains "$hermes_run_plan" 'Do not report the convergence blocker yet solely because no PR exists.' || return 1
  assert_file_contains "$hermes_run_plan" 'configured consult/council surface' || return 1
  assert_file_contains "$hermes_run_plan" 'A PR URL or PR feedback is not required' || return 1
  assert_file_contains "$hermes_run_plan" 'one consultation per distinct failure-family/scope identifier' || return 1
  assert_file_contains "$hermes_run_plan" 'Never repeat consultation for the same unresolved family/scope identifier' || return 1
  assert_file_contains "$hermes_run_plan" 'materially separate later failure-family/scope identifier may receive its own one consultation whether discovered pre-PR, during an authorized adversarial pass, or from later PR feedback' || return 1
  assert_file_contains "$hermes_run_plan" 'Verified rejection or reclassification clears that escaped finding/failure family' || return 1
  assert_file_contains "$hermes_run_plan" 'Revert, narrow, or defer follows the stated path under the normal scope rules' || return 1
  assert_file_contains "$hermes_run_plan" 'A user/product/scope-decision disposition stops for that decision' || return 1
  assert_file_contains "$hermes_run_plan" 'Only an explicit authorization starts the bounded adversarial pass' || return 1
  assert_file_contains "$hermes_run_plan" 'If disposition evidence cannot be verified or its stated path cannot be completed within current authority, report that specific unresolved blocker' || return 1
  assert_file_not_contains "$hermes_run_plan" 'repeat consultation until clean' || return 1
  assert_file_not_contains "$hermes_run_plan" 'loop until every reviewer is clean' || return 1
  assert_file_not_contains "$hermes_run_plan" 'Repeat Review Loop' || return 1
  assert_file_not_contains "$hermes_run_plan" 'cheap and safe enough to fix immediately' || return 1
  assert_file_contains "$hermes_run_plan" 'Run exactly one bounded, static inspection with the active harness' || return 1
  assert_file_not_contains "$hermes_run_plan" 'claude-code-review' || return 1
  assert_file_contains "_hermes/default/skills/software-development/reviewed-html-plan/SKILL.md" "active harness's \`reviewer\` subagent" || return 1
  assert_file_contains "APPEND_SYSTEM.md" 'For required implementation/code review, use exactly one active-harness read-only `reviewer` subagent' || return 1
  assert_file_contains "APPEND_SYSTEM.md" 'use the read-only `planner` subagent on GPT-5.6 Sol at medium reasoning effort' || return 1
}

test_active_agent_configuration_has_no_kimi() {
  local active_paths=(
    _pi/agents
    _pi/prompts
    _claude/commands
    _codex/prompts
    _pi/README.md
  )

  if grep -R -n -i -E 'kimi|k2\.5|context-builder|prd-researcher|plan-k2\.5|review-change-kimi' "${active_paths[@]}"; then
    return 1
  fi

  [[ ! -e _pi/agents/context-builder.md ]] || return 1
  [[ ! -e _pi/agents/plan-k2.5.md ]] || return 1
  [[ ! -e _pi/agents/prd-researcher.md ]] || return 1
  assert_file_contains _pi/agents/reviewer.md 'model: openai-codex/gpt-5.6-terra' || return 1
  assert_file_contains _pi/agents/reviewer.md 'reasoningEffort: medium' || return 1
  assert_file_contains _pi/agents/scout.md 'model: openai-codex/gpt-5.6-terra' || return 1
  assert_file_contains _pi/agents/scout.md 'reasoningEffort: low' || return 1
  assert_file_contains _claude/agents/reviewer.md 'model: claude-sonnet-5' || return 1
  assert_file_contains _claude/agents/reviewer.md 'effort: high' || return 1
  assert_file_contains _claude/commands/dev:run.md 'repository-owned, read-only `reviewer` subagent (`claude-sonnet-5`, high effort)' || return 1
  assert_file_contains _claude/commands/cmd:execute-plan.md 'one read-only `reviewer` subagent pass after each phase' || return 1
}

test_hermes_config_sync_preserves_cron_runtime_state() {
  python3 -m unittest scripts/test_hermes_config_sync.py
}

main() {
  run_test test_skills_mode_installs_additively_and_is_idempotent
  run_test test_skills_mode_does_not_update_skills_sh_by_default
  run_test test_update_modifier_runs_skills_sh_update_before_sync
  run_test test_update_modifier_normalizes_skills_sh_mutated_managed_skills
  run_test test_update_modifier_syncs_skills_for_modes_without_normal_skill_sync
  run_test test_default_mode_reuses_shared_sync_without_mutating_repo_root
  run_test test_single_surface_modes_reuse_shared_sync
  run_test test_project_local_central_skill_overrides_are_removed
  run_test test_non_managed_retired_skill_is_preserved
  run_test test_failpoint_after_backup_keeps_destination_recoverable
  run_test test_agent_extension_installs_preserve_or_manage_herdr_extensions
  run_test test_pi_install_removes_retired_packages
  run_test test_pi_install_replaces_gpt_config_packages
  run_test test_verify_pi_install_reports_stale_goal_package
  run_test test_pi_install_removes_retired_interactive_shell_when_pi_list_fails
  run_test test_pi_doctrine_renderer_tracks_exact_git_state
  run_test test_pi_interaction_doctrine_is_versioned_and_read_only_by_default
  run_test test_integration_integrity_is_common_and_portable
  run_test test_integration_integrity_materializes_across_workflows
  run_test test_tdd_test_writer_is_direct_and_distributed
  run_test test_hermes_integration_integrity_mirrors_are_reconciled
  run_test test_phase_three_docs_use_canonical_shared_skill_paths
  run_test test_phase_three_duplicate_skill_trees_are_removed
  run_test test_plan_authoring_contract_is_product_owner_friendly
  run_test test_codex_pi_skill_and_prompt_parity
  run_test test_parallel_review_protocol_installs_with_source_parity
  run_test test_phase_four_validation_proves_final_alignment
  run_test test_review_guidance_is_bounded_and_scope_safe
  run_test test_active_agent_configuration_has_no_kimi
  run_test test_hermes_config_sync_preserves_cron_runtime_state

  printf '\nTests run: %s\n' "$TESTS_RUN"
  printf 'Passed: %s\n' "$TESTS_PASSED"
  printf 'Failed: %s\n' "$TESTS_FAILED"

  [[ "$TESTS_FAILED" -eq 0 ]]
}

main "$@"
