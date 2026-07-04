# Linear issue coverage audit pattern

Use when Aaron asks whether a Linear issue is covered by an existing reviewer-facing Doct/repo plan.

## Goal

Make coverage concrete and reviewable. A plan title, Linear key badge, or `data-linear-issue` attribute proves linkage, not coverage. Coverage means every issue goal/acceptance area maps to named plan anchors, acceptance criteria, BDD scenarios, and phases.

## Steps

1. Read the issue, preferably through repo-local `ltui`:

   ```bash
   ltui --format json issues view NOD-123
   ```

2. Read the local HTML plan source and its discovery ledger.
3. Build a coverage matrix with one row per issue requirement:
   - issue requirement / acceptance area
   - plan section anchors
   - AC IDs
   - BDD scenario IDs
   - phase IDs
4. If the plan lacks explicit coverage, insert a dedicated section near Linear tracking / acceptance criteria:

   ```html
   <section data-section="nod-123-coverage" id="nod-123-coverage" data-anchor="nod-123-coverage" data-linear-issue="NOD-123" data-coverage="complete">
     <h2>NOD-123 Coverage Matrix</h2>
     <table><tbody>
       <tr><th>NOD-123 area</th><th>Plan coverage</th></tr>
       <tr><td>...</td><td>Target contract <a href="#target-contract">#target-contract</a>; AC <a href="#ac-1">#ac-1</a>; phase <a href="#phase-p1">P1</a>.</td></tr>
     </tbody></table>
   </section>
   ```

5. Update the discovery ledger with a short coverage audit note.
6. Validate locally:

   ```bash
   node scripts/plans/validate-html-plan.mjs thoughts/plans/<slug>.html
   git diff --check -- thoughts/plans/<slug>.html thoughts/discoveries/<slug>.md
   ```

7. Publish via Doct using the current integer document version:

   ```bash
   doct-agent documents get --base-url https://doct.nodaste.com --id <document-id> --json
   doct-agent plans update \
     --base-url https://doct.nodaste.com \
     --id <document-id> \
     --workspace-id <workspace-id> \
     --file thoughts/plans/<slug>.html \
     --source-format html \
     --expected-version <document.version> \
     --json
   ```

8. Read back and verify the coverage text/attributes are present:

   ```bash
   doct-agent documents get --base-url https://doct.nodaste.com --id <document-id> --json
   doct-agent plans queue list --base-url https://doct.nodaste.com --workspace-id <workspace-id> --document-id <document-id> --json
   ```

9. Add a Linear comment so the issue points to the Doct plan:

   ```bash
   ltui issues comment NOD-123 --body @/tmp/nod-123-plan-coverage-comment.md
   ```

## Notes

- Keep the coverage matrix focused on the Linear issue, not the broader umbrella project.
- Use stable HTML anchors because Doct comments are node/selector based.
- Mention untracked plan files in final handoff if they remain uncommitted.
