# Close out the source doc

For an item with a `Source doc:`, after its PR merges and before `CLEANED`.
The author asked for the report, so they must learn it is fixed. The driver
does this, not the worker. Read `~/.agents/skills/ava/SKILL.md` first.

1. **Live?** Run `pnpm rollout` in the ccore2 repo and compare the hub's
   deployed source commit with the merge commit. Never deploy or offer to.
2. **Add a short status section** to the doc: what changed, PR link, merge
   commit, live or not.
   - HTML doc: `ava document edit <doc> --file <html> --expected-revision
     <rev> --idempotency-key <key>`, revision from a fresh read. Keep its
     standing; check the render `warnings`.
   - Text doc: append the section to the current body; `ava document
     replace-body <doc> --file <md> --idempotency-key <key>`.
3. **Comment on that section mentioning the author.** An `@Name` in the body
   alone mentions nobody. Take `actorId` (as `targetId`) and `kind` (as
   `targetKind`) from `ava comment mention-suggestions`.
   - HTML doc: `ava document comment create <doc>` with a `dom` anchor on the
     new section and `mentions: [{"token":"@Name","targetKind":"human"|"agent","targetId":"act_..."}]`.
   - Text doc: `ava document text-comment create <doc>` with a unique `quote`
     from the new section and `mentions: [{"token":"@Name","targetId":"act_..."}]`.
   Mention the human principal and the reporting agent when both are known.
   Read the comment back (`ava document comment list <doc>` or `ava document
   text-comment list <doc>`) and confirm the mentions are stored.
4. **No self-mention**; it notifies nobody. When another agent owns the doc
   (for example perf-explorer for its inventory), hand it the update with the
   PR link and merge commit.
5. **A design doc with several items** is updated once, after all its items
   land. If the operator asks, note partial progress after each item instead.

Record the section and comment links in the item's timeline. An item with no
`Source doc:`, or one concluded without a merge, skips this.
