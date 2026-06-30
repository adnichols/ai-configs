---
name: opencode-gated-pr-bundle-sync
description: Use when updating Aaron's portable OpenCode gated PR workflow bundle in hermes-configs, including safe push/export from the source Hermes profile and pull/import on another Hermes instance.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [hermes, bundle, sync, opencode, github, workflow]
    related_skills: [hermes-workflow-bundle, hermes-opencode-linear-build, opencode-http-coding-workflow, github-pr-workflow]
---

# OpenCode Gated PR Bundle Sync

## Overview

This skill keeps Aaron's portable OpenCode gated PR workflow bundle current across Hermes instances. The canonical bundle lives in the private `hermes-configs` repository and packages only portable Hermes-layer workflow artifacts: selected skills, helper scripts, policy, prompt templates, sanitized config guidance, and a manifest.

The bundle must be updated in two directions:

- **Push/export:** source Hermes profile changes are rebuilt into the repo bundle, verified, committed, and pushed when the human has asked for a sync.
- **Pull/import:** another Hermes instance pulls the repo, installs the bundled skills into its target Hermes home/profile, and starts a fresh session.

Do not rely on memory alone for this workflow. The build script and bundled skills are the source of truth that travels between machines.

## Canonical Paths

Aaron's current canonical repository path:

```text
~/code/hermes-configs
```

Bundle root inside the repo:

```text
opencode-gated-pr-workflow/
```

Important files:

```text
opencode-gated-pr-workflow/build/build_bundle.py
opencode-gated-pr-workflow/bundle/README.md
opencode-gated-pr-workflow/bundle/SPEC.md
opencode-gated-pr-workflow/bundle/manifest.json
opencode-gated-pr-workflow/bundle/scripts/install_bundle.py
```

Session-specific migration details for the OpenCode-owned Linear build conversion are in `references/opencode-linear-build-migration-2026-05.md`.

Default source Hermes profile on Aaron's machines:

```text
~/.hermes/profiles/nerd
```

The build script also honors `HERMES_HOME` and accepts `--hermes-home` for non-default profiles.

Known receiving-instance profile shapes:

- Aaron's Mac/source profile usually uses `~/.hermes/profiles/nerd`.
- `dever` currently installs bundled skills into the base Hermes home, `~/.hermes/skills/...`; it does not have `~/.hermes/profiles/nerd`.

Prefer `python3` on Linux/dever because `python` may not be installed.

## When to Use

Use this skill when the user asks to:

- update the OpenCode gated PR workflow bundle
- add a skill to the bundle
- sync the bundle from one machine to another
- push a refreshed bundle from the current Hermes profile
- pull/install the current bundle into another Hermes profile
- verify whether a receiving Hermes instance has current bundled workflow skills

Do not use this for general repo coding workflow execution. Use `hermes-opencode-linear-build` for current Linear-backed OpenCode PR work; `opencode-http-coding-workflow` is now a compatibility wrapper/HTTP helper.

## Push / Export Flow

Use this on the machine/profile where the current workflow skills were edited.

### 1. Check repository state

Work from the repo root:

```bash
git status --short
```

If the repo has unrelated local changes, stop and preserve them. Do not overwrite or clean them casually.

Check branch and remote:

```bash
git branch --show-current
```

```bash
git remote -v
```

The normal branch is `main`, and the normal remote is `origin` pointing at `adnichols/hermes-configs`.

### 2. Fast-forward before changing the bundle

Fetch first:

```bash
git fetch origin
```

If HTTPS GitHub auth fails under a Hermes/gateway process with an error like `could not read Username ... Device not configured`, retry through Aaron's login shell so `gh` credentials and the normal home directory are visible:

```bash
HOME=/Users/anichols zsh -lc 'git fetch origin'
```

If the working tree is clean, fast-forward only:

```bash
git pull --ff-only
```

Use the same login-shell wrapper for pull/push if needed:

```bash
HOME=/Users/anichols zsh -lc 'git pull --ff-only'
```

If `git pull --ff-only` refuses because local commits diverged, stop and inspect. Do not rebase, merge, or force push without explicit human approval.

### 3. Update source skills first

For skill content changes, identify the canonical source before editing. Most bundled skills are sourced from the active Hermes profile, usually:

```text
~/.hermes/profiles/nerd/skills/<category>/<skill-name>/SKILL.md
```

Some externally-authored/shared skills may live outside the profile tree first. For Aaron's current OpenCode Linear build workflow, the canonical source skill is:

```text
~/.agents/skills/hermes-opencode-linear-build/SKILL.md
```

When a user points out a canonical source path, copy or reconcile that source into the profile skill before rebuilding, then verify with `cmp -s <source> <profile-skill>` or an equivalent checksum. Do not overwrite the canonical source with an older profile copy.

If adding a new skill that should travel with the bundle, update `SELECTED_SKILLS` in:

```text
opencode-gated-pr-workflow/build/build_bundle.py
```

Use category-relative paths such as:

```python
"productivity/opencode-gated-pr-bundle-sync",
```

Generated files under `opencode-gated-pr-workflow/bundle/` should not be hand-edited except for emergency inspection. Change source skills or the build script, then rebuild.

### 4. Rebuild the bundle

From the repo root:

```bash
python opencode-gated-pr-workflow/build/build_bundle.py
```

For an explicit source profile:

```bash
python opencode-gated-pr-workflow/build/build_bundle.py --hermes-home ~/.hermes/profiles/nerd
```

The build moves the prior generated `bundle/` aside as `bundle.previous-<timestamp>/`, rewrites `bundle/`, regenerates `manifest.json`, and creates a `.tar.gz`. Previous bundles and tarballs are ignored by git.

### 5. Verify generated artifacts

Compile generated Python scripts:

```bash
python -m py_compile opencode-gated-pr-workflow/build/build_bundle.py opencode-gated-pr-workflow/bundle/scripts/install_bundle.py opencode-gated-pr-workflow/bundle/scripts/workflow_gate_check.py
```

Inspect the diff:

```bash
git diff --stat
```

Inspect tracked changes:

```bash
git diff -- opencode-gated-pr-workflow/bundle/README.md opencode-gated-pr-workflow/bundle/SPEC.md opencode-gated-pr-workflow/build/build_bundle.py
```

Confirm the new skill exists in the generated bundle if one was added:

```bash
test -f opencode-gated-pr-workflow/bundle/skills/productivity/opencode-gated-pr-bundle-sync/SKILL.md
```

Check the manifest mentions it:

```bash
grep -n "opencode-gated-pr-bundle-sync" opencode-gated-pr-workflow/bundle/manifest.json
```

Before committing, scan the diff for accidental secrets or host-only config. The bundle should never include `.env`, OAuth tokens, `auth.json`, sessions, channel IDs, raw gateway config, credential caches, or private request dumps.

### 6. Commit and push when requested

If the user asked to push/sync the bundle, stage the changed tracked files:

```bash
git add opencode-gated-pr-workflow/build/build_bundle.py opencode-gated-pr-workflow/bundle README.md
```

If `README.md` was not changed, omit it or use a focused path list from `git status --short`.

Commit with a clear message:

```bash
git commit -m "chore: update OpenCode workflow bundle"
```

Push:

```bash
git push origin main
```

If HTTPS GitHub auth fails from Hermes/gateway, use Aaron's login shell wrapper:

```bash
HOME=/Users/anichols zsh -lc 'git push origin main'
```

If the user only asked to prepare the bundle and did not ask to push, stop after verification and report the local diff/commit state.

## Pull / Import Flow

Use this on a receiving Hermes instance that should adopt the current bundle.

### 1. Get the repo

If `~/code/hermes-configs` already exists, work there:

```bash
git status --short
```

Fetch and fast-forward only:

```bash
git fetch origin
```

```bash
git pull --ff-only
```

If HTTPS GitHub auth fails under Hermes/gateway, use the login-shell wrapper:

```bash
HOME=/Users/anichols zsh -lc 'git fetch origin'
```

```bash
HOME=/Users/anichols zsh -lc 'git pull --ff-only'
```

If the repo is missing, clone it into the normal code directory:

```bash
git clone https://github.com/adnichols/hermes-configs.git ~/code/hermes-configs
```

### 2. Inspect the received bundle

From the repo root:

```bash
python3 -m py_compile opencode-gated-pr-workflow/bundle/scripts/install_bundle.py opencode-gated-pr-workflow/bundle/scripts/workflow_gate_check.py
```

Use `python3`; on dever `python` may not exist.

Check the manifest exists:

```bash
test -f opencode-gated-pr-workflow/bundle/manifest.json
```

Optionally inspect selected skills:

```bash
grep -n "selected_skills" opencode-gated-pr-workflow/bundle/manifest.json
```

### 3. Install into the target Hermes home/profile

For the base Hermes home, used by `dever`:

```bash
python3 opencode-gated-pr-workflow/bundle/scripts/install_bundle.py --target-hermes-home ~/.hermes
```

For Aaron's `nerd` profile on macOS/source machines:

```bash
python3 opencode-gated-pr-workflow/bundle/scripts/install_bundle.py --target-hermes-home ~/.hermes/profiles/nerd
```

The installer skips existing skills by default. To replace existing target skills with bundled versions, use `--overwrite`; it backs up each replaced skill directory as `<skill>.pre-bundle-backup` and refuses to proceed if that backup already exists.

```bash
python3 opencode-gated-pr-workflow/bundle/scripts/install_bundle.py --target-hermes-home ~/.hermes --overwrite
```

If backup conflicts exist and the user has explicitly asked to sync/update the receiving instance, preserve the existing backups by timestamp-renaming them, then rerun install. Do not delete them.

