---
name: integration-integrity
description: Use when an authorized change touches exact contracts that types cannot verify or behavior required across multiple production sites.
---

# Integration Integrity

Load this skill before the first dependent edit when either trigger applies.

## Triggers

### Exact contract

Use this path for positional data, serialized field names, environment variables, configuration keys, command flags, paths, headers, wire payloads, migration fields, documented command forms, or other exact values that compilation cannot fully check.

### Distributed behavior

Use this path when the required behavior spans multiple production call sites, handlers, operations, resources, surfaces, or environments.

If neither trigger applies, continue without manufacturing or recording an inventory.

## Record before editing

Keep a compact record in the active work state:

```markdown
## Integration integrity
- Trigger: exact contract | distributed behavior | both
- Source of truth: <file, schema, command definition, or authoritative source>
- Producers: <writers or emitters>
- Consumers: <readers or parsers>
- Dependent docs/examples: <paths or none>
- Inventory basis: <source search used to find sites or families>
- Coverage: exhaustive-by-site | exhaustive-by-family | justified-representative
- Required proof: <cross-boundary or production-path verification>
- Reconciliation: pending | reconciled
```

For justified representative coverage, state why the selected evidence covers omitted sites.

## Change procedure

1. Reopen the current source of truth before editing a producer, consumer, or dependent example.
2. Search for every in-scope reader, writer, importer, string reference, documented example, and production site or family.
3. Update the in-scope results and keep the record current.
4. Run the real boundary or production-dispatch verification.
5. Repeat the stale-reference search after the change.
6. After compaction, handoff, resume, rebase, or a material review finding, reopen the source of truth and reconcile the record before continuing dependent work.

A contractual documented CLI form must execute through the actual parser. Help text or documentation-string assertions alone are not proof.

## Completion bar

A helper, middleware, wrapper, shared event, or event-existence test proves infrastructure only. Completion requires:

- the declared producers, consumers, sites, or families are reconciled;
- the intended behavior is proven through the real cross-boundary or production path;
- dependent documentation and examples are current;
- the final stale-reference search is clean; and
- any newly exposed product outcome is returned to the owner for direction rather than silently added to scope.
