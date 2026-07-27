---
description: Run comprehensive PRD review using five parallel specialized reviewers, integrate their findings into the PRD, and record review status for handoff
argument-hint: '<path to prd.md | prd slug | legacy: <spec> <tasks> | legacy: <directory containing spec.md and tasks.md>'
---

# Multi-Reviewer PRD Review Process

This command runs five independent PRD reviewers in parallel, stores each reviewer’s output separately, integrates the combined feedback into the PRD, and leaves a machine-readable review status artifact for `/dev:plan-from-prd`.

Use it only after PRD intent has been clarified and a wider review is worthwhile.

Reviewers:

1. PRD Intent
2. PRD Product Principles
3. PRD Security Privacy Reliability
4. PRD Scope Stage Fit
5. PRD Dependencies

Documents to review: $ARGUMENTS

## Phase 0: Resolve Inputs

Preferred input is one PRD file at `thoughts/plans/prd-<slug>.md`.

Resolution rules:

- Strip a leading `@` and treat the remainder as workspace-relative.
- Treat one existing `.md` argument as `prd_path`.
- Resolve a slug that starts with `prd-` through repo-local active-plan guidance; do not infer a Markdown path.
- Otherwise resolve the slug to `thoughts/plans/prd-<slug>.md`.
- Ask for an explicit path when no file or multiple candidates match.

Derive:

- `prd_slug` from the PRD filename without `.md`
- `review_dir` = `thoughts/validation/prd-reviews/<prd_slug>/`
- `ledger_path` = `<review_dir>/integration-ledger.md`
- `status_path` = `<review_dir>/review-status.json`

Reviewer files:

- `01-prd-intent.md`
- `02-prd-product-principles.md`
- `03-prd-security-privacy-reliability.md`
- `04-prd-scope-stage-fit.md`
- `05-prd-dependencies.md`

## Execution Mode

- Launch all five background reviewers with `Agent` before waiting for any result.
- Each reviewer reads the PRD and writes only to its assigned file.
- Reviewers must not edit the PRD or inspect other reviewer files.
- The primary agent is the integrator; do not launch a synthesis subagent.
- After all reviewers finish, read every output, update the ledger, integrate findings, write final status, and remove only the five reviewer files.

## Phase 1: Initialize Artifacts

Create `integration-ledger.md` with one pending row per reviewer and write this in-progress status:

```json
{
  "schemaVersion": 1,
  "prdPath": "thoughts/plans/prd-<slug>.md",
  "reviewDir": "thoughts/validation/prd-reviews/<prd-slug>",
  "status": "in_progress",
  "reviewersExpected": 5,
  "reviewersCompleted": 0,
  "integratedCount": 0,
  "pendingCount": 5,
  "reviewerFilesRemoved": false,
  "generatedAt": "<ISO-8601 timestamp>"
}
```

Ledger shape:

```markdown
# PRD Review Integration Ledger

- PRD: `thoughts/plans/prd-<slug>.md`
- Review dir: `thoughts/validation/prd-reviews/<prd-slug>/`
- Status file: `thoughts/validation/prd-reviews/<prd-slug>/review-status.json`

| Reviewer | Output File | Status | Integration Note |
| --- | --- | --- | --- |
| PRD Intent | `01-prd-intent.md` | pending | Awaiting reviewer output |
| PRD Product Principles | `02-prd-product-principles.md` | pending | Awaiting reviewer output |
| PRD Security Privacy Reliability | `03-prd-security-privacy-reliability.md` | pending | Awaiting reviewer output |
| PRD Scope Stage Fit | `04-prd-scope-stage-fit.md` | pending | Awaiting reviewer output |
| PRD Dependencies | `05-prd-dependencies.md` | pending | Awaiting reviewer output |
```

## Phase 2: Parallel Review

