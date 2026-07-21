1. Scope checked

Reviewed the requested roster, callers, PRD flow, direct Linear workflow, policy tests, and docs against `HEAD` and the plan.

2. Coverage table

| Surface | Check | Result | Status |
|---|---|---|---|
| `_pi/agents/` | Exact four-agent roster, models/effort, disabled Explore | Pass | Complete |
| Migrated prompts | No active retired/non-roster subagent routes found | Pass | Complete |
| Generic reviewer routes | Caller write/output authority preserved | Fail; conflicting authority | Complete |
| PRD workflow | Five distinct lenses and downstream handoff parity | Fail; handoff still requires seven | Complete |
| Direct Linear workflow | Branch/path, mismatch, collision, note, upstream contract | Static contract present; required source coverage missing | Complete |
| `_pi/README.md` | PRD roster documentation truth | Fail; still says seven | Complete |

3. Findings

1. **P1 — REGRESSION_FROM_THIS_DIFF**
   [`_pi/prompts/dev:plan-from-prd.md:63`](/Users/anichols/code/ai-configs/_pi/prompts/dev:plan-from-prd.md:63) still requires `reviewersExpected: 7`, `reviewersCompleted: 7`, and an integration count through 7. The migrated PRD review writes five ([`review:prd.md:67`](/Users/anichols/code/ai-configs/_pi/prompts/review:prd.md:67)) and the extension accepts five ([`index.ts:604`](/Users/anichols/code/ai-configs/_pi/extensions/pi-prd-mode/index.ts:604)). Consequently, every successful five-lens review is rejected by `/dev:plan-from-prd`, blocking the required PRD-to-plan handoff. The plan requires maintained-caller parity and BDD5’s five-lens flow.

2. **P2 — REGRESSION_FROM_THIS_DIFF**
   [`_pi/agents/reviewer.md:15`](/Users/anichols/code/ai-configs/_pi/agents/reviewer.md:15) says the reviewer must “never modify the artifact under review,” but `/review:change-gpt` explicitly requires inline edits to that artifact ([`review:change-gpt.md:36`](/Users/anichols/code/ai-configs/_pi/prompts/review:change-gpt.md:36)), as does `/review:plan` ([`review:plan.md:31`](/Users/anichols/code/ai-configs/_pi/prompts/review:plan.md:31)). This makes the generic authority contract contradict the caller-supplied output contract, so inline review comments may be refused. AC4 requires callers to retain authorized annotation/output behavior.

3. **P2 — IN_PLAN**
   [`scripts/tests/test_pi_agent_roster.py:44`](/Users/anichols/code/ai-configs/scripts/tests/test_pi_agent_roster.py:44) covers roster, generic prompts, model retirement, and stale routes, but contains no assertions for `/cmd:start-linear-issue`. The plan explicitly requires source-contract assertions for its exact branch/path derivation, `.ltui.json` mismatch stop, context-note fields, success output, and non-destructive collision handling. The current pass result therefore does not verify BDD6 or the direct-worktree migration.

4. **P3 — REGRESSION_FROM_THIS_DIFF**
   [`_pi/README.md:339`](/Users/anichols/code/ai-configs/_pi/README.md:339) still states that `/review:prd` writes and removes seven reviewer files. The migrated workflow and extension use five. This violates AC8’s documentation-truth requirement and gives operators an incorrect status-artifact contract.

5. **Final verdict**

VERDICT: FIX_IN_SCOPE_FINDINGS