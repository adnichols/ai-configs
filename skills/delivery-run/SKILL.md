---
name: delivery-run
description: Explicit opt-in for the shared delivery workflow for OMP or Pi. Use only when the operator says "arm our delivery workflow", invokes /delivery or delivery arm, invokes delivery spawn / /delivery:spawn, or asks to attach delivery for review/completeness/PR after a non-delivery implementation. Do not trigger for generic planning, implementation, execute, run-plan, PR, Linear, worktree, autonomous-build, or continuation requests, or for another named workflow such as prewalk.
---

# Delivery Run

## Explicit opt-in boundary

Delivery has one operator entrypoint. Arm it only when the operator says
"arm our delivery workflow", invokes `/delivery` or `delivery arm`, or
invokes `delivery spawn` / `/delivery:spawn` (new-worktree form of the same
arm). The same entrypoint also covers a late attach: after a non-delivery
implementation, the operator may ask to use delivery for review, completeness,
and PR — run `delivery arm --from existing-implementation` and do not launch
an implementation pane.

Do not treat "start delivery", "run this through delivery", `execute`,
`/run-plan`, `/prewalk`, `/delivery:run`, `/delivery:bootstrap`, or
`/skill:delivery-run` as authorization to create a ledger. Those commands
operate a ledger that is already armed, or they are not delivery. The presence of
this skill, the `delivery` CLI, a Linear issue, a worktree, a plan, `run-plan`,
or another execution workflow is not authorization to arm delivery. In
particular, do not bootstrap or initialize delivery for generic
build/implement/plan/PR requests or when the operator selects another named
workflow such as prewalk.

`/prewalk` and delivery are mutually exclusive while both would be live.
If prewalk is still armed, refuse to arm delivery. If a delivery ledger already
exists, refuse `/prewalk`. After prewalk has switched and disarmed, a late
delivery attach is allowed.

An existing `.delivery/ledger.json` may be inspected or continued only when the
operator explicitly asks to inspect, resume, or continue that delivery run, or
when the current agent was launched by an explicitly invoked delivery command.
Never create a ledger merely because delivery tooling is available.

After that activation condition is satisfied, select the runtime before
operating the shared delivery state machine:

- **OMP session:** use `runtime=omp`, `workflowProfile=omp-lite`, and the OMP
  path in this skill.
- **Pi session:** use `runtime=pi`, `workflowProfile=pi-full`, and the Pi path
  in this skill.

Never infer Pi merely because this skill originated in the shared
configuration repository. Never create a second ledger or translate the
workflow into ad hoc todos.

```text
plan ↔ independent readiness review → implementation → scoped review →
PM outcome → pre-PR review → independent completeness review → verify → PR
```

This skill is an **orchestrator and scoreboard**, not a replacement for the
worker skills.

## From any session: spawn a new delivery worktree

Operators give **one freeform request**. They will not pass flags. Agents infer
the rest, but runtime selection is mandatory.

```bash
# OMP — use this when the current agent is running in OMP
delivery spawn --runtime omp -- "honest auto-sync status"
delivery spawn --runtime omp -- "NOD-1457 one login path"

# Pi — use this only when the current agent is running in Pi
delivery spawn --runtime pi -- "fix comment box jump on doct"

# Rare overrides (agent-only)
delivery spawn --runtime omp --base origin/develop -- "…"
delivery spawn --runtime omp --no-agent -- "…"
delivery spawn --runtime omp --dry-run -- "preview naming"
```

Pi also exposes `/delivery:spawn ...`; OMP does not require a Pi prompt
command. In OMP, invoke `delivery` directly.

`delivery spawn` auto-derives:
- Linear issue from any `TEAM-123` token in the text
- slug/branch/label from the remaining intent words
- Herdr worktree + delivery bootstrap + a child agent matching the selected runtime
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

This parent session runs spawn and reports paths; the child worktree agent does
the delivery cycle. When already inside the target worktree, bootstrap there
instead of spawning a nested worktree.

## Cold start (already inside a new Herdr worktree / new agent)

If you were just spawned in a worktree, or an operator asked you to arm/start
delivery for the current worktree, do this immediately:

```bash
# OMP, no Linear issue yet
delivery bootstrap --runtime omp --slug <feature-slug> --goal "<operator ask>"

# OMP, Linear known
delivery bootstrap --runtime omp --issue NOD-123 --goal "<operator ask>"

# Pi equivalents
delivery bootstrap --runtime pi --slug <feature-slug> --goal "<operator ask>"
delivery bootstrap --runtime pi --issue NOD-123 --goal "<operator ask>"

# Already bootstrapped earlier in this worktree
delivery bootstrap --refresh
```

1. Read `.delivery/AGENT_BRIEF.md` (written by bootstrap) end-to-end when present. If it is absent, continue from `delivery show`, the ledger, and the plan; optionally recreate it with `delivery bootstrap --refresh`. A missing brief is not a code-work blocker.
2. Run `delivery show` and `delivery check -v`.
3. Execute the brief's **Recommended next step** via the named worker skill.
4. After progress: `delivery stage ...`, `delivery record ...`, `delivery bootstrap --refresh`.

**Linear is optional at start.** When an issue appears later:

```bash
delivery set --issue NOD-123 --retarget-id
delivery bootstrap --refresh
```

**Operator prompt to hand another OMP agent** (copy/paste into a new Herdr pane):

```text
You are in a fresh worktree. Read skill://delivery-run, bootstrap with
runtime=omp, read .delivery/AGENT_BRIEF.md, then continue the OMP Lite delivery
cycle from the recommended next step. Linear is optional; attach it later with
delivery set --issue KEY --retarget-id.

Goal: <paste goal>
```
For Pi, use `/delivery:bootstrap` and the Pi Full cycle instead.

## OMP Lite path

When the current runtime is OMP, this section overrides every Pi-specific
launch, model-profile, slash-command, and visible-Grok instruction elsewhere
in this skill.

1. Arm the current worktree with
   `delivery bootstrap --runtime omp --slug <slug> --goal "<ask>"`, or spawn a
   new OMP-owned worktree with `delivery spawn --runtime omp -- "<ask>"`.
2. Confirm `delivery show` reports `runtime: omp` and
   `workflowProfile: omp-lite`. A mismatch is a hard stop; do not continue on a
   Pi ledger.
3. Keep the current OMP agent as owner from planning through implementation.
   `delivery stage EXECUTION_READY` records authorization only; it does not
   launch a replacement Pi agent, choose a Pi model profile, or require OMP
   native plan mode.
4. Materialize the plan, request one bounded independent readiness review with
   the configured OMP `@planner`, resolve findings within the review-cycle
   limit, and record the current request/evidence. Do not enter
   `IMPLEMENTING` until the CLI accepts `EXECUTION_READY`.
5. Implement directly in the driving OMP session, whose configured default is
   `openai-codex/gpt-5.6-luna:xhigh`. Run implementation, scoped review, and
   PM outcome review there; use `openai-codex/gpt-5.6-terra:high` when correctness
   depends materially on technical judgment; run the configured OMP `@reviewer` pre-PR review
   and verification; record each result with `delivery record`.
6. At `COMPLETENESS_REVIEW`, run
   `delivery completion-review --prepare --reviewer-identity
   omp-completeness-grok-4.5-high`. Give the emitted packet to
   `@completeness`, pinned to `xai/grok-4.6:high`; it must write its result to
   the exact packet artifact using the exact seven-line envelope. Accept only
   with the emitted `acceptCommand`. On `INCOMPLETE`, fix the findings and
   prepare a fresh request.
7. Stage `VERIFY_FRESHNESS`, create the PR with repository conventions, record
   the PR URL, then stage `PR_OPEN` and `MERGE_READY`. `ADVERSARIAL_QA` and
   `REFLECT` are optional OMP actions recorded without exposing extra OMP
   phases; finish at `DONE`.

OMP Lite visible phase codes are only `PL`, `I`, `R`, `PR`, `D`, and `B`.
Detailed stages remain in `.delivery/ledger.json`; do not surface Pi-only
ceremony in OMP status labels. Run `delivery stages` and `delivery check -v`
for the current exact next-step and evidence contract.

