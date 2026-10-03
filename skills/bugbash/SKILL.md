---
name: bugbash
description: Run a bug bash from one conversation. The operator rapid-fires bug reports, feature requests, and screenshots; you log each one, enrich it with background research into a complete report, and hand every ready item to its own Paseo worktree running OMP with verified-build and ADN mode. When the operator says they are done, switch to orchestration and drive every item to a validated, operator-approved, merged PR with its worktree cleaned up. Use when the operator says "bugbash", "bug bash", "I'm going to dump bugs/issues on you", "collect these as I send them", or starts pasting a batch of bugs and feature requests meant to be fixed in parallel. For a single bug the operator wants fixed in the current worktree, use verified-build directly instead.
---

# Bugbash

This conversation becomes the bugbash driver. It owns the ledger, the issue
reports, the worker launches, the operator conversation, and every PR the
workers open until each is merged or the operator closes it. Workers own
reproduction, implementation, lab validation, and their PRs.

The session has three modes, recorded in the ledger:

1. `INTAKE`: the operator sends reports; you log, enrich, and hand off.
2. `ORCHESTRATION`: starts when the operator says they are done; you drive
   everything to merge.
3. `CONCLUDED`: every item is merged or explicitly closed, and every worker
   worktree is cleaned up.

Read the `paseo` skill now for tool and CLI syntax. Read `session-cleanup`
before the first cleanup. Do not read `verified-build` or `adn-mode` to do
the work yourself; the workers load them. You only need enough of
`verified-build` to understand worker states and evidence.

## State lives on disk

The operator's messages arrive faster than you can finish each one, and the
session will compact. Keep all state in a bugbash directory so a compacted or
restarted driver can resume from files alone:

```
~/.local/state/bugbash/<YYYYMMDD>-<slug>/
  ledger.md           # mode, defaults, status board, decisions, waiting-on-you queue
  issues/BB-NN-<slug>.md
  images/             # exported screenshots + manifest.jsonl
```

After any compaction, or whenever you are unsure of state, re-read
`ledger.md` before acting. Update the ledger and the issue file in the same
step as each state change, not later. Templates are in
`references/ledger-template.md` and `references/issue-template.md`.

## Start

When triggered:

1. Create the bugbash directory and ledger. Record the driver's cwd, session
   file, and Paseo workspace ID (`list_workspaces`, match the path).
2. Resolve the default target: repository checkout path, base branch, and
   lab system, plus how many labs this bugbash may hold at once when that is
   knowable from the lab manager or repo guidance. Infer these from the
   conversation, the current checkout, and recent Paseo workspaces. Ask once,
   in one short message, only for what you cannot infer. Individual issues
   may override the default target.
3. Tell the operator, in two or three lines: the bugbash ID and ledger path,
   that you are in intake mode, that they can paste issues freely, and that
   they should say "done" when finished. Also state the approval rule from
   [Merge authority](#merge-authority) so it is agreed up front.

## Intake

Each operator message may contain zero, one, or several issues, follow-up
detail for an existing issue, or answers to your questions. Process each
message quickly and return control so the operator can keep typing.

For every message:

1. **Capture evidence first.** Run
   `python3 <skill-dir>/scripts/collect_images.py --out <bugbash>/images`.
   It exports newly pasted images from this session's transcript (OMP blobs
   or Codex data URLs), skips images already exported, and prints one JSON
   line per new image with the message text it arrived with. Copy any image
   path cited in the text (for example `~/.cache/clipssh/...png`) into
   `images/` too. Workers in other worktrees cannot see this conversation;
   an image that is not on disk does not exist for them.
2. **Split and match.** Split the message into distinct issues. Match each
   against existing issues: same surface and same failure means a follow-up
   or duplicate, not a new ID. When unsure, log it as new and note the
   suspected relation.
3. **Log.** Create or update the issue file. Quote the operator verbatim.
   Describe each screenshot in words in the Evidence section (what surface,
   what state, what is wrong) so a worker that cannot render images still has
   the content. Classify `BUG` (current behavior is wrong) or `FEATURE` (new
   or changed behavior).
4. **Research in the background.** Start a read-only research agent per new
   issue (OMP: `task` with the `scout` agent; elsewhere, the runtime's
   background subagent). Use the packet in `references/research-brief.md`.
   Never wait on it inside the intake turn. Merge its findings into the issue
   file when it returns, marking inferences as `[INFERRED]`.
5. **Acknowledge.** Reply with one line per issue:
   `BB-07 logged — bug, Ava Signals: acknowledge throws in nodaste space. 1 screenshot. Researching.`
   Add at most one or two blocking questions, only when research cannot
   answer them. Batch non-blocking questions for later.

