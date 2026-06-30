---
name: agent-memory-skill-hygiene
description: Audit Hermes memory and skills after corrections, workflow discoveries, or periodic maintenance. Use session recall plus live verification to keep durable memory compact and skills accurate.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [memory, skills, maintenance, hermes, hygiene]
---

# Agent memory + skill hygiene

Use this when:
- the user asks to review/refine memory
- several sessions contained corrections or workflow discoveries
- a skill may now be stale relative to live CLI behavior or current docs
- memory is nearing capacity and needs compression

## Goals
1. Keep durable memory compact, high-value, and current.
2. Patch or create skills when a reusable workflow or command quirk is confirmed.
3. Avoid saving temporary task state, noisy session summaries, or facts easy to rediscover.

## Audit flow

### 1. Recall recent corrections first
- Use `session_search` with broad OR queries such as:
  - `correction OR outdated OR wrong command OR failed`
  - `remember this OR skill update OR overreach`
- Look for:
  - user corrections that should become durable preferences
  - repeated command/API quirks worth skill updates
  - places where an existing skill caused drift or overreach

### 2. Inspect relevant skills before editing
- Load any potentially relevant skills with `skill_view`.
- Prefer patching an existing skill over creating a near-duplicate.
- If a skill is broad and security-scanned as dangerous, expect patch attempts to require confirmation; in that case, patch a narrower related skill or summarize the blocked change clearly.

### 3. Verify live behavior
Never trust stale recollection for command syntax or current behavior.
- Use `terminal` for CLI help/version checks.
- Use `web_search` / `web_extract` for current docs when the behavior depends on upstream releases.
- Only write skill guidance that was either:
  - confirmed live, or
  - clearly labeled as doc-derived.

### 4. Decide what belongs in memory
Good memory candidates:
- durable user preferences
- stable environment quirks
- recurring naming/identity conventions
- persistent workflow interpretations that prevent future correction

Do not save:
- completed work logs
- one-off task outcomes
- bulky session recaps
- facts that belong better in a skill than memory

### 5. Compress before adding
When memory is tight:
- replace verbose entries with shorter versions rather than adding duplicates
- merge closely related rules into one concise line
- remove obsolete facts after confirming they are no longer needed

### 6. Patch/create skills when reuse is likely
Update a skill when:
- a command changed
- fallback behavior was learned from failure
- a workflow needs a new guardrail
- a user correction revealed a style, sequence, or scope preference for that task class

Create a skill when:
- the procedure is reusable
- it took multiple steps or multiple tools to validate
- future sessions would benefit from a named playbook

Default posture: be active. Most substantive sessions should produce at least a small skill patch, support reference, or explicit memory compression. "Nothing to save" is valid only when there were no corrections, no workflow discoveries, no tool/API quirks, and no loaded skill gaps.

## Output checklist
Before finishing, report:
- what memory was added/replaced/removed
- which skills were patched/created
- anything you attempted but could not update (for example confirmation-gated skill edits)
- any recommended next cleanup items

## Heuristics
- Prefer one strong concise memory entry over several overlapping ones.
- Prefer targeted skill patches over broad rewrites.
- If a discovered lesson only matters in one channel/context, say so explicitly in memory/skill text.
- If the user corrects a path, canonical location, or source-of-truth assumption, patch the workflow skill that used the wrong assumption immediately. Treat this as both a memory candidate (if durable) and a skill/library candidate (because future executions need the corrected procedure).
