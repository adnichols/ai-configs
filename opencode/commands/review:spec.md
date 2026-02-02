---
description: Provide critical feedback on a specification as inline comments
argument-hint: "<path to specification>"
---

# Multi-Model Specification Review

Review the specification document and provide critical feedback as HTML comments annotated with your identity.

**Specification to review:** $ARGUMENTS

## Your Identity

If you selected a reviewer subagent, use its friendly name for comment attribution. If no subagent is selected, use **OPENCODE** as the reviewer name.

## Process

### 0. Confirm Reviewer Identity

If a reviewer subagent is selected, use its friendly name for all comment labels. Otherwise use **OPENCODE**. Do not override a subagent-provided name.

### 1. Read the Specification

Read the specification file in full. Understand:
- The problem being solved
- The proposed solution
- Technical approach and architecture
- Success criteria and constraints

### 2. Explore Codebase for Context

Before providing feedback, explore the codebase to understand:
- Existing patterns and conventions that apply
- Related implementations that inform feasibility
- Potential conflicts or integration challenges
- Missing context that affects the specification

Use the Task tool with `subagent_type=Explore` to efficiently gather codebase context.

### 3. Ask Clarifying Questions

Before adding extensive comments, use the question tool to clarify ambiguities with the user. This minimizes back-and-forth in the document and drives clarity in the specification itself.

Ask about:
- Unclear requirements or scope
- Ambiguous technical decisions
- Missing constraints or assumptions
- Conflicting requirements

### 4. Add Critical Feedback as Comments

Insert review tags directly into the specification document. Format each comment as:

```markdown
[REVIEW:Reviewer Name] Your critical feedback here. Be specific and actionable. [/REVIEW]
```

### Comment Guidelines

**DO:**
- Identify missing requirements or edge cases
- Question technical feasibility based on codebase research
- Highlight potential integration issues
- Point out ambiguities that need clarification
- Suggest alternatives when you see problems
- Challenge assumptions that seem unfounded
- Note inconsistencies within the document

**DON'T:**
- Modify or delete comments from other reviewers
- Make purely stylistic suggestions
- Add praise or validation (focus on critical feedback)
- Rewrite sections (comment on what needs fixing)

### 5. Respond to Other Reviewers

If you see comments from other reviewers (Gemini, Codex, GPT, etc.), you may:
- Add your own comment agreeing or disagreeing with their feedback
- Provide additional context that supports or refutes their points
- Offer alternative perspectives on their concerns

Format responses to other reviewers:

```markdown
[REVIEW:Reviewer Name] RE: [OtherReviewer] - Your response to their comment [/REVIEW]
```

### 6. Summary

After adding all comments, provide a brief summary to the user:
- Number of comments added
- Major concerns identified
- Key questions that need resolution
- Recommended next steps

## Comment Placement

Place comments:
- **Inline** - immediately after the content they reference
- **At section headers** - for section-level concerns
- **At the end** - for document-wide or cross-cutting concerns

## Example Comments

```markdown
[REVIEW:Reviewer Name] This success criteria is not measurable. Consider adding specific
metrics like "response time < 200ms" or "support 1000 concurrent users". [/REVIEW]

[REVIEW:Reviewer Name] The security section doesn't address rate limiting. Based on
examining src/middleware/auth.ts, the existing auth middleware doesn't include
rate limiting - this needs to be explicitly addressed. [/REVIEW]

[REVIEW:Reviewer Name] RE: [Gemini] - I disagree that this is over-engineered. The
existing codebase in src/services/ follows this same pattern for similar
complexity features. [/REVIEW]
```

## Critical Mindset

Your role is to find problems, not validate the specification. Assume the spec has issues and look for:
- Gaps in requirements
- Unrealistic assumptions
- Technical debt creation
- Integration challenges
- Security or performance risks
- Unclear success criteria
- Missing error handling
- Scope creep or scope gaps

Be constructive but critical. The goal is to improve the specification before implementation begins.

---

## ➡️ Next Command

After all reviewers (Claude, Gemini, Codex, etc.) have completed their reviews, run:
```
/review:spec-integrate <path to specification>
```

This command integrates all feedback into the specification, resolves open questions, and prepares the spec for implementation.
