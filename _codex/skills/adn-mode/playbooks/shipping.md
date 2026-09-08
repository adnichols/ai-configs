# Shipping

Read the parent skill and [Codex runtime contract](../references/codex-runtime.md).

Require task authorization for landing the exact repository and changes. Inspect the current heads, required checks, review findings, target branch, and stack dependencies. Verify the intended candidate rather than a stale green head. Use the repository's merge policy and only its authorized remote. For a stack, land only the contiguous verified portion from the root and recheck dependent PRs. Do not reset dirty work, force-push shared branches, bypass required checks, or infer deployment permission from merge permission. Report landed and remaining changes with evidence.
