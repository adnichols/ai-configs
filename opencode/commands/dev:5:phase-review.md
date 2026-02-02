---
description: Propagate decisions from completed phases to future phases
argument-hint: "<completed phase path> [future phases...]"
---

# Phase Review and Decision Propagation

After completing a phase of work, analyze what was implemented versus what was specified, extract decisions made during implementation, and propagate those decisions forward to future phase specs via inline annotations.

## Input

Phase paths: $ARGUMENTS

First argument is the completed phase. Remaining arguments (or auto-discovered) are future phases.

**Completed phase:** First argument in $ARGUMENTS
**Future phases:** Remaining arguments (or auto-discovered from parent spec)

## Process Flow

```
PARSE → GATHER_EVIDENCE → EXTRACT_DECISIONS → ANALYZE_IMPACT → GENERATE_ANNOTATIONS → APPROVAL → APPLY
```

## Process

### 1. Parse Arguments and Locate Files

Parse `$ARGUMENTS` to extract:
- **Completed phase path**: First argument (required)
- **Future phase paths**: Remaining arguments (optional)

Example: `/dev:5:phase-review thoughts/specs/phases/phase-1-*.md thoughts/specs/phases/phase-2-*.md`

**If no future phases specified**, auto-discover from parent spec:
1. Read completed phase spec, extract `parent:` from YAML frontmatter
2. Find all sibling phase files in same directory
3. Filter to phases with higher phase number than completed phase

Validate all paths exist. If any missing, report error and halt.

### 2. Read Completed Phase and Extract Metadata

Read the completed phase specification completely:
- Extract YAML metadata: `parent`, `dependencies`, `status`
- Extract scope of work sections (Objective, Implementation Plan)
- Extract verification plan (what was supposed to be tested)
- Note any "Open Questions" or "Decisions Deferred" sections

Read the parent research spec:
- Locate via `parent:` field in phase spec
- Extract relevant Technical Design and Implementation Plan sections
- Note existing Review Resolution Log entries (decisions already documented)

### 3. Gather Implementation Evidence

Collect evidence of what was actually implemented from multiple sources, prioritized by quality:

**PRIMARY SOURCE: Task File Deviations Log**

The task file (`thoughts/plans/tasks-*-phase-[n]-*.md`) may contain a `## Deviations Log` section populated during `dev:3:process-tasks`. This is the **highest quality source** because decisions were captured at the moment they were made.

Read the task file and extract any Deviations Log entries:
```markdown
## Deviations Log

### D1: [Decision Title] - [Date]
- **Category:** [...]
- **Discovery:** [...]
- **Decision Made:** [...]
- **Future Phases Affected:** [...]
```

If a Deviations Log exists with entries, these become your primary decisions to propagate.

**SECONDARY SOURCES: Git History & Documentation**

Use these to supplement or fill gaps when no Deviations Log exists:

*Git History Analysis:*

Use Task tool with `subagent_type=explore` to search:
```bash
# Commits related to this phase
git log --oneline --all --grep="Phase [N]" --grep="phase-[n]"

# Recent commits with detailed changes
git log --name-only --oneline -20

# Detailed diff for key changes
git diff --stat HEAD~10
```

*Documentation Sources:*

Search and read:
- `thoughts/handoffs/*/` - Handoff documents from this phase
- `thoughts/validation/*` - Any validation reports
- `thoughts/research/*` - Research documents created during implementation

### 4. Extract Decisions

Analyze gathered evidence to identify decisions made during implementation.

**Decision Categories:**

| Category | Description | Example |
|----------|-------------|---------|
| **Uncertainty Resolved** | Spec was ambiguous, implementation chose a path | "Chose partial unique index instead of trigger" |
| **Scope Adjusted** | Feature was modified, deferred, or dropped | "Deferred parseDocumentHandle to Phase 3" |
| **Pattern Discovered** | Implementation revealed a pattern for future phases | "Used atomic get-or-create with ON CONFLICT" |
| **Constraint Identified** | Found a limitation affecting future work | "RLS prevents direct access; must use withAuthenticatedDb" |
| **API Contract Defined** | Concrete interface was established | "GET /api/workspaces returns { id, name, slug, handle }" |

**Decision Extraction Process:**

**If Deviations Log exists in task file:**
- Import decisions directly - they are already in the correct format
- The `Future Phases Affected` field tells you exactly what to annotate
- High confidence for all logged decisions (they were captured at decision time)

