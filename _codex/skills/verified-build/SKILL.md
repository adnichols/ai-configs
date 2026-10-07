---
name: verified-build
description: "Codex-only lab workflow for bug fixes, feature changes, and live product exploration. Use when Codex should publish clickable UI prototypes on demos.keramos.tech for approval, claim a shared lab, send confirmed build work to OMP in the same worktree, validate the exact PR head, and publish visual evidence. Do not invoke from OMP (the shared verified-build skill serves OMP) or for changes that have no user-facing behavior to exercise."
---

# Verified build

Codex owns the lab, test design, evidence, and final verdict. OMP handles planning, product code, tests, review, Git history, and PR mechanics. Codex remains accountable for the task's PRs through verification and final disposition, including PRs opened by replacement workers, unless ownership is explicitly handed off. Codex may inspect source and the PR to diagnose a result, but it does not edit the implementation.

When the user requests verified-build, request and claim a manager-assigned isolated lab without asking for separate lab-checkout permission. Lab checkout alone does not authorize deployment, fixture mutations, PR creation, or PR evidence updates; resolve those actions from the requested task and existing session authorization. Do not ask again for actions already authorized. This workflow never implies permission for merging, destructive fixture cleanup, or unrelated changes.

The lab is the only deploy target for product code. Never deploy to production, and never ask or offer to. After a merge, report that production deploy is a human operator action.

## Route the request

Choose one mode without asking when the request is clear:

- `BUG_FIX`: the user describes current behavior as wrong and supplies or implies the expected behavior. The baseline must reproduce the defect before OMP starts.
- `FEATURE_CHANGE`: the user asks for new or changed behavior and may supply prose, an image, or a clickable prototype. The baseline records the current flow and the desired reference defines the target.
- `EXPLORATION`: the user asks whether the live product matches a description. Stay read-only apart from isolated test fixtures. Report confirmed gaps, but do not start OMP unless the user also asked to fix findings.

If a request mixes exploration and authorized fixes, explore first. Route each confirmed failure through `BUG_FIX`. Do not treat an unexpected result as a defect until a clean retry rules out operator error, stale state, and an unsubmitted action.

## Use the orchestrator's current worktree

The run checkout is the orchestrator's current worktree of the target repository, including a Paseo- or Herdr-managed worktree. Resolve its path and intended base SHA before prototype staging, evidence capture, or build work. Preserve existing changes and record any difference from the intended base. Do not require a clean checkout or a path under `~/.codex/worktrees/`, and do not create another worktree or workspace for this workflow. If the current directory is the operator's primary checkout or belongs to a different repository, report `BLOCKED` and ask the operator to start the workflow in the intended worktree.

Run subsequent commands from this checkout. The OMP worker joins the orchestrator as another tab in the same Paseo workspace and shares this exact checkout. Keep uncommitted evidence in the checkout's evidence area and record its path in `run.md`.

## Preview UI changes before build

For a build mode that changes UI, produce a clickable prototype before starting OMP and publish it on Cloudflare at a unique hostname under `demos.keramos.tech`. The same hosting requirement applies to prototype-only requests. Localhost URLs, downloadable HTML, screenshots alone, and workers.dev URLs do not satisfy prototype delivery. An explicit operator skip is the only exception.

