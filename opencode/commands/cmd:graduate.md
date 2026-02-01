---
description: Synthesize completed artifacts into permanent documentation with codebase verification
argument-hint: "[feature name or spec/plan path]"
---

# Graduate Feature (with Verification)

Graduate completed feature artifacts to permanent documentation. This command VERIFIES that specs/research match actual implementation before documenting, ensuring permanent docs reflect what was actually built.

## Input

Feature name or spec/plan path: $ARGUMENTS

Feature or path: $ARGUMENTS

## Process Overview

```
DISCOVER → EXTRACT → LOCATE → VERIFY → REPORT → UPDATE → CLEANUP → COMMIT
```

## Phase 1: Discover Artifacts

Use `@thoughts-locator` to find all artifacts related to the feature:

```
thoughts/specs/spec-[feature].md       - Technical specification
thoughts/plans/prd-[feature].md        - PRD (if exists)
thoughts/plans/tasks-*-[feature].md    - Task list
thoughts/research/[date]-[feature].md  - Research documents
thoughts/handoffs/[feature]/           - Handoff documents
thoughts/validation/[date]-[feature].md - Validation reports
thoughts/debug/[date]-[feature].md     - Debug reports
```

### Categorize Artifacts

| Category | Files | Action |
|----------|-------|--------|
| **Verifiable** | specs, research | Extract claims → verify against codebase → document actual |
| **Removable** | tasks, PRDs, handoffs, validation, debug | Remove without review |

Read all **verifiable** artifacts completely. Note **removable** artifacts for cleanup.

## Phase 2: Extract Spec Claims

Use `@thoughts-analyzer` to extract verifiable claims from specs and research documents.

### From Specifications, Extract:

- **Behaviors**: What the feature should do (user-facing functionality)
- **API Contracts**: Interfaces, endpoints, function signatures, parameters
- **Constraints**: Limitations, edge cases, error handling
- **Configuration**: Options, defaults, environment variables
- **Dependencies**: External libraries, services, integrations

### From Research Documents, Extract:

- **Architectural Decisions**: Technical approaches chosen
- **Alternatives Rejected**: Approaches considered but not used
- **Rationale**: Why specific decisions were made
- **Technical Constraints**: Discovered limitations or requirements

Output a list of **verifiable claims** with source references:

```markdown
## Extracted Claims

### Behaviors (from spec-[feature].md)
1. [Behavior description] (line 45)
2. [Behavior description] (line 52)

### API Contracts (from spec-[feature].md)
1. [Interface/endpoint] (line 78)

### Decisions (from research-[feature].md)
1. [Decision] because [rationale] (line 23)
```

## Phase 3: Locate Codebase Files

Use `@codebase-locator` to find implementation files relevant to the extracted claims.

### Search Using:

1. **Feature name** - Direct search for feature-related files
2. **Key terms from specs** - Module names, class names, function names
3. **Explicit file paths** - Any paths mentioned in specs
4. **API identifiers** - Endpoint paths, interface names

### Cross-Reference:

- Check task lists for "Relevant Files" sections
- Check handoffs for "Recent Changes" sections
- Look for test files that exercise the feature

Output a categorized list of implementation files:

```markdown
## Relevant Implementation Files

### Core Implementation
- src/features/[feature]/index.ts
- src/features/[feature]/[component].ts

### API/Interfaces
- src/api/[endpoint].ts
- src/types/[feature].ts

### Configuration
- src/config/[feature].ts

### Tests
- tests/[feature].test.ts
```

## Phase 4: Verify Implementation

Use `@codebase-analyzer` to examine each relevant file and verify spec claims against actual implementation.

### For Each Claim, Determine:

**Match** - Implementation matches spec claim exactly
**Modified** - Behavior exists but works differently than specified
**Missing** - Spec describes something not found in codebase
**Added** - Implementation has functionality not in spec

### Verification Checklist:

#### Behaviors
- [ ] Each behavior from spec exists in code
- [ ] Behavior works as described (API matches)
- [ ] Edge cases handled as specified
- [ ] Error handling matches spec

#### Decisions/Architecture
- [ ] Decision from research is reflected in code
- [ ] Rejected alternatives are NOT implemented
- [ ] Rationale constraints are respected

#### Configuration
- [ ] Config options from spec exist
- [ ] Defaults match spec
- [ ] Validation matches spec constraints

### Record Divergences:

For each divergence, record:
- **Claim**: What the spec says
- **Reality**: What the code does
- **Location**: File and line reference
- **Impact**: Minor (implementation detail) or Major (user-facing change)

## Phase 5: Report and Confirm

Present verification results before updating permanent docs.

### Verification Report Format:

