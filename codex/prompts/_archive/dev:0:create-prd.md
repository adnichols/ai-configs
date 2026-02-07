---
description: Generate a Product Requirements Document (PRD) with strict scope preservation and fidelity focus. Usage: [Feature Description]
---

# Rule: Generating a Product Requirements Document (PRD) with Fidelity Preservation

## Goal

To guide an AI assistant in creating a Product Requirements Document (PRD) in Markdown format with YAML front-matter, using a fidelity-preserving approach that captures exact requirements without scope expansion. The document creation is the sole purpose of this command - implementation is handled by separate commands.

## Core Principle: Specification Fidelity

**The user's requirements are the absolute authority.** This command:

- Adds ZERO requirements beyond user specifications
- Makes NO scope expansions or "improvements"
- Preserves ALL original decisions and constraints
- Creates PRDs that document EXACTLY what's requested

## Input

Some input may be provided via $ARGUMENTS

The user will provide:

1. **Feature Description:** Brief description or request for new functionality

## Process

1. **Gather Precise Requirements:** Ask focused questions to understand exact scope and boundaries
2. **Define Clear Boundaries:** Explicitly capture what's included and what's excluded
3. **Generate PRD with Fidelity Metadata:** Create PRD with YAML front-matter containing fidelity settings
4. **Save PRD:** Save as `prd-[feature-name].md` in `thoughts/plans/` directory
5. **End Command:** The command completes after saving the PRD. Implementation is a separate phase.

## Clarifying Questions for Scope Definition

Ask targeted questions to gather precise requirements:

### Core Scope Questions

- "What specific problem does this feature solve?"
- "Who is the primary user of this feature?"

### Boundary Definition Questions

- "What specific functionality should this feature include?"
- "Are there things this feature should NOT do?"

### Testing and Security Scope

- "What level of testing is expected?"
- "Are there specific security requirements?"

## PRD Template Structure

```markdown
---
version: 1
fidelity_mode: strict
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

## Scope Boundaries

### Explicitly Included

- [Functionality that is clearly part of this PRD]

### Explicitly Excluded

- [Functionality that is clearly NOT part of this PRD]

### Assumptions & Clarifications

- [Any assumptions made during requirement gathering]

## Success Criteria

- [Measurable criteria tied directly to explicit requirements]

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

## Open Questions

- [Any remaining questions needing clarification before implementation]

## Document Status

✅ **PRD Complete:** This document captures the exact requirements as specified. Ready for specification phase.
```

## Key Principles

1. **Absolute Fidelity:** User requirements are the complete and sole authority
2. **Zero Additions:** No requirements, features, or scope beyond user specifications
3. **Clear Boundaries:** Explicit documentation of what's included and excluded
4. **Scope Preservation:** Maintain all limitations and boundaries from original requirements

## Output Format

- **Format:** Markdown (`.md`)
- **Location:** `thoughts/plans/`
- **Filename:** `prd-[feature-name].md`

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

# After all reviews complete, integrate feedback in Claude Code
/review:spec-integrate thoughts/specs/spec-[feature-name].md
```

### 3. Generate Tasks

```
/dev:2:gen-tasks thoughts/specs/spec-[feature-name].md
```
