---
name: adn-mode
description: "ADN engineering style for Codex: task-specific playbooks, scoped design, native independent review, and verified work. Use when ADN mode is requested."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# ADN mode for Codex

Use the engineering principles and playbooks for the user's task. Keep the selected driving model. The driver implements and verifies; independent agents provide bounded discovery, design alternatives, and review under the runtime contract.

For a multi-step task, keep a short task list, read the applicable principle files, and choose a playbook below. Apply principles where they change a decision. Explain consequential choices without reciting principle names in every reply. A narrow answer or small edit does not need an architecture panel.

## Routing

- Read-only questions and audits: `playbooks/investigation.md` and `how`; use `why` for historical rationale.
- Reported defects: `playbooks/bug-fix.md`. Reproduce before claiming a fix.
- New behavior: `playbooks/feature.md`.
- Behavior-preserving changes: `playbooks/refactoring.md`.
- Design uncertainty: `architect`, or `playbooks/prototype.md` for an empirical question.
- Performance work: `playbooks/perf-issue.md`; sustained metric improvement: `playbooks/hillclimb.md`.
- Live runtime diagnosis: `playbooks/runtime-forensics.md`; supplied profiles: `playbooks/trace-forensics.md`.
- Visual equivalence: `playbooks/visual-parity.md`.
- Skill changes: `playbooks/authoring-a-skill.md`; comparing skill behavior: `playbooks/eval.md`.
- PR status and requested maintenance: `playbooks/babysit.md`; authorized landing: `playbooks/shipping.md`.
- Long execution: `playbooks/autonomous-run.md`; phased work: `playbooks/multi-phase-plan.md`.
- A standing program: `playbooks/orchestrate.md`; independent queue: `playbooks/autopilot-full.md`; an ordered stack: `playbooks/autopilot-stack.md`.
- Resume: `playbooks/session-pickup.md`; pause: `playbooks/pause-safely.md`.
- Disk cleanup: `playbooks/worktree-cleanup.md`.
- PR creation, when included in the task: `playbooks/opening-a-pr.md`.

Read only the selected playbook and dependencies required by it. `run-plan` owns lifecycle when explicitly invoked. Completeness is on request. Do not turn an ordinary change into a delivery run, mandatory stack, TDD exercise, or extra PR.

## Engineering guidance

Read the matching leaf skill before applying it. Use the domain and foundational-thinking principles for data shapes, boundary-discipline for parsing and validation, and type-system-discipline for signatures. For changes to structure, use laziness-protocol, subtract-before-you-add, minimize-reader-load, and migrate-callers-then-delete-legacy-apis. Use separate-before-serializing-shared-state for concurrent ownership and make-operations-idempotent for retries.

For design choices, use experience-first and exhaust-the-design-space when alternatives would resolve a real uncertainty. Use redesign-from-first-principles and fix-root-causes when implementation evidence disproves the current shape. Outcome-oriented-execution and sequence-verifiable-units govern phased changes. Prove-it-works requires evidence from the actual affected behavior.

Use build-the-lever for repeated transformations, guard-the-context-window for bounded evidence gathering, never-block-on-the-human for authorized reversible work, and encode-lessons-in-structure for recurring mistakes. These are the installed `principle-*` skills with the names above.

Apply `unslop` to prose and `technical-writing` to substantial documentation. Preserve useful constraint comments; `no-comments` is a scoped review, not a blanket deletion gate. A broken supporting skill is a reported dependency issue, not authorization for an unrelated repository change.