```
================================================================================
VERIFICATION REPORT: [Feature Name]
================================================================================

VERIFIED MATCHES (Spec = Code)
------------------------------
[x] Behavior A: Implemented as specified
    Location: src/features/[feature]/index.ts:45
[x] Decision X: Code follows documented approach
    Location: src/services/[service].ts:120
[x] Config option Y: Present with correct defaults
    Location: src/config/defaults.ts:78

DIVERGENCES FOUND
-----------------

## Modified Behaviors (Implementation differs from spec)

1. [Behavior Name]
   Spec says: "[Quote from spec]"
   Code does: "[Actual implementation]"
   Location: src/features/[feature]/handler.ts:89
   Impact: [Minor/Major]

## Missing from Implementation

2. [Feature Name]
   Spec describes: "[Quote]"
   Not found in codebase
   Likely: [Deferred/Dropped/Different location]

## Added Beyond Spec

3. [Feature Name]
   Not in spec
   Implementation adds: "[Description]"
   Location: src/features/[feature]/extras.ts:34
   Likely: [Implementation detail/Undocumented feature]

RECOMMENDED ACTIONS
-------------------

For Modified Behaviors:
  → Document ACTUAL behavior (recommended)
  → Use --spec-authority to document spec instead

For Missing:
  → Omit from permanent docs (recommended)
  → Note as "Planned but not implemented"

For Added:
  → Document in permanent docs (recommended)
  → Omit as implementation detail

================================================================================
```

### Decision Points:

**Auto-Continue** when:
- All behaviors verified as matching
- Only minor divergences or additions
- No missing core functionality

**Halt and Confirm** when:
- More than 3 Modified behaviors with Major impact
- Core feature behavior is missing
- User specified `--confirm-each` flag

## Collaborative Divergence Resolution

When divergences are found, use **`question`** proactively to determine the right approach.

### Initial Triage Question

```
Question: "Significant divergences found between spec and implementation. How should we proceed?"
Header: "Proceed"
Options:
- Continue with ACTUAL implementation state (Recommended)
- Stop and review divergences manually
- Use --spec-authority to trust spec over code
```

### Per-Divergence Questions (for Major impacts)

When a divergence has Major impact, engage the user before deciding:

**Challenge Question (spec vs implementation conflict):**
```
Question: "Spec says [X] but code does [Y]. Which is correct?"
Header: "Conflict"
Options:
- Code is correct (document actual behavior)
- Spec is correct (this is a bug in implementation)
- Both are partly right (explain further)
```

**Scope Question (missing functionality):**
```
Question: "Spec describes [feature] but it's not in the codebase. What happened?"
Header: "Missing"
Options:
- Feature was intentionally deferred
- Feature was dropped from scope
- It's implemented elsewhere (help me find it)
- This is a gap that should be addressed
```

**Discovery Question (undocumented additions):**
```
Question: "Code includes [feature] not mentioned in spec. Should we document it?"
Header: "Added"
Options:
- Yes, document as implemented feature
- No, it's an implementation detail
- It's temporary/experimental (omit)
```

### When to Engage Per-Divergence

- **Always ask** for Major impact divergences on core functionality
- **Batch similar** Minor divergences into a summary question
- **Skip asking** for clearly additive implementation details
- **Escalate** when divergences suggest the feature may be incomplete

### Low-Confidence Decisions

When you're uncertain about how to categorize or resolve a divergence:

```
Question: "I'm unsure how to handle this divergence. Can you clarify?"
Header: "Clarify"
Options:
- [Option based on your interpretation]
- [Alternative interpretation]
- Let me explain the context first
```

**Key Principle:** When spec and implementation significantly diverge, the user should decide which represents intent. Don't guess—ask.

## Phase 6: Update Permanent Documentation

Based on verification, update permanent docs using **ACTUAL implementation state** by default.

### Target Files

| Document | Location | Action |
|----------|----------|--------|
| Architecture Spec | `spec/architecture/[feature-slug].md` | Create new file |
| Architecture Index | `spec/architecture/README.md` | Add row to table |
| ADR Log | `spec/adr-log.md` | Prepend new ADR entry |
| Changelog | `CHANGELOG.md` | Prepend new entry |

### spec/architecture/[feature-slug].md

Create new architecture document following the established structure:

```markdown
# [Feature Name] System

**Last Updated:** YYYY-MM-DD
**Status:** ✅ Implemented

## Overview

[Description based on ACTUAL implementation, not spec]

## Database Schema

[Tables, relationships, constraints - as actually implemented]

## API Contracts

[Routes, request/response formats from actual code]

## Data Flow

[How data moves through the system]

## Behaviors

- [Behavior 1 - as actually implemented]
- [Behavior 2 - as actually implemented]

## Constraints

- [Constraint from actual implementation]
- [Limitation discovered during verification]

## Configuration

- `CONFIG_KEY`: [Actual default and behavior from code]

## Security

[Auth, authorization, RLS enforcement as implemented]

## Testing

[How to test the system]

## Integration Points

[How it connects to other systems]

## Implementation Notes

[Any notable divergences from original spec worth documenting]
```

### spec/architecture/README.md

Add row to the Architecture Docs table:

```markdown
| [Feature Name] | [[feature-slug].md](./{feature-slug}.md) | ✅ Implemented | [Key features summary] |
```

### spec/adr-log.md

Prepend new ADR entry (after the header, before existing ADRs):

```markdown
## ADR NNNN: [Decision Title]
**Status:** Accepted (implemented and verified)
**Date:** YYYY-MM

**Context:** [From research - verified as still accurate]

**Decision:**
- [What was actually implemented, not just planned]
- [Key implementation choices]

**Alternatives considered:**
- [From research - verified these were NOT used in code]

**Current state:** [File references where decision is reflected]

---
```

