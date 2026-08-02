---
name: cmd-create-pr
description: Create a GitHub pull request from the current branch using gh CLI. Use when ready to submit code for review.
---

# Create Pull Request

Create a GitHub PR for the current branch using `gh`.

## Usage

```
/skill:cmd-create-pr [BASE_REF]
```

If BASE_REF is omitted, prefers `origin/develop` if it exists; otherwise uses `origin/main`.

## Process

### 1) Resolve Base

Resolve `base_ref`:

- If arguments provided: use them
- Else use `origin/develop` if it exists
- Else use `origin/main`

Verify base exists:
```bash
git rev-parse --verify "${base_ref}^{commit}"
```

### 2) Check for Existing PR

```bash
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
gh pr list --head "$BRANCH" --json number,title,url --limit 1
```

If a PR already exists, report the URL and STOP.

### 3) Prepare Title and Evidence

If the current work is tied to a Linear issue, the PR title must start with the
Linear issue key and include the Linear issue title:

```text
NOD-632: Ccore health auth guidance
```

Resolve Linear context from the most reliable available source before falling
back to commit text:

- current branch name, if it contains a Linear key such as `NOD-632`
- plan or handoff files that name the Linear issue
- `thoughts/linear/<KEY>.md`
- the user request or issue URL used to start the work

Do not create a Linear-backed PR with only the commit subject as the title. If
you can identify the Linear key but not the issue title locally, inspect the
available Linear note or ask for the title before creating the PR.

```bash
# For Linear-backed work, set TITLE to "<KEY>: <Linear issue title>".
# For non-Linear work, the latest commit subject is acceptable.
TITLE="${TITLE:-$(git log -1 --format=%s)}"
git log --oneline "${base_ref}...HEAD"
git diff --stat "${base_ref}...HEAD"
```

### 4) Final Committed-Candidate Check

Run this after the final scoped commit and any rebase, not only against unstaged files:

```bash
MERGE_BASE="$(git merge-base "$base_ref" HEAD)"
git diff --check "$MERGE_BASE"..HEAD
git status --short
CHANGED="$(git diff --name-only "$MERGE_BASE"..HEAD)"
if [[ -n "$CHANGED" ]]; then
  rg -n "PR #TBD|TODO-PR|CHANGELOG_PLACEHOLDER" $CHANGED
fi
```

A placeholder hit, unclassified changed/untracked path, stale base, incomplete plan progress, or stale Doct source stops agent-default PR creation with the exact remediation. An operator may explicitly override the gate; disclose the real state rather than calling it clean.

### 5) Create PR

```bash
BASE_NAME="${base_ref#origin/}"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
# Use the Linear-aware title prepared in step 3.

gh pr create \
  --base "$BASE_NAME" \
  --head "$BRANCH" \
  --title "$TITLE" \
  --body "## Summary
- (fill from commits / plan)

## Verification
- (commands run)

## Notes
- (links / caveats)"
```

After creation, print the PR URL.

Note: squash-vs-merge is typically configured at merge time; `gh pr create` does not enforce squash on its own.
