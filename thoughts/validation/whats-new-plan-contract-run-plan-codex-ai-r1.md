# Run-plan implementation review — Codex ai-configs slice (cycle 1)

- Review ID: `whats-new-ai-codex-r1`
- Nonce: `3e3b86957c26287fac0abd68297e0358`
- Model: `gpt-5.6-terra`, high reasoning, read-only
- Comparison: `origin/main...cb78fc0`
- Fingerprint: unchanged before/after review
- Verdict: `FIX_IN_SCOPE_FINDINGS`

## Findings

1. **P2 / IN_PLAN** — `_hermes/default/skills/software-development/planning-workflow/SKILL.md` and the mirrored `writing-plans` guidance weaken the canonical content contract by omitting the headline, promise, before/after workflow, and observable result.
2. **P2 / IN_PLAN** — `_hermes/default/skills/software-development/reviewed-html-plan/SKILL.md` checks What’s new in PM review but omits it from the independent GPT reviewer’s required readiness concerns.
3. **P2 / IN_PLAN** — `test_install_shared_skills.sh` uses whole-file keyword checks for those Hermes surfaces, so it does not bind the required semantics to the canonical section or the reviewer concern list.

Required follow-up: strengthen the managed Hermes authoring/reviewer guidance without changing Hermes-specific mechanics, tighten section-scoped tests, refresh the manifest, rerun focused verification, then targeted rereview.