## Doctrine: guidance, not gates

- Recommended checks produce **advisories and ledger gaps**.
- Most stage transitions succeed even with advisory evidence gaps.
- `delivery check` always exits 0, even when evidence is missing.
- A broken optional integration such as Herdr labels must never force the operator to disable the whole workflow. Explicit readiness and completeness boundaries fail closed and report a retry command. Pi Full additionally enforces its plan-review and implementation-profile boundaries.
- Runtime-specific worker skills remain authoritative: OMP uses the configured `@planner`, `@reviewer`, and Grok-high `@completeness` contracts plus direct Terra-high driving-session implementation; Pi Full uses `reviewed-html-plan`, `run-plan`, `autoreview`, PM review, and its visible Grok reviewer.
- Completeness is the exception to advisory quality evidence. OMP Lite requires a fresh accepted `@completeness` envelope from `xai/grok-4.6:high`; Pi Full requires a fresh accepted labeled-tab Grok 4.6 `COMPLETE` verdict unless the operator explicitly waives it. `delivery stage MERGE_READY` rejects missing or stale evidence.
- Firmness is limited to explicit readiness authorization, the selected runtime/profile, and runtime-specific completion evidence; the rest of the ledger optimizes for visibility, resumability, and honest status.
- Pi Full implementation runs cannot enter `DONE` until current implementation, scoped review, PM outcome, pre-PR review, completeness, verification, PR, customer-impact/completion, and adversarial-QA disposition evidence is recorded. OMP Lite cannot enter `PR_OPEN` or `MERGE_READY` without `implPm`, `autoreview`, and a current accepted request-bound completeness artifact, and cannot enter `DONE` without those plus `verify`, `pr`, and `prUrl`. Planning-only runs that never entered `IMPLEMENTING` may still finish without a PR.
- Planning readiness has a three-cycle convergence budget. Every `planTech=gap` consumes one cycle; after three gaps, stop with a blocker or explicit operator decision rather than launching another ordinary review.

If guidance and checks/balances are right, agents should usually do the right thing without hard boundaries. Record when they do not, and keep going unless the operator stops the work.

## CLI

Installed as `delivery` (from `skills/delivery-run/scripts/delivery`).

```bash
# Single operator entrypoint. Creates the ledger. Never call this from run-plan/prewalk.
delivery arm [--plan thoughts/plans/foo.html] [--issue NOD-123] [--slug my-feature]
# Late attach after a non-delivery implementation (review / completeness / PR only):
delivery arm --from existing-implementation --plan thoughts/plans/foo.html

# Linear/issue is optional at start — attach anytime later
# `init` is a low-level test/internal helper. Agents arm with `delivery arm`.
delivery init [--slug my-feature] [--plan thoughts/plans/foo.html] [--stage INTAKE]
delivery init --issue NOD-123 --plan thoughts/plans/foo.html   # also fine when you already have one

delivery set --issue NOD-123                 # attach Linear after the fact
delivery set --issue NOD-123 --retarget-id   # also rebuild id to repo/NOD-123
delivery set --plan thoughts/plans/foo.html --doct-url https://doct... --pr-url https://github.com/...
delivery set --clear-issue

# New agent / new worktree navigator (always name the runtime on first bootstrap)
delivery bootstrap --runtime omp --slug my-feature --goal "what the operator asked"
delivery bootstrap --runtime pi --issue NOD-123 --goal "..."
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
delivery note "waiting on product decision about empty states"
delivery record planPm --status pass --artifact thoughts/validation/foo-pm.md --summary "stage-fit ok"
delivery record planTech --status pass \
  --artifact thoughts/validation/foo-plan-review.md \
  --summary "independent Sol medium review" --reviewer planner \
  --model openai-codex/gpt-5.6-sol --reasoning-level medium \
  --verdict PLAN_EXECUTION_READY \
  --implementation-profile luna-xhigh \
  --implementation-rationale "deterministic tests support the default Luna implementation"
# Use --implementation-profile terra-high instead when correctness depends materially
# on technical judgment beyond the available deterministic tests.
# Entering EXECUTION_READY automatically authorizes the reviewed plan and launches
# a dedicated Herdr Pi agent on the planner-selected profile.
delivery stage EXECUTION_READY
# Rare compatibility/manual override before launch:
delivery stage EXECUTION_READY --hold
delivery approve-implementation --source chat --summary "Deliberate manual model override" \
  --model openai-codex/gpt-5.6-terra --reasoning-level high \
  --override-reason "manual choice for this run"
# Run by the newly launched implementation agent:
delivery verify-implementation-profile
# If the recorded implementation pane was deliberately switched to another model:
delivery verify-implementation-profile --adopt-current-runtime \
  --reason "manual choice for this run"
delivery stage IMPLEMENTING --note "starting run-plan"
# Opens a visible labeled Herdr tab running Pi on xai/grok-4.6:high.
delivery completion-review
# After the driving agent fixes its findings, ask that same named reviewer again in its existing tab.
delivery completion-review --rerun
# Captures the completeness tab's latest COMPLETE verdict, writes its artifact, and validates freshness.
delivery completion-review --accept
delivery record completionEval --status gap --gap "BDD3 not evidenced" --summary "one scenario missing"
delivery record permanentDocs --status pass|skip|gap --summary "disposition=... paths=..."
delivery record customerImpact --status pass --summary "Operators see honest sync status" \
  --promised "honest auto-sync status" --observed "status axes + receipts shipped"
delivery check -v        # soft advisories only; exit 0
delivery blocker "need auth decision" --mark-blocked
delivery blocker --clear --stage IMPLEMENTING
delivery path
```

