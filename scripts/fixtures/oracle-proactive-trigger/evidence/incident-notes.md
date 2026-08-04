# Incident notes (new evidence after plan lock)

Date: synthetic

## Observed failure

In 4/4 forced-kill reproductions:

1. Hub remote delete succeeded (space gone on Hub).
2. Process died inside `local_cleanup_v1` after deleting `sync_remote` but before
   deleting `space`.
3. Local UI still listed the space; sync retry then recreated partial remote
   pointers against a Hub 404.

## Conclusion from reproduction

Option A (CLI best-effort cleanup after Hub success) cannot meet AC2 under
process death. The node-owned transactional cleanup path (`node_tx_cleanup_v2`)
already used by neighboring authority mutations would keep receipt + local
cleanup atomic.

## Tension

This directly conflicts with locked plan decision #1 (Option A). Choosing
Option B revises a locked ownership/public-contract boundary and is
hard-to-reverse once clients depend on node-side cleanup semantics.
