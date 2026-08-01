---
name: delivery-run
description: Spawn a Herdr worktree from a goal and run plan ↔ review → run-plan → autoreview → visible completeness review → PR with a durable stage ledger, adjacent Grok 4.5 reviewer pane, board visibility, and end-of-run reflections. Use when the operator wants a new worktree started for them, delivery spawn/bootstrap/status/board/reflect, resuming delivery, or attaching a Linear issue later.
---

# Delivery Run

Use this skill to keep each delivery worktree visible in the existing development cycle:

```text
plan ↔ review → run-plan → autoreview → visible completeness review → PR
```

with a visible plan-completeness reviewer, PM/customer-impact notes, and adversarial QA prompts.

This skill is an **orchestrator and scoreboard**, not a replacement for the worker skills.

## From any Pi session: spawn a new delivery worktree

Operators give **one freeform request**. They will not pass flags. Agents infer the rest.

```bash
# Typical human/agent usage — plain language only
delivery spawn -- "honest auto-sync status"
delivery spawn -- "NOD-1457 one login path"          # issue auto-detected
delivery spawn -- "fix comment box jump on doct"

# Rare overrides (agent-only)
delivery spawn --base origin/develop -- "…"
delivery spawn --no-agent -- "…"
delivery spawn --dry-run -- "preview naming"
```

Or: `/delivery:spawn NOD-1457 one login path`

`delivery spawn` auto-derives:
- Linear issue from any `TEAM-123` token in the text
- slug/branch/label from the remaining intent words
- Herdr worktree + delivery bootstrap + child Pi prompt
- a workspace-scoped, Herdr-valid default child-agent name so concurrent runs do not collide
- phase-prefixed Herdr **space** (workspace) + tab labels that update on `delivery stage`

### Herdr space phase codes

Workspace/tab title format: `CODE: base title`

| Code | Stages |
|---|---|
| `PL` | intake + planning through execution-ready |
| `I` | implementing |
| `R` | scoped review, PM outcome, autoreview, visible completeness review, verify, adversarial QA |
| `PR` | PR open / merge-ready |
| `RF` | reflect |
| `D` | done |
| `B` | blocked |

Examples: `PL: NOD-1234 one login path`, `I: NOD-1234 one login path`, `D: honest auto-sync status`.
The descriptive half is always the work title/slug — never the long stage name (`IMPLEMENTING`, `AUTOREVIEW`, …).

`delivery stage …` refreshes the Herdr workspace name best-effort (never hard-fails).

This parent session runs spawn and reports paths; the child worktree agent does the delivery cycle.

## Cold start (already inside a new Herdr worktree / new agent)

If you were just spawned in a worktree, or an operator asked you to start the delivery workflow, do this immediately:

```bash
# Common: no Linear issue yet
delivery bootstrap --slug <feature-slug> --goal "<operator ask>"

# Linear known
delivery bootstrap --issue NOD-123 --goal "<operator ask>"

# Already bootstrapped earlier in this worktree
delivery bootstrap --refresh
```

Then:

1. Read `.delivery/AGENT_BRIEF.md` (written by bootstrap) end-to-end.
2. Run `delivery show` and `delivery check -v`.
3. Execute the brief's **Recommended next step** via the named worker skill.
4. After progress: `delivery stage ...`, `delivery record ...`, `delivery bootstrap --refresh`.

**Linear is optional at start.** When an issue appears later:

```bash
delivery set --issue NOD-123 --retarget-id
delivery bootstrap --refresh
```

**Operator prompt to hand another agent** (copy/paste into a new Herdr pane):

```text
You are in a fresh worktree. Run /delivery:bootstrap with this goal, read .delivery/AGENT_BRIEF.md, then continue the delivery cycle (plan ↔ review → run-plan → autoreview → PR) from the recommended next step. Linear issue is optional; attach later with delivery set --issue KEY --retarget-id. Guidance not gates — do not hard-block on missing delivery evidence.

Goal: <paste goal>
```

## Doctrine: guidance, not gates

- Recommended checks produce **advisories and ledger gaps**.
- Stage transitions always succeed.
- `delivery check` always exits 0, even when evidence is missing.
- A broken optional integration (Doct, Herdr labels, a reviewer flake) must never force the operator to disable the whole workflow.
- Existing skills (`reviewed-html-plan`, `run-plan`, `autoreview`, PM review, `qa:run`) remain authoritative for their work.
- The adjacent **visible completeness review** is the exception to advisory quality evidence for a Herdr delivery run: `delivery stage MERGE_READY` rejects a missing, stale, or unaccepted Grok 4.5 `COMPLETE` verdict unless the operator explicitly waives that review. `delivery check` and all other stage changes remain non-blocking so work can be inspected, corrected, or handed off.
- Firmness is limited to explicit authorization and completion evidence; the rest of the ledger optimizes for visibility, resumability, and honest status.

