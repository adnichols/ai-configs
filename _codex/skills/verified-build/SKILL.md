---
name: verified-build
description: "Codex-only lab workflow for bug fixes, feature changes, and live product exploration. Use when Codex should publish clickable UI prototypes on demos.keramos.tech for approval, claim a shared lab, send confirmed build work to OMP, validate the exact PR head, and publish visual evidence. Do not invoke from OMP or for changes that have no user-facing behavior to exercise."
---

# Verified build

Codex owns the lab, test design, evidence, and final verdict. OMP owns planning, product code, tests, review, Git history, and the pull request. Codex may inspect source and the PR to diagnose a result, but it does not edit the implementation.

Confirm that the current user request authorizes lab use, PR creation, and PR evidence updates before doing them. Run only the authorized portion when it does not. This workflow never implies permission for production deployment, merging, destructive fixture cleanup, or unrelated changes.

## Route the request

Choose one mode without asking when the request is clear:

- `BUG_FIX`: the user describes current behavior as wrong and supplies or implies the expected behavior. The baseline must reproduce the defect before OMP starts.
- `FEATURE_CHANGE`: the user asks for new or changed behavior and may supply prose, an image, or a clickable prototype. The baseline records the current flow and the desired reference defines the target.
- `EXPLORATION`: the user asks whether the live product matches a description. Stay read-only apart from isolated test fixtures. Report confirmed gaps, but do not start OMP unless the user also asked to fix findings.

If a request mixes exploration and authorized fixes, explore first. Route each confirmed failure through `BUG_FIX`. Do not treat an unexpected result as a defect until a clean retry rules out operator error, stale state, and an unsubmitted action.

## Run from a dedicated worktree

Never run this workflow in the operator's primary repository checkout. Before any step that reads or writes repository files — prototype staging, evidence capture, `run.md`, research or plan notes, commits, rebases, deploys — establish the run checkout: a Codex-owned worktree of the target repository under `~/.codex/worktrees/`, created at the intended base SHA (the default branch head when the base is not yet known). Reuse an existing Codex-owned worktree only when it is clean and on the intended base; otherwise create a fresh one. Run every subsequent command with the run checkout as the working directory. When the run produces reviewable commits, create a branch in the worktree; a detached HEAD suffices for lab-only runs. Keep uncommitted evidence in the worktree until the run finishes, then record its path in `run.md`.

## Preview UI changes before build

For a build mode that changes UI, produce a clickable prototype before starting OMP and publish it on Cloudflare at a unique hostname under `demos.keramos.tech`. The same hosting requirement applies to prototype-only requests. Localhost URLs, downloadable HTML, screenshots alone, and workers.dev URLs do not satisfy prototype delivery. An explicit operator skip is the only exception.

1. Perform only the read-only discovery needed to understand the current UI and design question. Reuse supplied references and the real app shell, components, density, and representative data when available.
2. Load the `prototype` skill. Use one faithful proposal when the requested direction is specific. Use its variant process when meaningful design choices remain. Keep prototype code throwaway and separate from the OMP implementation worktree; stage it in the run checkout or a scratch directory outside the primary checkout.
3. Publish the clickable prototype using the demo hosting procedure below. Show full-UI screenshots of the proposed result for the known affected states and return the HTTPS demo URL. For a workflow change, also provide a short walkthrough video when practical. If video is unavailable, provide an ordered screenshot storyboard.
4. Ask the operator to approve or revise the proposal. When approved, record the selected prototype version, approval, screenshots, video or prototype URL, and observable behavior in a prototype note. Copy that note into `run.md` when the build run begins. These become the target for OMP and later lab validation.
5. If the prototype cannot be produced or its demo URL cannot be deployed and verified after a bounded attempt, record `PROTOTYPE_UNAVAILABLE` with the reason. Finish the independent discovery and written acceptance criteria, then report the blocker; do not start the UI build or claim the prototype is delivered. If the operator explicitly asks to skip or proceed without it, record `PROTOTYPE_SKIPPED` and continue. Never claim approval that was not given.

Do not start OMP while an available prototype is awaiting operator review. Keep any lab claim open while waiting for feedback, including claims used to inspect the current UI. Reuse that claim for the build run after approval or a recorded skip.

## Publish clickable prototypes on Cloudflare

A request to generate or review UI prototypes with this skill includes publishing their disposable demo artifacts. This standing operator preference authorizes that demo publication only; it does not authorize production or product-lab deployment.

