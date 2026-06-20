---
name: scoped-plan-run
description: Execute an existing implementation plan persistently through code changes, scoped Claude and Codex reviews, Pi GPT/GLM pre-PR implementation review when running in Pi, fixes, verification, commit, push, PR creation, and Codex/Pi goal-backed PR monitoring until feedback is addressed, Codex approves with a :thumbsup:, and the PR is mergeable without expanding beyond the plan's stated scope.
---

# Scoped Plan Run

Use this skill when the user has a plan file and wants it implemented all the way to a pull request with Claude/Codex review and, in Pi, the GPT/GLM pre-PR review gate, while preventing reviewer-driven scope creep.

The plan is the contract. Reviews can reveal adjacent problems, but they do not expand the contract unless the user explicitly approves that expansion.

This skill is goal-backed in Codex and Pi. A scoped plan run is not complete at PR creation; it remains active until the PR satisfies the post-PR completion criteria. In Codex, back this with the Codex goal tools. In Pi, back this with the todo tool plus explicit working notes/handoff state so the monitoring obligation survives normal turn-to-turn execution.

## Invocation

```text
Use $scoped-plan-run to execute an explicit plan path or a slug resolvable by repo-local active plan guidance
```

Accept either a plan path or a slug. For a slug, resolve using repo-local active plan guidance; do not infer a markdown path.

## Non-Negotiable Rules

- Do not implement if the request is plan-only, review-only, or investigation-only.
- Do not run destructive git commands unless the user explicitly requested them.
- Do not fix adjacent issues just because a reviewer found them.
- Do not let Claude or Codex edit files during review. Reviews are read-only.
- Do not ask reviewers to review the whole product for open-ended problems.
- Do not proceed past a blocked plan decision by silently choosing a larger scope.
- Do not silently defer work that is required by the plan, required for verification, or introduced by this branch; fix it before merge or stop with a blocker.
- Do not create a PR until verification appropriate to the touched surfaces has run or a blocker is clearly reported.
- In Pi executions, do not create a PR until the GPT/GLM pre-PR implementation review gate has passed with no unresolved in-scope P1/P2 issues or the user explicitly waives that gate.
- Do not mark the active run state complete just because the implementation PR exists.
- Do not mark the active run state complete until PR feedback has been monitored and addressed, the PR is mergeable with the destination branch, and Codex has provided a `:thumbsup:` on the original PR description.
- Treat actionable Codex PR feedback after local reviews as a review escape: the earlier review cycle missed something, so the next local review cycle must become scope-bound adversarial review instead of only patching the commented issue.
- Do not mark the active run state blocked or stop monitoring merely because PR feedback or the qualifying Codex `:thumbsup:` is slow to arrive. Treat slow review response as a wait state that requires continued polling, not as a blocker.
- Do not create, add, request, simulate, or otherwise manufacture the required Codex `:thumbsup:` from inside this skill, this workflow, this execution, or any account controlled by the executing agent. That approval signal exists only to prove an external PR reviewer accepted the current PR state.
- Do not treat a self-authored reaction, local review verdict, chat transcript, manual note, or workflow-generated approval substitute as satisfying the Codex `:thumbsup:` criterion. If the executing agent accidentally or incorrectly adds such a reaction, remove it immediately, disclose the incident, and continue monitoring as incomplete.

## Scope Contract

Before editing, read the full plan and extract:

- Goal and user-visible outcome
- Explicit in-scope files, surfaces, phases, and acceptance criteria
- Explicit out-of-scope items
- Required tests and verification commands
- Base branch and PR target, if stated
- Open questions, unresolved decisions, or readiness status

Stop before implementation if:

- the plan is not execution-ready,
- acceptance criteria are vague enough that scope cannot be enforced,
- required user decisions remain unresolved,
- the current branch contains unrelated dirty changes that make isolation unsafe,
- Claude or Codex review is required but unavailable and the user has not waived it.
- In Pi executions, the GPT/GLM pre-PR review gate is required but unavailable and the user has not waived it.

## Scope Classification

Every requested change and every reviewer finding must be classified before implementation:

- `IN_PLAN`: directly required by the plan's acceptance criteria, phase work, or verification.
- `PLAN_PREREQUISITE`: not named in the plan, but the plan cannot work or verify without it.
- `REGRESSION_FROM_THIS_DIFF`: caused by the current implementation and must be fixed before PR.
- `OUT_OF_SCOPE_FOLLOW_UP`: real issue, but not required for this plan, not required to make verification truthful, and not introduced by this branch.
- `QUESTION`: requires user/product decision before implementation.

Only implement `IN_PLAN`, `PLAN_PREREQUISITE`, and `REGRESSION_FROM_THIS_DIFF`. Treat BDD gaps, verification gaps, implicit-only coverage, misleading evidence, or any finding tied to a plan acceptance criterion as in-scope until proven otherwise.

Use this acceptance test for any non-obvious finding:

1. Which exact plan line, acceptance criterion, or verification command requires this?
2. Would the planned feature be incorrect or unverifiable if this remained unchanged?
3. Was the issue introduced by this branch?

If the answer to all three is no, it may be left out of this PR only after it is documented as an `OUT_OF_SCOPE_FOLLOW_UP` with evidence, owner/destination, and a durable record in the PR body plus the plan deviation log or repo discovery ledger. If any answer is yes, fix it now; do not label it deferred.

## Workflow

### 1. Establish Run State

1. Check whether a scoped-plan-run goal or task state is already active.
2. If no compatible run state is active, create one before implementation begins.
   - In Codex, use the Codex goal tools for this lifecycle. Do not treat the goal as a checklist in notes only.
   - In Pi, use the todo tool to create an explicit lifecycle task set before implementation. Keep exactly one active item at a time and include a final post-PR monitoring item that cannot be marked done until all completion criteria are satisfied.
3. The objective must require both:
   - executing the specified plan through implementation, verification, scoped reviews, Pi GPT/GLM pre-PR review when applicable, commit, push, and PR creation;
   - monitoring the PR after creation until the post-PR completion criteria are satisfied.
4. If an active run state already exists and it is compatible with this scoped plan run, continue under it and state the compatibility in working notes.
5. If an active run state exists but conflicts with this scoped plan run, stop and ask the user whether to finish, block, or abandon the existing run before creating a new one.

Use this objective shape:

```text
Execute <plan path> through scoped implementation, verification, scoped reviews, Pi GPT/GLM pre-PR implementation review when applicable, commit, push, PR creation, and persistent post-PR monitoring. Do not mark complete until all PR feedback has been addressed and repeatedly rechecked, monitoring has continued until an external reviewer provides the qualifying Codex :thumbsup: on the original PR description for the current PR state, the :thumbsup: was not provided by this skill/workflow/execution or any account controlled/requested by the executing agent, and the PR is mergeable with <target branch>. Do not stop or mark blocked merely because review feedback or the qualifying :thumbsup: takes a long time to arrive.
```

The `:thumbsup:` in the objective must be interpreted as external reviewer approval only. The executing agent must not provide it, cause it to be provided by this workflow, or count any reaction from itself or its automation as completion evidence.

Pi-specific state expectation: keep the todo/working notes current with the plan path, PR URL once known, target branch, latest verification status, latest review state, mergeability, and whether the qualifying external `:thumbsup:` is still missing. Do not clear or complete those todos until the same criteria that would close the Codex goal are satisfied.

### 2. Prepare

1. Read repo instructions and the plan file.
2. Check git status and current branch.
3. Identify the base branch from the plan, or use the repo's normal integration branch.
4. Create or confirm a task branch if needed.
5. Record the scope contract in your working notes before editing.

If the worktree is dirty, preserve unrelated changes. Do not clean them up for convenience.

### 3. Implement Phase by Phase

For each unfinished phase:

1. Write or update only the tests required by the phase.
2. Implement the smallest product change that satisfies the phase.
3. Run the phase's targeted verification.
4. Update the plan progress only when that phase is actually complete.
5. Record only documented out-of-scope discoveries in the plan's deviation log or the repo's discovery ledger. In-scope findings are not discoveries to defer; fix them before advancing.

If a phase exposes a broader product problem, classify it. Fix it only if it is a plan prerequisite or a regression from this diff.

### 4. Self Scope Audit

Before external review, inspect the diff against the plan:

```bash
git diff --stat
git diff --name-only
```

