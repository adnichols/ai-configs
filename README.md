# Claude Code, Codex, Gemini CLI & OpenCode Configuration

A comprehensive configuration system for Claude Code, Codex, Gemini CLI, and OpenCode that provides specialized agents, custom commands, and complete development workflows for building software with AI assistance.

## 🚀 Quick Start

### Installation

This repository supports installation for **Claude Code**, **Codex**, **Gemini CLI**, and **OpenCode**.

#### Option 1: Install to a Project

```bash
# Clone this repository (if not already done)
git clone <repository-url>
cd adn-claude-configs

# Install Python dependencies for docs-fetch commands
pip3 install -r requirements.txt

# Install to your project
cd /path/to/your/project

# Install Claude Code only
bash /path/to/adn-claude-configs/install.sh --claude

# Install Gemini CLI only
bash /path/to/adn-claude-configs/install.sh --gemini

# Install Codex only
bash /path/to/adn-claude-configs/install.sh --codex

# Install OpenCode only
bash /path/to/adn-claude-configs/install.sh --opencode

# Install everything (Claude, Gemini, Codex, OpenCode, tools, skills)
bash /path/to/adn-claude-configs/install.sh --all
```

#### Option 2: Install Globally (to Home Directory)

```bash
# Install to ~/.claude, ~/.gemini, ~/.codex, and ~/.opencode for global access
bash /path/to/adn-claude-configs/install.sh --all ~
```

### Updating Existing Installations

To sync the latest changes from this repository, simply run the install script again:

```bash
cd /path/to/your/project
bash /path/to/adn-claude-configs/install.sh --all
```

The install script auto-detects existing installations and:
- Updates agents, commands/prompts, and scripts
- Cleans up legacy directory structures
- Preserves your local settings and configuration files
- Mirrors Codex prompts to `~/.codex/prompts` for global CLI access

## 🧠 Fidelity-Preserving System

This repository features a **Fidelity-Preserving System** that automatically:

- **Preserves exact scope** from requirements through implementation
- **Uses fidelity-preserving agents** for implementation and quality review
- **Prevents scope creep** by maintaining strict adherence to specifications
- **Ensures quality** through comprehensive validation while staying within scope
- **Unified task processor** (`/3:process-tasks`) works with PRD and spec workflows

### Agent Types

| Purpose | Agent Type | Validation Requirements |
|---------|------------|------------------------|
| **Implementation** | `developer-fidelity` | Lint + Build + Secrets + Unit Tests |
| **Quality Review** | `quality-reviewer-fidelity` | Production readiness validation |
| **Fidelity Check** | `fidelity-reviewer` | Specification compliance validation |

## 📁 Repository Structure

```
adn-claude-configs/
├── claude/                   # Claude Code configuration (Source of Truth for Agents)
│   ├── agents/              # Agent definitions
│   ├── commands/            # Slash commands
│   ├── scripts/             # Shared utility scripts
│   ├── settings.local.json  # Claude Code settings template
├── gemini/                   # Gemini CLI configuration
│   ├── commands/            # Gemini commands (TOML)
│   └── GEMINI.template.md   # Gemini context template
├── codex/                    # Codex configuration
│   ├── prompts/             # Codex prompts
│   ├── config.toml          # Codex configuration template
│   └── mcp-servers.toml     # MCP server definitions
├── opencode/                 # OpenCode configuration
│   └── commands/            # OpenCode slash commands
├── tools/                    # Distributable CLI tools
│   └── ltui/                # Linear CLI for AI agents
├── skills/                   # Claude Code skills
│   └── linear/              # Linear integration skill for ltui
├── docs/                     # Fetched documentation
├── install.sh                # Install and update script
└── AGENTS.md                 # Agent catalog and fidelity rules
```

**Key Directories:**