- Use the Nodaste Labs account `e6d3e575b97001f8ad1a7e98e497afa5`. Load `wrangler`; confirm account and domain ownership before deployment. Keep demo configuration separate from product deployables.
- Choose a unique run name such as `<feature>-<YYYYMMDD>-<random-8-hex>`. Publish at `https://<run-name>.demos.keramos.tech` using a Cloudflare custom domain. Use a new name for a new proposal; reuse only this run's hostname for corrections. Never replace another demo or the parent domain.
- Reuse existing demo hosting when it can preserve other demos; otherwise prefer Workers Static Assets for an HTML/JS prototype. Stage an explicit allowlist of public prototype files, screenshots, and walkthrough media. Keep credentials, session state, internal run logs, claim-owner details, and unrelated records out of uploaded assets. Use invented or disposable representative data; keep prototype mutations in memory or an isolated demo store.
- Preserve existing Cloudflare Access protection; verify through an authorized login when required and mention that requirement with the returned URL. Open the hosted HTTPS URL in a fresh browser. Exercise its main interactions, direct state/variant links, reload behavior, responsive forms, and linked screenshots/media. Verify the custom domain serves this prototype; a successful upload or workers.dev response alone is insufficient.
- Record the unique name, account, public URL, deployment version, public asset manifest, and browser verification in the prototype note and `run.md`. Return the clickable demo URL in the final response and use its stable media URLs for approved prototype references in a PR.
- Release any product-lab claim after baseline capture. Keep the published demo available for review; remove it only when the operator requests cleanup. Demo hosting remains required even when no implementation or PR is authorized.

## Prepare the run

1. Read the repository guidance, lab/deploy instructions, and any project-local `verify-*` skill. Load the app-appropriate verification skill and the `herdr` skill. Load `safe-git-index` when Git mutations are needed.
2. Resolve the target lab, repository, base branch, authenticated browser or client profile, and evidence location from repo guidance. Ask only for a missing value that cannot be discovered and changes the run.
3. Use the repository's existing lab claim or lease mechanism. Record the lab, claim identity, owner, owning host/worktree, expiry if applicable, and release procedure. For CCore labs, load `lab-manager`; its claims do not expire. Keep the claim through review and handoff. For expiring leases, arrange supported renewal through review; report any retention limit rather than promising a reservation that will lapse. If the lab is already claimed, use another authorized lab or stop. Never invent a lock by convention.
4. Verify which source SHA the lab serves. The baseline must match the intended base SHA. If it does not, deploy the intended base only when the request authorizes lab deployment. Otherwise stop with the mismatch.
5. Create one run directory in the run checkout's evidence area. If none exists, use `artifacts/verified-build/<run-id>/`. Keep screenshot and video evidence untracked and out of every Git ref. A repository-defined external artifact store is acceptable, but a source branch, dedicated evidence branch, tag, or Git LFS is not a substitute for PR attachments unless the operator explicitly requests repository storage. When repository storage is explicitly required, commit and push from the run checkout — never from the operator's primary checkout.
6. Start `run.md` with the mode, user request, desired references, prototype status and approval record, lab URL, claim details, baseline deployment identity, browser/client profile, fixture identifiers, visual coverage matrix, and cleanup obligations.

Do not expose credentials, session cookies, API keys, personal data, or unrelated customer data in evidence. Use disposable records or a repo-defined QA account. Only remove data created by this run.

## Establish the baseline

Drive the real user path with the selected verification skill. Use stable accessible selectors or commands, not coordinates, when the tool supports them.

For build modes, list every UI surface the change could affect and every reachable state whose layout, content, interaction, or visibility could change. This visual coverage matrix must include empty or unconfigured and populated or configured states when both exist. Include other states such as loading, errors, permissions, selection, or disabled controls when the change can affect them. Create safe fixtures needed to reveal conditional UI. Every matrix row needs a baseline and candidate image at the same viewport. Each image must show the complete app UI or complete product surface with its surrounding navigation and context, not a cropped control or isolated region.

For a bug fix:

1. Reproduce the reported steps on the claimed lab at the recorded baseline identity.
2. Capture a baseline image for every visual coverage row, including the state that proves the defect.
3. Repeat from a clean navigation or fresh fixture. Verify persistence after reload and cross-client or cross-tab effects when they are part of the behavior.
4. If the clean retry passes, inspect the interaction and source as needed. Record `NOT_REPRODUCED` or `EXPECTED_BEHAVIOR` and stop without creating an OMP worktree or PR.

