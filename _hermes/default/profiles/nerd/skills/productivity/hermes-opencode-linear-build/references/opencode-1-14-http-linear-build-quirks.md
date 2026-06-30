# OpenCode 1.14 HTTP Linear build quirks observed during NOD-533

Date observed: 2026-05-08, OpenCode `1.14.40`.

## Session creation permissions

`POST /session` rejects the older map form:

```json
{"permission":{"edit":"allow","bash":"allow","webfetch":"allow"}}
```

Error shape:

```json
{"error":[{"expected":"array","code":"invalid_type","path":["permission"],"message":"Invalid input: expected array, received object"}]}
```

Use an array instead:

```json
{
  "title": "Linear build NOD-533",
  "agent": "build",
  "permission": [
    {"permission":"edit","action":"allow","pattern":"*"},
    {"permission":"bash","action":"allow","pattern":"*"},
    {"permission":"webfetch","action":"allow","pattern":"*"}
  ]
}
```

## `prompt_async` success is `204 No Content`

For `/session/{id}/prompt_async`, `204 No Content` is a successful async launch. Do not fall back to `/message` after a 204. Falling back can duplicate the prompt and create confusing extra user messages or delegated subtasks.

## Slash command over HTTP may be handled as chat by the agent

Posting `/cmd:linear-build-workspace ...` via HTTP did not directly expand the command in-session; the agent read the command file and proceeded manually/delegated via Task. Monitor the ledger/workspace, not the text response. If the agent starts using the older `cmd-start-linear-issue` flow, nudge it back to the `cmd:linear-build-workspace` command file and helper/ledger.

## Shell-quoting hazard in generated commands

Linear issue titles may contain backticks, e.g. `` `hub_account_auth.access_token_enc` ``. If OpenCode constructs a shell command with `--title "..."`, zsh will execute backtick content before Python receives the argument. Safer patterns:

- pass title through a Python subprocess argument list, not a shell string;
- read title from the captured JSON inside Python;
- or single-quote with proper escaping if shell is unavoidable.

If the title was mangled in the workspace `extra.issueTitle`, the ledger can still be corrected from `ltui issues view` before continuing.

## Monitoring

The useful source of truth remained the ledger status:

```bash
HOME=/Users/anichols python3 /Users/anichols/.config/opencode/scripts/linear_build_orchestrator.py status \
  --ledger /path/to/workspace/thoughts/runs/nod-533*.md
```

When Hermes launches a long build from Discord, a quiet `no_agent` cron watchdog that reports only terminal/blocking/stalled states keeps the channel clean while preserving liveness monitoring.
