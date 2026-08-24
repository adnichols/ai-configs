---
name: domain-modeling
description: Build and sharpen a project's domain model. Use when discussing codebase terminology, updating the configured glossary, or recording a durable architectural decision.
---

# Domain Modeling

Actively build and sharpen the project's domain model as you design. This is the *active* discipline — challenging terms, inventing edge-case scenarios, and writing the glossary and decisions down the moment they crystallise. Merely reading the configured domain docs is not this skill; use it when changing the model.

## Configured homes

Read `docs/agents/domain.md` first when it exists. It names the repository's canonical glossary, durable decision records, and update rules. Follow that convention exactly; a mature architecture manual, numbered decision section, or other established system is stronger than adding parallel `CONTEXT.md` and ADR files.

Without configuration, use the standard fallback: a root `CONTEXT.md` glossary and `docs/adr/` decision records. If `CONTEXT-MAP.md` exists, follow it to the relevant context-local paths.

Create fallback files lazily — only when there is a resolved term or qualifying decision to record.

## During the session

### Challenge against the glossary

When the user uses a term that conflicts with the configured glossary, call it out immediately. "Your glossary defines 'cancellation' as X, but you seem to mean Y — which is it?"

### Sharpen fuzzy language

When the user uses vague or overloaded terms, propose a precise canonical term. "You're saying 'account' — do you mean the Customer or the User? Those are different things."

### Discuss concrete scenarios

When domain relationships are being discussed, stress-test them with specific scenarios. Invent scenarios that probe edge cases and force the user to be precise about the boundaries between concepts.

### Cross-reference with code

When the user states how something works, check whether the code agrees. If you find a contradiction, surface it: "Your code cancels entire Orders, but you just said partial cancellation is possible — which is right?"

### Update the glossary inline

When a term is resolved, update its configured canonical home right there. Don't batch these up. For the standard fallback, use [CONTEXT-FORMAT.md](./CONTEXT-FORMAT.md).

A fallback `CONTEXT.md` is an implementation-free glossary, not a spec, scratch pad, or repository for implementation decisions. Respect an existing configured format instead of forcing this fallback shape onto it.

### Record durable decisions sparingly

Only offer to create a durable decision record when all three are true:

1. **Hard to reverse** — the cost of changing your mind later is meaningful
2. **Surprising without context** — a future reader will wonder "why did they do it this way?"
3. **The result of a real trade-off** — there were genuine alternatives and you picked one for specific reasons

If any of the three is missing, skip the record. Follow the configured decision convention; only when none exists, use [ADR-FORMAT.md](./ADR-FORMAT.md).