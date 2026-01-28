---
description: Generate a lean, increment-focused functional review for a spec or openspec change
argument-hint: "<path to spec or openspec change> [reviewer name]"
---

# Lean Functional Review

Answer the lean functional review questions below for the provided specification or openspec change set.
The goal is to drive small, testable increments and prevent scope creep.

Write the output as a sibling markdown document that captures the answers with the reviewer name.

**Input:** $ARGUMENTS

## Reviewer Identity

Use the reviewer name provided in arguments if present. Otherwise use **OPENCODE**.
Keep the reviewer name exactly as provided for headers. For filenames, slugify it by lowercasing, replacing spaces and punctuation with hyphens, collapsing repeats, and trimming leading or trailing hyphens. If the slug would be empty, use `opencode`.

## Input Handling

1. If the path is a file, treat it as the specification.
2. If the path is a directory, treat it as an openspec change set:
   - Read all non-hidden `.md` files in the directory.
   - If `spec.md`, `change.md`, or `README.md` exists, read it first and treat it as the primary source.
   - Use the full set of markdown files as context for the answers.

## Output File

Create a sibling review document and write all answers there:

- If input is a file: `{input_basename}.lean-functional-review-{reviewer_slug}.md` in the same directory.
- If input is a directory: `lean-functional-review-{reviewer_slug}.md` inside that directory.

Always include the reviewer name in the filename and headers. Overwrite any existing file at that path.

## Output Format

Write a single markdown document using this structure:

```markdown
---
reviewer: {Reviewer Name}
source: {Input Path}
date: YYYY-MM-DD
---

# Lean Functional Review - {Reviewer Name}

Source: {Input Path}

## 0. Increment definition (required)
Define the smallest shippable increment.

Shipping now (1-2 sentences):
<text>

Non-goals / deferred for later (3 bullets):
- <text>
- <text>
- <text>

What would be over-engineering for this increment? (2 bullets)
- <text>
- <text>

Fastest validation path (can include manual steps, mocks, "wizard-of-oz") (2-4 bullets):
- <text>

Stop line: what must we NOT do in this increment, even if it is tempting? (1 sentence)
<text>

## 1. User impact and behavior change (required)
How will users' behavior or experience change because of this increment? Clarify personas affected and what they will do differently. Call out any UX surprise and how to message it.

Answer:
<3-5 sentences>

## 2. Intended outcome and success signal for this increment (required)
What are we trying to learn or prove with this increment, and how will we know within days (not quarters)? Prefer observable signals over theoretical completeness.

Answer:
<3-5 sentences>

## 3. Minimal approach + guardrails (required)
Describe the simplest acceptable implementation that is safe enough to ship.

Include:
- Any feature flag / kill switch shape (even if manual)
- Any "cheap guardrails" (timeouts, limits, caps, validation, idempotency keys) you will add now
- What you are explicitly not hardening yet

Answer:
<4-7 sentences>

## 4. Surface area and compatibility (required)
What contracts change (API/schema/UI behavior), and is compatibility preserved? Identify who might break and whether breakage is noisy vs silent.

Answer:
<3-6 sentences>

## 5. Top risks: accept now vs mitigate now (required)
List the top 3 risks introduced by this increment. For each, choose "accept now" or "mitigate now" and name the cheapest mitigation.

Answer:
<3-6 sentences>

## Deep Dive Triggers
Only complete the appendix sections that are actually triggered by this increment.

Triggered? Mark each:
- [ ] Irreversible writes or destructive operations
- [ ] Data migration / legacy backfill / dual-read or dual-write
- [ ] Multi-step user workflow with in-flight operations
- [ ] External dependency (3P API, queue, payment provider, webhooks)
- [ ] Fanout/retries/backpressure risk
- [ ] Hot path or high traffic (near-term)
- [ ] Multi-tenant isolation or permission boundary changes
- [ ] Security/privacy/compliance-sensitive data
- [ ] Operational ownership changes (new on-call/support burden)

If a deep dive is skipped, write: `Skipped: not triggered`.

## Appendix A. Legacy data and in-flight operations (only if triggered)
How will legacy data and in-flight operations be handled during rollout? If this increment avoids migrations, say so explicitly and explain the constraint.

Answer:
<3-6 sentences OR "Skipped: not triggered">

## Appendix B. Rollout and rollback safety (only if triggered)
What is the rollout and rollback plan, and is rollback safe after data writes? Prefer flags and progressive exposure over perfect reversibility.

Answer:
<3-6 sentences OR "Skipped: not triggered">

## Appendix C. Failure modes and containment (only if triggered)
What are the most likely failure modes, and what is the safe expected behavior? Focus on containment and user impact, not exhaustive theoretical failures.

Answer:
<3-6 sentences OR "Skipped: not triggered">

## Appendix D. Observability (minimal) and runbook notes (only if triggered)
What is the minimum instrumentation to know if this increment works? If something breaks, what is the first action and who owns it?

Answer:
<3-6 sentences OR "Skipped: not triggered">

## Appendix E. Performance and bottlenecks (only if triggered)
At expected near-term usage, what is the likely bottleneck and the earliest signal we are nearing it? Avoid speculative optimization.

Answer:
<3-6 sentences OR "Skipped: not triggered">

## Appendix F. Boundary changes and abstractions (only if triggered)
Can boundaries remain as-is for this increment? If introducing a new abstraction/layer, justify why it is necessary now and what cheaper seam was rejected.

Answer:
<3-6 sentences OR "Skipped: not triggered">
```

## Response to User

After writing the review file, respond with:
- The output file path
- The reviewer name used
- Which deep dive triggers were checked
- Any missing information that blocked full answers

Do not modify the original specification or change files.
