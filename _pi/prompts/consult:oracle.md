---
description: Ask the read-only GPT-5.6 Sol Oracle for bounded decision support
argument-hint: '<decision, tradeoff, plan concern, or review disagreement>'
---

# Consult Oracle

Use the repository-owned `oracle` subagent for this decision:

```text
$ARGUMENTS
```

Before launching it, inspect enough current evidence to give it a useful bounded packet. Include:

- the decision to make;
- established requirements, constraints, and inherited decisions;
- relevant files, errors, verification, or other evidence;
- credible options;
- the driving agent's current recommendation and uncertainty;
- one narrow question.

Launch `Agent` with `subagent_type: "oracle"` and a short 3–5 word description. Omit caller-side model, thinking, `inherit_context`, and `isolation` overrides because the checked-in Oracle frontmatter pins GPT-5.6 Sol high, inherited context, and the live checkout. The consultation is read-only and advisory; it must not edit files, implement changes, or authorize scope expansion.

After Oracle returns, verify its material factual claims against the current sources. The driving agent decides whether to accept, partially accept, reject, or escalate the recommendation and explains that disposition before acting. If the request is read-only, do not treat the consultation as implementation authority.