Ledger path: `<worktree>/.delivery/ledger.json`  
Board scan: cwd + `~/.herdr/worktrees/*/*/.delivery/ledger.json`

Delivery reconciles operator attention from the resulting ledger after every write. Routine `EXECUTION_READY` handoff is automatic and does not request operator attention. An explicit `BLOCKED` stage uses the latest blocker text; stage exit or blocker clear derives and publishes the next state rather than relying on paired events. `DELIVERY_SKIP_HERDR=1` disables both attention and labels. Completeness review and advisory gaps are agent-owned work and never set operator-blocked attention.

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
| `PLAN_DRAFT` | `$dev-plan` / `$reviewed-html-plan` — pick one canonical title and write it everywhere before register: Markdoc YAML `title:` (+ matching `#` heading if present), HTML both `<title>` and `<h1>`, and `doct-agent plans register --title`. Doct document/tree name and in-content chrome must be identical; Markdoc without frontmatter `title:` shows **Untitled Plan**. |
| `PLAN_BROWSER_REVIEW` | `doct-document-ops` listener; integrate feedback and wait for the explicit execution-ready review request. `delivery check` warns with `PLAN_TITLE` if titles are missing, HTML `<title>`/`<h1>` disagree, or an explicitly recorded Doct title (`delivery set --doct-title` after `documents get`) drifts from content — fix all sides before review handoff. |
| `PLAN_PM_REVIEW` | after that request, `/dev:pm-review <plan> plan` |
| `PLAN_TECH_REVIEW` | after that request, independent `planner` pinned to `openai-codex/gpt-5.6-sol` at medium |
| `EXECUTION_READY` | automatically authorize the reviewed plan and launch the dedicated planner-selected implementation agent |

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

This is an authorization boundary: `delivery stage PLAN_PM_REVIEW` and `PLAN_TECH_REVIEW` reject a missing or stale `planReadinessRequest=pass` record. `EXECUTION_READY` additionally requires a current `PLAN_EXECUTION_READY` artifact from the independent `planner` subagent with model `openai-codex/gpt-5.6-sol` and medium reasoning. That planner chooses `luna-xhigh` by default, or `terra-high` when correctness depends materially on technical judgment beyond the available deterministic tests, and records a concise rationale. Both records are tied to the current plan content, so a changed plan requires a fresh explicit request and fresh Sol-medium review. When `agenticPlan` is set (dual-plan trial), `EXECUTION_READY` also requires a current `planSync=pass` binding operator and agentic fingerprints; missing/stale companions fail closed. Other delivery evidence remains advisory.

