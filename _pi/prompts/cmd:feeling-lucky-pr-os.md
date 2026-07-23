---
description: End-to-end autopilot from a FeelingLucky Linear issue to a pushed PR
argument-hint: '[ISSUE_KEY] [BASE_REF]'
model: openai-codex/gpt-5.6-sol
---

## Critical Requirement
These instructions refer to slash commands such as `/dev:plan` - these are for you to execute directly. Under NO CIRCUMSTANCES are you to look at files outside this repository - that will trigger a permission prompt and will interrupt this flow. If that happens this entire process is terminated and we have failed.

DO NOT access files outside this repository.

# FeelingLucky Linear -> Branch -> Plan -> Review -> Implement -> Validate -> PR

End-to-end autonomous flow:

1) Find a "FeelingLucky" issue in DocThingy that is "Ready to pull" (unless ISSUE_KEY provided)
2) Create a feature branch off a fresh `origin/develop` (or provided base)
3) Create a single-file plan
4) Multi-review + integrate the plan
5) Execute the plan
6) Validate implementation vs plan
7) Code-review, then commit+push and open a PR

## Requirements

- The driving agent MUST perform code changes and repository management directly
- The reviewer agent may be used only for read-only code review
- Run the planning command directly; the planner remains planning-only
- Do not delegate implementation, fixes, tests, verification, or repository operations to subagents

## Inputs

`$ARGUMENTS` may be:

- `ISSUE_KEY` (optional) - e.g. `NOD-123`.
- `BASE_REF` (optional) - defaults to `origin/develop`.

## Process

### 0) Preconditions

```bash
git status --porcelain=v1

# Repo-local scratch space (do NOT use /tmp)
mkdir -p .opencode/tmp
OPENCODE_TMP=".opencode/tmp"
```

If dirty, STOP: "Working tree is dirty. Please commit or stash changes first."

```bash
gh auth status
ltui auth test

git fetch --prune --tags
```

Resolve base:

- `base_ref`: `$BASE_REF` if provided, else `origin/develop`

```bash
git rev-parse --verify "${base_ref}^{commit}"
```

 Critical: Driving Agent Boundaries
**YOU ARE THE DRIVING AGENT. OWN IMPLEMENTATION DIRECTLY.**
Your responsibilities:
- Use native repository tools for investigation, code changes, tests, verification, and repository operations
- Keep implementation context in this session instead of delegating it
- Use planning or review agents only for their bounded non-implementation roles
- Coordinate the flow continuously between phases
**When a read-only helper returns empty or incomplete:**
- Continue the investigation directly with repository tools
- Retry the helper only when its bounded evidence or review role is still useful
- Ask the user only for a genuinely unresolved decision
Direct product-code edits, Git operations, plan updates under `thoughts/`, and scratch JSON under `.opencode/tmp/` are allowed when required by the workflow.

### 1) Select ISSUE_KEY (FeelingLucky)

If `ISSUE_KEY` is provided, skip selection.

Otherwise:

1) Resolve the DocThingy project ref (prefer id):

```bash
ltui --format json projects list > "$OPENCODE_TMP/ltui-projects.json"

PROJECT_REF="$(python3 - <<'PY'
import json

payload = json.load(open('.opencode/tmp/ltui-projects.json'))
projects = payload.get('rows', []) if isinstance(payload, dict) else (payload if isinstance(payload, list) else [])

def norm(s: str) -> str:
    return (s or '').strip().lower()

target = 'docthingy'

def project_key(p: dict) -> str:
    return p.get('key') or p.get('identifier') or p.get('projectKey') or ''

matches = [p for p in projects if norm(p.get('name')) == target or norm(project_key(p)) == target]

if len(matches) == 1:
    p = matches[0]
    print(p.get('id') or p.get('key') or p.get('name') or '')
else:
    print('')
PY
)"
```

If `PROJECT_REF` is empty, ask the user to provide the project id/key (list projects to help them choose).

2) List issues:

```bash
ltui --format json --fields identifier,title,updatedAt --limit 25 \
  issues list --project "$PROJECT_REF" --state "Ready to pull" --label "Feeling Lucky" \
  > "$OPENCODE_TMP/ltui-feeling-lucky-issues-1.json" \
  || python3 - <<'PY' > "$OPENCODE_TMP/ltui-feeling-lucky-issues-1.json"
import json
print(json.dumps([]))
PY

ltui --format json --fields identifier,title,updatedAt --limit 25 \
  issues list --project "$PROJECT_REF" --state "Ready to pull" --label "FeelingLucky" \
  > "$OPENCODE_TMP/ltui-feeling-lucky-issues-2.json" \
  || python3 - <<'PY' > "$OPENCODE_TMP/ltui-feeling-lucky-issues-2.json"
import json
print(json.dumps([]))
PY

python3 - <<'PY' > "$OPENCODE_TMP/ltui-feeling-lucky-issues.json"
import json

def load_issues(path: str):
    try:
        payload = json.load(open(path))
    except Exception:
        return []
    if isinstance(payload, dict):
        rows = payload.get('rows', [])
        return rows if isinstance(rows, list) else []
    if isinstance(payload, list):
        return payload
    return []

issues = load_issues('.opencode/tmp/ltui-feeling-lucky-issues-1.json') + load_issues('.opencode/tmp/ltui-feeling-lucky-issues-2.json')

seen = set()
out = []
for i in issues:
    key = (i.get('key') or i.get('identifier') or '').strip()
    if not key or key in seen:
        continue
    seen.add(key)
    out.append(i)

print(json.dumps(out))
PY

python3 - <<'PY'
import json, random

issues = json.load(open('.opencode/tmp/ltui-feeling-lucky-issues.json'))
if not issues:
    print('NO_MATCHES')
    raise SystemExit(2)

random.seed()  # FeelingLucky: non-deterministic is intentional
pick = random.choice(issues)

print('PICK_KEY=' + (pick.get('identifier') or pick.get('key') or ''))
print('PICK_TITLE=' + (pick.get('title') or ''))
print('PICK_URL=' + (pick.get('url') or ''))
PY
```