The operator reports tersely: usually one or two sentences naming a UI
surface ("signals", "the left navbar", "requested by me"), the desired
behavior, and a screenshot of the wrong state. Structured repro steps,
environment, account, and URL are usually missing. Recover them through
research and the conversation's defaults before asking. Reports may also be
secondhand (a meeting recap, someone else's observation); record the source
and whose words they are.

### Readiness

An issue is `READY` when a fresh agent could begin reproducing it without
asking the operator anything. That requires:

- target repository and base branch;
- for bugs, observed and expected behavior; for features, current and
  desired behavior, both grounded in the operator's words rather than your
  inference;
- the product surface located in code or in the running product;
- a reproduction path or precise trigger, with inferred steps marked;
- observable acceptance criteria;
- scope and non-goals, including anything the operator ruled out;
- no unresolved product decision; and
- overlap resolved: an issue touching the same surface and root cause as an
  in-flight issue joins that workstream or waits for it, so two workers do
  not edit the same code in parallel.

Do not over-gather. The worker reproduces the problem itself and
verified-build obtains prototype approval for UI changes. Hand off as soon as
the bar is met.

### Handoff

For each `READY` issue, launch its worker without waiting for the operator:

1. Create a worktree workspace: `create_workspace` with
   `isolation: "worktree"`, `mode: "branch-off"`, `path` set to the target
   checkout, `baseBranch` from the issue, and
   `branchName: "bugbash/bb-NN-<slug>"`.
2. Read the launch profile with `list_profiles` and take the row whose name
   is exactly `omp`; do not choose by notes. Materialize it: `provider` is
   `omp/<model>` (normally `omp/@default`, which resolves OMP's configured
   default model), `settings.modeId` is its `modeId`, and
   `settings.thinkingOptionId` is set only if present. Do not choose or
   override the model.
3. `create_agent` in the new `workspaceId`, titled `[BB-NN] <short title>`,
   with the brief from `references/worker-brief.md`, and leave
   `notifyOnFinish` at its default of true.
4. Verify placement with `get_agent_status`: provider `omp`, the profile's
   mode, and a cwd equal to the new worktree. If the worker landed elsewhere,
   archive it and relaunch before it edits anything.
5. Record workspace ID, worktree path, branch, and agent ID in the issue file
   and ledger, and set the issue to `HANDED_OFF`.

Each worker claims its own lab through verified-build, and keeps it while
waiting for prototype review. Cap concurrent workers per lab system at the
capacity recorded in the ledger. When capacity is unknown and a worker
reports that no lab is available, record the observed capacity, stop
launching for that lab system, and queue the remaining `READY` issues as
`QUEUED`. Launch the next one when a lab frees up.

### Worker notifications during intake

Workers finish turns while the operator is still typing. On each
notification, read the worker's final `BUGBASH_STATUS` block (defined in the
worker brief), update the issue and ledger, and act:

- `IN_PROGRESS`: no operator action needed; record it.
- `PROTOTYPE_REVIEW` or `NEEDS_OPERATOR`: add the item to the ledger's
  "Waiting on you" queue and append the queue, one line per item, to your
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
   off every issue that can reach `READY`. For the rest, ask all remaining
   blocking questions in one numbered message.
2. Create a heartbeat (`create_heartbeat`, every 20 minutes) whose prompt
   says: `bugbash <id> status pass: re-read <ledger path>, inspect every
   active worker, act on changes, and report only changes or blockers.` It
   catches stuck workers that send no notification and re-anchors the session
   after compaction. Record its ID in the ledger.
3. Post the status board (format below), then drive each issue through its
   states as notifications, heartbeats, and operator answers arrive.

Late reports during orchestration are normal: log them through intake and
continue.

### Relaying between operator and workers

- Relay operator answers to the worker with `send_agent_prompt`. Quote the
  operator verbatim and label your own reading as interpretation. Log each
  decision verbatim in the ledger's decisions section.
- Answer worker questions yourself when the answer is already in the
  operator's words, the issue file, or the repository. Escalate only product
  intent, scope expansion, approvals, credentials, and irreversible actions.
- Send follow-ups to a worker only for new evidence, an operator answer, a
  concrete scope correction, or a verified problem. Do not prompt a worker
  that is running.
- If a worker has not progressed across two heartbeats, inspect its logs.
  Nudge it once with the specific gap. If it is still stuck, report it to the
  operator as `BLOCKED` with the cause and options (retry, relaunch, narrow
  scope, or drop).

### Review and approval

When a worker reports `VALIDATED`, verify the receipt before bothering the
operator: the PR exists, its head SHA equals the validated SHA, CI is green
or pending only on known-slow checks, the PR shows the visual evidence
table, and the PR carries the interaction table that passes the gate below.
Then present one review packet:

```
BB-07 ready for your review — Signals acknowledge error (bug)
PR: <url>   head: <sha>   lab: <lab>   demo: <url or n/a>
What changed: <one or two sentences>
Evidence: <baseline vs candidate summary; PR evidence table link>
Checks: <CI + local checks>   Review: <reviewer verdict>
Risks / not covered: <list or none>
Reply "approve BB-07" to merge and clean up, or tell me what to change.
```