After each meaningful step:

```bash
delivery stage <STAGE>
delivery record <key> --status pass|skip|gap|na --artifact <path> --summary "..."
```

### 2a. Oracle decision support

Load `oracle-consultation` and invoke Oracle proactively when targeted evidence leaves one consequential technical choice or drift from locked decisions unresolved. Record the verified disposition in the plan decisions/deviations log or delivery coverage ledger when it affects the run.

Oracle cannot authorize product-changing expansion, replace Doct or operator decisions, satisfy readiness or implementation review gates, substitute for completeness review, or add review cycles.

### 2b. Automatic execution-ready handoff

`EXECUTION_READY` is the automatic handoff from reviewed planning to implementation. In a Herdr delivery run, entering this stage records workflow authorization for the exact reviewed plan, creates a labeled **implementation owner** tab, starts the planner-selected implementation runtime, claims ledger `workspaceOwner` for that tab, and prompts it to continue through implementation, verification, bounded reviews, completeness review, and PR creation. The planning agent stops after the handoff; it does not ask for another routine approval. The planning tab is enqueued for retirement and is closed when the implementation agent runs `delivery verify-implementation-profile` (never self-closed mid-launch). Workspace chrome follows `workspaceOwner`, not ambient `HERDR_TAB_ID`. Failed `agent start` attempts close their shell tabs immediately.

On the **opt-in dual-plan hydrate trial** (`agenticPlan` set), that owner tab launches on Luna xhigh with `--delivery-hydrate --prewalk-into <executor>` rather than cold-starting the executor alone. Generic `/prewalk` outside delivery remains a separate named workflow and does not arm delivery.

```bash
delivery stage EXECUTION_READY
# In the automatically launched implementation agent:
delivery verify-implementation-profile
delivery stage IMPLEMENTING
/skill:run-plan <plan>
```

Use `delivery stage EXECUTION_READY --hold` only for a deliberate operator-requested pause or a known external dependency. `approve-implementation` remains a compatibility/manual-override command after a hold; a deliberate model/reasoning override must include `--override-reason`.

The CLI rejects readiness-review stages without a current explicit readiness request and rejects `EXECUTION_READY` without the Sol-medium planner verdict. When `agenticPlan` is set, it also rejects without current `planSync=pass`, authorizes a Luna xhigh **hydrate** launch with the planner-selected **executor** pair (`luna-xhigh` or `terra-high`), arms delivery-owned prewalk (`--delivery-hydrate`), and advances `hydrateProtocol` through `delivery verify-implementation-profile` (hydrate-verified → executor-verified). Executor-verified requires a real `.delivery/hydrate-transition.json` receipt from the first edit/write transition (not prompt-only adoption). Before `IMPLEMENTING`, it requires current workflow authorization, implementation-agent launch evidence, the exact plan fingerprint, **executor-verified** (dual-plan) or matching live Pi runtime (legacy), the recorded Herdr pane, and a matching live Pi runtime. Legacy Pi Full (no `agenticPlan`) and OMP Lite remain unchanged. `start-implementation` retries a failed launch; when Herdr reports the expected Pi agent after a start race, delivery reconciles that live agent instead of leaving a false `start-failed` record. An exclusive per-worktree launch lease plus ledger revisions rejects concurrent launches and stale writers.

If material browser feedback changes the contract before implementation begins, update the plan, revoke the authorization, and return to browser review:

```bash
delivery revoke-implementation-approval --reason "material plan feedback"
delivery stage PLAN_BROWSER_REVIEW
```

A fresh explicit **Request execution-ready review** action and fresh readiness review are required after a material contract change. Progress bookkeeping during implementation is not a new readiness request: record phase progress in the delivery/coverage ledger and synchronize plan checkboxes to Doct once before completeness review so bookkeeping does not invalidate the live implementation handoff.

### 3. Implement through PR

