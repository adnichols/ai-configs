---
name: bugbash
description: Indefinite alias for orchestrate. Use when the operator says "/bugbash", "bugbash", "bug bash", or "start a bug bash", or when resuming a bug bash whose state is under ~/.local/state/bugbash/. Immediately follow the canonical orchestrate skill; the two names start the same work tracker.
---

# Bugbash alias

`bugbash` and `orchestrate` are the same skill. Read `skill://orchestrate`
(OMP: `/skill:orchestrate`) now and follow it exactly, treating this
invocation and its arguments as an `/orchestrate` invocation. Do not
redefine or duplicate any of its process here.

`scripts/` and `references/` in this skill are links to the orchestrate
copies, so `~/.agents/skills/bugbash/scripts/...` commands in an existing
bug bash ledger keep working.

To resume a bug bash started before the rename, keep its state directory
under `~/.local/state/bugbash/`, its `BB-NN` IDs, its `issues/` directory,
and its `Type` status column. The orchestrate scripts read those ledgers as
they are, including `Broken:` in Waiting on you cards and `--bugbash-dir` for
`spec_diff.py`. New trackers use the orchestrate layout.
