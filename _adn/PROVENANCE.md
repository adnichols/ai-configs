# ADN provenance

Upstream: https://github.com/cursor/plugins/tree/46756f89270d7e7dcb8c28c90fd0f957ade4ce2c/pstack
Pin: `46756f89270d7e7dcb8c28c90fd0f957ade4ce2c`
License: MIT (Lauren Tan). Full text: `LICENSE.pstack`
Review date: 2026-08-26

ADN translates pstack behavior into OMP. It does not copy Cursor runtime, Graphite, cloud workers, Plan Mode, Benny, or vendor model files.
Post-pin upstream changes, including `make-bot-ui`, require explicit `adopt-skill` adoption. Installed source is pinned; do not silently refresh it.

OMP adaptation policy: retain named outcomes; replace only declared runtime dependencies; fail closed on missing required sources or roles.
