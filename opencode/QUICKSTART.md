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

"Please follow opencode/OPENCODE_ONBOARDING.md to set up OpenCode with
all configurations, MCP servers, and model providers from this repository.
The document uses relative paths starting from the repository root."
```

### 3. Manual Installation (Step-by-Step)

If you prefer manual installation or need to troubleshoot:

```bash
# 1. Create directories
mkdir -p ~/.config/opencode/{agents,commands,prompts,skills/playwright-skill/lib,plugin}

# 2. Copy config files
cp opencode/config-template.json ~/.config/opencode/opencode.json
cp opencode/prompts/glm-reasoning.md ~/.config/opencode/prompts/
cp -r opencode/skills/playwright-skill/ ~/.config/opencode/skills/
cp -r opencode/commands/ ~/.config/opencode/commands/
cp -r opencode/agents/ ~/.config/opencode/agents/

# 3. Install Playwright dependencies
cd ~/.config/opencode/skills/playwright-skill
npm run setup

# 4. Configure API keys
opencode auth add --provider synthetic
opencode auth add --provider deepinfra

# 5. Verify
cd /tmp && opencode
```

## What Gets Installed

- ✅ **MCP Servers**: Playwright (browser automation), Serena (code analysis)
- ✅ **Model Providers**: Synthetic.new, DeepInfra, Google (via Antigravity)
- ✅ **Custom Skills**: Playwright browser automation skill
- ✅ **Custom Prompts**: GLM-4.7 preserved thinking protocol

## Key Files in this Repository

- `opencode/OPENCODE_ONBOARDING.md` - Comprehensive onboarding guide (use this!)
- `opencode/config-template.json` - OpenCode configuration template
- `opencode/prompts/glm-reasoning.md` - GLM thinking prompt
- `opencode/skills/playwright-skill/` - Browser automation skill

## For Other Repositories

To use these configurations in any repository:

1. Copy the `opencode/` directory from this repo to your target repo
2. Run the onboarding: "Follow opencode/OPENCODE_ONBOARDING.md"
3. All paths in the onboarding document are relative to the repository root

## Need More Details?

See the comprehensive guide: **`opencode/OPENCODE_ONBOARDING.md`**

It includes:
- Step-by-step installation instructions
- Verification commands
- Model recommendations
- Troubleshooting guide
- Configuration file reference
