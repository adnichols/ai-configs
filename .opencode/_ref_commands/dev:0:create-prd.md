---
description: Generate a Product Requirements Document (PRD) with strict scope preservation and fidelity focus
argument-hint: "[Feature Description]"
---

# Rule: Generating a Product Requirements Document (PRD) with Fidelity Preservation

## Goal

To guide an AI assistant in creating a Product Requirements Document (PRD) in Markdown format with YAML front-matter, using a fidelity-preserving approach that captures exact requirements without scope expansion. The document creation is the sole purpose of this command - implementation is handled by separate commands. Think harder.

## Core Principle: Specification Fidelity

**The user's requirements are the absolute authority.** This command:

- Adds ZERO requirements beyond user specifications
- Makes NO scope expansions or "improvements"
- Preserves ALL original decisions and constraints
- Creates PRDs that document EXACTLY what's requested
- Uses fidelity-preserving agents that cannot modify scope

## Input

Feature description: $ARGUMENTS

The user will provide:

1. **Feature Description:** Brief description or request for new functionality

## Process

1. **Gather Precise Requirements:** Ask focused questions to understand exact scope and boundaries
2. **Define Clear Boundaries:** Explicitly capture what's included and what's excluded
3. **Generate PRD with Fidelity Metadata:** Create PRD with YAML front-matter containing fidelity settings
4. **Save PRD:** Save as `prd-[feature-name].md` in `thoughts/plans/` directory with fidelity preservation settings
5. **End Command:** The command completes after saving the PRD. Implementation is a separate phase.

**IMPORTANT:** If you encounter write permission errors when saving to `thoughts/plans/`, you are likely in **plan mode** (read-only). STOP and ask the user:
- "I'm in plan mode and cannot write files. Would you like me to:"
  - "A) Present the PRD here for review, then you can save it"
  - "B) Wait until we exit plan mode to save it"
  - "C) Save to a different location (please specify)"

## Clarifying Questions for Scope Definition

Use the **AskUserQuestion tool** to gather precise requirements through structured questions. This provides a better user experience than plain text questions.

### Question Strategy

Ask 1-4 targeted questions at a time using AskUserQuestion. Group related questions logically:

### Core Scope Questions

Use AskUserQuestion with questions like:

```
Question 1: "What specific problem does this feature solve?"
Header: "Problem"
Options:
- [Suggested interpretation 1]
- [Suggested interpretation 2]
- [Suggested interpretation 3]
(Users can always select "Other" for custom input)

Question 2: "Who is the primary user of this feature?"
Header: "User type"
Options:
- End users (customers/clients)
- Internal team members
- Developers/technical users
- System administrators
```

### Boundary Definition Questions

```
Question 1: "What specific functionality should this feature include?"
Header: "Scope"
Options:
- [Core functionality option 1]
- [Core functionality option 2]
- [Core functionality option 3]

Question 2: "Are there things this feature should NOT do?"
Header: "Exclusions"
Options:
- No restrictions - implement all related functionality
- Keep minimal - exclude complex features
- Exclude certain capabilities (specify in Other)
- Exclude integration with other systems
```

### Testing and Security Scope

```
Question 1: "What level of testing is expected?"
Header: "Testing"
Options:
- Basic functionality validation only
- Comprehensive testing including edge cases
- Testing scope to be determined later

Question 2: "Are there specific security requirements?"
Header: "Security"
Options:
- Standard security practices
- Enhanced security measures needed
- Security scope to be determined later
```

### AskUserQuestion Usage Notes

- Use `multiSelect: true` when choices aren't mutually exclusive
- Keep headers short (max 12 chars) - they appear as chips/tags
- Provide clear descriptions for each option to explain trade-offs
- Users always have an "Other" option for custom responses
- Ask follow-up questions if initial answers need clarification

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

## PRD Template Structure

### Unified Fidelity-Preserving Template

