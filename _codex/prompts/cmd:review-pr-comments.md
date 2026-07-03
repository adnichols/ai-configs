---
description: Review and address PR comments since last commit
argument-hint: ""
---

# Review PR Comments

Process recent PR comments, verify them, track as a todo list, and implement fixes.

## Process

### 1. Identify Context
1. **Resolve PR**:
   - If the user provided a PR URL/number, use it directly.
   - Otherwise resolve from current branch:
     - `git rev-parse --abbrev-ref HEAD`
     - `gh pr list --head [branch] --json number,title,url`
2. **Use PR head commit time (not local commit time)**:
   - Get PR head SHA + latest commit timestamp from GitHub:
     - `gh pr view [number] --json number,url,headRefOid,commits --jq '{number,url,headSha:.headRefOid,lastPrCommitAt:.commits[-1].committedDate}'`
   - This avoids false negatives when local branch has unpushed commits.

### 2. Fetch & Filter Comments
1. **Fetch from all review channels** (do not rely only on `gh pr view --json comments,reviews`):
   - Top-level PR conversation comments:
     - `gh api --paginate "repos/[owner]/[repo]/issues/[number]/comments?per_page=100"`
   - Review summaries (approve/comment/request changes):
     - `gh api --paginate "repos/[owner]/[repo]/pulls/[number]/reviews?per_page=100"`
   - Inline code review comments on diffs:
     - `gh api --paginate "repos/[owner]/[repo]/pulls/[number]/comments?per_page=100"`
   - Reusable merge snippet (writes a normalized, newest-first JSON list to `/tmp/pr-comments-merged.json`):
     ```bash
     OWNER_REPO="Nodaste-Lab/doct"
     PR_NUMBER=82

     ISSUE_JSON="$(mktemp)"
     REVIEWS_JSON="$(mktemp)"
     INLINE_JSON="$(mktemp)"

     gh api --paginate "repos/$OWNER_REPO/issues/$PR_NUMBER/comments?per_page=100" > "$ISSUE_JSON"
     gh api --paginate "repos/$OWNER_REPO/pulls/$PR_NUMBER/reviews?per_page=100" > "$REVIEWS_JSON"
     gh api --paginate "repos/$OWNER_REPO/pulls/$PR_NUMBER/comments?per_page=100" > "$INLINE_JSON"

     jq -s '
       (.[0] // []) as $issue
       | (.[1] // []) as $reviews
       | (.[2] // []) as $inline
       | (
           ($issue | map({
             source: "issue_comment",
             id,
             author: .user.login,
             createdAt: .created_at,
             body,
             url: .html_url,
             state: null,
             path: null,
             line: null
           }))
           + ($reviews | map({
             source: "review",
             id,
             author: .user.login,
             createdAt: (.submitted_at // .created_at),
             body: (.body // ""),
             url: .html_url,
             state: (.state // null),
             path: null,
             line: null
           }))
           + ($inline | map({
             source: "review_comment",
             id,
             author: .user.login,
             createdAt: .created_at,
             body,
             url: .html_url,
             state: null,
             path: (.path // null),
             line: (.line // .original_line // null)
           }))
         )
       | sort_by(.createdAt)
       | reverse
     ' "$ISSUE_JSON" "$REVIEWS_JSON" "$INLINE_JSON" > /tmp/pr-comments-merged.json

     rm -f "$ISSUE_JSON" "$REVIEWS_JSON" "$INLINE_JSON"
     ```
   - Reusable filter snippet (applies cutoff + severity fallback + conservative bot-noise filtering):
     ```bash
     LAST_PR_COMMIT_AT="$(gh pr view "$PR_NUMBER" --repo "$OWNER_REPO" --json commits --jq '.commits[-1].committedDate')"

     jq --arg cutoff "$LAST_PR_COMMIT_AT" '
       def body_lc: (.body // "" | ascii_downcase);
       def author_lc: (.author // "" | ascii_downcase);
       def is_reviewer_agent:
         author_lc | test("(claude(\\[bot\\])?|copilot|chatgpt-codex-connector)");
       def is_obvious_noise:
         ((author_lc | test("^(github-actions(\\[bot\\])?|railway-app(\\[bot\\])?)$"))
          and (body_lc | test("deploy|deployed|workflow|run details|preview|status")));
       def has_severity:
         body_lc | test("\\b(critical|major|must fix|blocker|p0|p1)\\b");
       def keep_candidate:
         (is_obvious_noise | not) or is_reviewer_agent;

       map(select(keep_candidate)) as $candidates
       | ($candidates | map(select(.createdAt > $cutoff))) as $primary
       | if ($primary | length) > 0 then
           $primary
         else
           (($candidates | map(select(has_severity))) + ($candidates | .[:20]))
           | unique_by(.source + ":" + (.id | tostring))
         end
       | sort_by(.createdAt)
       | reverse
     ' /tmp/pr-comments-merged.json
     ```
