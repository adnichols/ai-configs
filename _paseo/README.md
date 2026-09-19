# Paseo configuration in ai-configs

This tree captures the managed parts of the Paseo daemon configuration so
profiles, provider definitions, and tuned skills are reviewed here and
installed everywhere instead of drifting per host.

## Current bundle

- `config.json` — managed keys for `~/.paseo/config.json`: agent profiles,
  provider definitions and enablement, `agents.skills.selection`, CORS, relay,
  and feature flags. `agents.providers.omp.additionalModels` marks `@default`
  as the default model so launches without a profile resolve OMP's configured
  `modelRoles.default` (Paseo passes the model through unvalidated and OMP
  resolves the `@default` role sentinel itself).
- `merge_config.py` — deep-merge installer for the daemon config. Managed keys
  win; `daemon.agentProfiles` merges by `name` so locally added profiles
  survive; unmanaged keys (auth state, host-local tweaks, future daemon keys)
  are preserved.
- `skills/` — repo-owned copies of the `paseo*` skills. Seeded from the
  `@getpaseo/server` bundle; tune them here.
- `install.sh` — merges the config, syncs `skills/` into `~/.agents/skills`,
  `~/.claude/skills`, and `~/.codex/skills`, then runs `paseo reload` when a
  daemon is reachable.

## Why skills are managed here

The daemon rewrites its bundled skill files from the npm package at startup
(`orchestration-skills` auto-update), so edits to `~/.agents/skills/paseo*` are
reverted. The managed config sets `agents.skills.selection` to
`{"mode": "custom", "skills": []}` so the daemon stops owning those
directories, and this installer owns them instead. Consequences:

- The daemon's skills UI may report drift and offer to reinstall the bundle.
  Decline, or rerun `bash _paseo/install.sh` to restore the repo copies.
- New bundled skills in a Paseo release are not auto-installed; add them to
  `_paseo/skills/` deliberately.

## Normal workflow

```bash
# Local install (also runs under install.sh --tools / --all)
bash _paseo/install.sh

# Stream to the other hosts (mbp, dever, thump; local host is skipped)
bash scripts/install-paseo-remote-hosts.sh
```

Overrides: `PASEO_CONFIG_TARGET` (daemon home), `PASEO_SKILL_TARGETS`
(space-separated skills roots), `PASEO_SKIP_RELOAD=1`, `PASEO_REMOTE_HOSTS`,
`PASEO_CONFIG_SKIP_REMOTE=1`, `PASEO_CONFIG_STRICT_REMOTE=1`.

Test: `bash test_paseo_config_install.sh`.
