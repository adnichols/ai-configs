# OpenCode Onboarding Guide

This document provides comprehensive onboarding instructions for configuring OpenCode with optimal MCP servers, model providers, and custom skills. This guide is designed to be executed by an AI agent with write permissions.

## Agent Instructions

**How to use this document:**

1. **Assume write permissions**: This guide expects the agent to be able to:
   - Create directories and files in `~/.config/opencode/`
   - Execute shell commands for installation and testing
   - Modify configuration files

2. **Use relative paths**: All source paths are relative to the repository root where this onboarding document lives
   - Example: `./opencode/config-template.json` refers to `config-template.json` in the repository's `opencode/` directory
   - Destinations are always absolute paths to `~/.config/opencode/`

3. **Execute steps sequentially**: Complete each step before moving to the next
4. **Verify at each step**: After each major step, run the verification command to confirm success
5. **Ask for API keys when needed**: If API keys are missing, prompt the user to provide them

## Prerequisites Check

Before starting, verify the following are available:

### System Tools Check

```bash
# Check for curl (for OpenCode installation)
curl --version

# Check for node and npm (for Playwright skill)
node --version
npm --version

# Check for uvx (for Serena MCP server)
uvx --version

# Check for Python 3 (may be needed for Serena)
python3 --version
```

If any tools are missing, install them first:

```bash
# Install node/npm (macOS)
brew install node

# Install uvx (if not present with Python)
# uvx should come with uv: pip install uv
```

### OpenCode Installation Check

```bash
# Check if OpenCode is already installed
opencode --version
```

If OpenCode is not installed, proceed to Step 1.

---

## Step 1: Install OpenCode CLI

Install the OpenCode CLI globally:

```bash
curl -fsSL https://opencode.ai/install | bash
```

### Verification

```bash
opencode --version
# Expected output: 1.1.13 or higher
```

If installation fails, check:
- You have an internet connection
- You have write permissions to `/usr/local/bin` (or the appropriate bin directory)
- Your shell is properly configured (restart your terminal if needed)

---

## Step 2: Create Directory Structure

Create the OpenCode configuration directory structure:

```bash
# Create main config directory
mkdir -p ~/.config/opencode

# Create subdirectories
mkdir -p ~/.config/opencode/agents
mkdir -p ~/.config/opencode/commands
mkdir -p ~/.config/opencode/prompts
mkdir -p ~/.config/opencode/skills/playwright-skill/lib
mkdir -p ~/.config/opencode/plugin
```

### Verification

```bash
ls -la ~/.config/opencode/
# Should show: agents/, commands/, prompts/, skills/, plugin/
```

---

## Step 3: Copy Configuration Files

Now copy the configuration files from this repository to `~/.config/opencode/`.

### 3.1 Copy Main Configuration

Copy the main OpenCode configuration template:

```bash
# Source: ./opencode/config-template.json
# Destination: ~/.config/opencode/opencode.json

cp ./opencode/config-template.json ~/.config/opencode/opencode.json
```

### 3.2 Copy Prompts

Copy the GLM-4.7 preserved thinking prompt:

```bash
# Source: ./opencode/prompts/glm-reasoning.md
# Destination: ~/.config/opencode/prompts/glm-reasoning.md

cp ./opencode/prompts/glm-reasoning.md ~/.config/opencode/prompts/glm-reasoning.md
```

### 3.3 Copy Playwright Skill

Copy the Playwright skill directory recursively:

```bash
# Source: ./opencode/skills/playwright-skill/
# Destination: ~/.config/opencode/skills/playwright-skill/

cp -r ./opencode/skills/playwright-skill/ ~/.config/opencode/skills/playwright-skill/
```

### Verification

```bash
# Verify main config exists
test -f ~/.config/opencode/opencode.json && echo "✅ opencode.json exists"

# Verify prompt exists
test -f ~/.config/opencode/prompts/glm-reasoning.md && echo "✅ glm-reasoning.md exists"

# Verify playwright skill exists
test -d ~/.config/opencode/skills/playwright-skill && echo "✅ playwright-skill directory exists"

# Verify skill files
test -f ~/.config/opencode/skills/playwright-skill/package.json && echo "✅ package.json exists"
test -f ~/.config/opencode/skills/playwright-skill/run.js && echo "✅ run.js exists"
test -f ~/.config/opencode/skills/playwright-skill/SKILL.md && echo "✅ SKILL.md exists"
test -f ~/.config/opencode/skills/playwright-skill/lib/helpers.js && echo "✅ lib/helpers.js exists"
```

