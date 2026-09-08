# Bug fix

Read the parent skill and [Codex runtime contract](../references/codex-runtime.md).

Reproduce the reported behavior on the relevant runtime or a faithful local path. Record the failing observation. Trace candidate causes with `how` and relevant regression history with `why`; test hypotheses until evidence supports the mechanism. The driver implements the smallest in-scope fix. Rerun the original reproduction and relevant regression checks. Use TDD only when explicitly requested. Run `adversarial-fix-review` for an independent check of the necessity and evidence, counting existing equivalent review once. If reproduction is unavailable, report the exact evidence gap and do not claim the bug fixed. Publish only within task authorization. Report symptom, mechanism, change, and before/after evidence.
