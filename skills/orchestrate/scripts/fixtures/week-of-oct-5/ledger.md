# Work orchestration — week of October 5 (as of 2026-10-11 13:30Z)

Mode: ORCHESTRATION

## Status
| ID | Type | Title | Repo | State | Workspace / agent | PR | Waiting on | Merged | Deployed |
| ---- | ------ | ------- | ------ | ------- | ------------------- | ---- | ------------ | ------ | -------- |
| BB-116 | BUG | WebSocket handshake writes document_session_occupancy before admission | ccore2 | QUEUED | — | — | driver: reviewer-two BLOCK on #745, pre-existing; dependency of any BB-114 cleanup proof | — | — |
| BB-115 | BUG | An admission row is still left when a disconnected request's work outlives the 30 s waitUntil budget | ccore2 | QUEUED | — | — | driver: reviewer-two BLOCK on #745, residual and fail-closed; needs a safety design | — | — |
| BB-114 | FEATURE | Operator-run, fail-closed command to clear leaked hub admission rows | ccore2 | QUEUED | — | — | driver: remediation half of BB-104. Merge after BB-116. | — | — |
| BB-78 | FEATURE | Bring the Web UI in line with the amended contract from #704 (ADR 0055 D6–D7) | ccore2 | QUEUED | — | — | gate: BB-69, BB-75 (document-chrome work settled; contract approved, no operator ask) | — | — |
| BB-75 | BUG | Comment author shows a raw Actor id instead of a name | ccore2 | CLEANED | archived | https://github.com/Nodaste-Lab/ccore2/pull/718 | — | 2026-10-08 22:45Z 366fd5683 | — |
| BB-69 | BUG | (W072) Document details rail says "No saved versions" after a version is saved | ccore2 | CLEANED (merged 703c2ca3f) | archived | https://github.com/Nodaste-Lab/ccore2/pull/716 | — | 2026-10-08 17:58Z 703c2ca3f | — |

## Landing queue
Empty.
