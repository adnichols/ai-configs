---
description: Research an idea and produce a specification document
argument-hint: "[Idea/Feature Description]"
---

# Rule: Research and Generate Specification Document

## Goal

To guide an AI assistant in researching a user's idea and creating a focused, practical specification document in Markdown format with YAML front-matter. This document will serve as input to downstream task generation commands. Think harder.

## Non-Negotiable Guardrails (Spec-Only)

You are in SPEC-ONLY mode.

Forbidden:
- Editing or creating product code files (anything outside `thoughts/specs/`)
- Running implementation steps (installs, builds, migrations, dev servers, refactors)
- Creating tasks/PRs/commits or moving toward implementation
- Making documentation changes in the repository (no writing under `docs/`, no updating `CLAUDE.md`)

Allowed:
- Read-only codebase inspection (search, read files, git history inspection)
- Asking clarifying questions
- Producing ONE output artifact: the spec document (or printing it in-chat if write is unavailable)

Stop condition:
- After producing the spec, STOP. Do not proceed to task generation or implementation.

## Research Approach

This command uses a standard research depth approach to create comprehensive specification documents that include:

1. **Core functionality analysis** based on research findings and feature characteristics
2. **Appropriate technical depth** matching the requirements
3. **Integration considerations** for existing codebase patterns
4. **Standard quality requirements** for production-ready features

## Input

Consider any input from $ARGUMENTS

The user will provide:

1. **Idea/Feature Description:** Initial concept or problem statement that needs research

## Instructions

The AI will need to:

1. Analyze the user's idea for completeness and scope
2. Conduct comprehensive research on the feature
3. Engage the user proactively throughout the process
4. Generate a complete specification document (which may differ from the initial request based on research findings)

## Agent Judgment & Course Corrections

You are expected to exercise judgment throughout this process. Your role is **collaborator**, not stenographer.

### Proactive Improvements

- If research reveals the user's initial approach has significant issues, **proactively suggest alternatives**
- If a better solution exists than what the user described, present it with rationale
- Don't just document a flawed idea faithfully—help the user build something better

### When to Deviate from the Original Request

- **Technical infeasibility**: Research shows the approach won't work as described
- **Better alternatives exist**: A different pattern/technology solves the problem more elegantly
- **Scope misalignment**: The stated scope doesn't match the actual problem being solved
- **Missing considerations**: Critical aspects (security, performance, UX) weren't mentioned but are essential
- **Contradictory evidence**: Codebase patterns or constraints conflict with the proposed approach

### How to Handle Deviations

1. Document your finding clearly
2. Explain why the original approach is problematic
3. Present alternatives with trade-offs
4. Use `question` to get user input on the direction
5. Proceed with the user's chosen direction (which may be original or modified)

**Key principle:** Fidelity to user intent ≠ fidelity to user's initial words. Users often benefit most when the agent pushes back thoughtfully.

## Process

1. **Initial Research:** Conduct preliminary research to understand the idea's scope and characteristics
2. **Codebase Research Protocol:** Perform comprehensive codebase research (read-only) to establish the baseline of what exists today (see Codebase Research Protocol section below)
3. **Traceability Metadata:** Capture git metadata (commit hash + branch) and include it in the spec front-matter
4. **Documentation Discovery (Read-Only):** Identify relevant documentation sources, but do not fetch/write/update docs during this command (see Documentation Discovery section below)
5. **Requirements Analysis:** Based on research findings:
   - Analyze impact scope and integration needs
   - Identify functional requirements
   - Assess technical constraints and decisions
   - Evaluate integration complexity
6. **Deep Research Phase:** Conduct comprehensive research covering:
   - Core functionality and integration patterns
   - Testing approaches and security considerations
   - Performance considerations and reliability features
   - Implementation planning and dependencies
7. **Generate Specification:** Create complete document with all necessary sections
8. **Save Specification:** Save as `spec-[idea-name].md` in `thoughts/specs/` directory
9. **End Command:** The command completes after saving the specification. Task generation and implementation are separate phases.

