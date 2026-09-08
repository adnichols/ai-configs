---
name: interrogate
description: "Use for \"interrogate\", \"adversarial review\", \"multi-model review\", \"challenge this\", \"stress test this code\", \"find blind spots\", or \"tear this apart\". Multiple LLM reviewers challenge changes from independent angles."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Interrogate

Produce an independent adversarial verdict over a named diff or artifact. This skill does not apply fixes. Establish the user's intent, scope, comparison range, and verification evidence before review. Include dirty and untracked candidate files when relevant.

Request bounded read-only reviewers with the same raw intent and rubric from references/rubric.md and references/code-quality-review.md. Use the native reviewer and planner roles for complementary scrutiny when capacity and useful independent driver work permit. Two GPT roles provide independent evaluations, not cross-provider consensus. If the user requires different model families, obtain that explicitly authorized capability or report the requirement unavailable.

Each packet names allowed artifacts, authority, output format, evidence already collected, and stop condition. Do not give the implementer's narrative as proof. Reviewers return findings with locations, concrete triggers, effects, and evidence limitations.

Deduplicate findings and investigate disagreements. Classify each as act on, consider, noted, or dismissed, with rationale. Consensus is supporting evidence, not proof of correctness. A lone finding with a concrete reproduction can outweigh agreement. Report actual reviewers, coverage gaps, and the verdict. Do not restart review until unanimous; respect the task's bounded review budget.
