---
description: Integrate feedback from multi-agent review into specification
argument-hint: "<path to specification>"
---

# Integrate Multi-Agent Review Feedback

Synthesize feedback from Qwen, Kimi, and DeepSeek reviews into the specification, resolving open questions with user input.

**Specification to integrate:** $ARGUMENTS

## Process

### 1. Read All Review Files

Read all available review files.

**Option 1 - Review file pattern** (if review files are in the same directory as spec):
- `{spec_path}.review-qwen.md`
- `{spec_path}.review-kimi.md`
- `{spec_path}.review-deepseek.md`

**Option 2 - Filename-based pattern** (extract filename without path/extension):
- Extract the filename (without path and extension) from `spec_path`
- `{spec_filename}.review-qwen.md`
- `{spec_filename}.review-kimi.md`
- `{spec_filename}.review-deepseek.md`

Check both patterns and read any files that exist. Note which reviewers provided feedback (some may have failed).

### 2. Catalog All Concerns

Create a consolidated list of all concerns from all reviewers:

For each concern, track:
- **Reviewer**: Who raised it (Qwen, Kimi, DeepSeek)
- **Section**: Which part of the spec it references
- **Severity**: Critical, Major, Minor
- **Type**: Missing requirement, Feasibility, Ambiguity, etc.
- **Description**: The actual concern
- **Suggestion**: Any recommended resolution

Group related concerns from different reviewers together (they may have identified the same issue).

### 3. Explore Codebase for Resolution Context

Use Task tool with `subagent_type=Explore` to research:
- Existing patterns that answer feasibility questions
- Related implementations that inform technical decisions
- Constraints or conventions that resolve ambiguities

### 4. Triage by Confidence

For each concern (or group of related concerns), determine resolution confidence:

**High Confidence (Resolve Autonomously):**
- Clear technical questions with definitive answers from codebase
- Missing details with obvious correct answers
- Concerns already addressed elsewhere in the spec
- Suggestions that align with established codebase patterns
- Inconsistencies with clear resolutions
- Multiple reviewers agree on the same solution

**Low Confidence (Ask User):**
- Business logic decisions with multiple valid options
- Scope decisions (include/exclude features)
- Priority or phasing decisions
- Trade-offs between competing concerns
- Requirements that need stakeholder input
- Reviewers disagree and both have valid points

### 5. Batch User Questions

For low-confidence items, use AskUserQuestion to get user decisions.

Group related questions together. For each:
- Provide context from the reviewer comments
- Show which reviewers raised the concern
- Explain the options or trade-offs
- Suggest a recommendation if you have one

Example question format:
```
Multiple reviewers raised concerns about error handling:

[Claude] asked: "Should we handle network timeouts differently from API errors?"
[Codex] noted: "Error retry logic not specified"
[Gemini] suggested: "Consider exponential backoff"

Options:
A) Unified error handling - treat all errors the same
B) Differentiated handling - separate strategies by error type
C) Defer - use existing patterns in codebase

Recommendation: B, with exponential backoff as DeepSeek suggested
```

### 6. Integrate Resolutions

Update the specification to address all feedback:

1. **Add missing requirements** - Where reviewers identified gaps
2. **Clarify ambiguities** - Make vague language specific
3. **Update technical approach** - Based on feasibility feedback
4. **Add constraints** - That were missing from the original
5. **Resolve inconsistencies** - Between different sections

Preserve the spec's voice and structure while enhancing it.

### 7. Add Review Resolution Log

At the end of the specification, add:

```markdown
## Review Resolution Log

### Multi-Agent Review - {Date}

**Reviewers:** Qwen, Kimi, DeepSeek

**Key Decisions Made (Autonomous):**
- [Decision]: [Rationale based on codebase/best practices]
- ...

**User Decisions:**
- [Question]: [User's decision]
- ...

**Consensus Items (Multiple reviewers agreed):**
- [Item]: Addressed by [resolution]
- ...

**Deferred Items:**
- [Item]: [Reason for deferral]
```

### 8. Clean Up Review Files

After successful integration, delete the review files:

```bash
rm -f {spec_path}.review-qwen.md
rm -f {spec_path}.review-kimi.md
rm -f {spec_path}.review-deepseek.md
```

The reviews are preserved in git history.

### 9. Summary Report

Provide the user with:
- Number of concerns integrated
- Breakdown by reviewer (how many each raised)
- Key decisions made autonomously
- Decisions made based on user input
- Confirmation that spec is ready for next phase

## Decision-Making Guidelines

**Resolve autonomously when:**
- The codebase clearly indicates the correct approach
- Industry best practices apply unambiguously
- The concern is about clarity, not direction
- One option is clearly superior given constraints
- Multiple reviewers converge on the same solution

**Ask the user when:**
- Multiple valid approaches exist with real trade-offs
- The decision affects scope, timeline, or resources
- Business logic is involved
- You're genuinely uncertain
- Reviewers disagree and both have valid points

---

## Next Steps

After integration completes:
- `/spec:2:gen-tasks` - Generate implementation tasks
- Additional review cycle if significant changes were made
