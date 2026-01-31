---
description: Integrate review feedback into an OpenSpec change (proposal/specs/design/tasks)
argument-hint: "<change name OR path to openspec/changes/<name>>"
---

# Integrate OpenSpec Change Review Feedback

Integrate inline reviewer comments across an OpenSpec change set into the change artifacts themselves, resolving open questions with user input.

**Change input:** $ARGUMENTS

## Process

### 0. Resolve the Change Directory

Resolve the OpenSpec change directory from `$ARGUMENTS`:

1. If `$ARGUMENTS` is a directory path and exists, use it.
2. Otherwise, treat `$ARGUMENTS` as a change name and use `openspec/changes/$ARGUMENTS`.
3. If neither exists, run `openspec list --json` and ask the user which change to integrate.

### 1. Read the Change Artifacts

Read (if present):
- `{change_dir}/proposal.md`
- All `{change_dir}/specs/*/spec.md`
- `{change_dir}/design.md`
- `{change_dir}/tasks.md`

Treat the delta specs in `{change_dir}/specs/*/spec.md` as the authority for correctness when fixing `tasks.md`.

### 2. Extract Inline Review Comments

Scan each artifact for inline review tags:

- Preferred format (section anchored):
  ```markdown
  [REVIEW:Reviewer Name] SECTION "Section Title": comment text [/REVIEW]
  ```
- Supported fallback:
  ```markdown
  [REVIEW:Reviewer Name] comment text [/REVIEW]
  ```

For `tasks.md` also support line anchored tags:

```markdown
[REVIEW:Reviewer Name] LINE 42: comment text [/REVIEW]
```

If no inline review comments exist across all artifacts, inform the user and abort.

### 3. Catalog All Concerns

Build a working list of concerns to address. For each:
- File (`proposal.md`, `design.md`, `specs/<capability>/spec.md`, `tasks.md`)
- Reviewer
- Anchor (SECTION "..." / LINE N / nearest header / nearest task line)
- Concern type (Missing requirement, Ambiguity, Feasibility, Scope drift, Incorrect task, etc.)
- Proposed resolution (if obvious)

### 4. Explore Codebase for Resolution Context

Before making decisions, gather codebase context for feasibility and conventions.
Use the Task tool with `subagent_type=Explore` to research as needed.

### 5. Triage by Confidence

For each concern:

High confidence (resolve autonomously):
- Codebase gives a definitive answer
- Clarifications are mechanical and non-controversial
- Corrections align directly with the delta specs

Low confidence (ask user):
- Business logic/scope decisions
- Competing trade-offs
- Delta specs are ambiguous
- Reviewers disagree

Batch low-confidence items into a single question tool call.

### 6. Integrate Resolutions

Update the artifacts in place:

**proposal/specs/design**
- Add missing detail
- Clarify ambiguous language
- Resolve inconsistencies
- Remove each original inline review comment once addressed

**tasks.md**
- Fix inaccuracies so tasks match the delta specs
- Remove scope-drift tasks or rewrite them to be in-scope
- Correct wrong references (paths/APIs/components)
- Remove each original inline review comment once addressed

Integration principles:
- Preserve each file's voice and structure
- Do not add new requirements beyond what the delta specs/proposal intend
- When uncertain, ask the user rather than guessing

### 7. Add a Review Resolution Log

Record decisions and outcomes in a single place.

Preferred location:
- Append a `## Review Resolution Log` section to `{change_dir}/design.md`.

If `design.md` does not exist:
- Append the log to `{change_dir}/proposal.md`.

The log should include:
- Date
- Files updated
- Key autonomous decisions (with brief rationale)
- User decisions (if any)
- Deferred items

### 8. Final Validation

Re-read the updated artifacts to ensure:
- No `[REVIEW:...]` comments remain
- `tasks.md` aligns with the delta specs
- Cross-file consistency (proposal/specs/design/tasks) is preserved

### 9. Summary Report

Report:
- Which files were updated
- Number of comments integrated (by file and reviewer)
- Key decisions made autonomously
- User decisions requested/used
- Confirmation that inline review comments were removed

---

## ➡️ Next Steps

STOP HERE. Do not automatically proceed to implementation.

After integration, the OpenSpec change is ready to continue via your normal workflow (e.g., `/opsx:continue`, `/opsx:apply`, etc.).