For every changed file, answer: why does this file need to change for this plan?

If a changed file has no plan-bound reason, revert only your own edits to that file or split the work into a separate follow-up branch. Never revert user changes.

### 5. Codex Review

Use the `codex-review-partner` skill or its wrapper for a read-only implementation review.

The review prompt must include:

- the plan path,
- the base branch or comparison range,
- the changed files,
- the scope contract,
- instructions to classify every finding using `IN_PLAN`, `PLAN_PREREQUISITE`, `REGRESSION_FROM_THIS_DIFF`, `OUT_OF_SCOPE_FOLLOW_UP`, or `QUESTION`,
- instructions not to propose unrelated improvements.

Required verdict format:

```text
VERDICT: PASS_SCOPED
VERDICT: PASS_WITH_DOCUMENTED_OUT_OF_SCOPE_FOLLOW_UPS
VERDICT: FIX_IN_SCOPE_FINDINGS
VERDICT: BLOCKED_BY_SCOPE_QUESTION
```

Reject malformed reviews and rerun once with a tighter prompt. `PASS_WITH_DOCUMENTED_OUT_OF_SCOPE_FOLLOW_UPS` is valid only when every remaining finding is classified `OUT_OF_SCOPE_FOLLOW_UP` and includes evidence plus a tracking destination; otherwise treat the review as `FIX_IN_SCOPE_FINDINGS` or `BLOCKED_BY_SCOPE_QUESTION` by substance.

### 6. Claude Review

Use the `claude-code-review` skill for a read-only Claude review through its canonical private-tmux interactive launcher.

Claude must receive the same bounded prompt as Codex. It must not edit files. It must return findings in chat, classified with the same scope categories. Do not use alternate Claude transports for this required gate.

If Claude reports broad adjacent risks, keep them out of the PR only when they satisfy the `OUT_OF_SCOPE_FOLLOW_UP` definition and are documented. If the risk maps to the plan, verification, or this diff, treat it as in-scope and fix it.

### 7. Triage Reviews Before Fixing

Create a short triage table in your working notes:

```text
Finding | Source | Classification | Decision | Evidence
```

For each Claude and Codex finding:

- Fix `IN_PLAN`, `PLAN_PREREQUISITE`, and `REGRESSION_FROM_THIS_DIFF`.
- Record `OUT_OF_SCOPE_FOLLOW_UP` without fixing it only after documenting why it is outside this plan and where it will be tracked.
- Stop and ask the user for `QUESTION`.

Do not implement fixes directly from reviewer prose. Convert them through this triage step first.

### 8. Repeat Review Loop

After fixing in-scope findings:

1. Rerun targeted tests for touched code.
2. Rerun Codex review with the previous findings and current diff.
3. Rerun Claude review with the same bounded scope.
4. Repeat until both reviewers return `PASS_SCOPED` or `PASS_WITH_DOCUMENTED_OUT_OF_SCOPE_FOLLOW_UPS`.

Stop and report a convergence blocker if:

- the same finding recurs after two fix attempts,
- reviewers disagree on scope and the plan does not resolve it,
- a needed fix would clearly expand the plan,
- three full review cycles have not converged.

### 9. GPT/GLM Pre-PR Review Gate

After phase implementation and the scoped Claude/Codex review loop have no unresolved in-scope findings, run the GPT/GLM pre-PR gate before final PR preparation when this `scoped-plan-run` is executing in Pi.

In Pi, run `$pre-pr-implementation-review <plan path>`. That gate must use both:

- GPT-5.5 via Pi's `quality-reviewer` subagent,
- GLM-5.2 via Pi's `quality-reviewer-glm` subagent.

In non-Pi consumers, do not try to invoke the Pi-only `$pre-pr-implementation-review` skill. Run an equivalent GPT-5.5 plus GLM-5.2 read-only implementation review only when both reviewers are explicitly available in that consumer; otherwise continue the existing scoped Claude/Codex workflow and record that the Pi-only GPT/GLM gate was not run.

Pass the plan path, base/comparison range, changed files, scope contract, and latest verification results. The reviewers must classify findings by P1/P2/P3 severity and by the normal scope categories.