1. Perform only the read-only discovery needed to understand the current UI and design question. Reuse supplied references and the real app shell, components, density, and representative data when available. A UI prototype must look and behave like the target product, so find the repository's own prototype template or clickable demo before building anything: check repo guidance files such as `AGENTS.md`, `thoughts/prototypes/`, `prototypes/`, and the template's README. When one exists, it is the starting point; read its README and `AGENTS.md` for publish conventions. Only when the repo has none, build from the product's real DOM and CSS captured from the lab baseline.
2. Load the `prototype` skill. Use one faithful proposal when the requested direction is specific. Use its variant process when meaningful design choices remain. Build from the template when one was found: reuse its components, design tokens, icons, and menus, follow its publish conventions, and change only the screens and fixtures the proposal needs. Do not invent a standalone page or restyle. Keep prototype code throwaway and out of the implementer's diff; stage it in the run checkout's evidence area or a scratch directory outside the primary checkout.
3. Publish the clickable prototype using the demo hosting procedure below. Show full-UI screenshots of the proposed result for the known affected states, and compare them side by side with the lab baseline screenshots of the real UI at the same viewport, theme, and data state. If they do not read as the same product, the prototype is not ready to publish. Return the HTTPS demo URL. For a workflow change, also provide a short walkthrough video when practical. If video is unavailable, provide an ordered screenshot storyboard.
4. Ask the operator to approve or revise the proposal. When approved, record the template used (path and commit) or why none applied, the selected prototype version, approval, screenshots, video or prototype URL, and observable behavior in a prototype note. Copy that note into `run.md` when the build run begins. These become the target for OMP and later lab validation.
5. If the prototype cannot be produced or its demo URL cannot be deployed and verified after a bounded attempt, record `PROTOTYPE_UNAVAILABLE` with the reason. Finish the independent discovery and written acceptance criteria, then report the blocker; do not start the UI build or claim the prototype is delivered. If the operator explicitly asks to skip or proceed without it, record `PROTOTYPE_SKIPPED` and continue. Never claim approval that was not given.

Do not start OMP while an available prototype is awaiting operator review. Keep any lab claim open while waiting for feedback, including claims used to inspect the current UI. Reuse that claim for the build run after approval or a recorded skip.

## Publish clickable prototypes on Cloudflare

A request to generate or review UI prototypes with this skill includes publishing their disposable demo artifacts. This standing operator preference authorizes that demo publication only; it does not authorize product-lab deployment.

- Use the Nodaste Labs account `e6d3e575b97001f8ad1a7e98e497afa5`. Load `wrangler`; confirm account and domain ownership before deployment. Keep demo configuration separate from product deployables.
- Choose a unique run name such as `<feature>-<YYYYMMDD>-<random-8-hex>`. Publish at `https://<run-name>.demos.keramos.tech` using a Cloudflare custom domain. Use a new name for a new proposal; reuse only this run's hostname for corrections. Never replace another demo or the parent domain. Immediately after each publish, record it in `artifacts/verified-build/<run-id>/demos.json` in this worktree, in the format `worktree-cleanup` documents (run, worker, D1 database or `null`, account, URL, this worktree's absolute path, branch). Cleanup deletes only what that manifest lists.
- Reuse existing demo hosting when it can preserve other demos; otherwise prefer Workers Static Assets for an HTML/JS prototype. Stage an explicit allowlist of public prototype files, screenshots, and walkthrough media. Keep credentials, session state, internal run logs, claim-owner details, and unrelated records out of uploaded assets. Use invented or disposable representative data; keep prototype mutations in memory or an isolated demo store.
- Preserve existing Cloudflare Access protection; verify through an authorized login when required and mention that requirement with the returned URL. Open the hosted HTTPS URL in a fresh browser. Exercise its main interactions, direct state/variant links, reload behavior, responsive forms, and linked screenshots/media. Verify the custom domain serves this prototype; a successful upload or workers.dev response alone is insufficient.
- Record the unique name, account, public URL, deployment version, public asset manifest, and browser verification in the prototype note and `run.md`. Return the clickable demo URL in the final response and use its stable media URLs for approved prototype references in a PR.
- Release any product-lab claim after baseline capture once no prototype review is pending and no build run follows. Keep the published demo available for review; remove it only when the operator requests cleanup, or when `worktree-cleanup` runs. Demo hosting remains required even when no implementation or PR is authorized.

## Prepare the run