---

## Step 4: Install Playwright Skill Dependencies

Install the npm dependencies for the Playwright skill:

```bash
cd ~/.config/opencode/skills/playwright-skill
npm install
```

This will install:
- `playwright@^1.57.0` - The Playwright browser automation library

### Verification

```bash
cd ~/.config/opencode/skills/playwright-skill
test -d node_modules && echo "✅ node_modules exists"
test -d node_modules/playwright && echo "✅ Playwright installed"
```

---

## Step 5: Install Playwright Browsers

Install the Chromium browser for Playwright:

```bash
cd ~/.config/opencode/skills/playwright-skill
npx playwright install chromium
```

This downloads and installs the Chromium browser binaries required for automation.

**Note:** This step may take a few minutes as it downloads browser binaries (~300MB).

### Alternative: Using npm script

If you prefer, you can run the setup script instead:

```bash
cd ~/.config/opencode/skills/playwright-skill
npm run setup
```

This runs both `npm install` and `npx playwright install chromium` in one command.

### Verification

```bash
cd ~/.config/opencode/skills/playwright-skill
npx playwright --version
# Expected output: Version 1.57.0 or higher
```

---

## Step 6: Configure Model Providers

OpenCode needs API keys for the configured model providers. You'll need to add these to your OpenCode configuration.

### 6.1 Configure Synthetic.new

Synthetic.new is the primary provider (GLM-4.7 with preserved thinking).

```bash
# Set your Synthetic.new API key
opencode auth add --provider synthetic
# You'll be prompted for your API key
```

Alternatively, you can manually add the API key to `~/.config/opencode/opencode.json`:

```json
{
  "provider": {
    "synthetic": {
      "apiKey": "YOUR_SYNTHETIC_NEW_API_KEY_HERE",
      "models": {
        "hf:zai-org/GLM-4.7": {
          "variants": {
            "thinking": {
              "description": "Deep reasoning with Preserved Thinking",
              "temperature": 1.0,
              "extra_body": {
                "thinking": {
                  "reasoningEffort": "high",
                  "type": "enabled",
                  "clear_thinking": false
                }
              }
            }
          }
        }
      }
    }
  }
}
```

### 6.2 Configure DeepInfra

DeepInfra provides MiniMax-M2.1 and GLM-4.7 alternatives.

```bash
# Set your DeepInfra API key
opencode auth add --provider deepinfra
# You'll be prompted for your API key
```

Or add manually to the config:

```json
{
  "provider": {
    "deepinfra": {
      "apiKey": "YOUR_DEEPINFRA_API_KEY_HERE",
      "models": {
        "MiniMaxAI/MiniMax-M2.1": {
          "name": "MiniMaxAI/MiniMax-M2.1"
        },
        "zai-org/GLM-4.7": {
          "variants": {
            "thinking": {
              "description": "Deep reasoning with Preserved Thinking",
              "temperature": 1.0,
              "extra_body": {
                "thinking": {
                  "reasoningEffort": "high",
                  "type": "enabled",
                  "clear_thinking": false
                }
              }
            }
          }
        }
      }
    }
  }
}
```

### 6.3 Configure Google (Antigravity)

Google models are provided via the Antigravity plugin, which handles authentication automatically.

The plugin should already be configured in `~/.config/opencode/opencode.json`:

```json
{
  "plugin": ["opencode-antigravity-auth@latest"]
}
```

If you need to authenticate:

```bash
# Run OpenCode and the Antigravity plugin will handle auth
opencode auth
```

### Verification - Model Access

Test that your API keys are working:

```bash
# List all available models
opencode models

# Try to use a model (this will test the connection)
opencode --model synthetic/GLM-4.7 --message "Hello, are you working?"
```

---

## Step 7: Verification & Testing

Now verify that everything is working correctly.

### 7.1 Verify MCP Server Configuration

Check that MCP servers are configured:

```bash
cat ~/.config/opencode/opencode.json | grep -A 10 '"mcp"'
```

You should see:
- **playwright** MCP server configured with `npx @playwright/mcp@latest`
- **serena** MCP server configured with `uvx` and the git repository

### 7.2 Test Serena MCP Server

Verify Serena can be invoked:

```bash
# Test that uvx can run the Serena MCP server
uvx --from "git+https://github.com/oraios/serena" serena-mcp-server --help 2>&1 | head -20
```

You should see help output or no errors.

