# Run-plan coverage ledger

## Scope contract

- Plan: `thoughts/plans/delivery-herdr-agent-tabs.html`
- Goal: launch delivery implementation and completeness agents into full-size labeled Herdr tabs in the existing workspace, preserving unique agent names and pane-based agent start/control.
- In scope: `skills/delivery-run/scripts/delivery`, delivery CLI tests, delivery/run-plan/supervise docs and prompts named by the plan, source-plan progress synchronization, review and PR evidence.
- Out of scope: Pi subagent transport, auto-focus/auto-close, workspace-per-agent redesign, Herdr GUI/theme changes, global non-delivery Herdr defaults.
- Required verification: `bash skills/delivery-run/tests/test_delivery_cli.sh`; stale pane-split instruction searches; named AC1–AC7 / BDD1–BDD5 coverage.
- Target branch: `origin/main` (repository default).

## Integration record

| Contract / distributed behavior | Source of truth | Producers | Consumers / dependent surfaces | Coverage declaration | Required proof | Status |
|---|---|---|---|---|---|---|
| `herdr tab create --workspace <id> --cwd <root> --label <label> --no-focus` JSON at `result.root_pane.pane_id` and `result.tab.tab_id` | Reviewed plan live Herdr 0.7.5 probe; `skills/herdr/references/cli.md` | New shared delivery helper | Implementation launch; completeness launch; dry-run output | Exhaustive-by-family for delivery multi-agent launch sites | Production entry tests assert argv, parse exact response, and start on returned pane | Reconciled — P2 tests green |
| Workspace discovery | `resolve_herdr_targets()` plus `herdr pane get <source>` response `result.pane.workspace_id` | Shared helper | Both launch families | Exhaustive-by-family | Failure matrix covers missing/non-JSON/non-object pane-get results | Reconciled — seven fail-closed cases green |
| Agent identity and launch | Existing `herdr agent start <name> --pane <id>` / `agent prompt <name>` contract | Implementation and completeness launch paths | Pi agents, rerequest/read/accept flow | Exhaustive-by-family | Tests assert names remain control targets and rerun reuses the existing agent | Reconciled — production and rerun tests green |
| Ledger agent location | `.delivery/ledger.json` schema-in-code | Implementation profile; completeness review record | Verification, rerun, accept, show/history/debug | Exhaustive-by-writer | Tests assert `paneId` + `tabId`; primary `labels.herdrTabId` unchanged | Reconciled — primary tab target test green |
| Delivery launch instructions | Plan inventory and current corpus search over delivery/run-plan/supervise/prompts/AGENTS | Docs and generated brief | Operators and agents | Exhaustive over plan-named corpus | Corpus test and stale-reference search | Reconciled — corpus test and final search green |

Source search before edits:

```text
rg -n "pane split|launch_implementation_agent|cmd_completion_review|resolve_herdr_targets|maybe_herdr_label" \
  skills/delivery-run/scripts/delivery skills/delivery-run/tests/test_delivery_cli.sh \
  skills/delivery-run/SKILL.md skills/run-plan/SKILL.md skills/supervise \
  _pi/prompts/delivery:run.md _pi/prompts/delivery:bootstrap.md AGENTS.md
```

Inventory reconciliation before edits: implementation and completeness are the only production delivery launch families; supervise is documentation-only and is explicitly included. Agent tab IDs must never flow into `labels.herdrTabId`.

## Phase / verification log

- Runtime authorization: `delivery verify-implementation-profile` passed for `openai-codex/gpt-5.6-sol` at medium; stage entered `IMPLEMENTING`.
- Doct: lifecycle active; board moved from `backlog` to visible `in_progress` before code edits.
- Review-cycle budget: 3/3 ordinary implementation-review cycles used. Cycle 1 found stale dry-run help; cycle 2 confirmed that fix and exposed one stale sibling completeness instruction; cycle 3 passed after the scope-bound docs/test correction. Final active-harness verdict: PASS.
- Verification convergence: 3 purposeful full-suite attempts on the evolving working tree (P2, P3 RED/GREEN, final P4); latest `bash skills/delivery-run/tests/test_delivery_cli.sh` passed 34/34.
- P1: complete — shared label/workspace/tab-create helpers exist and fail closed.
- P2: complete — implementation and completeness launch families use labeled tabs; IDs persist; production/rerun/failure tests pass.
- P3: complete — delivery, run-plan, supervise, prompts, generated brief, and AGENTS guidance use labeled tabs; corpus test passes.
- P4: complete — Python and shell syntax checks pass; exact `pane split` and stale `splitCommand` searches are empty; named AC/BDD suite passes 34/34.
- Visible completeness review: Grok 4.5 high returned `VERDICT: COMPLETE` for request `25b519eb30454aa6ba65204b6fae32ee`; accepted artifact `thoughts/validation/delivery-use-tabs-completeness.md`. The live launch itself exercised the new path in workspace `wDV`, labeled tab `wDV:t3`, root pane `wDV:p4`, while the primary delivery tab remained `wDV:t1`.
