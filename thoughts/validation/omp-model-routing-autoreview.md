# OMP model-routing targeted rereview

## Scope checked

Rereviewed only the prior P2 correction in
`skills/delivery-run/scripts/delivery`, its focused regression coverage in
`skills/delivery-run/tests/test_delivery_cli.sh`, and the two generated OMP
instruction paths affected by the correction.

## Evidence

- **Fixed OMP identity and default packet:**
  `skills/delivery-run/scripts/delivery:3110-3117` declares the fixed
  `OMP_COMPLETENESS_REVIEWER_IDENTITY` as
  `omp-completeness-grok-4.5-high`. In the OMP-only `--prepare` branch,
  `:3161-3177` rejects any supplied identity other than that constant and
  assigns the packet reviewer from the constant rather than from user input.
  The pending ledger record and required envelope both use that assigned value
  at `:3178-3218`. Thus omission of `--reviewer-identity` and an explicitly
  matching value produce the same fixed identity.

- **Mismatch fails before pending-state mutation:** The mismatch validation at
  `skills/delivery-run/scripts/delivery:3164-3176` occurs before construction
  of `pending` and before the only pending/evidence/history/ledger writes in
  this branch at `:3180-3203`. A different `--reviewer-identity` therefore
  exits without replacing an existing pending request or creating a new one.

- **Envelope acceptance remains bound and unchanged:**
  `skills/delivery-run/scripts/delivery:3134-3158` continues to require the
  exact seven-line ASCII/LF envelope, its existing field grammar, and one
  occurrence of every field. Acceptance at `:3223-3246` still compares the
  response ID, reviewer identity, plan SHA-256, worktree fingerprint, and
  `COMPLETE` verdict to the pending request. The correction changes the source
  of the pending identity, not the envelope parser or acceptance comparison.

- **Direct OMP instructions route the request correctly while preserving
  ownership:** `agent_start_prompt` at
  `skills/delivery-run/scripts/delivery:3902-3913` says to remain in the same
  OMP session, never hand implementation to another agent, and send the packet
  to `@completeness` on `xai/grok-4.5:high` with the fixed identity. The
  generated OMP agent brief at `:4556-4589` repeats the fixed prepare command
  and the same `@completeness`/`xai/grok-4.5:high` route, while its ownership
  contract at `:4567-4571` retains same-session normal OMP implementation and
  prohibits Pi/handoff.

- **Focused regression coverage:**
  `skills/delivery-run/tests/test_delivery_cli.sh:1943-1985` prepares an OMP
  packet with no identity override and asserts its fixed reviewer identity,
  then invokes `--prepare --reviewer-identity reviewer.one`, requires failure
  mentioning the fixed identity, and prepares a subsequent fresh packet.
  Existing OMP same-owner regression coverage at `:725-769` asserts the OMP
  agent kind and same-session/no-Pi handoff prompt contract. The acceptance
  exercise at `:1945-2005` and `:2068-2084` continues to generate and accept
  the required envelope.

No material in-scope finding remains from the prior P2.

Not examined: runtime behavior of the external OMP dispatcher/model resolver;
a live host installation; broader delivery CLI behavior outside the named
routing, envelope, ownership, and focused-regression surfaces; and execution
of tests, linters, formatters, or project-wide commands (read-only rereview
constraint). The caller supplied post-fix focused verification results, which
were not independently rerun here.

VERDICT: PASS