1. Read the repository guidance, lab/deploy instructions, and any project-local `verify-*` skill. Load the app-appropriate verification skill and the `paseo` skill. Load `safe-git-index` when Git mutations are needed.
2. Resolve the target lab, repository, base branch, authenticated browser or client profile, and evidence location from repo guidance. Ask only for a missing value that cannot be discovered and changes the run.
3. Use the repository's existing lab claim or lease mechanism. Record the lab, claim identity, owner, owning host/worktree, expiry if applicable, and release procedure. For CCore labs, load the ccore2 repo-local `lab-manager` skill (`.agents/skills/lab-manager`); its claims do not expire. Keep the claim while a PR using it is open or a prototype review is pending, and release it as soon as the work is done (see Release when the work is done). For expiring leases, arrange supported renewal while the claim is kept; report any retention limit rather than promising a reservation that will lapse. If the lab is already claimed, use another authorized lab or stop. Never invent a lock by convention.
4. Verify which source SHA the lab serves. The baseline must match the intended base SHA. If it does not, deploy the intended base only when the request authorizes lab deployment. Otherwise stop with the mismatch.
5. Create one run directory in the run checkout's evidence area. If none exists, use `artifacts/verified-build/<run-id>/`. Keep screenshot and video evidence untracked and out of every Git ref. A repository-defined external artifact store is acceptable, but a source branch, dedicated evidence branch, tag, or Git LFS is not a substitute for PR attachments unless the operator explicitly requests repository storage. When repository storage is explicitly required, commit and push from the run checkout — never from the operator's primary checkout.
6. Start `run.md` with the mode, user request, desired references, prototype status, template, and approval record, lab URL, claim details, baseline deployment identity, browser/client profile, fixture identifiers, visual coverage matrix, and cleanup obligations.

Do not expose credentials, session cookies, API keys, personal data, or unrelated customer data in evidence. Use disposable records or a repo-defined QA account. Only remove data created by this run.

Do not use Paseo's built-in browser (the `browser_*` tools) for browser work.

## Establish the baseline

Drive the real user path with the selected verification skill. Use stable accessible selectors or commands, not coordinates, when the tool supports them.

For build modes, list every UI surface the change could affect and every reachable state whose layout, content, interaction, or visibility could change. This visual coverage matrix must include empty or unconfigured and populated or configured states when both exist. Include other states such as loading, errors, permissions, selection, or disabled controls when the change can affect them. Create safe fixtures needed to reveal conditional UI. Every matrix row needs a baseline and candidate image at the same viewport. Each image must show the complete app UI or complete product surface with its surrounding navigation and context, not a cropped control or isolated region.

For a bug fix:

1. Reproduce the reported steps on the claimed lab at the recorded baseline identity.
2. Capture a baseline image for every visual coverage row, including the state that proves the defect.
3. Repeat from a clean navigation or fresh fixture. Verify persistence after reload and cross-client or cross-tab effects when they are part of the behavior.
4. If the clean retry passes, inspect the interaction and source as needed. Record `NOT_REPRODUCED` or `EXPECTED_BEHAVIOR` and stop without launching the implementer or opening a PR.

For a feature change:

1. Exercise the nearest current flow and capture a baseline image for every visual coverage row.
2. Record the desired outcome as observable acceptance criteria. Treat supplied images and prototypes as references, not proof that the live app already behaves that way.
3. Keep visual parity separate from behavioral parity unless the user requested both.

For exploration:

1. Convert the supplied product description into a short checklist of observable scenarios.
2. Exercise every scenario in the live lab. Record `PASS`, `FAIL`, `SKIP`, or `BLOCKED`, with steps, expected state, actual state, and a screenshot.
3. Retry failures once from a clean state. Keep the claim and review fixtures available when handing off the findings. Remove only this run's fixtures during agreed cleanup. Do not open a PR.

## Send confirmed build work to OMP

Use Paseo. OMP is responsible for managing model selection, not the orchestrator; allow OMP to choose the appropriate model and do not interfere with its selection. Load the `paseo` skill for CLI and tool syntax only. Do not follow `paseo-handoff`. That skill picks a profile by notes. If `paseo` is missing or the daemon is unreachable, record `BLOCKED` and stop.

Use the orchestrator's existing Paseo workspace ID and verify that its path resolves to the run checkout. Never create a workspace or worktree to launch the worker. If the orchestrator's workspace cannot be identified, record `BLOCKED` and resolve that placement before launching OMP. One workstream is the default. Split work only when evidence proves distinct independently mergeable root causes or an existing PR already owns a dependency. Any additional or replacement workers use this same workspace ID.

