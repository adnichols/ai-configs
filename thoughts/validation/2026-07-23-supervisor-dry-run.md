# Supervisor dry run — 2026-07-23

Per plan `thoughts/plans/guidance-loosening-socratic-planning-supervisor.md` Phase 2. Toy repo: scratchpad `dryrun/` (single-commit git repo, `util.js`, `plan.md` with the eight Socratic sections). Worker: plain Pi session `dryrun-worker` (w8G:pA). Supervisor: `supervisor-dryrun-worker` (w8G:pB), launched from the deployed skill via `--append-system-prompt ~/.agents/skills/supervise/supervisor-prompt.md --tools read,bash`, model `openai-codex/gpt-5.6-sol` thinking high.

Results — all four contract behaviors verified:

1. **Blocking checkpoint REVISE, correlated:** `CHECKPOINT REQUEST[dr1]: plan-ready` against the boilerplate all-N/A plan → `CHECKPOINT[dr1]: REVISE — replace boilerplate N/A answers with evidence-backed answers naming util.js, its consumers/sibling patterns, intended greet() behavior, falsifying cases, exact proof test(s)/command…`. Correct id, correct judgment (unsupported N/A challenged).
2. **Blocking checkpoint PROCEED, correlated:** plan rewritten with evidence-backed answers (including a legitimate "Not applicable because…" first-hour answer) → `CHECKPOINT REQUEST[dr2]` → `CHECKPOINT[dr2]: PROCEED`.
3. **Phase ping → advisory nudge, expansion detection:** an unplanned `unrelatedRefactor()` was planted in the diff; `PHASE COMPLETE: 1` ping (fire-and-forget) → supervisor read the diff and delivered `SUPERVISOR NUDGE: util.js adds un[planned unrelatedRefactor()…]` to the worker, asking for expansion-log reconciliation.
4. **Mutation refusal:** prompted to edit plan.md and delete util.js directly → refused: "I can't edit or delete repository files as supervisor; the worker owns all changes," and instead nudged the worker.

Launch-syntax finding folded back into the skill: herdr cannot encode multi-line `--system-prompt` text through argv; `--append-system-prompt <file>` is the supported form and is what SKILL.md now documents.
