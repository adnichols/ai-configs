---
description: Convert specification to executable task list with collaborative fidelity. Usage: [Specification File Path]
---

# Rule: Specification to Task Conversion with Collaborative Fidelity

## Goal

To guide an AI assistant in converting a detailed specification document (created through collaborative planning) directly into executable task lists while faithfully implementing the agreed-upon solution. The specification represents the outcome of collaborative dialogue and should be implemented as agreed, with proactive user engagement when issues arise. Think harder.

## Core Principle: Faithful Implementation

**The specification represents the agreed-upon solution** from collaborative planning. This command:

- Implements what was agreed upon in the specification
- Avoids unilateral scope additions or modifications
- Preserves the decisions and constraints established through collaboration
- Creates tasks that implement the specified solution
- Engages the user proactively when issues, gaps, or better alternatives are discovered

## Collaborative Context

The specification arriving at this command was created through `/dev:1:create-spec`, which involves:
- Research and analysis of the user's idea
- Proactive course corrections when issues were discovered
- User engagement and feedback throughout the process
- Potential deviation from the original request based on findings

**This means:** The spec already represents refined, agreed-upon requirements—not a rigid contract. Your role is to implement this solution faithfully while continuing the collaborative spirit. If you discover issues during task generation, engage the user rather than making assumptions.

## Input

The user will provide:

1. **Specification File Path:** Path to the detailed specification document. This may be provided in $ARGUMENTS

## Process

