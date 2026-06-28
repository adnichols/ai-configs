---
description: Run blocker-focused multi-model plan review using GPT, Kimi K2.5, and Opus 4.8 Extra High
argument-hint: '<existing-plan-path | plan slug | legacy: <spec> <tasks> | legacy: <directory containing spec.md and tasks.md>'
---

# Multi-Model Plan Review Process

This command orchestrates a blocker-focused plan review using three independent reviewers running in parallel, followed by a final synthesis review.

Documents to review: $ARGUMENTS

## Execution Mode

- Run three parallel reviews by delegating to the Task tool with three separate subagents.
- Each subagent runs independently without seeing the others' work.
- After all three complete, run a final synthesis review using GPT on high reasoning.
- Review against the plan's stated goal, non-goals, original requested scope, source requirements, and validated repo evidence.
- Add comments only for blockers, materially risky gaps, or missing decisions required to execute that stated scope.
- Suppress nice-to-haves, opportunistic cleanup, adjacent surfaces not required by the source scope, and extra explicitness that would not change execution readiness.
- Do not perform any reviews directly in the primary agent.

## Phase 1: Parallel Review (3 Subagents)

Launch three independent reviews simultaneously:

### Subagent 1: GPT Review
- **Agent:** `reviewer-plan-gpt5.5`
- **Model:** `openai-codex/gpt-5.5`
- **Reasoning:** High
- **Task:** Perform blocker/materiality plan review per reviewer-plan-gpt5.5 instructions
- **Output:** Plan file with `[REVIEW:GPT]` comments + summary

### Subagent 2: Kimi K2.5 Review
- **Agent:** `reviewer-plan-kimi`
- **Model:** `opencode-zen/kimi-k2.5`
- **Reasoning:** High
- **Task:** Perform blocker/materiality plan review per reviewer-plan-kimi instructions
- **Output:** Plan file with `[REVIEW:Kimi K2.5]` comments + summary

### Subagent 3: Opus 4.8 Extra High Review
- **Agent:** `reviewer-plan-opus`
- **Model:** `opencode-zen/claude-opus-4-8`
- **Reasoning:** Extra High
- **Task:** Perform blocker/materiality plan review per reviewer-plan-opus instructions
- **Output:** Plan file with `[REVIEW:Opus 4.8]` comments + summary

### Parallel Execution

Launch three independent Task calls to run reviews in parallel:

**Task 1: GPT Reviewer**
```
Task(
  subagent_type="reviewer-plan-gpt5.5",
  description="Review plan with GPT",
  prompt="Review the plan at $ARGUMENTS. Follow your reviewer-plan-gpt5.5 instructions exactly. Add [REVIEW:GPT] comments only for blockers, materially risky gaps, or missing decisions required to execute the stated goal within the validated source scope, then provide a readiness summary."
)
```

**Task 2: Kimi K2.5 Reviewer**
```
Task(
  subagent_type="reviewer-plan-kimi",
  description="Review plan with Kimi K2.5",
  prompt="Review the plan at $ARGUMENTS. Follow your reviewer-plan-kimi instructions exactly. Add [REVIEW:Kimi K2.5] comments only for blockers, materially risky gaps, or missing decisions required to execute the stated goal within the validated source scope, then provide a readiness summary."
)
```

**Task 3: Opus 4.8 Reviewer**
```
Task(
  subagent_type="reviewer-plan-opus",
  description="Review plan with Opus 4.8",
  prompt="Review the plan at $ARGUMENTS. Follow your reviewer-plan-opus instructions exactly. Add [REVIEW:Opus 4.8] comments only for blockers, materially risky gaps, or missing decisions required to execute the stated goal within the validated source scope, then provide a readiness summary."
)
```

Use the Task tool to launch all three simultaneously. Wait for all three to complete before proceeding.

## Phase 2: Synthesis Review (Final)

After receiving all three review outputs:

### Final Reviewer: GPT Synthesis
- **Model:** `openai-codex/gpt-5.5`
- **Reasoning:** High
- **Task:** 
  1. Read the original plan
  2. Review all comments from GPT, Kimi K2.5, and Opus 4.8
  3. Identify conflicts or agreements between reviewers
  4. Add synthesis comments using `[REVIEW:Synthesis]` format only where they clarify material blockers, materially risky disagreements, or missing decisions that affect readiness
  5. Provide final consolidated summary

The synthesis should:
- Highlight areas where all reviewers agree on a material blocker or readiness risk
- Flag material areas where reviewers disagree (requires human judgment)
- Identify any materially important gaps that only one reviewer caught
- Provide a final recommendation considering all perspectives

