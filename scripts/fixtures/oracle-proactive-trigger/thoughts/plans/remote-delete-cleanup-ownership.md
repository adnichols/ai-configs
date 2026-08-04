# Remote delete cleanup ownership

Status: execution-ready reviewed plan (synthetic fixture)

## Goal

After a successful remote owner-space delete, local cleanup must not leave
split-brain state.

## Locked decisions

1. **Cleanup ownership = Option A (CLI helper).**  
   Keep using `local_cleanup_v1` in the CLI after Hub returns success. Do not
   move cleanup into the node transactional path in this slice.
2. Public CLI success still means "Hub delete acknowledged."
3. No new user-visible product flags.

## Acceptance criteria

- AC1: Documented ownership boundary is intentional and consistent with the lock
  above, or the lock is explicitly revised with recorded advisory disposition.
- AC2: Split-brain after Hub success is not left as an accepted silent failure.

## Implementation notes

Current helper path: `src/cleanup_policy.md` documents `local_cleanup_v1` as the
CLI post-success cleanup owner.

## Out of scope

- Dependency upgrades
- UI work
- Broad deletion redesign beyond the ownership boundary choice