**If no Deviations Log (or supplementing it):**
- Analyze git history and documentation sources
- For each source, extract:
  1. **What changed** from original spec
  2. **Why** it changed (rationale from handoffs/comments/commits)
  3. **Impact** on future phases (which phases affected)
- These inferred decisions are lower confidence

Document as structured list:

```markdown
## Extracted Decisions

### D1: [Decision Title]
- **Category:** [Category from table above]
- **Source:** [File path and section reference]
- **Original Spec Said:** [Quote or summary]
- **Implementation Did:** [What was actually done]
- **Rationale:** [Why this choice was made]
- **Future Phases Affected:** [Phase 2, Phase 3, etc.]
```

### 5. Read and Analyze Future Phase Specs

For each future phase spec:
1. Read completely
2. Extract YAML metadata (verify `dependencies` includes completed phase)
3. Identify sections that reference or depend on completed phase
4. Note any explicit assumptions about completed phase behavior

Create decision impact mapping:

```markdown
## Decision Impact Mapping

| Decision | Phase 2 Impact | Phase 3 Impact | Phase 4 Impact |
|----------|----------------|----------------|----------------|
| D1 | Section 2.3 | - | Section 4.1 |
| D2 | Section 2.1, 2.4 | Section 3.2 | - |
```

### 6. Generate Annotations for Future Specs

For each future phase spec, generate inline HTML comment annotations where decisions affect the content.

**Annotation Format:**

```html
<!-- PROPAGATED from Phase [N] (YYYY-MM-DD):
Decision: [D#: Decision Title]
Impact: [How this decision affects this specific section]
Action: [What implementer should do differently, if anything]
Source: [Path to completed phase spec or handoff]
-->
```

**Placement Rules:**
- Place annotation ABOVE the affected section heading
- If decision affects multiple points in same section, use single annotation with numbered impacts
- Do not annotate if decision has no material impact on section content

**Example:**

```markdown
<!-- PROPAGATED from Phase 1 (2025-12-27):
Decision: D3: API Response Contract for /api/workspaces
Impact: Use the established response format: { id, name, slug, handle, createdAt, isPersonal }
Action: Workspace Home UI should consume this exact contract, including 'handle' for URL construction
Source: thoughts/specs/phases/phase-1-workspace-routing-data-api.md
-->

### 2. Client Context Refactor
- **`AppViewProvider` Updates:**
  - **Remove:** Logic that derives workspace from local storage...
```

### 7. Generate Phase Retrospective for Parent Spec

Create a Phase Retrospective section to append to the parent research spec.

**Format:**

```markdown
## Phase Retrospective

### Phase [N]: [Phase Title] - Completed [YYYY-MM-DD]

**Implementation Status:** [Completed as specified | Completed with modifications | Partially completed]

**Git References:**
- Branch: `[branch-name]`
- Key Commits: `[commit-hash]` - [description]

**Decisions Made:**

| Decision | Category | Description | Rationale |
|----------|----------|-------------|-----------|
| D1 | Uncertainty Resolved | [Brief description] | [Why] |
| D2 | Scope Adjusted | [Brief description] | [Why] |
| D3 | Pattern Discovered | [Brief description] | [Why] |

**Propagated to Future Phases:**
- Phase [M]: [N] annotations added
- Phase [P]: [N] annotations added

**Learnings for Future:**
- [Key insight 1]
- [Key insight 2]

**Artifacts:**
- Task List: `thoughts/plans/tasks-*-phase-[n]-*.md` (all tasks complete)
- Validation: `thoughts/validation/YYYY-MM-DD-*.md`
- Handoffs: [List any handoff documents created]
```

### 8. Triage Changes by Confidence

Categorize all proposed changes by confidence level:

**High Confidence (Auto-Apply Candidate):**
- **Decisions from Deviations Log** - These were captured at decision time with user approval
- Annotations adding factual information (API contracts, file paths, concrete implementations)
- Status updates in YAML frontmatter
- Phase Retrospective additions to parent spec
- Annotations where decision is documented in multiple sources with clear rationale

**Low Confidence (Requires User Approval):**
- **Inferred decisions** (from git/docs, not from Deviations Log)
- Annotations that suggest scope changes to future phases
- Annotations where rationale is inferred rather than explicit
- Any decision that contradicts content in future phase spec
- Decisions that affect user-facing behavior or requirements
- Scope adjustments without explicit user approval in Deviations Log

### 9. Present Changes for Approval

