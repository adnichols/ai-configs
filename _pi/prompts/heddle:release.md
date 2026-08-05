---
description: Cut a Heddle release in a Herdr worktree (auto-resumes from on-disk progress)
argument-hint: "[dryRun] [bump=patch|minor|major] [publishTarget=none|github|github-sparkle] [key=value...]"
---

# Heddle release

Run the saved Heddle release workflow **now**:

```text
$ARGUMENTS
```

## Hard rules

1. **Invoke the `workflow` tool immediately** after parsing args.
2. **Do not** call `workflow_catalog` for `shell`, `parallel`, `agent`, etc.
3. **Do not** read or reimplement the workflow script.
4. **Do not** run cut/build/publish yourself with ad-hoc bash.
5. If the script file is missing, copy `_pi/workflows/heddle-release.js` → `~/.pi/agent/workflows/` once and retry.

## Parse args (in head)

| Key | Default |
|---|---|
| `dryRun` | false |
| `bump` | patch |
| `publishTarget` | none (local signed build only; set github or github-sparkle to publish) |
| `developRepo` | `/Users/anichols/code/heddle-develop` |
| `parentRepo` | same as developRepo |
| `worktreePath` | omit |
| `releaseVersion` | omit (from develop tip, or cwd release worktree) |
| `resumeFrom` | omit (`auto` if progress exists) |
| `slackChannel` | `#heddle-release` |
| `slackWorkspace` | nodaste |
| `agentKind` | pi |

## Launch

```text
workflow
  name: heddle-release
  scriptPath: /Users/anichols/.pi/agent/workflows/heddle-release.js
  args: { ...parsed }
  foreground: true
```

State lives in `~/.heddle-release/v{version}/` (outside the git worktree) so signed provenance stays clean.

## After run

Summarize stages, `stateDir`, pkg path, publish/Slack, blockers.
