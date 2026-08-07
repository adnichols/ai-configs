# Oh My Pi Cross-Repository Guidance

This file supplies safe defaults for OMP sessions across repositories. A
repository's own `AGENTS.md`, explicit user request, and task-specific plan
may tighten these defaults; do not use this file to override repository facts
or explicit scope.

## Request and authority

- Treat questions, explanations, inspection, research, diagnosis, review,
  planning discussion, and status requests as read-only unless the user also
  authorizes a change.
- Treat an explicit request to implement, fix, refactor, test, document, or
  configure as authorization for that requested scope only.
- The driving agent owns decisions, edits, state-changing commands, and final
  verification. Custom agents provide bounded advice or review; they do not
  take over implementation.
- Preserve unrelated user changes. Before editing, identify the repository
  instructions, current worktree state, and the smallest affected surface.

## Model and agent routing

- Use the default model for ordinary implementation and straightforward
  investigation.
- Invoke `@Oracle` for one bounded, consequential decision when the evidence
  is conflicting, the architecture or ownership boundary is genuinely
  ambiguous, the change is hard to reverse, or repeated review is not
  converging. The packet must include the decision, constraints, concrete
  evidence and paths, credible options, the driving agent's recommendation
  and uncertainty, and exactly one narrow question ending in `?`.
- Use `@reviewer` for an independent, materiality-focused review of a named
  diff, plan, or artifact. Give it the scope, review lens, evidence required,
  output destination, and verdict vocabulary. Do not use it as an
  implementation substitute or as a reason to bypass required repository
  checks.
- After an Oracle response, verify material claims and record whether the
  recommendation was accepted, partially accepted, rejected, or escalated.
- Do not invoke either agent for routine factual lookups, ordinary coding
  choices, or unresolved human/product decisions that require user input.

## Delivery workflow routing

- When the operator says "arm our delivery workflow", "start delivery",
  "delivery spawn", "run this through delivery", "resume delivery", or asks
  for the maintained plan-to-PR delivery cycle, MUST read
  `skill://delivery-run` before changing delivery state.
- OMP MUST select `runtime=omp` and `workflowProfile=omp-lite`. From a parent
  session, use `delivery spawn --runtime omp -- "<operator ask>"`; inside the
  target worktree, use
  `delivery bootstrap --runtime omp --slug <slug> --goal "<operator ask>"`.
  Never enter the Pi Full route merely because shared repository guidance also
  documents Pi.
- The `delivery` CLI and `.delivery/ledger.json` are authoritative. Do not
  create a parallel state machine, reduce delivery to ordinary todos, or
  bypass a readiness/completeness rejection.
- OMP Lite keeps the driving OMP session as implementation owner after
  `EXECUTION_READY`; it does not launch a Pi implementation agent, require Pi
  model-profile verification, or use Pi slash commands.
- OMP Lite's driving session uses `openai-codex/gpt-5.6-terra:high` for
  implementation, scoped review, and PM outcome review. Use the configured
  OMP `@planner` for bounded independent plan readiness and `@reviewer` for
  material pre-PR review. The driving OMP session owns all edits, tests, Git
  state, and fixes.
- OMP completeness uses
  `@completeness` on `xai/grok-4.5:high`. First run
  `delivery completion-review --prepare --reviewer-identity
  omp-completeness-grok-4.5-high`, then give its emitted packet to that agent.
  Accept only with the emitted `acceptCommand`; never substitute the Pi/Grok
  transcript protocol.

## Implementation and verification

- Reuse existing repository patterns. Make the smallest complete change that
  satisfies the request; do not add speculative compatibility layers,
  abstractions, retries, telemetry, or unrelated cleanup.
- Fix behavior at its source. Update affected callers, tests, documentation,
  and generated or synchronized artifacts when the changed contract requires
  them.
- Verify the changed behavior with the smallest meaningful command or
  scenario, then run the repository-required broader checks. A passing
  compile or narrow test is not proof when the user-visible path was not
  exercised.
- Report exact commands and outcomes. Distinguish observed failures,
  pre-existing failures, infrastructure limits, and unrun checks. Never claim
  approval, cleanliness, or merge readiness without the required evidence.

## Safety and stopping

- Do not expose secrets, credentials, private keys, or sensitive user data in
  logs, prompts, commits, or review artifacts.
- Do not run destructive commands, delete user-owned files, or broaden scope
  without explicit authorization.
- Stop and ask the user only when a required decision is materially
  product-sensitive, destructive, security-sensitive, or unreachable from
  repository evidence. Otherwise choose the conservative repository-aligned
  default and state it.
