# Hillclimb

Read the parent skill and [Codex runtime contract](../references/codex-runtime.md).

State the target metric, baseline, stable workload, correctness constraints, and bounded stopping condition. Log each hypothesis and before/after measurement. The driver runs isolated experiments, keeps wins that meet correctness constraints, and reverts only its rejected experimental changes. Preserve evidence and the best verified candidate. Stop at the target, a user limit, or a concrete blocker. Report the metric trajectory and retained change. Do not create a goal or automation unless explicitly requested.
