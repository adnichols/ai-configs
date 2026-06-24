# OpenCode Onboarding Quick Start

This quick start guide helps you rapidly set up OpenCode with the configurations from this repository.

## Quick Steps

### 1. Get OpenCode

```bash
curl -fsSL https://opencode.ai/install | bash
```

### 2. Run the Full Onboarding

**For developers setting up this repo:**

```bash
# Navigate to the repository root
cd /path/to/adn-claude-configs

# Ask your AI agent (Claude Code, OpenCode, etc.) to execute the onboarding
# Provide this instruction:

"Please follow _opencode/OPENCODE_ONBOARDING.md to set up OpenCode with
all configurations, MCP servers, and model providers from this repository.
The document uses relative paths starting from the repository root."
```

### 3. Manual Installation (Step-by-Step)

If you prefer manual installation or need to troubleshoot:

```bash
# 1. Install OpenCode resources and shared skills
./install.sh --opencode

# 2. Copy config files that are intentionally not auto-installed
mkdir -p ~/.config/opencode ~/.opencode
cp ./_opencode/config-template.json ~/.config/opencode/opencode.json
cp ./_opencode/openai-codex-auth-config.template.json ~/.opencode/openai-codex-auth-config.json

# 3. Install Playwright dependencies from the canonical shared skill path
cd ~/.agents/skills/playwright-skill
npm run setup

# 4. Configure API keys
opencode auth add --provider synthetic
opencode auth add --provider deepinfra

# 5. Verify
cd /tmp && opencode
```

Shared skills are installed to `~/.agents/skills`; OpenCode-compatible entries are linked under `~/.config/opencode/skills`.

## What Gets Installed

- ✅ **MCP Servers**: Playwright (browser automation), Serena (code analysis)
- ✅ **Model Providers**: Synthetic.new, DeepInfra, Google (via Antigravity)
- ✅ **Custom Skills**: Playwright browser automation skill
- ✅ **Custom Prompts**: GLM-4.7 preserved thinking protocol

## Key Files in this Repository

- `_opencode/OPENCODE_ONBOARDING.md` - Comprehensive onboarding guide (use this!)
- `_opencode/config-template.json` - OpenCode configuration template
- `_opencode/openai-codex-auth-config.template.json` - `oc-codex-multi-auth` runtime config template
- `_opencode/prompts/glm-reasoning.md` - GLM thinking prompt
- `~/.agents/skills/playwright-skill/` - Browser automation skill installed from `skills/install-matrix.json`

## For Other Repositories

To use these configurations in any repository:

1. Copy or vendor the `_opencode/` directory and `skills/install-matrix.json` into your target repo
2. Run the onboarding: "Follow _opencode/OPENCODE_ONBOARDING.md"
3. All paths in the onboarding document are relative to the repository root

## Need More Details?

See the comprehensive guide: **`_opencode/OPENCODE_ONBOARDING.md`**

It includes:
- Step-by-step installation instructions
- Verification commands
- Model recommendations
- Troubleshooting guide
- Configuration file reference
