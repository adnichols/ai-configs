---
name: oracle-consultation
description: Use when a consequential technical choice remains unresolved after targeted inspection, or when the operator requests Oracle or Sol.
---

# Oracle Consultation

Use Oracle proactively once targeted evidence leaves a real consequential choice. Do not wait for the operator to request it.

Do not use Oracle for routine discovery, mechanical edits, ordinary factual lookups with one authoritative source, test execution, or a review already covered by the required reviewer or planner.

## Launch contract (Pi)

Call `Agent` with only:

- `subagent_type: "oracle"`
- a short 3–5 word `description`
- one bounded decision `prompt`

Omit caller-side `model`, `thinking`, `reasoningEffort`, `inherit_context`, and `isolation`. Checked-in Oracle frontmatter pins Sol high, inherited/forked context, and the live checkout. Setting `inherit_context: false` or `isolation: "worktree"` is a workflow violation.

## Launch contract (Devin)

Call `run_subagent` with only:

- `profile: "oracle"` (the repository-owned profile at `~/.config/devin/agents/oracle.md`; it pins its own model)
- a short `title`
- one bounded decision `task`

Devin subagents do not inherit the parent's conversation, so the packet below must be fully self-contained. Run the consultation in the foreground, or in the background and join via `read_subagent` with `block: true`.

## Decision packet

Include:

- the decision to make;
- established constraints and inherited decisions;
- current evidence and relevant files;
- credible options;
- the driving agent's current recommendation;
- remaining uncertainty; and
- exactly one narrow question ending with `?`.

Oracle is advisory. It cannot edit files, authorize scope expansion, make a product decision, replace a required review, or become implementation authority.

## After return

1. Verify material factual claims against current sources.
2. Record one disposition: `accepted`, `partially-accepted`, `rejected`, or `escalated`.
3. State why that disposition was chosen before acting.
4. Do not repeat the same consultation without materially new evidence.
5. If Oracle identifies a product or scope decision, stop for the operator.
