# Plan: Loosen agent guidance, Socratic planning, supervisor counterweight

**Status:** EXECUTION_READY — Pi review consensus (gpt-5.6-sol high, 6 rounds, 2026-07-23). Execution not yet started.
**Date:** 2026-07-23
**Motivation:** The heddle 0.2.48–0.2.51 regression chain. Every escaped regression lived one hop outside a declared scope boundary. Post-incident audit found the guidance stack's prohibitions acted as *attention* barriers, not just *action* barriers, for a literal-minded executing model. The correction: fewer rules, a Socratic planning format, a trajectory-guarding supervisor, and rigor relocated into tests.

## Harness scope and authority hierarchy

The main development harness is **Pi**: `_pi/prompts/` + `_pi/agents/` (`planner`, `reviewer`, `scout`; `Explore.md` is a **disabled override**, not an active agent) → `~/.pi/agent/`; shared `skills/` → `~/.agents/skills` per `skills/install-matrix.json`; heddle's committed repo-local `.agents/skills/`. `_claude/` contains full planning/execution workflow mirrors used by Claude sessions — a parity surface, secondary to Pi. **Hermes** carries independent doctrine copies (`_hermes/default/skills/software-development/…`) pinned by `test_install_shared_skills.sh`; live Hermes config is deployed by `scripts/hermes_config_sync.py`, **not** `install.sh`.

**Authority hierarchy is in scope (round-2 F1).** The doctrine change is ineffective if higher-priority instructions retain the old framing. `APPEND_SYSTEM.md:16` ("stop before meaningful scope expansion") and `:21` ("keep changes scoped"), and root `AGENTS.md:82,90,112` ("do not broaden/expand scope") are rewritten in Phase 3 to distinguish two different things:
- **Retained (human-authorization boundary):** stop and get owner approval before *product-changing* expansion — new/changed product behavior, public contracts, persistence formats, ownership, release behavior.
- **Removed (attention restriction):** any implication that investigating, testing, or reporting beyond the plan is a violation. These lines are rewritten to reference the canonical scope definition below.

## Design principles

1. **Bound effort and mutation — never attention and reporting.** Effort budgets stay; "don't look/test/mention" goes.
2. **Permission form, not ban form.** "Do not X" meaning "X is not required" becomes "you are not required to X." True bans stay bans (don't weaken tests to pass them; don't mutate production; don't publish without the gate; don't touch secrets/private persistence outside supported surfaces).
3. **Questions over checklists.** Plans answer questions in prose; validators check presence, never content. **"Not applicable because \<evidence\>" is a legitimate answer**; the supervisor challenges *unsupported* N/A only.
4. **Rigor lives in tests.** Process gates lighten *only after* replacement tests exist (Phase 5 sequencing).
5. **Disclosure over scoping.** Green claims carry a "Not examined:" list. Expansions are explained, never silent and never forbidden.
6. **Fewer agents over time (honest scope — round-2 F11).** This plan deletes the unused Claude reviewer agents (fidelity pair, multi-reviewer) and adds one supervisor. The Codex+Claude dual-review legs (`autoreview`, `run-plan` second-reviewer policy) and the `review:prd` multi-reviewer workflow **remain unchanged in this plan**; consolidating them is an explicit owner decision *after* the supervisor proves out.

## The scope definition (canonical text, appears once in `skills/planning-workflow/SKILL.md`)

> **Scope creep is changing what the product does beyond the promised outcome.** Building unrequested features, redesigning working systems, polishing things nobody asked about — that needs its own plan and, when product-changing, owner approval.
>
> **Understanding and protecting existing behavior around your change is never scope creep — it is the cost of the change.** When you change a contract, its consumers are part of your change whether or not the plan names them. When you fix one instance of a pattern, its siblings are part of the question you were asked. Reading, tracing, and reporting **within authorized surfaces — code, tests, documentation, and supported diagnostics; never secrets, production data, or private persistence** — is always free.
>
> The test, when unsure: is this work making something *new* happen, or keeping something *existing* working while I make my change? The first needs an expansion-log entry — and owner approval if it changes product behavior, public contracts, persistence, ownership, or release behavior. The second is yours.

The disposition rule (replaces the classification taxonomy) — now carrying the newly-reachable-domain protection (round-2 F2):

