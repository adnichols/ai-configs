---
description: Review an OpenSpec change (proposal/specs/design/tasks) as inline comments
argument-hint: "<change name OR path to openspec/changes/<name>>"
---

# OpenSpec Change Review

Review an OpenSpec change set and provide critical feedback as inline review tags across the change artifacts.

**Change input:** $ARGUMENTS

## Your Identity

If you selected a reviewer subagent, use its friendly name for comment attribution. If no subagent is selected, use **OPENCODE** as the reviewer name.

## Scope

Review the change as a set:
- `proposal.md`
- `specs/*/spec.md` (delta specs)
- `design.md`
- `tasks.md`

## Process

### 0. Resolve the Change Directory

Resolve the OpenSpec change directory from `$ARGUMENTS`:

1. If `$ARGUMENTS` is a directory path and exists, use it.
2. Otherwise, treat `$ARGUMENTS` as a change name and use `openspec/changes/$ARGUMENTS`.
3. If neither exists, run `openspec list --json` and ask the user which change to review.

### 1. Read the Change Artifacts

Read (if present):
- `{change_dir}/proposal.md`
- All `{change_dir}/specs/*/spec.md`
- `{change_dir}/design.md`
- `{change_dir}/tasks.md`

If an expected file is missing, note it in your response, but continue with what exists.

### 2. Explore Codebase for Context

Before adding feedback, explore the codebase to understand:
- Existing patterns and conventions that apply
- Related implementations that inform feasibility
- Potential conflicts or integration challenges

Use the Task tool with `subagent_type=explore` to efficiently gather codebase context.

### 3. Ask Clarifying Questions (Only If Needed)

If the change contains ambiguities that block meaningful review, ask 1-4 clarifying questions using the question tool.

### 4. Add Critical Feedback as Inline Review Tags

Insert review tags directly into the artifact files.

Preferred format (helps integration place the comment correctly):

```markdown
[REVIEW:Reviewer Name] SECTION "Section Title": Your critical feedback here. Be specific and actionable. [/REVIEW]
```

For `tasks.md`, prefer line-referenced tags:

```markdown
[REVIEW:Reviewer Name] LINE 42: INCORRECT: Task says X but delta specs require Y. [/REVIEW]
```

If you cannot confidently reference an exact line number, omit `LINE` and place the comment immediately after the task item.

### Comment Guidelines

DO:
- Identify missing requirements, edge cases, and unclear success criteria
- Question technical feasibility based on codebase research
- Highlight integration issues and contradictions across artifacts
- Flag scope drift between `tasks.md` and `specs/*/spec.md`

DON'T:
- Rewrite sections (comment on what needs fixing)
- Modify or delete other reviewers' comments
- Add praise or validation (stay critical)

### 5. Summary

After adding all comments, provide a brief summary:
- Which artifact files you reviewed
- Number of comments added per file
- Major concerns identified
- Key questions that need resolution

---

## ➡️ Next Steps

STOP HERE. Do not automatically proceed to integration.

Inform the user that when they are ready to integrate all review feedback into the OpenSpec change artifacts, they can run:

```
/review:openspec-integrate <change name OR path to openspec/changes/<name>>
```
