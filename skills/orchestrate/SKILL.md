---
name: orchestrate
description: Start a work orchestrator (/orchestrate). The operator rapid-fires bugs, feature requests, and other changes with screenshots; you log each as a work item on a tracker, enrich it with background research, and hand each ready item to its own Paseo worktree running OMP, where ADN mode routes it by its description and verified-build verifies it. When the operator says done, drive every item to a validated, merged PR and a cleaned-up worktree, merging each PR yourself once it is validated, its decisions are answered, and every gate passes. The tracker is a live Ava dashboard in Development › Coding Work, named for the day or the operator's theme; trackers may run in parallel. Use for "/orchestrate", "start an orchestrator", "new work tracker", "bug bash", or "I'm going to dump bugs/features on you". Not ADN's Orchestrate playbook (one standing project). For one item in the current worktree, use verified-build directly.
---

# Orchestrate

This conversation becomes the orchestrator for one work tracker. It owns the
ledger, the item reports, the worker launches, the operator conversation, and
every PR the workers open until each is merged or the operator closes it.
Workers own routing, reproduction or baseline, implementation, lab validation,
and their PRs.

A tracker runs until the operator says they are done with it, whether that is
the end of a day or of a week. The operator may start another tracker in
another conversation at any time; trackers run in parallel and never share
items, state directories, or dashboards.

Every item takes the same path regardless of kind. Bugs, features, and other
changes are all logged, researched, handed to a worker, verified through
verified-build, and merged under the same gates. The kind you record is your
read of the report; the worker's ADN mode routes the item from its
description, and verified-build picks its own mode (`BUG_FIX` or
`FEATURE_CHANGE`).

The session has three modes, recorded in the ledger:

1. `INTAKE`: the operator sends reports; you log, enrich, and hand off.
2. `ORCHESTRATION`: starts when the operator says they are done; you drive
   everything to merge.
3. `CONCLUDED`: every item is merged or explicitly closed, and every worker
   worktree is cleaned up.

Read the `paseo` skill now for tool and CLI syntax. Read `worktree-cleanup`
before the first merge. Do not read `verified-build` or `adn-mode` to do
the work yourself; the workers load them. You only need enough of
`verified-build` to understand worker states and evidence.

## State lives on disk

The operator's messages arrive faster than you can finish each one, and the
session will compact. Keep all state in a tracker directory so a compacted or
restarted orchestrator can resume from files alone:

```
~/.local/state/orchestrate/<YYYYMMDD>-<slug>/
  ledger.md           # tracker title, mode, defaults, status board, decisions, waiting-on-you queue
  items/WI-NN-<slug>.md
  images/             # exported screenshots + manifest.jsonl
  dashboard.json      # Ava draft synchronization state, incl. folder id (written by scripts/dashboard.py)
  dashboard.html      # last rendered dashboard
  dashboard-template.html  # only when dashboard feedback changed this tracker's layout
  listener.json       # comment listener state: pid, seen message ids, last_poll, last_error
  listener.log        # listener output
```

The slug distinguishes parallel trackers started the same day (the theme, or
the weekday when there is none). After any compaction, or whenever you are
unsure of state, re-read `ledger.md` before acting. Update the ledger and the
item file in the same step as each state change, not later. Templates are in
`references/ledger-template.md` and `references/item-template.md`.

Item IDs are `WI-NN`, sequential within the tracker and never reused. Use the
same ID in the item file, branch name, worker title, status blocks, and
dashboard.

## Start

When triggered:

1. Name the tracker. Its title is the weekday and date
   (`Tuesday, October 6, 2026`). When the operator says what the tracker is
   for, lead with that theme (`Signals polish — Tuesday, October 6, 2026`).
   Do not ask for a theme; use the date when none is given.
2. Create the tracker directory and ledger, with the title as the ledger's
   `# ` heading. Record the orchestrator's cwd, session file, and Paseo
   workspace ID (`list_workspaces`, match the path).
3. Resolve the default target: repository checkout path, base branch, and
   lab system, plus how many labs this tracker may hold at once when that is
   knowable from the lab manager or repo guidance. Infer these from the
   conversation, the current checkout, and recent Paseo workspaces. Ask once,
   in one short message, only for what you cannot infer. Individual items
   may override the default target. Parallel trackers share lab capacity, so
   check the lab manager's free count rather than assuming it is yours.
