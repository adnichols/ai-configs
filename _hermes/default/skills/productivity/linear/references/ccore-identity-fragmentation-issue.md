# C-Core / Heddle account identity fragmentation evidence

Session-derived reference from the investigation that led to Linear issue NOD-1084. Use this when opening or refining issues around account identity resolution, support diagnostics, or operator-facing account lookup.

## Core finding

`system_account_profile` is the closest local account identity table, but it is narrow and under-hydrated. It reliably covers logged-in/local accounts, while collaborator identities often live only inside per-space JSON or authority artifacts.

## Local schema evidence

`ccore/crates/ccore-node/migrations/0012_system_audit.sql`:

```sql
CREATE TABLE system_account_profile (
  hub_url TEXT NOT NULL,
  account_id TEXT NOT NULL,
  account_handle TEXT NOT NULL,
  provenance_json TEXT NOT NULL,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  PRIMARY KEY (hub_url, account_id)
);
```

Rust model in `ccore/crates/ccore-node/src/db/types_common.rs` only has typed fields for `hub_url`, `account_id`, `account_handle`, `provenance_json`, `first_seen_at`, and `last_seen_at`. Email/display name/Clerk provider/subject are not typed local fields.

Upsert path in `ccore/crates/ccore-node/src/db/system_audit.rs` only writes `account_handle` and opaque `provenance_json` for the profile row.

## Hydration evidence

`ccore/crates/ccore-node/src/http/runtime_auth.rs` upserts `system_account_profile` during runtime/Clerk login/bootstrap for the authenticated tuple, then uses it for Clerk linkage checks and account-handle display. That explains why signed-in accounts are visible in the profile table while other referenced accounts may not be.

`ccore/crates/ccore-node/src/account_catalog_runtime/reconcile.rs` persists catalog/converge linkage, scope, and `sharing_state_json` into `space_config`, but collaborator/member identities from `sharing_state` / `members` are not necessarily promoted into `system_account_profile`.

## Hub has richer identity shape

`ccore/packaging/cloudflare/hub/src/index.ts` has:

```ts
interface AccountProfile {
  account_id: string;
  account_handle: string;
  account_email: string;
  account_display_name: string;
  legacy_account_ids?: string[];
  external_auth_provider?: "clerk";
  external_subject?: string;
  ...
}
```

`MembershipStateArtifact.members` includes `account_id`, `account_handle`, `account_display_name`, `account_email`, `role`, `membership_scope`, `status`, and `joined_at`.

## Example impact from host inspection

The local active DB knew `acct_a631...` as Aaron/anichols/aaron@nodaste.com through `system_account_profile` and auth provenance.

The same host knew `acct_0221...` as Ana/ana@nodaste.com only via `space_config.sharing_state_json` for spaces like Nodaste/Tinker, not as a `system_account_profile` row.

Tinker vs Nodaste required cross-reading `space_config` and `sharing_state_json` to understand that:

- `linked_account_id` was Aaron's active account.
- `scope_id` could be another account's custody/creator scope for a shared space.
- The other account identity (`acct_0221...`) was Ana.

This is support-hostile: a supported operator surface should resolve account IDs without SQLite spelunking.

## Impact themes

- Account IDs appear in auth, discovery, scope/custody, authority, device delegation, device capability, sharing, membership, sync/quarantine, and support surfaces.
- Human identity may be typed on the hub, embedded in per-space JSON locally, embedded in provenance JSON, or absent.
- Support/quarantine code already reconstructs member identity ad hoc from roster evidence, including account id/fingerprint/handle/email/display name gated by visibility policy.
- Operators risk false diagnoses around account collision, wrong-context, Private-space scope, and shared-space provenance when identity is not canonical.
