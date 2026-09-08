---
name: why
description: "Use for 'why does X work this way', 'why we picked Y', design rationale, regressions, postmortems, or data-backed thresholds. Discovers available MCPs and queries each evidence category (source control, issue tracker, long-form docs, real-time chat, infrastructure observability, error tracking, product analytics warehouse) in parallel, then returns a cited read on decisions and tradeoffs. Use how for runtime behavior."
---

Read [the Codex runtime contract](../adn-mode/references/codex-runtime.md) before executing this skill.

# Why

Investigate the motivation for the current design. First understand what the system does through `how`, then trace the decision in commit history, blame, PR discussions, scoped issues, and relevant available documents. Separate an author's recorded rationale from an inference based on current code.

Use native tool discovery and available connectors rather than a client's MCP directory. Read `references/` only for the source-specific investigation being performed. Use installed `linear`, `agent-slack`, or document skills when the relevant source requires them. Read access does not authorize sending a message or posting a comment.

Independent sources may be examined by bounded read-only scouts. Name the question, allowed sources, required citations, and stopping condition. Keep narrow questions local. Synthesize in the driver, verify contradictions, and treat empty searches as missing evidence rather than proof that no rationale existed.

Return the actual rationale, constraints and tradeoffs, historical changes, supporting sources, and remaining uncertainty. Do not propose changing the design unless asked or necessary to answer the question.