4. Create the dashboard and start its comment listener per
   [Dashboard](#dashboard). The Space defaults to Development, the operator's
   standard; ask once, in the same short message as step 3, only if they have
   named another or the conversation points elsewhere.
5. Tell the operator, in two or three lines: the tracker title and ledger
   path, the dashboard link, that you are in intake mode, that they can paste
   bugs and feature requests freely, and that they should say "done" when
   finished. Also state the rule from [Merge authority](#merge-authority): you
   merge each PR yourself once it passes every gate and every decision on it
   is answered.

## Dashboard

The operator watches the tracker, and answers you, in a real Ava HTML document.
Load the installed `ava` and `ava-design-system` before authoring or editing;
never copy their managed skills. Register with `source_format: "html"`; use
revision-guarded `document edit`, never text create/replace-body for a dashboard.
Local Markdown ledgers remain inputs, not the user-facing format. Keep the
orchestrator as sole body writer; retain comments, stable operation keys and
existing sessions. A conflict or unexpected source drift requires reconciliation,
not a forced write or a second dashboard.
The ledger stays the single source of truth; `scripts/dashboard.py` only
renders it, so the dashboard can never say something the ledger does not.

```
python3 <skill-dir>/scripts/dashboard.py <tracker-dir> [--space spc_...] [--title ...]
```

The document title is the ledger's `# ` heading. The first run registers the
document, moves it into its folder, then writes `Ava space:`, `Dashboard:` and
`Dashboard folder:` into the ledger header. Later runs edit the same document
in place with the current revision guard and read source, render and warnings
back to confirm the saved HTML. Draft standing is sufficient; submit/promote
only when separately authorized by the workflow. A run with no ledger
change prints `unchanged`.

**Where it lives.** The Development Space
(`spc_16ef6d824e21402b9a42560b13436034`) holds development tracking, and it
is the default. Every open tracker is a document directly inside its root
folder "Coding Work". A concluded tracker's dashboard moves to
`Archive / Coding Work`. The script picks the path from the ledger's `Mode:`
and finds the folder in this order:

1. the folder id in `dashboard.json` or the ledger's `Dashboard folder:` line,
   if it is still a folder at that exact path;
2. otherwise the path by title through `ava document tree`, from the root;
3. a missing level is created under the right parent. Reruns reuse what they
   find, so no folder is created twice.

Each run also confirms the document is in the folder and moves it back if
not. To use another Space, pass `--space`; the same folders are resolved or
created there. `--folder-path` overrides `Coding Work` (a concluded tracker
then goes to `Archive/<that path>`) and exists for tests.

**Start.** Run the script and confirm the ledger has the `Dashboard:` line.
Use authorized native CUA on the assigned session to inspect the actual Ava render
in light/dark and narrow/wide views at creation and after layout changes. Check
priority order, summary, links, wrapping and collapsible history. Never operate
another agent's browser or bypass foreground/capture consent. If unavailable,
record visual verification pending separately from successful source/readback;
do not report a visual pass. Do not start live publication during skill validation.
Then start the listener as a persistent background service named
`orchestrate-<tracker>-listener`, using the runtime's long-lived service
facility (in OMP, a `bash` call with `name` and a `ready` log pattern), or
`nohup` with a log file when there is none:

```
python3 <skill-dir>/scripts/listener.py <tracker-dir> "$PASEO_AGENT_ID"
```

The second argument is the orchestrator's own Paseo agent id
(`$PASEO_AGENT_ID`; otherwise `paseo ls`, matching this session's cwd). The
listener polls the dashboard's comment threads every 30 seconds. For each new
message not written by this agent's own Ava actor (read from `ava whoami`), it
replies in the thread at once ("Received. The orchestrator is working on this
and will reply here.") and sends the comment to you with
`paseo send --no-wait`, so the operator can see it is being listened to. Each
relayed comment arrives as an operator message: apply it as feedback, an
answer, or a new report, reply in the thread with what you did, log it in the
ledger, and save the dashboard again. Record `Listener: <service name>, pid <pid>, log
<path>` in the ledger. Never use `ava agent listen` for this: its
review-request scope is the whole Space, so it claims routed comments on other
documents, including other trackers' dashboards.

`listener.json` has `last_poll` and `last_error`. After a compaction or
restart, read it: when the pid is dead or `last_poll` is older than two
minutes, restart the listener with the same command. It refuses to start
twice, and a restart skips comments it already handled and retries one whose
relay failed. The dashboard header tells the operator a listener is watching.

**Every ledger change.** Run the script in the same step as the ledger edit.
Whenever you ask the operator for something in chat (a product decision, a
prototype review, a spec or ADR diff approval), add the same ask to `## Waiting on you` in
that step and remove it when it is answered. A card's `Problem:` states why
this is a product decision, and its `Decide:` carries the oracle's
recommendation when there is one. The card format is unchanged. The ask in
chat and the ask in
the dashboard say the same thing, so the operator can answer from either
place.

**Subdocuments only.** Every Ava document a tracker creates (spec diffs,
review pages, anything derived from it) is created as a subdocument of that
tracker's dashboard document, never as a sibling in the folder. Use the
dashboard's `plan_id` from `dashboard.json` as `parent_id`, then read the
document tree to verify the parent, and move it when the create ignored it.

**Writing a Needs-you item.** Each item is a `###` block, one per work item:

```
### WI-10: link clicks open the comment box → restore the link exemption
Problem: what the operator or a user sees go wrong, or what is missing, in one or two sentences.
Fix: what we will change and what it touches.
Decide: the choice they must make, as short options (a `- ` or `1.` list is fine).
Links: prototype, PR, or lab URLs.
```

The title names the problem and the change, so the operator can tell the
items apart without opening them. `Problem:` explains the issue in plain
technical-founder language: concrete and short, the user-visible problem
before the mechanism, one sentence on the cause. `Decide:` says exactly what
the operator needs to do or choose, with a name for each option. Do not leave
internal jargon (state names, ledger terms, repo-private abbreviations, commit
hashes standing in for an explanation) unexplained. Omit `Fix:` or `Links:`
rather than pad it. Never use bold (`**`) or bullet-style asks such as
`- **WI-10: ...** prose`. `scripts/dashboard.py` exits 2 with the card rule
when `## Waiting on you` holds anything but `###` cards, a card lacks
`Problem:` (or its `Broken:` alias) or `Decide:`, or a card uses bold; fix the
ledger and rerun. Mirror the same text in chat.

**If it fails.** The script exits non-zero with a message when `ava` is
missing, unauthenticated, or the saved draft does not verify. Tell the operator
that message in chat right away and keep working from the ledger. Never skip
the dashboard silently, and never claim it is current when the last run
failed.

**Feedback on the dashboard.** When the operator comments on or asks for a
change to the dashboard's content or format, do both in the same step:

1. Apply it to the live dashboard now. Layout, wording, and styling changes go
   in `<tracker-dir>/dashboard-template.html` (copy
   `references/dashboard-template.html` there first; the script prefers it).
   Changes the template cannot express (a new column, a different grouping)
   go in a copy of `scripts/dashboard.py` kept in the tracker directory and
   run from there. Save the dashboard again and confirm it with the operator.
2. Log it as a skill follow-up: its own work item (`WI-NN`, repo ai-configs,
   target `skills/orchestrate`) with the operator's words verbatim and what
   you changed live. A worker then folds it into
   `references/dashboard-template.html` or `scripts/dashboard.py`, so the next
   tracker starts with the improved standard format. Do not edit the skill
   from the orchestrator session.

**Standard format.** `references/dashboard-template.html` owns the HTML layout:
top status/mode, updated time and tracker identity, counts, urgent decisions,
then prioritized items. Record Priority in the ledger's Status table; the
dashboard shows ID and priority, item, state, waiting on, and PR. Ledger columns
it does not render are ignored. Distinguish confirmed from suspected
or inconclusive findings. Keep operator-needed work first, then active/blocked,
then completed; within each tier sort by explicit priority before ID. Completed
items and decision history are collapsible. Preserve evidence URLs and original
occurrences in the ledger/item files. Every field remains reachable at narrow
widths; use overflow scrolling rather than hiding columns.
Legacy tracker-local templates must be reconciled with the maintained template
when the renderer rejects their older layout; preserve customizations and never
delete the live tracker or start a replacement session. Use Ava theme variables with fallbacks; no OS-only dark-mode media query or
fixed theme overrides inside Ava. Update script and template together.

**Styling follows Weft.** The template's corner radii are the Weft tokens
(`@nodaste-lab/weft` `css/weft.css`), declared in its `:root` as
`--weft-radius-chip: 2px` and `--weft-radius-card: 4px`. State chips, state
pills and inline `code` use the chip radius; cards use the card radius. Never
use `--weft-radius-pill` (`999px`) or an invented radius such as `8px` or
`12px` for a status label: Weft's own `.weft-badge` (including `.is-status`)
uses the chip radius, and the pill is kept for oblong controls and
announcements such as switches and progress tracks. When the
standard changes, take new values from `css/weft.css`, not from memory.

## Intake

Each operator message may contain zero, one, or several items, follow-up
detail for an existing item, or answers to your questions. Process each
message quickly and return control so the operator can keep typing.

For every message:

1. **Capture evidence first.** Run
   `python3 <skill-dir>/scripts/collect_images.py --out <tracker-dir>/images`.
   It exports newly pasted images from this session's transcript (OMP blobs
   or Codex data URLs), skips images already exported, and prints one JSON
   line per new image with the message text it arrived with. Copy any image
   path cited in the text (for example `~/.cache/clipssh/...png`) into
   `images/` too. Workers in other worktrees cannot see this conversation;
   an image that is not on disk does not exist for them.
2. **Split and match.** Split the message into distinct items. Match each
   against existing items: same surface and same request means a follow-up
   or duplicate, not a new ID. When unsure, log it as new and note the
   suspected relation.
3. **Log.** Create or update the item file. Quote the operator verbatim.
   Describe each screenshot in words in the Evidence section (what surface,
   what state, what is wrong or wanted) so a worker that cannot render images
   still has the content. Record your read of the kind: `BUG` (current
   behavior is wrong), `FEATURE` (new or changed behavior), or `REFACTOR`,
   `PERF`, `OTHER`. It labels the dashboard and informs research; the worker
   routes from the description.
   When the item comes from an Ava document (a bug report, a design, a case
   study, or another source doc), also record its URL and author in the item
   file (`Source doc:` and `Doc author:`). Run `ava document status <doc>
   --json` and take the creator or last editor agent from
   `contributor_actor_ids` or `actors`. Add the human principal behind that
   agent when the doc or the agent's name identifies one (a "(KD)" suffix, or
   `principal_id_at_commit` in `ava document revisions <doc>`). Read
   `~/.agents/skills/ava/SKILL.md` first. The closeout needs these.
4. **Research in the background.** Start a read-only research agent per new
   item (OMP: `task` with the `scout` agent; elsewhere, the runtime's
   background subagent). Use the packet in `references/research-brief.md`.
   Never wait on it inside the intake turn. Merge its findings into the item
   file when it returns, marking inferences as `[INFERRED]`.
5. **Acknowledge.** Reply with one line per item:
   `WI-07 logged — bug, Ava Signals: acknowledge throws in nodaste space. 1 screenshot. Researching.`
   Add at most one or two blocking questions, only when research cannot
   answer them. Batch non-blocking questions for later.

The operator reports tersely: usually one or two sentences naming a UI
surface ("signals", "the left navbar", "requested by me"), the desired
behavior, and a screenshot of the current state. Structured repro steps,
environment, account, and URL are usually missing. Recover them through
research and the conversation's defaults before asking. Reports may also be
secondhand (a meeting recap, someone else's observation); record the source
and whose words they are.

### Readiness

An item is `READY` when a fresh agent could begin reproducing or baselining
it without asking the operator anything. That requires:

- target repository and base branch;
- for bugs, observed and expected behavior; for features and other changes,
  current and desired behavior, both grounded in the operator's words rather
  than your inference;
- the product surface located in code or in the running product;
- a reproduction path or precise trigger, with inferred steps marked;
- observable acceptance criteria;
- scope and non-goals, including anything the operator ruled out;
- no unresolved product decision; and
- overlap resolved: an item touching the same surface and root cause as an
  in-flight item joins that workstream or waits for it, so two workers do
  not edit the same code in parallel.

Do not over-gather. The worker reproduces or baselines the behavior itself
and verified-build obtains prototype approval for UI changes. Hand off as
soon as the bar is met.

### Handoff

**Never build on a prototype branch.** NEVER base an item on a branch, or its
commits or code, that was used to build a prototype, whether someone else's
or ours. Implementation ALWAYS starts from a fresh branch off the base branch.
The only exception is the operator explicitly saying to use that branch. If
reusing it looks useful, ask the operator first. NEVER do it silently.

For each `READY` item, launch its worker without waiting for the operator:

1. Create a worktree workspace: `create_workspace` with
   `isolation: "worktree"`, `mode: "branch-off"`, `path` set to the target
   checkout, `baseBranch` from the item, and
   `branchName: "orchestrate/wi-NN-<slug>"`.
2. Read the launch profile with `list_profiles` and take the row whose name
   is exactly `omp`; do not choose by notes. Materialize it: `provider` is
   `omp/<model>` (normally `omp/@default`, which resolves OMP's configured
   default model), `settings.modeId` is its `modeId`, and
   `settings.thinkingOptionId` is set only if present. Do not choose or
   override the model.
3. `create_agent` in the new `workspaceId`, titled `[WI-NN] <short title>`,
   with the brief from `references/worker-brief.md`, and leave
   `notifyOnFinish` at its default of true.
4. Verify placement with `get_agent_status`: provider `omp`, the profile's
   mode, and a cwd equal to the new worktree. If the worker landed elsewhere,
   archive it and relaunch before it edits anything.
5. Record workspace ID, worktree path, branch, and agent ID in the item file
   and ledger, and set the item to `HANDED_OFF`.

Each worker claims its own lab through verified-build, and keeps it while its
PR is open or a prototype review is pending. The orchestrator releases it as
soon as the work is done (see [Cleanup per item](#cleanup-per-item)); it never
asks the operator to. Cap concurrent workers per lab system at the
capacity recorded in the ledger. When capacity is unknown and a worker
reports that no lab is available, record the observed capacity, stop
launching for that lab system, and queue the remaining `READY` items as
`QUEUED`. Launch the next one when a lab frees up.

### Worker notifications during intake

Workers finish turns while the operator is still typing. On each
notification, read the worker's final `WORKER_STATUS` block (defined in the
worker brief), update the item and ledger, and act:

- `IN_PROGRESS`: no operator action needed; record it, including the ADN
  playbook and verified-build mode the worker chose.
- `PROTOTYPE_REVIEW` or `NEEDS_OPERATOR`: for `NEEDS_OPERATOR`, first screen
  the question per [Asking the operator](#asking-the-operator); a non-product
  ask goes to the oracle, not the queue. Otherwise add the item to the ledger's
  "Waiting on you" queue (and republish the dashboard, per
  [Dashboard](#dashboard)) and append the queue, one line per item, to your
  next acknowledgment whenever it changed. Do not derail intake; the
  operator may answer between dumps or later. A worker waiting on prototype
  review cannot implement and is still holding a lab, so keep those items at
  the top of the queue.
- `FAILED_VALIDATION`: record it and let the worker iterate on the same PR.
  Escalate only when the worker reports the same failure surviving two
  materially different fixes, as verified-build requires.
- `BLOCKED`: resolve it yourself when the cause is in your control (missing
  evidence, wrong target, lab capacity). Otherwise queue it for the operator.

A notification with no status block, or a timeout, means inspect the agent
(`get_agent_status`, `paseo logs <id>`). It does not mean the worker failed.

## Orchestration

When the operator says they are done ("done", "that's all", "go"), set the
ledger mode to `ORCHESTRATION` and:

1. Finish intake: export any final images, merge pending research, and hand
   off every item that can reach `READY`. For the rest, ask all remaining
   blocking questions in one numbered message.
2. Create a heartbeat (`create_heartbeat`, every 20 minutes) whose prompt
   says: `orchestrate <tracker> status pass: re-read <ledger path>, inspect
   every active worker, act on changes, and report only changes or
   blockers.` It catches stuck workers that send no notification and
   re-anchors the session after compaction. Record its ID in the ledger.
3. Post the status board (format below), then drive each item through its
   states as notifications, heartbeats, and operator answers arrive.

Late reports during orchestration are normal: log them through intake and
continue.

### Relaying between operator and workers

- Relay operator answers to the worker with `send_agent_prompt`. Quote the
  operator verbatim and label your own reading as interpretation. Log each
  decision verbatim in the ledger's decisions section.
- Answer worker questions yourself when the answer is already in the
  operator's words, the item file, or the repository. Send everything else
  that is not a product behavior decision to the oracle
  ([Asking the operator](#asking-the-operator)).
- Send follow-ups to a worker only for new evidence, an operator answer, a
  concrete scope correction, or a verified problem. Do not prompt a worker
  that is running.
- If a worker has not progressed across two heartbeats, inspect its logs.
  Nudge it once with the specific gap. If it is still stuck, report it to the
  operator as `BLOCKED` with the cause and options (retry, relaunch, narrow
  scope, or drop).

### Asking the operator

The operator decides product behavior only: what users experience or what the
product does. Nothing else blocks on them. Send every other question to the
oracle first (OMP: `task` with the `oracle` agent; packet per the global
AGENTS.md "Model and agent routing" section: the decision, constraints,
evidence and paths, credible options, your recommendation and uncertainty,
and one narrow question ending in `?`), or decide it yourself with tools.
That covers technical choices, design trade-offs inside a settled product
direction, where to file findings, lab and access chores, tooling and process
questions, and risk calls on internal infrastructure. Record the oracle's
answer in the ledger's decisions section with whether you accepted it, and
act on it.

Use the operator only for a product behavior decision, or for an action that
is irreversible or explicitly reserved to them: merge authority beyond the
standing rule, production deploys (never offered), and repo rules that name
the operator when no operator ruling already decides the matter (the oracle
checks; see below). Also use them when the oracle confirms the only way forward is
something only they can supply, such as a credential; the card's `Problem:`
says so. Whether a reported behavior is expected or a feature is wanted
(`NOT_REPRODUCED`, `EXPECTED_BEHAVIOR`, `WONT_FIX`, `DEFERRED`) is a product
call and stays theirs.

When an operator ruling already decides the matter, even though a repo rule
names the operator, do not ask. Cite the ruling as the authority, make the
change, and disclose it in the PR description so the operator can veto at
review.

Workers consult the oracle before ending a turn with `NEEDS_OPERATOR`. Screen
every `NEEDS_OPERATOR` again before posting a card. When the question is not
a product decision, take it to the oracle yourself, send the worker the
answer, and post nothing. When it is, keep the worker's oracle recommendation
in the card.

### Review and merge

When a worker reports `VALIDATED`, verify the receipt yourself: the PR
exists, its head SHA equals the validated SHA, CI is green (or the
repository has no CI), GitHub reports it mergeable, the PR shows the visual
evidence table, and the PR carries the interaction table that passes the
gate below. Open at least one of its screenshots or videos.

If the receipt passes and every operator decision on the item is answered
(prototype approval, spec or ADR diff approval, product behavior choices),
merge it per [Merge authority](#merge-authority) without asking. Do not send
the operator an "approve?" packet: the worker and the gates have the
information, and asking the operator to confirm a passing PR only asks them
to rubber-stamp it. After merging, tell the operator in one short notice that
the change is merged and that production deploy is a human operator action. Do
not ask whether to deploy and do not offer to:

```
WI-07 merged — Signals acknowledge error (bug)
PR: <url>   squash: <sha>   validated head: <sha>   lab: <lab>
What changed: <one or two sentences>
Evidence: <baseline vs candidate summary; PR evidence table link>
Risks / not covered: <list or none>
```

Ask the operator only for what the gates cannot settle and the oracle cannot
answer: an open product behavior decision, a spec or ADR diff that changes
product behavior, a prototype review, a scope change that alters product
behavior, or an irreversible action reserved to the operator. A known gap the
worker could not verify, a step that needs hands, and risk calls on internal
infrastructure go to the oracle first or to the driver's own tools. Send
technical and process questions to the oracle first
([Asking the operator](#asking-the-operator)). Put the ask in
`## Waiting on you` as usual. Once it is answered and the gates pass, merge.

Change requests and post-merge feedback go back to the same worker
verbatim; the worker updates its PR (or opens a follow-up PR) and
revalidates.

`NOT_REPRODUCED`, `EXPECTED_BEHAVIOR`, and `VALIDATED` for a user-facing
item need interaction evidence before they count. Open the worker's
interaction table and look at its screenshots or video yourself. Bounce the
report back to the worker, citing the gap, unless the evidence shows the
operator's exact reported interaction (for a feature, the desired
interaction) performed in a real browser and its observed outcome. For an
item with no UI (CLI, API, job), the same gate applies to the exact command or
call the operator reported. The operator's words are the rationale: "So you
looked at a screenshot that showed that there were highlights. You didn't
open the UI. You didn't click on the highlight to see if it highlighted the
comment. You didn't check to see if any of the user experience was working.
That's not an acceptable way to check." DOM counts, render checks, data
checks, and static screenshots fail the gate, and so does your own read of a
worker's summary. Never tell the operator something does or doesn't
reproduce, or does or doesn't work, on that basis.

Do not use Paseo's built-in browser (the `browser_*` tools) for browser work.
Interaction evidence gathered there fails the gate.

A `NOT_REPRODUCED` or `EXPECTED_BEHAVIOR` that passes the gate goes to the
operator with the worker's evidence. The operator chooses whether to supply
more detail (the worker retries), close the item, or turn it into a feature
request.

### Spec and ADR changes

ADR numbers are not part of any approval. Allocate the next free number from the repo's tool (or max+1 across origin/main and open branches), renumber on any collision, and never ask the operator about a number or list it in `## Waiting on you`. The agent may merge a PR whose only purpose is resolving ADR number collisions once repo checks pass.

Any change under `spec/` or an ADR directory reaches the operator as a
rendered diff page, never as wording in chat or the ledger. The worker writes
the edit uncommitted in its worktree and runs
`python3 <skill-dir>/scripts/spec_diff.py <worktree> --base <base branch> --path spec --title "<what changes>" --summary-file <plain-terms note> --reply "<how to answer>" --tracker-dir <tracker-dir> --publish`
(one `--path` per spec directory; `--head <ref>` renders a commit instead of
the working tree). The script needs only Python and pandoc, reads the text
from git, and saves one draft Ava page as a subdocument of this tracker's
dashboard (`parent_id` is `plan_id` from `<tracker-dir>/dashboard.json`; it
fails when that file has no `plan_id`, and it moves and rechecks a page whose
create ignored the parent). The page shows
each changed file as before and after lines plus the whole file with the
change marked. `manifest.json` next to it fingerprints the proposed files.

Put a `Links:` entry to the page in the item's `## Waiting on you` card and
leave the wording out of it. The operator's approval covers exactly the
rendered diff. After approval the worker commits those bytes unchanged and
runs
`python3 <skill-dir>/scripts/spec_diff.py <worktree> --check <out>/manifest.json --head HEAD`
before pushing. Changed text is a new proposal: rerun the script with the
same `--out` to update the page, and ask again.

### Merge authority

The operator's standing rule (2026-10-06), given for bug bashes and carried
over to every orchestrator tracker: "any PR that we do a bug bash on, that is
validated, where all decisions are approved, and it's passing all of our
gates, you don't need to ask for my approval to merge it. You just need to
merge it." So the orchestrator merges a tracker's PR, then runs the per-item
cleanup below (lab claim, demos, worktree), when all of these hold:

- the worker reported `VALIDATED` for the exact head being merged;
- the receipt in [Review and merge](#review-and-merge) passes, including the
  interaction-evidence gate;
- every operator decision the item raised has an answer in the decisions
  log, and any spec or ADR change matches the approved diff page;
- the target repository's merge policy is met.

The rule does not authorize force-pushing, merging a head that was not
validated, or merging PRs that are not this tracker's. If the operator asks
to hold a PR, or to keep its lab or worktree, do so and record why.

Nobody in a tracker deploys to production: not the orchestrator, not a
worker, and not on request. Do not ask the operator whether to, offer to, or
list it as a next step. Validation happens in a lab. "Shipped" for an agent
means merged. Production deploy is a human operator action that happens
outside the tracker.

To merge:

1. Follow the target repository's merge policy (its AGENTS.md, merge-gate
   skills, required checks, and up-to-date-branch rules). If the repository
   designates a different merger, such as a merge bot, bring the PR to that
   process's ready state and track it until it merges.
2. Merge one PR at a time. If the base moved, check whether anything merged
   since the validated base touches the PR's files, migrations, or ADR
   numbers. If it does, the repository requires an up-to-date branch, or the
   PR now conflicts, ask the worker to rebase and revalidate the new head.
3. Otherwise merge at the validated head with the repository's merge method
   (default `gh pr merge <n> --squash --match-head-commit <sha>`) and confirm
   GitHub reports it merged. Never pass `--delete-branch`: it also removes the
   worker's checked-out worktree, and the lab claim file with it, before the
   lab can be released. Branch, lab, demo, and worktree teardown belong to
   the `worktree-cleanup` script below.
4. After each merge, tell workers whose open PRs touch the same files that
   the base moved, including workers on other trackers when you know of them.

### Close out the source doc

When an item has a `Source doc:`, update the doc once the item's PR is
merged and before the item is `CLEANED`. The author asked for the issue to be
reported, so they must learn it is fixed. The driver does this, not the worker.

1. **Check whether it is live.** Run `pnpm rollout` in the ccore2 repo and
   compare the hub's deployed source commit with the merge commit. Never
   deploy, and never offer to.
2. **Add a short status section to the doc.** Say what changed, give the PR
   link and merge commit, and say whether it is live.
   - HTML doc: `ava document edit <doc> --file <html> --expected-revision
     <rev> --idempotency-key <key>`, using the revision from a fresh read.
     Keep its standing and check the render `warnings`.
   - Text doc: append the section to the current body and run `ava document
     replace-body <doc> --file <md> --idempotency-key <key>`.
3. **Comment on that section and mention the author.** An `@Name` in the
   body alone mentions nobody. Take `actorId` (as `targetId`) and `kind` (as
   `targetKind`) from `ava comment mention-suggestions`.
   - HTML doc: `ava document comment create <doc>` with a `dom` anchor on the
     new section and `mentions: [{"token":"@Name","targetKind":"human"|"agent","targetId":"act_..."}]`.
   - Text doc: `ava document text-comment create <doc>` with a unique `quote`
     from the new section and `mentions: [{"token":"@Name","targetId":"act_..."}]`.
   Mention the human principal and the reporting agent when both are known.
   Read the comment back (`ava document comment list <doc>` or `ava document
   text-comment list <doc>`) and confirm the mentions are stored.
4. **Skip the mention for your own identity.** A self-mention notifies
   nobody. When another agent owns the doc (for example perf-explorer for its
   inventory), hand the doc update to it with the PR link and merge commit.
5. **A design doc with several items** is updated once, after all its items
   land. If the operator asks, note partial progress after each item instead.

Record the section and comment links in the item's timeline. An item with no
`Source doc:`, or one concluded without a merge, skips this step.

### Cleanup per item

Once an item's PR is merged:

1. Run the script from the orchestrator's own checkout, against the worker's
   workspace, as soon as the PR is merged. The merge is the completion of the
   work; no operator agreement is needed or requested:
   `python3 ~/.agents/skills/worktree-cleanup/scripts/worktree_cleanup.py --workspace <workspace-id>`.
   It releases the lab claim, removes the demos, archives the workspace
   (which also archives the worker's agent), and deletes the remote branch.
   Do not do any of those by hand, and do not ask the worker to.
2. Act on the exit code. Exit 2 or 3: read `error`, fix the cause (a worker
   that is still running, an unreachable lab manager, uncommitted work) or
   take it to the operator, then run the same command again. Never take a
   lab release to the operator. Exit 4: run each `remaining[].command` that
   names the orchestrator, and report the operator's items. Use `--abandon`
   only for work concluded without a merge, never to get past an open PR or a
   pending prototype review.
3. Set the item to `CLEANED` only when the script reports exit 0, or exit 4
   with nothing owned by you, and the item's source doc is closed out (see
   [Close out the source doc](#close-out-the-source-doc)) or it has none.
   Record the lab release, demo removal, and archive results from its report.

An item concluded without a merge gets the same cleanup, with `--abandon
<reason>`, as soon as the worker reports `NOT_REPRODUCED` or
`EXPECTED_BEHAVIOR`, or the item is closed (duplicate, won't fix, deferred,
superseded). Do not hold the lab for the operator's answer. Keep the lab only
while a PR using it is open or a prototype review is pending, or when the
operator asks to keep it. Closing its PR or deleting its branch requires the
operator's explicit instruction. A lost claim file is the orchestrator's to
resolve: release the orphaned claim through the lab-manager's agent release
path (see the ccore2 lab-manager skill) and never queue it for the operator.

### Status board

Post this whenever you are asked for status, after the done signal, and when
something material changes during orchestration. Keep each line short:

```
Tuesday, October 6, 2026 — 9 items: 3 merged, 2 need you, 3 in progress, 1 blocked

Needs you
  WI-07 spec diff: <page url>
  WI-04 prototype review: <demo url>
  WI-09 question: should acknowledged signals also hide from the bell?
Blocked
  WI-05 no lab available in ccore labs; queued behind WI-02
In progress
  WI-02 implementing (PR draft <url>)   WI-03 reproducing   WI-08 lab validation
Done
  WI-01 merged #812   WI-06 merged #815   WI-10 closed (duplicate of WI-03)
```

## Conclude

The tracker is complete when every item is `CLEANED` and no worker workspace
remains. Then:

1. Run the `session-cleanup` inventory over the session's children to
   confirm that no workspace, lab claim, or demo remains. Re-running
   `worktree-cleanup --workspace <id>` on a cleaned item is a no-op that
   confirms it.
2. Post the final report: one row per item (ID, kind, title, outcome, PR
   link, and for a source-doc item the doc link and who was mentioned),
   operator decisions worth keeping, follow-ups the operator deferred,
   and anything left in place with its reason.
3. Read the dashboard's comments one last time and answer or log anything
   open. Stop the listener (end its background service, or kill the pid in
   `listener.json`; it clears the pid on exit), delete the status heartbeat and
   any schedule this session created, and record that in the ledger. Then, as
   the last ledger edit, set the mode to `CONCLUDED`, clear
   `## Waiting on you`, and run `scripts/dashboard.py` so the dashboard ends
   on its final state. Because the mode is `CONCLUDED`, that run moves the
   dashboard into `Archive / Coding Work`, creating the folders if needed;
   confirm the move in its output. The document stays in Ava as the record.
4. Report the orchestrator's own workspace as ready to archive. Archive it
   only if the operator asks.

## Boundaries

- The orchestrator does not implement changes, edit worker worktrees, or run
  Git mutations in them. Diagnose by reading; correct by messaging the worker.
  The `worktree-cleanup` script is the one sanctioned exception.
- No agent deploys to production, asks about it, or offers to. The worker
  brief says so.
- Do not expose credentials, claim tokens, or customer data in item files,
  briefs, or messages.
- Never mark an item merged, validated, or cleaned without observing it
  (GitHub state, worker receipt checked against the PR, archive result).
