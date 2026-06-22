---
name: product-principles
description: Shared product design doctrine for planning, reviewing, and testing operator-facing or agent-facing systems. Use when shaping workflows, defaults, onboarding, recovery behavior, error handling, architecture, or regression strategy. Encodes golden-path-first design, safe defaults, self-healing systems, actionable errors, and repo-alignment audits that detect dissonance in AGENTS.md, product-intent docs, onboarding docs, config, and tests.
---

# Product Principles

## Purpose

Use this skill to design and evaluate products so the correct action is the easiest action.

This doctrine is broader than CLI ergonomics. It should shape:
- product architecture,
- onboarding,
- defaults and discovery,
- recovery behavior,
- error semantics,
- documentation,
- regression strategy,
- and the guidance stored in repo files like `AGENTS.md`, product-intent docs, README/onboarding docs, and test plans.

## Core doctrine

Build products so the right thing to do is:
- obvious,
- simple,
- safe,
- and easy to recover when something is missing or stale.

The product should guide both operators and agents toward the correct behavior by default.

A supported product workflow should not depend on hidden tribal knowledge, extra flags that the system could infer safely, or brittle setup steps the system could repair automatically.

Routine product success should not depend on asking the user to run separate status or remedial commands just to complete the original task.

## Golden-path first

Treat the simplest reasonable workflow as a primary product contract.

That means:
- the default onboarding path must work,
- the default day-1 interaction path must work,
- the default recovery path must work,
- and regression tests must validate those paths first.

Advanced flags, override paths, operator escape hatches, and low-level setup steps are still important, but they are secondary surfaces.

A product is not healthy if it technically works only for users who already know the hidden incantation.

## Make the right action the easiest action

Prefer designs where the system naturally steers the user or agent toward the correct next move.

Design for:
- minimal explicit arguments on the common path,
- safe inference from current state, config, and connected product surfaces,
- clear defaults that match the most common successful path,
- and explicit guidance when ambiguity or security boundaries mean inference should stop.

The system should reduce operator burden rather than exporting internal complexity into the interface.

If the product knows the next obvious safe step, it should usually take that step instead of merely describing it.

## Safe defaults and inference rules

Prefer inference when the value can be determined safely from:
- current authenticated state,
- existing config,
- canonical server or API metadata,
- conventional names,
- current workspace or document context,
- or previously validated state.

Rules:
- Prefer canonical discovery over hardcoded environment knowledge.
- Persist healed or discovered defaults when that keeps future state truthful.
- Do not require users to specify values the system can safely determine.
- Do not silently guess when multiple plausible values would materially change behavior.
- When inference is unsafe, fail closed and explain the exact next input required.

## Self-healing systems

Known recoverable preconditions should be repaired automatically whenever that can be done safely.

Examples:
- missing but discoverable runtime config,
- stale session or renewable auth,
- missing local state that can be rehydrated from a canonical source,
- outdated cached config that should be refreshed,
- legacy config locations that can be migrated automatically.

Self-healing expectations:
- detect the issue,
- repair or refresh it,
- retry the intended operation when safe,
- persist the healed state when appropriate,
- and surface what happened in a way the user can understand.

Treat this as the default rule for normal recoverable faults.

Reserve fail-closed behavior for cases where the system lacks high confidence or where the wrong automatic choice could create data loss, privacy/security harm, or identity/authority corruption.

Do not leave systems in a state where the product healed itself successfully but still reports stale or misleading status.

## Errors must always provide a path forward

A product should never leave the operator or agent wondering what to do next.

Error messages should:
- say what failed,
- say why when knowable,
- say what the system already tried,
- distinguish retryable vs fixable vs fail-closed cases,
- name the exact next action,
- and include specific commands, flags, environment variables, or UI steps when relevant.

Assume a capable agent is reading the output.

Errors should be detailed enough that an agent can continue the workflow without needing source-repo access just to decode what happened.

Good errors reduce support burden and make automation more reliable.

Bad errors only describe absence (for example "missing config") without explaining:
- whether the system could have derived it,
- whether the user needs to repair something,
- or what the correct next step actually is.

## Architectural implications

These principles should influence system architecture, not just documentation.

Architect for:
- canonical sources of truth for defaults and discovery,
- explicit capabilities/config discovery from the primary product surface,
- state that can be reconciled and backfilled after healing,
- first-class repair paths instead of ad hoc operator runbooks,
- stable status surfaces that tell the truth after recovery,
- and contracts that support simple onboarding across environments.

