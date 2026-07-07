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
}

trap cleanup EXIT

new_tmp_dir() {
  local dir
  dir="$(mktemp -d)"
  TMP_DIRS+=("$dir")
  printf '%s\n' "$dir"
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
  list)
    if [[ "${AI_CONFIGS_FAKE_PI_LIST_FAILS:-}" == "1" ]]; then
      exit 1
    fi
    if [[ -f "$settings_path" ]]; then
      python3 - "$settings_path" <<'PY'
import json
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
        print(f"  {source}")
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

echo "stub npm $*" >/dev/null
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

  printf '%s\n' "$bin_dir"
}

seed_phase_two_home() {
  local home="$1"
  # Split the retired skill name so stale-name greps can still guard active surfaces.
  local old_skill="scoped""-plan-run"

  mkdir -p \
    "$home/.claude/skills/custom-local" \
    "$home/.config/opencode/skills/custom-local" \
    "$home/.config/opencode/skills/cmd-debug" \
    "$home/.config/opencode/skills/$old_skill" \
    "$home/.pi/agent/skills/$old_skill" \
    "$home/.omp/agent" \
    "$home/.agents/skills/external-skill" \
    "$home/.agents/skills/linear" \
    "$home/.agents/skills/$old_skill" \
    "$home/.agents/skills/algorithmic-art" \
    "$home/.claude/skills/linear" \
    "$home/.claude/skills/$old_skill" \
    "$home/.claude/skills/algorithmic-art" \
    "$home/.config/opencode/skills/algorithmic-art"

  printf 'external\n' > "$home/.agents/skills/external-skill/SKILL.md"
  printf 'foreign-linear\n' > "$home/.agents/skills/linear/SKILL.md"
  printf 'old-%s\n' "$old_skill" > "$home/.agents/skills/$old_skill/SKILL.md"
  printf 'old-optional-algorithmic-art\n' > "$home/.agents/skills/algorithmic-art/SKILL.md"
  printf '{"repo":"ai-configs","source":"external-package:anthropics/skills#algorithmic-art","managed":true}\n' > "$home/.agents/skills/algorithmic-art/.ai-configs-managed.json"
  ln -s "$home/.agents/skills/algorithmic-art" "$home/.claude/skills/algorithmic-art"
  ln -s "$home/.agents/skills/algorithmic-art" "$home/.config/opencode/skills/algorithmic-art"
  printf 'old-claude-linear\n' > "$home/.claude/skills/linear/SKILL.md"
  printf 'old-claude-%s\n' "$old_skill" > "$home/.claude/skills/$old_skill/SKILL.md"
  printf 'foreign-opencode-cmd-debug\n' > "$home/.config/opencode/skills/cmd-debug/SKILL.md"
  printf 'old-opencode-%s\n' "$old_skill" > "$home/.config/opencode/skills/$old_skill/SKILL.md"
  printf 'old-pi-%s\n' "$old_skill" > "$home/.pi/agent/skills/$old_skill/SKILL.md"
  mkdir -p "$home/.agents"
  printf '{"skills":{"%s":{"source":"old"},"linear":{"source":"old"}}}\n' "$old_skill" > "$home/.agents/.skill-lock.json"
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
  local opencode_backup_dir
  # Split the retired skill name so stale-name greps can still guard active surfaces.
  local old_skill="scoped""-plan-run"

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

  [[ -f "$home/.agents/skills/adn-dev-wf/SKILL.md" ]] || return 1
  [[ -f "$home/.agents/skills/adn-dev-wf/.ai-configs-managed.json" ]] || return 1
  assert_file_contains "$home/.agents/skills/adn-dev-wf/.ai-configs-managed.json" '"repo": "ai-configs"' || return 1
  assert_file_contains "$home/.agents/skills/adn-dev-wf/.ai-configs-managed.json" '"source": "skills/adn-dev-wf"' || return 1
  assert_file_contains "$home/.agents/skills/adn-dev-wf/.ai-configs-managed.json" '"managed": true' || return 1

  [[ -f "$home/.agents/skills/plan-reviewer-execution-ready/SKILL.md" ]] || return 1
  [[ -f "$home/.agents/skills/plan-reviewer-execution-ready/.ai-configs-managed.json" ]] || return 1
  assert_file_contains "$home/.agents/skills/plan-reviewer-execution-ready/SKILL.md" 'quality-reviewer-glm' || return 1
  assert_file_contains "$home/.agents/skills/plan-reviewer-execution-ready/.ai-configs-managed.json" '"repo": "ai-configs"' || return 1
  assert_file_contains "$home/.agents/skills/plan-reviewer-execution-ready/.ai-configs-managed.json" '"source": "skills/plan-reviewer-execution-ready"' || return 1
  assert_file_contains "$home/.agents/skills/plan-reviewer-execution-ready/.ai-configs-managed.json" '"managed": true' || return 1

  [[ -f "$home/.agents/skills/plan-reviewer-build/SKILL.md" ]] || return 1
  [[ -f "$home/.agents/skills/plan-reviewer-build/.ai-configs-managed.json" ]] || return 1
  assert_file_contains "$home/.agents/skills/plan-reviewer-build/SKILL.md" 'run-plan' || return 1
  assert_file_not_contains "$home/.agents/skills/plan-reviewer-build/SKILL.md" "$old_skill" || return 1
  assert_file_contains "$home/.agents/skills/plan-reviewer-build/.ai-configs-managed.json" '"repo": "ai-configs"' || return 1
  assert_file_contains "$home/.agents/skills/plan-reviewer-build/.ai-configs-managed.json" '"source": "skills/plan-reviewer-build"' || return 1
  assert_file_contains "$home/.agents/skills/plan-reviewer-build/.ai-configs-managed.json" '"managed": true' || return 1

  [[ -f "$home/.agents/skills/run-plan/SKILL.md" ]] || return 1
  [[ -f "$home/.agents/skills/run-plan/.ai-configs-managed.json" ]] || return 1
  assert_file_contains "$home/.agents/skills/run-plan/SKILL.md" 'name: run-plan' || return 1
  assert_file_contains "$home/.agents/skills/run-plan/.ai-configs-managed.json" '"repo": "ai-configs"' || return 1
  assert_file_contains "$home/.agents/skills/run-plan/.ai-configs-managed.json" '"source": "skills/run-plan"' || return 1
  assert_file_contains "$home/.agents/skills/run-plan/.ai-configs-managed.json" '"managed": true' || return 1
  [[ ! -e "$home/.agents/skills/$old_skill" ]] || return 1
  [[ ! -e "$home/.claude/skills/$old_skill" ]] || return 1
  [[ ! -e "$home/.config/opencode/skills/$old_skill" ]] || return 1
  [[ ! -e "$home/.pi/agent/skills/$old_skill" ]] || return 1
  assert_file_not_contains "$home/.agents/.skill-lock.json" "$old_skill" || return 1

  [[ ! -e "$home/.agents/skills/algorithmic-art" ]] || return 1
  [[ ! -e "$home/.claude/skills/algorithmic-art" ]] || return 1
  [[ ! -e "$home/.config/opencode/skills/algorithmic-art" ]] || return 1
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
  assert_file_contains "$home/.agents/skills/herdr/SKILL.md" 'external package=ogulcancelik/herdr skill=herdr' || return 1
  [[ -f "$home/.agents/skills/herdr/.ai-configs-managed.json" ]] || return 1
  assert_file_contains "$home/.agents/skills/herdr/.ai-configs-managed.json" '"source": "external-package:ogulcancelik/herdr#herdr"' || return 1

  [[ -d "$home/.claude/skills/custom-local" ]] || return 1
  [[ -d "$home/.config/opencode/skills/custom-local" ]] || return 1

  claude_backup_dir="$(find_consumer_backup_dir "$home" claude linear)"
  [[ -n "$claude_backup_dir" ]] || return 1
  assert_file_contains "$claude_backup_dir/SKILL.md" 'old-claude-linear' || return 1

  opencode_backup_dir="$(find_consumer_backup_dir "$home" opencode cmd-debug)"
  [[ -n "$opencode_backup_dir" ]] || return 1
  assert_file_contains "$opencode_backup_dir/SKILL.md" 'foreign-opencode-cmd-debug' || return 1

  assert_symlink_target "$home/.claude/skills/linear" "$home/.agents/skills/linear" || return 1
  assert_symlink_target "$home/.config/opencode/skills/linear" "$home/.agents/skills/linear" || return 1
  assert_symlink_target "$home/.claude/skills/adn-dev-wf" "$home/.agents/skills/adn-dev-wf" || return 1
  assert_symlink_target "$home/.config/opencode/skills/adn-dev-wf" "$home/.agents/skills/adn-dev-wf" || return 1
  assert_symlink_target "$home/.claude/skills/run-plan" "$home/.agents/skills/run-plan" || return 1
  assert_symlink_target "$home/.config/opencode/skills/run-plan" "$home/.agents/skills/run-plan" || return 1
  assert_symlink_target "$home/.claude/skills/design-skill" "$home/.agents/skills/design-skill" || return 1
  assert_symlink_target "$home/.config/opencode/skills/design-skill" "$home/.agents/skills/design-skill" || return 1
  assert_symlink_target "$home/.claude/skills/herdr" "$home/.agents/skills/herdr" || return 1
  assert_symlink_target "$home/.config/opencode/skills/herdr" "$home/.agents/skills/herdr" || return 1

  [[ ! -e "$home/.claude/skills/cmd-debug" ]] || return 1
  [[ ! -e "$home/.config/opencode/skills/cmd-debug" ]] || return 1
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
  local target

  home="$(new_tmp_dir)"
  target="$(new_tmp_dir)"
  seed_phase_two_home "$home"

  run_installer "$home" --gemini --update "$target" || return 1
  assert_file_contains "$home/.agents/fake-npx-skills-update.log" 'update -g -y' || return 1
  assert_file_contains "$home/.agents/skills/linear/.ai-configs-managed.json" '"source": "skills/linear"' || return 1
  [[ -d "$target/.gemini" ]] || return 1
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
  [[ -d "$target/.gemini" ]] || return 1
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
  target="$(new_tmp_dir)"
  seed_phase_two_home "$home"
  run_installer "$home" --opencode "$target" || return 1
  [[ -d "$home/.agents/skills" ]] || return 1
  assert_symlink_target "$home/.config/opencode/skills/linear" "$home/.agents/skills/linear" || return 1
  [[ ! -e "$home/.config/opencode/skills/cmd-debug" ]] || return 1

  home="$(new_tmp_dir)"
  seed_phase_two_home "$home"
  run_installer "$home" --pi || return 1
  [[ -d "$home/.agents/skills" ]] || return 1
  [[ ! -e "$home/.pi/agent/skills/linear" ]] || return 1
  [[ ! -e "$home/.pi/agent/skills/cmd-debug" ]] || return 1

  home="$(new_tmp_dir)"
  target="$(new_tmp_dir)"
  seed_phase_two_home "$home"
  run_installer "$home" --omp "$target" || return 1
  [[ -d "$home/.agents/skills" ]] || return 1
  [[ ! -e "$home/.omp/agent/skills" ]] || return 1
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

  mkdir -p "$home/.pi/agent/extensions" "$home/.omp/agent/extensions"
  printf 'pi-herdr-sentinel\n' > "$home/.pi/agent/extensions/herdr-agent-state.ts"
  printf 'omp-herdr-sentinel\n' > "$home/.omp/agent/extensions/herdr-agent-state.ts"

  output_file="$home/pi-install.log"
  run_installer_capture "$home" "$output_file" --pi || {
    cat "$output_file" >&2
    return 1
  }
  assert_file_contains "$home/.pi/agent/extensions/herdr-agent-state.ts" 'HERDR_INTEGRATION_ID=pi' || return 1
  assert_file_contains "$home/.pi/agent/extensions/herdr-agent-state.ts" 'managed by ai-configs' || return 1
  [[ -f "$home/.pi/agent/extensions/todo.ts" ]] || return 1
  [[ -d "$home/.pi/agent/extensions/pi-plan-mode" ]] || return 1

  output_file="$home/omp-install.log"
  run_installer_capture "$home" "$output_file" --omp || {
    cat "$output_file" >&2
    return 1
  }
  assert_file_contains "$home/.omp/agent/extensions/herdr-agent-state.ts" 'omp-herdr-sentinel' || return 1
  [[ -d "$home/.omp/agent/extensions/aplan" ]] || return 1
  [[ -d "$home/.omp/agent/extensions/pi-vcc" ]] || return 1
}

