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

1. Read `_pi/workflows/heddle-release.js` as the authoritative step spec and resume with `resumeFrom: "auto"` semantics.
2. Prefer launching **from inside the release worktree** — version + progress auto-detect.
3. Do not use develop tip for version (already bumped after cut).
4. Do not reimplement release logic or run manual release bash.

## Args

Resume from the newest in-flight train, auto. Optional: `releaseVersion`, `worktreePath`, `publishTarget`, `dryRun`.

Bare semver → releaseVersion. Path → worktreePath.

## Progress

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