Note: ADR numbers continue from the highest existing number in `spec/adr-log.md`.

### CHANGELOG.md

Add entry (newest first, after header):

```markdown
## [Feature Name] - YYYY-MM-DD

### Added

- [Based on actual code, not spec]
- [Verified functionality]

### Changed

- [Actual modifications made]

### Technical Notes

- [Notable implementation details from codebase]
- Verified against spec: [X] matches, [Y] divergences documented
```

## Phase 7: Delete Working Artifacts

Remove all artifacts (both verifiable and removable):

```bash
# Verifiable artifacts (specs, research) - now verified
rm thoughts/specs/spec-[feature].md
rm thoughts/research/*-[feature].md

# Removable artifacts (no review needed)
rm thoughts/plans/prd-[feature].md
rm thoughts/plans/tasks-*-[feature].md
rm -rf thoughts/handoffs/[feature]/
rm thoughts/validation/*-[feature].md
rm thoughts/debug/*-[feature].md
```

## Phase 8: Commit Changes

### Commit 1: Permanent Documentation Update

```bash
git add spec/architecture/[feature-slug].md spec/architecture/README.md spec/adr-log.md CHANGELOG.md
git commit -m "docs: graduate [feature-name] with verified implementation

Verification summary:
- Behaviors: [X] verified, [Y] divergences (documented actual)
- Decisions: [A] verified, [B] divergences
- Added items: [Z] undocumented features now documented

Sources verified:
- thoughts/specs/spec-[feature].md
- thoughts/research/*-[feature].md

Implementation files checked:
- src/features/[feature]/*
- [other relevant paths]"
```

### Commit 2: Artifact Cleanup

```bash
git add -A
git commit -m "chore: clean up [feature-name] working artifacts

Artifacts graduated to permanent documentation.
Original files preserved in git history.
Verification report in previous commit."
```

## Completion Report

```
================================================================================
FEATURE GRADUATED SUCCESSFULLY
================================================================================

Verification Summary:
  Behaviors Verified:  [X]/[Y] matched spec
  Divergences Found:   [Z] (documented as actual)
  Decisions Verified:  [A]/[B] reflected in code
  Added to Docs:       [C] undocumented features

Permanent Documentation Updated:
  [x] spec/architecture/[feature-slug].md - Feature architecture doc (new)
  [x] spec/architecture/README.md         - Architecture index updated
  [x] spec/adr-log.md                     - Architectural decision recorded
  [x] CHANGELOG.md                        - Implementation summary

Artifacts Cleaned Up:
  - thoughts/specs/spec-[feature].md
  - thoughts/plans/tasks-*-[feature].md
  - thoughts/research/*-[feature].md
  - [other removed files]

Git History:
  All original artifacts preserved in git history.
  To recover: git show [commit]:thoughts/specs/spec-[feature].md

================================================================================
```

## Options

### `--dry-run`

Preview without making changes:
- Show artifacts found
- Show extracted claims
- Show verification results
- Show what would be added to permanent docs
- Show files that would be deleted

No files modified, no commits created.

### `--spec-authority`

Trust spec over implementation when divergences found:
- Document spec content even when code diverges
- Useful when implementation is known to be incomplete/incorrect
- Adds warning to permanent docs about divergence

```markdown
> **Note**: This behavior is documented from specification.
> Implementation may differ - see git history for details.
```

### `--confirm-each`

Interactive mode with confirmations:
- Pause after verification report
- Ask for confirmation before each permanent doc update
- Allow selective inclusion/exclusion of divergences
- Allow selective artifact removal

### `--skip-verify`

Skip verification (legacy behavior):
- Synthesize directly from specs without checking codebase
- Faster but may document planned rather than actual behavior
- Use only when confident spec matches implementation

## Guidelines

- **Verify before documenting** - Always confirm spec matches reality
- **Document actual state** - Users encounter the implementation, not the spec
- **Report divergences clearly** - Help catch implementation drift
- **Preserve in git** - Original artifacts recoverable from history
- **Commit separately** - Docs update and cleanup are separate commits

## Error Handling

### No Artifacts Found

```
Error: No artifacts found for feature "[feature]"

Searched:
- thoughts/specs/spec-[feature].md
- thoughts/plans/*-[feature].md
- thoughts/research/*-[feature].md

Did you mean one of these?
- [similar-feature-1]
- [similar-feature-2]
```

### No Codebase Files Found

```
Warning: No implementation files found for feature "[feature]"

This could mean:
- Feature was not implemented
- Feature uses unexpected file naming
- Feature is in a different location

Options:
1. Specify implementation paths manually
2. Skip verification (--skip-verify)
3. Abort graduation
```

### Verification Failed

```
Error: Verification found critical issues

- [X] core behaviors missing from implementation
- [Y] major divergences that change user-facing behavior

Cannot graduate without resolution. Options:
1. Fix implementation to match spec
2. Update spec to match implementation
3. Force graduation with --spec-authority (not recommended)
```