### Synthesis Execution

Launch the synthesis review using:

```
Task(
  subagent_type="reviewer-plan-gpt5.5",
  description="Synthesize all plan reviews",
  prompt="Read the plan at $ARGUMENTS which now contains review comments from GPT, Kimi K2.5, and Opus 4.8. Perform a synthesis review following the instructions above. Add [REVIEW:Synthesis] comments only where they clarify material blockers, materially risky disagreements, or missing decisions that affect readiness within the stated scope, then provide a final consolidated summary."
)
```
## Review Integration Output

All four sets of comments (GPT, Kimi K2.5, Opus 4.8, and Synthesis) will be present in the plan file before integration. Only material findings may change the required plan scope during Phase 3.

## Summary Format

After completing all reviews, provide:

```
## Multi-Model Review Complete

### Reviewers:
- ✅ GPT (openai-codex/gpt-5.5, high reasoning)
- ✅ Kimi K2.5 (opencode-zen/hf:moonshotai/Kimi-K2.5, high reasoning)
- ✅ Opus 4.8 (opencode-zen/claude-opus-4-8, extra high reasoning)
- ✅ Synthesis (openai-codex/gpt-5.5, high reasoning)

### Consensus Blockers:
[List blocker-level or materially risky issues multiple reviewers flagged]

### Divergent Material Risks:
[List material issues where reviewers disagreed]

### Unique Material Risks:
[List blocker-level or materially risky issues caught by only one reviewer]

### Final Recommendation:
[Major revision needed / Proceed with caution / Ready to execute]
```

## Scope (Review Phases 1-2 Only)

Phases 1 and 2 are review-only.

- Subagents only modify the plan by inserting inline `[REVIEW:...] ... [/REVIEW]` comments.
- Those comments must be limited to blockers, material readiness risks, or missing decisions required for the plan's stated scope.
- Do not change any other plan content during review phases.
- Phase 3 performs automatic integration (see below).

### Phase 3: Automatic Integration

Phase 3 is NOT review-only. It:

- Reads all review comments from Phases 1-2
- Applies only material edits directly to the plan
- Removes resolved inline review comments
- Updates all relevant plan sections
- Validates the final plan structure

The output of this command is a clean, integrated plan ready for execution.

## Phase 3: Auto-Integration

After synthesis is complete, automatically integrate all review comments into the plan.

### Core Rule

The plan is the authority. Integrate only material feedback into the plan while preserving progress state.

### Materiality Filter

Treat review comments as required only when they identify a blocker, material risk, incorrect assumption, or missing decision/work needed to execute the plan's stated goal, non-goals, acceptance criteria, source requirements, or validated repo evidence.

- Do not expand required scope to satisfy optional comments, opportunistic cleanup, adjacent surfaces, or extra detail that would not change readiness.
- If optional feedback is worth retaining, preserve it as concise non-goal or deferred follow-up context instead of turning it into required plan work.

### Integration Process

#### 3.0) Read Plan and Extract Comments
- Read the plan file with all review comments
- Extract all inline review tags: `[REVIEW:GPT]`, `[REVIEW:Kimi K2.5]`, `[REVIEW:Opus 4.8]`, `[REVIEW:Synthesis]`
- If no review comments exist, integration is already complete

#### 3.1) Explore Codebase for Context
For any feedback that depends on feasibility or existing patterns, explore the codebase to resolve it.
Use the Task tool with `subagent_type=Explore`.

#### 3.2) Apply Integration Edits
Apply edits directly to the plan based on classified review feedback:

- Classify each review comment as material or optional before editing the plan
- Remove each resolved inline review comment after addressing it
- Integrate only material findings that affect readiness for the stated scope
- If material feedback implies adding or changing requirements, update:
  - Locked Decisions
  - Goal/Non-goals / Acceptance Criteria
  - `## Progress` if phase structure changes
  - The impacted phase(s) `### End State` / `### Work` / `### Verify`
  - `### Tests first` sections so they still describe the intended user-visible behavior
  - `Resume Instructions (Agent)` if needed
- For optional or nice-to-have comments, remove the inline comment without expanding required scope. If preserving the note helps later work, record it as concise non-goal or deferred follow-up context instead of required work.
- If review feedback establishes that a dependency/library evaluation checkpoint was missing or under-specified, preserve or add that decision explicitly in the cleaned plan only when the missing decision materially affects readiness for the stated scope.
- If a review comment shows that custom implementation was proposed without adequate library research, integrate the requirement to evaluate official SDKs / well-maintained libraries only when that omission is a material blocker for the scoped plan.
- Append a new entry to `## Plan Changelog` describing what changed due to review integration.

