# Behavior-changing spec diff page

Only for spec or ADR changes that change what users see or a documented API
contract and that no operator ruling or approved prototype already decides
(SKILL.md § Spec and ADR changes).

1. The worker writes the edit uncommitted in its worktree and runs:

   ```
   python3 <skill-dir>/scripts/spec_diff.py <worktree> --base <base branch> --path spec --title "<what changes>" --summary-file <plain-terms note> --reply "<how to answer>" --tracker-dir <tracker-dir> --publish
   ```

   One `--path` per spec directory; `--head <ref>` renders a commit instead of
   the working tree. Needs only Python and pandoc; reads the text from git.
2. It saves one draft Ava page as a subdocument of the tracker's dashboard
   (`parent_id` = `plan_id` from `<tracker-dir>/dashboard.json`; it fails
   when that file has no `plan_id`, and moves and rechecks a page whose create
   ignored the parent). The page shows each changed file as one inline diff,
   removed words struck through and added words marked in place, plus a
   collapsed view of the whole file with the change marked. `manifest.json`
   beside it fingerprints the proposed files.
3. The item's `## Waiting on you` card links the page in `Links:` and leaves
   the wording out. The operator's decision covers exactly the rendered diff.
4. After the decision the worker commits those bytes unchanged and runs
   `python3 <skill-dir>/scripts/spec_diff.py <worktree> --check
   <out>/manifest.json --head HEAD` before pushing. Changed text is a new
   proposal: rerun with the same `--out` to update the page, and ask again.