If guidance and checks/balances are right, agents should usually do the right thing without hard boundaries. Record when they do not, and keep going unless the operator stops the work.

## CLI

Installed as `delivery` (from `skills/delivery-run/scripts/delivery`).

```bash
# Linear/issue is optional at start — attach anytime later
delivery init [--slug my-feature] [--plan thoughts/plans/foo.html] [--stage INTAKE]
delivery init --issue NOD-123 --plan thoughts/plans/foo.html   # also fine when you already have one

delivery set --issue NOD-123                 # attach Linear after the fact
delivery set --issue NOD-123 --retarget-id   # also rebuild id to repo/NOD-123
delivery set --plan thoughts/plans/foo.html --doct-url https://doct... --pr-url https://github.com/...
delivery set --clear-issue

# New agent / new worktree navigator
delivery bootstrap --slug my-feature --goal "what the operator asked"
delivery bootstrap --issue NOD-123 --goal "..."
delivery bootstrap --refresh

# End-of-run reflection (outside worktree → ~/.pi)
delivery stage REFLECT
delivery reflect --trigger end-of-run --outcome done \
  --friction "..." --rework "..." --improvement "..." --mark-done
delivery reflect --list 5

delivery show
delivery status          # current ledger, or board if none
delivery board [--json]  # all known worktree ledgers
delivery stages          # stage → recommended next skill
delivery stage IMPLEMENTING --note "starting run-plan"
delivery note "waiting on product decision about empty states"
delivery record planPm --status pass --artifact thoughts/validation/foo-pm.md --summary "stage-fit ok"
# Opens a visible adjacent Herdr pane running Pi on xai/grok-4.5:high.
delivery completion-review
# After the driving agent fixes its findings, ask that same reviewer again.
delivery completion-review --rerun
# Captures the adjacent pane's latest COMPLETE verdict, writes its artifact, and validates freshness.
delivery completion-review --accept
delivery record completionEval --status gap --gap "BDD3 not evidenced" --summary "one scenario missing"
delivery record customerImpact --status pass --summary "Operators see honest sync status" \
  --promised "honest auto-sync status" --observed "status axes + receipts shipped"
delivery check -v        # soft advisories only; exit 0
delivery blocker "need auth decision" --mark-blocked
delivery blocker --clear --stage IMPLEMENTING
delivery path
```

Ledger path: `<worktree>/.delivery/ledger.json`  
Board scan: cwd + `~/.herdr/worktrees/*/*/.delivery/ledger.json`

## Stages

```text
INTAKE
PLAN_DRAFT
PLAN_BROWSER_REVIEW
PLAN_PM_REVIEW
PLAN_TECH_REVIEW
EXECUTION_READY
IMPLEMENTING
SCOPED_REVIEW
IMPL_PM_OUTCOME
AUTOREVIEW
COMPLETENESS_REVIEW
VERIFY_FRESHNESS
PR_OPEN
MERGE_READY
ADVERSARIAL_QA
DONE
BLOCKED
```

Move freely in either direction. The plan loop is expected to bounce among `PLAN_*` stages.

## Recommended cycle (soft)

### 1. Start or resume

Most work starts without a Linear issue. That is normal.

```bash
delivery init --slug <feature-slug> --plan <plan-path>   # no issue yet
# later, when Linear exists:
delivery set --issue <KEY> --retarget-id

# or, if you already have an issue:
delivery init --issue <KEY> --plan <plan-path>

delivery show
delivery check -v
```

### 2. Plan ↔ review

| Stage | Recommended skill |
|---|---|
| `PLAN_DRAFT` | `$dev-plan` / `$reviewed-html-plan` |
| `PLAN_BROWSER_REVIEW` | `doct-document-ops` listener; integrate feedback and wait for the explicit execution-ready review request |
| `PLAN_PM_REVIEW` | after that request, `/dev:pm-review <plan> plan` |
| `PLAN_TECH_REVIEW` | after that request, active-harness `reviewer` via reviewed-html-plan |
| `EXECUTION_READY` | pause, summarize the reviewed plan and implementation profile, then obtain explicit operator approval |

#### Browser-feedback escalation rule

A browser comment is not automatically a readiness-review request. While the ledger
is at `PLAN_BROWSER_REVIEW`:

- A routed generic comment (`routingMetadata.submitAction: "agent"` without
  `routingMetadata.agentRoute.requestedSkill`) is feedback to integrate and
  acknowledge. Keep listening in `PLAN_BROWSER_REVIEW` after updating the plan.
- Do **not** advance to PM or technical review because the first comment was
  handled, the listener became quiet, or `planBrowserReview` is marked `pass`.
- Start the PM/technical readiness cycle only when the operator explicitly asks
  for it or clicks Doct's **Request execution-ready review** control. The current
  control emits
  `routingMetadata.agentRoute.requestedSkill: "plan-reviewer-execution-ready"`.
  Treat a Doct `submitAction: "execution-ready"` as the same explicit request
  when that form is returned by the service.
- Before advancing, record the signal:

```bash
delivery record planReadinessRequest --status pass \
  --summary "Doct execution-ready review request"
delivery stage PLAN_PM_REVIEW
```

This is an authorization boundary: `delivery stage PLAN_PM_REVIEW`, `PLAN_TECH_REVIEW`, and `EXECUTION_READY` reject a missing or stale `planReadinessRequest=pass` record. The record is tied to the current plan content, so a changed plan requires a fresh explicit readiness request before the review cycle can begin. Other delivery evidence remains advisory.

After each meaningful step:

```bash
delivery stage <STAGE>
delivery record <key> --status pass|skip|gap|na --artifact <path> --summary "..."
```

### 2a. Execution-ready approval pause

`EXECUTION_READY` is a pause, not an automatic handoff to `$run-plan`. At that stage,
keep the Doct listener active and give the operator a concise summary of:

1. the current plan/review status and residual non-blocking observations;
2. the customer-visible and technical changes implementation will make;
3. the exact implementation model and reasoning level selected for the run; and
4. the remaining implementation, test, review, verification, and PR steps.

Ask whether to proceed. Do not change product code, invoke `$run-plan`, or move to
`IMPLEMENTING` until the operator directly approves in chat or uses a deliberate Doct
implementation-approval action. Record the approval against the current plan content,
then start execution:

```bash
delivery approve-implementation --source chat|doct \
  --summary "Operator received plan status, changes, model/reasoning, and remaining steps"
delivery stage IMPLEMENTING
# only now: /skill:run-plan <plan>
```

The CLI rejects readiness-review stages without a current explicit readiness-request fingerprint and rejects `delivery stage IMPLEMENTING` without a current approval fingerprint. These are authorization boundaries, not quality-evidence advisories.
If the plan changes or material browser feedback arrives before implementation, reply and
update the plan, then invalidate the approval and return to browser review:

```bash
delivery revoke-implementation-approval --reason "material plan feedback"
delivery stage PLAN_BROWSER_REVIEW
```

A fresh explicit **Request execution-ready review** action and fresh readiness review are
required before a new operator approval. Generic feedback, a quiet listener, readiness
metadata, and an old approval never authorize implementation.

### 3. Implement through PR

| Stage | Recommended skill |
|---|---|
| `IMPLEMENTING` | `$run-plan` |
| `SCOPED_REVIEW` | run-plan scoped quality review |
| `IMPL_PM_OUTCOME` | `/dev:pm-review <plan> implementation` |
| `AUTOREVIEW` | `$autoreview` |
| `COMPLETENESS_REVIEW` | visible adjacent Pi/Grok 4.5 reviewer; resolve feedback and rereview until `COMPLETE` |
| `VERIFY_FRESHNESS` | final verify + base freshness inside run-plan |
| `PR_OPEN` | run-plan / `$cmd-create-pr` |
| `MERGE_READY` | run-plan local merge-readiness |

### 4. Soft quality inserts

These are **recommended evidence**, not blockers.

**Visible completeness review** before final verification / local merge readiness:

```bash
delivery stage COMPLETENESS_REVIEW
# Splits the driving pane right without stealing focus, starts Pi with
# --model xai/grok-4.5:high, and submits the visible read-only review packet.
delivery completion-review

# Read the adjacent review. Fix every in-plan finding, then ask the same agent
# to inspect the updated live worktree. Repeat until it returns VERDICT: COMPLETE.
delivery completion-review --rerun
# Captures the current COMPLETE verdict and artifact; only this validates merge-readiness evidence.
delivery completion-review --accept
delivery record completionEval --status pass --summary "AC1-AC4 evidenced; BDD green"
```