test_pi_interactive_shell_local_install_purges_stale_git_when_pi_list_fails() {
  local home output_file local_fork settings_path
  home="$(new_tmp_dir)"
  output_file="$home/pi-install.log"
  local_fork="$(cd "$SCRIPT_DIR/../3p/pi-interactive-shell" 2>/dev/null && pwd || true)"
  settings_path="$home/.pi/agent/settings.json"

  [[ -n "$local_fork" ]] || return 0
  mkdir -p "$(dirname "$settings_path")"
  cat > "$settings_path" <<'JSON'
{
  "packages": [
    "git:github.com/adnichols/pi-interactive-shell"
  ]
}
JSON

  AI_CONFIGS_FAKE_PI_LIST_FAILS=1 run_installer_capture "$home" "$output_file" --pi || {
    cat "$output_file" >&2
    return 1
  }

  assert_file_contains "$output_file" 'Purged stale pi-interactive-shell package registration git:github.com/adnichols/pi-interactive-shell' || return 1
  assert_file_not_contains "$settings_path" 'git:github.com/adnichols/pi-interactive-shell' || return 1
  python3 - "$settings_path" "$local_fork" <<'PY'
import json
import sys
from pathlib import Path
settings_path = Path(sys.argv[1])
expected = Path(sys.argv[2]).resolve()
data = json.loads(settings_path.read_text())
for item in data.get("packages", []):
    source = item.get("source") if isinstance(item, dict) else item if isinstance(item, str) else None
    if isinstance(source, str) and "pi-interactive-shell" in source:
        path = Path(source)
        if not path.is_absolute():
            path = settings_path.parent / path
        if path.resolve() == expected:
            raise SystemExit(0)
raise SystemExit(1)
PY
}

