# Babysit

Read the parent skill and [Codex runtime contract](../references/codex-runtime.md).

Distinguish a status-only request from a request to fix CI or review findings. Inspect the current PR head, checks, mergeability, and existing comments once. For status-only, return the snapshot without edits. For authorized maintenance, triage each finding against intent, fix real in-scope failures in the driver, verify changed behavior, and refresh the snapshot. Use bounded waits for running checks. Do not wait indefinitely for absent bot approval or start babysitting just because a PR was opened. Do not merge without authorization.
