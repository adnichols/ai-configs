---
name: verfied-build
description: "Codex-only lab workflow for bug fixes, feature changes, and live product exploration. Use when Codex should claim a shared lab, establish current behavior, send confirmed build work to OMP in a Herdr worktree, validate the exact PR head in the lab, and record screenshots and video. Do not invoke from OMP or for changes that have no user-facing behavior to exercise."
---

# Verfied build

Codex owns the lab, test design, evidence, and final verdict. OMP owns planning, product code, tests, review, Git history, and the pull request. Codex may inspect source and the PR to diagnose a result, but it does not edit the implementation.

Confirm that the current user request authorizes lab use and ready-for-review PR creation before doing either. Run only the authorized portion when it does not. This workflow never implies permission for production deployment, merging, destructive fixture cleanup, or unrelated changes.

## Route the request

Choose one mode without asking when the request is clear:

- `BUG_FIX`: the user describes current behavior as wrong and supplies or implies the expected behavior. The baseline must reproduce the defect before OMP starts.
- `FEATURE_CHANGE`: the user asks for new or changed behavior and may supply prose, an image, or a clickable prototype. The baseline records the current flow and the desired reference defines the target.
- `EXPLORATION`: the user asks whether the live product matches a description. Stay read-only apart from isolated test fixtures. Report confirmed gaps, but do not start OMP unless the user also asked to fix findings.

If a request mixes exploration and authorized fixes, explore first. Route each confirmed failure through `BUG_FIX`. Do not treat an unexpected result as a defect until a clean retry rules out operator error, stale state, and an unsubmitted action.

## Prepare the run

1. Read the repository guidance, lab/deploy instructions, and any project-local `verify-*` skill. Load the app-appropriate verification skill and the `herdr` skill. Load `safe-git-index` when Git mutations are needed.
2. Resolve the target lab, repository, base branch, authenticated browser or client profile, and evidence location from repo guidance. Ask only for a missing value that cannot be discovered and changes the run.
3. Use the repository's existing lab claim or lease mechanism. Record the lab, claim identity, owner, expiry, and release procedure. If the lab is already claimed, use another authorized lab or stop. Never invent a lock by convention.
4. Verify which source SHA the lab serves. The baseline must match the intended base SHA. If it does not, deploy the intended base only when the request authorizes lab deployment. Otherwise stop with the mismatch.
5. Create one run directory in the repository's existing evidence area. If none exists, use `artifacts/verfied-build/<run-id>/` and keep it uncommitted unless repo policy says otherwise.
6. Start `run.md` with the mode, user request, desired references, lab URL, claim details, baseline deployment identity, browser/client profile, fixture identifiers, and cleanup obligations.

Do not expose credentials, session cookies, API keys, personal data, or unrelated customer data in evidence. Use disposable records or a repo-defined QA account. Only remove data created by this run.

## Establish the baseline

Drive the real user path with the selected verification skill. Use stable accessible selectors or commands, not coordinates, when the tool supports them.

For a bug fix:

1. Reproduce the reported steps on the claimed lab at the recorded baseline identity.
2. Capture `before.png` at the state that proves the defect.
3. Repeat from a clean navigation or fresh fixture. Verify persistence after reload and cross-client or cross-tab effects when they are part of the behavior.
4. If the clean retry passes, inspect the interaction and source as needed. Record `NOT_REPRODUCED` or `EXPECTED_BEHAVIOR` and stop without creating an OMP worktree or PR.

For a feature change:

1. Exercise the nearest current flow and capture `before.png` at the matching point.
2. Record the desired outcome as observable acceptance criteria. Treat supplied images and prototypes as references, not proof that the live app already behaves that way.
3. Keep visual parity separate from behavioral parity unless the user requested both.

For exploration:

1. Convert the supplied product description into a short checklist of observable scenarios.
2. Exercise every scenario in the live lab. Record `PASS`, `FAIL`, `SKIP`, or `BLOCKED`, with steps, expected state, actual state, and a screenshot.
3. Retry failures once from a clean state. Restore or remove only this run's fixtures, release the claim, and finish with the findings. Do not open a PR.

## Send confirmed build work to OMP

Use Herdr to create a dedicated worktree from the exact recorded base SHA, then start one OMP agent in that worktree. One workstream is the default. Split work only when evidence proves distinct independently mergeable root causes or an existing PR already owns a dependency.

Prompt OMP to use ADN mode and include:

- mode, requested outcome, and non-goals;
- exact baseline SHA and lab deployment identity;
- clean reproduction steps and raw evidence paths;
- desired image or prototype paths when present;
- observable acceptance criteria, including persistence and cross-client behavior;
- applicable repo guidance and project verification skill paths;
- a requirement to find the shared root cause and check every caller before editing;
- a requirement to plan, implement, add proportional regression coverage, run repo checks, complete bounded review, and create one ready-for-review PR;
- a prohibition on lab deployment, production deployment, merge, and changes outside the requested outcome; and
- a completion receipt containing the PR URL, exact head SHA, changed files, checks, review verdict, and remaining risks.

Monitor with `herdr agent get`, bounded waits, and `herdr agent read`. Send follow-ups only when new lab evidence, a concrete scope correction, or a verified review problem requires one. A timeout means inspect state; it does not mean the agent failed.

## Validate the PR head in the lab

After OMP reports a locally verified PR:

1. Confirm the PR diff and exact head SHA. Reject stale receipts or unrelated commits.
2. Confirm the lab claim is still valid.
3. Build and deploy that exact head with the repository's documented lab command. Use a separate Codex-owned lab checkout when deployment can modify the OMP worktree. Record deployment output and independently verify the lab is serving the candidate identity.
4. Recreate the baseline scenario with equivalent fixtures, account, viewport, and starting state.
5. Capture `after.png` at the same meaningful point as `before.png`.
6. Record `flow.webm` or `flow.mp4` from a clean start through the changed behavior and its persisted result. Use the selected verification skill's recorder. For web flows, a small Playwright test with video enabled is acceptable when it exercises the real lab and authenticated user path.
7. Check the requested outcome, the reproduced failure path, any directly affected guardrail, persistence after reload, and required cross-tab or cross-client updates. Do not substitute unit tests, DOM state, or a final screenshot for the user flow.

If validation fails, retry once from a clean state. For a confirmed candidate failure, add the exact candidate SHA, steps, expected result, actual result, and evidence paths to `run.md`, then send that packet to the same OMP agent. OMP updates the same PR. Repeat exact-head deployment and validation after each new SHA.

Stop and ask the user when the same failure survives two materially different fixes, the required fix expands product scope, the lab claim is lost, the environment cannot prove which build is running, or safe validation would destroy data. Record infrastructure failures as `BLOCKED`, not product failures.

## Evidence and completion

Before finishing, make `run.md` contain:

- mode and requested outcome;
- lab claim and release status;
- baseline and candidate deployment identities;
- PR URL and exact validated head SHA, for build modes;
- scenario steps, expected result, actual result, and verdict;
- paths to `before.png`, `after.png`, and `flow.webm` or `flow.mp4`, for build modes;
- exploration screenshots and per-scenario verdicts, for exploration mode;
- verification commands and results;
- fixture cleanup performed and anything intentionally left in the lab; and
- open blockers or follow-ups that were not added to the PR.

Finish only when the evidence files exist and the manifest points to them. A build result is `VALIDATED` only when the exact current PR head passed in the claimed lab. Otherwise report `NOT_REPRODUCED`, `BLOCKED`, or `FAILED_VALIDATION` truthfully. Release only the claim created by this run, using the recorded procedure. Do not merge the PR.
