# Planning Overrides AGENTS Template

Use this template for `thoughts/plans/AGENTS.md` only when the repo needs planning rules beyond the shared `planning-workflow` skill.

Do not restate the full shared planning doctrine here. This file is for repo-local overrides only.

## Objective

- State which planning behaviors differ from or add to the shared `planning-workflow` skill.
- Keep repo-local overrides additive to the shared `planning-workflow` doctrine for `execution-ready` versus `research-ready` readiness, `low-confidence` decision handling, the default `test coverage matrix`, and the execution review-to-`original test scope` feedback loop.
- Keep overrides concrete, repo-specific, and minimal.

## Required local inputs

- Product intent path if different from `thoughts/specs/product_intent.md`.
- Required docs or directories planners must read before writing a plan.
- Canonical plan output path and file format for this repo.

## Repo-specific plan additions or overrides

- Additional required headings beyond the shared plan contract.
- Allowed heading aliases for this repo, if any.
- Any mandatory plan metadata or delivery-order conventions.
- How repo-local templates and validators map the canonical semantics of the shared `planning-workflow` `What's new` contract, including its after-Product-owner-context/before-Goal order.

## Repo-specific TDD / BDD expectations

- Additional scenario types required in this repo.
- Contract, fixture, parity, or evidence-source expectations unique to this repo.
- Cases where strict TDD is commonly impractical and what compensating verification is required.
- Only document repo-local additions here; shared execution-path reassessment of the `original test scope` and shared `test coverage matrix` expectations already come from the global doctrine.

## Skill routing hints

- List the skills planners should load for common repo surfaces.
- Example: frontend work -> `vercel-react-best-practices`, browser flows -> `webapp-testing`, Rust services -> `rust-best-practices`.

## Verify command requirements

- Canonical quality-gate commands that plans should reference.
- Any repo-specific command patterns, package filters, or environment requirements planners must use.

## Legacy migration policy

- What old plan formats are acceptable to preserve.
- Which sections must be backfilled before an old plan can continue execution.

## Local ready bar additions

- Any repo-specific conditions that must be true before a plan is considered ready.
- Only add repo-specific conditions beyond the shared `execution-ready` / `research-ready` ready bar; do not relax low-confidence decision closure or convert a shared `research-ready` case into local execution.
- Keep this additive to the shared ready bar.

## Notes

- If this file grows into a restatement of the shared planning workflow, collapse it back into repo-specific deltas and push the shared rule into the central skill instead.