> **A regression this change causes is in scope wherever it appears. When this change routes new valid inputs into a shared primitive or expands its reachable domain, correctness across that newly reachable domain is part of this change even where defects predate it. A defect this change merely discovers — and does not cause or newly expose — is a finding: capture it and keep going.**

---

## Phase 1 — Remove the fidelity layer and unused reviewers

**Delete (source):** `_claude/agents/quality-reviewer-fidelity.md`, `_claude/agents/fidelity-reviewer.md`, `_claude/agents/multi-reviewer.md`.

**Deployed strays in `~/.claude/agents/`** (`developer-fidelity.md`, `developer.md`, copies of deleted agents): **manual one-time cleanup, no install.sh automation.** Provenance check via ai-configs git history (`git log --all --diff-filter=A -- '*developer-fidelity*' '*developer.md'`); provably ex-managed files are backed up to `~/.agents/skill-backups/` then removed; anything else left in place and reported. Project-level `.claude/agents/` copies shed via the existing managed cleanup on next `install.sh --all`.

**Update stale docs** — retired references are exactly `/prd:1:create-prd`, `/prd:2:gen-tasks`, `/spec:1:create-spec`, `/spec:2:gen-tasks`, `/3:process-tasks` (**`/prd:clarify-round` is live and stays**): root `CLAUDE.md`, `AGENTS.md`, `GEMINI.md`, `_claude/commands/README.md`, `_codex/prompts/README.md` — remove Fidelity-Preserving Workflow sections, fidelity agent listings, and those exact references.

**Rosters after Phase 1:** Claude — `quality-reviewer` (rewritten in Phase 3), `debugger`, locators/analyzers, `technical-writer`, `simplify-planner`. Pi — unchanged (`planner`, `reviewer`, `scout` + disabled `Explore` override); the supervisor is **not** a `_pi/agents/` persona (see Phase 2 design) so `scripts/tests/test_pi_agent_roster.py` is untouched.

## Phase 2 — The supervisor (built and operational BEFORE doctrine loosening — round-2 F15)

The supervisor is the counterweight that makes the loosened model safe, so it is implemented, tested, and deployable **before** any doctrine text changes activate.

**Mechanism (round-2 F7 resolved):** the supervisor is a **top-level Pi process with an explicit system prompt and tool allowlist**, not a pi-subagents persona — no `_pi/agents/` entry, no roster-test change, and the adjacent-Herdr-pane topology is preserved.

**New files:**
- `skills/supervise/SKILL.md` — workflow doc: launch, checkpoint protocol, shutdown.
- `skills/supervise/supervisor-prompt.md` — the system prompt (charter below).
- `skills/install-matrix.json` — add `supervise` entry so the skill deploys to `~/.agents/skills`.
- Docs: root `AGENTS.md` and `_pi/README.md` gain a supervisor-workflow section (they document the Pi surface; round-2 F10).

**Deployment before use (round-3 F5):** Phase 2 runs `install.sh --skills` (or `--all`) immediately after adding the `supervise` install-matrix entry, so `~/.agents/skills/supervise/` exists before the dry run; the dry run exercises the deployed path.

**Launch (exact — round-3 F1):**
```
herdr pane split <worker-pane> --direction right --no-focus
herdr agent start supervisor-<worker-name> --kind pi --pane <new-pane> -- \
  --provider openai-codex --model gpt-5.6-sol --thinking high \
  --system-prompt "$(cat ~/.agents/skills/supervise/supervisor-prompt.md)" \
  --tools read,bash
herdr agent prompt supervisor-<worker-name> \
  "Worker agent: <worker-name>. Plan: <plan-path>. Begin the supervisory loop." \
  --wait --timeout 60000
```
Pi's `--system-prompt` takes text, so the file is loaded via shell substitution; the second command supplies worker identity and plan path and starts the loop. The agent name `supervisor-<worker-name>` keeps multiple concurrent workers unambiguous (round-3 F2). **Tool posture, honestly stated (round-3 F3):** `--tools read,bash` removes Pi's structured edit/write tools, but bash can still mutate; repository non-mutation is **prompt-enforced, not technically enforced**, and the Phase 2 dry run includes a probe verifying the supervisor declines a mutation request.