Treat every in-scope P1/P2 finding as blocking. Triage findings before editing, fix only `IN_PLAN`, `PLAN_PREREQUISITE`, and `REGRESSION_FROM_THIS_DIFF` P1/P2 issues, rerun targeted verification, and rerun both reviewers until both return no unresolved in-scope P1/P2 issues. P3 and true `OUT_OF_SCOPE_FOLLOW_UP` findings may remain only when documented with evidence and a tracking destination.

If the gate applies fixes after final verification has already run, rerun final verification before commit/PR. In Pi executions, if GLM-5.2 or GPT-5.5 review infrastructure is unavailable, stop unless the user explicitly waives this pre-PR gate.

Record the GPT verdict, GLM verdict, artifact path, waived/not-run status, and any documented non-blocking follow-ups for the PR body.

## Final Verification

Run the plan's final verification commands after the GPT/GLM pre-PR review gate is clean or recorded as not applicable for the current non-Pi consumer. If the plan does not specify enough verification, run the smallest repo-appropriate gate for the changed surfaces and report the gap as a plan defect.

Do not hide failures. Fix failures when they are in scope, required for truthful verification, or caused by this branch. Otherwise, report them as pre-existing or documented out-of-scope follow-ups with evidence and tracking destination.

## Commit, Push, and PR

When implementation, scoped reviews, the applicable GPT/GLM pre-PR review gate status, and final verification pass:

1. Review `git diff --stat` and `git diff --name-only`.
2. Commit only the scoped changes.
3. Push the branch.
4. Open a PR to the plan's target branch, or the repo's normal integration branch.

The PR body must include:

- plan path,
- in-scope summary,
- verification commands and results,
- Claude review verdict,
- Codex review verdict,
- GPT/GLM pre-PR review verdicts and artifact path, or explicit waived/not-run status,
- documented out-of-scope follow-ups with evidence and tracking destination,
- known residual risks.

Do not include memory citations in PR messages.

## Post-PR Completion Loop

After the PR is open, keep the active Codex goal or Pi todo/run state active and monitor the PR until all completion criteria are satisfied.

### Completion Criteria

The run state can be marked complete only when all of these are true:

- All actionable PR feedback has been addressed.
- PR feedback has been checked repeatedly after fixes, not just once immediately after PR creation.
- Codex has provided a `:thumbsup:` on the original PR description from the expected external PR reviewer account.
- The required `:thumbsup:` was not added by the executing agent, this skill/workflow/execution, an agent-controlled account, or any approval action requested by the executing agent.
- After every PR feedback item is addressed, monitoring continues until the external reviewer adds the qualifying `:thumbsup:` for the current PR state.
- The branch has been rebased or otherwise updated against the destination branch as needed.
- GitHub reports the PR as mergeable with the destination branch.

### Monitoring Loop

Repeat this loop until the completion criteria are met or a true blocker is reached. Slow or absent reviewer feedback, pending checks, and a missing qualifying Codex `:thumbsup:` are not true blockers by themselves; they require continued polling.

1. Inspect PR reviews, review threads, comments, status checks, and mergeability.
2. Classify every new feedback item using the same scope categories.
3. If any actionable feedback comes from Codex after the local Codex/Claude review gates already passed, mark the cycle as a `REVIEW_ESCAPE` in working notes. Fixing only the mentioned line is insufficient.
4. Fix `IN_PLAN`, `PLAN_PREREQUISITE`, and `REGRESSION_FROM_THIS_DIFF` feedback.
5. Record or report `OUT_OF_SCOPE_FOLLOW_UP` feedback with evidence and tracking destination without expanding the PR.
6. Stop for user input on `QUESTION` feedback.
7. For each `REVIEW_ESCAPE`, run the adversarial escalation loop below before considering the feedback addressed.
8. Rerun the smallest meaningful verification for any changes.
9. Commit and push fixes to the PR branch.
10. Rebase onto the destination branch when GitHub reports the branch out of date, conflicted, or not mergeable.
11. Recheck until GitHub shows the PR as mergeable and the external-reviewer Codex `:thumbsup:` is present on the original PR description for the current PR state.
12. If feedback is addressed but the external reviewer has not added the qualifying `:thumbsup:`, keep the run state active and continue monitoring. Do not add the reaction yourself, ask this workflow to add it, or mark the run state complete.
13. If a poll finds no new feedback and no qualifying `:thumbsup:`, report the latest PR state briefly, keep the run state active, wait, and poll again. Do not end the scoped-plan run or mark the run state blocked for review latency alone.