**IMPORTANT:** If you encounter write permission errors when saving to `thoughts/specs/`, you are likely in **plan mode** (read-only). STOP and ask the user:
- "I'm in plan mode and cannot write files. Would you like me to:"
  - "A) Present the specification here for review, then you can save it"
  - "B) Wait until we exit plan mode to save it"
  - "C) Save to a different location (please specify)"

**Throughout the process:**
- Challenge assumptions when evidence suggests they're incorrect
- Don't preserve the user's original framing if research shows it's misguided
- Present findings honestly, even if they contradict the initial request
- The goal is the best solution, not faithful reproduction of the original idea

## Codebase Research Protocol (Required)

This command incorporates the core codebase research approach from `/cmd:research`, but extends it with explicit option evaluation (spec work requires judgment).

Phase A - Baseline (Document-only)
- Document the codebase as it exists today: what exists, where it exists, and how components interact.
- Do not critique or propose changes during this phase.
- Avoid solutioning until a baseline snapshot is captured.

Phase B - Options & Recommendation (Evaluate)
- Identify multiple viable approaches grounded in the baseline.
- Compare trade-offs and recommend a direction.

### Step 1: Read Mentioned Files First

If the user mentions specific files or paths:
- Read them fully before spawning sub-tasks.

### Step 2: Analyze and Decompose

Break down the research question into:
- Components to investigate
- Patterns to find
- Connections to trace
- Directories and files to explore

Track this as a checklist (`todowrite`).

### Step 3: Parallel Research Strategy

Use the Task tool to spawn parallel research subagents for efficient codebase exploration. Spawn parallel Task agents with `subagent_type=explore`.

Each subagent must:
- Return specific `path/to/file.ts:line` references for each claim
- Clearly separate "confirmed in code" from "inferred"

Recommended task split:

```
Task: Find WHERE things live
- Search for file patterns
- Locate key modules and entry points

Task: Understand HOW it works today
- Read specific implementations
- Trace data flow and boundaries

Task: Find PATTERNS & PRECEDENTS
- Look for similar implementations
- Document conventions and shared utilities

Task: Production Readiness Patterns
- Find performance and observability patterns
- Identify testing patterns (unit/integration/e2e)
- Identify paired dependencies requiring version alignment (client/server, protocol pairs)
- Flag infrastructure that may need smoke testing before feature work
```

### Step 4: Synthesize Findings

Wait for ALL subagents to complete before synthesis.

The parent agent (you) handles:
- Initial scope analysis and question formulation
- Synthesizing baseline findings into the spec
- Option generation + trade-off evaluation
- User communication and clarifications

## Documentation Discovery (Read-Only; No Repo Changes)

This command must NOT fetch, write, or modify documentation in the repository.

Allowed:
- Inspect existing local docs (read-only)
- Link to official documentation URLs in the spec
- Include brief extracted notes in the spec itself

Forbidden:
- Writing anything under `docs/`
- Updating `CLAUDE.md`
- Running documentation commands that create/modify files

If documentation gaps are discovered:
- Record them explicitly in the specification under `## Implementation Plan` as `### Documentation Tasks (Post-Spec)` including:
  - What doc should be added/updated
  - Proposed location (path in repo)
  - Why it's needed
  - Who/when (later; not executed in create-spec)

## Research Areas

The research should comprehensively cover:

### Core Research (Always Include)

- Existing implementations and design patterns
- Framework and library recommendations (from current codebase)
- Integration with existing systems
- User journey and interface patterns
- Existing code patterns and conventions
- Available utilities and shared components

### Technical Research

- Data modeling requirements
- Security considerations (input validation, authentication, authorization)
- Testing approaches (unit, integration, e2e tests)
- Error handling patterns and edge cases
- Configuration and environment requirements

### Production Readiness Research

- Performance considerations and optimization opportunities
- Security best practices and compliance needs
- Reliability and resilience features
- Monitoring and observability requirements
- Deployment considerations and CI/CD integration
- Backward compatibility requirements (if applicable)

## User Engagement & Feedback