#### 3.3) Resolve Open Questions
- Resolve every important question that materially affects readiness for the stated scope before considering integration complete
- If the codebase, existing specs, product-intent docs, or plan context answer a question with high confidence, answer it directly in the plan
- If a question cannot be answered with high confidence, ask the user with the `question` tool
- Incorporate the user's answer into the plan and re-check the whole document for any downstream phase updates needed
- Do not leave an `Open Questions` section or any unresolved-decision placeholder in the final plan when it would materially affect readiness for the stated scope
- Do not preserve optional idea backlog as unresolved required work
- If review established that non-trivial build-vs-buy work needs a dependency/library evaluation checkpoint, the final plan is not complete until that decision is documented when it materially affects the scoped plan

#### 3.4) Final Validation
- No `[REVIEW:...]` comments remain in the plan
- `## Progress` still corresponds to the phase headers
- Each acceptance criterion has at least one verification step
- Each phase has `### End State`, `### Tests first`, `### Work`, and `### Verify`
- The plan has `Resume Instructions (Agent)` and `## Decisions / Deviations Log`
- Required dependency/library evaluation decisions established during review remain present in the final clean plan
- The plan does not leave unresolved `Open Questions`, `Decision Points`, or equivalent unresolved-decision sections that materially affect readiness for the stated scope
- Optional feedback was not converted into new required scope

#### 3.5) Integration Summary
After integration completes, provide:

```
## Integration Complete

### Changes Made:
- [List of changes made based on review feedback]

### Review Comments Addressed:
- ✅ GPT comments integrated
- ✅ Kimi K2.5 comments integrated
- ✅ Opus 4.8 comments integrated
- ✅ Synthesis comments integrated

### Open Questions Resolved:
- [List any questions answered during integration]

### Final State:
- Plan is clean with no review comments
- All required sections present and valid
- Plan changelog updated

### Next Step:
```
`/cmd:execute-plan <plan path | plan slug>`
```
```

---

## Updated Scope (Review + Integration)

This command now performs both review AND integration:

- Phase 1-2: Review-only (subagents insert `[REVIEW:...]` comments for blockers/material risks only)
- Phase 3: Integration (apply only material feedback and remove all review comments)
- The final output is a clean, updated plan ready for execution

## Execution Flow Summary

```
Input Plan
    ↓
Phase 1: Parallel Reviews (3 subagents)
  ├─ GPT Review → [REVIEW:GPT] comments
  ├─ Kimi K2.5 Review → [REVIEW:Kimi K2.5] comments
  └─ Opus 4.8 Review → [REVIEW:Opus 4.8] comments
    ↓
Phase 2: Synthesis (GPT)
  └─ Consolidates material feedback → [REVIEW:Synthesis] comments
    ↓
Phase 3: Auto-Integration
  └─ Applies only material feedback → Clean updated plan
    ↓
Output: Integrated Plan (ready for /cmd:execute-plan, /run-plan, or direct /dev:run)
```
---

## Oh My Pi Integration Instructions

### For ALL Plan Reviews in Oh My Pi:

**This `/review:plan` command MUST be used as the standard review process for ALL plans.**

Whenever a plan is created or updated and needs review:

1. **Primary agent MUST delegate to this command** instead of performing direct review
2. **Always use the full multi-model review** - do not skip reviewers or use single-reviewer shortcuts
3. **Wait for parallel completion** - all 3 reviewers + synthesis must complete
4. **Respect the materiality boundary** - reviewers and synthesis judge readiness within the plan's stated goal, non-goals, source requirements, and validated repo evidence
5. **During integration, change required scope only for material findings** - optional comments must be dropped or preserved as deferred/non-goal context rather than converted into plan requirements

### Process Flow:

```
User: "Review this plan"
Agent: Delegate to /review:plan <plan-path>
  → Task launches 3 parallel reviewers
  → Each adds [REVIEW:Name] comments
  → Synthesis reviewer consolidates all feedback
  → Returns blocker-focused multi-model assessment
```

### Benefits:

- **Multiple perspectives:** Three different model architectures catch different issue types
- **High reasoning mode:** All reviewers use maximum reasoning effort
- **Parallel efficiency:** Reviews run simultaneously for faster turnaround
- **Synthesis quality:** Final GPT review consolidates all perspectives
- **Consistency:** Standardized review format and process across all plans

### Do NOT:

- Run single-reviewer reviews for plans
- Skip the synthesis phase
- Use lower reasoning settings to save time
- Manually review plans without delegating to this command