| Stage | Recommended skill |
|---|---|
| `IMPLEMENTING` | `$run-plan` |
| `SCOPED_REVIEW` | run-plan scoped quality review |
| `IMPL_PM_OUTCOME` | `/dev:pm-review <plan> implementation` |
| `AUTOREVIEW` | `$autoreview` |
| `COMPLETENESS_REVIEW` | visible labeled-tab Pi/Grok 4.6 reviewer; resolve feedback and rereview until `COMPLETE` |
| `VERIFY_FRESHNESS` | final verify + base freshness inside run-plan |
| `PR_OPEN` | run-plan / `$cmd-create-pr` |
| `MERGE_READY` | run-plan local merge-readiness |

### 4. Soft quality inserts

These are **recommended evidence**, not blockers. `permanentDocs` is recommended visibility for Heddle/local permanent-doc disposition (`pass|skip|gap`); it does not create a completeness-class hard stage reject—`run-plan` and `cmd-create-pr` own that hard stop.

**Visible completeness review** before final verification / local merge readiness:

```bash
delivery stage COMPLETENESS_REVIEW
# Creates a short-lived completeness witness tab (not workspace owner); closed after --accept/--waive.
delivery completion-review

# Read the labeled completeness tab. Fix every in-plan finding, then ask the same named agent
# to inspect the updated live worktree. Repeat until it returns VERDICT: COMPLETE.
delivery completion-review --rerun
# Captures the current COMPLETE verdict and artifact; only this validates merge-readiness evidence.
delivery completion-review --accept
delivery record completionEval --status pass --summary "AC1-AC4 evidenced; BDD green"
```

The reviewer is read-only. It evaluates the plan against the actual current worktree, including post-mutation UI states, required wiring, and verification evidence. The driving agent owns fixes and tests. Each request has a unique ID, and `--accept` accepts only a matching current `COMPLETE` response, so an earlier response in the reviewer tab cannot certify a rereview. A `FINDINGS_TO_RESOLVE` verdict requires an in-scope fix and rereview. A missing reviewer or a `BLOCKED_BY_QUESTION` verdict blocks a local merge-readiness claim unless the operator explicitly waives the review.

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
6. At `COMPLETENESS_REVIEW`, run `delivery completion-review`; while the witness tab is live, read the labeled Grok 4.6 tab, fix its in-plan findings, and call `delivery completion-review --rerun` until it returns `VERDICT: COMPLETE`. Run `delivery completion-review --accept` to capture the artifact and retire the witness tab. After accept, the artifact is authoritative—do not require the closed TUI.
7. Treat generic browser feedback as plan iteration; wait for the explicit execution-ready review action before PM or technical readiness review. Record that request before trying to move out of browser review; the stage command enforces it.
8. Treat execution-ready as automatic implementation authorization for a delivery-managed run: `delivery stage EXECUTION_READY` launches the recommended profile on a new owner tab and the planning agent stops. Do not wait for another routine approval. Use `--hold` only when the operator explicitly requests a pause or a real external dependency blocks execution; invalidate authorization and launch evidence if material feedback changes the plan. After handoff, do not keep or inspect the planning tab—use the plan path, ledger, and validation artifacts.
9. The implementation agent must run `delivery verify-implementation-profile` before entering `IMPLEMENTING`; the stage gate independently checks the live Pi provider/model/reasoning environment.
10. Do not reimplement run-plan/autoreview/reviewed-html-plan here.
11. If something is truly stuck on a human decision, `delivery blocker "..." --mark-blocked` and say what is needed — still leave the workflow usable.
12. Before finishing (`DONE` / hand-off), run `delivery reflect` (or Pi `delivery_reflect`) so friction/rework/improvements land in `~/.pi` outside the worktree.

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
5. At `COMPLETENESS_REVIEW`, run the visible labeled-tab Grok reviewer to `COMPLETE`, then run `delivery completion-review --accept`
6. Repeat until ready to finish
7. `delivery reflect ... --mark-done` (logs to `~/.pi`, not the git tree)

## Non-goals

- Generic hard gates or tool locks; the explicit implementation authorization and visible completeness-review readiness rule are the narrow exceptions
- Replacing worker skills
- Multi-ticket fan-out scheduler
- Web dashboard
- Post-merge delivery health (separate concern)
