---
name: github
description: "Full GitHub workflow: authenticate, manage repositories, open and review PRs, triage issues, run CI, and cut releases."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [GitHub, git, PR, CI/CD, code-review, issues, repositories, releases]
    related_skills: [requesting-code-review]
---

# GitHub Workflows

Complete guide for working with GitHub via `gh` CLI (preferred) or `git` + `curl` fallback. Covers authentication, repository management, the PR lifecycle, code review, issue triage, CI monitoring, and releases.

## Auth Detection Pattern

Every section below assumes this preamble has run:

```bash
if command -v gh &>/dev/null && gh auth status &>/dev/null; then
  AUTH="gh"
else
  AUTH="git"
  if [ -z "$GITHUB_TOKEN" ]; then
    if [ -f ~/.hermes/.env ] && grep -q "^GITHUB_TOKEN=" ~/.hermes/.env; then
      GITHUB_TOKEN=$(grep "^GITHUB_TOKEN=" ~/.hermes/.env | head -1 | cut -d= -f2 | tr -d '\n\r')
    elif grep -q "github.com" ~/.git-credentials 2>/dev/null; then
      GITHUB_TOKEN=$(grep "github.com" ~/.git-credentials 2>/dev/null | head -1 | sed 's|https://[^:]*:\([^@]*\)@.*|\1|')
    fi
  fi
fi

REMOTE_URL=$(git remote get-url origin)
OWNER_REPO=$(echo "$REMOTE_URL" | sed -E 's|.*github\.com[:/]||; s|\.git$||')
OWNER=$(echo "$OWNER_REPO" | cut -d/ -f1)
REPO=$(echo "$OWNER_REPO" | cut -d/ -f2)
```

## Authentication

### Git-Only (No gh, No sudo)
**HTTPS with Personal Access Token (Recommended):**
1. User creates token at https://github.com/settings/tokens (scopes: `repo`, `workflow`, `read:org`)
2. `git config --global credential.helper store`
3. `git ls-remote https://github.com/<user>/<repo>.git` → enter token as password
4. `git config --global user.name "..." && git config --global user.email "..."`

**SSH Key:**
1. `ssh-keygen -t ed25519 -C "..."`
2. Add public key to https://github.com/settings/keys
3. `git config --global url."git@github.com:".insteadOf "https://github.com/"`

### gh CLI
```bash
gh auth login                  # Browser (desktop)
echo "<TOKEN>" | gh auth login --with-token   # Headless
gh auth setup-git
gh auth status
```

## Repository Management

### Clone / Create / Fork
```bash
git clone https://github.com/owner/repo.git    # Pure git
gh repo clone owner/repo                      # gh shorthand
gh repo create my-project --public --clone    # Create + clone
gh repo fork owner/repo --clone               # Fork + clone
```

### Settings & Branch Protection
```bash
gh repo edit --description "..." --add-topic "ml,python"
```

### Secrets
```bash
gh secret set API_KEY --body "value"
gh secret list
```

### Releases
```bash
gh release create v1.0.0 --title "v1.0.0" --generate-notes
gh release list
gh release download v1.0.0 --dir ./downloads
```

## Pull Request Lifecycle

### Branch and Commit
```bash
git checkout -b feat/description
git add ...
git commit -m "feat: concise description"
git push -u origin HEAD
```

### Create PR
**gh:**
```bash
gh pr create --title "feat: ..." --body "## Summary\n...\nCloses #42"
```

**curl:**
```bash
curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls \
  -d '{"title":"...","body":"...","head":"branch","base":"main"}'
```

### Monitor CI
```bash
gh pr checks --watch           # Poll until finish
```

### Merge
```bash
gh pr merge --squash --delete-branch
gh pr merge --auto --squash --delete-branch   # Auto-merge when green
```

## Code Review

### Local Changes (Pre-Push)
```bash
git diff main...HEAD --stat
git diff main...HEAD | grep -n "TODO\|FIXME\|debugger\|console\.log"
```

Present findings as: Critical / Warnings / Suggestions / Looks Good.

### Review a GitHub PR
```bash
gh pr view 123
gh pr diff 123
git fetch origin pull/123/head:pr-123 && git checkout pr-123   # Local checkout
```

### Inline Comments
**gh:**
```bash
gh pr review 123 --request-changes --body "See inline comments."
```

**curl (atomic multi-comment):**
```bash
HEAD_SHA=$(curl -s -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/123 | \
  python3 -c "import sys,json; print(json.load(sys.stdin)['head']['sha'])")

curl -s -X POST -H "Authorization: token $GITHUB_TOKEN" \
  https://api.github.com/repos/$OWNER/$REPO/pulls/123/reviews \
  -d "{\"commit_id\":\"$HEAD_SHA\",\"event\":\"REQUEST_CHANGES\",\"body\":\"...\",\"comments\":[...]}"
```

Event values: `"APPROVE"`, `"REQUEST_CHANGES"`, `"COMMENT"`.

## Issues

### View / Create / Manage
```bash
gh issue list --label bug
gh issue create --title "..." --body "..." --label "bug"
gh issue edit 42 --add-label "priority:high"
gh issue close 42 --reason "not planned"
```

### Bulk Operations
```bash
gh issue list --label wontfix --json number --jq '.[].number' | \
  xargs -I {} gh issue close {} --reason "not planned"
```

## GitHub Actions

```bash
gh workflow list
gh run list --limit 10
gh run view <RUN_ID> --log-failed
gh run rerun <RUN_ID> --failed
gh workflow run ci.yml --ref main
```

## Gists

```bash
gh gist create script.py --public --desc "Useful script"
gh gist list
```
