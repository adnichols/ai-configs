#!/bin/bash

# Installation script for Claude Code, Codex, Gemini, and optional OpenCode
# Usage: ./install.sh [--claude|--codex|--gemini|--opencode|--tools|--skills|--all] [--append-agents] [target-directory]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$SCRIPT_DIR"
TARGET_DIR="."
INSTALL_MODE="--default"
APPEND_AGENTS=false
INSTALL_TOOLS=false
INSTALL_SKILLS=false

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

print_usage() {
    echo "Usage: $0 [--claude|--codex|--gemini|--opencode|--tools|--skills|--all] [--append-agents] [target-directory]"
    echo ""
    echo "Options:"
    echo "  --claude    Install Claude Code configuration only"
    echo "  --codex     Install Codex configuration only"
    echo "  --gemini    Install Gemini CLI configuration only"
    echo "  --opencode  Install OpenCode configuration only"
    echo "  --tools     Install CLI tools only (e.g., ltui)"
    echo "  --skills    Install Claude skills only (to ~/.claude/skills/)"
    echo "  --all       Install everything: Claude, Codex, Gemini, OpenCode, tools, and skills"
    echo "  --append-agents"
    echo "             Ensure GEMINI.md exists and contains required Personas."
    echo "             If GEMINI.md exists but is missing the Personas section, append it from the template."
    echo ""
    echo "Default behavior (no args):"
    echo "  Installs Claude, Codex, and Gemini only (no OpenCode, no tools, no global skills)."
    echo ""
    echo "Notes:"
    echo "  - OpenCode does NOT auto-install opencode.json (copy config-template.json manually if needed)"
    echo "  - When using --opencode or --all, commands, prompts, and skills are installed to ~/.config/opencode"
    echo "  - In non-interactive mode, existing configs are preserved automatically"
    echo ""
    echo "Examples:"
    echo "  $0                               # Default: install Claude + Codex + Gemini"
    echo "  $0 --claude                      # Install Claude to current directory"
    echo "  $0 --codex ~/my-project          # Install Codex to ~/my-project"
    echo "  $0 --gemini ~/my-project         # Install Gemini to ~/my-project"
    echo "  $0 --opencode ~/my-project       # Install OpenCode to ~/my-project"
    echo "  $0 --tools                       # Install CLI tools globally"
    echo "  $0 --skills                      # Install Claude skills globally"
    echo "  $0 --all --append-agents         # Install everything and ensure GEMINI.md Personas"
}

ensure_codex_cli_flags() {
    local target_dir="$1"
    local config_path="$target_dir/config.toml"

    if [ ! -f "$config_path" ]; then
        return
    fi

    local status
    status=$(CONFIG_PATH="$config_path" python3 <<'PY'
import ast
import os
import re
from pathlib import Path

config_file = Path(os.environ["CONFIG_PATH"])
text = config_file.read_text()
required_flags = [
    "--dangerously-bypass-approvals-and-sandbox",
    "--enable-web-search",
]

pattern = re.compile(r"default_cli_flags\s*=\s*\[(.*?)\]", re.DOTALL)
match = pattern.search(text)
changed = False


def format_block(flags):
    inner = ",\n".join(f'  "{flag}"' for flag in flags)
    return f"default_cli_flags = [\n{inner}\n]"


if match:
    content = match.group(1)
    try:
        existing = ast.literal_eval("[" + content + "]")
    except Exception:
        existing = []

    updated = existing[:]
    for flag in required_flags:
        if flag not in updated:
            updated.append(flag)

    if updated != existing:
        block = format_block(updated)
        text = text[:match.start()] + block + text[match.end():]
        changed = True
else:
    cli_header = re.compile(r"^\[cli\]\s*$", re.MULTILINE)
    cli_match = cli_header.search(text)
    block = format_block(required_flags)
    insertion = block + "\n"

    if cli_match:
        block_start = cli_match.end()
        next_table = re.search(r"^\[.*?\]", text[block_start:], re.MULTILINE)
        insert_pos = len(text) if not next_table else block_start + next_table.start()

        if block_start < len(text) and text[block_start] != "\n":
            text = text[:block_start] + "\n" + text[block_start:]
            insert_pos += 1

        prefix = text[:insert_pos]
        suffix = text[insert_pos:]
        if prefix and not prefix.endswith("\n"):
            prefix += "\n"
        text = prefix + insertion + suffix
    else:
        if text and not text.endswith("\n"):
            text += "\n"
        text = text.rstrip() + "\n\n[cli]\n" + block + "\n"

    changed = True

if changed:
    config_file.write_text(text if text.endswith("\n") else text + "\n")
    print("updated")
else:
    print("unchanged")
PY
)
    local cli_update_status=$?

    if [ $cli_update_status -ne 0 ]; then
        echo "  - Unable to ensure Codex CLI flags (manual config update required)"
        return
    fi

    case "$status" in
        updated)
            echo "  - Ensured Codex CLI runs with --dangerously-bypass-approvals-and-sandbox and web search"
            ;;
        unchanged)
            echo "  - Codex CLI flags already configured for dangerous bypass and web search"
            ;;
        *)
            echo "  - Unable to validate Codex CLI flags (manual config update required)"
            ;;
    esac
}