Use the `question` tool proactively throughout the research process. This creates a collaborative specification rather than a one-way documentation exercise.

### When to Engage the User

**Always engage when:**
- Your research reveals potential issues with the original approach
- Multiple valid implementation paths exist with different trade-offs
- You've discovered information that might change the user's priorities
- The scope could reasonably be interpreted multiple ways
- You want to validate your understanding before deep-diving

**Don't delay engagement** waiting for "critical" blockers. Early course corrections save significant effort.

### Types of Engagement

**Validation questions** (confirm understanding):
```
Question: "Based on my research, I understand the core goal is [X]. Is this accurate, or should I adjust focus?"
Header: "Validate"
Options:
- Yes, that's correct
- Partially correct, but [adjustment needed]
- No, the focus should be [different]
```

**Trade-off questions** (present options):
```
Question: "I found two viable approaches. Which aligns better with your priorities?"
Header: "Approach"
Options:
- Approach A: [benefits/drawbacks summary]
- Approach B: [benefits/drawbacks summary]
- Let me explain both in more detail
```

**Challenge questions** (surface concerns):
```
Question: "My research suggests [original assumption] may cause [issue]. Should I explore alternatives?"
Header: "Concern"
Options:
- Yes, explore alternatives
- No, proceed with original approach (I understand the trade-offs)
- Let's discuss the implications first
```

**Scope questions** (clarify boundaries):
```
Question: "This feature could range from [minimal] to [comprehensive]. What scope fits your needs?"
Header: "Scope"
Options:
- Minimal: [description]
- Standard: [description]
- Comprehensive: [description]
```

### Engagement Philosophy

The best specifications emerge from dialogue, not dictation. Your role is:
- **Collaborator**, not stenographer
- **Advisor** who surfaces issues, not just documenter who records requirements
- **Partner** in problem-solving, not passive executor

### `question` Tool Usage Notes

- Keep headers short (max 12 chars) - they appear as chips/tags
- Use `multiple: true` when choices aren't mutually exclusive
- Provide clear descriptions for each option
- A freeform "Type your own answer" option is added automatically; do not add an "Other" option
- Ask 1-4 questions at a time, grouped logically

## Specification Template

The specification document uses this comprehensive structure:

```markdown
---
date: [ISO timestamp]
author: [your name]
git_commit: [git rev-parse HEAD]
branch: [git branch --show-current]
repository: [repository name]
type: spec
status: draft
tags: [relevant, tags]
---

# [Idea Name] - Research Specification

## Executive Summary

[Problem, solution, value, and success criteria]

## Existing System Snapshot (From Codebase Research)

[What exists today, grounded in file references. Focus on current reality before solutioning.]

## Code References

- `path/to/file.ts:123` - Description
- `another/file.ts:45` - Description

## Core Research Findings

### Integration Points

[System integration considerations and existing code patterns]

### Constraints & Invariants

[Auth/RLS, data access patterns, environment constraints, conventions]

## Problem & Solution

### Core Problem

[Detailed problem analysis with context and background]

### Target Users

[User personas and detailed use cases]

### Success Criteria

[Measurable success indicators and acceptance criteria]

## Technical Design

## Alternatives Considered (Decision Matrix)

Include at least 2 viable approaches grounded in codebase findings.

| Option | Fit w/ patterns | Complexity | Security | Performance | Testing impact | Notes |
|-------:|------------------|------------|----------|-------------|----------------|------|
| A      |                  |            |          |             |                |      |
| B      |                  |            |          |             |                |      |

## Recommendation

[Chosen option + why + explicit non-goals + rejected alternatives]

## User Interface

### User Flow

[User journeys and interaction patterns]

### Interface Needs

[UI/UX requirements and design considerations]

## Testing Approach

### Test Strategy

[Unit, integration, e2e, performance as relevant]

### Quality Assurance

[Quality gates, validation processes, acceptance testing]

## Performance & Reliability

### Performance Requirements

[Targets, monitoring, optimization strategies]

### Error Handling

[Error handling strategy and resilience patterns]

### Monitoring & Observability

[Logging, monitoring, metrics, debugging considerations]

## Security & Compliance

### Security Architecture

[AuthN/AuthZ, data protection]

### Compliance Requirements

[Only if applicable]

## Compatibility & Migration

### Backward Compatibility

[Breaking changes analysis and migration strategy (if applicable)]

### Integration Requirements

[API compatibility, data migration, system integration needs]

## Implementation Plan

### Development Phases

[Phased approach with clear milestones and quality gates]

### Key Dependencies

[Technical dependencies, external systems, critical requirements]

### Documentation Tasks (Post-Spec)

[List any documentation changes needed; do not perform them during create-spec.]

### Paired Dependencies (Version Alignment Required)

[List any client/server packages, protocol pairs, or infrastructure dependencies that MUST have matching versions]

| Package Pair | Required Alignment | Verification Notes |
|--------------|-------------------|-------------------|
| (e.g., @hocuspocus/provider ↔ @hocuspocus/server) | Same major version | Smoke test connectivity before feature work |

### Risk Analysis

[Risk assessment, mitigations, contingencies]

## Research References

- [Links to official docs, internal specs, prior art]

## Specification Complete

[This specification contains all necessary information for task generation and implementation]
```

