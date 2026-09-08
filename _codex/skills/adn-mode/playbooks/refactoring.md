# Refactoring

Read the parent skill and [Codex runtime contract](../references/codex-runtime.md).

Identify the behavior that must remain unchanged and the structural problem to solve. Trace callers and contracts. Choose the smallest coherent target shape; use `architect` only for material uncertainty. The driver migrates callers and removes the superseded path within the same complete slice. Run verification that would detect a behavior change. Review concrete regressions without adding unrelated product requirements. Preserve repository branch and commit policy. Report the structural change and evidence of preserved behavior.
