# Codex guidance

## External-agent model selection

This is a Codex-only instruction policy, not a runtime access control.

- Preserve the external agent's configured model and fallback policy. Quota
  exhaustion, rate limits, provider failures, and requests to continue
  autonomously do not authorize model overrides.

## Wrangler authentication

- Never run `wrangler login` on the operator's behalf, or use computer-use,
  browser automation, or another agent to authorize Wrangler for them.
- Before declaring Wrangler authentication blocked, try a login shell and
  other existing invocation paths, including the project's pinned Wrangler.
  Check credential-directory and environment differences without exposing
  secrets. Do not assume one invocation's authentication failure means the
  operator must log in again.
- If existing authorization still cannot be used, report the failed checks
  and tell the operator that their manual `wrangler login` is required. Stop
  the blocked action; do not start login, alter account scope, overwrite or
  delete credentials, or retry authorization automatically.

## Writing

- Do not substitute metaphor or flourish for a direct statement. Write "a
  parameter worth varying", not "a dial worth turning". Write "this still
  matters", not "this earns its keep". Those phrases display the writer. They
  make the reader work harder, and they drag in connotations you did not
  choose. When a literal phrase is available, use it.