test_pi_interactive_shell_git_fallback_purges_stale_local_when_pi_list_fails() {
  local home output_file temp_repo settings_path stale_local
  home="$(new_tmp_dir)"
  temp_repo="$(new_tmp_dir)/repo"
  output_file="$home/pi-install.log"
  settings_path="$home/.pi/agent/settings.json"
  stale_local="$(new_tmp_dir)/pi-interactive-shell"

  mkdir -p "$temp_repo" "$stale_local" "$(dirname "$settings_path")"
  cp "$INSTALLER" "$temp_repo/install.sh"
  mkdir -p "$temp_repo/_pi" "$temp_repo/skills"
  cp -R "$SCRIPT_DIR/_pi/prompts" "$temp_repo/_pi/"
  cp -R "$SCRIPT_DIR/_pi/agents" "$temp_repo/_pi/"
  cp -R "$SCRIPT_DIR/_pi/extensions" "$temp_repo/_pi/"
  cp -R "$SCRIPT_DIR/_pi/packages" "$temp_repo/_pi/"
  cp "$SCRIPT_DIR/_pi/models.json" "$temp_repo/_pi/models.json"
  cp -R "$SCRIPT_DIR/skills/adn-dev-wf" "$temp_repo/skills/"
  printf '{}\n' > "$temp_repo/skills/install-matrix.json"
  printf 'system\n' > "$temp_repo/APPEND_SYSTEM.md"
  printf 'readme\n' > "$temp_repo/_pi/README.md"
  printf '{}\n' > "$settings_path"
  cat > "$settings_path" <<JSON
{
  "packages": [
    "$stale_local"
  ]
}
JSON

  local fake_bin
  fake_bin="$(create_fake_tool_bin "$home")"
  (
    cd "$temp_repo" &&
      HOME="$home" PATH="$fake_bin:$PATH" AI_CONFIGS_FAKE_PI_LIST_FAILS=1 bash "$temp_repo/install.sh" --pi >"$output_file" 2>&1
  ) || {
    cat "$output_file" >&2
    return 1
  }

  assert_file_contains "$output_file" "Purged stale pi-interactive-shell package registration $stale_local" || return 1
  assert_file_not_contains "$settings_path" "$stale_local" || return 1
  assert_file_contains "$settings_path" 'git:github.com/adnichols/pi-interactive-shell' || return 1
}