ensure_gemini_personas() {
    # Ensure GEMINI.md has the required Personas section
    local project_root="$1"
    local template_path="$REPO_ROOT/gemini/GEMINI.template.md"
    local gemini_path="$project_root/GEMINI.md"
    local gemini_created=false

    # Do not touch the config repo's own files via this path
    if [ "$project_root" = "$REPO_ROOT" ]; then
        return
    fi

    if [ ! -f "$template_path" ]; then
        return
    fi

    if [ ! -f "$gemini_path" ]; then
        echo "  - No GEMINI.md found; installing from template..."
        cp "$template_path" "$gemini_path"
        gemini_created=true
    fi

    if grep -q "Available Personas" "$gemini_path"; then
        return
    fi

    echo "  - Existing GEMINI.md found without 'Available Personas' section."
    echo "    (These Personas are REQUIRED for Gemini commands to function)"

    local should_append=false

    if [ "$APPEND_AGENTS" = true ]; then
        should_append=true
    elif [ -t 0 ]; then
        printf "  - Append missing Personas to GEMINI.md now? [Y/n] "
        read -r reply
        case "$reply" in
            ""|"Y"|"y")
                should_append=true
                ;;
            *)
                echo "  - Skipping append. WARNING: Commands may fail without defined Personas."
                ;;
        esac
    else
        echo "  - Skipping automatic append (non-interactive; run with --append-agents or edit manually)."
    fi

    if [ "$should_append" = true ]; then
        echo "  - Appending Personas from template..."
        # Extract everything from "## Available Personas" to the end
        awk 'BEGIN{flag=0} /^## Available Personas/{flag=1} flag {print}' "$template_path" >> "$gemini_path"
    fi
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

    if [ -d "$REPO_ROOT/codex/prompts/_lib" ]; then
        cp -R "$REPO_ROOT/codex/prompts/_lib" "$destination/"
    fi

    for prompt in "$REPO_ROOT"/codex/prompts/*.md; do
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

    # Update agents (remove first to ensure clean state)
    echo "  - Installing agents..."
    if [ -d "$target/agents" ]; then
        rm -rf "$target/agents"
    fi
    cp -r "$REPO_ROOT/claude/agents" "$target/"

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
    cp -r "$REPO_ROOT/claude/commands" "$target/"

    # Update scripts (remove first to ensure clean state)
    echo "  - Installing scripts..."
    if [ -d "$target/scripts" ]; then
        rm -rf "$target/scripts"
    fi
    cp -r "$REPO_ROOT/claude/scripts" "$target/"

    # Handle settings.local.json (preserve if exists)
    if [ -f "$target/settings.local.json" ]; then
        echo -e "  ${YELLOW}✓ Preserved existing settings.local.json${NC}"
    else
        echo "  - Installing settings.local.json..."
        cp "$REPO_ROOT/claude/settings.local.json" "$target/"
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

    # Install ltui
    if [ -d "$REPO_ROOT/tools/ltui" ]; then
        echo "Installing ltui..."

        # Check for Bun
        if ! command -v bun &> /dev/null; then
            echo -e "${RED}Error: Bun is required to build ltui${NC}"
            echo "Install from: https://bun.sh"
            return 1
        fi

        local current_dir=$(pwd)
        cd "$REPO_ROOT/tools/ltui"

        echo "  - Installing dependencies..."
        bun install

        echo "  - Building ltui..."
        bun run build

        echo "  - Linking ltui globally..."
        bun link

        cd "$current_dir"
        echo -e "${GREEN}✓ ltui installed successfully${NC}"
        echo ""

        # Check if ~/.bun/bin is in PATH
        if [[ ":$PATH:" != *":$HOME/.bun/bin:"* ]]; then
            echo -e "${YELLOW}⚠  NOTE: ~/.bun/bin is not in your PATH${NC}"
            echo "  Add this to your shell profile (~/.bashrc, ~/.zshrc, etc.):"
            echo "    export PATH=\"\$HOME/.bun/bin:\$PATH\""
            echo ""
            echo "  After updating, run: source ~/.zshrc  (or restart your shell)"
            echo "  Then verify with: ltui --help"
        else
            echo "  ltui is now available globally. Try: ltui --help"
        fi
    else
        echo -e "${YELLOW}No tools directory found, skipping...${NC}"
    fi
}

install_skills() {
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  Installing Claude Skills${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
    echo ""

    local skills_dir="$HOME/.claude/skills"
    mkdir -p "$skills_dir"

    if [ -d "$REPO_ROOT/skills" ]; then
        echo "  - Installing skills to ~/.claude/skills/..."

        # Copy each skill directory
        for skill_path in "$REPO_ROOT/skills/"*/; do
            if [ -d "$skill_path" ]; then
                local skill_name=$(basename "$skill_path")
                echo "    - Installing skill: $skill_name"
                # Remove trailing slash to copy the directory itself, not just its contents
                cp -r "${skill_path%/}" "$skills_dir/"
            fi
        done

        echo -e "${GREEN}✓ Skills installed successfully${NC}"
        echo ""
        echo "  Skills are now available in Claude Code"
    else
        echo -e "${YELLOW}No skills directory found, skipping...${NC}"
    fi
}

