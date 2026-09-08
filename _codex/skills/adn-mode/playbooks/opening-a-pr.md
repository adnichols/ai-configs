# Opening a pr

Read the parent skill and [Codex runtime contract](../references/codex-runtime.md).

First establish that the task includes PR creation for this repository. Follow its branch policy, including main-only exceptions. Preserve unrelated dirty work; never reset or reconstruct a checkout to simplify publication. Run required verification and `autoreview` within the existing review budget. Use `safe-git-index` for index mutations and `cmd-create-pr` for publication. Respect explicit draft/ready choices and repository title conventions, including issue keys. Report the actual verification and review status. Opening a PR does not authorize a merge, deploy, or indefinite monitoring. Return its verified URL.