### Adversarial Escalation Loop

A `REVIEW_ESCAPE` means the previous review prompt was not thorough enough for this PR state. After applying the direct fix, broaden the next local review cycle within the plan's scope:

1. Write down the missed-defect pattern: reviewer, feedback URL, affected file/line, why earlier review missed it, and the failure family it represents.
2. Audit the PR diff for sibling instances: same assumption, same edge case, same API contract, same missing validation, same lifecycle/state transition, analogous callsites, and tests that should have failed but did not.
3. Run a read-only Codex `adversarial-implementation-review` against the full current PR diff, the plan scope contract, the direct PR feedback, and the sibling-audit notes. Ask Codex to actively look for additional missed issues in the same failure family and nearby plan-bound surfaces, not to re-approve the one fix.
4. If the escaped issue involves user-visible behavior, data loss, auth/security, migrations, concurrency, or broad callsite risk, also rerun Claude with the same adversarial prompt.
5. Triage new adversarial findings using the normal scope classifications. Fix in-scope findings, document true out-of-scope follow-ups, and stop for questions.
6. Repeat the adversarial review once after fixes if it finds any in-scope issue. Return to the normal monitoring loop only after the adversarial pass reports no additional in-scope findings or only documented out-of-scope follow-ups.

Keep this escalation scope-bound: it should search harder around the PR's implementation, assumptions, and failure modes, not turn into an unrelated whole-product audit.

### Polling Persistence

When the run has reached post-PR monitoring, the agent must persist across goal/session turns:

- Keep polling the PR until the qualifying external Codex `:thumbsup:` appears or a real actionable blocker requires user input.
- Poll every 60 seconds while waiting for PR feedback or the qualifying `:thumbsup:`. Do not use a slower default such as five minutes unless the user explicitly asks to reduce polling frequency.
- Continue monitoring even after all current feedback is addressed, because late feedback can still arrive before the `:thumbsup:`.
- Do not treat "no new feedback", "review still pending", "checks still running", or "no `:thumbsup:` yet" as completion, failure, or a blocker.
- In Pi, leave the monitoring todo active and summarize the latest PR URL, mergeability, feedback state, and missing/completed `:thumbsup:` evidence in any handoff or final-in-turn status.
- A true blocker must be something the agent cannot resolve by continued polling or scoped fixes, such as lost GitHub authentication, a closed/deleted PR, a force-push/base-branch conflict requiring a product decision, or `QUESTION` feedback that needs the user.
- If a true blocker is reached, report the exact blocker and the latest PR state. Otherwise, keep the active run state open and continue polling.

Use GitHub product surfaces for this check. The watcher must inspect both feedback surfaces and `:thumbsup:` reactions on every poll:

- PR issue comments via `gh pr view ... --json comments` and/or `GET /repos/<owner>/<repo>/issues/<pr>/comments`.
- PR reviews via `gh pr view ... --json reviews`.
- Inline review comments via `GET /repos/<owner>/<repo>/pulls/<pr>/comments`.
- Status/mergeability via `gh pr view ... --json mergeable,mergeStateStatus,statusCheckRollup,reviewDecision`.
- `+1` reactions on the PR issue itself via `GET /repos/<owner>/<repo>/issues/<pr>/reactions`.

Reference implementation for Pi: write this to `/tmp/monitor-pr-<pr>.sh`, start it with the `process` tool, and set `logWatches` for `FEEDBACK_CHANGED` and `QUALIFYING_THUMBSUP_PRESENT`. It polls every 60 seconds, stores snapshots, reports comment/review/status changes, and separately reports `+1` reactions without ever creating one.

