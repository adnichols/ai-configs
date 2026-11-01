---
name: workstream-owner
description: Start a WKS workstream owner, a top-level OMP agent in its own pinned Paseo worktree workspace titled `WKS <name>` that takes one source document (usually an Ava design or plan) all the way to merged PRs on main, in any repository the orchestrator manages, with a Paseo heartbeat that prompts it whenever it sits idle so it does not stall. The owner plans delivery with the repository's own delivery skill (verified-build where the repository has one) in ADN mode, ships one fully validated PR unless a listed reason forces a split, and works with the orchestrator until every PR of its plan merges. Use when the operator says start, spin up, launch or hand off to a workstream agent, WKS agent, WKS owner or workstream owner, or hands over a document for execution. The started agent reads this skill for its owner contract.
user-invocable: true
---

# Workstream owner

A WKS owner is the one agent accountable for a workstream, from its source document to its PRs merged on main. The orchestrator finds owners by workspace title. Every live workspace titled `WKS ...` gets a status request every few hours, and the agent in that workspace's worktree (top-level agents first) owns the workstream's PRs until they merge. So each owner has its own worktree workspace, its title starts with `WKS `, and it is nobody's subagent. Nothing here depends on the repository: its own rules and the orchestrator's profile for it supply the setup, validation and landing steps.

## Start an owner

This part is for the session the operator asked to start one.

1. Get the name and the source. The name is the topic as the operator says it (`ava-document format`); the workspace and the agent are both titled `WKS <name>`. The source is the document URL, or several when the operator gives several. Anything the operator says that the documents do not (a deadline, a scope limit, a ring) is a note. Ask only when the name or the source is missing.
2. Preview, then launch, on the host the owner should run on:

   ```sh
   S=~/.agents/skills/workstream-owner/scripts/start_wks.py
   python3 $S --name "<name>" --source <url> [--source <url>] [--checkout <main checkout>] [--note "<text>"] --dry-run
   python3 $S --name "<name>" --source <url> ...    # the same arguments without --dry-run
   ```

   `--checkout` is the repository's main checkout and defaults to the one holding the current directory. The script refuses, creating nothing, when a workspace titled `WKS <name>` exists on this host or another host in `~/.config/orchestrate/hosts.json`, or branch `wks/<slug>` exists. It cuts that branch from `origin/<base>` (`--base`, default `main`) into a new worktree workspace and starts the owner there with `assets/owner-brief.md` as its prompt. It then checks with `paseo inspect` that the owner has the requested provider, model, thinking, mode and cwd, and no parent. The owner runs `omp` with `anthropic/claude-opus-5-5` at `high` in mode `full`, like the owners running when this skill was written; `--model` and `--thinking` change that. Next it gives the owner its progress heartbeat, `WKS <name> progress`: every 30 minutes, `assets/progress-heartbeat.md` tells the owner to take its next step or say what it waits on. Paseo skips a firing while the owner is in a turn, so the heartbeat only reaches an idle owner, and completes it when the owner is archived. A heartbeat that cannot be created, or lands on another agent, fails the start like a failed `paseo inspect`. Last, it pins the workspace to Paseo's sidebar. The `paseo` CLI has no pin command, so `scripts/pin_workspace.mjs` sends the app's pin request through the installed CLI's own daemon client; a Paseo update can break that, and a failed pin does not fail the start. Stdout is one JSON object with the agent, workspace, worktree, branch and base commit, `heartbeat` (its id), `unchecked_hosts` (hosts that could not be listed for a duplicate), `pinned`, and `pin_error` when the pin failed.
3. Tell the operator the agent id, the workspace, the worktree, the heartbeat id, any unchecked host and any `pin_error`, then stop. The owner registers with the orchestrator itself, and since it is not your subagent you get no reports from it.

On another host, run the same command there, with that host's checkout: `ssh <host> python3 '~/.agents/skills/workstream-owner/scripts/start_wks.py' --checkout <checkout> ...`. The hosts file `~/.config/orchestrate/hosts.json` lists each host's checkouts.

