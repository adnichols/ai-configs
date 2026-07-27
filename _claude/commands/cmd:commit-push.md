---
description: Commit all changes in the repo and push to GitHub
argument-hint: '["commit subject"]'
---

# Commit + Push (All Changes)

Commit ALL current working tree changes on the current branch and push to the tracked remote.

## Input

Optional commit subject: `$ARGUMENTS`.

If omitted, generate a default from the branch name (and an inferred Linear issue key if present).

## Preconditions

1) Must not be on a protected branch:

```bash
git rev-parse --abbrev-ref HEAD
```

If on `main`, `master`, or `develop`, STOP and ask the user to switch to a feature branch.

2) Must have something to commit:

```bash
git status --porcelain=v1
```

If empty, STOP (nothing to do).

3) Secret hygiene (conservative):

If `git status` includes files matching `.env*`, `*.pem`, `*.key`, `credentials*.json`, or `*.p12`, STOP and ask before staging.

## Process

### 1) Stage Everything

Use `git-with-index-lock` for index-mutating commands so stale/contended `.git/index.lock` is recovered automatically (retry, wait for live holders, clear only unheld locks).

Bootstrap if the command is missing (new host / empty PATH):

```bash
ENSURE="$(command -v ensure-git-with-index-lock 2>/dev/null || true)"
if [[ -z "$ENSURE" && -n "${AI_CONFIGS_ROOT:-}" && -x "${AI_CONFIGS_ROOT}/scripts/ensure-git-with-index-lock" ]]; then
  ENSURE="${AI_CONFIGS_ROOT}/scripts/ensure-git-with-index-lock"
fi
TOP="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [[ -z "$ENSURE" && -n "$TOP" && -x "$TOP/scripts/ensure-git-with-index-lock" ]]; then
  ENSURE="$TOP/scripts/ensure-git-with-index-lock"
fi
if [[ -z "$ENSURE" ]]; then
  echo "git-with-index-lock bootstrap unavailable: set AI_CONFIGS_ROOT or run ai-configs install.sh" >&2
  exit 1
fi
GIT_WL="$("$ENSURE")" || exit 1
"$GIT_WL" add -A
git diff --cached --stat
```

Do not fall back to raw index-mutating `git`.

### 2) Build Commit Subject

If `$ARGUMENTS` provided, use it.

Else generate:

```bash
BRANCH="$(git rev-parse --abbrev-ref HEAD)"
ISSUE_KEY="$(python3 -c 'import re,sys; b=sys.argv[1]; m=re.search(r"([A-Za-z]+-\\d+)", b); print(m.group(1).upper() if m else "")' "$BRANCH")"

if [ -n "$ISSUE_KEY" ]; then
  COMMIT_SUBJECT="feat: ${ISSUE_KEY} ${BRANCH}"
else
  COMMIT_SUBJECT="feat: ${BRANCH}"
fi
```

### 3) Commit

```bash
"$GIT_WL" commit -m "$COMMIT_SUBJECT"
```

If commit fails due to hooks, fix issues and create a NEW commit (do not amend unless explicitly requested).

### 4) Push

```bash
BRANCH="$(git rev-parse --abbrev-ref HEAD)"

if git rev-parse --abbrev-ref --symbolic-full-name "@{u}" >/dev/null 2>&1; then
  git push
else
  git push -u origin "$BRANCH"
fi
```

### 5) Output

Report:

- Branch name
- Commit SHA (`git rev-parse HEAD`)
- Remote tracking status (`git status -sb`)
