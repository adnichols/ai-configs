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

1. **Read `_pi/workflows/heddle-release.js` as the authoritative step spec**, then execute its stages (cut → gate → build → publish) with the `herdr` CLI from a Herdr pane.
2. **Do not** reimplement release logic or invent a substitute pipeline. Do not run cut/build/publish yourself with ad-hoc bash outside the documented stage flow.
3. **Do not** skip the state directory: keep state in `~/.heddle-release/v{version}/` (outside the git worktree) so signed-release provenance stays clean.
4. If `_pi/workflows/heddle-release.js` is missing, stop and report; do not improvise a release.
5. Auto-resume from the newest in-flight train when progress exists.

## Parse args (in head)

| Key | Default |
|---|---|
| `dryRun` | false |
| `bump` | patch |
| `publishTarget` | none (local signed build only; set github or github-sparkle to publish) |
| `developRepo` | omit (auto: `~/code/heddle`, then `~/code/heddle-develop`) |
| `parentRepo` | omit (same as developRepo) |
| `worktreePath` | omit |
| `releaseVersion` | omit (from develop tip, or cwd release worktree) |
| `resumeFrom` | omit (`auto` if progress exists) |
| `slackChannel` | `#heddle-release` |
| `slackWorkspace` | nodaste |

## Launch

Omit `developRepo` / `parentRepo` unless the operator overrode them. The workflow auto-resolves `~/code/heddle` then `~/code/heddle-develop`. Use `herdr` CLI orchestration and the saved release scripts exactly as the workflow spec directs.

## After run

Summarize stages, `stateDir`, pkg path, publish/Slack, blockers.
