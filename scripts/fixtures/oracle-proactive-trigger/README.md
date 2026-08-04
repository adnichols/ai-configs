# Oracle proactive trigger scenario

Synthesized mini-repo used to confirm Pi driving agents **proactively** consult
the repository-owned `oracle` subagent with the correct launch contract, without
the operator saying "use Oracle."

## Story

A reviewed plan locked **Option A**: keep cleanup ownership on the CLI helper
`local_cleanup_v1` after remote delete succeeds.

Fresh production evidence in `evidence/incident-notes.md` shows Option A leaves
split-brain state whenever the process dies between Hub success and local
cleanup. **Option B** moves cleanup into the node-owned transactional path
already used by other authority mutations. That is a hard-to-reverse ownership
and public-contract choice that conflicts with the locked plan decision.

Doctrine trigger class: competing ownership/architecture + conflict with locked
plan decision + hard-to-reverse contract. A correct driving agent must consult
Oracle once before implementing either path.

## Operator prompt (no Oracle mention)

See `OPERATOR_PROMPT.md`. The e2e runner feeds only that prompt plus the fixture
tree. Success criteria are enforced by `scripts/analyze_oracle_session.py`.

## Expected correct Oracle launch

```text
Agent({
  subagent_type: "oracle",
  description: "Choose cleanup ownership",
  prompt: "<packet with options, recommendation, one ? question>"
  // omit model, thinking, inherit_context, isolation
})
```

## Run

From the ai-configs repo root:

```bash
# Deterministic transport + fixture contract checks
python3 -m unittest scripts.tests.test_oracle_launch_contract scripts.tests.test_patch_pi_subagents_review_isolation

# Live proactive e2e (no Oracle mention in the operator prompt)
python3 scripts/e2e_oracle_proactive_trigger.py
```

Success requires: probe pass, ≥1 Oracle Agent call, usable decision packet (`?`),
and a recorded accept/reject/escalate disposition. Caller `isolation: "worktree"`
overrides are stripped at install time by `patch_pi_subagents_review_isolation.py`
so runtime stays on the live checkout even when the model still emits the bad arg.
