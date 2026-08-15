---
description: Create a GitHub pull request from the current branch
argument-hint: '[BASE_REF]'
---

# Create Pull Request

Create a GitHub PR for the current branch using `gh`.

## Authority boundary

PR authority is repository-bound. Create a PR only for the current task repository against its owner-approved integration remote. Never create, reopen, update, comment on, or coordinate a PR against a third-party repository from a fork without explicit operator permission naming that repository and action. Fork remotes, authentication, dependency work, and mandatory-PR workflow language do not imply permission. If ownership or target authority is uncertain, stop before any mutating `gh pr` command and ask.

## Input

Optional `BASE_REF`: `$ARGUMENTS`.

If omitted, prefer `origin/develop` if it exists; otherwise use `origin/main`.

## Process

### 0) Confirm repository authority

Identify the current task repository, remote owner, and intended PR target. If the target is a third-party repository or differs from the task repository's owner-approved integration remote, require explicit operator permission naming that repository and action. Without it, report the local/downstream branch or patch and stop.

### 1) Resolve Base

Resolve `base_ref`:

- If `$ARGUMENTS` provided: use it.
- Else:
  - Use `origin/develop` if it exists
  - Else use `origin/main`

Verify base exists:

```bash
git rev-parse --verify "${base_ref}^{commit}"
```

### 2) Resolve Head + Check Existing PR

```bash
BRANCH="$(git rev-parse --abbrev-ref HEAD)"

gh pr list --head "$BRANCH" --json number,title,url --limit 1
```

If a PR already exists, report the URL and STOP.

### 3) Prepare Title + Evidence

If this is Linear-backed work, resolve the Linear key from the branch name, commits, plan, or user-provided issue. Fetch the issue title before creating the PR:

```bash
ltui --format detail issues view "$ISSUE_KEY"
# Copy the exact title from the verified ltui output, then set:
LINEAR_ISSUE_TITLE="<Linear issue title from ltui output>"
TITLE="${ISSUE_KEY}: ${LINEAR_ISSUE_TITLE}"
```

For Linear-backed work, the PR title must be exactly shaped as:

```text
<ISSUE_KEY>: <Linear issue title>
```

Do not rely on the latest commit subject unless it already satisfies that format. For non-Linear work, use the latest commit subject or a concise plan-derived title.

```bash
if [ -n "${ISSUE_KEY:-}" ]; then
  # Linear-backed work must have set TITLE="${ISSUE_KEY}: ${LINEAR_ISSUE_TITLE}" above.
  : "${TITLE:?Set TITLE from the verified Linear issue title before creating the PR}"
else
  : "${TITLE:=$(git log -1 --format=%s)}"
fi

git log --oneline "${base_ref}...HEAD"
git diff --stat "${base_ref}...HEAD"
```

### 4) Create PR

```bash
# Ensure base_ref is set (if you didn't set it earlier, set it now).
if [ -n "$1" ]; then
  base_ref="$1"
elif git rev-parse --verify "origin/develop^{commit}" >/dev/null 2>&1; then
  base_ref="origin/develop"
else
  base_ref="origin/main"
fi

BASE_NAME="${base_ref#origin/}"
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
if [ -n "${ISSUE_KEY:-}" ]; then
  # Preserve the Linear-aware TITLE prepared from the verified ltui issue title.
  : "${TITLE:?Set TITLE from the verified Linear issue title before creating the PR}"
else
  : "${TITLE:=$(git log -1 --format=%s)}"
fi

gh pr create \
  --base "$BASE_NAME" \
  --head "$BRANCH" \
  --title "$TITLE" \
  --body "$(cat <<'EOF'
## Summary
- (fill from commits / plan)

## Verification
- (commands run)

## Notes
- (links / caveats)
EOF
)"
```

After creation, print the PR URL.

Note: squash-vs-merge is typically configured at merge time; `gh pr create` does not enforce squash on its own.
