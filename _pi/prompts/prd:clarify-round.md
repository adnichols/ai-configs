---
description: Analyze the current PRD round with a clarification-gap reviewer and optional bounded scout evidence before asking the next question
argument-hint: '<prd path | prd slug>'
---

# PRD Clarification Round

Run the clarification support loop for the current PRD delta.

Documents to inspect: $ARGUMENTS

## Contract

This command is for the iterative clarification loop, not the final five-reviewer gate.

Use it after each meaningful batch of new user answers:
- update the PRD with the new answers first,
- then rerun this clarification command,
- then decide whether more clarification is needed or whether `/review:prd` is now worthwhile.

Required order per round:
1. Run the clarification-gap reviewer first on the updated PRD.
2. Only run the scout if the clarification-gap reviewer identifies a decision-relevant gap that needs external defaults, prior art, or precedent.
3. After those support passes, ask the prioritized clarification questions directly whenever more clarification is still needed, or explicitly say no further clarification questions are currently needed.

Do not run `/review:prd` from this command.
Do not launch any of the five final PRD reviewer passes from this command.

## Phase 0: Resolve Inputs

- If `$ARGUMENTS` starts with `@`, strip the leading `@` and treat it as workspace-relative.
- If a single argument is an existing `.md` file, treat it as `prd_path`.
- If a single argument is a slug, resolve to `thoughts/plans/prd-<slug>.md`.
- If the PRD file does not exist, ask for an explicit PRD path.

## Phase 1: Read the Current PRD and Baseline

Read the PRD fully.
Also read any selected functional spec paths named in the PRD.
If `thoughts/specs/product_intent.md` exists and is relevant, read it too.

## Phase 2: Clarification-Gap Reviewer Pass (Always)

Launch the clarification-gap reviewer first.

```javascript
const critic = Agent({
  subagent_type: "reviewer",
  description: "Analyze PRD clarification gaps",
  prompt: "Analyze the current PRD round for $ARGUMENTS. Read the PRD and its selected baseline specs. Use the clarification-gap lens. Preserve the caller-supplied PRD/baseline artifact authority and return blockers, missing baseline facts, prioritized clarification questions with suggested options, a recommended option plus why for each question, and whether clarification is still needed.",
  run_in_background: true,
});

const criticResult = await get_subagent_result({ agent_id: critic.agent_id ?? critic.id, wait: true });
```

## Phase 3: Research Pass (Conditional)

Run the scout only if the clarification-gap reviewer shows that research would change a concrete decision.
Examples:
- missing precedent or prior art,
- missing default behavior guidance,
- uncertainty about a recommended pattern,
- a decision that cannot be grounded from repo-local evidence alone.

If the clarification-gap reviewer only found local contradictions, missing flows, or missing user intent, skip research.

Conditional launch:

```javascript
const research = Agent({
  subagent_type: "scout",
  description: "Research PRD decision gaps",
  prompt: "Research only the decision-relevant gaps identified for $ARGUMENTS. Keep the brief concise and tied to active decisions, with findings, authoritative sources, and a recommendation.",
  run_in_background: true,
});

const researchResult = await get_subagent_result({ agent_id: research.agent_id ?? research.id, wait: true });
```

## Phase 4: Next-Step Decision

Using the PRD plus the support-agent outputs:

- Treat the clarification-gap reviewer's `## Clarification questions` section as the default source for the next user questions.
- If the PRD still has unresolved contradictions, missing required behavior, or unclear intent, ask those questions directly in the conversation.
- Preserve the critic's priority order. Ask all material questions for the round unless the user's answers make later questions obsolete.
- For each question, include every viable option supported by current evidence and a thorough explanation of each option's resulting behavior, benefits, costs/risks, implementation and compatibility implications, and reversibility.
- Make the critic's recommendation explicit, including why it is preferred, confidence level, and supporting evidence. Allow the user to provide a custom answer when the listed options do not fit.
- If the critic recommends a choice that is not already one of the listed options, revise the option list so the recommended choice is present before asking the user.
- Keep the question set high-signal; do not pad it just to reach 10.
- If the PRD is internally coherent and no further clarification is currently needed, say that explicitly.
- After the user answers, fold those answers into the PRD and start another clarification round from the clarification-gap reviewer.
- If wider review is now worthwhile, say that `/review:prd <prd-path>` is available, but do not run it automatically.

## Output Format

```markdown
## Clarification Round Complete

### Clarification-Gap Reviewer
- [Key blocker or confirmation]

### Scout Evidence
- [Finding] or `Skipped — not needed for this round`

### Next Step
- `Asked the prioritized clarification set directly.`
- or `No further clarification questions are currently needed.`

### Review Gate
- `Do not run yet.`
- or `A wider /review:prd pass is now worthwhile.`
```
