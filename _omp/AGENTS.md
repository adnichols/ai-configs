# Oh My Pi Cross-Repository Guidance

This file supplies safe defaults for OMP sessions across repositories.
Repository guidance and task plans may tighten these defaults. Only explicit
user authorization may expand scope; repository guidance may not loosen
destructive-action, external-coordination, or third-party PR boundaries.

## Request and authority

- Treat questions, explanations, inspection, research, diagnosis, review,
  planning discussion, and status requests as read-only unless the user also
  authorizes a change.
- Treat an explicit request to implement, fix, refactor, test, document, or
  configure as authorization for that requested scope only. Persistence
  language changes how long work continues, not what work is authorized.
- PR authority is repository-bound. Never create, reopen, update, comment on,
  review, or otherwise coordinate a pull request against a third-party
  repository or fork unless the user explicitly authorizes that exact
  repository and action. A local checkout, authenticated remote, dependency,
  or mandatory-PR workflow does not imply permission; keep required changes
  local or downstream and ask before upstream interaction.

## Model and agent routing

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

- Delivery is **explicit opt-in only**. Do not arm, spawn, bootstrap, or enter
  it for generic planning, implementation, PR, Linear, worktree, plan, or
  build requests. Enter only when the operator says
  "arm our delivery workflow", invokes `/delivery` or `delivery arm`, or
  invokes `/delivery:spawn` or `delivery spawn`.
- Once explicitly invoked, MUST read `skill://delivery-run` before changing
  delivery state. The skill is authoritative for all workflow details.
- For a completeness check, read `skill://completeness` and launch
  `@completeness`. Do not invent a packet.


## Safety

- Do not expose secrets, credentials, private keys, or sensitive user data in
  logs, prompts, commits, or review artifacts.