**Authoritative caller (round-2 F8):** `run-plan` (and `dev:run`) gain a required startup step: record the supervising agent's Herdr name in the plan's session metadata, starting one via the commands above if none is attached. Absence of a supervisor is not silent: the worker records `SUPERVISOR: none — <reason>` in the expansion log, which the pre-PR review surfaces to the human.

**Checkpoint protocol (round-2 F8; round-3 F2; round-4 F1/F2 — reactive supervisor, correlated receipts):**
- **Topology: the supervisor is purely reactive — it runs no standing wait loop** (a permanent `agent wait` on the worker would deadlock against the worker's synchronous checkpoint waits). It rests idle between wakes. Wakes: (a) the worker's checkpoint requests; (b) fire-and-forget phase-boundary pings from the worker's run-plan steps (`herdr agent prompt supervisor-<worker> "PHASE COMPLETE: <n> — plan <path>"`, **no `--wait`**), on which the supervisor reads plan/diff/expansion log and may issue an advisory nudge back.
- **Blocking checkpoints (2), correlated handshake:** the worker generates a request id (any unique string) and runs `herdr agent prompt supervisor-<worker> "CHECKPOINT REQUEST[<id>]: <plan-ready|pre-pr> — plan <path>" --wait --timeout 600000`, then reads the supervisor transcript and accepts **only** a receipt bearing the same id: `CHECKPOINT[<id>]: PROCEED` or `CHECKPOINT[<id>]: REVISE — <items>`. A receipt with any other id (stale prior approval) is ignored. **If the wait returns without a matching receipt** (e.g. it matched the end of an in-flight phase-boundary turn — Herdr's prompt wait is state-based, not turn-correlated), the worker loops: `herdr agent wait supervisor-<worker> --until idle --until done` → reread transcript → check for `CHECKPOINT[<id>]` — until the matching receipt appears or a **10-minute wall-clock deadline** from the original request expires (round-5 F2). REVISE → address items (or record reasoned disagreement in the expansion log) → new request with a **new id**; repeat until PROCEED or human intervention. Deadline expiry with no matching receipt → proceed, recording `SUPERVISOR: timeout at <checkpoint>[<id>]` in the expansion log.
- **Advisory nudges:** non-blocking; acknowledged in the worker's next expansion-log entry.
- **Shutdown (honest bounds — round-5 F1):** orderly — the caller that created the pane closes it as the worker's final wrap-up step. If a wake finds the worker agent gone (`herdr agent get <worker>` fails), the supervisor exits its session. **A crashed worker generates no further wakes, so an idle supervisor can persist until the operator closes the pane — crashed-worker cleanup is an operator responsibility**, and the supervisor's idle state costs nothing meanwhile.

**Charter (in `supervisor-prompt.md`):** worker owns technical judgment; supervisor owns trajectory and budget. Watches for: outcome drift; unreasoned expansion; stalls; unsupported N/A / boilerplate Socratic answers; verification theater. Powers: nudge/refocus; require expansion-log entries; **recommend parking optional technical cleanup** (park = capture as an issue) — but the worker's technical judgment is authoritative for work the disposition rule makes *necessary* (regressions this change causes; newly-reachable-domain correctness): the supervisor may question that classification, never override it (round-3 F4); **escalate — never approve — product-changing expansions**, which need the human under the authority hierarchy (round-2 F9; `APPEND_SYSTEM.md:16` retained). Not allowed: write or dictate code; add requirements silently; veto investigation or testing; impose file/area boundaries. Charter line: *"Exploration is never a violation. Only unexplained product change and lost aim are."* Written in goal/permission form.

**Verification:** a scripted dry run — worker Pi session on a toy repo, supervisor attached, both blocking checkpoints exercised (one PROCEED, one REVISE), one advisory nudge acknowledged, one parked expansion — recorded in `thoughts/validation/`.

## Phase 3 — Rewrite the scope doctrine (atomic activation with Phase 4)

**Files (shared source):** `skills/planning-workflow/SKILL.md`, `skills/run-plan/SKILL.md`, `skills/autoreview/SKILL.md` (+ `pre-pr-implementation-review` alias).
**Files (authority hierarchy):** `APPEND_SYSTEM.md`, root `AGENTS.md` (per the Harness-scope section above).
**Files (Pi):** `_pi/prompts/run-plan.md`, `dev:plan.md`, `dev:run.md`, `_pi/agents/planner.md` (soften "Do not broaden scope, invent requirements" — inventing requirements stays banned; investigation breadth is free), `_pi/agents/reviewer.md` (light touch).
**Files (Hermes):** `_hermes/default/skills/software-development/run-plan/SKILL.md` + siblings found by `rg "OUT_OF_SCOPE_FOLLOW_UP|PASS_SCOPED|promised slice" _hermes/`.
**Files (mirrors):** `_claude/commands/dev:plan.md`, `dev:run.md`, `run-plan.md`, `_claude/agents/quality-reviewer.md`, `_codex/prompts/` equivalents.
**Files (tests pinning doctrine text):** `test_install_shared_skills.sh:1126-1171,1649-1702,1704-1725` — same commit series.

**3a. planning-workflow:** insert the canonical scope definition + disposition rule; delete the scope-tightening cluster; keep one statement of "plan complete promised slices, not skeletons."

**3b. run-plan:** delete the three-question disposition test, `OUT_OF_SCOPE_FOLLOW_UP` machinery, "do not fix adjacent issues," "do not expand to prove harmless," "do not add tests solely to prove out-of-scope," and the enumerated in-scope refinements — subsumed by the disposition rule *including its newly-reachable-domain clause*. **Keep:** test-integrity rules; round caps and diff-split thresholds as effort budgets; rebase mechanics; the second-reviewer policy (unchanged per design principle 6).

**3c. Ban→permission pass** across run-plan/autoreview.

**3d. Verdict vocabulary — scoped grammar (round-2 F5/F6; round-3 F6/F7).**
- **Exact mapping table (round-4 F3 — decided here, `rg` sweep verifies only).**
  - **Read-as-green forever, never emitted again:** `PASS_SCOPED`, `CLEAN_FOR_PR`, `CLEAN`, `PASS_WITH_DOCUMENTED_OUT_OF_SCOPE_FOLLOW_UPS` (active in `run-plan/SKILL.md:201`, `review_orchestration.py:39`, codex-review `runtime.ts:24,83`), plus the four green forms in `migrate-md-plan-to-html.mjs:153`.
  - **Emitted going forward (green):** `PASS` only.
  - **Unchanged, both emit and read:** `FINDINGS_TO_RESOLVE`, `BLOCKED_BY_QUESTION`, `BLOCKED_BY_PRODUCT_QUESTION`, `REVIEW_INCOMPLETE_RERUN_NEEDED`, `PLAN_NEEDS_REVISION`.
  - **Read-normalized, never emitted again:** `FIX_IN_SCOPE_FINDINGS` → `FINDINGS_TO_RESOLVE` semantics; `BLOCKED_BY_SCOPE_QUESTION` → `BLOCKED_BY_QUESTION` semantics (under the new doctrine a scope question is just a question).
  - **`PLAN_EXECUTION_READY` — exclusively an external orchestration handoff token** (reviewed-html-plan skills, codex-review runtime), emitted and parsed there exactly as today, no `Not examined:` requirement. The heddle validator does **not** accept it as phase-advancing — unchanged from current behavior; plans whose latest record carries it remain outside the valid baseline (see 5c corpus rule).
- **Disclosure contract:** attribute `data-not-examined` on the review record (value: free text, non-empty; the literal `none` means "nothing — full surface exercised"); fallback: a `Not examined:` line in summary text, parsed leniently. **Deterministic rule:** historical green tokens without disclosure are accepted and normalized to green-with-`legacy: no disclosure recorded` *metadata* (never rewritten into a literal token); a **newly written** literal `PASS` without valid disclosure is rejected by writer and validator.
- **Rollout staging (round-3 F6 — hard ordering):** a small heddle **reader-compatibility commit** (validators/writers/plugin accept `PASS` alongside legacy tokens: `validate-html-plan.mjs:327-350`, `html-plan-writer.mjs:139-153`, **`plugins/heddle/scripts/lib/html-plan-workflow.js:8,114-119`** — previously missing from the consumer list) lands **before** any ai-configs/Hermes producer deploys the new grammar. Then producers switch to emitting `PASS`. Legacy reads are permanent.
- **Migration policy:** single-pass producer update after the reader-compat stage; no dual-emit window.
- **Assigned consumers (updated in this phase, one commit series):** heddle `scripts/plans/validate-html-plan.mjs:327-350`, `html-plan-writer.mjs:70-108,139-153` (writer default `PASS_SCOPED` → `PASS`), `migrate-md-plan-to-html.mjs:150-170`; ai-configs `scripts/review_orchestration.py`, `scripts/audit-codex-review-sessions.py`, `skills/codex-review-partner/scripts/run-review.sh:256-260`, `skills/herdr-reviewers/SKILL.md:86,100,156,240`, `skills/reviewed-html-plan/SKILL.md`, `skills/codex-full-build/SKILL.md`, `_pi/disabled-extensions/codex-review/runtime.ts:22-26,83-84`, `_pi/disabled-extensions/claude-review/runtime.ts`, `_hermes/default/skills/software-development/reviewed-html-plan/SKILL.md`, `scripts/tests/test_audit_codex_review_sessions.py:17-26`, `tests/test_review_orchestration.py:125-143,547-558`; closing `rg` sweep across ai-configs + heddle + `~/.pi` for every historical token as verification (not as the enumeration).

**3e. quality-reviewer rewrite:** charter = *"would a customer on the previous version experience a regression after this change reaches them?"*; delete IGNORE lists, RULE 0 dismissal framing, search restrictions; keep report-don't-redesign, effort bounds, evidence requirements.

## Phase 4 — Socratic plan format (lands with Phase 3)

**Files:** `skills/planning-workflow/SKILL.md`, `skills/dev-plan/SKILL.md`, `_pi/prompts/dev:plan.md` + mirrors. Heddle template/validator in Phase 5.

Eight questions answered in prose (evidence-backed N/A valid): **1. First hour** (customer on previous shipped version, first hour after update). **2. Consumers** (contracts altered; who consumes each today; how you'll know each still works). **3. Siblings** (other instances of the fixed pattern). **4. Moving ground** (merged-since-scoped; in-flight work on same contracts; re-answered per rebase). **5. Falsification** (what would make this wrong; which test catches it). **6. Proof** (test proving customer-visible outcome from customer behavior, not implementation pathways). **7. Untested** (what this environment can't verify; residual risk → feeds "Not examined:"). **8. Expansion log** (living; where you went beyond the ask and why it protects the outcome).

## Phase 5 — Heddle repo changes (direct on `develop`)

**Step 0 — repository-state preflight (round-2 F14, round-3 F11 — strict order):** the heddle checkout is currently `develop [ahead 1, behind 6]` with modified `VENT.md`. In order: (1) commit the `VENT.md` modification as its own standalone commit so the worktree is clean (rebase refuses a dirty tracked file); (2) local commit `b3a8f0c1` (Hub deploy dependency bootstrap): **owner disposition recorded 2026-07-23 — retain and push** (confirmed no equivalent on origin via `git cherry`); (3) `git pull --rebase` onto `origin/develop`; (4) push the rebased commits; (5) record the exact base SHA in the first Phase 5 commit message.

**5a. `.agents/skills/` reconciliation — chosen model (round-2 F13, round-3 F10).** Skills split by canonical source: `planning-workflow`, `product-principles`, `dev-plan` **have ai-configs canonical sources** → restructured as canonical core (verbatim, in a marked region) + delimited **"Heddle-local additions"** section, with retained local clauses enumerated in the reconciliation commit. `contract-boundaries` and `tdd-test-writer` **are wholly heddle-local** (no ai-configs source exists) → edited in place only (contract-boundaries also loses the "purely mechanical refactors" exclusion clause). **Drift check — honest claim (round-4 F4): a local-installed-snapshot comparison.** A heddle dev-machine script (`scripts/check-skill-canonical-drift.mjs`, run from the repo's standard local gate list, not CI) hashes each canonical region against the deployed copy in `~/.agents/skills/<skill>/SKILL.md` and reports the deployed snapshot's provenance from the per-skill marker `~/.agents/skills/<skill>/.ai-configs-managed.json` (source path + commit — the repo-managed provenance mechanism; `.skill-lock.json` covers externally installed skills only; round-5 F3). This detects divergence between heddle's embedded canon and *the last-installed shared skill on that machine* — it does not prove freshness against the current ai-configs source (a stale install can mask upstream drift, and machines without this ai-configs install lack the reference). That bound is accepted: the check is advisory; `install.sh` refreshes the deployed snapshot so the next run *reveals* any disagreement with heddle's embedded region (reconciling it remains a manual edit). The warning names both paths and the marker's commit so staleness is visible.

**5b. `AGENTS.md` tone pass:** ban→permission; delete scope-echo repetitions; reframe reviews around the customer-regression question; keep gate ladders as effort guidance; the secrets/private-persistence protections (`AGENTS.md:20,33`) are explicitly retained and are the source of the canonical definition's authorized-surfaces carve-out.

**5c. Plan schema v2 — locked design (round-2 F4).**
- **Discriminator:** `data-plan-schema="2"` on `article[data-plan]` (round-3 F12). Absent attribute = schema 1. Generator `scripts/plans/new-html-plan.mjs` and a new template `docs/planning/templates/html-plan-v2.html` (v1 template retained untouched for historical reference) emit schema 2.
- **Section map.** Retained verbatim with existing semantic checks and writer behavior (15): `summary`, `whats-new`, `linear-tracking`, `decision-attention`, `locked-decisions`, `ui-impact-triage`, `phases` (incl. `end-state|tests-first|expected-files|work|verify` blocks), `progress`, `test-coverage-matrix`, `security-privacy`, `comments`, `decisions-deviations`, `verification`, `resume-instructions`, `review-record`. Replaced (11): `why-this-plan-exists`, `authority-inputs`, `non-goals`, `functional-impact`, `product-intent`, `current-reality`, `target-contract`, `acceptance-criteria`, `bdd-scenarios`, `dependency-map`, `delivery-order` → new sections `socratic-first-hour`, `socratic-consumers`, `socratic-siblings`, `socratic-moving-ground`, `socratic-falsification`, `socratic-proof`, `socratic-untested`, `expansion-log` — presence + non-emptiness validation only.
- **Compatibility mechanism (single choice): validator branches on the discriminator.** Schema-1 plans validate against the current 26-section contract; no migration of existing files. Writers (`html-plan-writer.mjs`) mutate lifecycle sections (`comments`, `progress`, `review-record`) identically in both schemas; plan *creation* (generator + template + `migrate-md-plan-to-html.mjs`) emits schema 2 only.
- **Grandfather preservation (round-3 F8):** the validator currently activates newer section requirements from `data-updated-at` (`validate-html-plan.mjs:136-177`), and lifecycle writes bump that date (`html-plan-writer.mjs:111-115`) — so appending a comment would break a grandfathered schema-1 plan. Fix: on its first lifecycle write to a schema-1 plan lacking it, the writer stamps `data-contract-baseline` with the plan's pre-write `data-updated-at`; the validator uses `data-contract-baseline` (when present) instead of `data-updated-at` for contract-date activation on schema-1 plans. Test uses a pre-`whats-new` schema-1 fixture (e.g. modeled on `account-attach-key-repair.html`), not only a current-contract fixture.
- **Corpus test = no-regression baseline (round-3 F9):** the current validator already rejects 12 of 45 tracked HTML files (mockups without `article[data-plan]`, plans with `PLAN_EXECUTION_READY` verdicts, etc.). The compatibility gate therefore records the set of currently-valid schema-1 `article[data-plan]` files as a committed baseline and asserts **no file leaves that set** — it does not demand a green state that never existed.
- **Tests (same commit series):** baseline corpus no-regression; grandfathered-fixture lifecycle write; schema-2 create+validate; review append, comment append, readiness downgrade, readiness restore on **both** schemas; verdict grammar per 3d.

**5d. Verdict consumers** (heddle files from 3d's list) — same commit series as 3d.

**5e. `.cursor/rules/repository-pre-pr-contract.mdc`:** now that the newly-reachable-domain clause lives in the canonical definition (round-2 F2), simplify this rule to reference it.

## Phase 6 — Deploy, align, measure

- ai-configs: `install.sh --all` (skills, Pi, Codex, Claude surfaces).
- **Hermes live deploy (round-2 F12) — exact steps, not `install.sh`:** source-first changes in `_hermes/default`, then `python3 scripts/hermes_config_sync.py install --dry-run` → `install --apply` → `export` → `verify`.
- Parity: green `test_install_shared_skills.sh` run (assertions updated in Phase 3, so green is meaningful).
- **Measure:** regressions reaching customers per release; expansion-log entries endorsed vs. parked vs. escalated; review rounds per PR; time-to-merge (expected to rise — accepted).

## Out-of-plan follow-up (named stage — round-2 F16)

**Gate-lightening** (reducing full-gate re-certification language in autoreview/run-plan) is **not part of this plan's completion.** Trigger: heddle NOD-1420's signed-artifact acceptance suite (fresh install + sign-in, N-1 upgrade with populated DB, idle steady-state readiness, account/hub switch, relaunch) is operational in the release path, evidenced by the release-check command NOD-1420 defines. Until that evidence exists, current gate language stays everywhere. (What exists today: packaging/launch checks in `scripts/release/__tests__/signed-release-contract.node.mjs:216-229` and the duplicate-migration gate from NOD-1410.) **Reviewer-leg consolidation** (design principle 6) is a second named follow-up, owner-decided after the supervisor proves out.

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| Higher-priority instructions undercut the new doctrine | APPEND_SYSTEM.md + root AGENTS.md rewritten in Phase 3 with the retained human-authorization boundary made explicit |
| Verdict change breaks parsers or control states | Green-token-only grammar; control/handoff states preserved; consumers assigned by name; legacy grandfathering; closing `rg` as verification |
| Heddle plan tooling loses machine contracts | Locked schema-v2 map + discriminator + both-schema writer tests; schema-1 valid forever |
| Supervisor never runs / runs without its prompt | System-prompt + tool-allowlist launch; run-plan/dev:run required startup step; `SUPERVISOR: none` disclosure path |
| Supervisor becomes a fence or exceeds authority | Not-allowed list; endorse/park vs. escalate split; product change always escalates to the human |
| Doctrine active without counterweight | Supervisor is Phase 2, before doctrine (Phase 3); heddle migration (Phase 5) after both |
| Hermes drift | Source + parity tests in Phase 3; `hermes_config_sync.py` sequence in Phase 6 |
| Heddle-local skill drift recurs | Delimited-overlay model + mechanical region-hash drift check |
| Direct-on-develop mixes pre-existing work | Phase 5 step-0 preflight (VENT.md, `b3a8f0c1`, rebase, recorded base SHA) |
| "Reading is free" read as license on secrets | Authorized-surfaces carve-out in the canonical text |
| Boilerplate Socratic answers | Named-artifact questions; evidence-backed N/A; supervisor plan-ready checkpoint |

## Execution gating and order

**Gate:** re-review by Pi (`gpt-5.6-sol`, high) until consensus `EXECUTION_READY`.

**Order (supervisor-first, atomic activation — round-2 F15; reader-compat first — round-3 F6):**
1. Phase 1 (removals — safe standalone)
2. Phase 2 (supervisor built, `install.sh --skills` deploy, dry-run verified under *current* doctrine)
3. Heddle **reader-compatibility commit** (accept `PASS` alongside legacy tokens in validator/writer/plugin — includes the Phase 5 step-0 preflight, since it commits to develop)
4. Phases 3+4 (doctrine + Socratic format + verdict grammar) as one commit series, deployed immediately (Phase 6 ai-configs + Hermes steps run at this point — activation is atomic with the supervisor operational and heddle readers compatible)
5. Phase 5 remainder (heddle, direct on develop)
6. Phase 6 parity verification + measurement baseline
7. Follow-ups (gate-lightening; reviewer consolidation) remain out-of-plan, trigger-gated.

## Review-process note (owner directive, 2026-07-23)

This plan's own review loop must not reenact the pathology it fixes. The convergence standard for `EXECUTION_READY`: **no false factual claims, no undecided design choices, no missing owner approvals.** Remaining micro-details (exact test names, helper-script internals, prompt wording) are delegated to executor judgment under the plan's stated principles and the supervisor checkpoint — demanding their pre-specification is the over-specification failure mode this plan removes. Review effort budget: initially four rounds; extended round-by-round at the owner's direction (round 5+ authorized 2026-07-23).
