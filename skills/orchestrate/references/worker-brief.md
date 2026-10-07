# Worker brief

Send this as the worker's initial prompt. Fill every `<...>`, and inline the
item file's contents so the worker does not depend on the orchestrator's
machine-local paths for the facts (image paths are still required; they are
on the same host). Delete lines that do not apply.

```
You own WI-NN end to end as part of orchestrator tracker <tracker-id>. Read
`skill://adn-mode` and `skill://verified-build` first and follow both:
- ADN mode routes the work. Match this item's description to its playbook
  (Bug fix, Feature, Refactoring, Perf issue, or whichever fits) and use it
  for planning, implementation, and review. The orchestrator's read of the
  kind is `<BUG | FEATURE | REFACTOR | PERF | OTHER>`; the description, not
  that label, decides the route. Record the playbook you chose in your first
  status block.
- verified-build governs verification: pick its mode from the description
  (`BUG_FIX` when current behavior is wrong, `FEATURE_CHANGE` for new or
  changed behavior), then follow it for lab reproduction or baseline,
  prototype approval, exact-head lab validation, and PR evidence.

You are the driving verified-build session in this worktree:
<worktree path> (branch `orchestrate/wi-NN-<slug>`, based on <base branch> at <base SHA>).
It is a dedicated Paseo worktree, not the operator's primary checkout. Follow
the repository's AGENTS.md and project verification skills.

# Item
<inline the full item file: operator report verbatim, evidence descriptions,
observed/expected or current/desired, reproduction, environment, research
findings, acceptance criteria, scope and non-goals, related items>

Screenshots (read them): <absolute image paths>
Full item file: <absolute path to items/WI-NN-<slug>.md>

Facts marked [INFERRED] came from research, not the operator. Verify them;
do not trust them blindly. Find the shared root cause and check every caller
before editing.

# Reproduction and validation
Reproducing, baselining, or validating a user-facing item means driving the operator's
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
ADR numbers are mechanical: take the next free number from the repo's tool (or max+1 across origin/main and open branches), renumber on any collision, and never ask about a number. Do not put a number in an approval question.

Do not quote spec or ADR wording in a status block. When the fix needs a
change under `spec/` or an ADR directory, write the edit uncommitted in this
worktree and run `python3 <skill-dir>/scripts/spec_diff.py <worktree> --base
<base branch> --path spec --title "<what changes>" --summary-file <note>
--reply "<how to answer>" --tracker-dir <tracker-dir> --publish`. Put the
page URL in `demo:` and end the turn with the approval question. Approval
covers exactly the rendered diff. After approval, commit those bytes
unchanged and run the script with `--check <out>/manifest.json --head HEAD`
before pushing. If the text changes, rerun the script and ask again. The
summary note says what changes, why, and what it costs, in plain terms.
Every Ava page you create for this tracker is a subdocument of its dashboard
document, never a sibling. `spec_diff.py` does this from `<tracker-dir>/dashboard.json`
and fails when that file has no `plan_id`; do the same for any other page.

# Authorization
- Claim a lab, publish clickable prototypes on demos.keramos.tech, push the
  branch, open and update one PR for this item, and post PR evidence.
- Do not merge or change anything outside this item.
  Never deploy to production, and never ask whether to; deploy and validate
  only in your lab. Never run `worktree-cleanup`, `lab release`, or
  `gh pr merge --delete-branch`; the orchestrator releases your lab claim as
  soon as the PR merges or you report the item concluded (`NOT_REPRODUCED`,
  `EXPECTED_BEHAVIOR`), with no operator step. Keep the claim while your PR is
  open or a prototype review is pending. Never ask the operator to release a
  lab or resolve a stale claim from your own work. If your claim file is lost,
  release your own orphaned claim through the lab-manager's agent release path
  (see the ccore2 lab-manager skill).
  Write `demos.json` for every prototype you publish, as `verified-build`
  describes. If the right fix expands scope, stop and ask.
- Do not change your model configuration.

# Reporting
The orchestrator relays between you and the operator. It is notified each
time your turn ends. Do not wait for an answer in the middle of a turn.

The operator decides only product behavior: what users experience or what the
product does. Send everything else to the oracle first (the `oracle` task
agent, with the packet format in the global AGENTS.md "Model and agent
routing" section), or decide it yourself with tools. That covers technical
choices, design trade-offs inside a settled product direction, where to file
findings, lab and access chores, tooling and process questions, and risk calls
on internal infrastructure. Record the oracle's answer, say whether you
accepted it, and act on it.

Before you end a turn with `NEEDS_OPERATOR`, consult the oracle. Use
`NEEDS_OPERATOR` only for a product behavior decision, or for an action that is
irreversible or explicitly reserved to the operator: merge authority beyond the
standing rule, production deploys (never offered), and repo rules that name the
operator, or when the oracle confirms that only the operator can supply the way
forward, such as a credential. Put the oracle's recommendation in `question:`
and say why only the operator can answer it. Answers arrive as the operator's
verbatim words.

End every turn with this block:

WORKER_STATUS
item: WI-NN
playbook: <ADN playbook>; verified-build mode: <BUG_FIX | FEATURE_CHANGE>
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
