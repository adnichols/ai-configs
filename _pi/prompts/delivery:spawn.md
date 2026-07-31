---
description: From any Pi session, create a Herdr worktree from a freeform request and start the delivery workflow there
argument-hint: '<plain-language request; Linear key optional anywhere in the text>'
---

# /delivery:spawn

The operator will almost always give **one freeform request**. They will not pass flags.

Your job: interpret the request, then run `delivery spawn` so a new Herdr worktree is created and the delivery workflow starts. Do not ask them to create the worktree or invent flag syntax.

## Operator input

`$ARGUMENTS` is plain language, for example:

- `honest auto-sync status`
- `NOD-1457 one login path`
- `fix the comment box jumping around on doct`
- `spike ccore health auth guidance NOD-632`

## Interpret, then spawn

1. **Goal / intent** — the whole request, cleaned of pure meta words if needed.
2. **Linear issue** — if a `TEAM-123` key appears anywhere, treat it as the issue. Explicit `--issue` only if you must disambiguate multiple keys.
3. **Slug / branch / label** — do **not** invent flags for these. `delivery spawn` derives them from the goal (and strips issue keys from the slug/label).
4. **Repo / base** — default to the current git root and `origin/main`, unless the request or repo guidance clearly says otherwise (`develop`, a path, etc.).
5. **Agent** — default starts Pi in the new worktree. Use `--no-agent` only if the operator asked for worktree-only setup.

Then run **one** command:

```bash
delivery spawn -- "$ARGUMENTS"
```

Only add flags when inference truly needs them:

```bash
# rare overrides
delivery spawn --base origin/develop -- "$ARGUMENTS"
delivery spawn --cwd /path/to/repo -- "$ARGUMENTS"
delivery spawn --no-agent -- "$ARGUMENTS"
delivery spawn --dry-run -- "$ARGUMENTS"   # preview naming only
```

Prefer:

```bash
delivery spawn -- "NOD-123 fix login redirect"
```

over asking the operator for `--issue` / `--slug`.

## What success looks like

- Herdr worktree created and labeled from the request
- Branch named from issue or `delivery/<slug>`
- `.delivery/ledger.json` + `.delivery/AGENT_BRIEF.md` present
- Child Pi agent prompted to follow the brief (unless `--no-agent`)
- You report worktree path, workspace/pane ids, brief path, inferred issue (if any)

## Parent session rules

1. Run spawn here; do not implement the feature in this session unless asked.
2. If spawn fails, report the exact error and recovery (Herdr down, dirty base, missing git root).
3. If the child agent did not get the prompt, paste a short fallback pointing at `.delivery/AGENT_BRIEF.md`.
4. Guidance not gates — keep going with best-effort inference; do not interrogate the operator for slug/label/params they will not provide.

## Fallback child prompt

```text
Read .delivery/AGENT_BRIEF.md, run delivery show && delivery check -v,
then continue from the recommended next step through
plan ↔ review → run-plan → autoreview → PR. Reflect at the end.
Request: <same freeform text>
```