### Template Flexibility

The template above is a **guide, not a mandate**. Adapt it based on the actual feature:

- **Skip irrelevant sections:** A simple utility doesn't need "Compliance Requirements"
- **Expand critical sections:** If security is paramount, that section should be detailed
- **Add custom sections:** If the feature has unique considerations (e.g., "Offline Support Strategy"), add them
- **Merge related sections:** If distinctions don't add value, combine them

The goal is a **useful specification**, not a filled-out template.

## Output

- **Format:** Markdown (`.md`)
- **Location:** `thoughts/specs/`
- **Filename:** `spec-[idea-name].md`

## Key Principles

1. **Collaborative Excellence:** Work with the user to create the best possible specification, which may differ from their initial vision
2. **Evidence-Based Recommendations:** Ground suggestions in thorough research, and surface when evidence contradicts assumptions
3. **Proactive Problem-Solving:** Identify and address issues before they become implementation problems
4. **Pragmatic Flexibility:** Adapt the template and process to fit the actual needs—structure serves the goal, not vice versa
5. **Honest Assessment:** If an idea has fundamental issues, say so clearly and offer alternatives
6. **User Agency:** Present options and recommendations, but let the user make final decisions on direction

## Target Audience

This command is designed for standard feature development requiring:

- Production-ready quality with reliability and performance considerations
- Comprehensive technical planning and risk assessment
- Integration with existing systems and codebases
- Full testing, security, and monitoring coverage

## Success Indicators

A successful specification should:

- **Solve the Right Problem:** May differ from the initially stated problem after research reveals better approaches
- **Reflect User Intent:** Incorporates user feedback and decisions from engagement points throughout the process
- **Surface Risks Early:** Issues are identified in the spec, not discovered during implementation
- **Enable Confident Implementation:** Contains enough context for downstream task generation
- **Represent Shared Understanding:** Both agent and user aligned on what will be built
- **Be Appropriately Detailed:** Depth matches complexity—not over-engineered for simple features

---

## ➡️ Next Steps

### Recommended: Multi-Model Review

Before generating tasks, consider having multiple AI models review the specification for critical feedback:

```bash
# Run in each tool (Claude, Gemini, Codex) to gather diverse perspectives
/review:spec thoughts/specs/spec-[idea-name].md
```

Each reviewer adds inline review tags with their identity (e.g., `[REVIEW:Claude] ... [/REVIEW]`). Reviews can respond to each other's feedback.

After all reviews complete, integrate the feedback:
```bash
/review:spec-integrate thoughts/specs/spec-[idea-name].md
```

This resolves all comments, asks for user decisions on ambiguous items, and produces a refined specification.

### Generate Tasks

When the specification is complete (and optionally reviewed), run:
```
/dev:2:gen-tasks thoughts/specs/spec-[idea-name].md
```