test_phase_three_docs_use_canonical_shared_skill_paths() {
  assert_file_contains "AGENTS.md" '"skills": ["skills"]' || return 1
  assert_file_not_contains "AGENTS.md" '"skills": [".agents/skills", "opencode/skills"]' || return 1
  assert_file_contains "README.md" 'skills/install-matrix.json' || return 1
  assert_file_contains "_pi/README.md" 'skills/install-matrix.json' || return 1

  assert_file_contains "_omp/commands/cmd:send-plan-to-doct.md" 'doct-agent documents publish-plan' || return 1
  assert_file_contains "_opencode/commands/cmd:send-plan-to-doct.md" 'doct-agent documents publish-plan' || return 1
  assert_file_contains "_pi/prompts/cmd:send-plan-to-doct.md" 'doct-agent plans register' || return 1
  assert_file_contains "_codex/prompts/cmd:send-plan-to-doct.md" 'doct-agent plans register' || return 1
  assert_file_not_contains "_omp/commands/cmd:send-plan-to-doct.md" 'publish-coding-plan.sh' || return 1
  assert_file_not_contains "_pi/prompts/cmd:send-plan-to-doct.md" 'publish-coding-plan.sh' || return 1
  assert_file_not_contains "_codex/prompts/cmd:send-plan-to-doct.md" 'publish-coding-plan.sh' || return 1
  assert_file_not_contains "_opencode/commands/cmd:send-plan-to-doct.md" 'publish-coding-plan.sh' || return 1

  assert_file_contains "skills/install-matrix.json" '"playwright-skill"' || return 1
  assert_file_contains "skills/install-matrix.json" '"packageSource": "lackeyjb/playwright-skill"' || return 1

  # removed root duplicate
  # assert_file_not_contains "OPENCODE_ONBOARDING.md" 'cp -r ./_opencode/skills/playwright-skill/' || return 1
  assert_file_not_contains "_opencode/OPENCODE_ONBOARDING.md" 'cp -r ./_opencode/skills/playwright-skill/' || return 1
  assert_file_not_contains "_opencode/QUICKSTART.md" 'cp -r _opencode/skills/playwright-skill/' || return 1
  # removed root duplicate
  # assert_file_contains "OPENCODE_ONBOARDING.md" '~/.agents/skills/playwright-skill' || return 1
  assert_file_contains "_opencode/OPENCODE_ONBOARDING.md" '~/.agents/skills/playwright-skill' || return 1
  assert_file_contains "_opencode/QUICKSTART.md" '~/.agents/skills/playwright-skill' || return 1
}