The launch profile is named `omp`. That is the Paseo bundle for this worker.

1. Call `list_profiles`, or on the CLI read the `omp` row in `daemon.agentProfiles` on the target host. Take the row whose `name` is exactly `omp`. Do not pick by notes.
2. Identify the workspace the orchestrator already occupies using `list_workspaces` or `paseo workspace ls --json`. Confirm its path resolves to the run checkout and retain its `workspaceId`.
3. Start the worker with `create_agent` in that `workspaceId` — the same workspace, so the worker appears as an adjacent tab in the same worktree. Materialize the `omp` row only:
   - `provider`: `omp/<model>`
   - `notifyOnFinish`: `true`
   - `settings.modeId`: the profile `modeId`
   - `settings.thinkingOptionId`: the profile `thinkingOptionId` when present
   - omit absent fields

When dedicated Paseo tools are unavailable, use the same launch on the CLI:

```
paseo run -d --json \
  --workspace <workspaceId> \
  --title <short-run-title> \
  --provider omp/<omp.model> \
  --mode <omp.modeId> \
  --thinking <omp.thinkingOptionId> \
  "<OMP prompt>"
```

Pass `--thinking` only when the profile has `thinkingOptionId`. Do not edit OMP's model configuration or instruct OMP to change it unless the operator explicitly authorizes that in the current request. Requesting ADN mode does not authorize a model change.

After start, inspect the worker (`paseo inspect --json <id>` or `get_agent_status`). Confirm `Provider` is `omp`, `Mode` matches the profile `modeId`, `Cwd` resolves to the orchestrator's run checkout, and the worker's workspace ID equals the orchestrator's workspace ID. If placement differs, stop the worker before implementation and correct the launch. Record those values and the observed model in `run.md`.

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
- a prohibition on lab deployment, merge, and changes outside the requested outcome, and a statement that production is never a deploy target and is never to be asked about; and
- a completion receipt containing the PR URL, exact head SHA, changed files, checks, review verdict, and remaining risks.

### Wait through Paseo

After the initial placement check, let the worker own its implementation process. Use completion and attention events for routine monitoring; avoid repeatedly reading output, checking status, or sending reminders merely to watch progress. Ten to thirty minutes without a message is normal.

This is a default for routine waiting, not a restriction on investigation or oversight. Read as much output as needed, including the full transcript line by line, when it helps verify claims, understand a blocker, investigate suspected scope drift, answer the user, recover a handoff, or resolve conflicting evidence. Intervene when the task needs it, including while the worker is active. Choose the depth of inspection from the question being resolved and return to event-based waiting when it is resolved.

Use Paseo's event path instead:

1. Keep `notifyOnFinish: true` when the tool exposes it. Paseo will notify the parent when the worker finishes, errors, or needs permission. Continue Codex-owned baseline, lab, and verification preparation while the worker runs.
2. When no independent Codex work remains, yield and let the notification resume the session. With CLI-only Paseo, prefer `paseo wait <agent-id>` over repeated short status checks. Use the execution environment's supported background or yielding mechanism so a long wait does not prevent user interaction.
3. On a completion or attention notification, inspect the status and receipt, then read supporting output as needed. A short relevant tail is a useful starting point; expand the read whenever necessary to establish what actually happened.
4. Bundle related follow-up requests where practical. State the evidence or decision needed and the desired outcome, give the worker room to choose its approach, and return to event-based waiting. Avoid directing each step or the worker's subagents unless a concrete coordination need warrants it.

A wait timeout or lack of recent output alone is not evidence of failure. Use judgment about deadlines, missing notifications, stalled operations, and other signs of trouble to decide when inspection or intervention is useful; do not require a reported error before investigating.

## Validate the PR head in the lab

After OMP reports a locally verified PR:

Because the worker shares the run checkout, the driving session must not run Git mutations (checkout, rebase, commit, reset) while the worker is active. Evidence files stay untracked in the run checkout's evidence area so they never collide with the worker's diff.


