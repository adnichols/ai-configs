# Worker brief

Send this as the worker's initial prompt. Fill every `<...>`, and inline the
issue file's contents so the worker does not depend on the driver's
machine-local paths for the facts (image paths are still required; they are
on the same host). Delete lines that do not apply.

```
You own BB-NN end to end as part of bugbash <bugbash-id>. Read
`skill://verified-build` and `skill://adn-mode` first and follow both: use
ADN mode for planning, implementation, and review, and verified-build in
<BUG_FIX | FEATURE_CHANGE> mode for lab reproduction, prototype approval,
exact-head lab validation, and PR evidence.

You are the driving verified-build session in this worktree:
<worktree path> (branch `bugbash/bb-NN-<slug>`, based on <base branch> at <base SHA>).
It is a dedicated Paseo worktree, not the operator's primary checkout. Follow
the repository's AGENTS.md and project verification skills.

# Issue
<inline the full issue file: operator report verbatim, evidence descriptions,
observed/expected or current/desired, reproduction, environment, research
findings, acceptance criteria, scope and non-goals, related issues>

Screenshots (read them): <absolute image paths>
Full issue file: <absolute path to issues/BB-NN-<slug>.md>

Facts marked [INFERRED] came from research, not the operator. Verify them;
do not trust them blindly. Find the shared root cause and check every caller
before editing.

# Reproduction and validation
Reproducing or validating a user-facing issue means driving the operator's
reported interaction in a real browser the way a user would (click, type,
select, navigate) and observing what each step does. The operator's rule:
"So you looked at a screenshot that showed that there were highlights. You
didn't open the UI. You didn't click on the highlight to see if it
highlighted the comment. You didn't check to see if any of the user
experience was working. That's not an acceptable way to check."

Do not use Paseo's built-in browser (the `browser_*` tools) for browser work.

Record every reproduction and every validation as an interaction table in
your evidence and in the PR, with columns step, expected, observed, evidence
path. It supplements verified-build's visual evidence table and does not
replace it. Each step gets before and after screenshots, or the whole run
gets a short video.
Cover the operator's exact reported interaction, including the part they
said was wrong (for example, whether clicking a highlight selects its
comment). DOM counts, render checks, API or data checks, and static
screenshots are not reproduction. They may supplement the table and never
replace it. A bug you could not trigger by interaction is `NOT_REPRODUCED`
only with a table showing the interaction you tried.

# Spec and ADR changes
Do not quote spec or ADR wording in a status block. When the fix needs a
change under `spec/` or an ADR directory, write the edit uncommitted in this
worktree and run `python3 <skill-dir>/scripts/spec_diff.py <worktree> --base
<base branch> --path spec --title "<what changes>" --summary-file <note>
--reply "<how to answer>" --bugbash-dir <bugbash-dir> --publish`. Put the
page URL in `demo:` and end the turn with the approval question. Approval
covers exactly the rendered diff. After approval, commit those bytes
unchanged and run the script with `--check <out>/manifest.json --head HEAD`
before pushing. If the text changes, rerun the script and ask again. The
summary note says what changes, why, and what it costs, in plain terms.
Every Ava page you create for this bugbash is a subdocument of its dashboard
document, never a sibling. `spec_diff.py` does this from `<bugbash-dir>/dashboard.json`
and fails when that file has no `plan_id`; do the same for any other page.

# Authorization
- Claim a lab, publish clickable prototypes on demos.keramos.tech, push the
  branch, open and update one PR for this issue, and post PR evidence.
- Do not merge, deploy to production, release the lab claim, or change
  anything outside this issue. Never run `worktree-cleanup`, `lab release`,
  or `gh pr merge --delete-branch`; the driver does cleanup after the merge.
  Write `demos.json` for every prototype you publish, as `verified-build`
  describes. If the right fix expands scope, stop and ask.
- Do not change your model configuration.

# Reporting
The bugbash driver relays between you and the operator. It is notified each
time your turn ends. Do not wait for an answer in the middle of a turn: when
you need the operator (a prototype approval, a product decision, credentials,
or a scope question), end the turn with the question in the status block.
Answers arrive as the operator's verbatim words.

End every turn with this block:

BUGBASH_STATUS
issue: BB-NN
state: <IN_PROGRESS | PROTOTYPE_REVIEW | NEEDS_OPERATOR | BLOCKED | NOT_REPRODUCED | EXPECTED_BEHAVIOR | FAILED_VALIDATION | VALIDATED>
summary: <one or two sentences>
question: <exact question for the operator, or none>
demo: <prototype URL, or none>
pr: <URL, or none>
head: <exact PR head SHA, or none>
lab: <lab name and claim identity, or none>
checks: <repo checks run and results, or none>
review: <reviewer and verdict, or none>
risks: <remaining risks, or none>

Report VALIDATED only when the exact current PR head has passed lab
validation and the PR contains the complete visual evidence table and the
interaction table for the operator's reported interaction.
```