test_phase_three_duplicate_skill_trees_are_removed() {
  [[ ! -d ".agents/skills/dependency-selection" ]] || return 1
  [[ ! -d "_pi/skills" ]] || return 1
  [[ -d "_opencode/skills" ]] || return 1
  [[ -d "_opencode/skills/codex-computer-use" ]] || return 1
  [[ -d "_opencode/skills/opencode-conversation-reviewer" ]] || return 1
  [[ -d "_opencode/skills/template" ]] || return 1
  [[ ! -d "_opencode/skills/playwright-skill" ]] || return 1

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

  local unexpected
  unexpected="$(find _opencode/skills -mindepth 1 -maxdepth 1 -type d ! -name 'codex-computer-use' ! -name 'opencode-conversation-reviewer' ! -name 'template' -print)"
  [[ -z "$unexpected" ]]
}

test_codex_pi_skill_and_prompt_parity() {
  python3 - <<'PY'
import json
from pathlib import Path

matrix = json.loads(Path('skills/install-matrix.json').read_text())['installableSkills']
missing_codex = [
    name
    for name, meta in sorted(matrix.items())
    if 'pi' in meta.get('allowedConsumers', []) and 'codex' not in meta.get('allowedConsumers', [])
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
    'dev:reviewed-html-plan.md',
    'prd:clarify-round.md',
    'review:change-claude-code.md',
    'review:change-k2.5.md',
    'review:change-opus.md',
    'review:plan.md',
    'review:plan-adversarial.md',
    'review:prd.md',
]
for prompt in pi_delegated:
    text = Path('_codex/prompts', prompt).read_text()
    if 'pi -p --approve' not in text:
        raise SystemExit(f"Codex prompt {prompt} must delegate to Pi")

for prompt in sorted(pi_prompts - set(pi_delegated)):
    pi_text = Path('_pi/prompts', prompt).read_text()
    codex_text = Path('_codex/prompts', prompt).read_text()
    if pi_text != codex_text:
        raise SystemExit(f"Shared non-delegated prompt drifted: {prompt}")

for skill in [
    'pre-pr-implementation-review',
    'reviewed-html-plan',
    'plan-reviewer-execution-ready',
    'run-plan',
]:
    text = Path('skills', skill, 'SKILL.md').read_text()
    if 'Codex' not in text or 'Pi' not in text or 'pi -p --approve' not in text:
        raise SystemExit(f"Skill {skill} must document Codex-to-Pi delegation")
PY
}

