---
name: pi-pr-finalization-fallbacks
description: Fallbacks for finishing Aaron's pi coding workflow when commit-plan path matching or GitHub PR creation/check handling behaves unexpectedly.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [pi, github, pull-request, workflow, fallback, tmux]
    related_skills: [pi-coding-workflow, github-pr-workflow, tmux-scoped-pi-control]
---

# Pi PR Finalization Fallbacks

Use this when running Aaron's `pi-coding-workflow` and the work is done, but plan commit / PR creation / post-PR follow-up hit orchestration quirks.

## 1. `pi_workflow_ctl.py --stage commit-plan` dirty-tree false positive

Symptom:
- `commit-plan` fails with `refusing commit-plan with unexpected dirty tree`
- repo status only shows the expected plan file

Cause:
- On Aaron's machine, the controller's allowlist compares against repo-relative `git status` paths.
- Passing `--plan` as an absolute path can mismatch the dirty-tree allowlist.

Fix:
- Retry `commit-plan` with a repo-relative plan path, e.g.

```bash
python3 ~/.hermes/scripts/pi_workflow_ctl.py \
  --pane %PANE \
  --repo ~/code/<worktree> \
  --plan thoughts/plans/<slug>.md \
  --stage commit-plan
```

Do not assume the tree is actually dirty until you confirm with `git status --short`.

## 2. `pm-plan` / controller stage drift after forced commit-plan

Symptom:
- after a forced or out-of-band `commit-plan`, controller says the next legal stage is wrong

Fix:
- ground truth from the pane tail and state file
- if the worker already completed PM plan review and is ready for execution, use:

```bash
python3 ~/.hermes/scripts/pi_workflow_ctl.py \
  --pane %PANE \
  --repo ~/code/<worktree> \
  --plan thoughts/plans/<slug>.md \
  --stage execute --force
```

Only do this when the pane clearly shows the preceding stage already happened.

## 3. `gh pr create` timeout fallback

Symptom:
- `gh pr create` or controller `create-pr` times out even though auth and branch state are fine
- PR may still not exist afterward

Reliable fallback:
1. Check whether a PR already exists:
```bash
gh pr list --head <branch> --json number,title,url,state
```
2. If none exists, create via direct API with explicit owner-qualified head:
```bash
GH_DEBUG=api gh api -X POST repos/<owner>/<repo>/pulls \
  --field title='...' \
  --field head='<owner>:<branch>' \
  --field base='main'
```
3. If you used a minimal/debug body to get creation through, patch the PR afterward:
```bash
gh api -X PATCH repos/<owner>/<repo>/pulls/<number> --field title='...'
gh pr edit <number> --body-file <body-file>
```

Notes:
- In this environment, large body payloads can be the part that hangs.
- A minimal create followed by `gh pr edit --body-file` is safer than repeatedly retrying timed-out creates.

## 4. Post-PR check failures caused by billing, not code

Symptom:
- all Actions jobs fail almost instantly
- `gh pr checks` shows every job failed
- `gh run view <run-id>` annotation says jobs were not started because payments failed or spending limit needs to be increased

Interpretation:
- this is an external GitHub billing blocker, not a code regression

Workflow:
1. Confirm with:
```bash
gh run view <run-id>
```
2. Leave a PR comment summarizing:
- checks did not start
- reason is billing/spending-limit block
- local validation for the scoped change is green
- no code-side CI fix is available until billing is restored

## 5. Keep local-only artifacts out of the commit

Before final commit/PR, explicitly verify whether these are local-only:
- `.pi/`
- ad hoc validation reports under `thoughts/validation/`

If they are only workflow artifacts for the current run, do not include them unless the repo explicitly wants them.

## Quick checklist

- [ ] Use repo-relative `--plan` for `commit-plan`
- [ ] If controller stage lags reality, confirm from pane then use `--force` carefully
- [ ] If `gh pr create` hangs, check for existing PR first, then use `gh api` create + `gh pr edit`
- [ ] Distinguish billing-blocked Actions from real CI failures
- [ ] Exclude `.pi/` and ad hoc validation notes unless intentionally tracked