```bash
ssh dever 'bash -lc '\''ts=$(date -u +%Y%m%dT%H%M%SZ); for d in ~/.hermes/skills/*/*.pre-bundle-backup; do if [ -e "$d" ]; then echo "preserve $d -> $d.$ts"; mv "$d" "$d.$ts"; fi; done'\'''
ssh dever 'cd ~/code/hermes-configs && python3 opencode-gated-pr-workflow/bundle/scripts/install_bundle.py --target-hermes-home ~/.hermes --overwrite'
```

If the user did not authorize overwrite/sync, stop at the conflict and ask.

### 4. Verify the installed bundle

On the receiving instance, verify the repo commit, clean state, script syntax, and skill path resolution:

```bash
ssh dever 'cd ~/code/hermes-configs && git rev-parse --short HEAD && git status --short'
ssh dever 'python3 -m py_compile ~/code/hermes-configs/opencode-gated-pr-workflow/bundle/scripts/install_bundle.py ~/code/hermes-configs/opencode-gated-pr-workflow/bundle/scripts/workflow_gate_check.py ~/.hermes/skills/productivity/opencode-http-coding-workflow/scripts/opencode_http.py'
ssh dever 'test -f ~/.hermes/skills/productivity/hermes-opencode-linear-build/SKILL.md && test -f ~/.hermes/skills/productivity/opencode-http-coding-workflow/scripts/opencode_http.py && echo bundled-opencode-linear-build-installed'
```

If a bundled workflow skill contains command examples, make them path-portable through `OPENCODE_WORKFLOW_SKILL_DIR` rather than hardcoding `~/.hermes/profiles/nerd`; otherwise receiving hosts like dever will install correctly but the examples will point at nonexistent paths.

### 5. Start fresh and verify skill loading

After installing skills, start a fresh Hermes session or reset the current one so the skill index refreshes. Load the workflow skill explicitly:

```text
/skill hermes-opencode-linear-build
/skill opencode-http-coding-workflow
```

For future bundle maintenance, also load:

```text
/skill opencode-gated-pr-bundle-sync
```

## Bidirectional Sync Pattern

When a receiving machine improves a bundled skill, that machine temporarily becomes the source:

1. Update the source skill in its active Hermes profile.
2. Add the skill to `SELECTED_SKILLS` if it is new to the bundle.
3. Run the push/export flow.
4. Commit and push to `origin/main` when authorized.
5. Other machines run the pull/import flow.

Avoid editing `bundle/skills/...` directly because those edits are overwritten on the next rebuild. If you discover a needed fix while inspecting bundled output, apply the fix to the source profile skill or build script, then rebuild.

## Common Pitfalls

1. **Forgetting to add a new skill to `SELECTED_SKILLS`.** The local skill can exist and still not travel. Always check `bundle/manifest.json` after rebuild.

2. **Installing without `--overwrite` and thinking the target updated.** The installer skips existing skills by default. Use `--overwrite` when the target profile must adopt the bundled version.

3. **Editing generated bundle files.** Rebuild will overwrite direct edits under `bundle/`. Change source skills or `build_bundle.py` instead.

4. **Using merges for config sync.** This repo should usually fast-forward cleanly. If it does not, stop and inspect rather than creating merge commits casually.

5. **Leaking local runtime state.** Never add `.env`, `auth.json`, session transcripts, credential caches, gateway routing, or machine-specific config dumps.

6. **GitHub HTTPS auth unavailable in gateway context.** If `git fetch`, `git pull`, or `git push` fails with `could not read Username ... Device not configured`, retry with `HOME=/Users/anichols zsh -lc '<git command>'` so the process can see Aaron's normal `gh` credential setup.

7. **Assuming source-profile paths work everywhere.** The source Mac may use `~/.hermes/profiles/nerd`, while dever uses base `~/.hermes`. Bundle docs and helper examples should use `OPENCODE_WORKFLOW_SKILL_DIR` with a fallback from the nerd profile to base `~/.hermes/skills/...`.

8. **Using `python` on dever.** Use `python3` for install/verify commands on dever; `python` can be absent.

9. **Reinstall blocked by existing `.pre-bundle-backup`.** Preserve old backups with a timestamp suffix before rerunning `--overwrite`; never delete them as a cleanup shortcut.

## Verification Checklist

- [ ] Repo is on intended branch and remote.
- [ ] Pull/import used `git pull --ff-only`, not a casual merge.
- [ ] Push/export rebuilt via `build/build_bundle.py`.
- [ ] New bundled skills are listed in `SELECTED_SKILLS` and present under `bundle/skills/...`.
- [ ] `manifest.json` was regenerated and mentions the expected files.
- [ ] Generated Python scripts compile.
- [ ] Diff was inspected for secrets and host-specific runtime state.
- [ ] Commit/push happened only when requested or clearly within the user's sync instruction.
- [ ] GitHub HTTPS auth worked, or failed commands were retried through `HOME=/Users/anichols zsh -lc '<git command>'`.
- [ ] Receiving instance installed into the intended Hermes home/profile and started a fresh session.