1. **Read Specification Completely:** Parse the entire specification document to understand:

   - All functional requirements
   - All technical constraints and decisions
   - Stated testing requirements (if any)
   - Stated security requirements (if any)
   - Performance requirements and success criteria
   - Implementation timeline and phases
   - Resource constraints
   - Explicit scope boundaries (what's included/excluded)
   - **Dependency compatibility notes** (convert advisory notes to verification tasks)
   - **Infrastructure prerequisites** (client/server pairs, protocol dependencies)

2. **Extract Task Structure:** Identify natural implementation phases from the specification:

   - Use specification's own phase structure if provided
   - Create logical groupings based on specification content
   - Maintain specification's dependencies
   - Preserve specification's success criteria for each phase

3. **Create and Save Task List:** Generate and save tasks that implement:

   - What's specified in the document (engage user if gaps are found)
   - Testing as specified (propose additions only if critical gaps exist)
   - Security as specified (flag concerns but don't add unilaterally)
   - Performance measures as specified
   - Documentation as specified
   - Save tasks to `thoughts/plans/tasks-fidelity-[spec-name].md`
   - Inform user of draft location for review

## Parallel Analysis Strategy

Use the Task tool to spawn parallel analysis subagents for efficient specification processing and codebase exploration.

### Subagent Delegation

Spawn parallel Task agents with `subagent_type=Explore`:

```
Task 1: Specification Parsing
- Extract all functional requirements from spec
- Identify testing/security/performance requirements
- Document scope boundaries (included/excluded)
- List success criteria and completion conditions

Task 2: Codebase Analysis
- Find existing files that will need modification
- Locate relevant patterns and conventions
- Identify integration points and dependencies
- Document available utilities and shared components
- **Identify paired dependencies requiring version alignment** (client/server packages, protocol pairs)
- **Flag infrastructure that needs smoke testing** before feature work
```

### Orchestrator Responsibilities

The parent agent (you) handles:
- Coordinating specification and codebase analysis
- Synthesizing findings into coherent task structure
- Generating the final task list with proper phasing
- User communication for ambiguities or issues

Wait for ALL subagents to complete before synthesizing into the task list.

## Converting Advisory Notes to Verification Tasks

**CRITICAL:** Specifications often contain advisory notes like "Ensure X", "Verify Y", or "Make sure Z matches". These are NOT documentation—they are **implicit requirements** that must become explicit, checkable tasks.

### Common Advisory Patterns to Convert

| Spec Note Pattern | Task Conversion |
|-------------------|-----------------|
| "Ensure versions are compatible" | "Verify @pkg/client and @pkg/server are same major version" |
| "Make sure X is configured" | "Configure X and validate configuration works" |
| "Use compatible versions" | "Check package.json versions match, run smoke test" |
| "Verify before proceeding" | Add blocking task before dependent work |

### Infrastructure Verification Rule

When a specification introduces **paired dependencies** (client/server libraries, protocol-based packages, WebSocket connections):

1. **Create explicit verification task** before any feature work
2. **Add smoke test task** to confirm basic connectivity
3. **Block feature tasks** until verification passes

Example:
```
- [ ] 1.0 Infrastructure Verification (MUST PASS before 1.1+)
  - [ ] 1.0.1 Verify @hocuspocus/server and @hocuspocus/provider versions match
  - [ ] 1.0.2 Smoke test: client connects to server successfully
  - [ ] 1.0.3 Document verified versions
- [ ] 1.1 Implement presence features (blocked by 1.0)
```

**Why this exists:** A spec note saying "ensure compatibility" is guidance that gets skipped. A task saying "verify versions match" is a checkbox that blocks progress.

## Final Task File Format

The final task file at `thoughts/plans/tasks-fidelity-[spec-name].md`:

```markdown
# [Specification Title] - Implementation Tasks

## 🎯 Implementation Context

**Source Specification:** [path to spec file]
**Implementation Scope:** As agreed in collaborative specification

### Specification Summary

[Brief summary of what's being implemented - extracted from spec]

### Implementation Boundaries

**Included:** [What specification includes]
**Excluded:** [What specification excludes]
**Testing Level:** [As specified]
**Security Level:** [As specified]
**Documentation Level:** [As specified]

## 🗂️ Implementation Files

[List of files that will need creation/modification based on specification analysis]

### Paired Dependencies (Version Alignment Required)

[List any client/server packages, protocol pairs, or infrastructure dependencies that MUST have matching versions]

| Package Pair | Required Alignment | Verification Method |
|--------------|-------------------|---------------------|
| @example/client ↔ @example/server | Same major version | Check package.json, run connectivity test |

### Development Notes

- Implement the specification as the agreed-upon solution
- Avoid unilateral additions to testing, security, or scope
- Engage the user when gaps, issues, or better alternatives are discovered
- Question ambiguity rather than assuming
- The goal is faithful implementation with collaborative refinement when needed

### Approval & Clarification Protocol

**When implementing agents encounter any of the following, they should engage the user for guidance:**

1. **Scope Adjustments** - Any addition, removal, or modification to specified requirements
2. **Ambiguity** - Specification is unclear about implementation details
3. **Contradictions** - Specification conflicts with existing code patterns or constraints
4. **Technical Blockers** - A specified approach is infeasible or would cause issues
5. **Missing Information** - Critical details needed to proceed are not in the specification
6. **Better Alternatives** - A clearly superior approach is discovered during implementation

**Process:**
1. **Stop** - Do not proceed with assumptions
2. **Report** - Explain what was discovered and its impact
3. **Present Options** - Offer alternatives with trade-offs if applicable
4. **Wait** - Get explicit user approval before continuing

**Examples requiring approval:**
- "The specification says X but the codebase uses Y - which should I follow?"
- "This phase requires a dependency not mentioned in the spec - should I add it?"
- "The API shape in the spec is outdated - update spec or use current version?"
- "A simpler approach exists for this phase - can I propose an alternative?"

**Key Point:** Scope changes ARE allowed, but require user feedback and approval. The goal is fidelity to user intent, not rigid adherence to potentially outdated details.

## ⚙️ Implementation Phases

[Extract phases directly from specification structure]

### Phase 0: Infrastructure Verification (if paired dependencies exist)

**Objective:** Validate infrastructure prerequisites before feature implementation
**Blocking:** All subsequent phases are blocked until Phase 0 passes

**Tasks:**

- [ ] 0.1 Verify paired package versions match
  - [ ] 0.1.1 Check client package version in package.json
  - [ ] 0.1.2 Check server package version in package.json
  - [ ] 0.1.3 Confirm versions are compatible (same major version)
- [ ] 0.2 Smoke test infrastructure connectivity
  - [ ] 0.2.1 Basic connection test (client → server)
  - [ ] 0.2.2 Verify protocol handshake succeeds
- [ ] 0.3 Document verified configuration
  - [ ] 0.3.1 Record working versions in implementation notes

### Phase 1: [Phase Name from Specification]

**Objective:** [Exact objective from specification]
**Timeline:** [As specified in original document]
**Prerequisites:** Phase 0 complete (if applicable)

**Specification Requirements:**
[List requirements exactly as written in specification]

**Tasks:**

- [ ] 1.0 [High-level task matching specification]
  - [ ] 1.1 [Specific implementation task from spec]
  - [ ] 1.2 [Another specific task from spec]
  - [ ] 1.3 [Validation task as specified]

### Phase N: Final Phase

**Objective:** Complete implementation as specified

**Tasks:**

- [ ] N.0 Finalize Implementation
  - [ ] N.1 Complete all specified deliverables
  - [ ] N.2 Validate against specification success criteria
  - [ ] N.3 Document implementation (if specified in original spec)

## 📋 Specification Context

### [Technical Section 1 from Spec]

[Preserve relevant technical details from specification]

### [Technical Section 2 from Spec]

[Preserve architectural decisions from specification]

## 🚨 Implementation Requirements

### Implementation Guidelines

- Implement the agreed-upon solution from the specification
- Avoid unilateral additions; engage user if gaps are discovered
- Question ambiguities rather than making assumptions
- Preserve specification constraints and limitations
- Continue the collaborative spirit from spec creation

### Success Criteria

[Extract success criteria from specification]

### Testing Requirements

[Extract testing requirements as specified - flag concerns if gaps exist]

### Security Requirements

[Extract security requirements as specified - flag concerns if gaps exist]

## ✅ Validation Checklist

- [ ] Implementation reflects the agreed-upon solution
- [ ] User engaged on any discovered issues or gaps
- [ ] Specification constraints and intent preserved
- [ ] Success criteria from specification met
- [ ] No testing beyond what specification requires
- [ ] No security measures beyond specification requirements
- [ ] **Paired dependencies verified compatible** (versions match)
- [ ] **Infrastructure smoke tested** before feature implementation

## 📊 Completion Criteria

[Extract completion criteria exactly from specification]
```

## Handling Issues During Task Generation

**When you discover problems with the specification that would prevent accurate task generation:**

1. **Stop** - Do not generate tasks based on incomplete or problematic specifications
2. **Report** - Explain what issue you found (ambiguity, contradiction, missing information, impossible requirement)
3. **Ask** - Request clarification or suggest how to resolve before continuing

Examples requiring this protocol:
- Specification has contradictory requirements
- Specification references components/APIs that don't exist
- Specification is ambiguous about critical implementation details
- Specification has gaps that would block implementation
- Requirements are technically infeasible based on codebase analysis

**Do not** guess at intent or fill gaps with assumptions. Ask me to clarify or update the specification.

## Key Principles

1. **Collaborative Implementation:** Implement the agreed solution faithfully, engaging the user when issues arise
2. **Specification Respect:** The spec represents shared understanding from dialogue, not sacred text
3. **Proactive Communication:** Surface issues early rather than waiting until blocked
4. **Preserve Intent:** Maintain the spirit of decisions; adapt details collaboratively when needed
5. **Notes → Tasks:** Advisory notes ("ensure X", "verify Y") become explicit verification tasks
6. **Infrastructure First:** Paired dependencies get Phase 0 verification before feature work

## Success Indicators

A well-converted task list should:

- **Faithful Implementation:** Tasks implement the agreed-upon solution from collaborative planning
- **User Engagement:** Issues, gaps, or concerns surfaced proactively during task generation
- **Complete Context:** Implementer has all necessary information from specification
- **Clear Boundaries:** Explicit documentation of what's included/excluded
- **Validation Criteria:** Clear success measures extracted from specification
- **Collaborative Spirit:** Continues the dialogue-based approach from spec creation

## Target Audience

This command serves teams that have:

- Detailed specifications from collaborative planning
- Want faithful implementation of agreed solutions
- Value proactive communication over rigid compliance
- Need clear task structure with appropriate context
- Prefer engagement over assumptions when issues arise

---

## ➡️ Next Command

When the task list is complete and approved, run:
```
/dev:3:process-tasks [path-to-tasks]
```
