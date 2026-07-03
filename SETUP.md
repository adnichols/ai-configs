# Quick Setup

## Recommended project install

```bash
git clone <repository-url> ~/ai-configs
cd ~/ai-configs
pip3 install -r requirements.txt

cd /path/to/your/project
bash ~/ai-configs/install.sh --all
```

This installs the project-facing runtime directories as needed:

- `.claude/`
- `.gemini/`
- `.codex/`

And global/home resources where those tools expect them:

- `~/.omp/agent/`
- `~/.pi/agent/`
- `~/.config/opencode/`
- `~/.agents/skills/`

Shared skill inventory is declared in `skills/install-matrix.json`; default repo-owned payloads are copied from `skills/`, and default package-backed payloads are fetched via `npx skills`. Optional-profile skills are recorded in the matrix with `defaultInstall: false` and are not placed in `~/.agents/skills` by default.

## Single-surface installs

```bash
bash ~/ai-configs/install.sh --claude
bash ~/ai-configs/install.sh --codex
bash ~/ai-configs/install.sh --gemini
bash ~/ai-configs/install.sh --omp
bash ~/ai-configs/install.sh --pi
bash ~/ai-configs/install.sh --opencode
bash ~/ai-configs/install.sh --skills
bash ~/ai-configs/install.sh --tools
```

## Global install

```bash
bash ~/ai-configs/install.sh --all ~
```

## Updating

Re-run the same install command:

```bash
bash ~/ai-configs/install.sh --all
```

The installer refreshes managed resources while preserving local settings where supported.

## Source vs runtime

In this repo:

- `_<tool>/` = committed source-of-truth config
- `.<tool>/` = local runtime/install artifact

Examples:
- `_claude/` is repo source, `.claude/` is installed runtime
- `_codex/` is repo source, `.codex/` is installed runtime
- `_gemini/` is repo source, `.gemini/` is installed runtime

Shared helper scripts live in repo-level `scripts/` and are copied into runtime locations by `install.sh`.

## Verification

After install, sanity check the surfaces you care about:

```bash
ls .claude .gemini .codex 2>/dev/null
ls ~/.omp/agent ~/.pi/agent ~/.config/opencode ~/.agents/skills 2>/dev/null
```

## Troubleshooting

### Commands not showing up
Re-run `install.sh`, then restart the relevant tool.

### Codex prompts missing
Check:

```bash
ls ~/.codex/prompts
```

### Shared skills missing
Check:

```bash
ls ~/.agents/skills
```

### OpenCode onboarding
Use:

```text
_opencode/OPENCODE_ONBOARDING.md
```