```bash
#!/usr/bin/env bash
set -euo pipefail

repo="${1:?owner/repo required}"
pr="${2:?pr number required}"
expected_thumb_user="${3:-}" # Optional; if empty, report all +1 users as candidates.
interval_seconds="${PR_MONITOR_INTERVAL_SECONDS:-60}"
state_dir="${PR_MONITOR_STATE_DIR:-/tmp/pr-monitor-${repo//\//-}-${pr}}"
mkdir -p "$state_dir"

fetch_state() {
  gh pr view "$pr" --repo "$repo" \
    --json url,number,state,baseRefName,headRefName,headRefOid,mergeable,mergeStateStatus,reviewDecision,statusCheckRollup,comments,reviews \
    > "$state_dir/pr.json"
  gh api "repos/$repo/issues/$pr/comments" > "$state_dir/issue-comments.json"
  gh api "repos/$repo/pulls/$pr/comments" > "$state_dir/review-comments.json"
  gh api "repos/$repo/issues/$pr/reactions" > "$state_dir/reactions.json"
}

snapshot_feedback() {
  jq -S '{
    pr: {
      state, mergeable, mergeStateStatus, reviewDecision,
      checks: [.statusCheckRollup[]? | {name, status, conclusion}],
      reviews: [.reviews[]? | {id, author:.author.login, state, submittedAt, body}]
    },
    prComments: [.comments[]? | {id, author:.author.login, createdAt, updatedAt, body}],
    issueComments: input | [.[]? | {id, author:.user.login, createdAt:.created_at, updatedAt:.updated_at, body}],
    reviewComments: input | [.[]? | {id, author:.user.login, path, position, createdAt:.created_at, updatedAt:.updated_at, body}]
  }' "$state_dir/pr.json" "$state_dir/issue-comments.json" "$state_dir/review-comments.json" > "$state_dir/feedback.current.json"
}

snapshot_reactions() {
  jq -S --arg expected "$expected_thumb_user" '[.[] | select(.content == "+1") | {user:.user.login, createdAt:.created_at, qualifies:(($expected == "") or (.user.login == $expected))}]' \
    "$state_dir/reactions.json" > "$state_dir/thumbs.current.json"
}

while true; do
  ts=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  if ! fetch_state; then
    echo "$ts MONITOR_ERROR failed to fetch PR state; retrying in ${interval_seconds}s"
    sleep "$interval_seconds"
    continue
  fi
  snapshot_feedback
  snapshot_reactions

  if [ -f "$state_dir/feedback.previous.json" ] && ! cmp -s "$state_dir/feedback.previous.json" "$state_dir/feedback.current.json"; then
    echo "$ts FEEDBACK_CHANGED snapshot=$state_dir/feedback.current.json"
  fi
  if [ -s "$state_dir/thumbs.current.json" ] && [ "$(jq 'length' "$state_dir/thumbs.current.json")" -gt 0 ]; then
    users=$(jq -r '[.[] | select(.qualifies) | .user] | join(",")' "$state_dir/thumbs.current.json")
    if [ -n "$users" ]; then
      echo "$ts QUALIFYING_THUMBSUP_PRESENT users=$users snapshot=$state_dir/thumbs.current.json"
    else
      all_users=$(jq -r '[.[].user] | join(",")' "$state_dir/thumbs.current.json")
      echo "$ts NONQUALIFYING_THUMBSUP users=$all_users snapshot=$state_dir/thumbs.current.json"
    fi
  fi

  merge=$(jq -r '.mergeable + "/" + .mergeStateStatus' "$state_dir/pr.json")
  comments=$(jq 'length' "$state_dir/issue-comments.json")
  review_comments=$(jq 'length' "$state_dir/review-comments.json")
  reviews=$(jq '.reviews | length' "$state_dir/pr.json")
  thumbs=$(jq 'length' "$state_dir/thumbs.current.json")
  echo "$ts PR_MONITOR merge=$merge issue_comments=$comments review_comments=$review_comments reviews=$reviews thumbs_up=$thumbs"

  cp "$state_dir/feedback.current.json" "$state_dir/feedback.previous.json"
  cp "$state_dir/thumbs.current.json" "$state_dir/thumbs.previous.json"
  sleep "$interval_seconds"
done
```

Start it like this from Pi, leaving it running in the background:

```text
process.start name="pr-<number>-monitor" command="bash /tmp/monitor-pr-<number>.sh <owner>/<repo> <number> <expected-codex-reviewer-login>" logWatches=[FEEDBACK_CHANGED,QUALIFYING_THUMBSUP_PRESENT]
```

