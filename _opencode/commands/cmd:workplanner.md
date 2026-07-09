---
description: Review Feeling Lucky issues and promote ready work to Ready to pull
model: openai/gpt-5.6-sol
reasoningEffort: medium
---

## Critical Requirement
These instructions refer to slash commands such as `/doc:fetch` and direct `ltui` calls. Under NO CIRCUMSTANCES should you look at files outside this repository.

DO NOT access files outside this repository.

Commands used for this should be in .opencode inside this repository. You may make adjustments to those files to fix problems or improve this process. 

# FeelingLucky Workplanner (Linear triage -> Ready to pull)

Autonomous flow for cron usage:

1) Select `Feeling Lucky` issue(s) in `Backlog` or `Needs Feedback`
2) Evaluate if issue is actually net-new work vs existing functionality
3) If existing behavior already covers the need, require explicit delta requirements
4) If requirements are incomplete, request detail and move issue to `Needs Feedback`
5) If requirements are clear and change is warranted, move issue to `Ready to pull` and stop

Designed for periodic execution (for example every 10 minutes).

## Progress Output (Required)

This command is often run in headless `opencode run` mode. Tool output may be minimal, so you MUST print explicit progress as you go.

Rules:

- Prefix every progress line with `[workplanner]` so logs are greppable.
- Before running any `ltui` command, print what you're about to do.
- After each `ltui` command, print a short result summary (counts / selected key / state changes), not raw JSON.
- For each candidate issue, print `ISSUE_KEY`, issue URL (if available), whether it was skipped due to waiting feedback, and what action you took.
- Do not paste full issue descriptions/comments; keep to short summaries.

## Autopilot Rules (Required)

- Do not spend time exploring `.opencode/` or other repo scaffolding.
- Start with Linear: run `ltui auth test`, resolve the DocThingy project ref, and list candidate issues.
- Do not stop after a status/progress message. Continue until you either:
  - move exactly one issue to `Ready to pull`, or
  - move an issue to `Needs Feedback`, or
  - determine there are `NO_MATCHES`, or
  - determine the next candidate is `SKIPPED_WAITING_FOR_FEEDBACK`.
- Every response must either (a) run the next concrete tool command(s) or (b) STOP with one of the required outputs. No narration-only stops.

## Inputs

None.

This command is designed for cron usage and always triages the DocThingy project as a whole (all `Feeling Lucky` issues in `Backlog` or `Needs Feedback`).

## Process

### 0) Preconditions

```bash
ltui auth test

# Repo-local scratch space (do NOT use /tmp; outside-repo access can interrupt the run)
mkdir -p .opencode/tmp
OPENCODE_TMP=".opencode/tmp"
```

Resolve DocThingy project reference:

```bash
ltui --format json projects list > "$OPENCODE_TMP/ltui-projects.json"

PROJECT_REF="$(python3 - <<'PY'
import json

payload = json.load(open('.opencode/tmp/ltui-projects.json'))
projects = payload.get('rows', []) if isinstance(payload, dict) else (payload if isinstance(payload, list) else [])

def norm(s: str) -> str:
    # Normalize "Doc Thingy" -> "docthingy"
    return ''.join((s or '').strip().lower().split())

target = 'docthingy'

def project_key(p: dict) -> str:
    return p.get('key') or p.get('identifier') or p.get('projectKey') or ''

matches = [p for p in projects if norm(p.get('name')) == target or norm(project_key(p)) == target]

if len(matches) == 1:
    p = matches[0]
    print(p.get('id') or p.get('name') or '')
else:
    print('')
PY
)"
```

Print:

- `[workplanner] preconditions ok`
- `[workplanner] resolved PROJECT_REF=<value>`

If `PROJECT_REF` is empty, STOP and report the issue.

### 1) Select Candidate Issues

List `Feeling Lucky` issues in `Backlog` and `Needs Feedback` with server-side state filters:

```bash
ltui --limit 25 --format json --fields identifier,title,state,updatedAt \
  issues list --project "$PROJECT_REF" --label "Feeling Lucky" \
  --state Backlog --state "Needs Feedback" \
  > "$OPENCODE_TMP/ltui-feeling-lucky-all.json" \
  || python3 - <<'PY' > "$OPENCODE_TMP/ltui-feeling-lucky-all.json"
import json
print(json.dumps({"rows": []}))
PY

python3 - <<'PY'
import json

payload = json.load(open('.opencode/tmp/ltui-feeling-lucky-all.json'))
candidates = payload.get('rows', []) if isinstance(payload, dict) else []

for i in sorted(candidates, key=lambda x: x.get('updatedAt') or ''):
    print(i.get('identifier') or '')
PY
```

Print:

- `[workplanner] candidate scan complete: <n> candidates (Backlog/Needs Feedback)`
- If `n=0`, print `[workplanner] NO_MATCHES` and STOP.

Save the ordered keys for iteration:

```bash
python3 - <<'PY' > "$OPENCODE_TMP/ltui-feeling-lucky-candidates.txt"
import json

payload = json.load(open('.opencode/tmp/ltui-feeling-lucky-all.json'))
candidates = payload.get('rows', []) if isinstance(payload, dict) else []

for i in sorted(candidates, key=lambda x: x.get('updatedAt') or ''):
    issue_key = (i.get('identifier') or '').strip()
    if issue_key:
        print(issue_key)
PY
```

If no candidates, STOP with `NO_MATCHES`.

### 2) Review Loop (oldest-updated first)

For each candidate issue key, in order, do the following.

```bash
while IFS= read -r ISSUE_KEY; do
  [ -n "$ISSUE_KEY" ] || continue

  printf '%s\n' "[workplanner] reviewing ${ISSUE_KEY}"

  # (steps 2a/2b/2c apply to this ISSUE_KEY)
done < "$OPENCODE_TMP/ltui-feeling-lucky-candidates.txt"
```

Fetch full issue context with comments/history:

```bash
ltui issues view "${ISSUE_KEY}" \
  --no-attachment-probe --include-comments --include-history \
  --max-description-chars 12000 --max-comment-chars 4000 \
  > "$OPENCODE_TMP/ltui-${ISSUE_KEY}.txt"
```

Print:

- `[workplanner] fetched issue context: ${ISSUE_KEY}`

#### 2a) Marker and Feedback Check

Use a marker comment convention:

```text
[workplanner] review-marker
reviewedAt: 2026-02-25T00:00:00Z
outcome: needs-feedback | ready-to-pull
```

Find the latest marker (`reviewedAt`) created by this agent. Then determine whether any non-marker comment was added after that marker timestamp.

Operational definition (so this is automatable with `ltui` text output from `issues view --include-comments`):

- A **marker comment** is any comment whose body contains the substring `[workplanner] review-marker`.
- A **workplanner comment** is any comment whose body starts with `[workplanner]`.
- A **new external comment** is any comment created after the latest marker's `reviewedAt` timestamp whose body does *not* start with `[workplanner]`.

Suggested parsing snippet (prints `SHOULD_SKIP=1` if waiting for external feedback):

