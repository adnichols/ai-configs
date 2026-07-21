---
description: Fetch a Linear issue, create a branch from develop, and draft a plan (no worktree)
argument-hint: "ISSUE_KEY [BASE_BRANCH]"
---

# Start Linear Issue (Branch Only + Draft Plan)

Fetch the Linear issue, create an appropriately named branch from the current develop base, switch to it, and produce a first-draft plan.

This command does NOT create a worktree and does NOT change application code.

**Arguments**: `$ARGUMENTS`

## Instructions

### 1) Parse Arguments

- First argument: `ISSUE_KEY` (required) - e.g. `NOD-123`
- Second argument: `BASE_BRANCH` (optional) - defaults to `origin/develop`

If `ISSUE_KEY` is missing, respond with usage:

```text
Usage: /cmd:start-linear-issue-branch ISSUE_KEY [BASE_BRANCH]

Examples:
  /cmd:start-linear-issue-branch NOD-123
  /cmd:start-linear-issue-branch NOD-123 origin/develop
```

### 2) Verify Preconditions

```bash
git status --porcelain=v1
```

If output is not empty, STOP and report: "Working tree is dirty. Please commit or stash changes first."

Fetch latest refs:

```bash
git fetch --prune --tags
```

### 3) Fetch Linear Issue Metadata

```bash
ltui issues view <ISSUE_KEY> --format detail
```

Parse the output to capture:

- Title
- Project
- State
- URL
- Description (between DESCRIPTION_START and DESCRIPTION_END)

You will need at least:

- `ISSUE_TITLE` (raw title)
- `ISSUE_URL`
- `ISSUE_PROJECT`
- `ISSUE_STATE`

### 4) Create / Switch Branch (No Worktree)

Compute:

- `ISSUE_LOWER`: lowercased `ISSUE_KEY` (e.g. `NOD-123` -> `nod-123`)
- `TITLE_SLUG`: a slug derived from the Linear issue title:
  - lowercase
  - replace any run of non `[a-z0-9]` characters with `-`
  - collapse repeated `-`
  - trim leading/trailing `-`
  - limit to ~40 characters
- `base_ref`: `BASE_BRANCH` if provided, otherwise `origin/develop`
- `branch_name`: `${ISSUE_LOWER}-${TITLE_SLUG}`
  - If `TITLE_SLUG` is empty, use just `${ISSUE_LOWER}`

Recommended `TITLE_SLUG` computation:

```bash
TITLE_SLUG=$(python3 - <<'PY'
import re, sys
title = sys.stdin.read().strip()
slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
slug = re.sub(r'-+', '-', slug)
slug = slug[:40].strip('-')
print(slug)
PY
<<<"$ISSUE_TITLE")
```

Validate `base_ref` exists:

```bash
git rev-parse --verify "${base_ref}^{commit}"
```

If it fails, STOP and ask the user for the correct base ref.

Checkout logic (run as a single block):

```bash
if git show-ref --verify --quiet "refs/heads/${branch_name}"; then
  git checkout "${branch_name}"
elif git show-ref --verify --quiet "refs/remotes/origin/${branch_name}"; then
  git checkout --track -b "${branch_name}" "origin/${branch_name}"
else
  git checkout -b "${branch_name}" "${base_ref}"
fi
```

Do NOT push. Do NOT open a PR. Stop after drafting the plan.

### 5) Kick Off Planning (dev:plan-style) and Stop

Compute:

- `plan_slug`: `${ISSUE_LOWER}-${TITLE_SLUG}` (same as `branch_name`)
- If `TITLE_SLUG` is empty, use just `${ISSUE_LOWER}`
- `plan_path`: resolve from repo-local active plan guidance for `${plan_slug}`; do not infer a markdown path

Ensure the directory exists:

```bash
mkdir -p thoughts/plans
```

Spawn the planning-only `planner` subagent to draft the initial single-file plan (mimic `dev:plan`). The caller retains branch/repository authority; the planner may write only the named plan artifact.

```text
Task(
  subagent_type="planner",
  description="Draft planning-only artifact for Linear issue",
  prompt="""Draft a first-pass single-file execution plan for this Linear issue.

Use these inputs (substitute from the Linear metadata you fetched in step 3):

- Issue key: ${ISSUE_KEY}
- Title: ${ISSUE_TITLE}
- URL: ${ISSUE_URL}
- Project: ${ISSUE_PROJECT}
- State: ${ISSUE_STATE}
- Branch: ${branch_name}
- Base: ${base_ref}

Artifact and authority contract:
- Linear context is authoritative: issue ${ISSUE_KEY}, title ${ISSUE_TITLE}, URL ${ISSUE_URL}, project ${ISSUE_PROJECT}, state ${ISSUE_STATE}, branch ${branch_name}, base ${base_ref}
- Write exactly one file: ${plan_path}
- Planning-only: do not implement, change application code, manage Git, or modify any other file
- Stop after the artifact is written and report verification that only ${plan_path} changed

Guidance:
- Follow the repository's maintained planning format: specification, phases, progress, and resumability.
- This is a first draft: it's OK to include a dedicated Research phase and to mark things as unvalidated.
- You MUST do lightweight validation by inspecting the codebase (Glob/Grep/Read) so the plan references real files, patterns, and constraints.
- You MUST NOT change application code.
- Keep phases coarse (phase-level only) with `### End State`, `### Work`, and `### Verify` per phase.
- `## Progress` must be phase-level, include stable IDs (P1, P2, ...), and contain the ONLY checkboxes in the document.

Plan content requirements (from dev:plan):
- Include near the top, before implementation history and technical detail: standalone product-owner context for a reader with no prior issue/Linear context, why the work is needed now, an unmistakable conclusion distinguishing a runtime/customer defect from a stale test or evidence problem, and separate Customers / Runtime product behavior / Security or permissions / Testing or release confidence / Deployment or migration impact. Use a scannable table or equivalent structured block for non-trivial plans; lightweight drafts must use at least concise labeled prose.
- Include: Goal / Non-goals / Current State (Validated) / Proposed Approach
- Include: Acceptance Criteria (observable) and Verification Strategy
- Include: Resume Instructions (Agent)
- Include: Decisions / Deviations Log (append-only), Open Questions / Decision Points, Plan Changelog (append-only)

Stop after writing the plan."""
)
```

After the subagent completes, respond with:

- Current branch name
- Linear issue URL
- Plan path

Then STOP.
