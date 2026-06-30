# Hermes development workflow evolution — 2026-06-12

Session-specific reference for future plans that evolve Aaron's Hermes development workflow.

## Trigger

Aaron asked to evolve Hermes development workflow with four changes:

1. Replace Markdown planning processes/iterations with HTML planning through `plan-review` / HTML Plan Reviewer.
2. Replace tmux-first coding-agent management with Agent of Empires (`aoe`) sessions, ideally running Pi under AoE; tmux remains available for inspection.
3. Use the scoped development process and add PM review cycles like the Heddle Symphony workflow.
4. When a PR is open, watch for feedback and address it as it arrives.

## Resulting plan pattern

For workflow-evolution plans, create a semantic dark-mode HTML plan under `thoughts/plans/*.html` even when the repo does not already have a `thoughts/` tree. Include stable IDs for comment targets and a plan-reviewer-friendly structure:

- current workflow snapshot,
- requested evolution summary,
- target workflow flow diagram,
- phased implementation plan,
- command/control-surface mapping tables,
- plan-stage and implementation-stage PM review loops,
- PR feedback watcher loop,
- acceptance criteria,
- BDD scenarios,
- risks and mitigations,
- open questions.

Register with:

```bash
plan-review register thoughts/plans/<slug>.html --repo auto --branch auto --commit auto --execution-ready false --json
```

Then drain pending comments once and start the queue-backed listener:

```bash
plan-review agent next <planId> --url http://mbp.braid-python.ts.net:4317 --no-wait --json
plan-review agent next <planId> --url http://mbp.braid-python.ts.net:4317 --wait --json
```

## Durable workflow decision

When Aaron asks for this evolution in future sessions, treat it as a workflow preference for new Hermes-driven development work:

- HTML plans are the default planning artifact for new work unless repo-local instructions explicitly require Markdown.
- AoE is the development-session control plane; raw tmux is diagnostic/observability fallback, not the primary registry or prompt transport.
- Pi remains a preferred coding worker where appropriate, but it should be launched/supervised under AoE.
- PM review is a first-class scoped workflow gate at both plan and implementation stages.
- PR creation is not the end state; open PRs need feedback/check/mergeability watch loops.