```markdown
---
version: 1
fidelity_mode: strict
agents:
  developer: developer
  reviewer: quality-reviewer
scope_preservation: true
additions_allowed: none
document_metadata:
  source_type: user_requirements
  creation_date: [timestamp]
  fidelity_level: absolute
  scope_changes: none
---

# [Feature Name] - Product Requirements Document

## Problem Statement

[Clear description of the specific problem being solved - exactly as understood from user input]

## Explicit Requirements

### Core Functionality

1. [Requirement 1 - exactly as specified by user]
2. [Requirement 2 - exactly as specified by user]
3. [Requirement 3 - exactly as specified by user]

### User Stories (if provided)

- As a [user type], I want to [action] so that [benefit]
- As a [user type], I want to [action] so that [benefit]

## Scope Boundaries

### Explicitly Included

- [Functionality that is clearly part of this PRD]
- [Features mentioned by user or clarified as included]

### Explicitly Excluded

- [Functionality that is clearly NOT part of this PRD]
- [Features explicitly ruled out during clarification]
- [Future considerations not in current scope]

### Assumptions & Clarifications

- [Any assumptions made during requirement gathering]
- [Areas where user provided specific clarification]

## Success Criteria

- [Measurable criteria tied directly to explicit requirements]
- [Success indicators that match specified functionality only]

## Testing Requirements

[Include only if user explicitly mentioned testing needs, otherwise use:]
Testing scope: To be determined during implementation phase

## Security Requirements

[Include only if user explicitly mentioned security needs, otherwise use:]
Security scope: To be determined during implementation phase

## Technical Considerations

[Include only technical aspects explicitly mentioned by user, otherwise use:]
Technical approach: To be determined during implementation phase

## Implementation Notes

### Fidelity Requirements (MANDATORY)

- Implement ONLY what's explicitly specified in this PRD
- Do not add features, tests, or security beyond requirements
- Question ambiguities rather than making assumptions
- Preserve all requirement constraints and limitations

### Next Steps

- Use developer agent for implementation planning
- Use quality-reviewer agent for validation
- Follow strict scope preservation throughout implementation

## Open Questions

- [Any remaining questions needing clarification before implementation]
- [Areas where user input was ambiguous and needs resolution]

## Document Status

✅ **PRD Complete:** This document captures the exact requirements as specified. Ready for fidelity-preserving implementation.
```

## Key Principles

1. **Absolute Fidelity:** User requirements are the complete and sole authority
2. **Zero Additions:** No requirements, features, or scope beyond user specifications
3. **Clear Boundaries:** Explicit documentation of what's included and excluded
4. **Fidelity Agents:** Always use developer and quality-reviewer for implementation
5. **Scope Preservation:** Maintain all limitations and boundaries from original requirements

## Output Format

- **Format:** Markdown (`.md`)
- **Location:** `thoughts/plans/`
- **Filename:** `prd-[feature-name].md`
- **Metadata:** Fidelity-preserving YAML front-matter

## Success Indicators

A well-crafted PRD should:

- **Fidelity Metadata:** Include complete YAML front-matter with fidelity settings
- **Clear Scope Boundaries:** Explicit documentation of included and excluded functionality
- **Agent Specification:** Reference fidelity-preserving agents for implementation
- **Zero Scope Creep:** No additions, improvements, or expansions beyond user requirements
- **Complete Context:** All necessary information captured without external dependencies

## Target Audience

This command serves teams that need:

- Exact requirement preservation without scope creep
- Clear boundaries between what's included and excluded
- Fidelity guarantees throughout the development process
- Simple, predictable PRD creation without complexity overhead

---

## ➡️ Next Steps

### 1. Generate Specification

When the PRD is complete and approved, run:
```
/dev:1:create-spec thoughts/plans/prd-[feature-name].md
```

### 2. Review Specification (Recommended)

After the spec is generated, consider multi-model review before task generation:

```bash
# Run in each tool (Claude, Gemini, Codex) to gather diverse perspectives
/review:spec thoughts/specs/spec-[feature-name].md

# After all reviews complete, integrate feedback
/review:spec-integrate thoughts/specs/spec-[feature-name].md
```

### 3. Generate Tasks

```
/dev:2:gen-tasks thoughts/specs/spec-[feature-name].md
```
