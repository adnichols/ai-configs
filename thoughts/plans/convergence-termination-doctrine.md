# Convergence and Termination Doctrine (P5)

**Status:** proposed — not yet reviewed or executed
**Source:** 2026-07-24 retro of the NOD-1422 (PR #497) and NOD-1424 (PR #499) overnight runs against the 2026-07-23 guidance-loosening expectations.

## Product-owner context

The Jul 23 loosening worked: both overnight runs looked one hop out, found real defects, and disclosed honestly. But neither run could conclude. NOD-1422 had its PR open 5.5 hours in and then spent ~16 hours in rebase/re-review/evidence laps; NOD-1424 finished implementation in ~1.5 hours and spent ~9 hours chasing a clean certification the flaky strict harness could never produce. Both shipped only by operator fiat at ~5:50am. The stack bounds review cycles but not verification attempts, treats a SHA move as staleness, lets supervisors detect pauses but not futility, lets stale queued prompts outlive operator decisions, and grew a commit-per-observation evidence culture. This plan adds the missing half of the Jul 23 design: a definition of done arguing.

Design constraint carried over from Jul 23: **bound effort and mutation — never attention and reporting.** Everything below is written as budgets, dispositions, and permissions, not new prohibition lists.

## What's new

**Runs end on evidence, not exhaustion.** After this change, a run whose full-suite gate keeps failing on moving flakes classifies the residual failures (introduced vs. inherited, functional vs. infra/cosmetic) and ships with disclosure instead of looping overnight; a rebase that doesn't change the content diff no longer invalidates accepted reviews; a supervisor that sees the same gate fail three times escalates a ship/keep-fixing decision instead of ordering another lap; and an operator ship directive instantly voids everything queued behind it. Preserved guarantees: introduced or functional failures still block, review budgets are unchanged, and disclosure requirements are strengthened, not weakened.

## Non-goals

- No re-tightening of scope or attention doctrine; the Jul 23 loosening is untouched.
- No change to plan schema v2, Socratic questions, or the PASS/"Not examined:" grammar.
- Heddle harness code fixes (strict-suite contention, visual tolerance) are follow-up issues in heddle, not part of this guidance change.

---

## Phase 1 — Verification Convergence Budget (run-plan)

**File:** `skills/run-plan/SKILL.md`

**1a.** Insert a new section immediately after `## Unified Review-Cycle Budget` (after line "Apply the disposition rule in the Scope Classification section…"):

```markdown
## Verification Convergence Budget

Full-suite verification and certification gates get a convergence budget, exactly as reviews do. Track attempts per delivery head in the coverage ledger: gate name, attempt number, failure signature, and whether the root cause is new or a repeat.

- A repeated full-gate attempt is justified only by a new distinct root cause — a failure this attempt will address that previous attempts did not. Rerunning to "get a clean one" is not a root cause.
- Three full attempts at the same gate without a new distinct root cause exhaust the budget, or 90 minutes of attributable gate time on one delivery head — whichever comes first. Record the gate's normal green-run duration in the ledger so a legitimately slow, still-progressing gate is not misread as a loop; repo-local guidance may override these thresholds. When the budget is exhausted, the loop is over: classify every residual failure and dispose of it as below. Do not launch another attempt, a renamed certification, or a "final clean" serial lap to avoid the classification.

Classify each residual failure on two axes, with evidence:

- **Introduced** (caused or newly exposed by this branch) vs. **inherited** (reproducible at the merge-base or on the target branch). Inherited requires reproduction evidence at the merge-base or on the target branch, not inference from the failure's age — and the disposition rule still governs: a failure in a domain this change newly makes reachable is introduced regardless of where the defect predates the branch.
- **Functional** (customer-visible behavior wrong) vs. **infra/cosmetic** (harness contention, environment flake, rendering deltas within an approved tolerance). Where no approved tolerance exists, the delta is not classifiable as cosmetic — it is a `QUESTION`.

**Flake disposition:** a full-run failure is infrastructure-flake evidence, not a delivery blocker, when the failing tests pass in isolation or serial rerun and the failure point moves between attempts. Certify on the serial/isolated evidence and disclose the parallel-run state in the PR body. You are never required to keep spending budget chasing a clean parallel run.

Disposition when the budget is exhausted:

- Every residual is inherited or infra/cosmetic (with the evidence above), and targeted verification of the changed surfaces is green → **open the PR as a draft** with the two-axis classification and evidence in the PR body, then mark the run state blocked-on-operator with the ship/keep-fixing question. This is the terminal state for unattended runs: the finished branch is preserved and disclosed, and converting the draft to ready is an operator decision. Open it ready-for-review instead only when the operator has explicitly authorized that for this run or repo guidance documents an exception path.
- Any residual is introduced or functional → it is in scope: fix it, or stop with a blocker naming it.
- The classification itself needs a product judgment (for example, a rendering delta with no approved tolerance) → that is a `QUESTION` for the operator, presented with the two-axis classification. Never resolve it by choosing maximal strictness on the operator's behalf.

An operator ship or stop directive ends this budget immediately wherever it stands: discard queued and in-flight gate attempts, open the PR in the state the operator named (ready by default when they said "ship"), and disclose the truthful gate state.
```

**1b.** In `## Non-Negotiable Rules`, after the bullet beginning "Do not create a PR until verification appropriate to the touched surfaces has run…", add:

```markdown
- Verification convergence is budgeted. When the Verification Convergence Budget is exhausted and every residual failure classifies as inherited or infra/cosmetic with targeted verification green, opening the draft PR with disclosure and stopping on the ship/keep-fixing question is the required next action, not a policy violation.
```

**1c.** In `## Final Verification`, append to the second paragraph (after "…report the gap as a plan defect."):

```markdown
Full-gate reruns are governed by the Verification Convergence Budget; a failure with an already-classified root cause never by itself requires another full run. An exhausted convergence budget with all residuals classified inherited or infra/cosmetic and targeted verification green satisfies this section's evidence requirement for the draft-PR disposition — record the classification as the final-verification result rather than calling the gate passing.
```

**1d.** Make the terminal state coherent end-to-end:

- In `### Completion Criteria`, amend the first criterion from "Final verification for the touched surfaces has passed after the latest code change." to:

```markdown
- Final verification for the touched surfaces has passed after the latest code change, or the Verification Convergence Budget disposition applies: targeted verification is green, every residual failure is classified inherited or infra/cosmetic with evidence, and the classification is disclosed in the PR body. In the draft-PR disposition the run state does not complete — it is blocked-on-operator with the ship/keep-fixing question until the operator answers.
```

- In `### Monitoring Loop`, add after item 1:

```markdown
A run in the convergence-budget draft-PR disposition does not loop: it reports the ship/keep-fixing question with the classification and waits on the operator. Failing required checks that reproduce the already-classified inherited/infra residuals are part of that disclosure, not new work.
```

## Phase 2 — Content-identified review evidence (run-plan + herdr-reviewers)

Canonical content identity, used by every clause below. **Insertion point:** `skills/run-plan/SKILL.md`, as the opening paragraph of `## Base Freshness and Mergeability Gate` (before its numbered steps), so every clause that references it sits downstream of the definition:

```markdown
The **content identity** of a candidate is the combined hash of: the committed diff against the merge-base with the target branch (`git diff "$(git merge-base origin/<target> HEAD)"..HEAD`), the staged diff, the unstaged diff, and the deterministic untracked-path manifest as defined by `herdr-reviewers` (sorted paths with type/mode and content hash). This is the reviewer fingerprint with the HEAD commit component replaced by the merge-base diff hash: it identifies the change content — committed or not — while ignoring commit SHAs. Two candidates with equal content identity carry the same change; a rebase that alters only SHAs leaves it unchanged.
```

**2a.** `skills/run-plan/SKILL.md`, in `## Base Freshness and Mergeability Gate`, replace step 7 ("After any rebase, autostash replay, or conflict resolution, rerun the verification invalidated by the changed diff context.") with:

```markdown
7. After any rebase, autostash replay, or conflict resolution, compare the content identity (defined above) before and after. If it is unchanged, prior verification and review evidence remains current — record the rebase and the unchanged hash. If it changed, rerun only the verification the changed hunks invalidate, and record why the remainder stays current.
```

Then replace step 8:

> "Rerun scoped quality reviews, PM review, or the Codex/Claude pre-PR gate when the rebase materially changes the PR diff, touched files, acceptance evidence, or reviewer assumptions."

with:

```markdown
8. Review evidence follows the same content identity: rerun full scoped reviews only when the rebase materially changed the content diff, touched files, acceptance evidence, or reviewer assumptions. An unchanged content identity never by itself stales accepted review evidence.
```

**2b.** Same file, `### Rebase Guidance` steps 5–6, replace with:

```markdown
5. Rerun verification affected by the rebase only when the content identity changed; rerun only what the changed hunks invalidate.
6. Rerun scoped reviews when the content diff changed materially; a rebase that leaves the content identity unchanged does not invalidate accepted review evidence.
```

Also in `## Final Verification`, amend the invalidation sentence ("Rerun only checks invalidated by an implementation or review fix, dependency/configuration/generated-artifact change, rebase or conflict resolution, …") to read "…rebase or conflict resolution **that changed the content identity**, …".

**2c.** `skills/herdr-reviewers/SKILL.md`: after the fingerprint-components block (the `HEAD commit + …` code fence and its following manifest paragraph), add:

```markdown
The launch fingerprint protects in-flight stability: it answers "did the worktree change while this review ran," and HEAD is a correct component for that question. Accepted review evidence is identified separately, by the candidate's **content identity** as defined in `run-plan`'s Base Freshness section: the same components as this fingerprint, with the HEAD commit component replaced by the hash of the committed diff against the merge-base with the target branch. Record the content identity alongside the launch fingerprint in the review receipt. A later rebase that changes commit SHAs but leaves the content identity unchanged does not stale accepted evidence; any change to committed, staged, unstaged, or untracked content does. Consumers deciding whether to reuse prior review evidence compare content identities, not launch fingerprints.
```

## Phase 3 — Supervisor: futility, operator supremacy, single-flight recovery

**3a.** `skills/supervise/supervisor-prompt.md`, in `## What you watch for`, replace the `**Stalls**` bullet with:

```markdown
- **Stalls** — exploration that has stopped producing decisions, tests, or code.
- **Futility loops** — a worker continuously *working* is not necessarily progressing. Track gate attempts per stream: gate name, attempt number, failure signature. The thresholds are the run's effective Verification Convergence Budget — read it from the worker's coverage ledger or plan, including any repo-local override; fall back to the doctrine defaults (three attempts or 90 minutes of attributable gate time, whichever first) only when no effective budget is discoverable. When the budget is spent without a new distinct root cause, another lap is never the right intervention: direct the worker to classify the residual failures (introduced vs. inherited, functional vs. infra/cosmetic) and escalate a ship/keep-fixing decision to the human with that classification attached.
```

**3b.** Same file, new section between `## Your powers and their limits` and `## Conduct`:

```markdown
## Operator directives

An operator ship or stand-down directive takes effect immediately and voids everything queued behind it: pending nudges, queued recovery prompts, and standing strictness directives for that stream. Never demand fresh gates, evidence deletions, or REVISE after the operator has shipped. A wake that finds the stream's PR merged or shipped acknowledges completion and ends supervision of that stream.

A standing directive (for example, "all tests must pass") is premised on the evidence at the time it was given. When new evidence contradicts that premise — the failures prove inherited from the target branch, or infra flake — the collision is the operator's question. Present it with the classification; do not resolve it by maximal strictness on the operator's behalf.
```

**3c.** Same file, append to `## How you run` (after the worker-gone paragraph):

```markdown
Recovery prompts are single-flight: before sending a wake or recovery prompt, read the worker's transcript for an undelivered earlier one — a queued duplicate is worse than a late wake. Use `herdr agent wait` loops for pause detection; do not build custom watcher daemons. Time spent debugging supervision machinery is time not spent supervising.
```

**3d.** `skills/supervise/SKILL.md`, append to `## Shutdown`:

```markdown
An operator ship or stand-down directive for the worker's stream is also a shutdown signal: the supervisor discards its queued prompts and pending demands for that stream, acknowledges, and treats its supervision as complete. Stale supervision must never outlive an operator decision.
```

## Phase 4 — Evidence placement (run-plan)

`skills/run-plan/SKILL.md`, new short section immediately after `## Scope Classification`:

```markdown
## Evidence Placement

Evidence lives in the coverage ledger (working notes), the plan file's progress and deviation sections, and ultimately the PR body. Do not create repository commits whose sole content is recording verification, certification, review, or deferral status; fold plan-progress updates into at most one bookkeeping commit per completed phase. Never commit a "debt" record for a failure the disposition rule makes in scope — fix it or report the blocker. A run's commit history should read as the change, not as a diary of the process that produced it.
```

## Phase 5 — Parity copies and pinned tests

The consumers are not uniform; treat them in three classes with per-file work:

**5a. Thin run-plan wrappers** — `_pi/prompts/run-plan.md`, `_codex/prompts/run-plan.md`, `_claude/commands/run-plan.md`: these delegate to the `run-plan` skill. Verify each still resolves the skill and add no text unless a wrapper independently restates a rule this plan changes (inventory each with `rg -n "verification|rebase|budget"` before deciding; expected outcome: no edits).

**5b. Independent dev:run workflows** — `_pi/prompts/dev:run.md`, `_codex/prompts/dev:run.md`, `_claude/commands/dev:run.md`: each is a standalone workflow with its own headings; do not paste the run-plan sections verbatim. Add two condensed clauses to each, semantically equivalent, at these anchors:
  - after each file's verification/testing rules: a 3–4 sentence Verification Convergence Budget summary (attempt/time thresholds with repo override, two-axis classification with the inherited-evidence and disposition-rule guards, flake disposition, draft-PR-and-stop default);
  - in each file's rebase/freshness language (where present): the content-identity reuse rule with a pointer to the canonical definition in `run-plan`.
  Record the exact anchor chosen per file in the execution notes.

**5c. Supervisor + reviewer surfaces** — `skills/run-plan/agents/*.yaml` (inventory for wording that pins the sections being edited), `skills/supervise/supervisor-prompt.md` (Phase 3 is the edit; confirm no other copy exists via `rg -rn "Futility|single-flight" skills/ _pi/ _hermes/`), and `skills/herdr-reviewers/SKILL.md` (Phase 2c).

**Ordering:** edit canonical `skills/` sources first, then run `scripts/hermes_config_sync.py install --apply` and export so `_hermes/default/skills/software-development/run-plan/SKILL.md` (an abbreviated managed copy — verify the sync tool regenerates it rather than hand-editing) picks up the change; commit source and Hermes export together, as in commit `4b100dc`.

**Pinned tests:** update assertions in `test_install_shared_skills.sh`, `test_install.sh`, and `scripts/tests/` that pin wording of the edited sections (find them with `rg -l "Unified Review-Cycle|Base Freshness|supervisor-prompt" test_install*.sh scripts/tests/`). `scripts/review_orchestration.py` / `scripts/audit-codex-review-sessions.py` parse verdict tokens only — this plan adds none — but re-run their suites to confirm. Gate: repo pytest suite, `test_install.sh`, `test_install_shared_skills.sh` all green.

Rollout ordering (same lesson as the PASS-token rollout): no new verdict tokens or handshake strings are introduced, so no reader-compat pre-commit is required. The only cross-repo consumer is heddle's skill overlays — sync them in Phase 6 before the next overnight run.

## Phase 6 — Heddle uptake and infra follow-ups

Mechanism: heddle follows its normal branch policy — create a branch in `/Users/anichols/code/heddle`, apply the overlay sync, and open a PR; do not commit to heddle's default branch directly. If this session lacks authority over that checkout at execution time, hand Phase 6 off as an explicit heddle-side task instead of assuming a writable sibling.

- Sync canonical skill text into `heddle/.agents/skills/` overlays; run `scripts/check-skill-canonical-drift.mjs` (heddle) to verify.
- Add a repo-local overlay note in heddle's run-plan/planning overlay naming its concrete gates: `npm run pre-pr:check` and `cargo test-strict` are the budgeted gates, and serial/isolated rerun is the sanctioned flake-evidence procedure. Do not pre-classify visual-baseline deltas: until an operator-approved tolerance exists (issue 2 below), an unexplained visual delta routes as a `QUESTION` under the convergence budget, exactly as the canonical text says.
- File two Linear issues (operator to approve before filing):
  1. **Strict-harness contention:** full `cargo test-strict` / `pre-pr:check` runs fail on rotating timeouts (SQLite lock, node health, tuple-auth 500) under their own concurrent load; each failing test passes in isolation. Fix resourcing/serialization so the gate can go green, or make serial mode the certified path.
  2. **Visual baseline tolerance:** one-pixel rendering deltas fail certification and consumed a 2-hour investigation plus 24 PNG refreshes on NOD-1422; add a perceptual/pixel tolerance to the visual suite.

## Progress

- [ ] Phase 1 — Verification Convergence Budget in run-plan
- [ ] Phase 2 — Content-identified review evidence
- [ ] Phase 3 — Supervisor futility/operator-supremacy/single-flight
- [ ] Phase 4 — Evidence placement
- [ ] Phase 5 — Parity copies + pinned tests green
- [ ] Phase 6 — Heddle overlay sync + Linear issues filed

## Acceptance criteria

1. A simulated exhausted-gate scenario (3 failed attempts, failures pass in isolation, inherited-with-evidence) routes to draft-PR-with-disclosure plus a blocked-on-operator ship/keep-fixing question — not a fourth attempt — under the new run-plan text, and the Completion Criteria/Monitoring Loop language describes that state without contradiction.
2. A rebase with identical content identity (canonical definition present in run-plan) is documented as invalidating neither accepted review evidence nor verification evidence, in run-plan, herdr-reviewers, and the dev:run condensed clauses.
3. The supervisor prompt contains the futility-loop watch item, the operator-directive section, and single-flight recovery; the supervise dry-run scenarios extended with: (a) worker looping the same gate → supervisor escalates with classification instead of prodding; (b) simulated operator ship directive → supervisor discards queued demands and acknowledges.
4. Evidence Placement present in run-plan and parity copies; no pinned test regressions (pytest, both install test suites).
5. Heddle overlays drift-clean against the new canonical text.

## Not examined / residual risk

- The 3-attempt/90-minute thresholds are initial values ("whichever comes first", repo-overridable per the Codex review); tune after one real run — the same watch-item discipline as the Jul 23 supervisor rollout.
- Per Codex plan review (2026-07-24, Terra medium), the unattended default is **draft PR and stop**, not ready-for-review: an unattended agent cannot judge whether target-branch policy treats an inherited/infra failure as merge-blocking. Ready-for-review requires explicit operator authorization or a documented repo exception path.
- Supervisor watcher-daemon prohibition trades responsiveness for reliability; if `herdr agent wait` loops prove too coarse, Herdr itself is the right place for a watch primitive (feature request, not guidance).