Set:

- `ISSUE_KEY = PICK_KEY`

### 2) Create / Switch Branch (Follow commands/cmd:start-linear-issue-branch.md)

Fetch issue metadata in machine format:

```bash
ltui --format json --fields identifier,title,url,state issues view "${ISSUE_KEY}" --no-attachment-probe > "$OPENCODE_TMP/ltui-issue.json"

ISSUE_TITLE="$(python3 -c 'import json; print(json.load(open(".opencode/tmp/ltui-issue.json")).get("title", ""))')"
ISSUE_URL="$(python3 -c 'import json; print(json.load(open(".opencode/tmp/ltui-issue.json")).get("url", ""))')"
ISSUE_STATE="$(python3 -c 'import json; print(json.load(open(".opencode/tmp/ltui-issue.json")).get("state", ""))')"
```

Hard guard: only continue when the issue is currently in `Ready to pull`.

```bash
python3 - <<'PY'
import json, sys

issue = json.load(open('.opencode/tmp/ltui-issue.json'))
state = (issue.get('state') or '').strip().lower()

if state != 'ready to pull':
    key = issue.get('key') or ''
    url = issue.get('url') or ''
    print(f"STOP: {key} is in state '{issue.get('state', '')}', not 'Ready to pull'. {url}")
    raise SystemExit(2)
PY
```

Compute:

- `ISSUE_LOWER`: lowercased issue key
- `TITLE_SLUG`: slug of the title (lowercase, non `[a-z0-9]` -> `-`, collapse repeats, trim, max ~40)
- `branch_name`: `${ISSUE_LOWER}-${TITLE_SLUG}` (or `${ISSUE_LOWER}` if slug empty)
- `plan_slug`: same as `branch_name`
- `plan_path`: resolve from repo-local active plan guidance for `${plan_slug}`; do not infer a markdown path

```bash
ISSUE_LOWER="$(python3 -c 'import sys; print(sys.argv[1].lower())' "$ISSUE_KEY")"
TITLE_SLUG="$(python3 - <<'PY'
import re, sys

title = sys.stdin.read().strip()
slug = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
slug = re.sub(r'-+', '-', slug)
slug = slug[:40].strip('-')
print(slug)
PY
<<<"$ISSUE_TITLE")"

if [ -n "$TITLE_SLUG" ]; then
  branch_name="${ISSUE_LOWER}-${TITLE_SLUG}"
else
  branch_name="${ISSUE_LOWER}"
fi

plan_slug="$branch_name"
# Resolve plan_path from repo-local active plan guidance if a later step needs an explicit path; do not infer a markdown path.

mkdir -p thoughts/plans

if git show-ref --verify --quiet "refs/heads/${branch_name}"; then
  git checkout "${branch_name}"
elif git show-ref --verify --quiet "refs/remotes/origin/${branch_name}"; then
  git checkout --track -b "${branch_name}" "origin/${branch_name}"
else
  git checkout -b "${branch_name}" "${base_ref}"
fi
```

### 3) Create Plan (commands/dev:plan.md)

Run the planning command directly with slug `plan_slug` and ensure the plan includes:

- Linear issue key + URL (`ISSUE_KEY`, `ISSUE_URL`)
- Branch name (`branch_name`)

```text
/dev:plan ${plan_slug}
```

### 4) Plan Review + Integrate

```text
/review:plan ${plan_slug}
/review:change-integrate ${plan_slug}
```

### 5) Implement Through PR

```text
/run-plan ${plan_slug}
```

`/run-plan` owns implementation, validation, final review, commit, push, PR creation, current PR feedback snapshot, and local merge-readiness consensus. Do not run `/dev:validate`, `/review`, `/cmd:commit-push`, or `/cmd:create-pr` after it; if it exits with a blocker, stop and report the blocker instead of linking a PR. The PR it creates must start with `${ISSUE_KEY}:` and include the Linear issue title.

### 6) Link Existing PR to Linear

Link PR back to Linear:

```bash
PR_URL="$(gh pr view --json url -q .url)"
PR_TITLE="$(gh pr view --json title -q .title)"
HEAD_SHA="$(git rev-parse HEAD)"

ltui issues link "${ISSUE_KEY}" \
  --url "$PR_URL" \
  --title "$PR_TITLE" \
  --branch "${branch_name}" \
  --commit "$HEAD_SHA"

ltui issues update "${ISSUE_KEY}" --state "In Review" || true
```

## Output

Report:

- Issue: `ISSUE_KEY` + `ISSUE_URL`
- Branch: `branch_name`
- Plan: `plan_path`
- PR URL