```javascript
const reviewers = [
  {
    name: "PRD Intent",
    file: "thoughts/validation/prd-reviews/<prd-slug>/01-prd-intent.md",
    subagent_type: "reviewer",
    description: "Review PRD intent alignment",
    lens: "Intent: stated outcome, user need, internal coherence, and alignment to the selected baseline",
  },
  {
    name: "PRD Product Principles",
    file: "thoughts/validation/prd-reviews/<prd-slug>/02-prd-product-principles.md",
    subagent_type: "reviewer",
    description: "Review PRD product principles",
    lens: "Product principles: golden path, safe defaults, recovery, actionable errors, and repository alignment",
  },
  {
    name: "PRD Security Privacy Reliability",
    file: "thoughts/validation/prd-reviews/<prd-slug>/03-prd-security-privacy-reliability.md",
    subagent_type: "reviewer",
    description: "Review PRD security and reliability",
    lens: "Security, privacy, and reliability: credible current-path risks, permissions, data handling, failure behavior, and recovery",
  },
  {
    name: "PRD Scope Stage Fit",
    file: "thoughts/validation/prd-reviews/<prd-slug>/04-prd-scope-stage-fit.md",
    subagent_type: "reviewer",
    description: "Review PRD scope fit",
    lens: "Scope and stage fit: minimum complete outcome, non-goals, sequencing, and avoidance of unsupported expansion",
  },
  {
    name: "PRD Dependencies",
    file: "thoughts/validation/prd-reviews/<prd-slug>/05-prd-dependencies.md",
    subagent_type: "reviewer",
    description: "Review PRD dependency choices",
    lens: "Dependencies: build-versus-buy rationale, operational burden, compatibility, ownership, and exit risk",
  },
];

const launched = reviewers.map((reviewer) =>
  Agent({
    subagent_type: reviewer.subagent_type,
    description: reviewer.description,
    prompt: `Review the PRD at ${prd_path}. Use this distinct review lens: ${reviewer.lens}. Follow the shared reviewer authority and materiality rules. Respect selected functional-spec paths and unchanged constraints as hard scope boundaries. For docs-only PRDs, only flag materially misleading, contradictory, or insufficient guidance for the stated operator path. Do not invent broader product changes or implementation-detail requirements unless the PRD changes those behaviors. Write findings only to ${reviewer.file}. Do not edit the PRD. End with one of: no issues / needs changes / blocked.`,
    run_in_background: true,
    // Do NOT set isolation: "worktree" — review the live worktree only.
  }),
);

const results = await Promise.all(
  launched.map((job) => get_subagent_result({ agent_id: job.agent_id ?? job.id, wait: true })),
);
```

If any reviewer fails or omits its file, mark that row `blocked`, write `status: "review_failed"`, and stop without approving the PRD or handing off to `/dev:plan-from-prd`.

## Phase 3: Integration Ledger

After all five files exist:

1. Read all five outputs.
2. Mark each row:
   - `integrated` — actionable in-scope findings were written into the PRD
   - `skipped` — output was reviewed but required no PRD change or was out of scope
   - `blocked` — output was incomplete or unusable
3. Add a truthful integration note per reviewer.

`integratedCount` counts both `integrated` and `skipped` outputs because each was accounted for. Do not count `blocked` outputs.

## Phase 4: Integrate Findings

- Read the PRD and all five reviewer files before editing.
- Consolidate duplicate findings.
- Preserve nuance when it materially changes the recommendation.
- Treat selected functional specs and unchanged constraints as hard boundaries.
- Do not integrate scope-expanding or unsupported implementation-detail requirements; mark those outputs `skipped` with the reason.
- For docs-only PRDs, integrate only materially misleading, contradictory, or insufficient operator guidance.
- Add `[REVIEW:...]` comments at the relevant PRD sections when changes are required.
- Leave a clean PRD unchanged.
- Account for every substantive finding in the ledger.

## Phase 5: Final Status and Cleanup

Write one final status:

- `approved` — no unresolved issues remain
- `needs_changes` — unresolved issues were integrated as review comments
- `review_failed` — one or more outputs were missing, blocked, or unusable

```json
{
  "schemaVersion": 1,
  "prdPath": "thoughts/plans/prd-<slug>.md",
  "reviewDir": "thoughts/validation/prd-reviews/<prd-slug>",
  "status": "approved | needs_changes | review_failed",
  "reviewersExpected": 5,
  "reviewersCompleted": 5,
  "integratedCount": 0,
  "pendingCount": 0,
  "reviewerFilesRemoved": true,
  "generatedAt": "<ISO-8601 timestamp>"
}
```

`integratedCount` must be `0` through `5`.

Remove only these explicit files; never use a glob or broad directory deletion:

- `01-prd-intent.md`
- `02-prd-product-principles.md`
- `03-prd-security-privacy-reliability.md`
- `04-prd-scope-stage-fit.md`
- `05-prd-dependencies.md`

Keep `integration-ledger.md` and `review-status.json`.

## Final Summary

```markdown
## Five-Reviewer PRD Review Complete

### Review Status
- Status: approved | needs_changes | review_failed
- PRD: `<prd_path>`
- Ledger: `<ledger_path>`
- Status file: `<status_path>`

### Reviewer Ledger
- PRD Intent — integrated | skipped | blocked
- PRD Product Principles — integrated | skipped | blocked
- PRD Security Privacy Reliability — integrated | skipped | blocked
- PRD Scope Stage Fit — integrated | skipped | blocked
- PRD Dependencies — integrated | skipped | blocked

### Integration Outcome
- `[REVIEW:...]` comments added: yes | no
- Reviewer files removed: yes | no

### Next Step
- If `approved`: ready for `/dev:plan-from-prd`
- If `needs_changes`: resolve comments, then rerun `/review:prd`
- If `review_failed`: repair the review cycle before handoff
```
