---
name: perf-explorer
description: Run an overnight Avalandra performance and failure exploration on a Nodaste-shaped lab, using two parallel Codex computer-use explorers and Paseo investigation agents. Maintain an Ava Development inventory with reproductions, customer impact, proposed fixes, and evidence-backed architectural priorities. Investigate only; never fix the product.
---

# Perf explorer

You are the orchestrator. Set up the lab and inventory, then immediately launch
two Codex explorers through Paseo in parallel. One follows the feature map and
verification paths; the other explores beyond them. Keep working until coverage
is exhausted and investigations are accounted for. Do not stop at a plan, a
successful launch, or the first batch of findings.

This skill's invocation authorizes its lab setup, lab-only test mutations,
Paseo agents, and inventory updates. It does not authorize product fixes,
spec changes, PRs, merges, production deployment, or unsolicited messages to
people. The only production write is the requested Ava inventory document
and its evidence attachments. Never run exploratory actions against that hub.

When asked to author, review, or validate this skill, perform the requested
bounded validation rather than silently starting the full overnight run.

## Load the operating contracts

Read the current repository's `AGENTS.md` and these installed skills:

- `lab-manager` and `verify-ccore` from the CCore repository.
- `ava` and `ava-design-system` for the HTML inventory; `paseo`, `computer-use`, and `cua-driver`, including the host OS and
  browser references. CUA is required for the explorers' UI actions.
- `adn-mode`, its performance investigation playbook, `zero-tech-debt`, and
  the measurement guidance from `principle-explain-the-number`.

Use ADN and zero-tech-debt as investigation and proposal criteria. Their
implementation instructions never override this run's **DO NOT FIX** boundary.
Read [the run contract](references/run-contract.md) before launching agents.
It defines their packets, measurements, inventory fields, and completion bar.

Resolve CCore from the active worktree and verify its repository identity.
Follow its Groma discovery and Backlog guidance. A missing tracking CLI is a
reported setup limitation, not permission to hand-edit its records. No product
source changes are needed for this workflow.

## Work through recoverable obstacles

A problem report is not a stopping condition. The orchestrator, explorers and
investigators must make a reasonable effort to recover within the claimed lab
and their assigned authority, then continue. Preserve the original failure and
its evidence before trying a workaround; successful recovery does not erase a
finding or turn the original path into a pass.

Diagnose the immediate cause, inspect current help and operating contracts, and
try bounded, evidence-driven recovery. Examples include locating an installed
CLI outside PATH, correcting invocation or lab context, renewing an assigned
fixture login through supported access, reconnecting an owned CUA session,
retrying a transient failure, and using another supported product path. Use
reversible lab setup or disposable test-data changes when permitted. Keep
scratch helpers in the run's private directory; make no permanent code changes,
product patches, commits, or implementation PRs.

Stay inside lab claims, access controls, fixture ownership and browser rules.
Do not obtain privileged internal credentials, weaken permission checks, write
to production beyond the authorized inventory, or reset another agent's state.
Explorers and investigators recover
within their own assignments; send shared setup and lifecycle recovery to the
orchestrator, which must attempt permitted remedies rather than merely relay
the blocker. Coordinate changes that affect another agent. Preserve the same
build and corpus for comparable measurements; label changed conditions and
retain the original reproduction.

If recovery fails, record the attempts, results, remaining constraint and next
feasible action. Continue every independent coverage or investigation path and
revisit the blocked path when its prerequisite changes. End the run for a
blocker only when no useful authorized work remains and plausible permitted
remedies have been tried or ruled out with evidence. Do not repeat ineffective
attempts indefinitely or wait on the user while independent work is available.

## Establish one resumable run

Create a unique run ID and private evidence directory, normally
`~/.local/state/perf-explorer/<run-id>/`. Record in `run.md`:

- Checkout, branch, SHA, dirty state, orchestrator session, start time, and
  any user-specified deadline. Default termination is coverage exhaustion,
  not an arbitrary overnight timeout.
- Lab name, non-secret claim ID, provision generation, origin, profile and
  fixture readiness, deployment receipt, capabilities, and observed corpus size.
- Inventory hub, Organization, Development Space, document ID, `web_url`,
  revision, local body path, and last verified body hash.
- Paseo agent IDs, roles, provider/model/reasoning, output directories, browser
  ownership, identity allocations, current work, and outstanding investigations.
- Coverage ledger, issue queue, confirmed groups, blockers, and next action.

Never copy claim credentials, fixture passwords, cookies, tokens, or credential
files into these records or agent prompts. Preserve sanitized evidence across
context compaction. On resume, inspect existing agents, lab and document before
creating anything; resume the same inventory and queue. Do not duplicate agents
whose earlier launch succeeded but whose response was lost.

