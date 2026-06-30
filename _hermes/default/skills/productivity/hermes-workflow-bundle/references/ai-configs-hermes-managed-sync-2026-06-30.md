# ai-configs Hermes managed sync pattern (2026-06-30)

Session-derived pattern for capturing a live `~/.hermes` configuration into `~/code/ai-configs` as a source-of-truth copy while keeping secrets/runtime state out of git.

## Goal

Keep a repo-owned, reviewable copy of managed Hermes configuration so future changes can be made in `~/code/ai-configs` first, then installed into `~/.hermes`.

## Recommended layout

```text
~/code/ai-configs/
├── _hermes/
│   ├── README.md
│   └── default/
│       ├── README.md
│       ├── EXCLUSIONS.md
│       ├── manifest.json
│       ├── config/config.yaml
│       ├── skills/
│       ├── hooks/
│       ├── plugins/
│       ├── scripts/
│       ├── cron/jobs.json
│       ├── memories/{MEMORY.md,USER.md}
│       └── profiles/<profile>/...
└── scripts/hermes_config_sync.py
```

## Include

- Sanitized `config.yaml` with secret-like leaves replaced by a redaction marker.
- Skills, hooks, plugins, scripts, and source-like support files.
- `cron/jobs.json`, not `cron/output/`.
- `memories/MEMORY.md` and `memories/USER.md` when the goal is to clone the current workflow behavior.
- The same managed surfaces under nested Hermes profiles when present.
- A `manifest.json` with SHA-256 hashes for every exported file except the manifest itself.

## Exclude

- `.env`, `auth.json`, OAuth/PAT/API tokens, credential pools, private keys.
- `sessions/`, `state.db*`, `kanban.db*`, checkpoints, state snapshots, process state.
- logs, caches, audio/image artifacts, paste dumps, generated cron output, temp dirs.
- Hermes source checkout / venv / node_modules under `~/.hermes/hermes-agent`.
- lock and pid files.

## Export/install behavior

Use a reproducible sync script with three commands:

```bash
python3 scripts/hermes_config_sync.py export
python3 scripts/hermes_config_sync.py verify
python3 scripts/hermes_config_sync.py install --dry-run
python3 scripts/hermes_config_sync.py install --apply
```

Implementation requirements:

1. `export` writes to a temp stage first, sanitizes copied text files, builds the manifest, scans for obvious token patterns, then atomically replaces the repo bundle while preserving a local `.backups/` copy of the old bundle.
2. `verify` checks manifest hashes and scans for obvious token patterns after removing the redaction marker from the scan text.
3. `install --dry-run` prints every managed target and performs no writes.
4. `install --apply` backs up overwritten target files/directories under `~/.hermes/backups/ai-configs-install-<timestamp>/`.
5. Config install should recursively merge YAML and skip redacted leaves so local secrets remain in `~/.hermes/config.yaml`.
6. Directory installs can replace managed source-like dirs such as `skills/`, `hooks/`, `plugins/`, `scripts/`, and `platforms/`; be explicit that runtime dirs are not managed.

## Pitfalls

- Do not copy the whole `~/.hermes` tree into git. The live tree can contain multi-GB sessions/state/checkpoints and secret-bearing files.
- Sanitizing YAML config is not enough: examples inside skill Markdown can contain token-shaped placeholder strings. Scan and redact copied text files too.
- Keep generated safety backups out of git, e.g. add `_hermes/.backups/` to `.gitignore`.
- After every Hermes configuration change, run `python3 scripts/hermes_config_sync.py export`, then `verify`, then commit and push the `~/code/ai-configs` changes before reporting the work complete.
- If an SSH push to GitHub fails but `gh auth status` shows a valid HTTPS-capable account, do not stop at the SSH failure; push the committed `main` update with an explicit HTTPS remote such as `git push https://github.com/<owner>/<repo>.git main`.
- Exclude generated/runtime-like skill/plugin state in addition to obvious Hermes runtime dirs: skill hub caches (`.hub/`, `index-cache/`), curator backups/state, `.usage.json`, plugin `state/`, `state.json`, and scanner snapshots such as `scan_*.json`.
- Do not include `manifest.json` in its own manifest hash list.
- If future source-first edits need to delete a config key, a merge-only installer will not remove it; add an explicit deletion manifest rather than relying on absence from the repo copy.
