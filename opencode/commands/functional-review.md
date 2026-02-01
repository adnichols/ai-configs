---
description: Generate a systemic functional review for a spec or openspec change
argument-hint: "<path to spec or openspec change> [reviewer name]"
---

# Functional Review

Answer the systemic review questions below for the provided specification or openspec change set. The output is a sibling markdown document that captures the answers with the reviewer name.

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

- If input is a file: `{input_basename}.functional-review-{reviewer_slug}.md` in the same directory.
- If input is a directory: `functional-review-{reviewer_slug}.md` inside that directory.

Always include the reviewer name in the filename and headers. Overwrite any existing file at that path.

## Output Format

Write a single markdown document using this structure:

```markdown
---
reviewer: {Reviewer Name}
source: {Input Path}
date: YYYY-MM-DD
---

# Functional Review - {Reviewer Name}

Source: {Input Path}

## 1. User impact and behavior change
How will users' behavior or experience change because of this spec? Clarify which personas are affected and what they will do differently. Call out any new steps, removed steps, or changes to expectations. If there is a risk of confusion or surprise, note how UX, docs, or messaging should address it.

Answer:
<3-6 sentences>

## 2. Intended outcome and success signals
What problem or outcome is this change trying to achieve, and how will we know it succeeded? Restate the goal in system terms, not just features. Identify observable signals or metrics that would prove the change worked. If success is ambiguous, flag it and propose a measurable proxy.

Answer:
<3-6 sentences>

## 3. Boundary impact and scope growth
Which system boundaries or abstractions does this change cross, and should those boundaries change instead? Name the modules, services, or layers touched and why. If the change crosses a boundary, consider whether a new abstraction would reduce future coupling. If scope expands 3x, identify where the design would strain first.

Answer:
<3-6 sentences>

## 4. Implicit assumptions and constraints
What implicit assumptions or constraints does this depend on that are not explicitly stated? Surface expectations about data shape, timing, ordering, availability, or usage patterns. Note any assumptions that are usually true but not guaranteed. Flag which of these should be documented or enforced.

Answer:
<3-6 sentences>

## 5. Contract and compatibility changes
How does this change the contract with consumers or dependencies, and is compatibility preserved? Identify API, schema, or behavioral contracts that others rely on. Explain whether the change is backward or forward compatible, and what versioning strategy is required. Call out any clients that might break silently.

Answer:
<3-6 sentences>

## 6. Coupling and knowledge leakage
What new coupling or knowledge leakage does this introduce? Describe where components now need to know about each other's internal decisions. If the change pushes business logic across layers, note why. Suggest an alternative if the coupling seems unnecessary.

Answer:
<3-6 sentences>

## 7. State, data model, and ownership
What state or data model changes are required, and does ownership shift? Identify new fields, entities, or state transitions. Note whether the source of truth for any data moves to another component or service. If ownership becomes ambiguous, call out how to resolve it.

Answer:
<3-6 sentences>

## 8. Legacy data and in-flight operations
How will legacy data and in-flight operations be handled during rollout? Explain what happens to existing records or active workflows. Identify any transitional states and how long they may persist. If the system must support dual behavior, specify how and where.

Answer:
<3-6 sentences>

## 9. Rollout and rollback safety
What is the rollout and rollback plan, and is rollback safe after data writes? Describe the deployment sequence and any feature flags or phased releases. Note any writes or migrations that are irreversible without extra work. If rollback is risky, propose a mitigation or alternative strategy.

Answer:
<3-6 sentences>

## 10. Failure modes and expected behavior
What new failure modes are introduced, and what is the expected behavior when they occur? Enumerate the most likely failures such as timeouts, partial writes, or stale reads. For each, define what safe behavior looks like. If default error handling is inadequate, call it out.

Answer:
<3-6 sentences>

## 11. Blast radius and containment
What is the blast radius if this component fails or misbehaves? Map which downstream components, users, or data paths are affected. Determine whether failure is contained or spreads across the system. Suggest isolation mechanisms if needed.

Answer:
<3-6 sentences>

## 12. Cascading risks and graceful degradation
Could this cause cascading failures, and how do we prevent or degrade safely? Look for loops, retries, or backpressure that amplify load. Explain how the system should degrade under stress without taking others down. Recommend circuit breakers, limits, or fallbacks where appropriate.

Answer:
<3-6 sentences>

## 13. Observability and correctness signals
How will we observe correctness in production? List the metrics, logs, and alerts that would prove the change is working. Include leading indicators that detect issues before user impact. If observability is missing, propose minimal instrumentation.

Answer:
<3-6 sentences>

## 14. Operational ownership and runbooks
What operational ownership, runbooks, or support workflows does this require? Identify who is responsible when things break and what they need to do. If incidents are likely, outline what the runbook should cover. Note any new on-call or support coordination needs.

Answer:
<3-6 sentences>

## 15. Performance, scale, and bottlenecks
How does this behave under 10x load, and where are the bottlenecks? Describe expected scaling behavior and failure points. If performance relies on optimistic assumptions, flag them. Suggest caching, batching, or async paths where useful.

Answer:
<3-6 sentences>

## 16. Future evolution and pattern reuse
What future changes does this enable or constrain, and is this a reusable pattern? Explain whether this is a one-off exception or a pattern we might want to replicate. If it is a pattern, note the abstractions that make it reusable. If it constrains future evolution, document that tradeoff and why it is worth it.

Answer:
<3-6 sentences>
```

## Response to User

After writing the review file, respond with:
- The output file path
- The reviewer name used
- Any missing information that blocked full answers

Do not modify the original specification or change files.
