---
name: cmd-create-pr
description: Create a GitHub pull request from the current branch using gh CLI. Use when ready to submit code for review.
---

# Create Pull Request

Create a GitHub PR for the current branch using `gh`.

## Authority boundary

PR authority is repository-bound. This skill may create a PR only for the current task repository against its owner-approved integration remote. Never use it to create, reopen, update, comment on, or coordinate a PR against a third-party repository from a fork unless the operator explicitly authorizes that exact repository and action. A local checkout, fork remote, authenticated account, dependency patch, or another workflow's mandatory-PR instruction is not authorization. If repository ownership or target authority is uncertain, stop before any `gh` mutation and ask.

## Usage

```
/skill:cmd-create-pr [BASE_REF]
```

If BASE_REF is omitted, prefers `origin/develop` if it exists; otherwise uses `origin/main`.

## Process

### 0) Confirm repository authority

Before inspecting or mutating PR state, identify the current task repository, remote owner, and intended PR target. If the target is a third-party repository or differs from the task repository's owner-approved integration remote, require explicit operator permission naming that repository and action. Without it, do not run mutating `gh pr` commands; report the local/downstream branch or patch instead.

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

### 4b) Permanent documentation disposition (Heddle / local permanent-docs)

When the repo has `.agents/skills/heddle-permanent-docs/SKILL.md`, `docs/DEV_DOCUMENTATION_ARCHIVE.md`, or `changelog/unreleased/README.md` (or another repo-local `*-permanent-docs` skill), load that skill and hard-stop agent-default PR creation unless:

- exactly one disposition is recorded: `none` | `patch` | `new-record` | `ADR` | `deferred-to-final-plan-slice`;
- for `patch` / `new-record` / `ADR`, every claimed path exists in `$CHANGED`;
- for `deferred-to-final-plan-slice`, a final slice/issue and interim source of truth are named;
- the PR body will include a **Permanent documentation** section (or an explicit operator waiver is disclosed);
- the body does not claim a verified `graduated-plan/...` archive receipt when none exists.

Do not require CCore archive package creation or plan-source deletion. Changelog fragment rules remain the separate existing gate.

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

## Permanent documentation
- Disposition: none | patch | new-record | ADR | deferred-to-final-plan-slice
- Reason / final slice: ...
- Specs or docs updated: ...
- Changelog fragment: ...
- Plan source retained: ...
- Archive: post-merge only (not in this PR)

## Notes
- (links / caveats)"
```

After creation, print the PR URL.

Note: squash-vs-merge is typically configured at merge time; `gh pr create` does not enforce squash on its own.