The `:thumbsup:` criterion means a `+1` reaction from the expected external Codex reviewer account on the PR issue itself, not a local reviewer verdict pasted into chat and not a reaction from the executing agent. If the expected Codex account is ambiguous, identify the account from the repository's normal PR automation or ask the user before declaring the goal complete. The executing agent must never satisfy this criterion by adding its own `+1` reaction or by asking another agent in this workflow to add one.

If a non-qualifying `+1` reaction exists, ignore it for completion. If the executing agent created it, remove it when possible and report that the previous completion signal was invalid.

### Rebase Guidance

When rebase is needed:

1. Fetch the destination branch.
2. Rebase the PR branch onto the destination branch.
3. Resolve only conflicts in scoped files or conflicts required to preserve this plan's implementation.
4. Rerun verification affected by the rebase.
5. Push with lease.

Do not use destructive git commands to force mergeability. If conflicts require decisions outside the plan, stop with a scope question.

### Run State Closure

Only after the completion criteria are all satisfied, mark the Codex goal or Pi monitoring todo complete. Do not mark the run state blocked for a slow reviewer, no new feedback, pending review, pending checks, or missing qualifying `:thumbsup:`; those are polling wait states. Mark the run state blocked only for a real actionable blocker that prevents meaningful polling or scoped fixes, and report the exact blocker with the latest PR state.

## Reviewer Prompt Template

Use this shape for both reviewers:

```text
Read-only implementation review. Do not edit files.

Plan: <plan path>
Base/comparison: <base branch or range>
Changed files:
<files>

Scope contract:
<goal, acceptance criteria, in-scope, out-of-scope, verification>

Review only whether this diff correctly implements the plan.
Classify every finding as exactly one of:
- IN_PLAN
- PLAN_PREREQUISITE
- REGRESSION_FROM_THIS_DIFF
- OUT_OF_SCOPE_FOLLOW_UP
- QUESTION

Do not recommend unrelated cleanup, hardening, new features, or broad product audits.
If you notice adjacent problems, list them only as OUT_OF_SCOPE_FOLLOW_UP and explain why they are outside this plan.
Do not put IN_PLAN, PLAN_PREREQUISITE, REGRESSION_FROM_THIS_DIFF, QUESTION, BDD gaps, verification gaps, implicit-only coverage, or plan-required work in a deferred/out-of-scope section.

Return one verdict:
- VERDICT: PASS_SCOPED
- VERDICT: PASS_WITH_DOCUMENTED_OUT_OF_SCOPE_FOLLOW_UPS
- VERDICT: FIX_IN_SCOPE_FINDINGS
- VERDICT: BLOCKED_BY_SCOPE_QUESTION

For each finding include: file/line, classification, evidence, and why it is or is not required by the plan. For each OUT_OF_SCOPE_FOLLOW_UP, include the durable tracking destination that should receive it.
```

## Adversarial Reviewer Prompt Add-on

Append this when a `REVIEW_ESCAPE` occurred:

```text
Adversarial escalation context:
Codex found actionable PR feedback after our local review gates had passed. Treat that as evidence the prior review was not thorough enough.

Escaped feedback:
- Reviewer/comment URL: <url>
- Direct issue: <summary>
- Direct fix: <summary or commit>
- Suspected failure family: <edge case / contract / callsite / validation / state / security / data-loss / test-gap pattern>

Do not merely verify the direct fix. Search the current PR diff for additional missed issues in the same failure family and nearby plan-bound surfaces:
- sibling callsites or analogous code paths
- repeated assumptions or partial fixes
- tests that should have caught the escaped issue but still would not
- boundary, lifecycle, concurrency, auth, migration, or data-loss variants relevant to this plan
- evidence that the fix closes the root cause rather than one symptom

Stay within the scope contract. Classify every finding with the normal scope labels and return the same verdict format.
```

## Final Response

Report:

- PR URL,
- run-state status (Codex goal or Pi todo),
- changed files at a high level,
- verification run,
- Claude and Codex verdicts,
- GPT/GLM pre-PR review verdicts or waived/not-run status,
- PR feedback monitoring result,
- PR mergeability result,
- Codex `:thumbsup:` result,
- documented out-of-scope follow-ups with evidence and tracking destination,
- any residual risk.

Keep the closeout concise and evidence-based.
