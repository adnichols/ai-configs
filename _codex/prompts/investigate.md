---
description: Run the deterministic evidence-closed investigation workflow
argument-hint: "<question>"
---
Run the evidence-closed investigation workflow now for this question:

$@

Do not investigate manually with ad-hoc unconstrained browsing. Follow the
evidence-closed protocol:

1. Bounded landscape-discovery pass over the local repo and relevant web
   sources for the question, then a high-reasoning readiness review of the
   discovered surface before deciding the investigation scope.
2. Do not assume the current working directory is the entire scope.
3. If the protocol needs clarification, ask every returned question together
   and wait for one reply before continuing. Do not answer the original
   question until those answers are available.
4. Close the investigation with concrete evidence (file:line, command output,
   or source citations) and state exactly what was ruled out and why.

If no question was supplied, ask the user for one instead of starting.
