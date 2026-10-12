Reconstruction of tracker 20261006-weekly (`~/.local/state/bugbash/20261006-weekly`) as it stood on
2026-10-11 13:30Z, six minutes before the driver launched BB-78, BB-114, BB-115 and BB-116.
The final ledger shows all four as CLOSED (transferred), so this fixture restores their QUEUED
rows and timelines from the issue files' own logs (`logged QUEUED` 2026-10-08T13:50-06:00 and
2026-10-09T03:50Z) and the ledger's Merged cells for BB-69 and BB-75. The only addition is the
machine-readable `gate:` on BB-78, which the original ledger wrote as prose ("launch once BB-69/BB-75
document-chrome work is settled"). BB-114's "Depends on BB-116" is a merge-time dependency, not a
launch gate, so it has none. Run: `reconcile.py <this dir> --now 2026-10-11T13:30Z --no-live`.