| Exit | Meaning | What to do |
| --- | --- | --- |
| 0 | Started, or the dry-run plan. | Report it. |
| 1 | Bad arguments; `error` says which. | Fix them. |
| 2 | Refused; nothing was created. | Read `error`. |
| 3 | Failed or interrupted after it began creating the workspace. The script archived the workspace and deleted the unused branch. | Read `error` and remove what `left` lists, then rerun. |

A refusal for an existing `WKS <name>` workspace, on any host, means the workstream already has its workspace. If that workspace is your own session (a design session handing off its document), rename it without the prefix, `paseo workspace rename <id> "<name> design"`, and rerun. Otherwise report the existing workspace to the operator instead of starting a second owner. A refusal for an existing `wks/<slug>` branch means earlier work used that name; find out whose it is before picking another name.

## Owner contract

This part is for the owner your brief names. You own the workstream until every PR of its plan is merged to main and the orchestrator has taken over the cleanup. You make the engineering decisions. The orchestrator tracks and schedules the work and relays operator decisions. The repository's merge rule names who merges: the orchestrator or the operator. The operator decides product behavior. Follow these steps in order, and return to them after any interruption.

Your launcher gave you a progress heartbeat, `WKS <name> progress`. Every 30 minutes that you sit idle, Paseo sends you a message with a `fired (id=<id>, ...)` line and the heartbeat's instructions: take the next step of this contract, or check once on what you wait on and name it. That line is where you learn the heartbeat's id; `paseo heartbeat` has no list command. Paseo never sends it during a turn, so ending a turn while you wait is safe: the heartbeat brings you back. Use this heartbeat for every wait and create no other. During a wait that will last more than a day, slow it as its message says, and restore it when the wait ends. If you created a heartbeat of your own before this one existed, delete it.

### 1. Load the rules

- `skill://adn-mode` and `skill://adn-mode/references/omp-runtime.md`. Work in ADN mode for the whole workstream: its routing picks the playbook, and its principles apply in every phase.
- The repository's own rules, in your worktree: its `AGENTS.md` (or `CLAUDE.md`), its delivery skill and its PR skill under `.agents/skills/`. The delivery skill is `verified-build` where the repository has one; without one, ADN's Feature playbook and `principle-prove-it-works` define validation. The PR skill is the one the repository's guidance names, else `skill://cmd-create-pr`.
- Your worker brief. Registration (step 2) asks the orchestrator to open an item for the workstream and send you that item's worker brief, rendered by its `render_brief.py` from the repository's project profile. The brief carries the repository's setup, validation, status and landing rules, and who merges. Plan while you wait for it. If it has not arrived when you are ready to build, ask again, and until it arrives follow the orchestrator's own files, at the same paths on every host: `~/.local/share/orchestrate/nod-fleet-tools/orchestrate/references/worker-brief.md`, and the `[merge]` table and `[overlay]` fields of `~/.local/share/orchestrate/nod-fleet-tools/orchestrate/projects/<repo>.toml` over `projects/default.toml` in that directory (the default alone for a repository with no profile). Do not render the brief yourself; the orchestrator's tooling fills it. Operator rulings reach the orchestrator before its files change, so when its latest message differs from the brief, the message wins.
- The source documents in full, comments included. Use `skill://ava` for Ava URLs.

### 2. Register with the orchestrator

Look up the driver each time you write to it, because the driver changes: `ledger header get Driver` prints its agent id and host. Send each message from a file:

- on the driver's host: `paseo send --no-wait --behavior steer <driver> --prompt-file <file>`
- from any other host: `ssh <host> 'paseo send --no-wait --behavior steer <driver> --prompt-file /dev/stdin' < <file>`

If the orchestrator names another route in a message, use that one.

After reading the documents and before building, send:

```text
WKS_START
workstream: <name>
doc: <source URLs>
owner: agent <your id> on <host>, workspace <id> "WKS <name>", worktree <path>, branch <branch>
plan: <one PR, or the split and its reason>; <first milestone>
ask: open an item for this workstream (Repo <repo>, Branch <branch>, Source docs <URLs>, Workspace / agent <host>: <workspace id> / <first 8 hex of your id>) and send me its worker brief, rendered with --worktree <worktree> --base origin/<base> --base-sha <base commit>; record the workstream block for this doc with me as its owner; list every item, PR, branch and agent already working on it, and park those items as owned by agent <first 8 hex of your id>.
```