Prefer architecture where:
- the primary API can tell a client what it needs to know,
- runtime state can be healed and then persisted,
- and product surfaces can explain both current state and next steps.

Avoid architectures where:
- defaults are scattered across clients,
- recovery logic depends on operator folklore,
- or a successful repair still leaves config, status, or docs misleading.

## Testing doctrine

The easiest supported workflow should be the first thing tested.

Test in this order:
1. **Golden-path workflow tests** — the simplest real onboarding and usage path with minimal explicit inputs.
2. **Override and explicit-option tests** — prove advanced controls still work.
3. **Failure, ambiguity, and non-default-environment tests** — prove the system fails closed or discovers correctly when defaults are insufficient.
4. **Self-healing tests** — prove the system repairs known preconditions and leaves truthful persisted state behind.
5. **Error-guidance tests** — prove failures point users and agents to the correct next action.

Testing should validate:
- onboarding defaults,
- default day-1 workflows,
- normal recovery paths,
- state healing/backfill behavior,
- and cross-surface contract parity when the same workflow spans CLI/API/UI/MCP.

## Planning + review expectations

Plans are operator and agent interfaces. They should make the correct next action obvious before implementation starts, especially when the work has hidden risk, low-confidence choices, UI impact, recovery behavior, or readiness gates.

When planning product work, explicitly define:
- the default workflow,
- what the user or agent should be able to omit,
- which defaults are inferred and from where,
- what the system should self-heal,
- which routine issues must be absorbed into normal command flow rather than exported as extra manual steps,
- where fail-closed behavior begins and why,
- what errors should say,
- which decisions, blockers, and low-confidence areas need near-top Decision Attention,
- whether there is UI impact and what existing/target evidence proves the intended change,
- how agents recover or stop when plan metadata, comments, or readiness state are stale,
- and which tests prove the golden path stays intact.

When reviewing plans or implementations, ask:
- Is the correct path obvious?
- Is the simplest path actually supported?
- Are blockers, required user input, low-confidence choices, and phase-specific dependencies visible where agents will see them before execution?
- Are defaults safe and useful?
- Does the system self-heal known recoverable preconditions?
- After healing, does status/config/reporting tell the truth?
- Do errors provide a concrete path forward?
- Does UI-impacting work include enough current/target evidence to review the intended user experience rather than only prose claims?
- Are tests centered on real usage rather than only fully specified/internal paths?

## Repository alignment / dissonance audit

Use this skill to audit repo guidance and detect drift between intended product behavior and repo reality.

Check for dissonance in:
- `AGENTS.md`
- product-intent docs (`PRODUCT_INTENT.md`, `thoughts/specs/product_intent.md`, or equivalents)
- README/onboarding/install docs
- CLI help text and embedded onboarding text
- config defaults and migration behavior
- runtime status surfaces
- error messages in source and tests
- regression suites and contract tests
- recovery/runbook docs
- plan templates and review prompts
- readiness metadata, browser-review comments, and execution handoff status

Look for misalignments such as:
- docs telling users to supply values the product should discover,
- tests covering only fully explicit/internal workflows while ignoring the golden path,
- self-healing behavior that exists in code but is not reflected in status or docs,
- stale config namespaces, legacy paths, or install methods that confuse real usage,
- errors that describe what is missing but not the exact next step,
- plans that hide blockers, low-confidence decisions, or UI impact below the fold,
- execution handoffs that self-certify readiness, ignore stale comments, or contradict registered readiness metadata,
- product intent that prizes correctness but says nothing about obvious workflows and recoverability,
- or repo guidance that accidentally normalizes operator burden instead of eliminating it.

When you find dissonance:
- surface it explicitly,
- recommend concrete file updates,
- and treat contradictions in docs/tests/default-path behavior as real product debt rather than mere wording issues.

## Output expectations when used during planning

Plans that use this skill should make the following explicit when relevant:
- default workflow contract,
- inferred defaults and canonical discovery source,
- self-healing and backfill behavior,
- fail-closed boundaries,
- actionable error guidance,
- Decision Attention for blockers, low-confidence choices, user input, and phase dependencies,
- UI-impact triage with current/target evidence for visible changes,
- regression coverage for the golden path,
- and any repo-guidance or onboarding updates needed to stay aligned.

If the repo's current `AGENTS.md`, product-intent docs, onboarding docs, config defaults, or tests conflict with this doctrine, call that out directly and suggest the specific updates required to restore alignment.
