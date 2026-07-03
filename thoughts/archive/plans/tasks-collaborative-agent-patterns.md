# Collaborative Agent Patterns - Implementation Tasks

## Implementation Context

**Source**: Analysis of changes to `dev:1:create-spec.md` and `dev:2:gen-tasks.md`
**Goal**: Apply collaborative agent philosophy to remaining commands

### Key Patterns Being Applied

1. **Agent Judgment & Course Corrections** - Role is collaborator, not stenographer
2. **Proactive User Engagement** - Multiple question types (validation, trade-off, challenge, scope)
3. **Handling Issues Protocol** - Stop → Report → Ask pattern
4. **Parallel Research with Synthesis** - Task tool with subagent_type=Explore

### Implementation Boundaries

**Included**: 7 commands identified as needing updates
**Excluded**:
- `cmd:research.md` - Strict documentation focus is intentional (user decision)
- Utility commands (doc:fetch, cmd:commit-push, etc.) - No interpretation needed

## Relevant Files

- `claude/commands/dev:0:create-prd.md` - Add Collaborative Refinement section
- `claude/commands/simplify:1:create-plan.md` - Add Parallel Research + User Engagement
- `claude/commands/cmd:debug.md` - Add trade-off questions for hypotheses
- `claude/commands/cmd:graduate.md` - Enhanced divergence resolution
- `claude/commands/dev:3:process-tasks.md` - Strengthen proactive flagging
- `claude/commands/dev:4:validate.md` - Add engagement for concerning patterns
- `claude/commands/simplify:2:process-plan.md` - Add handling issues protocol

## Implementation Phases

### Phase 1: HIGH Priority Commands

- [x] 1.0 Update `dev:0:create-prd.md`
  - [x] 1.1 Add "Collaborative Refinement" section after "Clarifying Questions for Scope Definition"
  - [x] 1.2 Add "When to Challenge Requirements" subsection (conflicts, technical issues, scope mismatch, missing considerations)
  - [x] 1.3 Add "How to Challenge" subsection with AskUserQuestion patterns
  - [x] 1.4 Add key principle: "Fidelity to user intent ≠ blindly transcribing problematic requirements"
  - [x] 1.5 Add challenge question types to AskUserQuestion examples

- [x] 2.0 Update `simplify:1:create-plan.md`
  - [x] 2.1 Add "Parallel Research Strategy" section using Task tool with Explore subagents
  - [x] 2.2 Define 3 parallel research tasks: Complexity Analysis, Dependency Analysis, Test Coverage Analysis
  - [x] 2.3 Add "User Engagement During Analysis" section
  - [x] 2.4 Add question types: discovery, trade-off, concern questions
  - [x] 2.5 Add "Handling Issues Protocol" for concerns found during analysis

### Phase 2: MEDIUM Priority Commands

- [x] 3.0 Update `cmd:debug.md`
  - [x] 3.1 Add user engagement section after synthesizing findings
  - [x] 3.2 Add trade-off questions when multiple root cause hypotheses exist
  - [x] 3.3 Add proactive hypothesis engagement before deep-diving

- [x] 4.0 Update `cmd:graduate.md`
  - [x] 4.1 Enhance divergence resolution with collaborative options
  - [x] 4.2 Add challenge questions when spec-vs-implementation conflicts are significant
  - [x] 4.3 Expand AskUserQuestion usage for low-confidence decisions

- [x] 5.0 Update `dev:3:process-tasks.md`
  - [x] 5.1 Strengthen "Handling Discoveries" section with proactive flagging guidance
  - [x] 5.2 Add examples of when to surface concerns vs proceed autonomously
  - [x] 5.3 Add validation/trade-off question patterns for discovery handling

### Phase 3: LOW Priority Commands

- [x] 6.0 Update `dev:4:validate.md`
  - [x] 6.1 Add user engagement section for concerning validation patterns
  - [x] 6.2 Add AskUserQuestion when validation reveals unexpected issues
  - [x] 6.3 Add trade-off questions for ambiguous validation results

- [x] 7.0 Update `simplify:2:process-plan.md`
  - [x] 7.1 Add "Handling Issues During Execution" protocol
  - [x] 7.2 Add stop/report/ask pattern for discoveries during simplification
  - [x] 7.3 Add user engagement for unexpected complexity or risks found

## Detailed Implementation Guidance

### For `dev:0:create-prd.md`

Add this section after "Clarifying Questions for Scope Definition":