Before dispatching a creation or update, persist a private `intent.json` with
the exact non-secret payload, operation key, target, timestamp and status.
Ava retries use the same idempotency key and identical payload. Paseo launches
use unique labels for run ID, role and issue ID, saved before dispatch. After
a lost launch response, reconcile agents by those labels/workspace and inspect
the matching prompt. Adopt exactly one match; multiple matches or uncertain
absence remain `launch-unknown` rather than triggering another launch. Store
returned IDs and verified receipts immediately. Never persist secret inputs.

## Set up the lab and tracking document

1. Check installed CLI and CUA availability, Paseo Codex availability, and
   Ava Development access. Use `cua-driver doctor` to establish that a native
   desktop is usable. An installed binary alone is insufficient. Resolve an
   existing authorized desktop session when available; never guess a display
   or silently substitute headless browser automation.
2. Follow `lab-manager` from the claim-owning worktree. Reuse a run-owned claim
   only when its generation, fixture profile and build match. Never borrow an
   unrelated claim or choose a lab by name. Request the published Nodaste-shaped
   profile `large-tenant@v1`, backed by `nodaste-heavy-v1`, plus
   `standard,verify,empty` fixture sets. Request `ambient-agents` and
   `document-pdf-export` capabilities for their UI coverage, using current CLI
   help for repeated capability arguments. Before allocating a lab, verify that
   this build has the supported browser-login path described in step 4. Do not
   start a multi-hour restore when a known missing login contract prevents its
   use. Check published profile metadata without a claim via
   `pnpm --filter @ccore/lab-manager run lab -- fixtures profiles large-tenant@v1`.
   Example checkout shape:

   ```sh
   pnpm --filter @ccore/lab-manager run lab -- checkout \
     --agent codex --session <actual-session-id> --project perf-explorer \
     --profile large-tenant@v1 --fixture-sets standard,verify,empty
   ```

3. Deploy the current intended checkout through
   `pnpm run deploy -- --hub <assigned-lab>` and preserve its successful log.
   Follow `verify-ccore` for `lab.mjs record`, `start`, and `doctor`, using a
   fresh verification home and run ID. Never redeploy during measurement.
   Wait for the manager's profile and fixture assignment to become `ready`.
   Use `fixtures status`, `fixtures profile`, and `inspect`; large-profile
   restore has historically taken hours. Check periodically without a busy
   loop, keep reporting progress, and follow the manager's bounded recovery
   policy on failure. A missing profile or failed restore blocks realistic
   coverage. Never substitute a tiny tenant and call it Nodaste-shaped.
4. Verify imported Space identities, record counts/size from profile receipts
   and bounded product reads, membership access, and actual sign-in. The
   default verify harness Organization may be the small `verify` fixture;
   explicitly target the imported large corpus for performance measurements.
   Profile-ready does not prove browser access: the profile restores a separate
   synthetic Organization, and older builds expose no password identities for
   it. Verify the current supported profile-login contract before checkout.
   Require provisioning to grant the standard fixture credentials their
   intended access, available through normal manager-owned fixture access.
   Prove the standard admin and a second permitted user reach imported data,
   and an outsider is denied. If this path fails, inspect current supported
   fixture-access and login mechanisms and attempt permitted lab recovery
   before declaring it blocked. Do not manually bootstrap memberships, extract
   the manager's import agent key, or add a product/fixture patch. Record any
   remaining access gap and continue independent setup and reachable coverage.
   Reserve isolated fixtures for role, onboarding, and destructive checks and
   label their dataset separately. Leave space-free Organizations space-free.
5. Resolve the inventory's Development Space by `ava space list --json` on
   the user's existing Ava installation. Preserve this inventory context
   separately from every lab `AVA_HOME`, origin and Organization. Create a
   real HTML document titled `Performance exploration inventory - <run-id>`.
   Load `ava` and `ava-design-system`, then follow
   [the HTML dashboard contract](references/html-dashboard.md). Register a JSON
   payload with `source_format: "html"` through `ava document register`; never
   put HTML in a text document or use `document create` / `replace-body` for
   this dashboard. Preserve the local HTML source, exact source/render readbacks,
   warnings, revision and returned `web_url`. Draft standing is sufficient.
   This new document's body is exclusively owned by the run's orchestrator.
   State that ownership in its opening note and direct contributions to
   comments. Do not take over a preexisting collaboratively edited document.
6. Seed the coverage ledger from `.agents/skills/verify-ccore/features/README.md`,
   its linked feature files, manual checklists, and the current Web route map.
   Preserve known gaps and capability prerequisites. Do not copy historical
   passing results. Note CLI/API-only operations separately; API execution
   cannot count as a successful UI action.