Work the orchestrator lists becomes yours. Bring its unmerged changes into your branch. Ask each agent working on it to stop pushing and to report its PR, head and review. Name in your reports each PR yours replaces. The orchestrator closes them after yours merges, through its own close procedure (proof, an independent review, then the close); never close one yourself.

Answer every `WKS_STATUS` request immediately, in the format the request gives. Send VALIDATED reports, questions for the operator and plan changes when they happen, without waiting to be asked. If the ledger or the driver cannot be reached, keep building and try again with your next message.

### 3. Plan

Plan the delivery with the repository's delivery skill. Record the plan and your decisions in that skill's run record (verified-build keeps one at `artifacts/verified-build/<run-id>/run.md`), or in the PR body when the repository has no delivery skill.

Ship one PR. Split only for one of these reasons, and write the reason in that record:

- Another workstream or a deploy needs one part on main before the rest can be ready.
- The parts change deployables that are released or rolled back separately, such as a migration that must deploy before the code that reads it.
- The operator or the orchestrator asks for a split.

PR size, easier review and finishing one part sooner are not reasons. Each PR must be mergeable to main on its own; do not stack PRs. Tell the orchestrator about a split before opening the second PR.

A split does not end your ownership at the first merge: you own every PR of the plan, through steps 4 and 5, until the last one merges. You build them all in this worktree, and the orchestrator's cleanup of a merged item archives the workspace that item names. So when you tell it about the split, ask it to keep your workspace and worktree out of the cleanup of every item but the last PR's, and name the PRs still to come in each `WKS_STATUS`. Start each later PR on a new branch cut from `origin/main`, ask for its item and brief as at registration with `Branch <branch>-2` (then `-3`), and push to the PR branch that brief names. The worktree holds one branch at a time; switch back to an earlier PR's branch for its follow-up commits. When the next PR waits on something outside the workstream, such as another workstream's merge, a deploy or an operator action like a ring promotion, name what it waits on in each `WKS_STATUS`, check on it when your progress heartbeat fires, and start that PR once it is unblocked.

Make engineering decisions yourself, and take consequential ones to `@Oracle` first. A question whose answer changes what a user sees goes to the operator through the orchestrator, as a `question:` line in your message. Meanwhile, keep working on everything the question does not block.

### 4. Build and validate

Build and validate as your worker brief and the delivery skill require. In every repository, VALIDATED means the repository's checks pass on the exact PR head, `reviewer-two` APPROVEs that head, and every further gate the brief names (such as a lab run or `worker_done.py`) has passed. Then report it to the orchestrator for that PR's item, in the status format the brief gives. Never call a failure pre-existing or unrelated; when a check fails on current main without your change, report `BLOCKED: MAIN_RED <check>` with the evidence.

### 5. Drive it to merge

Whoever the repository's merge rule names merges your PRs; never merge one yourself unless that rule or a message names you. Until each PR merges:

- Follow the brief's landing rules for when to merge `origin/main` into your branch and what to rerun afterwards. Never rebase, squash or force-push. After any new commit, rerun the checks and the exact-head review, and report VALIDATED with the new head.
- Answer the orchestrator's questions about your PR's place in the merge order. While you wait on a gate or the merge, end the turn and let your progress heartbeat bring you back; never poll within a turn.

### 6. Finish

You are done when all of these are true:

1. `gh pr view <PR> --json state,mergeCommit` shows `MERGED` for every PR of your plan.
2. Your progress heartbeat is deleted (`paseo heartbeat delete <id>`), and the agents you started are gone (`skill://session-cleanup`), so nothing but you runs in your worktree. If the heartbeat has not fired yet, you do not have its id: report your final `WKS_STATUS`, end the turn, and delete it when it next fires. The orchestrator's cleanup, which archives you, also ends it.
3. The orchestrator has your final `WKS_STATUS`, with `prs: none open; merged <URL> @ <merge commit>` for each PR, the PRs yours replace for it to close, and your worktree ready for its cleanup. The orchestrator removes the worktree and the workspace with its cleanup tooling; the worker rules keep you from running `worktree-cleanup`. A production deploy is the operator's action; say so in that message and never offer one.