```markdown
## Collaborative Refinement

While user requirements are the primary source, the agent should proactively flag concerns during requirement gathering.

### When to Challenge Requirements

Challenge (with AskUserQuestion) when:
- **Stated requirements conflict with each other**
- **Requirements would cause technical issues** based on domain knowledge
- **Scope seems mismatched with stated problem** (too broad or too narrow)
- **Missing considerations** that are typically critical (security, performance, edge cases)
- **Requirements seem to describe symptoms rather than root problems**

### How to Challenge

1. Document the concern clearly
2. Explain potential impact
3. Present alternatives with trade-offs
4. Use AskUserQuestion to get user's decision
5. Proceed with user's chosen direction

Example challenge question:
```
Question: "You mentioned [X] and [Y], but these may conflict. Which should take priority?"
Header: "Conflict"
Options:
- Prioritize [X] (impact: [describe])
- Prioritize [Y] (impact: [describe])
- Let me explain both in more detail
```

### Key Principle

**Fidelity to user intent ≠ blindly transcribing potentially problematic requirements.**

The goal is to capture what the user truly needs, which may require dialogue to uncover.
```

### For `simplify:1:create-plan.md`

Add this section after "Pre-Simplification Requirements":

```markdown
## Parallel Research Strategy

Use Task tool to spawn parallel research subagents for efficient codebase exploration. This accelerates analysis while preserving orchestrator context for synthesis.

### Subagent Delegation

Spawn parallel Task agents with `subagent_type=Explore`:

Task 1: Complexity Analysis
- Find code patterns indicating complexity accumulation
- Locate deprecated or unused code with git history evidence
- Document dead code evidence
- Identify consolidation opportunities

Task 2: Dependency Analysis
- Map all external dependencies on target code
- Identify integration points and API contracts
- Document concurrent behavior requirements
- Find all callers of functions/methods being simplified

Task 3: Test Coverage Analysis
- Find existing test coverage for target area
- Identify gaps in test coverage for core functionality
- Locate performance benchmarks
- Document test patterns used in this codebase

### Orchestrator Responsibilities

The parent agent (you) handles:
- Initial scope analysis and question formulation
- Synthesizing findings from all subagents
- Generating the simplification plan
- User communication and clarifications

Wait for ALL subagents to complete before synthesizing findings.

## User Engagement During Analysis

Use the **AskUserQuestion tool** proactively when discoveries warrant user input.

### Discovery Questions (surface findings)
```
Question: "My analysis found [X] in the target code. Should I include this in the simplification plan?"
Header: "Include"
Options:
- Yes, include in plan
- No, leave it as-is
- Let me explain what I found first
```

### Trade-off Questions (present options)
```
Question: "I found two approaches to simplify [area]. Which aligns better with your priorities?"
Header: "Approach"
Options:
- Approach A: [description with trade-offs]
- Approach B: [description with trade-offs]
- Need more details before deciding
```

### Concern Questions (flag risks)
```
Question: "This simplification would affect [Y]. The change is [low/medium/high] risk. Are you comfortable with this scope?"
Header: "Risk"
Options:
- Yes, proceed with full scope
- Reduce scope to lower risk
- Let's discuss the risks first
```

## Handling Issues Protocol

When analysis reveals problems that affect plan viability:

1. **Stop** - Do not finalize plan based on incomplete analysis
2. **Report** - Explain what you discovered and its impact
3. **Ask** - Present options and get user guidance before continuing

Examples requiring this protocol:
- Test coverage is insufficient to safely simplify (< 60%)
- Target code has undocumented external dependencies
- Simplification would require breaking API changes
- Analysis reveals the "complexity" serves an undocumented purpose
```

### For other commands

Apply similar patterns scaled to each command's purpose:
- `cmd:debug.md`: Add hypothesis trade-off questions
- `cmd:graduate.md`: Enhance divergence handling with collaborative resolution
- `dev:3:process-tasks.md`: Strengthen when to stop and ask vs proceed
- `dev:4:validate.md`: Add engagement for concerning patterns
- `simplify:2:process-plan.md`: Add discovery handling during execution

## Validation Checklist

- [x] Each command update preserves existing functionality
- [x] "Think harder" directive preserved where it exists
- [x] AskUserQuestion patterns are natural, not forced
- [x] User engagement adds value (not bureaucratic gates)
- [x] Commands work well together as a workflow

## Completion Criteria

- [x] All 7 commands updated with collaborative patterns
- [x] Patterns are consistent across commands (same philosophy)
- [x] Changes tested by reviewing the updated commands
