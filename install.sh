#!/bin/bash

# Installation script for Claude Code, Codex, Pi, shared skills, and optional tools

if [ -z "${BASH_VERSION:-}" ]; then
    if command -v bash >/dev/null 2>&1; then
        exec bash "$0" "$@"
    fi
    echo "Error: install.sh requires bash" >&2
    exit 1
fi

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
TARGET_DIR="."
INSTALL_MODE="--default"
PI_VCC_PACKAGE_SOURCE=""
INSTALL_TOOLS=false
INSTALL_SKILLS=false
UPDATE_SKILLS=false
SKILLS_SH_UPDATE_RAN=false
SHARED_SKILLS_SYNCED=false
AI_CONFIGS_MANAGED_MARKER='.ai-configs-managed.json'
AI_CONFIGS_BACKUP_RUN_ID="$(date +"%Y%m%d-%H%M%S")"
AI_CONFIGS_REPO_NAME='ai-configs'
AI_CONFIGS_REPO_COMMIT="$(git -C "$REPO_ROOT" rev-parse HEAD 2>/dev/null || echo unknown)"
CENTRAL_ONLY_PROJECT_SKILLS=(ccore todoist-cli brave-cdp chrome-cdp)
DEPRECATED_SHARED_SKILLS=(
    agent-browser
    scoped-plan-run
    html-plan-reviewer
    omp-review-partner
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
# Retire the legacy, session-detail-backed todo extension in favor of the
# package-managed @tintinweb/pi-tasks extension.
RETIRED_PI_EXTENSIONS=(questionnaire.ts todo.ts)
DISABLED_PI_EXTENSIONS=(claude-review codex-review)

# Non-interactive SSH sessions on macOS may not source login shell files, so
# Homebrew's node/npm/npx can be installed but absent from PATH.
for brew_bin in /opt/homebrew/bin /usr/local/bin; do
    if [ -d "$brew_bin" ] && [[ ":$PATH:" != *":$brew_bin:"* ]]; then
        PATH="$brew_bin:$PATH"
    fi
done
export PATH

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_usage() {
    echo "Usage: $0 [--claude|--codex|--pi|--pi-vcc|--pi-review-stack|--tools|--skills|--all] [--update] [target-directory]"
    echo ""
    echo "Options:"
    echo "  --claude    Install Claude Code configuration and refresh shared skills for Claude"
    echo "  --codex     Sync global Codex prompts/scripts and refresh shared skills for Codex"
    echo "  --pi        Install Pi prompt templates, read-only/planning subagents, and extensions, then refresh shared skills"
    echo "  --pi-vcc [package-source]  Transactionally install only pi-vcc (repo package by default)"
    echo "  --pi-review-stack  Mutation-bounded Pi config plus six maintained review skills; no packages/global cleanup"
    echo "  --tools     Install/update managed Herdr config/plugins, Kitty remote workflow, and CLI tools"
    echo "  --skills    Sync repo-owned and package-managed shared skills into ~/.agents/skills"
    echo "  --all       Install Claude, Codex, Pi, tools, and shared skills"
    echo "  --update    Update globally installed skills tracked by skills.sh before shared-skill sync"
    echo ""
    echo "Default behavior (no args):"
    echo "  Installs Claude, Codex, Pi, and shared skills (no tools)."
    echo ""
    echo "Notes:"
    echo "  - Default shared skills are declared in skills/install-matrix.json and synced into ~/.agents/skills"
    echo "  - Shared review runtime installs at ~/.agents/scripts/review_orchestration.py"
    echo "  - Codex discovers shared default-profile skills directly from ~/.agents/skills"
    echo "  - Claude consumes compatible shared skills via per-skill links into ~/.agents/skills"
    echo "  - When using --pi or --all, Pi prompt templates, read-only/planning subagents, and repo-managed extensions are copied to ~/.pi/agent"
    echo "  - Repo-managed Pi extensions live under ~/.pi/agent/extensions and do NOT appear in 'pi list'"
    echo "  - When using --pi or --all, shared browser CDP skills install into ~/.agents/skills"
    echo "  - Package-managed Pi installs DO appear in 'pi list': @tintinweb/pi-subagents, @tintinweb/pi-tasks, @aliou/pi-processes, @narumitw/pi-goal, pi-web-access, @fnnm/pi-ast-grep, pi-updater, pi-powerline-footer, pi-no-soft-cursor, @tmustier/pi-files-widget, @tmustier/pi-raw-paste, @pi-kaush/pi-inline-skill-identifier, @howaboua/pi-vent, @howaboua/pi-explore-subagents, pi-service-tier, and vendored pi-vcc from the stable ~/.pi/agent/local-packages/ai-configs/pi-vcc mirror"
    echo "  - Use Herdr to launch and manage visible interactive agent sessions"
    echo "  - The tracked Herdr config is installed locally whenever --tools or --all runs"
    echo "  - Kitty/Herdr remote workflow files are streamed to mbp/dever whenever --tools or --all runs on macOS"
    echo "  - Managed Herdr plugins are refreshed from their upstream repositories whenever --tools or --all runs"
    echo "  - The installer removes positively identified managed deprecated skill entries; ambiguous Gemini, OMP, OpenCode, and Pi plan-mode files are preserved for explicit host cleanup"
    echo "  - Use --update to run 'npx skills update -g -y' for skills installed through skills.sh before the normal sync"
    echo "  - In non-interactive mode, existing configs are preserved automatically"
    echo ""
    echo "Examples:"
    echo "  $0                               # Default: install Claude + Codex + Pi + shared skills"
    echo "  $0 --claude                      # Install Claude to current directory"
    echo "  $0 --codex                       # Sync global Codex resources"
    echo "  $0 --pi                          # Install Pi prompt templates, read-only/planning subagents, extensions, and refresh shared skills"
    echo "  $0 --pi-vcc                     # Transactionally install only the vendored pi-vcc package"
    echo "  $0 --pi-vcc /path/to/pi-vcc     # Install or roll back from an explicit preserved package"
    echo "  $0 --tools                       # Install/update managed Herdr config/plugins, Kitty workflow, and CLI tools"
    echo "  $0 --skills                      # Sync repo-owned and package-managed shared skills into ~/.agents/skills"
    echo "  $0 --skills --update             # Update skills.sh-managed global skills, then sync shared skills"
    echo "  $0 --all                         # Install all maintained surfaces and tools"
}

cleanup_retired_runtime_surfaces() {
    local target_root="$1"
    local path

    # The retired Gemini, OMP, and Pi plan-mode trees may have been modified
    # after install. Preserve ambiguous live files here; host cleanup is an
    # explicit operator action after inspection.
    # OpenCode, Gemini, and OMP may contain user-owned files mixed into the
    # same directories. Their source trees are retired, but cleanup
    # intentionally leaves ambiguous live configuration untouched.
}

# Setup thoughts directory structure
setup_thoughts_structure() {
    local target_dir="$1"
    local thoughts_dir="$target_dir/thoughts"

    # Create main thoughts directory
    mkdir -p "$thoughts_dir"

    # Create all subdirectories
    local subdirs=(plans specs research handoffs prs validation debug linear archive)
    for subdir in "${subdirs[@]}"; do
        mkdir -p "$thoughts_dir/$subdir"
    done

    echo "  - Created thoughts/ directory structure"
}

# Create permanent documentation templates if they don't exist
create_permanent_docs() {
    local target_dir="$1"

    # CHANGELOG.md
    if [ ! -f "$target_dir/CHANGELOG.md" ]; then
        cat > "$target_dir/CHANGELOG.md" << 'EOF'
# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

<!--
Entries are added by /cmd:graduate after completing features.
Format:
## [Feature Name] - YYYY-MM-DD
### Added/Changed/Fixed
- Description of change
-->
EOF
        echo "  - Created CHANGELOG.md template"
    fi

    # spec/ directory structure
    if [ ! -d "$target_dir/spec" ]; then
        mkdir -p "$target_dir/spec/architecture"
        echo "  - Created spec/ directory structure"
    fi

    # spec/architecture/README.md
    if [ ! -f "$target_dir/spec/architecture/README.md" ]; then
        cat > "$target_dir/spec/architecture/README.md" << 'EOF'
# Architecture Documentation

This directory contains architecture documents for implemented features.

## Architecture Docs

| Feature | Document | Status | Description |
|---------|----------|--------|-------------|
<!-- Rows added by /cmd:graduate after completing features -->
EOF
        echo "  - Created spec/architecture/README.md template"
    fi

    # spec/adr-log.md
    if [ ! -f "$target_dir/spec/adr-log.md" ]; then
        cat > "$target_dir/spec/adr-log.md" << 'EOF'
# Architectural Decision Records

This document captures key architectural decisions and their rationale.

<!--
Entries are prepended by /cmd:graduate after completing features.
Format:
## ADR NNNN: [Decision Title]
**Status:** Accepted
**Date:** YYYY-MM

**Context:** ...
**Decision:** ...
**Alternatives considered:** ...
**Current state:** ...
-->
EOF
        echo "  - Created spec/adr-log.md template"
    fi
}

# Detect and migrate legacy directories
migrate_legacy_directories() {
    local target_dir="$1"
    local thoughts_dir="$target_dir/thoughts"

    # Check for legacy directories
    local has_tasks=false
    local has_tasks_complete=false
    local has_notes_linear=false
    local files_to_migrate=()

    if [ -d "$target_dir/tasks" ]; then
        has_tasks=true
    fi
    if [ -d "$target_dir/tasks-complete" ]; then
        has_tasks_complete=true
    fi
    if [ -d "$target_dir/notes/linear" ]; then
        has_notes_linear=true
    fi

    # If no legacy directories, return
    if [ "$has_tasks" = false ] && [ "$has_tasks_complete" = false ] && [ "$has_notes_linear" = false ]; then
        return 0
    fi

    # Display OBVIOUS migration banner
    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo -e "${CYAN}${BOLD}  🔄 MIGRATION DETECTED: Moving existing files to new thoughts/ structure${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "  ${BOLD}Found legacy directories:${NC}"

    if [ "$has_tasks" = true ]; then
        echo -e "    ${GREEN}✓${NC} tasks/           → will migrate to thoughts/plans/ and thoughts/specs/"
    fi
    if [ "$has_tasks_complete" = true ]; then
        echo -e "    ${GREEN}✓${NC} tasks-complete/  → will migrate to thoughts/archive/"
    fi
    if [ "$has_notes_linear" = true ]; then
        echo -e "    ${GREEN}✓${NC} notes/linear/    → will migrate to thoughts/linear/"
    fi
    echo ""

    # List files to be moved
    echo -e "  ${BOLD}The following files will be moved:${NC}"

    if [ "$has_tasks" = true ]; then
        shopt -s nullglob
        for file in "$target_dir/tasks"/*.md; do
            local filename=$(basename "$file")
            local dest=""
            case "$filename" in
                prd-*.md|tasks-*.md|simplify-plan-*.md)
                    dest="thoughts/plans/$filename"
                    ;;
                spec-*.md|research-spec-*.md)
                    dest="thoughts/specs/$filename"
                    ;;
                *)
                    dest="thoughts/plans/$filename"
                    ;;
            esac
            echo -e "    ${YELLOW}$filename${NC} → ${GREEN}$dest${NC}"
            files_to_migrate+=("$file:$target_dir/$dest")
        done
        shopt -u nullglob
    fi

    if [ "$has_tasks_complete" = true ]; then
        shopt -s nullglob
        for file in "$target_dir/tasks-complete"/*.md; do
            local filename=$(basename "$file")
            echo -e "    ${YELLOW}tasks-complete/$filename${NC} → ${GREEN}thoughts/archive/$filename${NC}"
            files_to_migrate+=("$file:$thoughts_dir/archive/$filename")
        done
        shopt -u nullglob
    fi

    if [ "$has_notes_linear" = true ]; then
        shopt -s nullglob
        for file in "$target_dir/notes/linear"/*.md; do
            local filename=$(basename "$file")
            echo -e "    ${YELLOW}notes/linear/$filename${NC} → ${GREEN}thoughts/linear/$filename${NC}"
            files_to_migrate+=("$file:$thoughts_dir/linear/$filename")
        done
        shopt -u nullglob
    fi

    echo ""
    echo -e "  ${YELLOW}⚠️  This is a ONE-TIME migration. Original directories will be removed.${NC}"
    echo -e "  ${YELLOW}⚠️  Git history preserves all files at their original locations.${NC}"
    echo ""

    # Prompt for confirmation
    if [ -t 0 ]; then
        printf "  Press ENTER to continue, or Ctrl+C to cancel... "
        read -r
    else
        echo "  (Non-interactive mode: proceeding with migration)"
    fi

    echo ""
    echo -e "${CYAN}═══════════════════════════════════════════════════════════════════════════════${NC}"
    echo ""

    # Perform migration
    echo "  - Migrating files..."

    # Ensure thoughts directory structure exists
    setup_thoughts_structure "$target_dir"

    # Move files
    for entry in "${files_to_migrate[@]}"; do
        local src="${entry%%:*}"
        local dest="${entry##*:}"
        if [ -f "$src" ]; then
            mv "$src" "$dest"
            echo "    Moved: $(basename "$src")"
        fi
    done

    # Remove empty legacy directories
    if [ "$has_tasks" = true ] && [ -d "$target_dir/tasks" ]; then
        if [ -z "$(ls -A "$target_dir/tasks" 2>/dev/null)" ]; then
            rmdir "$target_dir/tasks"
            echo "  - Removed empty tasks/ directory"
        else
            echo -e "  ${YELLOW}- tasks/ still contains files, not removing${NC}"
        fi
    fi

    if [ "$has_tasks_complete" = true ] && [ -d "$target_dir/tasks-complete" ]; then
        if [ -z "$(ls -A "$target_dir/tasks-complete" 2>/dev/null)" ]; then
            rmdir "$target_dir/tasks-complete"
            echo "  - Removed empty tasks-complete/ directory"
        else
            echo -e "  ${YELLOW}- tasks-complete/ still contains files, not removing${NC}"
        fi
    fi

    if [ "$has_notes_linear" = true ] && [ -d "$target_dir/notes/linear" ]; then
        if [ -z "$(ls -A "$target_dir/notes/linear" 2>/dev/null)" ]; then
            rmdir "$target_dir/notes/linear"
            # Also remove notes/ if empty
            if [ -d "$target_dir/notes" ] && [ -z "$(ls -A "$target_dir/notes" 2>/dev/null)" ]; then
                rmdir "$target_dir/notes"
            fi
            echo "  - Removed empty notes/linear/ directory"
        else
            echo -e "  ${YELLOW}- notes/linear/ still contains files, not removing${NC}"
        fi
    fi

    echo ""
    echo -e "${GREEN}  ✓ Migration complete!${NC}"
    echo ""
    echo -e "  ${BOLD}Suggested next step:${NC}"
    echo -e "    ${CYAN}git add -A && git commit -m \"chore: migrate to thoughts/ directory structure\"${NC}"
    echo ""
}

ask_overwrite_permission() {
    local target="$1"
    local description="$2"

    if [ -e "$target" ]; then
        echo ""
        echo -e "${YELLOW}  ═══════════════════════════════════════════════════════════════${NC}"
        echo -e "${YELLOW}  ⚠️  Existing configuration found${NC}"
        echo -e "${YELLOW}  ═══════════════════════════════════════════════════════════════${NC}"
        echo "  Location: $target"
        echo "  Type: $description"
        echo ""
        
        if [ -t 0 ]; then
            printf "  Overwrite existing configuration? [Y/n/skip] "
            read -r reply
            case "$reply" in
                ""|"Y"|"y")
                    echo -e "  ${GREEN}✓ Overwrite confirmed${NC}"
                    echo -e "${YELLOW}  ═══════════════════════════════════════════════════════════════${NC}"
                    echo ""
                    return 0
                    ;;
                *"skip"*|"n")
                    echo -e "  ${YELLOW}→ Skipping overwrite (preserving existing configuration)${NC}"
                    echo -e "${YELLOW}  ═══════════════════════════════════════════════════════════════${NC}"
                    echo ""
                    return 1
                    ;;
                *)
                    echo -e "  ${YELLOW}→ Skipping overwrite (preserving existing configuration)${NC}"
                    echo -e "${YELLOW}  ═══════════════════════════════════════════════════════════════${NC}"
                    echo ""
                    return 1
                    ;;
            esac
        else
            echo -e "  ${YELLOW}→ Non-interactive mode: preserving existing configuration${NC}"
            echo "  (Re-run with interactive shell to allow overwrite)"
            echo -e "${YELLOW}  ═══════════════════════════════════════════════════════════════${NC}"
            echo ""
            return 1
        fi
    fi
    return 0
}

sync_codex_prompts() {
    local destination="$1"
    local label="$2"
    local mode="${3:-merge}"

    if [ "$mode" = "replace" ] && [ -d "$destination" ]; then
        echo "  - Resetting $label at $destination"
        rm -rf "$destination"
    fi

    mkdir -p "$destination"

    echo "  - Syncing Codex prompts into $label ($destination)"

    local legacy_dirs=(cmd doc prd spec simplify)
    for legacy_dir in "${legacy_dirs[@]}"; do
        if [ -d "$destination/$legacy_dir" ]; then
            echo "    - Removing legacy subdirectory $legacy_dir/"
            rm -rf "$destination/$legacy_dir"
        fi
    done

    if [ -d "$destination/_lib" ]; then
        rm -rf "$destination/_lib"
    fi

    for prompt in "$REPO_ROOT"/_codex/prompts/*.md; do
        [ -e "$prompt" ] || continue
        cp "$prompt" "$destination/"
    done
}

install_claude() {
    local target="$1/.claude"
    local is_update=false

    # Detect if this is an update
    if [ -d "$target" ]; then
        is_update=true
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  Updating Claude Code Configuration${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${GREEN}Updating Claude Code configuration at $target${NC}"
    else
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  Installing Claude Code Configuration${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${GREEN}Installing Claude Code configuration to $target${NC}"
        mkdir -p "$target"
    fi

    # Preserve one read-only review subagent while removing any retired Claude
    # personas. The driving session remains the only implementation authority.
    echo "  - Installing managed Claude reviewer..."
    rm -rf "$target/agents"
    cp -r "$REPO_ROOT/_claude/agents" "$target/"

    # Update commands (remove first to ensure clean state)
    if [ -d "$target/commands" ]; then
        # Check for legacy subdirectories
        local has_legacy=false
        local legacy_dirs=(cmd doc prd spec)
        for legacy_dir in "${legacy_dirs[@]}"; do
            if [ -d "$target/commands/$legacy_dir" ]; then
                has_legacy=true
                break
            fi
        done

        if [ "$has_legacy" = true ]; then
            echo "  - Cleaning up legacy command structure (subdirectories will be flattened)..."
        fi
    fi

    echo "  - Installing commands..."
    if [ -d "$target/commands" ]; then
        rm -rf "$target/commands"
    fi
    cp -r "$REPO_ROOT/_claude/commands" "$target/"

    # Update scripts (remove first to ensure clean state)
    echo "  - Installing scripts..."
    if [ -d "$target/scripts" ]; then
        rm -rf "$target/scripts"
    fi
    cp -r "$REPO_ROOT/scripts" "$target/"

    # Handle settings.local.json (preserve if exists)
    if [ -f "$target/settings.local.json" ]; then
        echo -e "  ${YELLOW}✓ Preserved existing settings.local.json${NC}"
    else
        echo "  - Installing settings.local.json..."
        cp "$REPO_ROOT/_claude/settings.local.json" "$target/"
    fi

    # Setup thoughts directory structure and migrate legacy directories
    migrate_legacy_directories "$1"
    if [ ! -d "$1/thoughts" ]; then
        setup_thoughts_structure "$1"
    fi
    create_permanent_docs "$1"

    if [ "$is_update" = true ]; then
        echo -e "${GREEN}✓ Claude Code update complete${NC}"
    else
        echo -e "${GREEN}✓ Claude Code installation complete${NC}"
    fi
    echo ""
    echo "Note: CLAUDE.md is NOT installed - codex will generate this file."
}

install_tools() {
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Installing CLI Tools${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo ""

    install_herdr_config
    echo ""
    install_kitty_remote_workflow
    echo ""
    install_herdr_plugins
    echo ""
    install_ltui
}

install_herdr_config() {
    echo "Installing managed Herdr configuration..."
    bash "$REPO_ROOT/herdr/install.sh"
    echo -e "${GREEN}✓ Managed Herdr configuration installed${NC}"
}

install_kitty_remote_workflow() {
    echo "Installing managed Kitty remote workflow..."
    bash "$REPO_ROOT/kitty/install.sh"

    # A macOS Kitty client is the distribution point for both remote hosts.
    # Stream the tracked files instead of relying on either remote repo being
    # clean or already updated. Offline hosts warn by default rather than
    # blocking unrelated tool updates.
    if [ "$(uname -s)" = "Darwin" ]; then
        bash "$REPO_ROOT/scripts/install-kitty-remote-hosts.sh"
    fi

    echo -e "${GREEN}✓ Managed Kitty remote workflow processed${NC}"
}

install_herdr_plugins() {
    echo "Installing managed Herdr plugins..."

    local herdr_plugins=(
        "persiyanov/herdr-reviewr"
    )

    if ! command -v herdr >/dev/null 2>&1; then
        echo -e "${YELLOW}⚠ Herdr not found in PATH; skipping managed Herdr plugins${NC}"
        return 0
    fi

    for source in "${herdr_plugins[@]}"; do
        echo "  - Installing/updating $source..."
        if herdr plugin install "$source" --yes; then
            echo -e "    ${GREEN}✓ $source installed and current${NC}"
        else
            echo -e "    ${RED}✗ Failed to install/update Herdr plugin $source${NC}"
            return 1
        fi
    done

    echo -e "${GREEN}✓ Managed Herdr plugins processed${NC}"
}

install_ltui() {
    echo "Installing ltui from standalone repository..."

    local ltui_repo_url="${LTUI_REPO_URL:-https://github.com/Nodaste-Lab/ltui.git}"
    local ltui_ref="${LTUI_REF:-main}"
    local cache_root="${XDG_CACHE_HOME:-$HOME/.cache}/ai-configs/tools"
    local checkout_dir="$cache_root/ltui"
    local install_bin_dir="$HOME/.local/bin"

    for required_cmd in git npm node; do
        if ! command -v "$required_cmd" >/dev/null 2>&1; then
            echo -e "${RED}Error: $required_cmd is required to install ltui${NC}"
            return 1
        fi
    done

    mkdir -p "$cache_root" "$install_bin_dir"

    if [ -d "$checkout_dir/.git" ]; then
        echo "  - Updating $checkout_dir..."
        git -C "$checkout_dir" remote set-url origin "$ltui_repo_url"
        git -C "$checkout_dir" fetch --prune origin
    else
        if [ -e "$checkout_dir" ]; then
            echo "  - Replacing non-git ltui cache at $checkout_dir..."
            rm -rf "$checkout_dir"
        fi

        echo "  - Cloning $ltui_repo_url into $checkout_dir..."
        git clone "$ltui_repo_url" "$checkout_dir"
        git -C "$checkout_dir" fetch --prune origin
    fi

    if git -C "$checkout_dir" rev-parse --verify --quiet "origin/$ltui_ref" >/dev/null; then
        git -C "$checkout_dir" checkout --force -B ai-configs-install "origin/$ltui_ref"
    else
        git -C "$checkout_dir" checkout --force "$ltui_ref"
    fi

    echo "  - Installing dependencies..."
    (cd "$checkout_dir" && npm ci)

    echo "  - Building ltui..."
    (cd "$checkout_dir" && npm run build)

    echo "  - Installing ltui into $install_bin_dir..."
    ln -sfn "$checkout_dir/bin/ltui" "$install_bin_dir/ltui"

    # Older ai-configs installs may have put a Bun global link earlier in PATH.
    # If that link still points at the old vendored ai-configs copy, repoint it
    # so `which ltui` resolves to the standalone checkout too.
    local bun_module_link="$HOME/.bun/install/global/node_modules/ltui"
    local bun_bin_link="$HOME/.bun/bin/ltui"

    if [ -L "$bun_module_link" ]; then
        local bun_module_target
        bun_module_target="$(readlink "$bun_module_link")"
        if [[ "$bun_module_target" == *"ai-configs/tools/ltui"* ]]; then
            echo "  - Updating stale Bun ltui module link..."
            ln -sfn "$checkout_dir" "$bun_module_link"
        fi
    fi

    if [ -L "$bun_bin_link" ]; then
        local bun_bin_target
        bun_bin_target="$(readlink "$bun_bin_link")"
        if [[ "$bun_bin_target" == *"node_modules/ltui/bin/ltui"* || "$bun_bin_target" == *"ai-configs/tools/ltui/bin/ltui"* ]]; then
            echo "  - Updating stale Bun ltui binary link..."
            ln -sfn "$checkout_dir/bin/ltui" "$bun_bin_link"
        fi
    fi

    echo -e "${GREEN}✓ ltui installed successfully${NC}"
    echo "  Source: $ltui_repo_url"
    echo "  Ref: $ltui_ref"
    echo "  Checkout: $checkout_dir"
    echo ""

    if [[ ":$PATH:" != *":$install_bin_dir:"* ]]; then
        echo -e "${YELLOW}⚠  NOTE: $install_bin_dir is not in your PATH${NC}"
        echo "  Add this to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
        echo "    export PATH=\"$install_bin_dir:\$PATH\""
        echo ""
        echo "  After updating, run: source ~/.zshrc  (or restart your shell)"
        echo "  Then verify with: ltui --help"
    else
        echo "  ltui is now available globally. Try: ltui --help"
    fi
}

skill_matrix_path() {
    echo "$REPO_ROOT/skills/install-matrix.json"
}

iterate_installable_skills() {
    local matrix_path
    matrix_path="$(skill_matrix_path)"

    if [ ! -f "$matrix_path" ]; then
        echo -e "${RED}Error: Missing install matrix at $matrix_path${NC}" >&2
        return 1
    fi

    python3 - "$matrix_path" <<'PY'
import json
import sys

matrix_path = sys.argv[1]
with open(matrix_path, 'r', encoding='utf-8') as handle:
    data = json.load(handle)

for name, meta in sorted(data["installableSkills"].items()):
    source_type = meta.get("sourceType", "repo")
    if source_type == "external-package":
        source_id = f"external-package:{meta['packageSource']}#{name}"
    else:
        source_id = meta["canonicalSource"]

    print("\t".join([
        name,
        source_id,
        meta.get("class", ""),
        ",".join(meta.get("allowedConsumers", [])),
        "false" if meta.get("defaultInstall") is False else "true",
    ]))
PY
}

iterate_repo_installable_skills() {
    local matrix_path
    matrix_path="$(skill_matrix_path)"

    python3 - "$matrix_path" <<'PY'
import json
import sys

matrix_path = sys.argv[1]
with open(matrix_path, 'r', encoding='utf-8') as handle:
    data = json.load(handle)

for name, meta in sorted(data["installableSkills"].items()):
    if meta.get("sourceType", "repo") != "repo":
        continue
    if meta.get("defaultInstall") is False:
        continue
    print("\t".join([name, meta["canonicalSource"]]))
PY
}

iterate_external_skill_packages() {
    local matrix_path
    matrix_path="$(skill_matrix_path)"

    python3 - "$matrix_path" <<'PY'
import json
import sys
from collections import defaultdict

matrix_path = sys.argv[1]
with open(matrix_path, 'r', encoding='utf-8') as handle:
    data = json.load(handle)

groups = defaultdict(list)
for name, meta in sorted(data["installableSkills"].items()):
    if meta.get("sourceType") != "external-package":
        continue
    if meta.get("defaultInstall") is False:
        continue
    package_skill_name = meta.get("packageSkillName", name)
    groups[meta["packageSource"]].append(f"{name}={package_skill_name}")

for package_source, skills in sorted(groups.items()):
    print("\t".join([package_source, ",".join(sorted(skills))]))
PY
}

iterate_optional_installable_skills() {
    local matrix_path
    matrix_path="$(skill_matrix_path)"

    python3 - "$matrix_path" <<'PY'
import json
import sys

matrix_path = sys.argv[1]
with open(matrix_path, 'r', encoding='utf-8') as handle:
    data = json.load(handle)

for name, meta in sorted(data["installableSkills"].items()):
    if meta.get("defaultInstall") is not False:
        continue
    source_type = meta.get("sourceType", "repo")
    if source_type == "external-package":
        source_id = f"external-package:{meta['packageSource']}#{name}"
    else:
        source_id = meta["canonicalSource"]
    print("\t".join([name, source_id, meta.get("profile", "optional")]))
PY
}

consumer_is_forced() {
    local consumer="$1"
    shift || true
    local forced_consumer
    for forced_consumer in "$@"; do
        if [ "$forced_consumer" = "$consumer" ]; then
            return 0
        fi
    done
    return 1
}

consumer_allows_skill() {
    local consumer="$1"
    local consumers_csv="$2"
    local default_install="${3:-true}"

    if [ "$default_install" != "true" ]; then
        return 1
    fi

    case ",${consumers_csv}," in
        *",${consumer},"*)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

is_repo_managed_skill_dir() {
    local skill_dir="$1"
    local expected_source="$2"
    local marker_path="$skill_dir/$AI_CONFIGS_MANAGED_MARKER"

    if [ ! -f "$marker_path" ]; then
        return 1
    fi

    python3 - "$marker_path" "$expected_source" <<'PY'
import json
import sys

marker_path = sys.argv[1]
expected_source = sys.argv[2]

with open(marker_path, 'r', encoding='utf-8') as handle:
    data = json.load(handle)

if data.get("repo") != "ai-configs":
    raise SystemExit(1)
if data.get("managed") is not True:
    raise SystemExit(1)
if data.get("source") != expected_source:
    raise SystemExit(1)
PY
}

write_skill_marker() {
    local skill_dir="$1"
    local source_rel="$2"

    python3 - "$skill_dir/$AI_CONFIGS_MANAGED_MARKER" "$source_rel" "$AI_CONFIGS_REPO_COMMIT" <<'PY'
import json
import sys

marker_path = sys.argv[1]
source_rel = sys.argv[2]
repo_commit = sys.argv[3]

payload = {
    "repo": "ai-configs",
    "source": source_rel,
    "managed": True,
    "commit": repo_commit,
}

with open(marker_path, 'w', encoding='utf-8') as handle:
    json.dump(payload, handle, indent=2)
    handle.write("\n")
PY
}

build_external_skill_source_id() {
    local package_source="$1"
    local skill_name="$2"
    echo "external-package:${package_source}#${skill_name}"
}

stage_skill_payload_from_dir() {
    local skill_name="$1"
    local source_id="$2"
    local source_path="$3"
    local shared_skills_dir="$4"
    local stage_dir

    if [ ! -d "$source_path" ]; then
        echo -e "${RED}Error: Missing skill source directory $source_path${NC}" >&2
        return 1
    fi

    stage_dir="$(mktemp -d "$shared_skills_dir/.${skill_name}.stage.XXXXXX")"
    cp -a "$source_path/." "$stage_dir/"
    write_skill_marker "$stage_dir" "$source_id"
    echo "$stage_dir"
}

stage_repo_skill_payload() {
    local skill_name="$1"
    local source_rel="$2"
    local shared_skills_dir="$3"
    local source_path="$REPO_ROOT/$source_rel"

    stage_skill_payload_from_dir "$skill_name" "$source_rel" "$source_path" "$shared_skills_dir"
}

stage_external_skill_payload() {
    local skill_name="$1"
    local package_source="$2"
    local package_skill_name="$3"
    local package_skills_dir="$4"
    local shared_skills_dir="$5"
    local source_id
    local source_path="$package_skills_dir/$package_skill_name"

    source_id="$(build_external_skill_source_id "$package_source" "$skill_name")"
    stage_skill_payload_from_dir "$skill_name" "$source_id" "$source_path" "$shared_skills_dir"
}

skills_are_identical() {
    local left_dir="$1"
    local right_dir="$2"
    diff -qr "$left_dir" "$right_dir" >/dev/null 2>&1
}

backup_existing_path() {
    local destination_path="$1"
    local backup_rel="$2"
    local backup_root="$HOME/.agents/skill-backups/$AI_CONFIGS_REPO_NAME/$AI_CONFIGS_BACKUP_RUN_ID"
    local backup_path="$backup_root/$backup_rel"

    mkdir -p "$(dirname "$backup_path")"
    cp -a "$destination_path" "$backup_path"
    echo "$backup_path"
}

backup_existing_skill() {
    local destination_path="$1"
    local skill_name="$2"
    backup_existing_path "$destination_path" "$skill_name"
}

backup_existing_consumer_entry() {
    local entry_path="$1"
    local consumer="$2"
    local skill_name="$3"
    backup_existing_path "$entry_path" "consumers/$consumer/$skill_name"
}

resolve_abs_path() {
    python3 - "$1" <<'PY'
import sys
from pathlib import Path

print(Path(sys.argv[1]).expanduser().resolve(strict=False))
PY
}

backup_project_local_skill() {
    local entry_path="$1"
    local target_root="$2"
    local skill_name="$3"
    local target_hash

    target_hash="$(python3 - "$target_root" <<'PY'
import hashlib
import sys

print(hashlib.sha1(sys.argv[1].encode('utf-8')).hexdigest())
PY
)"
    backup_existing_path "$entry_path" "project-local/$target_hash/$skill_name"
}

enforce_central_project_skills() {
    local target_root="$1"
    local resolved_target
    local resolved_repo
    local project_skills_dir
    local skill_name
    local local_skill_path
    local central_skill_path
    local backup_path

    resolved_target="$(resolve_abs_path "$target_root")"
    resolved_repo="$(resolve_abs_path "$REPO_ROOT")"

    if [ "$resolved_target" = "$resolved_repo" ]; then
        return 0
    fi

    project_skills_dir="$resolved_target/.agents/skills"
    if [ ! -d "$project_skills_dir" ]; then
        return 0
    fi

    for skill_name in "${CENTRAL_ONLY_PROJECT_SKILLS[@]}"; do
        local_skill_path="$project_skills_dir/$skill_name"
        if [ ! -e "$local_skill_path" ] && [ ! -L "$local_skill_path" ]; then
            continue
        fi

        central_skill_path="$HOME/.agents/skills/$skill_name"
        if [ ! -f "$central_skill_path/SKILL.md" ]; then
            echo -e "${RED}Error: Project-local skill $skill_name exists at $local_skill_path, but $central_skill_path/SKILL.md is missing.${NC}" >&2
            echo "  Install the central skill under ~/.agents/skills/$skill_name or remove the project-local copy manually." >&2
            return 1
        fi

        backup_path="$(backup_project_local_skill "$local_skill_path" "$resolved_target" "$skill_name")"
        rm -rf "$local_skill_path"
        echo "  - Removed project-local $skill_name skill; using ~/.agents/skills/$skill_name (backup: $backup_path)"
    done
}

failpoint_matches() {
    local phase_name="$1"
    local skill_name="$2"
    [ "${AI_CONFIGS_FAILPOINT:-}" = "${phase_name}:${skill_name}" ]
}

print_recovery_error() {
    local skill_name="$1"
    local backup_path="$2"
    local reason="$3"

    echo -e "${RED}Error: ${reason}${NC}" >&2
    echo "  Restore the affected skill from $backup_path and rerun ./install.sh --skills after resolving the underlying issue." >&2
}

install_staged_shared_skill() {
    local skill_name="$1"
    local source_id="$2"
    local stage_dir="$3"
    local shared_skills_dir="$4"
    local destination_path="$shared_skills_dir/$skill_name"
    local previous_path
    local backup_path

    if [ -e "$destination_path" ] || [ -L "$destination_path" ]; then
        if is_repo_managed_skill_dir "$destination_path" "$source_id"; then
            if skills_are_identical "$stage_dir" "$destination_path"; then
                rm -rf "$stage_dir"
                echo "    - Shared skill unchanged: $skill_name"
                return 0
            fi

            previous_path="$shared_skills_dir/.${skill_name}.previous.$$"
            rm -rf "$previous_path"
            mv "$destination_path" "$previous_path"
            if mv "$stage_dir" "$destination_path"; then
                rm -rf "$previous_path"
                echo "    - Updated shared skill: $skill_name"
                return 0
            fi

            mv "$previous_path" "$destination_path"
            rm -rf "$stage_dir"
            echo -e "${RED}Error: Failed to update managed shared skill $skill_name${NC}" >&2
            return 1
        fi

        backup_path="$(backup_existing_skill "$destination_path" "$skill_name")"
        if failpoint_matches "after-backup" "$skill_name"; then
            rm -rf "$stage_dir"
            print_recovery_error "$skill_name" "$backup_path" "Triggered test failpoint after-backup:$skill_name"
            return 1
        fi

        previous_path="$shared_skills_dir/.${skill_name}.previous.$$"
        rm -rf "$previous_path"
        mv "$destination_path" "$previous_path"
        if mv "$stage_dir" "$destination_path"; then
            rm -rf "$previous_path"
            echo "    - Replaced colliding shared skill: $skill_name"
            return 0
        fi

        mv "$previous_path" "$destination_path"
        rm -rf "$stage_dir"
        print_recovery_error "$skill_name" "$backup_path" "Failed to replace colliding shared skill $skill_name"
        return 1
    fi

    mv "$stage_dir" "$destination_path"
    echo "    - Installed shared skill: $skill_name"
}

install_shared_skill() {
    local skill_name="$1"
    local source_rel="$2"
    local shared_skills_dir="$3"
    local stage_dir

    stage_dir="$(stage_repo_skill_payload "$skill_name" "$source_rel" "$shared_skills_dir")"
    install_staged_shared_skill "$skill_name" "$source_rel" "$stage_dir" "$shared_skills_dir"
}

install_external_skill_package() {
    local package_source="$1"
    local csv_skill_mappings="$2"
    local shared_skills_dir="$3"
    local temp_home
    local package_skills_dir
    local skill_mapping
    local local_skill_name
    local package_skill_name
    local source_id
    local stage_dir
    local package_skill_names=()
    local skill_mappings=()

    if ! command -v npx >/dev/null 2>&1; then
        echo -e "${RED}Error: npx is required to fetch external package-managed skills${NC}" >&2
        return 1
    fi

    IFS=',' read -r -a skill_mappings <<< "$csv_skill_mappings"
    for skill_mapping in "${skill_mappings[@]}"; do
        local_skill_name="${skill_mapping%%=*}"
        package_skill_name="${skill_mapping#*=}"
        package_skill_names+=("$package_skill_name")
    done

    temp_home="$(mktemp -d)"
    package_skills_dir="$temp_home/.agents/skills"

    if ! HOME="$temp_home" npx skills add "$package_source" -g --skill "${package_skill_names[@]}" -y </dev/null >/dev/null; then
        rm -rf "$temp_home"
        echo -e "${RED}Error: Failed to fetch external skills from $package_source via npx skills${NC}" >&2
        return 1
    fi

    for skill_mapping in "${skill_mappings[@]}"; do
        local_skill_name="${skill_mapping%%=*}"
        package_skill_name="${skill_mapping#*=}"
        source_id="$(build_external_skill_source_id "$package_source" "$local_skill_name")"
        stage_dir="$(stage_external_skill_payload "$local_skill_name" "$package_source" "$package_skill_name" "$package_skills_dir" "$shared_skills_dir")" || {
            rm -rf "$temp_home"
            return 1
        }
        install_staged_shared_skill "$local_skill_name" "$source_id" "$stage_dir" "$shared_skills_dir" || {
            rm -rf "$temp_home"
            return 1
        }
    done

    rm -rf "$temp_home"
}

remove_skill_lock_entries() {
    local lock_path="$HOME/.agents/.skill-lock.json"

    if [ ! -f "$lock_path" ]; then
        return 0
    fi

    python3 - "$lock_path" "$@" <<'PY'
import json
import sys
from pathlib import Path

lock_path = Path(sys.argv[1])
skill_names = sys.argv[2:]

data = json.loads(lock_path.read_text())
skills = data.get("skills")
if not isinstance(skills, dict):
    raise SystemExit(0)

changed = False
for name in skill_names:
    if name in skills:
        del skills[name]
        changed = True

if changed:
    lock_path.write_text(json.dumps(data, indent=2) + "\n")
PY
}

cleanup_optional_profile_shared_skills() {
    local shared_skills_dir="$HOME/.agents/skills"
    local skill_name
    local source_rel
    local profile
    local path
    local backup_path
    local removed_skills=()

    while IFS=$'\t' read -r skill_name source_rel profile; do
        path="$shared_skills_dir/$skill_name"
        if [ ! -e "$path" ] && [ ! -L "$path" ]; then
            continue
        fi

        if is_repo_managed_skill_dir "$path" "$source_rel"; then
            backup_path="$(backup_existing_path "$path" "optional/$profile/$skill_name")"
            rm -rf "$path"
            removed_skills+=("$skill_name")
            echo "    - Removed optional-profile shared skill from default discovery: $skill_name (profile: $profile, backup: $backup_path)"
        fi
    done < <(iterate_optional_installable_skills)

    if [ ${#removed_skills[@]} -gt 0 ]; then
        remove_skill_lock_entries "${removed_skills[@]}"
    fi
}

cleanup_deprecated_shared_skills() {
    local shared_skills_dir="$HOME/.agents/skills"
    local skill_name
    local path
    local source_rel
    local backup_path
    local shared_managed
    local removed_skills=()

    for skill_name in "${DEPRECATED_SHARED_SKILLS[@]}"; do
        source_rel="skills/$skill_name"
        path="$shared_skills_dir/$skill_name"
        shared_managed=false
        if [ -d "$path" ] && is_repo_managed_skill_dir "$path" "$source_rel"; then
            shared_managed=true
            backup_path="$(backup_existing_path "$path" "deprecated/shared/$skill_name")"
            rm -rf "$path"
            removed_skills+=("$skill_name")
            echo "    - Removed deprecated shared skill: $skill_name (backup: $backup_path)"
        elif [ -e "$path" ] || [ -L "$path" ]; then
            echo "    - Preserved non-managed skill named $skill_name at $path"
        fi

        for path in \
            "$HOME/.claude/skills/$skill_name" \
            "$HOME/.config/opencode/skills/$skill_name" \
            "$HOME/.pi/agent/skills/$skill_name"; do
            if [ ! -e "$path" ] && [ ! -L "$path" ]; then
                continue
            fi
            if [ -L "$path" ] && [ "$(readlink "$path")" = "$shared_skills_dir/$skill_name" ]; then
                if [ "$shared_managed" = true ] || [ ! -e "$shared_skills_dir/$skill_name" ]; then
                    rm -f "$path"
                    echo "    - Removed deprecated managed or dangling skill link: $path"
                else
                    echo "    - Preserved skill link named $skill_name because its shared target is not ai-configs-managed: $path"
                fi
            elif [ -d "$path" ] && is_repo_managed_skill_dir "$path" "$source_rel"; then
                backup_path="$(backup_existing_path "$path" "deprecated/consumer/$skill_name")"
                rm -rf "$path"
                echo "    - Removed deprecated managed skill copy: $path (backup: $backup_path)"
            else
                echo "    - Preserved non-managed skill entry named $skill_name at $path"
            fi
        done
    done

    if [ ${#removed_skills[@]} -gt 0 ]; then
        remove_skill_lock_entries "${removed_skills[@]}"
    fi
}

consumer_entry_is_repo_managed() {
    local entry_path="$1"
    local shared_target="$2"
    local expected_source="$3"

    if [ -L "$entry_path" ] && [ "$(readlink "$entry_path")" = "$shared_target" ]; then
        return 0
    fi

    if [ -d "$entry_path" ] && is_repo_managed_skill_dir "$entry_path" "$expected_source"; then
        return 0
    fi

    return 1
}

ensure_consumer_skill_link() {
    local consumer="$1"
    local consumer_dir="$2"
    local skill_name="$3"
    local source_rel="$4"
    local shared_skills_dir="$5"
    local shared_target="$shared_skills_dir/$skill_name"
    local link_path="$consumer_dir/$skill_name"
    local previous_path
    local backup_path

    if [ ! -d "$shared_target" ]; then
        echo -e "${RED}Error: Shared skill target missing for $skill_name at $shared_target${NC}" >&2
        return 1
    fi

    if [ -L "$link_path" ] && [ "$(readlink "$link_path")" = "$shared_target" ]; then
        return 0
    fi

    if [ -e "$link_path" ] || [ -L "$link_path" ]; then
        previous_path="$consumer_dir/.${skill_name}.previous.$$"
        rm -rf "$previous_path"

        if consumer_entry_is_repo_managed "$link_path" "$shared_target" "$source_rel"; then
            mv "$link_path" "$previous_path"
            if ln -s "$shared_target" "$link_path"; then
                rm -rf "$previous_path"
                return 0
            fi

            mv "$previous_path" "$link_path"
            echo -e "${RED}Error: Failed to update managed $consumer skill entry $skill_name${NC}" >&2
            return 1
        fi

        backup_path="$(backup_existing_consumer_entry "$link_path" "$consumer" "$skill_name")"
        mv "$link_path" "$previous_path"
        if ln -s "$shared_target" "$link_path"; then
            rm -rf "$previous_path"
            echo "    - Backed up colliding $consumer skill before linking: $skill_name"
            return 0
        fi

        mv "$previous_path" "$link_path"
        echo -e "${RED}Error: Failed to replace colliding $consumer skill entry $skill_name${NC}" >&2
        echo "  Restore the affected consumer skill from $backup_path and rerun ./install.sh --skills after resolving the underlying issue." >&2
        return 1
    fi

    ln -s "$shared_target" "$link_path"
}

remove_consumer_skill_entry() {
    local consumer="$1"
    local consumer_dir="$2"
    local skill_name="$3"
    local source_rel="$4"
    local shared_skills_dir="$5"
    local entry_path="$consumer_dir/$skill_name"
    local shared_target="$shared_skills_dir/$skill_name"
    local previous_path
    local backup_path

    if [ ! -e "$entry_path" ] && [ ! -L "$entry_path" ]; then
        return 0
    fi

    if consumer_entry_is_repo_managed "$entry_path" "$shared_target" "$source_rel"; then
        rm -rf "$entry_path"
        return 0
    fi

    backup_path="$(backup_existing_consumer_entry "$entry_path" "$consumer" "$skill_name")"
    previous_path="$consumer_dir/.${skill_name}.previous.$$"
    rm -rf "$previous_path"
    mv "$entry_path" "$previous_path"
    if rm -rf "$previous_path"; then
        echo "    - Backed up incompatible $consumer skill before removal: $skill_name"
        return 0
    fi

    mv "$previous_path" "$entry_path"
    echo -e "${RED}Error: Failed to remove colliding $consumer skill entry $skill_name${NC}" >&2
    echo "  Restore the affected consumer skill from $backup_path and rerun ./install.sh --skills after resolving the underlying issue." >&2
    return 1
}

sync_consumer_skill_links() {
    local consumer="$1"
    local consumer_dir="$2"
    shift 2

    if consumer_is_forced "$consumer" "$@"; then
        mkdir -p "$consumer_dir"
    fi

    if [ ! -d "$consumer_dir" ]; then
        echo "  - Skipping $consumer compatibility links (directory missing: $consumer_dir)"
        return 0
    fi

    echo "  - Synchronizing $consumer compatibility links in $consumer_dir..."
    while IFS=$'\t' read -r skill_name source_rel _skill_class allowed_consumers default_install; do
        if consumer_allows_skill "$consumer" "$allowed_consumers" "$default_install"; then
            ensure_consumer_skill_link "$consumer" "$consumer_dir" "$skill_name" "$source_rel" "$HOME/.agents/skills"
        else
            remove_consumer_skill_entry "$consumer" "$consumer_dir" "$skill_name" "$source_rel" "$HOME/.agents/skills"
        fi
    done < <(iterate_installable_skills)
}

cleanup_pi_shared_skill_mirrors() {
    local pi_skills_dir="$1"

    if [ ! -d "$pi_skills_dir" ]; then
        return 0
    fi

    echo "  - Removing repo-managed shared skill mirrors from $pi_skills_dir..."
    while IFS=$'\t' read -r skill_name source_rel _skill_class _allowed_consumers _default_install; do
        remove_consumer_skill_entry "pi" "$pi_skills_dir" "$skill_name" "$source_rel" "$HOME/.agents/skills"
    done < <(iterate_installable_skills)
}

sync_shared_skills() {
    local shared_skills_dir="$HOME/.agents/skills"

    if [ "$UPDATE_SKILLS" = true ]; then
        update_installed_skills_from_skills_sh
        echo ""
    fi

    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Syncing Shared Skills${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo ""

    mkdir -p "$shared_skills_dir" "$HOME/.agents/scripts" "$HOME/.local/bin"
    install -m 0755 "$REPO_ROOT/scripts/review_orchestration.py" "$HOME/.agents/scripts/review_orchestration.py"
    echo "  - Installed shared review runtime at ~/.agents/scripts/review_orchestration.py"
    install -m 0755 "$REPO_ROOT/scripts/git-with-index-lock" "$HOME/.agents/scripts/git-with-index-lock"
    install -m 0755 "$REPO_ROOT/scripts/ensure-git-with-index-lock" "$HOME/.agents/scripts/ensure-git-with-index-lock"
    ln -sfn "$HOME/.agents/scripts/git-with-index-lock" "$HOME/.local/bin/git-with-index-lock"
    ln -sfn "$HOME/.agents/scripts/ensure-git-with-index-lock" "$HOME/.local/bin/ensure-git-with-index-lock"
    echo "  - Installed git-with-index-lock + ensure-git-with-index-lock at ~/.agents/scripts and ~/.local/bin"

    echo "  - Syncing repo-managed shared skills from skills/ into ~/.agents/skills/..."
    while IFS=$'\t' read -r skill_name source_rel; do
        install_shared_skill "$skill_name" "$source_rel" "$shared_skills_dir"
    done < <(iterate_repo_installable_skills)

    echo "  - Fetching external package-managed shared skills via npx skills..."
    while IFS=$'\t' read -r package_source csv_skill_names; do
        install_external_skill_package "$package_source" "$csv_skill_names" "$shared_skills_dir"
    done < <(iterate_external_skill_packages)

    cleanup_deprecated_shared_skills
    cleanup_optional_profile_shared_skills

    sync_consumer_skill_links "claude" "$HOME/.claude/skills" "$@"
    cleanup_pi_shared_skill_mirrors "$HOME/.pi/agent/skills"

    echo -e "${GREEN}✓ Shared skills synced successfully${NC}"
    SHARED_SKILLS_SYNCED=true
    echo ""
    echo "  Default shared skills now live in ~/.agents/skills"
    echo "  Repo-owned payloads come from skills/; package-backed payloads are fetched per skills/install-matrix.json"
    echo "  Optional-profile skills remain declared in the matrix but are backed out of default discovery"
}

update_installed_skills_from_skills_sh() {
    if [ "$SKILLS_SH_UPDATE_RAN" = true ]; then
        return 0
    fi

    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Updating Installed skills.sh Skills${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo ""

    if ! command -v npx >/dev/null 2>&1; then
        echo -e "${RED}Error: npx is required to update skills through skills.sh${NC}" >&2
        return 1
    fi

    echo "  - Running npx skills update -g -y..."
    if ! npx skills update -g -y </dev/null; then
        echo -e "${RED}Error: skills.sh update failed${NC}" >&2
        return 1
    fi

    SKILLS_SH_UPDATE_RAN=true
    echo -e "${GREEN}✓ skills.sh-managed global skills updated successfully${NC}"
}

install_skills() {
    sync_shared_skills "$@"
}

install_codex() {
    local target="$1/.codex"

    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Syncing Codex Global Resources${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo ""

    if [ -d "$target" ]; then
        echo "  - Found existing project .codex directory; cleaning only legacy generated files..."

        local project_prompts_dir="${target}/prompts"
        if [ -d "$project_prompts_dir" ]; then
            echo "    - Removing project prompts (Codex prefers ~/.codex/prompts)..."
            rm -rf "$project_prompts_dir"
        fi

        local project_scripts_dir="${target}/scripts"
        if [ -d "$project_scripts_dir" ]; then
            echo "    - Removing project scripts (Codex prefers ~/.codex/scripts)..."
            rm -rf "$project_scripts_dir"
        fi

        # Do not install or mutate Codex config.toml. Project-local Codex config
        # overrides ~/.codex/config.toml, including account/model settings.
        if [ -f "$target/config.toml" ]; then
            if grep -q '^# Codex Configuration Template$' "$target/config.toml" \
                && grep -q '^# MCP Servers - see mcp-servers.toml for additional server definitions$' "$target/config.toml"; then
                echo "    - Removing legacy generated Codex config.toml..."
                rm -f "$target/config.toml"
            else
                echo -e "    ${YELLOW}- Leaving existing Codex config.toml untouched${NC}"
            fi
        fi

        if [ -f "$target/mcp-servers.toml" ] && cmp -s "$REPO_ROOT/_codex/mcp-servers.toml" "$target/mcp-servers.toml"; then
            echo "    - Removing legacy generated mcp-servers.toml..."
            rm -f "$target/mcp-servers.toml"
        fi

        rmdir "$target" 2>/dev/null || true
    fi

    local global_codex_dir="$HOME/.codex"
    mkdir -p "$global_codex_dir"
    local global_prompts_dir="${global_codex_dir}/prompts"
    sync_codex_prompts "$global_prompts_dir" "global (~/.codex/prompts)" "replace"

    echo "  - Syncing Codex scripts globally..."
    rm -rf "$global_codex_dir/scripts"
    cp -r "$REPO_ROOT/scripts" "$global_codex_dir/"

    echo -e "${GREEN}✓ Codex global resource sync complete${NC}"
    echo ""
    echo "Codex account, model, and MCP settings remain in ~/.codex/config.toml"
}


# Install shared appended system guidance for Pi with traceable repo metadata.
install_pi_append_system_file() {
    local agent_target="$1"
    local append_system_source="$REPO_ROOT/APPEND_SYSTEM.md"
    local append_system_target="$agent_target/APPEND_SYSTEM.md"

    if [ -f "$append_system_source" ]; then
        local version
        version="$(python3 "$REPO_ROOT/scripts/render_pi_append_system.py" \
            --repo "$REPO_ROOT" \
            --source "$append_system_source" \
            --target "$append_system_target")" || return 1
        echo "  - Installed APPEND_SYSTEM.md (${version})"
    fi
}

remove_repo_managed_pi_extension_registrations() {
    local pi_agent_dir="$1"
    local pi_source_extensions_dir="$2"
    local pi_live_extensions_dir="$3"
    local settings_path="$pi_agent_dir/settings.json"

    [ -f "$settings_path" ] || return 0
    [ -d "$pi_source_extensions_dir" ] || return 0

    local disabled_names
    disabled_names="$(IFS=,; echo "${DISABLED_PI_EXTENSIONS[*]}")"

    python3 - "$settings_path" "$pi_source_extensions_dir" "$pi_live_extensions_dir" "$disabled_names" <<'PY'
import json
import os
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
source_dir = Path(sys.argv[2])
live_dir = Path(sys.argv[3])
disabled_names = {name for name in sys.argv[4].split(",") if name}
managed_names = {entry.name for entry in source_dir.iterdir()} | disabled_names

try:
    data = json.loads(settings_path.read_text())
except Exception:
    raise SystemExit(0)

extensions = data.get("extensions")
if not isinstance(extensions, list):
    raise SystemExit(0)

live_root = os.path.realpath(live_dir)
non_local_prefixes = ("npm:", "git:", "http:", "https:", "github:", "ssh:")
ambiguous_relative = []

def source_of(item):
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        return item.get("source")
    return None

def is_managed(item):
    source = source_of(item)
    if not isinstance(source, str) or source.startswith(non_local_prefixes):
        return False
    expanded = os.path.expanduser(source)
    if not os.path.isabs(expanded):
        normalized = os.path.normpath(expanded).replace(os.sep, "/")
        basename = os.path.basename(normalized)
        if normalized == f".pi/agent/extensions/{basename}" and basename in managed_names:
            return True
        if basename in managed_names:
            ambiguous_relative.append(source)
        return False
    resolved = os.path.realpath(expanded)
    return os.path.dirname(resolved) == live_root and os.path.basename(resolved) in managed_names

filtered = [item for item in extensions if not is_managed(item)]
for source in ambiguous_relative:
    print(
        f"  ! Preserving ambiguous relative Pi extension registration: {source}",
        file=sys.stderr,
    )
if filtered == extensions:
    raise SystemExit(0)
if filtered:
    data["extensions"] = filtered
else:
    data.pop("extensions", None)
settings_path.write_text(json.dumps(data, indent=2) + "\n")
PY
}

ensure_pi_prompt_paths() {
    local pi_agent_dir="$1"
    local pi_prompts_dir="$2"
    local settings_path="$pi_agent_dir/settings.json"

    if [ ! -d "$pi_prompts_dir" ]; then
        return
    fi

    local status
    status=$(PI_AGENT_DIR="$pi_agent_dir" PI_PROMPTS_DIR="$pi_prompts_dir" SETTINGS_PATH="$settings_path" python3 <<'PY'
import json
import os
from pathlib import Path

agent_dir = Path(os.environ["PI_AGENT_DIR"])
prompts_dir = Path(os.environ["PI_PROMPTS_DIR"])
settings_path = Path(os.environ["SETTINGS_PATH"])

if settings_path.exists():
    data = json.loads(settings_path.read_text())
else:
    data = {}

prompts = data.get("prompts")
if prompts is None:
    prompts = []
elif not isinstance(prompts, list):
    raise SystemExit("invalid-prompts-setting")

required_entries = []
for child in sorted(prompts_dir.iterdir(), key=lambda path: path.name):
    if child.is_dir():
        relative = child.relative_to(agent_dir).as_posix()
        required_entries.append(f"./{relative}")

managed_prefix = f"./{prompts_dir.relative_to(agent_dir).as_posix()}/"
updated = [entry for entry in prompts if not (isinstance(entry, str) and entry.startswith(managed_prefix))]
for entry in required_entries:
    if entry not in updated:
        updated.append(entry)

if updated != prompts:
    if updated:
        data["prompts"] = updated
    else:
        data.pop("prompts", None)
    settings_path.write_text(json.dumps(data, indent=2) + "\n")
    print("updated")
else:
    print("unchanged")
PY
)
    local settings_status=$?

    if [ $settings_status -ne 0 ]; then
        echo "  - Unable to update Pi prompt discovery paths (check $settings_path manually)"
        return
    fi

    if [ "$status" = "updated" ]; then
        echo "  - Synchronized Pi settings prompt directory entries"
    fi
}

configure_pi_model_defaults() {
    local pi_root_dir="$1"
    local pi_agent_dir="$2"
    local settings_path="$pi_agent_dir/settings.json"
    local web_search_path="$pi_root_dir/web-search.json"

    echo "  - Enforcing Pi local Codex defaults..."

    local status
    status=$(PI_SETTINGS_PATH="$settings_path" PI_WEB_SEARCH_PATH="$web_search_path" python3 <<'PY'
import json
import os
from pathlib import Path

settings_path = Path(os.environ["PI_SETTINGS_PATH"])
web_search_path = Path(os.environ["PI_WEB_SEARCH_PATH"])

DEFAULT_PROVIDER = "openai-codex"
DEFAULT_MODEL = "gpt-5.6-sol"
DEFAULT_MODEL_VALUE = f"{DEFAULT_PROVIDER}/{DEFAULT_MODEL}"
GLM_SCOPED_MODEL_VALUE = "opencode/glm-5.2"
SPARK_MODEL = "gpt-5.3-codex-spark"
# Retired Grok CLI-proxy models. Strip them from enabledModels on install so
# previously managed machines do not keep offering removed providers.
RETIRED_GROK_MODEL_PREFIXES = ("grok/",)
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

changed = []

if settings_path.exists():
    settings = json.loads(settings_path.read_text())
else:
    settings = {}

before_settings = json.dumps(settings, sort_keys=True)
settings["defaultProvider"] = DEFAULT_PROVIDER
settings["defaultModel"] = DEFAULT_MODEL
settings["gptConfig"] = {
    "fastMode": False,
    "personality": "none",
    "verbosity": "medium",
    "summary": "auto",
    "toolDiscipline": "off",
    "showFooter": True,
}
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
    if model.startswith(RETIRED_GROK_MODEL_PREFIXES) or model in RETIRED_GROK_MODEL_IDS:
        continue
    if model.startswith("openai-codex-") and model.endswith(f"/{DEFAULT_MODEL}"):
        model = DEFAULT_MODEL_VALUE
    if model not in normalized:
        normalized.append(model)
if DEFAULT_MODEL_VALUE not in normalized:
    normalized.insert(0, DEFAULT_MODEL_VALUE)
if GLM_SCOPED_MODEL_VALUE not in normalized:
    normalized.append(GLM_SCOPED_MODEL_VALUE)
settings["enabledModels"] = normalized

if json.dumps(settings, sort_keys=True) != before_settings:
    settings_path.parent.mkdir(parents=True, exist_ok=True)
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")
    changed.append("settings")

if web_search_path.exists():
    web_search = json.loads(web_search_path.read_text())
else:
    web_search = {}
if not isinstance(web_search, dict):
    raise SystemExit("web-search.json must be a JSON object")

before_web_search = json.dumps(web_search, sort_keys=True)
web_search["summaryModel"] = DEFAULT_MODEL_VALUE
if json.dumps(web_search, sort_keys=True) != before_web_search:
    web_search_path.parent.mkdir(parents=True, exist_ok=True)
    web_search_path.write_text(json.dumps(web_search, indent=2) + "\n")
    changed.append("web-search")

print(",".join(changed) if changed else "unchanged")
PY
)
    local config_status=$?

    if [ $config_status -ne 0 ]; then
        echo "  - Unable to enforce Pi local Codex defaults (check $settings_path and $web_search_path manually)"
        return
    fi

    if [ "$status" = "unchanged" ]; then
        echo "  - Pi local Codex defaults already configured"
    else
        echo "  - Updated Pi local Codex defaults: $status"
    fi
}

install_pi_agents_from_repo() {
    local pi_source_dir="$1"
    local pi_agents_dir="$2"

    rm -rf "$pi_agents_dir"
    mkdir -p "$pi_agents_dir"
    if [ -d "$pi_source_dir/agents" ]; then
        cp -r "$pi_source_dir/agents/." "$pi_agents_dir/"
    fi
}

cleanup_pi_multi_codex_config() {
    local pi_agent_dir="$1"
    local auth_path="$pi_agent_dir/auth.json"
    local multi_pass_path="$pi_agent_dir/multi-pass.json"

    local status
    status=$(PI_AGENT_DIR="$pi_agent_dir" python3 <<'PY'
import json
import os
import shutil
import time
from pathlib import Path

agent_dir = Path(os.environ["PI_AGENT_DIR"])
stamp = time.strftime("%Y%m%d-%H%M%S")
changed = []

auth_path = agent_dir / "auth.json"
if auth_path.exists():
    data = json.loads(auth_path.read_text())
    if isinstance(data, dict):
        stale_keys = [key for key in data if isinstance(key, str) and key.startswith("openai-codex-")]
        if stale_keys:
            shutil.copy2(auth_path, agent_dir / f"auth.json.backup-before-local-codex-{stamp}")
            for key in stale_keys:
                data.pop(key, None)
            auth_path.write_text(json.dumps(data, indent=2) + "\n")
            changed.append("auth")

multi_pass_path = agent_dir / "multi-pass.json"
if multi_pass_path.exists():
    shutil.copy2(multi_pass_path, agent_dir / f"multi-pass.json.backup-before-local-codex-{stamp}")
    multi_pass_path.unlink()
    changed.append("multi-pass")

print(",".join(changed) if changed else "unchanged")
PY
)
    local cleanup_status=$?

    if [ $cleanup_status -ne 0 ]; then
        echo "  - Unable to clean stale multi-Codex auth/config (check $pi_agent_dir manually)"
        return
    fi

    if [ "$status" = "unchanged" ]; then
        echo "  - Stale multi-Codex auth/config already absent"
    else
        echo "  - Removed stale multi-Codex auth/config: $status"
    fi
}

validate_pi_model_inputs() {
    local pi_source_dir="$1"
    local pi_agent_dir="$2"
    local source_path="$pi_source_dir/models.json"
    local target_path="$pi_agent_dir/models.json"
    local settings_path="$pi_agent_dir/settings.json"

    if [ ! -f "$source_path" ]; then
        return
    fi

    PI_MODELS_SOURCE="$source_path" PI_MODELS_TARGET="$target_path" PI_SETTINGS_TARGET="$settings_path" python3 <<'PY'
import json
import os
from pathlib import Path

source_path = Path(os.environ["PI_MODELS_SOURCE"])
target_path = Path(os.environ["PI_MODELS_TARGET"])
settings_path = Path(os.environ["PI_SETTINGS_TARGET"])
source_data = json.loads(source_path.read_text())
target_data = json.loads(target_path.read_text()) if target_path.exists() else {}

if not isinstance(source_data, dict):
    raise SystemExit("source models.json must be a JSON object")
if not isinstance(target_data, dict):
    raise SystemExit("target models.json must be a JSON object")
source_providers = source_data.get("providers")
if not isinstance(source_providers, dict):
    raise SystemExit("source models.json must contain a providers object")
if "providers" in target_data and not isinstance(target_data["providers"], dict):
    raise SystemExit("target models.json providers field is not an object")

for provider_id, provider in source_providers.items():
    if not isinstance(provider, dict):
        raise SystemExit(f"provider {provider_id!r} is not an object")
    models = provider.get("models")
    if models is not None:
        if not isinstance(models, list):
            raise SystemExit(f"provider {provider_id!r} models field is not a list")
        if any(not isinstance(model, dict) or not isinstance(model.get("id"), str) for model in models):
            raise SystemExit(f"provider {provider_id!r} contains a model without an id")
    if "modelOverrides" in provider and not isinstance(provider["modelOverrides"], dict):
        raise SystemExit(f"provider {provider_id!r} modelOverrides field is not an object")

if settings_path.exists():
    settings = json.loads(settings_path.read_text())
    if not isinstance(settings, dict):
        raise SystemExit("settings.json must be a JSON object")
    enabled_models = settings.get("enabledModels")
    if enabled_models is not None and not isinstance(enabled_models, list):
        raise SystemExit("settings enabledModels must be a list when present")
PY
}

install_pi_models_from_repo() {
    local pi_source_dir="$1"
    local pi_agent_dir="$2"
    local inputs_validated="${3:-false}"
    local source_path="$pi_source_dir/models.json"
    local target_path="$pi_agent_dir/models.json"

    if [ ! -f "$source_path" ]; then
        return
    fi
    if [ "$inputs_validated" != true ]; then
        validate_pi_model_inputs "$pi_source_dir" "$pi_agent_dir"
    fi

    echo "  - Merging Pi model configuration..."

    local status
    status=$(PI_MODELS_SOURCE="$source_path" PI_MODELS_TARGET="$target_path" python3 <<'PY'
import copy
import json
import os
from pathlib import Path

source_path = Path(os.environ["PI_MODELS_SOURCE"])
target_path = Path(os.environ["PI_MODELS_TARGET"])
settings_path = target_path.parent / "settings.json"
source_data = json.loads(source_path.read_text())
target_exists = target_path.exists()
target_data = json.loads(target_path.read_text()) if target_exists else {}

if not isinstance(source_data, dict):
    raise SystemExit("source models.json must be a JSON object")
if not isinstance(target_data, dict):
    raise SystemExit("target models.json must be a JSON object")

source_providers = source_data.get("providers")
if not isinstance(source_providers, dict):
    raise SystemExit("source models.json must contain a providers object")

if "providers" in target_data and not isinstance(target_data["providers"], dict):
    raise SystemExit("target models.json providers field is not an object")

updated_data = copy.deepcopy(target_data)
target_providers = updated_data.setdefault("providers", {})

# Retire only exact model IDs previously managed by ai-configs. Display names
# are not an ownership boundary: callers may keep custom CLI Proxy API models.
RETIRED_OPENAI_CODEX_MODEL_IDS = {"gpt-5.4", "gpt-5.4-mini"}

def prune_retired_managed_models():
    openai_codex_provider = target_providers.get("openai-codex")
    if isinstance(openai_codex_provider, dict):
        target_models = openai_codex_provider.get("models")
        if isinstance(target_models, list):
            openai_codex_provider["models"] = [
                model for model in target_models
                if not (
                    isinstance(model, dict)
                    and model.get("id") in RETIRED_OPENAI_CODEX_MODEL_IDS
                )
            ]

    ollama_provider = target_providers.get("ollama")
    if isinstance(ollama_provider, dict):
        models = ollama_provider.get("models")
        if isinstance(models, list):
            retired_model_ids = {"glm-5.2:cloud", "kimi-k2.5:cloud"}
            ollama_provider["models"] = [
                model for model in models
                if not (isinstance(model, dict) and model.get("id") in retired_model_ids)
            ]
            if not ollama_provider["models"]:
                ollama_provider.pop("models")

        is_old_managed_ollama = (
            ollama_provider.get("baseUrl") == "https://ollama.com/v1"
            and ollama_provider.get("api") == "openai-completions"
            and ollama_provider.get("apiKey") == "$OLLAMA_API_KEY"
            and "models" not in ollama_provider
        )
        if is_old_managed_ollama:
            target_providers.pop("ollama", None)

    opencode_provider = target_providers.get("opencode")
    if isinstance(opencode_provider, dict):
        overrides = opencode_provider.get("modelOverrides")
        if isinstance(overrides, dict):
            overrides.pop("glm-5.2", None)
            if not overrides:
                opencode_provider.pop("modelOverrides")
        if not opencode_provider:
            target_providers.pop("opencode", None)

    opencode_zen_provider = target_providers.get("opencode-zen")
    if isinstance(opencode_zen_provider, dict):
        overrides = opencode_zen_provider.get("modelOverrides")
        if isinstance(overrides, dict):
            overrides.pop("glm-5", None)
            overrides.pop("glm-5.2", None)
            if not overrides:
                opencode_zen_provider.pop("modelOverrides")
        if not opencode_zen_provider:
            target_providers.pop("opencode-zen", None)

    # Grok was previously managed via the local CLI Proxy API provider. Remove
    # the whole provider once it is no longer present in _pi/models.json.
    if "grok" not in source_providers:
        target_providers.pop("grok", None)

prune_retired_managed_models()

def merge_missing(target, source):
    for merge_key, merge_value in source.items():
        if merge_key not in target:
            target[merge_key] = copy.deepcopy(merge_value)
        elif isinstance(target[merge_key], dict) and isinstance(merge_value, dict):
            merge_missing(target[merge_key], merge_value)

# Model overrides are repo-managed compatibility fixes. Source values must win
# so rerunning install repairs stale or incorrect effort mappings.
def merge_source_wins(target, source):
    for merge_key, merge_value in source.items():
        if isinstance(target.get(merge_key), dict) and isinstance(merge_value, dict):
            merge_source_wins(target[merge_key], merge_value)
        else:
            target[merge_key] = copy.deepcopy(merge_value)

for provider_id, source_provider in source_providers.items():
    if not isinstance(source_provider, dict):
        raise SystemExit(f"provider {provider_id!r} is not an object")

    target_provider = target_providers.get(provider_id)
    if not isinstance(target_provider, dict):
        target_providers[provider_id] = copy.deepcopy(source_provider)
        continue

    for key, source_value in source_provider.items():
        if key == "models":
            if not isinstance(source_value, list):
                raise SystemExit(f"provider {provider_id!r} models field is not a list")
            target_models = target_provider.get("models")
            if not isinstance(target_models, list):
                target_models = []
                target_provider["models"] = target_models

            models_by_id = {
                model.get("id"): model
                for model in target_models
                if isinstance(model, dict) and isinstance(model.get("id"), str)
            }
            for source_model in source_value:
                if not isinstance(source_model, dict) or not isinstance(source_model.get("id"), str):
                    raise SystemExit(f"provider {provider_id!r} contains a model without an id")
                existing_model = models_by_id.get(source_model["id"])
                if existing_model is None:
                    copied_model = copy.deepcopy(source_model)
                    target_models.append(copied_model)
                    models_by_id[copied_model["id"]] = copied_model
                elif provider_id == "openai-codex":
                    merge_source_wins(existing_model, source_model)
                else:
                    merge_missing(existing_model, source_model)
        elif key == "modelOverrides":
            if not isinstance(source_value, dict):
                raise SystemExit(f"provider {provider_id!r} modelOverrides field is not an object")
            target_overrides = target_provider.get("modelOverrides")
            if not isinstance(target_overrides, dict):
                target_provider["modelOverrides"] = copy.deepcopy(source_value)
            else:
                merge_source_wins(target_overrides, source_value)
        elif key == "compat" and isinstance(source_value, dict) and isinstance(target_provider.get("compat"), dict):
            if provider_id == "openai-codex":
                merge_source_wins(target_provider["compat"], source_value)
            else:
                merge_missing(target_provider["compat"], source_value)
        elif provider_id == "openai-codex" or key not in target_provider:
            target_provider[key] = copy.deepcopy(source_value)

models_changed = updated_data != target_data
settings = None
settings_changed = False
if settings_path.exists():
    settings = json.loads(settings_path.read_text())
    if not isinstance(settings, dict):
        raise SystemExit("settings.json must be a JSON object")
    enabled_models = settings.get("enabledModels")
    if enabled_models is not None and not isinstance(enabled_models, list):
        raise SystemExit("settings enabledModels must be a list when present")
    if isinstance(enabled_models, list):
        retained = []
        for value in enabled_models:
            retired = False
            if isinstance(value, str):
                if value in RETIRED_OPENAI_CODEX_MODEL_IDS:
                    retired = True
                elif "/" in value:
                    provider_id, model_id = value.split("/", 1)
                    retired = (
                        model_id in RETIRED_OPENAI_CODEX_MODEL_IDS
                        and (provider_id == "openai-codex" or provider_id.startswith("openai-codex-"))
                    )
            if not retired:
                retained.append(value)
        if retained != enabled_models:
            settings["enabledModels"] = retained
            settings_changed = True

if models_changed:
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(json.dumps(updated_data, indent=2) + "\n")
if settings_changed:
    settings_path.write_text(json.dumps(settings, indent=2) + "\n")

if models_changed or settings_changed:
    print("created" if models_changed and not target_exists else "updated")
else:
    print("unchanged")
PY
)
    local merge_status=$?

    if [ $merge_status -ne 0 ]; then
        echo "  - Unable to merge Pi model configuration (check $target_path manually)"
        return
    fi

    case "$status" in
        created) echo "  - Created Pi model configuration" ;;
        updated) echo "  - Updated Pi model configuration" ;;
    esac
}

install_pi() {
    local is_update=false
    local pi_root_dir="$HOME/.pi"
    local pi_agent_dir="$pi_root_dir/agent"
    local pi_skills_dir="$pi_agent_dir/skills"
    local pi_prompts_dir="$pi_agent_dir/prompts"
    local pi_agents_dir="$pi_agent_dir/agents"
    local pi_extensions_dir="$pi_agent_dir/extensions"
    local pi_source_dir="$REPO_ROOT/_pi"

    # This is a home-directory install only, similar to shared skills.
    if [ ! -d "$pi_source_dir" ]; then
        echo -e "${YELLOW}No _pi directory found in repository, skipping Pi install...${NC}"
        return
    fi

    if [ -d "$pi_agent_dir" ]; then
        is_update=true
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  Updating Pi Configuration${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${GREEN}Updating Pi configuration at $pi_agent_dir${NC}"
    else
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  Installing Pi Configuration${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${GREEN}Installing Pi configuration to $pi_agent_dir${NC}"
        mkdir -p "$pi_agent_dir"
    fi

    # Install Pi prompt templates.
    echo "  - Installing Pi prompt templates..."
    rm -rf "$pi_prompts_dir"
    mkdir -p "$pi_prompts_dir"
    if [ -d "$pi_source_dir/prompts" ]; then
        cp -r "$pi_source_dir/prompts/." "$pi_prompts_dir/"
        ensure_pi_prompt_paths "$pi_agent_dir" "$pi_prompts_dir"
    fi

    # Shared installable skills are discovered via ~/.agents/skills.
    echo "  - Shared installable skills are discovered via ~/.agents/skills; ~/.pi/agent/skills is reserved for Pi-local-only entries."

    # Install planning and read-only subagent definitions for @tintinweb/pi-subagents.
    echo "  - Installing Pi planning/read-only subagents..."
    install_pi_agents_from_repo "$pi_source_dir" "$pi_agents_dir"

    # Install extensions.
    echo "  - Installing Pi extensions..."
    mkdir -p "$pi_extensions_dir"
    for retired_extension in "${RETIRED_PI_EXTENSIONS[@]}"; do
        rm -rf "$pi_extensions_dir/$retired_extension"
    done
    for disabled_extension in "${DISABLED_PI_EXTENSIONS[@]}"; do
        rm -rf "$pi_extensions_dir/$disabled_extension"
    done
    if [ -d "$pi_source_dir/extensions" ]; then
        # Detect external clobbering of ai-configs-managed extensions before
        # restoring them, so the drift is visible in the install log. The main
        # offender is `herdr integration install pi`, which overwrites
        # herdr-agent-state.ts with herdr's stock (non-watchdog) asset.
        local herdr_ext_src="$pi_source_dir/extensions/herdr-agent-state.ts"
        local herdr_ext_live="$pi_extensions_dir/herdr-agent-state.ts"
        local herdr_ext_clobbered=false
        if [ -f "$herdr_ext_src" ] && [ -f "$herdr_ext_live" ]; then
            if ! cmp -s "$herdr_ext_src" "$herdr_ext_live" 2>/dev/null; then
                herdr_ext_clobbered=true
            fi
        fi

        # Remove only repo-managed extension entries before re-copying so
        # foreign extensions injected by other apps at runtime (i.e. any
        # extension not tracked under _pi/extensions) are preserved across
        # reinstalls. Entries that ARE tracked here are treated as
        # ai-configs-managed and overwritten every run.
        shopt -s nullglob
        for entry in "$pi_source_dir/extensions"/*; do
            local ext_base
            ext_base="$(basename "$entry")"
            rm -rf "$pi_extensions_dir/$ext_base"
        done
        shopt -u nullglob
        cp -r "$pi_source_dir/extensions/." "$pi_extensions_dir/"
        # Pi auto-discovers ~/.pi/agent/extensions. Remove stale explicit
        # registrations for repo-managed files so the same extension is not
        # loaded twice on hosts that predate auto-discovery.
        remove_repo_managed_pi_extension_registrations \
            "$pi_agent_dir" "$pi_source_dir/extensions" "$pi_extensions_dir"

        if [ "$herdr_ext_clobbered" = true ]; then
            echo -e "  ${YELLOW}→ herdr-agent-state.ts was modified externally (likely 'herdr integration install pi'); restored ai-configs version${NC}"
        fi
    fi

    install_pi_models_from_repo "$pi_source_dir" "$pi_agent_dir"
    configure_pi_model_defaults "$pi_root_dir" "$pi_agent_dir"
    cleanup_pi_multi_codex_config "$pi_agent_dir"

    # Install globally managed pi-tasks defaults so every Pi session uses the
    # repo-owned scope unless an explicit PI_TASKS override is supplied.
    if [ -f "$pi_source_dir/tasks-config.json" ]; then
        echo "  - Installing Pi task configuration..."
        cp "$pi_source_dir/tasks-config.json" "$pi_agent_dir/tasks-config.json"
    fi

    # Install documentation.
    if [ -f "$pi_source_dir/README.md" ]; then
        echo "  - Installing Pi documentation..."
        cp "$pi_source_dir/README.md" "$pi_agent_dir/README.md"
    fi

    install_pi_append_system_file "$pi_agent_dir"

    if [ "$is_update" = true ]; then
        echo -e "${GREEN}✓ Pi update complete${NC}"
    else
        echo -e "${GREEN}✓ Pi installation complete${NC}"
    fi
    echo ""
    echo "Note: Pi prompt templates, planning/read-only subagents, extensions, and managed model entries are installed to $HOME/.pi/agent"
    echo "      Prompt templates load from ~/.pi/agent/prompts, shared installable skills load from ~/.agents/skills, subagents load from ~/.pi/agent/agents, extensions load from ~/.pi/agent/extensions, custom models load from ~/.pi/agent/models.json, and managed task defaults load from ~/.pi/agent/tasks-config.json"

    # Remove retired Pi tooling before installing supported packages.
    remove_retired_pi_goal_plugin "$pi_agent_dir"
    remove_retired_pi_interactive_shell_package "$pi_agent_dir"
    remove_deprecated_pi_git_packages

    # Install npm-based pi extensions
    install_pi_npm_packages

    # Install vendored pi-vcc through Pi so compaction behavior is pinned to this repo.
    install_vendored_pi_vcc_package

    # Reinstall repo-managed planning/read-only subagent overrides after package
    # installs so they win over plugin defaults and stay under version control.
    echo "  - Re-installing Pi planning/read-only subagent overrides after Pi package installs..."
    install_pi_agents_from_repo "$pi_source_dir" "$pi_agents_dir"

    # Package installs/extensions can touch settings; finish by restoring the
    # repo-owned default model contract so obsolete multi-Codex routes cannot be reintroduced.
    configure_pi_model_defaults "$pi_root_dir" "$pi_agent_dir"
    cleanup_pi_multi_codex_config "$pi_agent_dir"
}

install_pi_review_stack() {
    local pi_source="$REPO_ROOT/_pi"
    local agent="$HOME/.pi/agent"
    local shared="$HOME/.agents/skills"
    local review_runtime_dir="$HOME/.agents/scripts"
    local skill entry base target parent_metadata managed_pi_path
    if [ -L "$HOME/.pi" ]; then
        echo "Error: mutation-bounded Pi review-stack installation requires ~/.pi to be a real directory, not a symlink." >&2
        return 1
    fi
    for managed_pi_path in "$HOME/.pi/agent" "$HOME/.pi/agent/prompts" "$HOME/.pi/agent/agents" "$HOME/.pi/agent/extensions" "$HOME/.pi/agent/models.json" "$HOME/.pi/agent/tasks-config.json" "$HOME/.pi/agent/settings.json" "$HOME/.pi/agent/README.md" "$HOME/.pi/agent/APPEND_SYSTEM.md"; do
        if [ -L "$managed_pi_path" ]; then
            echo "Error: mutation-bounded Pi review-stack installation refuses symlinks at managed ~/.pi paths: $managed_pi_path" >&2
            return 1
        fi
    done
    # Validate every model/settings JSON shape before creating directories or
    # replacing any bounded review-stack surface.
    validate_pi_model_inputs "$pi_source" "$agent"
    parent_metadata="$(mktemp)"
    python3 - "$parent_metadata" "$HOME/.agents" "$HOME/.agents/skills" "$review_runtime_dir" <<'PY'
import json, os, stat, sys
out = {}
for raw in sys.argv[2:]:
    if os.path.isdir(raw):
        resolved = os.path.realpath(raw)
        value = os.stat(resolved)
        out[resolved] = {"mode": stat.S_IMODE(value.st_mode), "atime_ns": value.st_atime_ns, "mtime_ns": value.st_mtime_ns}
json.dump(out, open(sys.argv[1], "w"))
PY
    mkdir -p "$agent/prompts" "$agent/agents" "$agent/extensions" "$shared" "$review_runtime_dir"
    chmod 700 "$HOME/.pi" "$agent" "$agent/prompts" "$agent/agents" "$agent/extensions" 2>/dev/null || true

    # Prompts and extensions remain mutation-bounded: replace only entries owned
    # by this repository and preserve caller-installed siblings.
    for target in prompts extensions; do
        if [ -d "$pi_source/$target" ]; then
            shopt -s nullglob
            for entry in "$pi_source/$target"/*; do
                base="$(basename "$entry")"
                rm -rf "$agent/$target/$base"
                cp -a "$entry" "$agent/$target/$base"
            done
            shopt -u nullglob
        fi
    done

    for disabled_extension in "${DISABLED_PI_EXTENSIONS[@]}"; do
        rm -rf "$agent/extensions/$disabled_extension"
    done
    remove_repo_managed_pi_extension_registrations \
        "$agent" "$pi_source/extensions" "$agent/extensions"

    # Agent definitions are one exact managed directory in both full and
    # bounded installs. Reuse the canonical helper so retired/stale personas
    # cannot survive a review-stack transaction.
    install_pi_agents_from_repo "$pi_source" "$agent/agents"
    chmod 700 "$agent/agents" 2>/dev/null || true
    install_pi_models_from_repo "$pi_source" "$agent" true
    cp "$pi_source/README.md" "$agent/README.md"
    install_pi_append_system_file "$agent"

    for skill in autoreview claude-code-review codex-review-partner pre-pr-implementation-review reviewed-html-plan run-plan; do
        rm -rf "$shared/$skill"
        cp -a "$REPO_ROOT/skills/$skill" "$shared/$skill"
    done
    rm -f "$review_runtime_dir/review_orchestration.py" "$review_runtime_dir/git-with-index-lock" "$review_runtime_dir/ensure-git-with-index-lock"
    install -m 0755 "$REPO_ROOT/scripts/review_orchestration.py" "$review_runtime_dir/review_orchestration.py"
    install -m 0755 "$REPO_ROOT/scripts/git-with-index-lock" "$review_runtime_dir/git-with-index-lock"
    install -m 0755 "$REPO_ROOT/scripts/ensure-git-with-index-lock" "$review_runtime_dir/ensure-git-with-index-lock"
    mkdir -p "$HOME/.local/bin"
    ln -sfn "$review_runtime_dir/git-with-index-lock" "$HOME/.local/bin/git-with-index-lock"
    ln -sfn "$review_runtime_dir/ensure-git-with-index-lock" "$HOME/.local/bin/ensure-git-with-index-lock"
    python3 - "$parent_metadata" <<'PY'
import json, os, sys
for raw, value in json.load(open(sys.argv[1])).items():
    if os.path.isdir(raw):
        os.chmod(raw, value["mode"])
        os.utime(raw, ns=(value["atime_ns"], value["mtime_ns"]))
PY
    rm -f "$parent_metadata"
    echo -e "${GREEN}✓ Mutation-bounded Pi review stack installed${NC}"
}

remove_retired_pi_goal_plugin() {
    local pi_agent_dir="$1"
    local settings_path="$pi_agent_dir/settings.json"
    local source

    while IFS= read -r source; do
        [ -n "$source" ] || continue
        echo "  - Removing retired Pi goal package $source..."
        pi remove "$source" 2>/dev/null || true
    done < <(pi list 2>/dev/null | awk '/^  [^ ]/ && /pi-codex-goal/ { sub(/^  /, ""); print }')

    python3 - "$settings_path" <<'PY'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
if not settings_path.exists():
    raise SystemExit(0)
try:
    data = json.loads(settings_path.read_text())
except json.JSONDecodeError:
    raise SystemExit(0)
if not isinstance(data, dict):
    raise SystemExit(0)
packages = data.get("packages")
if isinstance(packages, list):
    data["packages"] = [
        item for item in packages
        if "pi-codex-goal" not in (
            item.get("source", "") if isinstance(item, dict) else item if isinstance(item, str) else ""
        )
    ]
data.pop("piCodexGoal", None)
settings_path.write_text(json.dumps(data, indent=2) + "\n")
PY

    rm -rf \
        "$pi_agent_dir/git/github.com/adnichols/pi-codex-goal" \
        "$pi_agent_dir/npm/node_modules/pi-codex-goal"
}

remove_deprecated_pi_git_packages() {
    local deprecated_git_packages=(
        "git:github.com/adnichols/pi-dcp"
        "git:github.com/adnichols/pi-rlm"
        "git:github.com/pasky/chrome-cdp-skill"
        "git:github.com/adnichols/pi-multi-pass"
        "git:github.com/edxeth/pi-gpt-config"
    )

    for source in "${deprecated_git_packages[@]}"; do
        if pi list 2>/dev/null | grep -Fq "$source"; then
            echo "  - Removing deprecated Pi package $source..."
            if pi remove "$source" 2>/dev/null; then
                echo -e "    ${GREEN}✓ $source removed${NC}"
            else
                echo -e "    ${YELLOW}⚠ Failed to remove deprecated package $source${NC}"
                echo "      To remove manually, run:"
                echo "        pi remove $source"
            fi
        fi
    done
}

report_pi_vcc_upstream_status() {
    local check_script="$REPO_ROOT/scripts/check-pi-vcc-upstream.sh"
    local output
    local status

    if [ ! -f "$check_script" ]; then
        echo -e "    ${YELLOW}⚠ Upstream check script missing: ./scripts/check-pi-vcc-upstream.sh${NC}"
        return 0
    fi

    echo "  - Checking vendored pi-vcc against upstream..."
    set +e
    output="$($check_script 2>&1)"
    status=$?
    set -e

    case "$status" in
        0)
            echo -e "    ${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "    ${BLUE}ℹ vendored pi-vcc matches the reviewed upstream baseline with the intentional selective patch/skip manifest${NC}"
            printf '%s\n' "$output" | sed -n '/^local package version:/p;/^version status:/p;/^commit status:/p;/^drift status:/p' | sed 's/^/      /'
            echo "      Review details with: ./scripts/check-pi-vcc-upstream.sh --verbose"
            echo -e "    ${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            ;;
        1)
            echo -e "    ${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "    ${YELLOW}⚠ vendored pi-vcc has unexpected or stale manifest drift${NC}"
            printf '%s\n' "$output" | sed -n '/^local package version:/p;/^version status:/p;/^commit status:/p;/^drift status:/p;/^unexpected diff count:/p;/^missing expected diff count:/p;/^review details with:/p' | sed 's/^/      /'
            echo -e "    ${YELLOW}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            ;;
        2)
            if [ "${PI_VCC_SHOW_UPSTREAM_STALE:-}" = "1" ]; then
                echo -e "    ${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
                echo -e "    ${BLUE}ℹ vendored pi-vcc reviewed-upstream metadata is stale; re-review upstream before changing local uptake${NC}"
                printf '%s\n' "$output" | sed -n '/^local package version:/p;/^version status:/p;/^commit status:/p;/^drift status:/p' | sed 's/^/      /'
                echo "      Review details with: ./scripts/check-pi-vcc-upstream.sh --verbose"
                echo -e "    ${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            else
                echo "    - Upstream pi-vcc uptake intentionally deferred while stabilizing the vendored fork; set PI_VCC_SHOW_UPSTREAM_STALE=1 for details."
            fi
            ;;
        *)
            echo -e "    ${YELLOW}⚠ Unable to verify vendored pi-vcc upstream status automatically${NC}"
            printf '%s\n' "$output" | sed 's/^/      /'
            ;;
    esac

    return 0
}

resolve_pi_package_source() {
    local source="$1"
    local settings_path="$2"

    case "$source" in
        npm:*|git:*) printf '%s\n' "$source" ;;
        *) python3 - "$source" "$settings_path" <<'PY'
import os
import sys
from pathlib import Path
source, settings_path = sys.argv[1:]
path = Path(source)
if not path.is_absolute():
    path = Path(settings_path).parent / path
print(os.path.realpath(path))
PY
        ;;
    esac
}

remove_retired_pi_interactive_shell_package() {
    local pi_agent_dir="$1"
    local settings_path="$pi_agent_dir/settings.json"
    local source removal_source

    while IFS= read -r source; do
        [ -n "$source" ] || continue
        removal_source="$(resolve_pi_package_source "$source" "$settings_path")"
        echo "  - Removing retired pi-interactive-shell package $source..."
        if pi remove "$removal_source" 2>/dev/null; then
            echo -e "    ${GREEN}✓ $source removed${NC}"
        else
            echo -e "    ${YELLOW}⚠ Failed to remove retired pi-interactive-shell package $source${NC}"
            echo "      To remove manually, run:"
            echo "        pi remove $removal_source"
        fi
    done < <(
        {
            pi list 2>/dev/null | awk '/^  [^ ]/ && /pi-interactive-shell/ { sub(/^  /, ""); print }'
            python3 - "$settings_path" <<'PY'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
try:
    data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
except json.JSONDecodeError:
    data = {}
for item in data.get("packages", []) if isinstance(data.get("packages"), list) else []:
    source = item.get("source") if isinstance(item, dict) else item if isinstance(item, str) else None
    if isinstance(source, str) and "pi-interactive-shell" in source:
        print(source)
PY
        } | sort -u
    )

    python3 - "$settings_path" <<'PY'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
if not settings_path.exists():
    raise SystemExit(0)
try:
    data = json.loads(settings_path.read_text())
except json.JSONDecodeError:
    raise SystemExit(0)
if not isinstance(data, dict):
    raise SystemExit(0)
packages = data.get("packages")
if not isinstance(packages, list):
    raise SystemExit(0)
data["packages"] = [
    item for item in packages
    if "pi-interactive-shell" not in (
        item.get("source", "") if isinstance(item, dict) else item if isinstance(item, str) else ""
    )
]
settings_path.write_text(json.dumps(data, indent=2) + "\n")
PY
}

install_vendored_pi_vcc_package() {
    local source_rel="./_pi/packages/pi-vcc"
    local source_abs="$REPO_ROOT/_pi/packages/pi-vcc"
    local pi_agent_dir="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
    local settings_path="$pi_agent_dir/settings.json"
    local stable_parent="$pi_agent_dir/local-packages/ai-configs"
    local stable_source="$stable_parent/pi-vcc"
    local normalized_source

    echo ""
    echo -e "${GREEN}  Installing vendored pi-vcc via pi package manager...${NC}"

    if [ ! -d "$source_abs" ]; then
        echo -e "    ${YELLOW}⚠ Vendored pi-vcc package not found at $source_rel${NC}"
        return 1
    fi

    mkdir -p "$stable_parent" "$(dirname "$settings_path")"
    rm -rf "$stable_source"
    cp -R "$source_abs" "$stable_source"
    normalized_source="$(cd "$stable_source" && pwd)"
    echo "  - Synced vendored pi-vcc to stable package mirror ($normalized_source)"

    local existing_source
    while IFS= read -r existing_source; do
        [ -n "$existing_source" ] || continue
        if [ "$existing_source" = "$normalized_source" ]; then
            continue
        fi

        echo "  - Removing legacy pi-vcc package $existing_source..."
        if pi remove "$existing_source" 2>/dev/null; then
            echo -e "    ${GREEN}✓ removed $existing_source${NC}"
        else
            echo -e "    ${YELLOW}⚠ pi remove could not remove $existing_source; settings cleanup will purge it${NC}"
        fi
    done < <(
        {
            pi list 2>/dev/null | awk '/^  [^ ]/ && /pi-vcc/ { sub(/^  /, ""); print }'
            python3 - "$settings_path" <<'PY'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
try:
    data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
except json.JSONDecodeError:
    data = {}
for item in data.get("packages", []) if isinstance(data.get("packages"), list) else []:
    source = item.get("source") if isinstance(item, dict) else item if isinstance(item, str) else None
    if isinstance(source, str) and "pi-vcc" in source:
        print(source)
PY
        } | sort -u
    )

    python3 - "$settings_path" <<'PY'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
try:
    data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
except json.JSONDecodeError:
    data = {}
packages = data.get("packages")
if not isinstance(packages, list):
    packages = []
data["packages"] = [
    item for item in packages
    if not (
        isinstance(item, str) and "pi-vcc" in item
        or isinstance(item, dict) and isinstance(item.get("source"), str) and "pi-vcc" in item["source"]
    )
]
settings_path.write_text(json.dumps(data, indent=2) + "\n")
PY
    echo "  - Purged stale pi-vcc package registrations from $settings_path"

    echo "  - Installing vendored pi-vcc from stable mirror ($normalized_source)..."
    if pi install "$normalized_source" 2>/dev/null; then
        echo -e "    ${GREEN}✓ vendored pi-vcc installed${NC}"
    else
        echo -e "    ${YELLOW}⚠ Failed to install vendored pi-vcc via pi package manager${NC}"
        echo "      To install manually, run:"
        echo "        pi install $normalized_source"
        return 1
    fi

    python3 - "$settings_path" "$normalized_source" <<'PY'
import json
import sys
from pathlib import Path

settings_path = Path(sys.argv[1])
source = sys.argv[2]
try:
    data = json.loads(settings_path.read_text()) if settings_path.exists() else {}
except json.JSONDecodeError:
    data = {}
packages = data.get("packages")
if not isinstance(packages, list):
    packages = []
next_packages = []
for item in packages:
    item_source = item.get("source") if isinstance(item, dict) else item if isinstance(item, str) else None
    if isinstance(item_source, str) and "pi-vcc" in item_source:
        continue
    next_packages.append(item)
next_packages.append(source)
seen = set()
deduped = []
for item in next_packages:
    key = item.get("source") if isinstance(item, dict) else item if isinstance(item, str) else json.dumps(item, sort_keys=True)
    if key in seen:
        continue
    seen.add(key)
    deduped.append(item)
data["packages"] = deduped
settings_path.write_text(json.dumps(data, indent=2) + "\n")
PY
    echo "  - Pinned vendored pi-vcc to stable mirror in $settings_path"

    report_pi_vcc_upstream_status
}

install_scoped_pi_vcc_package() (
    set -eE

    local source_input="${PI_VCC_PACKAGE_SOURCE:-$REPO_ROOT/_pi/packages/pi-vcc}"
    local pi_agent_dir="${PI_CODING_AGENT_DIR:-$HOME/.pi/agent}"
    local settings_path="$pi_agent_dir/settings.json"
    local stable_parent="$pi_agent_dir/local-packages/ai-configs"
    local stable_source="$stable_parent/pi-vcc"
    local identity_helper="$REPO_ROOT/scripts/pi-vcc-package-tree.py"
    local verify_script="$REPO_ROOT/scripts/verify-pi-vcc-install.sh"
    local source_abs source_hash staged_hash
    local stage_path=""
    local backup_path=""
    local settings_snapshot=""
    local settings_existed=0
    local settings_snapshot_ready=0
    local stable_moved=0
    local candidate_installed=0
    local committed=0
    local failpoint="${PI_VCC_INSTALL_FAILPOINT:-}"

    case "$failpoint" in
        ""|copy|staged-hash|backup-move|swap|registration|post-swap-verification|remove-candidate|restore-mirror|restore-settings) ;;
        *) echo "Error: unknown PI_VCC_INSTALL_FAILPOINT: $failpoint" >&2; exit 2 ;;
    esac

    [ -d "$source_input" ] || { echo "Error: pi-vcc package source is not a directory: $source_input" >&2; exit 1; }
    [ -f "$source_input/package.json" ] || { echo "Error: pi-vcc package source is missing package.json: $source_input" >&2; exit 1; }
    [ -f "$source_input/src/core/coordinator.ts" ] || { echo "Error: pi-vcc package source is missing src/core/coordinator.ts: $source_input" >&2; exit 1; }

    source_abs="$(python3 - "$source_input" <<'PY'
import os, sys
print(os.path.realpath(os.path.expanduser(sys.argv[1])))
PY
)"
    if python3 - "$source_abs" "$stable_source" <<'PY'
import os, sys
source = os.path.realpath(os.path.expanduser(sys.argv[1]))
stable = os.path.realpath(os.path.expanduser(sys.argv[2]))
try:
    overlap = os.path.commonpath((source, stable)) in (source, stable)
except ValueError:
    overlap = False
raise SystemExit(0 if overlap else 1)
PY
    then
        echo "Error: pi-vcc package source overlaps the stable mirror: $source_abs" >&2
        exit 1
    fi
    [ ! -L "$source_input" ] || { echo "Error: pi-vcc package source must not be a symlink: $source_input" >&2; exit 1; }
    [ ! -e "$source_abs/node_modules" ] && [ ! -L "$source_abs/node_modules" ] || {
        echo "Error: pi-vcc package source node_modules must be absent: $source_abs/node_modules" >&2
        exit 1
    }
    python3 - "$pi_agent_dir" <<'PY'
import os, stat, sys
from pathlib import Path
agent = Path(os.path.abspath(os.path.expanduser(sys.argv[1])))
current = Path(agent.anchor)
targets = [current]
for part in agent.parts[1:]:
    current /= part
    targets.append(current)
targets.extend((agent / "local-packages", agent / "local-packages/ai-configs"))
for path in targets:
    try:
        mode = path.lstat().st_mode
    except FileNotFoundError:
        continue
    if stat.S_ISLNK(mode):
        raise SystemExit(f"pi-vcc managed path must not contain a symlink ancestor: {path}")
PY
    [ ! -L "$stable_source" ] || { echo "Error: pi-vcc stable mirror must not be a symlink: $stable_source" >&2; exit 1; }
    [ ! -L "$settings_path" ] || { echo "Error: pi-vcc settings path must not be a symlink: $settings_path" >&2; exit 1; }
    if [ -f "$settings_path" ]; then
        python3 - "$settings_path" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as handle:
    value = json.load(handle)
if not isinstance(value, dict):
    raise SystemExit("settings.json must contain a JSON object")
PY
    elif [ -e "$settings_path" ]; then
        echo "Error: pi-vcc settings path is not a regular file: $settings_path" >&2
        exit 1
    fi

    source_hash="$(python3 "$identity_helper" "$source_abs")"

    rollback_scoped_pi_vcc() {
        local status=$?
        local restore_failed=0
        trap - EXIT INT TERM
        set +e
        if [ "$committed" -ne 1 ]; then
            local candidate_removed=1
            if [ "$candidate_installed" -eq 1 ]; then
                if [ "$failpoint" = "remove-candidate" ]; then
                    candidate_removed=0
                    restore_failed=1
                elif ! rm -rf "$stable_source"; then
                    candidate_removed=0
                    restore_failed=1
                fi
            fi
            if [ "$stable_moved" -eq 1 ] && [ "$candidate_removed" -eq 1 ] && [ -n "$backup_path" ] && [ -e "$backup_path" ]; then
                if [ "$failpoint" = "restore-mirror" ]; then
                    restore_failed=1
                elif mv "$backup_path" "$stable_source"; then
                    backup_path=""
                else
                    restore_failed=1
                fi
            fi
            if [ "$settings_existed" -eq 1 ] && [ "$settings_snapshot_ready" -eq 1 ]; then
                if ! python3 - "$settings_snapshot" "$settings_path" "$failpoint" <<'PY'
import os, shutil, sys, tempfile
source, destination, failpoint = sys.argv[1:]
parent = os.path.dirname(destination)
fd, staged = tempfile.mkstemp(prefix=".pi-vcc-settings-restore.", dir=parent)
os.close(fd)
try:
    shutil.copy2(source, staged)
    if failpoint == "restore-settings":
        raise OSError("injected pi-vcc settings restore failure")
    os.replace(staged, destination)
except BaseException:
    try:
        os.unlink(staged)
    except FileNotFoundError:
        pass
    raise
PY
                then
                    restore_failed=1
                fi
            elif [ "$settings_existed" -eq 0 ]; then
                rm -f "$settings_path" || restore_failed=1
            fi
        fi
        [ -z "$stage_path" ] || rm -rf "$stage_path" || restore_failed=1
        if [ "$restore_failed" -eq 0 ]; then
            [ -z "$backup_path" ] || rm -rf "$backup_path" || restore_failed=1
            [ -z "$settings_snapshot" ] || rm -f "$settings_snapshot" || restore_failed=1
        fi
        if [ "$restore_failed" -ne 0 ]; then
            echo "Error: pi-vcc automatic rollback encountered an error; recovery evidence retained at backup=${backup_path:-none} settings=${settings_snapshot:-none}" >&2
            status=1
        fi
        exit "$status"
    }
    trap rollback_scoped_pi_vcc EXIT
    trap 'exit 130' INT
    trap 'exit 143' TERM

    mkdir -p "$stable_parent" "$(dirname "$settings_path")"
    stage_path="$(mktemp -d "$stable_parent/.pi-vcc-stage.XXXXXX")"
    settings_snapshot="$(mktemp "$stable_parent/.pi-vcc-settings.XXXXXX")"
    if [ -f "$settings_path" ]; then
        settings_existed=1
        cp -p "$settings_path" "$settings_snapshot"
        settings_snapshot_ready=1
    fi

    [ "$failpoint" != "copy" ] || { echo "Injected pi-vcc install failure: copy" >&2; exit 1; }
    python3 - "$source_abs" "$stage_path" <<'PY'
import shutil, sys
shutil.copytree(sys.argv[1], sys.argv[2], dirs_exist_ok=True, symlinks=True, copy_function=shutil.copy2)
PY
    staged_hash="$(python3 "$identity_helper" "$stage_path")"
    [ "$failpoint" != "staged-hash" ] || { echo "Injected pi-vcc install failure: staged-hash" >&2; exit 1; }
    [ "$source_hash" = "$staged_hash" ] || { echo "Error: staged pi-vcc package identity differs from source" >&2; exit 1; }

    if [ -e "$stable_source" ]; then
        backup_path="$(mktemp -d "$stable_parent/.pi-vcc-backup.XXXXXX")"
        rmdir "$backup_path"
        [ "$failpoint" != "backup-move" ] || { echo "Injected pi-vcc install failure: backup-move" >&2; exit 1; }
        mv "$stable_source" "$backup_path"
        stable_moved=1
    fi
    [ "$failpoint" != "swap" ] || { echo "Injected pi-vcc install failure: swap" >&2; exit 1; }
    mv "$stage_path" "$stable_source"
    stage_path=""
    candidate_installed=1

    python3 - "$settings_path" "$stable_source" "$REPO_ROOT/scripts" <<'PY'
import json, os, stat, sys, tempfile
from pathlib import Path
sys.path.insert(0, sys.argv[3])
from pi_vcc_registration import (
    PiGitUrlParserUnavailable,
    is_pi_vcc_source,
    package_source,
    require_pi_package_root,
)
settings = Path(sys.argv[1])
source = sys.argv[2]
stable = Path(source)
data = json.loads(settings.read_text()) if settings.exists() else {}
packages = data.get("packages")
if not isinstance(packages, list):
    packages = []
try:
    # Fail closed before rewriting settings if the Pi parser cannot be loaded.
    require_pi_package_root()
    data["packages"] = [
        item for item in packages if not is_pi_vcc_source(package_source(item), stable)
    ] + [source]
except PiGitUrlParserUnavailable as exc:
    raise SystemExit(f"Error: pi-vcc registration classification unavailable: {exc}") from exc
mode = stat.S_IMODE(settings.stat().st_mode) if settings.exists() else 0o644
settings.parent.mkdir(parents=True, exist_ok=True)
with tempfile.NamedTemporaryFile("w", dir=settings.parent, delete=False, encoding="utf-8") as handle:
    json.dump(data, handle, indent=2)
    handle.write("\n")
    temporary = handle.name
os.chmod(temporary, mode)
os.replace(temporary, settings)
PY
    [ "$failpoint" != "registration" ] || { echo "Injected pi-vcc install failure: registration" >&2; exit 1; }
    case "$failpoint" in
        post-swap-verification|remove-candidate|restore-mirror|restore-settings)
            echo "Injected pi-vcc install failure: $failpoint" >&2
            exit 1
            ;;
    esac

    PI_CODING_AGENT_DIR="$pi_agent_dir" bash "$verify_script" --expected-package "$source_abs" >/dev/null

    committed=1
    trap - EXIT INT TERM
    [ -z "$backup_path" ] || rm -rf "$backup_path"
    rm -f "$settings_snapshot"
    echo "pi-vcc scoped install: PASS source=$source_abs stable=$stable_source hash=$source_hash"
)

# Install npm-based pi extensions
install_pi_npm_packages() {
    echo ""
    echo -e "${GREEN}  Installing npm-based pi extensions...${NC}"

    # Core extensions for the user's workflow
    local npm_packages=(
        "@tintinweb/pi-subagents"
        "@tintinweb/pi-tasks"
        "@aliou/pi-processes"
        "@narumitw/pi-goal"
        "pi-web-access"
        "@fnnm/pi-ast-grep"
        "pi-updater"
        "pi-powerline-footer"
        "pi-no-soft-cursor"
        "@tmustier/pi-files-widget"
        "@tmustier/pi-raw-paste"
        "@pi-kaush/pi-inline-skill-identifier"
        "@howaboua/pi-vent"
        "@howaboua/pi-explore-subagents"
        "pi-service-tier"
    )
    local deprecated_npm_packages=(
        "@howaboua/pi-codex-conversion"
        "pi-subagents"
        "pi-mcp-adapter"
        "@sting8k/pi-vcc"
        "lsp-pi"
        "pi-multi-pass"
        "pi-side-agents"
        "@howaboua/pi-dynamic-tools"
        "@ff-labs/pi-fff"
    )
    local deprecated_git_packages=(
        "git:github.com/adnichols/pi-codex-conversion"
    )

    # Check if npm is available
    if ! command -v npm &> /dev/null; then
        echo -e "    ${YELLOW}⚠ npm not found in PATH${NC}"
        echo "      Please install Node.js/npm to install pi extensions"
        return 1
    fi

    # Remove deprecated packages from Pi settings before installing replacements.
    for pkg in "${deprecated_npm_packages[@]}"; do
        local source="npm:$pkg"
        if pi list 2>/dev/null | grep -Fq "$source"; then
            echo "  - Removing deprecated Pi package $pkg..."
            if pi remove "$source" 2>/dev/null; then
                echo -e "    ${GREEN}✓ $pkg removed${NC}"
            else
                echo -e "    ${YELLOW}⚠ Failed to remove deprecated package $pkg${NC}"
                echo "      To remove manually, run:"
                echo "        pi remove $source"
            fi
        fi
    done
    for source in "${deprecated_git_packages[@]}"; do
        if pi list 2>/dev/null | grep -Fq "$source"; then
            echo "  - Removing deprecated Pi package $source..."
            if pi remove "$source" 2>/dev/null; then
                echo -e "    ${GREEN}✓ $source removed${NC}"
            else
                echo -e "    ${YELLOW}⚠ Failed to remove deprecated package $source${NC}"
                echo "      To remove manually, run:"
                echo "        pi remove $source"
            fi
        fi
    done

    # Install/update each package through Pi so it is registered in settings
    for pkg in "${npm_packages[@]}"; do
        local source="npm:$pkg"
        echo "  - Checking $pkg..."
        if pi list 2>/dev/null | grep -Fq "$source"; then
            echo "    - $pkg already registered with Pi, updating..."
            pi update "$source" 2>/dev/null || echo -e "    ${YELLOW}⚠ Update check skipped (pi update may require manual run)${NC}"
        else
            echo "    Installing $pkg via pi package manager..."
            if pi install "$source" 2>/dev/null; then
                echo -e "    ${GREEN}✓ $pkg installed${NC}"
            else
                echo -e "    ${YELLOW}⚠ Failed to install $pkg via pi package manager${NC}"
                echo "      To install manually, run:"
                echo "        pi install $source"
            fi
        fi
    done

    echo -e "${GREEN}  ✓ npm-based extensions processed${NC}"

    # CLIProxyAPI exposes Codex GPT models through Pi's standard
    # openai-responses adapter, while pi-service-tier's upstream provider check
    # only recognizes openai-codex-responses. Keep the installed package
    # compatible with the repo-managed local CLIProxyAPI provider.
    if ! python3 "$REPO_ROOT/scripts/patch_pi_service_tier.py"; then
        echo -e "${YELLOW}⚠ Failed to apply pi-service-tier CLIProxyAPI compatibility patch${NC}"
    fi
}

# Argument parsing. The scoped pi-vcc mode intentionally accepts no other
# installer options or target directory so it cannot fan out into unrelated work.
if [ "${1:-}" = "--pi-vcc" ]; then
    INSTALL_MODE="--pi-vcc"
    shift
    if [ "$#" -gt 1 ]; then
        echo -e "${RED}Error: --pi-vcc accepts at most one package-source path${NC}" >&2
        exit 1
    fi
    if [ "$#" -eq 1 ]; then
        [[ "$1" != -* ]] || { echo -e "${RED}Error: unknown scoped pi-vcc option $1${NC}" >&2; exit 1; }
        PI_VCC_PACKAGE_SOURCE="$1"
        shift
    fi
else
    while [ "$#" -gt 0 ]; do
        case "$1" in
            --claude|--codex|--pi|--pi-review-stack|--tools|--skills|--all|--default)
                INSTALL_MODE="$1"
                shift
                ;;
            --update)
                UPDATE_SKILLS=true
                shift
                ;;
            --help|-h)
                print_usage
                exit 0
                ;;
            *)
                if [[ "$1" == -* ]]; then
                    echo -e "${RED}Error: Unknown option $1${NC}"
                    echo ""
                    print_usage
                    exit 1
                fi
                TARGET_DIR="$1"
                shift
                ;;
        esac
    done
fi

# The review-stack transaction treats the complete ~/.pi tree as one snapshot
# boundary. Following a symlink here would mutate storage outside that boundary.
if [ "$INSTALL_MODE" = "--pi-review-stack" ] && [ -L "$HOME/.pi" ]; then
    echo "Error: --pi-review-stack requires ~/.pi to be a real directory, not a symlink, so the complete snapshot boundary is truthful. Replace the symlink with a real directory before installing." >&2
    exit 1
fi

# Preserve ambiguous retired runtime trees, but remove positively identified
# managed deprecated skills before installing any maintained surface.
if [ "$INSTALL_MODE" != "--pi-review-stack" ] && [ "$INSTALL_MODE" != "--pi-vcc" ]; then
    cleanup_retired_runtime_surfaces "$TARGET_DIR"
    cleanup_deprecated_shared_skills
fi

# Main installation logic
case "$INSTALL_MODE" in
    --default)
        install_claude "$TARGET_DIR"
        echo ""
        install_codex "$TARGET_DIR"
        echo ""
        install_pi
        echo ""
        sync_shared_skills claude
        echo ""
        enforce_central_project_skills "$TARGET_DIR"
        ;;
    --claude)
        install_claude "$TARGET_DIR"
        echo ""
        sync_shared_skills claude
        echo ""
        enforce_central_project_skills "$TARGET_DIR"
        ;;
    --codex)
        install_codex "$TARGET_DIR"
        echo ""
        sync_shared_skills
        enforce_central_project_skills "$TARGET_DIR"
        ;;
    --pi)
        install_pi
        echo ""
        sync_shared_skills
        echo ""
        enforce_central_project_skills "$TARGET_DIR"
        ;;
    --pi-vcc)
        install_scoped_pi_vcc_package
        exit 0
        ;;
    --pi-review-stack)
        install_pi_review_stack
        ;;
    --tools)
        install_tools
        ;;
    --skills)
        install_skills
        ;;
    --all)
        install_claude "$TARGET_DIR"
        echo ""
        install_codex "$TARGET_DIR"
        echo ""
        install_pi
        echo ""
        install_tools
        echo ""
        sync_shared_skills claude
        echo ""
        enforce_central_project_skills "$TARGET_DIR"
        ;;
    *)
        echo -e "${RED}Error: Unknown option $INSTALL_MODE${NC}"
        echo ""
        print_usage
        exit 1
        ;;
esac

if [ "$UPDATE_SKILLS" = true ] && [ "$SHARED_SKILLS_SYNCED" != true ]; then
    echo ""
    sync_shared_skills
fi

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Review and customize settings as needed"
echo "  2. Run this script again to sync future updates (it auto-detects existing installations)"
