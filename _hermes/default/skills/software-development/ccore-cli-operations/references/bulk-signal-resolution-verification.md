# Bulk signal resolution verification

When Aaron says all signals are handled/obsolete, it is reasonable to bulk-resolve current nonterminal C-Core signals, but verification matters.

Observed pattern:
- `ccore signal list nodaste --json` returned several `new` signals.
- A batch `ccore signal resolve <id> --expected-current-version-id <version> --json` succeeded for each listed nonterminal signal.
- A fresh list still showed one signal as `in_progress` with a different `current_version_id`.
- `ccore signal get <id> --json` returned the fresh version; resolving with that version succeeded.
- A final `ccore signal list ... --json` confirmed `active_count: 0`.

Reusable operator pattern:

```bash
ccore signal list nodaste --json
ccore signal resolve <id> --expected-current-version-id <version> --json
ccore signal list nodaste --json   # verify nonterminal set
ccore signal get <remaining-id> --json
ccore signal resolve <remaining-id> --expected-current-version-id <fresh-version> --json
ccore signal list nodaste --json   # final verification
```

Use a terminal-status filter such as:
- terminal: `resolved`, `canceled`, `cancelled`, `deleted`
- also ignore archived/deleted records.

Do not report completion until the fresh post-update list has zero active/nonterminal signals.
