ADN_RUNTIME_MARKER:playbook-investigation:ecc249f1e306fc64ddf83c7bed16cacf7c2239db

### Investigation

**You own the answer. Plan, route, write.**

Investigation requests are read-only. They produce a cited explanation or a recommendation, not a code change.

<!-- source-step:investigation:1 -->
1. Route through the **how** skill. Route "are we sure?" questions through the **interrogate** skill. For motivation questions, also route through the **why** skill.
<!-- source-step:investigation:2 -->
2. Produce the `how`-shaped output (Overview / Key Concepts / How It Works / Where Things Live / Gotchas), or a recommendation with a tradeoffs table if the request is a decision between alternatives.
<!-- source-step:investigation:3 -->
3. Apply the **unslop** skill to the reply.

No PR, no babysit, no `architect` unless the investigation precedes a code change. If it does, hand back to the user and re-route to Bug fix or Feature.

<!-- source-step:investigation:4 -->
4. No PR. End cleanly.

**Reply:** the investigation output. For "are we sure?" answers, include your real judgment with reasons. Push back if the premise is wrong (see Autonomy).
