ADN_RUNTIME_MARKER:playbook-visual-parity:ecc249f1e306fc64ddf83c7bed16cacf7c2239db

### Visual parity

**You own pixel-exact equivalence. The baseline is the spec. You do not touch it.** Equivalence is verified by image diff, not by eye.

<!-- source-step:visual-parity:1 -->
1. Establish the baseline first, before any migration: a visual regression harness that screenshots the current component across its states, plus the target when matching two implementations. No baseline, no parity claim. A blocking prerequisite, not a follow-up.
<!-- source-step:visual-parity:2 -->
2. Anti-shortcut clauses, stated and held: no harness modifications, no baseline tampering, no component restructuring to make a diff pass. If the baseline looks wrong, stop and ask, don't edit it.
<!-- source-step:visual-parity:3 -->
3. Migrate one component at a time. Parallelize across worktrees, one owner per component (the **separate-before-serializing-shared-state** principle skill). Shared primitives migrate first as a blocking phase.
<!-- source-step:visual-parity:4 -->
4. Verify each component against its baseline via image diff on the matching surface via the control skill. A nonzero diff is a fail. Investigate the pixel delta. `/loop` per component until the diff is zero.
<!-- source-step:visual-parity:5 -->
5. Run **Opening a PR** per component or per safe batch.

<!-- source-step:visual-parity:6 -->
6. Run **Opening a PR** (`playbooks/opening-a-pr.md`).

**Reply:** components migrated, the diff result for each, the baseline harness location, what's left.