**CRITICAL:** You MUST display the complete inventory of changes BEFORE asking for approval. The user cannot approve what they cannot see.

**Step 1: Display the Full Report**

Output the complete report to the user (do NOT use `question` yet):

```
================================================================================
PHASE REVIEW: Decision Propagation Report
================================================================================

COMPLETED PHASE: [path]
  Title: [Phase N: Description]
  Status: [Verified Complete | Partial - see notes]

================================================================================
DECISIONS EXTRACTED: [N total]
================================================================================

PROPAGATING FORWARD: [X decisions]
-----------------------------------

D1. [Title] - [Category] - [HIGH/LOW confidence]
    Source: [Deviations Log | Git commit | Handoff doc]
    Original: "[What spec said]"
    Decision: "[What was implemented]"
    Rationale: [Why]
    Affects: Phase 2 (Section 2.3), Phase 3 (Section 3.1)

D2. [Title] - [Category] - [HIGH/LOW confidence]
    Source: [...]
    Original: "[...]"
    Decision: "[...]"
    Rationale: [...]
    Affects: Phase 2 (Section 2.1)

[... list ALL decisions being propagated ...]

NOT PROPAGATING: [Y decisions]
------------------------------

D3. [Title] - [Category]
    Reason: [No future phases affected | Already documented | Implementation detail only]

[... list decisions NOT being propagated and why ...]

================================================================================
PROPOSED ANNOTATIONS (Exact Content)
================================================================================

## Phase 2: [path]

### Section 2.3: [Section Name]

The following annotation will be inserted ABOVE this section:

```html
<!-- PROPAGATED from Phase 1 (2025-12-27):
Decision: D1: [Exact decision title]
Impact: [Exact impact description]
Action: [Exact action for implementer]
Source: [Exact source path]
-->
```

Confidence: [HIGH/LOW]

---

### Section 2.4: [Section Name]

The following annotation will be inserted ABOVE this section:

```html
<!-- PROPAGATED from Phase 1 (2025-12-27):
Decision: D2: [Exact decision title]
Impact: [Exact impact description]
Action: [Exact action for implementer]
Source: [Exact source path]
-->
```

Confidence: [HIGH/LOW]

---

## Phase 3: [path]

[... show ALL annotations with exact content ...]

================================================================================
PARENT SPEC UPDATE
================================================================================

## [parent spec path]

The following Phase Retrospective section will be appended:

```markdown
## Phase Retrospective

### Phase 1: [Phase Title] - Completed [YYYY-MM-DD]

**Implementation Status:** [Status]

**Decisions Made:**

| Decision | Category | Description | Rationale |
|----------|----------|-------------|-----------|
| D1 | [Category] | [Description] | [Rationale] |
| D2 | [Category] | [Description] | [Rationale] |

**Propagated to Future Phases:**
- Phase 2: [N] annotations
- Phase 3: [N] annotations

**Learnings for Future:**
- [Learning 1]
- [Learning 2]
```

================================================================================
SUMMARY
================================================================================

Changes to apply:
  - [X] annotations across [Y] future phase specs
  - [1] Phase Retrospective section to parent spec
  - [1] status update to completed phase spec

High-Confidence: [N] (from Deviations Log or explicit documentation)
Low-Confidence:  [M] (inferred from git/docs)

================================================================================
```

**Step 2: Clarify Low-Confidence Decisions (if any)**

If there are low-confidence decisions, use `question` to get clarification BEFORE finalizing annotations. Group related questions together (max 4 per call).

For each low-confidence decision, ask:

```
Question: "Decision D3 was inferred from git history. Should we propagate it?"
Header: "D3"
Options:
- Yes, propagate as shown
- Yes, but modify the annotation (describe in "Other")
- No, don't propagate this decision
- Need more context (describe in "Other")
```

Example with multiple low-confidence decisions:

```
Questions:
1. "D3: API returns 404 for missing workspace. Inferred from commit abc123. Propagate to Phase 2?"
   Options: [Propagate as shown | Modify | Don't propagate | Need context]

2. "D5: Rate limiting deferred to Phase 4. Inferred from PR comments. Propagate to Phase 3?"
   Options: [Propagate as shown | Modify | Don't propagate | Need context]
```

After receiving answers:
- Update annotations based on user input
- Remove decisions user rejected
- Modify annotations where user requested changes
- Re-display affected sections if significant changes were made

**Step 3: Final Batch Approval**

After all clarifications are integrated, use `question` for final approval:

```
Question: "Ready to apply [N] annotations to [M] future phase specs. Proceed?"
Header: "Apply"
Options:
1. Apply all changes
2. Review the final annotations again before applying
3. Abort (no changes made)
```

### 10. Apply Approved Changes

After user approval:

1. **Update Future Phase Specs:**
   - Insert annotations at identified locations
   - Preserve all existing content
   - Do not modify any non-annotation content

2. **Update Parent Spec:**
   - Append Phase Retrospective section
   - Place after existing Review Resolution Log (or at end if none exists)

3. **Update Completed Phase Spec:**
   - Change `status:` in YAML frontmatter to `completed`

### 11. Summary Report

```
================================================================================
PHASE REVIEW COMPLETE
================================================================================

Completed Phase: [Phase N: Title]
  Status updated: proposed → completed

Decisions Propagated: [N]
  - Uncertainty Resolved: [X]
  - Scope Adjusted: [Y]
  - Pattern Discovered: [Z]
  - Constraint Identified: [W]
  - API Contract Defined: [V]

Future Phases Annotated:
  - Phase [M]: [A] annotations
  - Phase [P]: [B] annotations

Parent Spec Updated:
  - Phase Retrospective added to [parent path]

================================================================================

Next Steps:
  - Review annotated future phase specs before implementation
  - Run /dev:2:gen-tasks on next phase when ready to proceed
  - Consider /review:spec if annotations reveal significant gaps
================================================================================
```

## Decision-Making Guidelines

**Resolve autonomously when:**
- Decision is in the task file's Deviations Log (highest confidence)
- Decision is explicitly documented in handoff or commit message
- Implementation matches spec exactly (confirmation, not decision)
- API contract is clearly defined in code or tests
- Pattern follows existing codebase conventions

**Ask the user when:**
- Decision was inferred from git history (not in Deviations Log)
- Decision rationale is unclear or missing
- Decision contradicts future phase spec content
- Scope was reduced/deferred without explicit documentation
- Multiple interpretations of the decision are possible
- Decision affects requirements, not just implementation details

## Error Handling

### Completed Phase Not Found

```
Error: Completed phase spec not found at [path]

Please provide a valid path to a completed phase specification.
Example: /dev:5:phase-review thoughts/specs/phases/phase-1-workspace-routing-data-api.md
```

### Parent Spec Not Found

```
Error: Parent spec not found

Phase spec [path] references parent: [parent-path]
But this file does not exist.

Options:
1. Specify parent spec path manually with --parent [path]
2. Continue without parent spec update (--no-parent)
```

### No Future Phases Found

```
Warning: No future phases found

Searched for sibling phase files with higher phase numbers.
No phases found to propagate decisions to.

This may mean:
- This is the final phase
- Future phases haven't been created yet
- Phase files use unexpected naming

Options:
1. Specify future phase paths manually
2. Continue with parent spec update only
```

### No Implementation Evidence Found

```
Warning: No implementation evidence found for Phase [N]

Searched:
- Git commits mentioning "Phase [N]"
- thoughts/handoffs/ for related documents
- thoughts/plans/ for task list
- thoughts/validation/ for reports

This phase may not be complete. Options:
1. Proceed anyway (decisions may be incomplete)
2. Specify date range for git search with --since [date]
3. Abort and complete implementation first
```

### Future Phase Already Has Annotations

```
Warning: Future phase spec already contains propagated annotations

Phase [M] already has [X] annotations from previous propagations.

Options:
1. Add new annotations (existing preserved)
2. Replace all propagated annotations (remove existing)
3. Skip phases with existing annotations
```

## Options

### `--dry-run`

Preview all changes without applying:
- Show extracted decisions
- Show proposed annotations
- Show parent spec update
- No files modified

### `--no-parent`

Skip parent spec update:
- Only annotate future phase specs
- Useful when parent spec doesn't exist or shouldn't be modified

### `--auto-apply`

Apply all high-confidence changes without confirmation:
- Still prompts for low-confidence changes
- Useful for trusted/automated workflows

### `--since [date]`

Specify start date for git evidence search:
- Only search commits since specified date
- Format: YYYY-MM-DD
- Useful when phase implementation spans known date range

---

## Next Steps

After phase review completes:

- `/dev:2:gen-tasks` - Generate tasks for next phase (incorporates propagated decisions)
- `/review:spec` - Review future phase if annotations reveal gaps
- `/cmd:commit-push` - Commit propagated changes
