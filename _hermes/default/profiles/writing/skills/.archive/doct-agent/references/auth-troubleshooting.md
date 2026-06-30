# doct-agent Auth Troubleshooting

## Symptom
`doct-agent auth status` returns `no local authentication found` even after a previous successful login.

## macOS Config Locations

| Tool / version | Config path |
|---|---|
| Legacy `doct-cli` | `~/.config/doct-cli/config.json` |
| Current `doct-agent` | `~/Library/Application Support/dev.doct.doct-agent/config.json` + `pat` file |

Do not confuse the two. The legacy CLI token is separate and will fail PAT validation in `doct-agent`.

## Recovery Steps

1. Check the current auth storage:
   ```bash
   ls ~/Library/Application\ Support/dev.doct.doct-agent/
   # should show: config.json  pat
   ```

2. Read the token from the `pat` file:
   ```bash
   cat ~/Library/Application\ Support/dev.doct.doct-agent/pat
   ```

3. Re-import it:
   ```bash
   doct-agent auth import-pat \
     --base-url "https://doct.nodaste.com" \
     --websocket-url "wss://p.doct.nodaste.com" \
     --token "<token-from-pat-file>"
   ```

4. Verify:
   ```bash
   doct-agent auth status
   ```

## Note on `--websocket-url`
Some commands (e.g. `collab edit`, `collab anchored`) require a websocket URL. If it was not configured during initial login, import-pat with `--websocket-url` ensures collaborative commands work without extra flags.