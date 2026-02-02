---
description: Integrate spec review comments into the specification
argument-hint: "<path to specification>"
---

# Integrate Specification Review Comments

Integrate all inline reviewer comments in a specification into the specification itself, resolving all open questions and concerns.

**Specification to integrate:** $ARGUMENTS

## Process

### 1. Read the Specification

Read the specification file to understand the full context and to locate inline review comments.

### 2. Extract Inline Comments

Scan the specification for inline review tags using the reviewer format:

- Preferred format with explicit section:
  ```markdown
  [REVIEW:Reviewer Name] SECTION "Section Title": comment text [/REVIEW]
  ```
- Supported fallback without explicit section:
  ```markdown
  [REVIEW:Reviewer Name] comment text [/REVIEW]
  ```

For comments without a section marker, associate the comment with the nearest following section header.

If no inline review comments exist, inform the user that no review data was found and abort.

### 3. Read and Catalog All Comments

From the inline comments, extract all reviewer feedback and parse each comment to extract:
- **Reviewer**: The reviewer name from the comment prefix
- **Section**: `SECTION "..."` when present, otherwise nearest following header
- **Content**: The actual comment feedback

Create a working list of all feedback items to address.

### 4. Explore Codebase for Resolution Context

Before resolving comments, gather codebase context that informs decisions:
- Existing patterns that answer feasibility questions
- Related implementations that inform technical decisions
- Constraints or conventions that resolve ambiguities

Use the Task tool with `subagent_type=Explore` to efficiently research.

### 5. Triage Comments by Confidence

For each comment, determine your confidence level in resolving it:

**High Confidence (Resolve Autonomously):**
- Clear technical questions with definitive answers from codebase research
- Missing details that have obvious correct answers
- Concerns already addressed elsewhere in the spec
- Suggestions that align with established patterns
- Inconsistencies with clear resolutions

**Low Confidence (Ask User):**
- Business logic decisions with multiple valid options
- Scope decisions (include/exclude features)
- Priority or phasing decisions
- Trade-offs between competing concerns
- Requirements that need stakeholder input
- Ambiguities where codebase doesn't provide guidance

### 6. Batch User Questions

Collect all low-confidence items and ask the user. Group related questions together. For each question:
- Provide context from the reviewer comments
- Explain the options or trade-offs
- Indicate which reviewers raised the concern
- Suggest a recommendation if you have one

Example:
```
Multiple reviewers raised concerns about error handling scope:

[Reviewer] SECTION "Error Handling": Should we handle network timeouts differently from API errors?
[Reviewer] noted: Error retry logic not specified - is this in scope?

Options:
A) Unified error handling - treat all errors the same way
B) Differentiated handling - separate strategies for network vs API errors
C) Defer to existing patterns - use whatever error handling exists in codebase

Recommendation: B seems appropriate given the complexity, but this affects scope.
```

### 7. Integrate Resolutions

For each resolved comment:

1. **Locate the section** in the specification that was referenced
2. **Update the specification** - Insert a review tag at the beginning of the referenced section with the integrated feedback:
   ````markdown
   [REVIEW:Integrated {reviewer_name} feedback] {resolved feedback} [/REVIEW]
   ````
3. **Add clarifying content** - Where comments identified gaps, add the missing information to the specification text
4. **Modify the relevant section** - Update to address the feedback directly in the section content
5. **Remove the original inline comment** - Delete the resolved inline review comment from the spec

Integration principles:
- Preserve the spec's voice and structure
- Add detail where reviewers identified gaps
- Clarify ambiguous language
- Add constraints or requirements that were missing
- Update technical approach based on feasibility feedback

### 8. Document Decisions

At the end of the specification, add or update a "Review Resolution Log" section:

```markdown
## Review Resolution Log

### Integrated Feedback - [Date]

**Reviewers:** {Reviewer Name}

**Key Decisions Made:**
- [Decision 1]: [Rationale]
- [Decision 2]: [Rationale]

**User Decisions:**
- [Question]: [User's decision]

**Deferred Items:**
- [Item]: [Reason for deferral]
```

### 9. Final Validation

After integration:
- Re-read the full specification for coherence
- Verify all sections referenced in comments have been addressed
- Check that all reviewer concerns are addressed
- Ensure the spec is internally consistent

### 10. Summary Report

Provide the user with:
- Number of comments integrated
- Number of comments by reviewer name
- Key decisions made autonomously (with brief rationale)
- Decisions made based on user input
- Confirmation that inline review comments were removed
- Confirmation that spec is ready for next phase

## Decision-Making Guidelines

**Resolve autonomously when:**
- The codebase clearly indicates the correct approach
- Industry best practices apply unambiguously
- The concern is about clarity, not direction
- One option is clearly superior given constraints
- The feedback is about missing detail, not missing decisions

**Ask the user when:**
- Multiple valid approaches exist with real trade-offs
- The decision affects scope, timeline, or resources
- Business logic is involved
- You're genuinely uncertain
- Reviewers disagreed and both have valid points

## Output

The specification file should be updated in place with:
- All feedback integrated from inline review comments
- Review Resolution Log added/updated
- Clean, coherent specification ready for implementation

The inline review comments should be deleted after successful integration. If integration fails, keep the inline comments for debugging.

---

## ➡️ Next Steps

After integration completes, the specification is ready for:
- `/spec:2:gen-tasks` - Generate implementation tasks
- Additional review cycles if significant changes were made
