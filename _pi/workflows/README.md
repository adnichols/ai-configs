# Pi workflows

Live copies: `~/.pi/agent/workflows/`.

```bash
mkdir -p ~/.pi/agent/workflows ~/.pi/agent/prompts ~/.pi/agent/pi-extensible-workflows
cp _pi/workflows/*.js ~/.pi/agent/workflows/
cp _pi/prompts/heddle:release*.md ~/.pi/agent/prompts/
cp _pi/pi-extensible-workflows/settings.json ~/.pi/agent/pi-extensible-workflows/settings.json
```

## heddle-release

Commands: `/heddle:release`, `/heddle:release-resume`

- Herdr-native panes
- State in `~/.heddle-release/v{version}/` (outside git worktree — required for clean signed provenance)
- Deterministic cut script (temp develop worktree)
- Interactive gate TTY + watch script; `herdr-operator-attention` marks the stable work pane blocked while the 1Password gate is waiting and clears it on every outcome
- Single flocked `npm ci` + `release:signed` with failure `build.json`
- Auto-resume from cut/gate/build progress
- Publish agent + Slack `#heddle-release`

```text
/heddle:release
/heddle:release-resume          # from release worktree
/heddle:release-resume 0.3.3
```
