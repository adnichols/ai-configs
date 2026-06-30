---
name: github-deployment-change-audit
description: Audit a GitHub repo's recent deployments and summarize functional merged changes, excluding docs-only PRs.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [GitHub, Deployments, Changelog, Audit, PRs]
    related_skills: [github-code-review]
---

# GitHub Deployment Change Audit

Use this when the user wants a concise summary of what functionally changed in a GitHub repository over a recent window (for example, last 24 hours), grounded in both deployment history and merged PRs.

## When to use
- "What changed in deployments in the last day?"
- "What functional changes were merged recently?"
- Daily/recurring repo health or changelog briefs
- "Tell me what is live right now and what was reverted"

## Core approach

### 1. Prefer GitHub API/gh over browser pages
The `/deployments` page may return a 404 or login wall when accessed unauthenticated in the browser. Prefer `gh api` for deployments and PR metadata.

Repository examples below use `NousResearch/hermes-agent`.

### 2. Get the current time and define the window
Always ground the time window with a live clock.

```bash
date -u '+%Y-%m-%dT%H:%M:%SZ'
date '+%Y-%m-%d %H:%M:%S %Z'
```

Use the first timestamp as `now`, then compute the cutoff (commonly 24h earlier).

### 3. Fetch recent deployments
```bash
gh api repos/OWNER/REPO/deployments?per_page=30
```

For each deployment in the time window, also fetch statuses:

```bash
gh api repos/OWNER/REPO/deployments/DEPLOYMENT_ID/statuses?per_page=5
```

Interpretation:
- `success` = current active/latest successful deployment
- `inactive` = older superseded deployment
- lack of failures in statuses usually means there were no failed deployments in the window

Report:
- number of deployments in window
- latest/currently active deployment SHA and timestamp
- coarse status counts (`success`, `inactive`, failures if present)

### 4. Fetch merged PRs in the same window
Use GraphQL for merged PR discovery:

```bash
gh api graphql -f query='query {
  repository(owner:"OWNER", name:"REPO") {
    pullRequests(first: 50, states: MERGED, orderBy: {field: UPDATED_AT, direction: DESC}) {
      nodes {
        number
        title
        mergedAt
        url
        author { login }
        mergeCommit { oid }
      }
    }
  }
}'
```

Filter locally to PRs with `mergedAt >= cutoff`.

Then fetch changed files per PR:

```bash
gh pr view PR_NUMBER --json files
```

Important: also check for **direct commits on `main` in the same window** so you don't miss non-PR changes or repo-maintenance noise that should be explicitly excluded. Example:

```bash
gh api repos/OWNER/REPO/commits?sha=main&since=CUTOFF&per_page=100
```

For each commit SHA, ask GitHub whether it belongs to a PR:

```bash
gh api repos/OWNER/REPO/commits/SHA/pulls -H 'Accept: application/vnd.github.groot-preview+json'
```

Use this to:
- catch functional direct commits not attached to a PR
- identify non-functional direct commits (for example `AUTHOR_MAP` / attribution-only churn) and exclude them cleanly
- avoid accidentally reporting merge-queue helper commits as standalone functional changes

### 5. Exclude docs-only PRs
Treat a PR as docs-only if all changed files are documentation/content artifacts, for example:
- `website/`
- markdown-only files like `*.md`
- skill docs like `SKILL.md`
- repo docs such as `SECURITY.md`
- other purely static content if the user asked to exclude docs/content

Keep PRs that touch code, config, workflows, runtime logic, tests for behavioral changes, packaging, or platform adapters.

### 6. Detect net-effect reverts
Cross-reference deployment SHAs and merged PRs. If a feature PR is followed by a revert PR in the same window, call it out explicitly:
- feature merged
- revert merged shortly after
- therefore not part of the live net effect

Good signals:
- PR title starts with `Revert`
- same or overlapping touched files
- latest deployment SHA matches the revert commit rather than the original feature

### 7. Summarize by behavior, not by file list
Group kept PRs into categories like:
- major user-facing/platform changes
- messaging/gateway behavior
- provider/model/runtime fixes
- profile/env/plugin loading
- CLI/tooling/execution reliability
- security/redaction
- setup/packaging

For each bullet include:
- PR number
- short title
- one-line effect in plain English

### 8. Recommended output format
Use this structure:

```md
### Deployment readout
- N deployments in the last 24 hours
- Current live deployment: SHA at TIME
- Status counts

### Important net effect
- Feature PR merged, then reverted
- Therefore not live

## Functional changes merged in the last 24 hours
### Biggest user-facing / platform changes
- #1234 — title — impact

### Messaging / gateway behavior
- ...

### Provider / runtime fixes
- ...

### Short take
- 3 to 6 bullets on the highest-signal net changes
```

## Pitfalls
- Browser access to deployments may fail even when API access works; do not depend on the browser page.
- The deployments endpoint can return large payloads; keep page size bounded (`per_page=30` is usually enough for a 24h window on active repos).
- `gh` output can be large; if needed, use a short Python helper to filter by timestamp locally.
- Do not confuse `inactive` deployments with failed deployments.
- Do not include docs-only PRs when the user asked for functional changes only.

## Verification
Before finalizing:
1. Confirm the time window with a live `date` call.
2. Confirm latest deployment SHA and timestamp from deployments API.
3. Confirm merged PR list from GraphQL.
4. Confirm file lists for borderline PRs before classifying them as docs-only or functional.
5. Check for obvious revert pairs so the reported net effect matches what is live.