1. Confirm the PR diff and exact head SHA. Reject stale receipts or unrelated commits.
2. Confirm the lab claim is still valid.
3. Build and deploy that exact head with the repository's documented lab command from the run checkout. The run checkout is the Codex-owned lab checkout; the operator's primary checkout is never a deploy source. Because the worker shares this checkout, confirm `git rev-parse HEAD` equals the PR head and the worker is idle before building; if HEAD has moved, deploy through the repository's remote-deploy path or wait for the worker to settle rather than mutating the shared checkout. Record deployment output and independently verify the lab is serving the candidate identity.
4. Recreate the baseline scenario with equivalent fixtures, account, viewport, and starting state.
5. Capture a candidate image for every visual coverage row at the same viewport and meaningful point as its baseline image. Add states discovered from the PR diff or OMP's receipt. For a new state with no direct baseline equivalent, use the closest pre-change entry state and label the comparison.
6. Record `flow.webm` or `flow.mp4` from a clean start through the changed behavior and its persisted result. Use the selected verification skill's recorder. For web flows, a small Playwright test with video enabled is acceptable when it exercises the real lab and authenticated user path.
7. Check the requested outcome, the reproduced failure path, any directly affected guardrail, persistence after reload, and required cross-tab or cross-client updates. Do not substitute unit tests, DOM state, or a final screenshot for the user flow.

When an approved prototype exists, compare the candidate against that exact version and record any difference. A material difference requires operator approval or another OMP revision. When no prototype exists, validate against the recorded written acceptance criteria.

If validation fails, retry once from a clean state. For a confirmed candidate failure, add the exact candidate SHA, steps, expected result, actual result, and evidence paths to `run.md`, then send that packet to the same OMP agent. OMP updates the same PR. Repeat exact-head deployment and validation after each new SHA.

Stop and ask the user when the same failure survives two materially different fixes, the required fix expands product scope, the environment cannot prove which build is running, or safe validation would destroy data. If the lab claim is lost, release your own orphaned claim through the lab-manager's agent release path (see the ccore2 lab-manager skill) and claim a lab again; do not ask the operator. Record infrastructure failures as `BLOCKED`, not product failures.

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

For a prototype-only request, finish after the public demo passes browser verification and its evidence is recorded; approval may remain pending and no PR is required. For a build run, finish only when the evidence files exist, the manifest points to them, and the PR contains the complete visual evidence table with reviewer-accessible images. A build result is `VALIDATED` only when the exact current PR head passed in the claimed lab. Otherwise report `NOT_REPRODUCED`, `BLOCKED`, or `FAILED_VALIDATION` truthfully. Keep the lab claimed and the validated deployment and review fixtures available while the PR is open. Report the claim and its release status in the final handoff. Agent completion, successful validation, a blocker, or waiting for feedback does not release the claim by itself; a merge or concluded work does. Do not merge the PR.

## Release when the work is done

Release this work's claim, using the recorded procedure, as soon as the work using the lab is done. The work is done when every PR using the lab has merged, or when the work is abandoned or concluded without a merge (`NOT_REPRODUCED`, `EXPECTED_BEHAVIOR`, duplicate, won't fix, superseded). Do not wait for the operator's agreement and never ask the operator to release a lab or to resolve a stale claim from your own work. Keep the claim while a PR using it is open or a prototype review is pending. Do not infer that someone else's old claim is unused. Record the merge status and the release result.

Do not release the claim, delete the demo, or remove the worktree by hand. Run `skill://worktree-cleanup`, which releases the claim, verifies it, removes the demos in `demos.json`, archives the workspace, and deletes the remote branch. A session cleaned up by an orchestrator leaves this to the orchestrator, which runs it immediately after the merge or conclusion. Work concluded without a merge maps to its `--abandon <reason>` flag. If the claim file is lost, release the orphaned claim through the lab-manager's agent release path for your own claim (see the ccore2 lab-manager skill), not through the operator. Do not merge with `--delete-branch`: it deletes the worktree and the claim file before the lab can be released.
