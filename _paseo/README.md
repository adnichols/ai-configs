# Paseo configuration in ai-configs

This tree owns the `paseo*` skills. It does not override live Paseo daemon
configuration: profiles, providers, relay, listen, CORS, and feature flags
stay on each host.

## Current bundle

- `config.json` — the only managed daemon key is `agents.skills.selection`
  (`custom`, empty list). That stops the daemon from rewriting the repo-owned
  `paseo*` skill directories at startup. Everything else in `~/.paseo/config.json`
  is host-local. Shipping profiles, providers, or `daemon.relay` from here
  reset host `omp` profiles and disabled mobile relay.
- `merge_config.py` — deep-merge installer. Keys named in the managed file
  win; keys absent from it are preserved.
- `skills/` — repo-owned copies of the `paseo*` skills. Seeded from the
  `@getpaseo/server` bundle; tune and evaluate them here. The `paseo` and
  `paseo-help` overrides route state, logs, and terminal output through the
  CLI before any UI automation.
- `install.sh` — merges that one skills-selection key, syncs `skills/` into
  `~/.agents/skills`, `~/.claude/skills`, and `~/.codex/skills`, then runs
  `paseo reload` when a daemon is reachable.

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
- Replaced skill copies are preserved under the runtime parent directory's
  `.paseo-skill-backups/`, outside active skill discovery roots. The installer
  migrates legacy `*.before-ai-configs` backups out of those roots so stale
  copies cannot compete with the repo-owned skills.

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