Prepare the inventory while the profile loads. Once both are ready, launch the
two explorers immediately, without another planning or approval round.

## Launch the two explorers through Paseo

Read current Paseo profiles and all their notes. Both UI agents must use Codex.
Honor a user-selected model; otherwise select a matching allowed Codex profile.
If none fits, discover supported Codex models and reasoning values, disclose
the fallback, and select an available Codex model. Never select a profile
marked operator-only automatically. Validation/review agents for this skill
use Codex Astra with low reasoning when available, per Aaron's preference.
Do not impose that validation setting on the overnight explorers unless asked.

Use the current `paseo run --help` contract or Paseo `create_agent`, materializing
profile fields as specified by the Paseo skill. Create both agents before
waiting for either. Enable finish notifications and record returned IDs.

- **Walkthrough explorer:** systematically traverse the feature map,
  verification user paths, controls, role/state variants, and durable readback.
- **Fuzzy explorer:** explore realistic combinations and unexpected sequences
  beyond scripted coverage. Vary navigation, data scale, repeated actions,
  cancellation, search, editors, histories, Space switching, and recovery.

Use the packets in the run contract. Give each an independent persistent CUA
transport, driver-owned browser profile/window, assigned lab identity, unique
record prefix, and disjoint evidence directory. Test each session's snapshot,
action and verified postcondition before accepting its first coverage report.
Paseo `browser_*`, Playwright actions, raw CDP actions and API mutations are not
substitutes for the requested computer-use walkthrough. CUA Driver's own typed
browser tools are computer use and are allowed under its contract.

## Inventory, delegate, and reconsider causes continuously

Consume new findings throughout exploration. Agents write only their own
artifacts and report discoveries promptly through the available Paseo return
channel. The orchestrator alone edits the inventory and consolidated ledger.
Record every unexpected failure and every measured operation exceeding
**1000 ms**, including intermittent cases. Keep unmeasured slow observations
as suspected findings awaiting measurement. Expected permission denials are
coverage results unless they fail the contract or are themselves slow.

For each distinct finding, assign a stable `PERF-NNN` ID, save it to Ava
immediately, and spawn a Paseo investigation agent with the reproduction and
same lab/build identity. Duplicate observations update the existing issue and
agent; preserve every occurrence. Keep the two explorers running. Use a bounded
investigator pool, normally two, and a durable queue when capacity is full.
Every queued distinct issue must eventually get its investigation agent or
remain explicitly blocked. No finding may disappear because slots were busy.

Investigators reproduce on the same lab, inspect runtime evidence and relevant
source, explain customer impact, and propose the smallest coherent end-state
change. They must not edit source, apply patches, deploy, reset fixtures, or
create implementation PRs. Unreproduced findings stay in the inventory.

After each new investigation and every batch of explorer findings, reconsider
all issues using ADN and zero-tech-debt. Compare shared paths and measured work,
not just similar symptoms. When evidence connects two or more outcomes to one
underlying design issue, add an `ARCH-NNN` parent with linked symptoms, causal
evidence, confidence, and a proposed architectural change. Raise its priority
above comparable isolated findings; severe data loss or access failures still
take precedence. Keep individual reproductions and original evidence intact.
Unproven common causes remain hypotheses and standalone issues remain standalone.

Maintain the same HTML dashboard using `document edit` with the exact current
`--expected-revision` and one stable idempotency key per identical mutation.
Keep the orchestrator as sole body writer; comments are contributions, not
permission to overwrite another writer. On conflict or unexpected source drift,
preserve the current and pending sources, reread and reconcile before retrying.
Do not force a replacement or create another dashboard to bypass the conflict.
Follow the HTML dashboard contract for source/render/warnings and native visual
verification. If Ava is unavailable, preserve pending HTML locally, continue
independent lab work and retry boundedly. Never report synchronization or visual
verification as complete without the corresponding evidence.

## Finish only with accounted-for coverage

Use the run contract's exhaustion criteria. Ask explorers for missing areas
and targeted follow-ups. Drain investigation work and perform a final causal
grouping review. Attempt permitted recovery from unavailable providers, lost
sessions and lab failures before ending. If a deadline or an unrecoverable
prerequisite ends the run, report explicit incomplete coverage and recovery
attempts, never a claim that everything passed.

Write the final coverage matrix, prioritized inventory, unresolved hypotheses,
blocked paths, same-lab reproduction instructions, and run identity to Ava.
Verify its saved body. End owned CUA sessions and scratch processes after
preserving evidence. Follow verification cleanup only after all reproductions
finish. Preserve the claimed lab and its data for review; release only under
the lab-manager skill's explicit cleanup authorization.

Return the inventory link, failure/slow/architectural-group counts, coverage
gaps, lab disposition, and confirmation that no product fixes were made.