For a feature change:

1. Exercise the nearest current flow and capture a baseline image for every visual coverage row.
2. Record the desired outcome as observable acceptance criteria. Treat supplied images and prototypes as references, not proof that the live app already behaves that way.
3. Keep visual parity separate from behavioral parity unless the user requested both.

For exploration:

1. Convert the supplied product description into a short checklist of observable scenarios.
2. Exercise every scenario in the live lab. Record `PASS`, `FAIL`, `SKIP`, or `BLOCKED`, with steps, expected state, actual state, and a screenshot.
3. Retry failures once from a clean state. Keep the claim and review fixtures available when handing off the findings. Remove only this run's fixtures during agreed cleanup. Do not open a PR.

## Send confirmed build work to OMP

Use Herdr to create a dedicated worktree from the exact recorded base SHA, then start one OMP agent in that worktree. This OMP worktree is separate from the run checkout; never point OMP at the operator's primary checkout or the run checkout. One workstream is the default. Split work only when evidence proves distinct independently mergeable root causes or an existing PR already owns a dependency.

Launch OMP with its existing model, reasoning, and fallback configuration. Omit model, provider, reasoning, and fallback overrides. Do not edit OMP's model configuration or instruct OMP to change it unless the operator explicitly authorizes that change in the current request. Requesting ADN mode does not authorize a model change.

Before sending work, check OMP's active provider/model against the external-agent restrictions in the applicable Codex instructions, including aliases and reasoning variants. Read live runtime status with `herdr agent read` or another authoritative runtime source and record the observed model and evidence in `run.md`. Launching without overrides does not prove compliance; neither the parent Codex model nor availability in a model picker authorizes an OMP model.

Repeat this check after launch, resume, restart, or an observed model/fallback change, and before each follow-up work assignment. If the model is unknown, obtain runtime evidence before dispatch. If it is prohibited, withhold work; interrupt an active worker owned by this run and report the model and policy mismatch as `BLOCKED`. Preserve its context and configuration. Quota exhaustion, provider errors, and requests to continue autonomously do not authorize a substitute model or fallback edit. Apply only explicitly authorized exceptions for their stated use; an Oracle exception does not permit an implementation worker.

Prompt OMP to use ADN mode and include:

- mode, requested outcome, and non-goals;
- exact baseline SHA and lab deployment identity;
- clean reproduction steps and raw evidence paths;
- the approved prototype, approval record, or recorded prototype skip, plus its image, video, or URL paths when present;
- the visual coverage matrix and baseline image paths, with a requirement to report any additional affected UI surface or state found during implementation;
- observable acceptance criteria, including persistence and cross-client behavior;
- applicable repo guidance and project verification skill paths;
- a requirement to find the shared root cause and check every caller before editing;
- a requirement to plan, implement, add proportional regression coverage, run repo checks, complete bounded review, and create or update one PR for lab validation;
- a prohibition on lab deployment, production deployment, merge, and changes outside the requested outcome; and
- a completion receipt containing the PR URL, exact head SHA, changed files, checks, review verdict, and remaining risks.

Monitor with `herdr agent get`, bounded waits, and `herdr agent read`. Send follow-ups only when new lab evidence, a concrete scope correction, or a verified review problem requires one. A timeout means inspect state; it does not mean the agent failed.

## Validate the PR head in the lab

After OMP reports a locally verified PR:

1. Confirm the PR diff and exact head SHA. Reject stale receipts or unrelated commits.
2. Confirm the lab claim is still valid.
3. Build and deploy that exact head with the repository's documented lab command from the run checkout. The run checkout is the Codex-owned lab checkout; the operator's primary checkout is never a deploy source. Record deployment output and independently verify the lab is serving the candidate identity.
4. Recreate the baseline scenario with equivalent fixtures, account, viewport, and starting state.
5. Capture a candidate image for every visual coverage row at the same viewport and meaningful point as its baseline image. Add states discovered from the PR diff or OMP's receipt. For a new state with no direct baseline equivalent, use the closest pre-change entry state and label the comparison.
6. Record `flow.webm` or `flow.mp4` from a clean start through the changed behavior and its persisted result. Use the selected verification skill's recorder. For web flows, a small Playwright test with video enabled is acceptable when it exercises the real lab and authenticated user path.
7. Check the requested outcome, the reproduced failure path, any directly affected guardrail, persistence after reload, and required cross-tab or cross-client updates. Do not substitute unit tests, DOM state, or a final screenshot for the user flow.

