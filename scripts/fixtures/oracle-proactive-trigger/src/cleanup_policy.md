# Cleanup policy (current code)

## local_cleanup_v1 (CLI)

After `space delete-remote` receives Hub HTTP 200:

1. CLI calls `local_cleanup_v1(space_id)`.
2. Helper deletes local `sync_remote`, then `access_event`, then `space` rows.
3. Failures after Hub success are logged and returned as soft warnings; Hub
   delete is not rolled back.

## node_tx_cleanup_v2 (exists, unused by delete-remote)

Other authority mutations already perform local cleanup inside the node SQLite
transaction that records the authority receipt. That path is atomic with the
local receipt write. Delete-remote does **not** call it today because the plan
locked Option A.
