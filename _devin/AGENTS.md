# Devin Cross-Repository Guidance

This file supplies safe defaults for Devin CLI sessions across repositories.
Repository guidance and task plans may tighten these defaults. Only explicit
user authorization may expand scope; repository guidance may not loosen
destructive-action, external-coordination, or third-party PR boundaries.

## Request and authority

- When I request implementation and a PR, that authorizes creating the PR, pushing changes, updating the PR, and marking it ready after required validation passes in the requested repository. Do not ask separately for those steps. Merging and production deployment require separate authorization unless explicitly included.
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

## PR ownership

Treat PRs opened for a task, including delegated work, as ongoing
responsibilities of the coordinating session. Keep their links and current
disposition in the existing task notes or handoff until merged, deliberately
closed, or transferred to a named owner. When discussing a merge, make the
intended PRs explicit and mention any others still outstanding. Awaiting merge
approval is a valid status; tracking a PR does not expand merge authority.

Prefer finishing the worktree's current PR before opening another. Prefer
independently mergeable changes against the current integration branch over
stacked PRs. When work depends on an unmerged change, usually extend the
existing PR or finish that prerequisite first. Surface any deliberate exception
and how it will be completed. A short PR status line in progress updates and
the final report helps keep these responsibilities visible.

## Model and agent routing

Devin subagents are launched with the `run_subagent` tool using a profile
name. This configuration installs custom profiles `oracle`, `reviewer`,
`planner`, and `completeness` under `~/.config/devin/agents/`. Launch them by
profile name; never invent caller-side model or tool overrides when the
profile already pins them.

- Invoke the `oracle` subagent profile for one bounded, consequential decision
  when the evidence is conflicting, the architecture or ownership boundary is
  genuinely ambiguous, the change is hard to reverse, or repeated review is
  not converging. The packet must include the decision, constraints, concrete
  evidence and paths, credible options, the driving agent's recommendation
  and uncertainty, and exactly one narrow question ending in `?`.
- Use the `reviewer` subagent profile for an independent, materiality-focused
  review of a named diff, plan, or artifact. Give it the scope, review lens,
  evidence required, output destination, and verdict vocabulary. Do not use
  it as an implementation substitute or as a reason to bypass required
  repository checks.
- After an oracle response, verify material claims and record whether the
  recommendation was accepted, partially accepted, rejected, or escalated.
- Do not invoke either profile for routine factual lookups, ordinary coding
  choices, or unresolved human/product decisions that require user input.
- Skills named in shared guidance as `skill://<name>` are invoked in Devin
  through the skill tool by name; the URI form is documentation shorthand,
  not a Devin-resolvable reference.

## Delivery workflow routing

- Delivery is **explicit opt-in only**. Do not arm, spawn, bootstrap, or enter
  it for generic planning, implementation, PR, Linear, worktree, plan, or
  build requests. Enter a full cycle when the operator says
  "arm our delivery workflow", invokes `/delivery` or `delivery arm`, or
  invokes `/delivery:spawn` or `delivery spawn`. After a non-delivery
  implementation, a request to run completeness, PM review, or pre-PR is
  late-attach authorization in a supported harness; do that paperwork
  silently and do not require a spoken phrase.
- The shared delivery ledger currently supports only the `omp` and `pi`
  runtimes. Do not arm or spawn a delivery ledger from a Devin session; if
  the operator asks, explain the limitation and offer `run-plan` instead.
  If they also asked for a completeness check, run the standalone packet
  form. Do not refuse the completeness check itself.
- Once delivery is explicitly invoked in a supported harness, the operator
  must run it there. In Devin, use the `run-plan` skill for plan execution.
  Completeness is on-request: if asked, use the `completeness` skill
  (standalone packet form) and do not invent a packet. Do not ask the
  operator to recite a delivery trigger phrase.

## Safety

- Do not expose secrets, credentials, private keys, or sensitive user data in
  logs, prompts, commits, or review artifacts.