- **claude/agents/** - Source of truth for all agents
- **claude/**, **gemini/**, **codex/**, **opencode/** - Installable configurations for each tool
- **tools/** - Distributable CLI tools (installed globally via `--tools`)
- **install.sh** - Single script for installation and updates

## 🔧 Distributed Tools

### ltui - Linear CLI for AI Agents

A token-efficient Linear issue tracker CLI optimized for AI coding agents.

**Installation:**

```bash
./install.sh --tools --skills
```

**Features:**
- **Token-efficient**: Uses compact TSV format
- **AI-friendly**: Deterministic outputs
- **Integrated**: Works natively with Claude Code via skills

**Usage:**

```bash
ltui issues list --assignee me
ltui issues create --team ENG --title "New Feature" --description "Details..."
```

## 🤖 Available Agents

The system uses carefully configured agents that focus on exact scope implementation and quality validation.

### Core Agents

**`@developer-fidelity`** - Fidelity-preserving implementation
- Implements only what's explicitly specified
- Comprehensive unit tests as required
- Zero linting violations enforced

**`@quality-reviewer-fidelity`** - Fidelity-preserving quality review
- Reviews against source specifications for exact compliance
- Prevents scope creep during review process

**`@fidelity-reviewer`** - Specification compliance validation  
- Compares implementations against original specifications
- Identifies missing requirements and scope additions

**`@developer`** - General implementation
- Standard developer persona for non-strict workflows

**`@quality-reviewer`** - General quality review
- Standard code review for production readiness

**`@technical-writer`** - Documentation
- Creates concise, actionable documentation

**`@simplify-planner`** - Complexity reduction
- Analyzes codebases for simplification opportunities

**`@debugger`** - Issue analysis
- Evidence-based bug investigation

### Utility Agents

- **`@codebase-analyzer`**: Explains code execution and data flows
- **`@codebase-locator`**: Finds relevant files
- **`@codebase-pattern-finder`**: Identifies architectural patterns
- **`@thoughts-analyzer`**: Synthesizes context from the `thoughts/` directory
- **`@web-search-researcher`**: Finds external information


## 🛠️ Command Workflows

### 1. Documentation Fetch Workflow

**Fetch Library Documentation**:

```
/doc:fetch react                    # Fetch React documentation
/doc:fetch typescript --version 5.3 # Specific version
/doc:fetch lodash --sections api    # API reference only
/doc:fetch vue --update             # Update existing docs
/doc:fetch express --format minimal # Condensed format
```

### 2. Feature Development Workflow

**PRD-Based Development** (Standard workflow):

```
/prd:1:create-prd → /prd:2:gen-tasks → /3:process-tasks
```

**Specification-Based Development** (Direct from specs):

```
[Detailed Spec] → /spec:2:gen-tasks → /3:process-tasks
```

**Research-Based Development** (From research documents):

```
[Research Doc] → /spec:1:create-spec → /spec:2:gen-tasks → /3:process-tasks
```

### 3. Code Quality Workflows

**Simplification Workflow**:

```
/simplify:create-plan → @quality-reviewer → /simplify:process-plan
```

## 🔄 Usage Patterns

### Fetching Documentation

The `/doc:fetch` command transforms scattered online documentation into locally stored, AI-friendly Markdown files for enhanced Claude Code integration:

1. **Basic usage**:

   ```bash
   /doc:fetch react
   # Fetches React documentation to /workspace/docs/frameworks/react/
   ```

2. **Advanced options**:

   ```bash
   /doc:fetch typescript --version 5.3
   # Fetch specific version

   /doc:fetch lodash --sections api
   # Fetch only API reference sections

   /doc:fetch vue --update
   # Update existing documentation

   /doc:fetch express --format minimal
   # Use condensed format
   ```

3. **Generated structure**:

   ```
   /workspace/docs/
   ├── libraries/lodash/
   ├── frameworks/react/
   └── languages/typescript/
       ├── index.md              # Overview and navigation
       ├── api-reference.md      # Complete API documentation  
       ├── best-practices.md     # Current patterns and conventions
       └── examples/             # Code examples and tutorials
   ```

**Features:**
- **AI-Optimized**: Content processed by Technical Writer agent for Claude Code understanding
- **Self-Learning**: Automatically discovers and saves site patterns for future use
- **Quality Validation**: Comprehensive content analysis with completeness metrics
- **Error Recovery**: Robust retry logic with exponential backoff
- **Enhanced Fetching**: Smart handling of JavaScript-heavy documentation sites

### Creating New Features

1. **Start with requirements gathering**:

   ```bash
   /prd:1:create-prd
   # Follow interactive prompts to create detailed PRD
   ```

2. **Build out the task lists**:

   ```bash
   git checkout -b feature/new-feature # optional, claude should do this
   /prd:2:gen-tasks @path-to-prd.md
   # Generate parent tasks, review, and then say "Go" to build sub-tasks.
   # Should detect if you are on a branch and create one if not
   ```

3. **Process the implementation**:

   ```bash
   /3:process-tasks @path-to-task-list.md
   # Processes tasks one at a time with fidelity preservation

   # Or, if you want no confirmation prompts
   /3:process-tasks @path-to-task-list.md NOSUBCONF
   ```

4. **Generate documentation**:

   ```bash
   /doc:update
   # Creates user and technical documentation
   ```

### Working with Research

1. **Convert research to specification**:

   ```bash
   /spec:1:create-spec @research-idea-description.md
   # Converts research ideas into comprehensive specification documents
   ```

2. **Convert specification to tasks**:

   ```bash
   /spec:2:gen-tasks @research-spec-file.md
   # Converts specifications to detailed task lists with fidelity preservation
   ```

3. **Execute with full context**:

   ```bash
   /3:process-tasks @fidelity-task-list.md
   # Preserves all specification context during implementation
   ```

### Code Simplification

1. **Analyze for improvements**:

   ```bash
   /simplify:create-plan
   # Creates detailed simplification plan
   ```

2. **Review with quality agent**:

   ```bash
   @quality-reviewer @refactor-plan.md
   ```

3. **Execute approved changes**:

   ```bash
   /simplify:process-plan @refactor-task-list.md
   ```

## 📖 Best Practices

### Git Workflow Requirements

- **Always work on feature branches** (never directly on main)
- **One sub-task at a time** unless `NOSUBCONF` is specified
- **Tests must pass** before any commits
- **Conventional commit format** is automatically applied

### Task Processing Guidelines

- Use `NOSUBCONF` parameter for batch processing when appropriate
- Provide clear, actionable task descriptions
- Break complex features into phases with clear boundaries
- Include test requirements in all implementation tasks

### Quality Standards

- All agents reference CLAUDE.md for project-specific standards
- Documentation is generated after implementation, not before

## 🔌 MCP Server Configuration

This repository includes MCP (Model Context Protocol) server definitions for Codex.

### Codex

MCP servers are defined in `codex/mcp-servers.toml`. To use them:

1. **Merge into config**: Copy `[mcp_servers.*]` sections into your `~/.codex/config.toml`
2. **Project-level**: Add to project's `.codex/config.toml`

### Example MCP Servers

The repository includes the Playwright MCP server by default. Add more as needed:

```toml
# Codex (TOML)
[mcp_servers.playwright]
command = "npx"
args = ["-y", "@playwright/mcp@latest"]
```

## 📝 Installation Notes

- **CLAUDE.md and CODEX.md are NOT installed** - Codex generates these files based on your project
- **Settings are preserved** - The update script never overwrites your local settings files
- **Source directories remain** - `agents/` and `commands/` are maintained as the source of truth
- **Both tools supported** - Install Claude Code, Codex, or both to the same project

## 📚 Documentation

- **[CLAUDE.md](CLAUDE.md)** - Repository-specific guidance for Claude Code integration

---

**Need help?** Check the documentation files above, review `claude/commands/README.md` or `opencode/commands/README.md` for detailed workflow guidance, or use the specialized agents for specific tasks.
