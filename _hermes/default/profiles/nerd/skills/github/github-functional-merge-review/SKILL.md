---
name: github-functional-merge-review
description: Review a GitHub repository for meaningful functional merges in a time window while excluding deploy/docs/site noise. Use for daily repo change reports.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [github, pull-requests, release-notes, changelog, reporting]
---

# GitHub functional merge review

Use this skill when asked to produce a daily/periodic report of meaningful functional code changes merged into a GitHub repo, especially when deploy noise, GitHub Pages commits, docs-site artifacts, or generated output must be excluded.

## Core workflow

1. Establish the exact window in UTC.

```bash
date -u '+%Y-%m-%dT%H:%M:%SZ'
```

Compute the start timestamp from the requested interval (for example, minus 24 hours).

2. Prefer `gh pr list` for merged PR discovery.

```bash
gh pr list --repo OWNER/REPO --state merged --limit 200 \
  --json number,title,mergedAt,url,author,mergeCommit \
  --jq '.[] | select(.mergedAt >= "START_ISO" and .mergedAt <= "END_ISO") | [.mergedAt, ("#"+(.number|tostring)), .title, .author.login] | @tsv'
```

Notes:
- Use a high enough `--limit` for busy repositories; increase or paginate if the window is not fully covered.
- `gh api repos/OWNER/REPO/pulls -f state=closed ...` can accidentally become a POST and fail with `"base", "head" weren't supplied`; if using `gh api`, force GET with `-X GET`.

3. Check commits too, to catch direct commits and understand squashed/merged details.

```bash
gh api -X GET repos/OWNER/REPO/commits \
  -f since=START_ISO -f until=END_ISO -f per_page=100 \
  --jq '.[] | [.commit.committer.date, .sha[0:7], .commit.message|split("\n")[0]] | @tsv'
```

For busy repos, fetch page 2/3 as needed:

```bash
gh api -X GET repos/OWNER/REPO/commits \
  -f since=START_ISO -f until=END_ISO -f per_page=100 -f page=2 \
  --jq '.[] | [.commit.committer.date, .sha[0:7], .commit.message|split("\n")[0]] | @tsv'
```

4. Inspect likely-functional PRs before summarizing.

```bash
gh pr view PR_NUMBER --repo OWNER/REPO \
  --json number,title,body,files,commits \
  --jq '{number,title,body:(.body[0:700]), files:[.files[].path][0:25], commits:[.commits[].messageHeadline][0:12]}'
```

Why: PR titles alone can be misleading; bodies and file lists reveal whether the change was runtime behavior, tests demonstrating behavior, docs-only, deploy-only, or generated output.

If JSON output is very large or tool output is capped, use `--jq` to pre-trim body/files/commits instead of loading the full JSON into Python. Large raw `gh` JSON captured through terminal wrappers can become truncated or contain control characters that break `json.loads`.

## Filtering guidance

Report functional changes, including:
- Runtime behavior changes
- User-facing features
- Bug fixes
- Tool/integration/platform changes
- Workflow or developer functionality changes
- Reliability/security/data-integrity fixes
- Tests that document or protect shipped behavior

Exclude unless mixed with real code changes:
- GitHub Pages deployments
- Website/docs-site publish artifacts
- Generated static site output
- Pure docs-only changes
- Formatting-only changes
- Version bumps without functional impact
- Release author-map/chore metadata
- CI-only or metadata-only churn unless it materially affects developer/release behavior
- Features merged and reverted within the same window; mention only if the net effect matters

When a PR contains both noise and functional changes, report only the functional part.

## Grouping and report style

- Group related PRs into coherent bullets: update/backup, gateway/platforms, Slack, TUI/CLI, security/provider, skills, file/session integrity, etc.
- Include PR numbers only if the prompt or user asks for traceability; otherwise omit specific PR numbers and commit hashes.
- Summarize material functional changes and why they matter; avoid listing every commit or every individual PR/change.
- Keep daily reports concise but not so terse that functional impact is lost.
- End with an explicit ignored/noise line if the prompt asks for it.

## Common pitfalls

- Do not answer from memory; use live `gh`/GitHub data.
- Do not treat docs-site deploy commits as product changes.
- Do not include generated site output just because it has many changed files.
- Beware `gh api` defaulting to POST when `-f` fields are used; add `-X GET` for list endpoints.
- If the repository is extremely active, `gh pr list --limit 50` may miss older merges in the window; use 200+ or paginate.
