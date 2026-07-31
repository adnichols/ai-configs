---
description: Resume Heddle release from last successful stage (auto-detects progress)
argument-hint: "[optional version or path] [publishTarget=...]"
---

# Heddle release resume

Resume from **whatever already succeeded** on disk.

```text
$ARGUMENTS
```

## Hard rules

1. Call **`workflow` immediately** with `resumeFrom: "auto"`.
2. Prefer launching **from inside the release worktree** — version + progress auto-detect.
3. Do not use develop tip for version (already bumped after cut).
4. No `workflow_catalog` for builtins; no manual release bash.

## Args

Always set `resumeFrom: "auto"`. Optional: `releaseVersion`, `worktreePath`, `publishTarget`, `dryRun`.

Bare semver → releaseVersion. Path → worktreePath.

## Launch

```text
workflow
  name: heddle-release
  scriptPath: /Users/anichols/.pi/agent/workflows/heddle-release.js
  args: { resumeFrom: "auto", ... }
  foreground: true
```

Progress files: `~/.heddle-release/v{version}/{cut,gate,build,publish,progress}.json`

| Present | Next |
|---|---|
| cut ready | gate (or skip if open) |
| + gate open | build |
| + build ok | publish |
| + publish done | nothing |

## Examples

```text
# cwd = release-v0.3.3 worktree
/heddle:release-resume

/heddle:release-resume 0.3.3
/heddle:release-resume publishTarget=github
```
