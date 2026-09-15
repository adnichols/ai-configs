## Golden rule: doct-agent only

Every doct operation goes through the `doct-agent` CLI on PATH. Do **not** use `doct-cli`, raw `curl`/REST calls, hand-written Hocuspocus/Yjs scripts, local wrapper scripts, or token-store fallbacks. `doct-agent` wraps REST for discovery, reads, creation, plan registration, metadata, and Yjs/Hocuspocus-safe edits/comments — with verified readback where supported. If a task seems to need raw REST or a custom Yjs script, you are on the wrong path: find the matching `doct-agent` subcommand or run `doct-agent onboard`.

- **Install/update via Homebrew only.** From the doct repo root: `brew tap local/doct "$(pwd)"` then `brew install --build-from-source local/doct/doct-agent`. Refresh with `brew reinstall --build-from-source local/doct/doct-agent`.
- Most discovery and mutation commands accept `--json`.
- `references/doct-agent-commands.md` is the local command reference. `doct-agent onboard` prints the canonical, always-current spec from the installed CLI — consult it if anything here looks stale.

## Auth and endpoint

Production Doct is the default target for plan registration:

```bash
https://doct.nodaste.com
```

Check first:

```bash
doct-agent auth status --all --json
doct-agent context --base-url https://doct.nodaste.com --json
```

If production is authenticated but not default, either pass `--base-url https://doct.nodaste.com` on every command or set it:

```bash
doct-agent auth default --base-url https://doct.nodaste.com
```

If not authenticated:

1. Ask the doct owner to generate and approve a selected-agent enrollment code.
2. `doct-agent auth login --base-url https://doct.nodaste.com` (develop: `https://doct.develop.nodaste.com`).
3. Paste the enrollment code when prompted, or pass `--enrollment-code <code>`.
4. Fallback: `doct-agent auth import-pat --base-url <url> --token <doct_pat_v1_...>`.

The CLI discovers and stores the collaboration websocket URL after auth; pass `--websocket-url` only to override. For one-off automation, `DOCT_AGENT_PAT` overrides the stored token only when paired with an explicit `--base-url`.

## Resolve the target first

Accept any of: a full doct URL, document id, workspace + path/title, or registered plan URL/id.

- Doct document URLs look like `https://doct.nodaste.com/d/<workspace-handle>/docs/<document-id>` — parse `<document-id>` from `/docs/<uuid>`, then use `doct-agent documents get --id <id>` or `doct-agent plans show --id <id>` for plan artifacts.
- Discover with `doct-agent workspaces list --base-url https://doct.nodaste.com --json`, then `doct-agent documents list --workspace-id <id> --json`.
- If still ambiguous, ask for exactly one missing locator: document URL, document/plan id, or workspace + path.
