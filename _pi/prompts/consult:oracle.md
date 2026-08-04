---
description: Ask the read-only GPT-5.6 Sol Oracle for bounded decision support
argument-hint: '<decision, tradeoff, plan concern, or review disagreement>'
---

# Consult Oracle

Use the repository-owned `oracle` subagent for this decision:

```text
$ARGUMENTS
```

Before launching it, inspect enough current evidence to give it a useful bounded packet. Include:

- the decision to make;
- established requirements, constraints, and inherited decisions;
- relevant files, errors, verification, or other evidence;
- credible options;
- the driving agent's current recommendation and uncertainty;
- one narrow question.

Launch `Agent` with only:

- `subagent_type: "oracle"`
- a short 3–5 word `description`
- the decision `prompt` packet above

**Do not set** caller-side `model`, `thinking`, `reasoningEffort`, `inherit_context`, or `isolation`. Checked-in Oracle frontmatter pins GPT-5.6 Sol high, inherited/forked parent context (`inherit_context: true` / `defaultContext: fork`), and the live checkout (`isolation: none`). Setting `inherit_context: false` or `isolation: "worktree"` is a workflow violation even if the transport later prefers persona defaults. Inspect the final tool arguments before launch and remove those properties if present. End the packet with exactly one narrow question marked by `?`.

The consultation is read-only and advisory; it must not edit files, implement changes, or authorize scope expansion.

After Oracle returns, verify its material factual claims against the current sources. The driving agent decides whether to accept, partially accept, reject, or escalate the recommendation and records that disposition (`accepted` / `partially-accepted` / `rejected` / `escalated`) with a one-line why before acting. If the request is read-only, do not treat the consultation as implementation authority.
