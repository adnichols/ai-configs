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

And global/home resources where those tools expect them:

- `~/.codex/`
- `~/.pi/agent/`
- `~/.agents/skills/`

Shared skill inventory is declared in `skills/install-matrix.json`; default repo-owned payloads are copied from `skills/`, and default package-backed payloads are fetched via `npx skills`. Optional-profile skills are recorded in the matrix with `defaultInstall: false` and are not placed in `~/.agents/skills` by default.

## Single-surface installs

```bash
bash ~/ai-configs/install.sh --claude
bash ~/ai-configs/install.sh --codex
bash ~/ai-configs/install.sh --pi
bash ~/ai-configs/install.sh --skills
bash ~/ai-configs/install.sh --tools
```

`--tools` installs `ltui` from the standalone `Nodaste-Lab/ltui` repository,
installs or updates the managed OMP Ponytail plugin when `omp` is available,
and installs or updates managed Herdr plugins, currently
`persiyanov/herdr-reviewr`. Herdr plugins are refreshed from upstream on each
run; the step warns and skips when `herdr` is unavailable. Use
`LTUI_REPO_URL` and `LTUI_REF` to test or pin a different ltui checkout/ref.

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
- `_codex/` is repo source, while Codex installs globally under `~/.codex/`
- `_pi/` is repo source, while Pi installs globally under `~/.pi/agent/`

Shared helper scripts live in repo-level `scripts/` and are copied into runtime locations by `install.sh`.

## Verification

After install, sanity check the surfaces you care about:

```bash
ls .claude 2>/dev/null
ls ~/.codex ~/.pi/agent ~/.agents/skills 2>/dev/null
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

### Retired surfaces still present
Re-run any maintained install mode to remove positively identified managed deprecated shared-skill entries such as `omp-review-partner`. Gemini, OMP, OpenCode, and Pi plan-mode runtime trees may contain user changes, so inspect and remove them explicitly during host cleanup.