When an approved prototype exists, compare the candidate against that exact version and record any difference. A material difference requires operator approval or another OMP revision. When no prototype exists, validate against the recorded written acceptance criteria.

If validation fails, retry once from a clean state. For a confirmed candidate failure, add the exact candidate SHA, steps, expected result, actual result, and evidence paths to `run.md`, then send that packet to the same OMP agent. OMP updates the same PR. Repeat exact-head deployment and validation after each new SHA.

Stop and ask the user when the same failure survives two materially different fixes, the required fix expands product scope, the lab claim is lost, the environment cannot prove which build is running, or safe validation would destroy data. Record infrastructure failures as `BLOCKED`, not product failures.

## Add visual evidence to the PR

After the exact PR head passes lab validation, update the PR through the repository's existing PR evidence process. Load `cmd-create-pr` before Codex performs a PR mutation. Add a visual evidence table with one row per surface and state, containing the surface, state, baseline image, candidate image, and a short description of the result. Include the approved prototype screenshots and walkthrough video when they exist, clearly labeled as design references rather than build evidence.

Use GitHub PR attachments for screenshots and videos by default. Prefer repeated `--attach` flags on `gh pr create`, `gh pr edit`, or `gh pr comment` when the installed GitHub CLI supports them; otherwise upload through an authenticated GitHub PR editor or comment. Keep the source media local and untracked. Do not commit media to the product branch, a dedicated evidence branch, a tag, or Git LFS merely to publish reviewer-visible URLs. A repository-defined non-Git artifact host is an acceptable alternative when it is already the established evidence process.

Verify that every uploaded image renders and every video opens from the PR as a reviewer. Local filesystem paths do not count as PR evidence. If neither PR attachments nor an established non-Git artifact host is available, record the run as `BLOCKED` and report the missing upload path; do not fall back to Git-backed media storage without explicit operator approval.

Do not call the PR ready for verification until every visual coverage row appears in the PR and every linked image exists. Keep the full UI visible in each image. If an applicable state cannot be produced safely, name it and the reason in the PR, record the run as `BLOCKED`, and do not silently omit it.

## Evidence and completion

Before finishing, make `run.md` contain:

- mode and requested outcome;
- hosted prototype URL, unique demo name, deployment version, verification result, and approval or explicit skip when a UI preview applies;
- lab URL, claim identity, owner, owning host/worktree, retention or renewal details, and release status;
- baseline and candidate deployment identities;
- PR URL and exact validated head SHA, for build modes;
- scenario steps, expected result, actual result, and verdict;
- the visual coverage matrix and paths to every baseline and candidate image, plus `flow.webm` or `flow.mp4`, for build modes;
- exploration screenshots and per-scenario verdicts, for exploration mode;
- verification commands and results;
- fixture cleanup performed and anything intentionally left in the lab; and
- open blockers or follow-ups that were not added to the PR.

For a prototype-only request, finish after the public demo passes browser verification and its evidence is recorded; approval may remain pending and no PR is required. For a build run, finish only when the evidence files exist, the manifest points to them, and the PR contains the complete visual evidence table with reviewer-accessible images. A build result is `VALIDATED` only when the exact current PR head passed in the claimed lab. Otherwise report `NOT_REPRODUCED`, `BLOCKED`, or `FAILED_VALIDATION` truthfully. Keep the lab claimed and the validated deployment and review fixtures available for the operator. Report the retained claim and cleanup requirements in the final handoff. Agent completion, successful validation, a blocker, or waiting for feedback does not authorize release. Do not merge the PR.

## Release during agreed cleanup

Release only this work's claim, using the recorded procedure, after all PRs using the lab have merged and the operator has explicitly agreed the work is complete. Merge alone or acceptance before merge is insufficient. For exploration or work without a PR, wait for the operator's explicit completion and cleanup agreement. An explicit operator instruction to abandon the work and release its lab also authorizes cleanup without merge. Until then, preserve the claim even if the agent stops or the work is idle. Record the agreement and merge status before release, and verify and record the release result. Never infer that an old claim is unused.
