---
name: autoreview
description: Run a bounded pre-PR implementation review with the active harness's configured reviewer subagent, fix or disposition blocking findings, and stop instead of entering non-converging review loops. Use this before opening pull requests, after an implementation is complete, or inside run-plan; inside run-plan this gate hands back to PR creation rather than waiting for external approval.
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Bounded implementation review

Review the user's completed candidate against its requirements and verification evidence. The gate concerns material in-scope correctness and regressions, not optional polish or unrelated pre-existing issues. Do not require PR-hosted approval or use an external client as the default review transport.

Record the target checkout, HEAD, comparison base, dirty/staged/untracked files, changed surfaces, acceptance criteria, exclusions, and actual verification results. A dirty or isolated checkout is provenance, not a reason to refuse review. The reviewer reads the explicitly named candidate paths.

Request one bounded read-only native reviewer using the runtime contract. Include raw requirements, the candidate, and evidence, not the implementer's conclusion as proof. Ask for findings with location, trigger, consequence, evidence, severity, and scope category, or a clear no-material-findings verdict. The reviewer performs static inspection; the driver owns executable checks and fixes.

Classify findings as blocking in-scope, non-blocking in-scope, out-of-scope, or refuted. P1/P2 concrete in-scope failures block a clean verdict. P3 is non-blocking unless required by the plan or verification, or a regression caused by the change. Verify claims before editing.

Count usable prior passes on the same unchanged candidate. Default to one review and one targeted rereview after fixes. A third pass is allowed only for a new concrete blocker introduced or exposed by the fixes. Before reporting non-convergence, run one bounded `oracle-consultation` for the fixed candidate; use any further escape pass only as repository policy permits. Do not reset the budget by renaming the review.

For small reversible work, one pass suffices unless a fix creates a new blocker. Missing reviewer coverage is not a clean verdict. Return findings, dispositions, evidence limitations, and OPEN_PR_READY when no material blocker remains. Within `run-plan`, that verdict hands back to publication. An explicit user instruction to publish regardless overrides publication gating, but not the truth of the review status.
