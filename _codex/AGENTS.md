# Codex guidance

## External-agent model restrictions

This is a Codex-only instruction policy, not a runtime access control.

- Restricted models: Astra, Fable, Kimi K3. This includes their provider IDs,
  aliases, and reasoning variants.
- When launching, resuming, supervising, or controlling an agent outside
  Codex, do not select a restricted model as its working model. This covers
  CLI arguments, interactive model pickers and shortcuts, configuration
  edits, role assignments, fallback changes, and instructions delegated to
  another agent or coordinator.
- Preserve the external agent's configured model and fallback policy. Quota
  exhaustion, rate limits, provider failures, and requests to continue
  autonomously do not authorize model overrides. A suggestion such as "use a
  high-reasoning model like Astra" is not permission to waive this restriction.
- If an external worker starts on a restricted model, do not send it
  implementation work. Report the mismatch instead of changing shared
  defaults. Do not restart it on a restricted model to bypass this rule.
- Astra is permitted only for a designated Oracle consultation, not for an
  implementation worker or general-purpose driving session. Do not relabel
  ordinary work as an Oracle consultation to obtain this exception. It never
  permits changing defaults, shared configuration, or fallback chains.
- Any other exception requires the operator to explicitly waive this
  restriction in the current conversation, naming the model and intended use.
  This rule does not change the model of the Codex session itself.

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