install_codex() {
    local target="$1/.codex"
    local is_update=false

    # Detect if this is an update
    if [ -d "$target" ]; then
        is_update=true
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  Updating Codex Configuration${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${GREEN}Updating Codex configuration at $target${NC}"
    else
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  Installing Codex Configuration${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${GREEN}Installing Codex configuration to $target${NC}"
        mkdir -p "$target"
    fi

    local project_prompts_dir="${target}/prompts"
    if [ -d "$project_prompts_dir" ]; then
        echo "  - Removing project prompts (Codex prefers ~/.codex/prompts)..."
        rm -rf "$project_prompts_dir"
    fi

    local project_scripts_dir="${target}/scripts"
    if [ -d "$project_scripts_dir" ]; then
        echo "  - Removing project scripts (Codex prefers ~/.codex/scripts)..."
        rm -rf "$project_scripts_dir"
    fi

    local global_codex_dir="$HOME/.codex"
    mkdir -p "$global_codex_dir"
    local global_prompts_dir="${global_codex_dir}/prompts"
    sync_codex_prompts "$global_prompts_dir" "global (~/.codex/prompts)" "replace"

    echo "  - Syncing Codex scripts globally..."
    rm -rf "$global_codex_dir/scripts"
    cp -r "$REPO_ROOT/codex/scripts" "$global_codex_dir/"

    # Merge config.toml if it exists
    if [ -f "$target/config.toml" ]; then
        echo -e "  ${YELLOW}- config.toml already exists${NC}"
        echo "  - Review $REPO_ROOT/codex/config.toml for settings to merge"
    else
        echo "  - Installing config.toml..."
        cp "$REPO_ROOT/codex/config.toml" "$target/"
    fi

    ensure_codex_cli_flags "$target"

    # Copy MCP servers configuration
    echo "  - Installing mcp-servers.toml..."
    cp "$REPO_ROOT/codex/mcp-servers.toml" "$target/"

    if [ "$is_update" = true ]; then
        echo -e "${GREEN}✓ Codex update complete${NC}"
    else
        echo -e "${GREEN}✓ Codex installation complete${NC}"
    fi
    echo ""
    if [ "$is_update" = false ]; then
        echo "To add MCP servers to Codex, merge mcp-servers.toml into ~/.codex/config.toml"
    fi
}


install_opencode_refs() {
    local target_root="$1"
    local target="$target_root/.opencode"
    
    # Ensure .opencode exists
    mkdir -p "$target"

    # Install reference commands (remove first to ensure clean state)
    if [ -d "$target/_ref_commands" ]; then
        rm -rf "$target/_ref_commands"
    fi
    mkdir -p "$target/_ref_commands"
    
    echo "  - Installing OpenCode reference commands to .opencode/_ref_commands..."
    
    # Prefer command (singular) as it matches source
    if [ -d "$REPO_ROOT/opencode/command" ]; then
        cp -r "$REPO_ROOT/opencode/command/"* "$target/_ref_commands/"
    elif [ -d "$REPO_ROOT/opencode/commands" ]; then
        cp -r "$REPO_ROOT/opencode/commands/"* "$target/_ref_commands/"
    fi

    # Create README in _ref_commands
    cat > "$target/_ref_commands/README.md" << "EOF"
# Reference Commands

These commands are provided for reference only and are not intended to be used directly from this directory.
The authoritative commands are installed and loaded from `~/.config/opencode/command/`.

These files are here so you can reference them in prompts if needed (e.g. "follow the pattern in .opencode/_ref_commands/cmd:graduate.md").
EOF
}


install_opencode() {
    local target_root="$1"
    local target="$target_root/.opencode"
    local is_update=false
    local opencode_config_dir="$HOME/.config/opencode"

    # Detect if this is an update
    if [ -d "$target" ]; then
        is_update=true
        echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  Updating OpenCode Configuration${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${GREEN}Updating OpenCode configuration at $target${NC}"
    else
        echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  Installing OpenCode Configuration${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${GREEN}Installing OpenCode configuration to $target${NC}"
        mkdir -p "$target"
    fi

    # Ensure reference commands are installed (User requested this always happens)
    install_opencode_refs "$target_root"

    # Remove legacy project-local commands directory (commands are now global)
    if [ -d "$target/commands" ]; then
        rm -rf "$target/commands"
    fi

    # Create OpenCode config directory structure
    echo "  - Creating OpenCode config directory structure..."
    mkdir -p "$opencode_config_dir"
    mkdir -p "$opencode_config_dir/prompts"
    mkdir -p "$opencode_config_dir/skill/playwright-skill/lib"
    mkdir -p "$opencode_config_dir/plugin"
    mkdir -p "$opencode_config_dir/command"

    # Install prompts
    echo "  - Installing OpenCode prompts..."
    if [ -d "$opencode_config_dir/prompts" ] && [ "$(ls -A "$opencode_config_dir/prompts" 2>/dev/null)" ]; then
        if ask_overwrite_permission "$opencode_config_dir/prompts" "OpenCode prompts directory"; then
            rm -rf "$opencode_config_dir/prompts"
        else
            echo "  - Preserved existing prompts directory"
        fi
    fi
    mkdir -p "$opencode_config_dir/prompts"
    cp "$REPO_ROOT/opencode/prompts/glm-reasoning.md" "$opencode_config_dir/prompts/" 2>/dev/null || true

    # Install skills
    echo "  - Installing OpenCode skills..."
    if [ -d "$opencode_config_dir/skill/playwright-skill" ]; then
        if ask_overwrite_permission "$opencode_config_dir/skill/playwright-skill" "OpenCode playwright-skill directory"; then
            rm -rf "$opencode_config_dir/skill/playwright-skill"
        else
            echo "  - Preserved existing playwright-skill directory"
        fi
    fi
    mkdir -p "$opencode_config_dir/skill/playwright-skill"
    if [ -d "$REPO_ROOT/opencode/skill/playwright-skill" ]; then
        cp -r "$REPO_ROOT/opencode/skill/playwright-skill"/* "$opencode_config_dir/skill/playwright-skill/"
    fi

    # Install commands (authoritative global location)
    echo "  - Installing OpenCode commands to ~/.config/opencode/command..."
    if [ -d "$opencode_config_dir/command" ] && [ "$(ls -A "$opencode_config_dir/command" 2>/dev/null)" ]; then
        if ask_overwrite_permission "$opencode_config_dir/command" "OpenCode commands directory"; then
            rm -rf "$opencode_config_dir/command"
        else
            echo "  - Preserved existing commands directory"
        fi
    fi
    mkdir -p "$opencode_config_dir/command"
    if [ -d "$REPO_ROOT/opencode/command" ]; then
        cp -r "$REPO_ROOT/opencode/command/"* "$opencode_config_dir/command/"
    elif [ -d "$REPO_ROOT/opencode/commands" ]; then
        cp -r "$REPO_ROOT/opencode/commands/"* "$opencode_config_dir/command/"
    fi

    # Install agents (remove first to ensure clean state)
    echo "  - Installing agents..."
    if [ -d "$target/agents" ]; then
        rm -rf "$target/agents"
    fi
    mkdir -p "$target/agents"
    if [ -d "$REPO_ROOT/opencode/agent" ]; then
        cp -r "$REPO_ROOT/opencode/agent/"* "$target/agents/"
    elif [ -d "$REPO_ROOT/opencode/agents" ]; then
        cp -r "$REPO_ROOT/opencode/agents/"* "$target/agents/"
    fi

    # Install documentation to target root
    echo "  - Installing documentation..."
    cp "$REPO_ROOT/opencode/OPENCODE_ONBOARDING.md" "$target_root/"

    if [ "$is_update" = true ]; then
        echo -e "${GREEN}✓ OpenCode update complete${NC}"
    else
        echo -e "${GREEN}✓ OpenCode installation complete${NC}"
    fi
    echo ""
    echo "Note: OpenCode configuration file opencode.json is not auto-installed"
    echo "      Copy opencode/config-template.json to your repo root and customize as needed"
    echo "      Commands, prompts, and skills installed to $HOME/.config/opencode"
    echo "      Documentation installed to $target_root/OPENCODE_ONBOARDING.md"
}

install_gemini() {
    local target_root="$1"
    local target="$target_root/.gemini"
    local is_update=false

    # Ensure GEMINI.md has the required Personas
    ensure_gemini_personas "$target_root"

    # Detect if this is an update
    if [ -d "$target" ]; then
        is_update=true
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  Updating Gemini CLI Configuration${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${GREEN}Updating Gemini configuration at $target${NC}"
    else
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo -e "${GREEN}  Installing Gemini CLI Configuration${NC}"
        echo -e "${GREEN}═══════════════════════════════════════════════════════${NC}"
        echo ""
        echo -e "${GREEN}Installing Gemini configuration to $target${NC}"
        mkdir -p "$target"
    fi

    # Install commands
    echo "  - Installing commands..."
    if [ -d "$target/commands" ]; then
        rm -rf "$target/commands"
    fi
    mkdir -p "$target/commands"
    cp -r "$REPO_ROOT/gemini/commands/"* "$target/commands/"

    # Setup thoughts directory structure
    if [ "$target_root" != "$HOME" ]; then
        setup_thoughts_structure "$target_root"
        create_permanent_docs "$target_root"
    fi

    if [ "$is_update" = true ]; then
        echo -e "${GREEN}✓ Gemini update complete${NC}"
    else
        echo -e "${GREEN}✓ Gemini installation complete${NC}"
    fi
    echo ""
    if [ "$APPEND_AGENTS" = true ]; then
        echo "Note: GEMINI.md was created or updated with required Personas."
    else
        echo "Note: To ensure GEMINI.md has all required Personas, re-run with --append-agents."
    fi
}

# Argument parsing
while [ "$#" -gt 0 ]; do
    case "$1" in
        --claude|--codex|--gemini|--opencode|--tools|--skills|--all|--default)
            INSTALL_MODE="$1"
            shift
            ;;
        --append-agents)
            APPEND_AGENTS=true
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

# Main installation logic
case "$INSTALL_MODE" in
    --default)
        install_claude "$TARGET_DIR"
        echo ""
        install_codex "$TARGET_DIR"
        echo ""
        install_gemini "$TARGET_DIR"
        echo ""
        install_opencode_refs "$TARGET_DIR"
        ;;
    --claude)
        install_claude "$TARGET_DIR"
        ;;
    --codex)
        install_codex "$TARGET_DIR"
        ;;
    --gemini)
        install_gemini "$TARGET_DIR"
        ;;
    --opencode)
        install_opencode "$TARGET_DIR"
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
        install_gemini "$TARGET_DIR"
        echo ""
        install_opencode "$TARGET_DIR"
        echo ""
        install_tools
        echo ""
        install_skills
        ;;
    *)
        echo -e "${RED}Error: Unknown option $INSTALL_MODE${NC}"
        echo ""
        print_usage
        exit 1
        ;;
esac

echo ""
echo -e "${GREEN}Installation complete!${NC}"
echo ""
echo "Next steps:"
echo "  1. Review and customize settings as needed"
echo "  2. Run this script again to sync future updates (it auto-detects existing installations)"