test_phase_four_validation_proves_final_alignment() {
  local home
  local target
  local claude_symlinks
  local opencode_symlinks
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
  [[ -f "$home/.agents/skills/plan-reviewer-execution-ready/SKILL.md" ]] || return 1
  [[ -f "$home/.agents/skills/plan-reviewer-build/SKILL.md" ]] || return 1
  [[ -f "$home/.agents/skills/run-plan/SKILL.md" ]] || return 1
  [[ ! -e "$home/.agents/skills/scoped""-plan-run" ]] || return 1
  [[ ! -e "$home/.agents/skills/algorithmic-art" ]] || return 1
  [[ ! -e "$home/.agents/skills/brave-cdp" ]] || return 1

  claude_symlinks="$(find "$home/.claude/skills" -mindepth 1 -maxdepth 1 -type l | sort)"
  opencode_symlinks="$(find "$home/.config/opencode/skills" -mindepth 1 -maxdepth 1 -type l | sort)"
  assert_command_output_contains "$claude_symlinks" "$home/.claude/skills/linear" || return 1
  assert_command_output_contains "$opencode_symlinks" "$home/.config/opencode/skills/linear" || return 1
  assert_command_output_contains "$claude_symlinks" "$home/.claude/skills/run-plan" || return 1
  assert_command_output_contains "$opencode_symlinks" "$home/.config/opencode/skills/run-plan" || return 1
  assert_command_output_not_contains "$claude_symlinks" "$home/.claude/skills/cmd-debug" || return 1
  assert_command_output_not_contains "$opencode_symlinks" "$home/.config/opencode/skills/cmd-debug" || return 1
  assert_command_output_not_contains "$claude_symlinks" "$home/.claude/skills/algorithmic-art" || return 1
  assert_command_output_not_contains "$opencode_symlinks" "$home/.config/opencode/skills/algorithmic-art" || return 1

  assert_no_dangling_symlinks "$home/.claude/skills" || return 1
  assert_no_dangling_symlinks "$home/.config/opencode/skills" || return 1

  [[ ! -e "$home/.pi/agent/skills/linear" ]] || return 1
  [[ ! -e "$home/.pi/agent/skills/doct-document-ops" ]] || return 1
  [[ ! -e "$home/.pi/agent/skills/cmd-debug" ]] || return 1

  assert_file_contains "$home/.agents/skills/doct-document-ops/SKILL.md" 'doct-agent plans register' || return 1
  assert_file_not_contains "$home/.agents/skills/doct-document-ops/SKILL.md" 'publish-coding-plan.sh' || return 1

  stale_tree_refs="$(git grep -n '_opencode/skills/\|_pi/skills/' README.md SETUP.md AGENTS.md _pi _opencode _omp skills install.sh || true)"
  assert_command_output_not_contains "$stale_tree_refs" 'cp -r ./_opencode/skills' || return 1
  assert_command_output_not_contains "$stale_tree_refs" '~/.config/opencode/skills/doct-document-ops/scripts/publish-coding-plan.sh' || return 1
  assert_command_output_not_contains "$stale_tree_refs" '$HOME/.pi/agent/skills/doct-document-ops/scripts/publish-coding-plan.sh' || return 1

  stale_install_instructions="$(git grep -n 'cp -r .*skills' README.md SETUP.md AGENTS.md _pi _opencode _omp skills install.sh || true)"
  [[ -z "$stale_install_instructions" ]] || return 1

  assert_file_not_contains "README.md" 'install to `~/.claude/skills`' || return 1
  assert_file_not_contains "README.md" 'install to `~/.config/opencode/skills`' || return 1
  assert_file_not_contains "README.md" 'install to `~/.pi/agent/skills`' || return 1
  # removed root duplicate
  # assert_file_not_contains "OPENCODE_ONBOARDING.md" 'install to `~/.config/opencode/skills`' || return 1
  assert_file_not_contains "_opencode/OPENCODE_ONBOARDING.md" 'install to `~/.config/opencode/skills`' || return 1

  assert_file_contains "thoughts/archive/plans/skill-consolidation-to-agents.md" '- [x] P4 - Validate migration behavior, preservation rules, consumer compatibility wiring, and final repo alignment.' || return 1
  assert_file_contains "thoughts/archive/plans/skill-consolidation-to-agents.md" '2026-04-02 (P4): Ran the final temp-home validation flow' || return 1
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
  run_test test_failpoint_after_backup_keeps_destination_recoverable
  run_test test_agent_extension_installs_preserve_or_manage_herdr_extensions
  run_test test_pi_interactive_shell_local_install_purges_stale_git_when_pi_list_fails
  run_test test_pi_interactive_shell_git_fallback_purges_stale_local_when_pi_list_fails
  run_test test_phase_three_docs_use_canonical_shared_skill_paths
  run_test test_phase_three_duplicate_skill_trees_are_removed
  run_test test_codex_pi_skill_and_prompt_parity
  run_test test_phase_four_validation_proves_final_alignment

  printf '\nTests run: %s\n' "$TESTS_RUN"
  printf 'Passed: %s\n' "$TESTS_PASSED"
  printf 'Failed: %s\n' "$TESTS_FAILED"

  [[ "$TESTS_FAILED" -eq 0 ]]
}

main "$@"
