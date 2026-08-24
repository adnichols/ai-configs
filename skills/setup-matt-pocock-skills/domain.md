# Domain Docs

How the engineering skills should consume this repository's canonical domain language and durable decisions.

## Configured sources

List the repository's actual sources of truth here:

- **Glossary / domain language:** `<path or section>`
- **Durable decisions:** `<path, directory, or section>`
- **Document map:** `<path or none>`

Read only the sources relevant to the area being explored. If a configured source is absent, proceed silently.

## Update rules

- Use the configured glossary's vocabulary in issue titles, refactor proposals, hypotheses, and test names.
- When a term is resolved, update its configured canonical home inline.
- When a decision conflicts with an existing record, surface the conflict instead of silently overriding it.
- Never create a parallel glossary or decision system when the repository already has a canonical one.

## Standard fallback

When no stronger convention exists, use a root `CONTEXT.md` as an implementation-free glossary and `docs/adr/` for sparse architectural decisions. A genuine multi-context repository may instead use a root `CONTEXT-MAP.md` pointing to context-local `CONTEXT.md` and `docs/adr/` paths.

Create fallback files lazily: the first resolved term creates `CONTEXT.md`; the first qualifying architectural decision creates `docs/adr/`.