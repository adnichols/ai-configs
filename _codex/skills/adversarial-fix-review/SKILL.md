---
name: adversarial-fix-review
description: "Independently assess a claimed fix from before/after evidence and actual code paths in Codex."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Independently verify a claimed fix

Before claiming a behavioral fix, obtain an independent bounded review of the necessity and proof. The driver supplies the original reproduction, pre-change evidence, candidate diff, relevant paths, and post-change verification. Do not present a ticket, self-written test, or implementation narrative as proof that a production state actually occurs.

Request a fresh native read-only reviewer under the runtime contract. Ordinary Codex review provides independence within available GPT models. If the task expressly requires another model family, report that requirement unavailable unless the user authorized a supported external route. Never claim cross-family coverage from a different GPT variant.

Ask the reviewer whether the bug existed on the relevant path without the change, whether this change addresses the mechanism, and whether the verification demonstrates the fix. Check that test setup does not construct a state rejected by production. Account for related repairs already shipped. The driver runs discriminating commands when additional executable evidence is needed; the reviewer inspects artifacts.

Return NECESSARY, UNNECESSARY, or NOT PROVEN with answers and evidence. Do not upgrade NOT PROVEN from conversation memory. Get missing evidence or narrow the claim. Do not publish a claim of a proven fix when evidence is missing. Honor explicit publication overrides with truthful limitations. Pure documentation or private renames without a behavior claim do not need this review. Count equivalent necessity review once rather than adding another pass under a new name.
