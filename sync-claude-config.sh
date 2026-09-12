#!/bin/bash

# sync-claude-config.sh
# Selectively sync Claude Code configurations from ~/.claude to local repository

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default options
DRY_RUN=false
FORCE_SETTINGS=false
VERBOSE=false

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

# Function to show usage
show_help() {
    cat << EOF
sync-claude-config.sh - Selective Claude Code Configuration Sync

USAGE:
    ./sync-claude-config.sh [OPTIONS]

DESCRIPTION:
    Syncs commands/ from ~/.claude to the current repository's .claude directory,
    plus agents/ when it exists. Also copies settings.template.json to
    settings.local.json.

OPTIONS:
    --dry-run           Preview changes without applying them
    --force-settings    Overwrite existing settings.local.json
    --verbose          Show detailed rsync output
    --help             Show this help message

EXAMPLES:
    ./sync-claude-config.sh                    # Normal sync
    ./sync-claude-config.sh --dry-run          # Preview changes
    ./sync-claude-config.sh --force-settings   # Overwrite settings file

NOTES:
    - Follows symlinks in ~/.claude (uses rsync -L)
    - Creates .claude directory if it doesn't exist
    - Won't overwrite settings.local.json unless --force-settings is used
    - Can be run from any repository root directory

EOF
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force-settings)
            FORCE_SETTINGS=true
            shift
            ;;
        --verbose)
            VERBOSE=true
            shift
            ;;
        --help|-h)
            show_help
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Check prerequisites
check_prerequisites() {
    print_info "Checking prerequisites..."

    # Check if ~/.claude exists
    if [[ ! -d "$HOME/.claude" ]]; then
        print_error "~/.claude directory not found"
        exit 1
    fi

    # Check if required source directories exist. The repo no longer ships a
    # managed Claude agents tree, so agents/ is optional.
    local missing_dirs=()
    if [[ ! -d "$HOME/.claude/commands" ]]; then
        missing_dirs+=("commands")
    fi

    if [[ ${#missing_dirs[@]} -gt 0 ]]; then
        print_error "Missing required directories in ~/.claude: ${missing_dirs[*]}"
        exit 1
    fi

    # Check if settings template exists
    if [[ ! -f "$HOME/.claude/settings.template.json" ]]; then
        print_warning "settings.template.json not found in ~/.claude"
    fi

    print_success "Prerequisites check passed"
}

# Create target directory structure
create_target_structure() {
    print_info "Creating .claude directory structure..."

    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "[DRY RUN] Would create .claude directory if needed"
    else
        mkdir -p .claude
        print_success "Created .claude directory"
    fi
}

# Sync a directory with rsync
sync_directory() {
    local src_dir="$1"
    local dest_dir="$2"
    local dir_name="$3"

    print_info "Syncing $dir_name directory..."

    # Build rsync options
    local rsync_opts=(-avL --delete)
    if [[ "$DRY_RUN" == "true" ]]; then
        rsync_opts+=(--dry-run)
    fi
    if [[ "$VERBOSE" == "false" ]]; then
        rsync_opts+=(--quiet)
    fi

    # Run rsync
    if rsync "${rsync_opts[@]}" "$src_dir/" "$dest_dir/"; then
        if [[ "$DRY_RUN" == "true" ]]; then
            print_success "[DRY RUN] Would sync $dir_name directory"
        else
            print_success "Synced $dir_name directory"
        fi
    else
        print_error "Failed to sync $dir_name directory"
        return 1
    fi
}

# Handle settings file
handle_settings() {
    local src_file="$HOME/.claude/settings.template.json"
    local dest_file=".claude/settings.local.json"

    # Check if source exists
    if [[ ! -f "$src_file" ]]; then
        print_warning "Skipping settings - template file not found"
        return 0
    fi

    print_info "Handling settings file..."

    # Check if destination exists and handle accordingly
    if [[ -f "$dest_file" ]] && [[ "$FORCE_SETTINGS" == "false" ]]; then
        print_info "settings.local.json already exists (use --force-settings to overwrite)"
    else
        if [[ "$DRY_RUN" == "true" ]]; then
            if [[ -f "$dest_file" ]]; then
                print_info "[DRY RUN] Would overwrite existing settings.local.json"
            else
                print_info "[DRY RUN] Would create settings.local.json"
            fi
        else
            if cp "$src_file" "$dest_file"; then
                if [[ -f "$dest_file" ]] && [[ "$FORCE_SETTINGS" == "true" ]]; then
                    print_success "Overwrote settings.local.json"
                else
                    print_success "Created settings.local.json"
                fi
            else
                print_error "Failed to copy settings file"
                return 1
            fi
        fi
    fi
}

# Main execution
main() {
    echo "🔄 Claude Config Sync"
    echo "===================="

    if [[ "$DRY_RUN" == "true" ]]; then
        print_warning "Running in DRY RUN mode - no changes will be made"
    fi

    check_prerequisites
    create_target_structure

    # Sync directories (agents/ is optional; the repo no longer ships one)
    if [[ -d "$HOME/.claude/agents" ]]; then
        sync_directory "$HOME/.claude/agents" ".claude/agents" "agents"
    fi
    sync_directory "$HOME/.claude/commands" ".claude/commands" "commands"
    # Handle settings
    handle_settings

    echo
    if [[ "$DRY_RUN" == "true" ]]; then
        print_info "DRY RUN completed - run without --dry-run to apply changes"
    else
        print_success "Sync completed successfully!"
        print_info "Your .claude directory has been updated with the latest configurations"
    fi
}

# Run main function
main "$@"