2. **Normalize + merge** all items into one list with:
   - `source` (`issue_comment` | `review` | `review_comment`)
   - `id`, `author`, `createdAt`, `body`, `url`
   - `state` (for reviews), and `path`/`line` (for review comments)
3. **Sort descending by `createdAt`** before triage so newest feedback is always processed first.
4. **Filter window**:
   - Primary: keep items where `createdAt > lastPrCommitAt`.
   - Safety net: if this returns nothing (or only bot noise), also include the newest 20 review items and any item containing severity markers (`critical`, `major`, `must fix`, `blocker`, `P0`, `P1`) regardless of timestamp.
5. **Bot filtering (conservative)**:
   - Do not blanket-drop bot authors.
   - Exclude obvious non-review automation noise (deploy/status-only comments).
   - Always include reviewer agents (e.g., `claude`, `claude[bot]`, `copilot`, `chatgpt-codex-connector`) and linter/static-analysis findings.
6. **Sanity check before proceeding**:
   - Report counts from each source (`issue comments`, `reviews`, `inline review comments`).
   - If inline review comments exist but none are in the filtered set, re-check filtering logic.

### 3. Triage & Task List Creation
1. **Analyze**: Read referenced code + full comment text for each filtered item.
2. **Deduplicate intelligently**:
   - Keep the latest comment when the same issue is repeated.
   - Prefer newer comments from the same reviewer when assessments conflict.
3. **Draft tasks**: Identify distinct actionable fixes.
4. **Detect review escapes**:
   - If actionable feedback comes from Codex after this branch already had local review passes, treat it as a `REVIEW_ESCAPE`.
   - A `REVIEW_ESCAPE` means the prior review was not thorough enough. Do not only fix the exact commented line.
   - Add a high-priority task to run an adversarial, scope-bound review cycle after the direct fixes.
5. **Create todos**:
   - Use the `TodoWrite` tool for all actionable items.
   - `content`: concise fix description.
   - `priority`: `high` for blocker/critical/major and any `REVIEW_ESCAPE` escalation, `medium` for substantive improvements, `low` for nits.
   - `status`: `pending`.

### 4. Resolution Loop
For each item in the todo list:
1. **Claim**: set item status to `in_progress`.
2. **Plan**: analyze target file/behavior.
3. **Implement**: make the code change.
4. **Verify**: run relevant tests/linters.
5. **Complete**: set item status to `completed`.
6. **Next**: continue with next pending item.

### 5. Review Escape Escalation

If the triage found a `REVIEW_ESCAPE`, run this before reporting the PR feedback as resolved:

1. Record the missed-defect pattern: feedback URL, affected file/line, why the prior review should have caught it, and the failure family it represents.
2. Inspect the full PR diff for sibling instances: analogous callsites, repeated assumptions, partial fixes, missing tests, related edge cases, and adjacent plan-bound surfaces.
3. Run a read-only adversarial implementation review over the current PR diff, the original PR feedback, and the sibling-inspection notes.
   - If using `codex-review-partner`, use `--mode adversarial-implementation-review`.
   - Ask the reviewer to find additional missed issues in the same failure family, not just to validate the direct fix.
4. Triage new findings normally. Fix in-scope issues, document true out-of-scope follow-ups, and ask the user about scope questions.
5. If the adversarial pass finds in-scope issues, rerun it once after fixes before returning to normal PR monitoring.

Keep the escalation scope-bound: it should be more aggressive around this PR's assumptions and failure modes, not an unrelated whole-product audit.

## Output
- Use `TodoWrite` to keep progress current.
- Include a short coverage-check note listing how many comments were found from each source, how many were actionable, and whether a `REVIEW_ESCAPE` adversarial cycle was required.