```bash
python3 - "$ISSUE_KEY" <<'PY'
import re
from datetime import datetime, timezone
import sys

issue_key = sys.argv[1] if len(sys.argv) > 1 else ''
issue_path = '.opencode/tmp/ltui-' + issue_key + '.txt'

def parse_iso(ts: str):
    ts = (ts or '').strip()
    if not ts:
        return None
    if ts.endswith('Z'):
        ts = ts[:-1] + '+00:00'
    try:
        return datetime.fromisoformat(ts).astimezone(timezone.utc)
    except Exception:
        return None

lines = open(issue_path, 'r', encoding='utf-8', errors='replace').read().splitlines()

# Comments appear between COMMENTS_START and COMMENTS_END, one per line:
# <comment_id>\t<author?>\t<createdAt>\t<body>
in_comments = False
comments = []
for ln in lines:
    if ln.strip() == 'COMMENTS_START':
        in_comments = True
        continue
    if ln.strip() == 'COMMENTS_END':
        in_comments = False
        continue
    if not in_comments:
        continue

    parts = ln.split('\t', 3)
    if len(parts) < 4:
        continue
    _cid, _author, created_at_raw, body = parts[0], parts[1], parts[2], parts[3]
    created_at = parse_iso(created_at_raw)
    if created_at is None:
        continue
    comments.append({'created_at': created_at, 'body': (body or '')})

marker_re = re.compile(r"\[workplanner\]\s+review-marker")
reviewed_at_re = re.compile(r"reviewedAt:\s*([^\s]+)")
outcome_re = re.compile(r"outcome:\s*(needs-feedback|ready-to-pull)")

markers = []
for c in comments:
    body = c['body']
    if not marker_re.search(body):
        continue
    reviewed_at_m = reviewed_at_re.search(body)
    outcome_m = outcome_re.search(body)
    reviewed_at = parse_iso(reviewed_at_m.group(1) if reviewed_at_m else '')
    effective_ts = reviewed_at or c['created_at']
    if effective_ts is None:
        continue
    markers.append({'effective_ts': effective_ts, 'outcome': (outcome_m.group(1) if outcome_m else '')})

latest = max(markers, key=lambda m: m['effective_ts']) if markers else None

has_external_after = False
if latest is not None:
    cutoff = latest['effective_ts']
    for c in comments:
        if c['created_at'] <= cutoff:
            continue
        body = c['body'].lstrip()
        if body.startswith('[workplanner]'):
            continue
        has_external_after = True
        break

marker_outcome = (latest.get('outcome') if latest else '')
should_skip = (marker_outcome == 'needs-feedback') and (not has_external_after)

print('MARKER_OUTCOME=' + (marker_outcome or ''))
print('HAS_EXTERNAL_COMMENTS_AFTER_MARKER=' + ('1' if has_external_after else '0'))
print('SHOULD_SKIP=' + ('1' if should_skip else '0'))
PY
```

If `SHOULD_SKIP=1`, print:

- `[workplanner] SKIPPED_WAITING_FOR_FEEDBACK: ${ISSUE_KEY}`

and continue to the next issue.

Rules:

- If latest marker outcome is `needs-feedback` AND there are no newer comments from others, SKIP this issue for now.
- If there are newer comments after the marker, continue to re-review.
- If there is no marker, continue to first review.

### 2b) Product/Codebase Evaluation

Determine whether the request is:

- Net-new needed functionality, or
- Already covered by existing behavior (fully or partially)

Evaluation requirements:

- Inspect relevant `spec/` docs and actual implementation files.
- Prefer concrete evidence: file paths, APIs, UI flows, and existing behavior.
- If issue asks for behavior that appears to already exist, identify the exact delta still needed.

### 2c) Sufficiency Decision

If requirements are NOT clear enough to start implementation:

1) Post a structured clarification comment with:
   - Existing behavior found (with concrete references)
   - What is still ambiguous
   - Exact questions to unblock implementation
2) Move issue to state `Needs Feedback`
3) Post/update a marker comment with outcome `needs-feedback` and current UTC timestamp
4) Continue to next candidate

Use comment template:

```text
[workplanner] clarification-needed

I reviewed current functionality and found related behavior in:
- <path or feature>

Before we can pull this into implementation, we need clarification on:
1) <question>
2) <question>

Please reply in-thread and we will re-review automatically.
```

If requirements ARE clear and change is warranted:

1) Move issue to `Ready to pull`
2) Post marker comment with outcome `ready-to-pull` and current UTC timestamp
3) STOP immediately (exit loop) so `/cmd:feeling-lucky-pr` can pick up work

### 3) State/Comment Commands

Use these commands when applying outcomes:

```bash
ltui issues comment "${ISSUE_KEY}" --body "${COMMENT_BODY}"
ltui issues update "${ISSUE_KEY}" --state "Needs Feedback"
ltui issues update "${ISSUE_KEY}" --state "Ready to pull"
```

For timestamp generation:

```bash
date -u +"%Y-%m-%dT%H:%M:%SZ"
```

## Output

Report one of:

- `NO_MATCHES`
- `SKIPPED_WAITING_FOR_FEEDBACK: ISSUE_KEY`
- `MOVED_TO_NEEDS_FEEDBACK: ISSUE_KEY`
- `MOVED_TO_READY_TO_PULL: ISSUE_KEY`

Include issue URL and short rationale when action is taken.
