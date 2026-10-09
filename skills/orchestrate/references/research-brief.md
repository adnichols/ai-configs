# Research brief

Send one read-only research agent per new item. It runs in the background
while intake continues; merge its findings into the item file when it
returns.

```
Read-only research for work item WI-NN in orchestrator tracker <tracker-id>.
Do not edit files, run Git mutations, or contact anyone.

Repository: <checkout path> (base <branch>)
Item file: <absolute path>; read it first. Screenshots: <absolute paths>.
Other open items in this tracker (for overlap): <ID + one-line title each>

Find, citing file paths and line ranges:
1. Where the named product surface lives in code: routes, components,
   handlers, and data paths involved in the reported behavior.
2. For a bug: the code path that plausibly produces the observed behavior,
   and one to three root-cause hypotheses ranked by evidence. For a feature
   or other change: the nearest existing behavior and where the change would
   land.
3. Recent commits or merged PRs touching this area (`git log` on the paths;
   `gh pr list --state all --search <terms>`), and open PRs or issues that
   already address it.
4. Reproduction steps written as user interactions, each with the expected
   observation (route, account role, fixture data, then "click X, expect
   Y"), marking each guessed step. The worker inherits these as its
   interaction checklist, so a data or render check is not a step.
5. Whether the change affects UI, which needs a verified-build prototype, and
   which UI states it could affect.
6. Overlap with the other items listed above (same surface or root cause).
7. Facts still missing to write observable acceptance criteria, phrased as
   product behavior questions the operator could answer in one line.

Return at most 400 words. Separate verified facts from inference.
```