The reviewer is read-only. It evaluates the plan against the actual current worktree, including post-mutation UI states, required wiring, and verification evidence. The driving agent owns fixes and tests. Each request has a unique ID, and `--accept` accepts only a matching current `COMPLETE` response, so an earlier pane response cannot certify a rereview. A `FINDINGS_TO_RESOLVE` verdict requires an in-scope fix and rereview. A missing reviewer or a `BLOCKED_BY_QUESTION` verdict blocks a local merge-readiness claim unless the operator explicitly waives the review.

**Customer impact** at plan PM and implementation PM:

```bash
delivery record customerImpact --status pass \
  --summary "Customer can recover from stale sync without support" \
  --promised "honest status" --observed "status axes + receipts"
```

**Adversarial QA** when the plan touches customer-visible paths (UI, onboarding, auth, sync honesty, permissions):

```bash
delivery stage ADVERSARIAL_QA
# run /qa:run or manual golden-path adversarial checks
delivery record adversarialQa --status pass --artifact thoughts/qa/findings.md
# backend-only / no customer path:
delivery record adversarialQa --status na --summary "no customer-visible path"
```

Early-stage lens (&lt;20 customers): no silent data lies, no fake success, recoverable errors, one obvious golden path. Not enterprise breadth.

### 5. Board visibility

```bash
delivery board
delivery board --json
```

Optional best-effort Herdr tab rename uses `HERDR_TAB_ID` when present. Failures are ignored. Set `DELIVERY_SKIP_HERDR=1` to disable.

### 6. End-of-run reflection (every workflow)

Before `DONE` / hand-off, capture process learning **outside the worktree** (same idea as vent):

```bash
delivery stage REFLECT
delivery reflect --trigger end-of-run --outcome pr-opened \
  --friction "reviewer isolation dropped dirty fixes twice" \
  --rework "had to re-run autoreview after false FAIL" \
  --improvement "preflight live-worktree check before reviewer launch" \
  --mark-done
```

Writes:
- `~/.pi/DELIVERY_REFLECTIONS.md` — human log
- `~/.pi/delivery-reflections.jsonl` — one JSON object per reflection for later processing

In Pi, the `delivery_reflect` tool is equivalent. Guidance not gates: missing reflection is an advisory, not a hard stop — but ending a delivery run without one is discouraged.

Prefer process-shaped notes (friction, retries, unclear guidance, handoff gaps), not ordinary code bugs.

## Agent operating rules

1. Prefer keeping the ledger current over perfect process compliance.
2. When invoking a worker skill, set the matching stage first when practical.
3. After a worker skill finishes, `delivery record` what happened and `delivery check -v`.
4. Treat check advisories as a to-do list, not a red light.
5. Do not stop the operator solely because recommended evidence is `pending` or `gap`, except that a Herdr delivery run cannot claim local merge readiness without a validated visible `completion-review --accept` result or an explicit operator waiver.
6. At `COMPLETENESS_REVIEW`, run `delivery completion-review`; read the adjacent Grok 4.5 pane, fix its in-plan findings, and call `delivery completion-review --rerun` until it returns `VERDICT: COMPLETE`. Run `delivery completion-review --accept` to capture and validate its artifact before final readiness.
7. Treat generic browser feedback as plan iteration; wait for the explicit execution-ready review action before PM or technical readiness review. Record that request before trying to move out of browser review; the stage command enforces it.
8. Treat execution-ready as eligibility only: present the approval summary and wait for explicit operator permission before implementation. Invalidate that permission if material feedback changes the plan.
9. Do not reimplement run-plan/autoreview/reviewed-html-plan here.
10. If something is truly stuck on a human decision, `delivery blocker "..." --mark-blocked` and say what is needed — still leave the workflow usable.
11. Before finishing (`DONE` / hand-off), run `delivery reflect` (or Pi `delivery_reflect`) so friction/rework/improvements land in `~/.pi` outside the worktree.

## Invocation

```text
/skill:delivery-run
/skill:delivery-run <issue-or-plan>
/delivery:run
/delivery:status
```

When used as the primary controller for a change:

1. `delivery bootstrap` / `delivery show`
2. Follow `delivery check` next-step guidance
3. Call the named existing skill
4. Record evidence and advance stage
5. At `COMPLETENESS_REVIEW`, run the visible adjacent Grok reviewer to `COMPLETE`, then run `delivery completion-review --accept`
6. Repeat until ready to finish
7. `delivery reflect ... --mark-done` (logs to `~/.pi`, not the git tree)

## Non-goals

- Generic hard gates or tool locks; the explicit implementation authorization and visible completeness-review readiness rule are the narrow exceptions
- Replacing worker skills
- Multi-ticket fan-out scheduler
- Web dashboard
- Post-merge delivery health (separate concern)