**Note:** If you get an error about missing dependencies, you may need to run:
```bash
# Install globally (optional, uvx should handle this)
pip install git+https://github.com/oraios/serena
```

### 7.3 Test Playwright Skill

Create a simple test script to verify Playwright is working:

```bash
# Create a test script
cat > /tmp/test-playwright.js << 'EOF'
const { chromium } = require('playwright');

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('https://example.com');
  const title = await page.title();
  console.log('✅ Page title:', title);
  await browser.close();
})();
EOF

# Run the test with the skill's executor
cd ~/.config/opencode/skills/playwright-skill
node run.js /tmp/test-playwright.js
```

Expected output: `✅ Page title: Example Domain`

### 7.4 Test OpenCode Start

Start OpenCode to verify everything integrates:

```bash
# Start OpenCode in a test directory
mkdir -p /tmp/opencode-test
cd /tmp/opencode-test
opencode

# OpenCode should start and load:
# - Your configured models
# - MCP servers (playwright, serena)
# - Playwright skill
# - GLM reasoning prompt
```

Once OpenCode starts, try these commands:
```
Hello, can you list the available MCP tools?
Can you write a simple Playwright script to test example.com?
```

### 7.5 Test Thinking Variant

Test the GLM-4.7 thinking variant (if you have access):

```bash
cd /tmp/opencode-test
opencode --model "synthetic/GLM-4.7:thinking" --message "Explain the concept of recursion in simple terms. Think step by step."
```

You should see the model's preserved thinking process in the output.

---

## Model Recommendations

Here are recommended model choices for different tasks:

| Task | Recommended Model | Reasoning |
|------|------------------|-----------|
| **Architectural Planning** | GLM-4.7 (thinking variant) | Preserved thinking with high reasoning effort maintains deep context |
| **Code Implementation** | Gemini 3 Pro High | Fast execution, code-focused, 1M context window |
| **Code Review** | MiniMax-M2.1 | Balanced speed and accuracy for reviewing quality |
| **Quick Edits** | Gemini 3 Flash | Fast, responsive for small tasks |
| **Multi-Stage Workflows** | GLM-4.7 thinking | Preserves reasoning across multiple steps |
| **Browser Automation** | Gemini 3 Flash | Fast for interactive Playwright tasks |
| **Debugging** | GLM-4.7 (thinking variant) | Deep reasoning helps analyze complex issues |
| **Documentation** | Gemini 3 Pro Medium | Good balance of quality and speed |

### When to Use Thinking Variants

The "thinking" variant (available for GLM-4.7) includes **preserved thinking** - the model shows its reasoning process in the output. Use this when:

- You need to see the model's step-by-step reasoning
- Working on complex architectural decisions
- Debugging complicated issues
- Want to understand why the model made certain choices
- Educational purposes (to learn from the model's thought process)

The thinking variant takes longer but provides better transparency.

### Cost/Performance Tradeoffs

| Model | Speed | Quality | Cost (approx) | Best For |
|-------|-------|---------|---------------|----------|
| Gemini 3 Flash | 🟢 Fast | 🟡 Good | 💰 Low | Quick edits, testing |
| MiniMax-M2.1 | 🟡 Medium | 🟢 Good | 💰💰 Medium | Code review, general coding |
| Gemini 3 Pro High | 🟡 Medium | 🟢 Excellent | 💰💰💰 High | Complex implementation |
| GLM-4.7 (thinking) | 🔴 Slow | 🟢 Excellent | 💰💰💰💰 Very High | Architecture, debugging |

---

## Troubleshooting

### OpenCode Won't Start

**Problem:** OpenCode fails to start

**Solutions:**

```bash
# Check if OpenCode is installed
opencode --version

# If not found, reinstall
curl -fsSL https://opencode.ai/install | bash

# Check for syntax errors in config
cat ~/.config/opencode/opencode.json | jq .
# If jq fails, there's a JSON syntax error
```

### MCP Servers Not Loading

**Problem:** MCP servers (Playwright, Serena) are not available

**Check configuration:**

```bash
# Verify MCP config exists
cat ~/.config/opencode/opencode.json | grep -A 15 '"mcp"'

# Test Playwright MCP directly
npx @playwright/mcp@latest --help

# Test Serena MCP directly
uvx --from "git+https://github.com/oraios/serena" serena-mcp-server --help
```

**Solutions:**

- For Playwright: Ensure `npx` is in your PATH
- For Serena: Ensure Python 3 and pip/uvx are installed
- Check for Internet connectivity (uvx needs to download Serena from git)

### Playwright Skill Not Working

**Problem:** Playwright skill fails to execute

**Solutions:**

```bash
# Check if Playwright is installed
cd ~/.config/opencode/skills/playwright-skill
test -f node_modules/playwright/package.json || echo "Playwright not installed"

# Reinstall dependencies
cd ~/.config/opencode/skills/playwright-skill
rm -rf node_modules package-lock.json
npm install
npx playwright install chromium

# Test the skill directly
node run.js "const { chromium } = require('playwright'); (async () => { const browser = await chromium.launch(); console.log('✅ Playwright works'); await browser.close(); })();"
```

### API Key Authentication Fails

**Problem:** Models return authentication errors

**Solutions:**

```bash
# Remove and re-add API keys
opencode auth remove --provider synthetic
opencode auth add --provider synthetic

# Or manually verify in config
cat ~/.config/opencode/opencode.json | grep -A 2 '"apiKey"'

# Test model access directly
opencode models synthetic/
```

### Serena MCP Server Errors

**Problem:** Serena fails to start or times out

**Solutions:**

```bash
# Install Serena globally (for testing)
pip install git+https://github.com/oraios/serena

# Install uv if uvx not available
pip install uv

# Test Serena MCP server manually
uvx --from "git+https://github.com/oraios/serena" serena-mcp-server --enable-web-dashboard false
```

**Note:** Serena installation is handled by uvx. Users may need to ensure Python 3 and pip are properly configured.

### Browser Browser Not Found

**Problem:** Playwright can't find chromium

**Solutions:**

```bash
cd ~/.config/opencode/skills/playwright-skill
npx playwright install chromium

# Force reinstall
npx playwright install --force chromium

# Check installed browsers
npx playwright install --dry-run
```

### Permission Errors

**Problem:** Cannot write to `~/.config/opencode/`

**Solutions:**

```bash
# Fix permissions
chmod 755 ~/.config/opencode
chmod 644 ~/.config/opencode/*.json
chmod 644 ~/.config/opencode/prompts/*.md
chmod -R 755 ~/.config/opencode/skills/

# Or recreate with correct permissions
rm -rf ~/.config/opencode
mkdir -p ~/.config/opencode/{agents,commands,prompts,skills/playwright-skill/lib,plugin}
```

---

## Getting Help

If you encounter issues not covered here:

1. **Check OpenCode docs**: https://opencode.ai/docs
2. **Check OpenCode GitHub**: https://github.com/anomalyco/opencode/issues
3. **Check Serens docs**: https://github.com/oraios/serena
4. **Check Playwright docs**: https://playwright.dev/docs/intro

---

## Next Steps

After completing onboarding:

1. **Explore the repository**: Check the `opencode/agents/` and `opencode/commands/` directories for customized agents and commands
2. **Create your first session**: `cd /your/project && opencode`
3. **Try the Playwright skill**: Ask OpenCode to "Create a Playwright test for example.com"
4. **Explore models**: Try different models with `opencode --model provider/model --message "test"`
5. **Use MCP tools**: Ask OpenCode to "Show me the available MCP tools"

---

## Configuration File Reference

### ~/.config/opencode/opencode.json

Main configuration file containing:
- **plugin**: Plugins to load (e.g., opencode-antigravity-auth)
- **mcp**: MCP server configurations (playwright, serena)
- **provider**: Model provider configurations with API keys and model variants

### ~/.config/opencode/prompts/glm-reasoning.md

Custom prompt for GLM-4.7 with preserved thinking protocol:
- Thread state management
- Execution rules with thinking blocks
- Architectural consistency focus

### ~/.config/opencode/skills/playwright-skill/

Browser automation skill:
- **package.json**: Dependencies and setup scripts
- **run.js**: Universal executor for Playwright code
- **SKILL.md**: Skill documentation and usage patterns
- **lib/helpers.js**: Utility functions for common tasks
- **API_REFERENCE.md**: Comprehensive Playwright API reference

---

## Summary

This onboarding guide sets up OpenCode with:

✅ **MCP Servers**: Playwright (browser automation), Serena (code analysis)
✅ **Model Providers**: Synthetic.new, DeepInfra, Google (via Antigravity)
✅ **Custom Skills**: Playwright browser automation skill
✅ **Custom Prompts**: GLM-4.7 preserved thinking protocol
✅ **Configured Models**: GLM-4.7 (with thinking variant), MiniMax-M2.1, Gemini 3 series

Ready to build software with AI assistance! 🚀
