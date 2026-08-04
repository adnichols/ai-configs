# Fixture repo guidance

This is a synthetic checkout for Oracle proactive-trigger validation.

## Pi subagents

Use the host Pi roster. In particular:

- `oracle` — GPT-5.6 Sol high, inherited context, live checkout. Proactively
  consult once when targeted inspection leaves competing architecture/ownership
  options, a hard-to-reverse contract choice, or conflict with a locked plan
  decision. Launch with only `subagent_type: "oracle"`, a short description, and
  the decision packet. Omit caller-side `model`, `thinking`, `inherit_context`,
  and `isolation`. Packet must include options, your current recommendation and
  uncertainty, and one narrow question ending with `?`. Record disposition
  before acting.
- `scout` — bounded read-only discovery only.
- `planner` / `reviewer` — not required for this fixture stop condition.

Development stays in the driving session. Do not implement through a subagent.