Approval covers that PR at that patch. If the code changes afterwards, ask
again. A rebase whose `git patch-id --stable` matches the approved patch
keeps the approval. Rejections and change requests go back to the same
worker verbatim; the worker updates the same PR and revalidates.

`NOT_REPRODUCED`, `EXPECTED_BEHAVIOR`, and `VALIDATED` for a user-facing
issue need interaction evidence before they count. Open the worker's
interaction table and look at its screenshots or video yourself. Bounce the
report back to the worker, citing the gap, unless the evidence shows the
operator's exact reported interaction performed in a real browser and its
observed outcome. For an issue with no UI (CLI, API, job), the same gate
applies to the exact command or call the operator reported. The operator's
words are the rationale: "So you looked at a screenshot that showed that
there were highlights. You didn't open the UI. You didn't click on the
highlight to see if it highlighted the comment. You didn't check to see if
any of the user experience was working. That's not an acceptable way to
check." DOM counts, render checks, data checks, and static screenshots fail
the gate, and so does your own read of a worker's summary. Never tell the
operator something does or doesn't reproduce on that basis.

A `NOT_REPRODUCED` or `EXPECTED_BEHAVIOR` that passes the gate goes to the
operator with the worker's evidence. The operator chooses whether to supply
more detail (the worker retries), close the issue, or turn it into a feature
request.

### Merge authority

The operator's approval of a review packet ("approve BB-NN") authorizes
merging that PR and then the per-issue cleanup below: releasing that
issue's lab claim, removing its demos, and archiving its worktree. The
kickoff message states this rule so the operator agrees to it before the
first approval. Approval does not authorize production deploys, merging
other PRs, or force-pushing. If the operator approves a merge but asks to
keep the lab or worktree, preserve them and record why.

To merge an approved PR:

1. Follow the target repository's merge policy (its AGENTS.md, merge-gate
   skills, required checks, and up-to-date-branch rules). If the repository
   designates a different merger, such as a merge bot, bring the PR to that
   process's ready state and track it until it merges.
2. Merge one PR at a time. If the base moved and the repository requires an
   up-to-date branch, or the PR now conflicts, ask the worker to rebase.
   A changed head needs lab revalidation per verified-build; a changed patch
   needs re-approval.
3. Otherwise merge with the repository's merge method (default
   `gh pr merge <n> --squash --delete-branch`) and confirm GitHub reports it
   merged.
4. After each merge, tell workers whose open PRs touch the same files that
   the base moved.

### Cleanup per issue

Once an issue's PR is merged:

1. Tell its worker: the PR merged, the operator explicitly agreed the work is
   complete (quote the approval), and it should release its lab claim and
   remove the demos it published, following `session-cleanup` step 1. Ask
   it to report the results and not to archive itself.
2. When it confirms, archive its workspace with `archive_workspace`. This
   also archives its agent and removes the Paseo-managed worktree. Never
   archive a workspace with uncommitted work or an unmerged PR without
   surfacing it to the operator first.
3. Set the issue to `CLEANED` and record the lab release, demo removal, and
   archive results.

An issue the operator closes without merging (duplicate, won't fix,
deferred) gets the same cleanup. Closing its PR or deleting its branch
requires the operator's explicit instruction.

### Status board

Post this whenever you are asked for status, after the done signal, and when
something material changes during orchestration. Keep each line short:

```
Bugbash <id> — 9 issues: 3 merged, 2 awaiting your review, 3 in progress, 1 blocked

Needs you
  BB-07 approve? <PR url> (packet above)
  BB-04 prototype review: <demo url>
  BB-09 question: should acknowledged signals also hide from the bell?
Blocked
  BB-05 no lab available in ccore labs; queued behind BB-02
In progress
  BB-02 implementing (PR draft <url>)   BB-03 reproducing   BB-08 lab validation
Done
  BB-01 merged #812   BB-06 merged #815   BB-10 closed (duplicate of BB-03)
```

## Conclude

The bugbash is complete when every issue is `CLEANED` and no worker workspace
remains. Then:

1. Delete the heartbeat and any schedule this session created.
2. Run the `session-cleanup` inventory over the session's children to
   confirm that no workspace, lab claim, or demo remains.
3. Post the final report: one row per issue (ID, title, outcome, PR link),
   operator decisions worth keeping, follow-ups the operator deferred, and
   anything left in place with its reason.
4. Set the ledger mode to `CONCLUDED`. Report the driver's own workspace as
   ready to archive. Archive it only if the operator asks.

## Boundaries

- The driver does not implement fixes, edit worker worktrees, or run Git
  mutations in them. Diagnose by reading; correct by messaging the worker.
- Workers never merge and never deploy to production; the brief says so.
- Do not expose credentials, claim tokens, or customer data in issue files,
  briefs, or messages.
- Never mark an issue merged, validated, or cleaned without observing it
  (GitHub state, worker receipt checked against the PR, archive result).
