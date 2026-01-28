---
description: Loop multi-agent review and integration until convergence (Ralph Wiggum)
argument-hint: "<path to task list>"
---

# Multi-Agent Review Loop (Ralph Wiggum)

Keep reviewing and integrating corrections until the task list converges (no new corrections).

**Task list to review:** $ARGUMENTS

## Configuration

- **Max iterations:** 5
- **Convergence criteria:** 0 corrections in an iteration
- **Reviewers:** Qwen3-Thinking, Kimi K2, DeepSeek

## Loop Process

### Initialization

1. Read the task list to confirm it exists
2. Extract the **Source Specification** path
3. Set `iteration = 1`
4. Set `total_corrections = 0`

### Iteration Loop (Repeat Until Convergence)

Display progress:
```
=== Iteration {iteration}/{max_iterations} ===
```

#### Step 1: Launch Multi-Agent Review

Follow the exact process from `/review:multi-tasks.md`:

**Generate unique comment file paths for this iteration:**
- `{task_path}.review-qwen.md`
- `{task_path}.review-kimi.md`
- `{task_path}.review-deepseek.md`

**Check for existing review files:**
- If `{task_path}.review-*.md` files exist, this indicates a previous incomplete review
- Delete them before starting this iteration

**Launch ALL THREE reviewers in parallel using Task tool:**

```python
Task(
  subagent_type="reviewer-qwen",
  description="Review task list with Qwen3-Thinking",
  prompt=f"""You are [Qwen Reviewer] reviewing a TASK LIST document.

**Task list to review:** {task_path}
**Source specification:** {spec_path}
**Comment file to write:** {qwen_comment_file}

**Review Process:**
1. Read the task list completely. Extract the source specification path from the task list header.
2. Read the source specification in full to understand:
   - The exact requirements as written
   - Technical decisions and constraints
   - Explicit scope boundaries
   - Success criteria
3. Compare the task list line-by-line against the specification. Look for:
   - INCORRECT: Factually wrong compared to spec (wrong paths, APIs, logic)
   - SCOPE DRIFT: Tasks that go beyond specification boundaries
   - MISINTERPRETATION: Tasks misunderstanding the spec's intent
   - CONTRADICTION: Task conflicts with another part of the spec
   - WRONG REFERENCE: File path, API, or component reference is wrong
4. Write critical feedback to the comment file at {qwen_comment_file}.
5. Format each comment as:
   [REVIEW:Qwen Reviewer] LINE {line_number}: INCORRECT: {explanation} [/REVIEW]
   [REVIEW:Qwen Reviewer] LINE {line_number}: SCOPE DRIFT: {explanation} [/REVIEW]
   [REVIEW:Qwen Reviewer] LINE {line_number}: MISINTERPRETATION: {explanation} [/REVIEW]
   [REVIEW:Qwen Reviewer] LINE {line_number}: CONTRADICTION: {explanation} [/REVIEW]
   [REVIEW:Qwen Reviewer] LINE {line_number}: WRONG REFERENCE: {explanation} [/REVIEW]
6. Replace {line_number} with the actual line number in the task list that your comment references.
7. Do NOT comment about missing tasks (those can be filled in from spec during implementation).
8. Do NOT modify or delete comments from other reviewers.
9. IMPORTANT: Do NOT modify the original task list file. Only write your comments to {qwen_comment_file}.
10. IMPORTANT: Write ALL your comments to a single file at {qwen_comment_file}.

This review is about accuracy, not completeness. Focus on details that would cause wrong implementations.

Return when you have completed your review and written all comments to {qwen_comment_file}."""
)
```

```python
Task(
  subagent_type="reviewer-kimi",
  description="Review task list with Kimi K2 thinking",
  prompt=f"""You are [Kimi Reviewer] reviewing a TASK LIST document.

**Task list to review:** {task_path}
**Source specification:** {spec_path}
**Comment file to write:** {kimi_comment_file}

**Review Process:**
1. Read the task list completely. Extract the source specification path from the task list header.
2. Read the source specification in full to understand:
   - The exact requirements as written
   - Technical decisions and constraints
   - Explicit scope boundaries
   - Success criteria
3. Compare the task list line-by-line against the specification. Look for:
   - INCORRECT: Factually wrong compared to spec (wrong paths, APIs, logic)
   - SCOPE DRIFT: Tasks that go beyond specification boundaries
   - MISINTERPRETATION: Tasks misunderstanding the spec's intent
   - CONTRADICTION: Task conflicts with another part of the spec
   - WRONG REFERENCE: File path, API, or component reference is wrong
4. Write critical feedback to the comment file at {kimi_comment_file}.
5. Format each comment as:
   [REVIEW:Kimi Reviewer] LINE {line_number}: INCORRECT: {explanation} [/REVIEW]
   [REVIEW:Kimi Reviewer] LINE {line_number}: SCOPE DRIFT: {explanation} [/REVIEW]
   [REVIEW:Kimi Reviewer] LINE {line_number}: MISINTERPRETATION: {explanation} [/REVIEW]
   [REVIEW:Kimi Reviewer] LINE {line_number}: CONTRADICTION: {explanation} [/REVIEW]
   [REVIEW:Kimi Reviewer] LINE {line_number}: WRONG REFERENCE: {explanation} [/REVIEW]
6. Replace {line_number} with the actual line number in the task list that your comment references.
7. Do NOT comment about missing tasks (those can be filled in from spec during implementation).
8. Do NOT modify or delete comments from other reviewers.
9. IMPORTANT: Do NOT modify the original task list file. Only write your comments to {kimi_comment_file}.
10. IMPORTANT: Write ALL your comments to a single file at {kimi_comment_file}.

This review is about accuracy, not completeness. Focus on details that would cause wrong implementations.

Return when you have completed your review and written all comments to {kimi_comment_file}."""
)
```

```python
Task(
  subagent_type="reviewer-deepseek",
  description="Review task list with DeepSeek",
  prompt=f"""You are [DeepSeek Reviewer] reviewing a TASK LIST document.

**Task list to review:** {task_path}
**Source specification:** {spec_path}
**Comment file to write:** {deepseek_comment_file}

**Review Process:**
1. Read the task list completely. Extract the source specification path from the task list header.
2. Read the source specification in full to understand:
   - The exact requirements as written
   - Technical decisions and constraints
   - Explicit scope boundaries
   - Success criteria
3. Compare the task list line-by-line against the specification. Look for:
   - INCORRECT: Factually wrong compared to spec (wrong paths, APIs, logic)
   - SCOPE DRIFT: Tasks that go beyond specification boundaries
   - MISINTERPRETATION: Tasks misunderstanding the spec's intent
   - CONTRADICTION: Task conflicts with another part of the spec
   - WRONG REFERENCE: File path, API, or component reference is wrong
4. Write critical feedback to the comment file at {deepseek_comment_file}.
5. Format each comment as:
   [REVIEW:DeepSeek Reviewer] LINE {line_number}: INCORRECT: {explanation} [/REVIEW]
   [REVIEW:DeepSeek Reviewer] LINE {line_number}: SCOPE DRIFT: {explanation} [/REVIEW]
   [REVIEW:DeepSeek Reviewer] LINE {line_number}: MISINTERPRETATION: {explanation} [/REVIEW]
   [REVIEW:DeepSeek Reviewer] LINE {line_number}: CONTRADICTION: {explanation} [/REVIEW]
   [REVIEW:DeepSeek Reviewer] LINE {line_number}: WRONG REFERENCE: {explanation} [/REVIEW]
6. Replace {line_number} with the actual line number in the task list that your comment references.
7. Do NOT comment about missing tasks (those can be filled in from spec during implementation).
8. Do NOT modify or delete comments from other reviewers.
9. IMPORTANT: Do NOT modify the original task list file. Only write your comments to {deepseek_comment_file}.
10. IMPORTANT: Write ALL your comments to a single file at {deepseek_comment_file}.

This review is about accuracy, not completeness. Focus on details that would cause wrong implementations.

Return when you have completed your review and written all comments to {deepseek_comment_file}."""
)
```

**Wait for all three Task agents to complete.**

#### Step 2: Count Corrections

Read the comment files and count total comments:

```python
qwen_content = read_file(qwen_comment_file) if file_exists(qwen_comment_file) else ""
kimi_content = read_file(kimi_comment_file) if file_exists(kimi_comment_file) else ""
deepseek_content = read_file(deepseek_comment_file) if file_exists(deepseek_comment_file) else ""

qwen_count = qwen_content.count("[REVIEW:Qwen Reviewer]")
kimi_count = kimi_content.count("[REVIEW:Kimi Reviewer]")
deepseek_count = deepseek_content.count("[REVIEW:DeepSeek Reviewer]")
iteration_corrections = qwen_count + kimi_count + deepseek_count
total_corrections += iteration_corrections
```

Display:
```
Corrections found: {iteration_corrections}
  Qwen: {qwen_count}
  Kimi: {kimi_count}
  DeepSeek: {deepseek_count}
```

#### Step 3: Check Convergence

If `iteration_corrections == 0`:
- **CONVERGED!** Exit the loop immediately
- Skip to "Final Summary"

If `iteration_corrections > 0`:
- Continue to integration step

#### Step 4: Integrate Corrections

Follow the exact process from `/review:tasks-integrate.md`:

**Read and catalog all comments:**
- Extract reviewer, line number, category, and content from each comment
- Create working list of inaccuracies to fix

**Read the task list and source specification:**
- Read task list for context and line locations
- Read source specification to determine correct content

**Verify each comment against spec:**
- Locate referenced section in specification
- Confirm comment validity
- Determine correct content based on spec

**Fix each inaccuracy:**
- Apply appropriate edit at specified line number
- INCORRECT: Rewrite task to match spec
- SCOPE DRIFT: Remove out-of-scope content
- MISINTERPRETATION: Rewrite to match spec intent
- WRONG REFERENCE: Correct file paths/APIs
- CONTRADICTION: Resolve to match specification

**Handle disputes:**
- Specification is final authority
- Ask user if spec is ambiguous

**Clean up temporary files:**
```bash
rm -f {task_path}.review-qwen.md
rm -f {task_path}.review-kimi.md
rm -f {task_path}.review-deepseek.md
```

Display:
```
✓ Corrections integrated
```

#### Step 5: Convergence Decision

If `iteration_corrections == 0`:
- Exit loop (converged)
- Skip to "Final Summary"

If `iteration_corrections > 0` AND `iteration < max_iterations`:
- Increment `iteration += 1`
- Continue to next iteration

If `iteration_corrections > 0` AND `iteration == max_iterations`:
- Ask user whether to continue

### Max Iterations Reached

When hitting iteration limit with corrections still being made:

Ask user:
```
⚠️  Maximum iterations reached (5) but task list hasn't converged.

Last iteration corrections: {iteration_corrections}
Total corrections across all iterations: {total_corrections}

Options:
1. Continue iterating (may consume more tokens)
2. Stop and accept current state

Continue? (y/n)
```

If user responds "y":
- Increment `iteration += 1`
- Continue loop

If user responds "n":
- Exit loop
- Proceed to "Final Summary"

## Final Summary

When loop completes:

```
=== Multi-Agent Review Loop Complete ===

Task List: {task-path}
Source Specification: {spec-path}
Total Iterations: {iteration}
Total Corrections: {total_corrections}
Status: {CONVERGED | STOPPED}

Final State:
{if converged} Task list achieved convergence (0 corrections in final iteration)
{if stopped} Task list stopped with N remaining corrections in last iteration

Per-Iteration Breakdown:
Iteration 1: N corrections
Iteration 2: N corrections
...

Next Steps:
{if converged} Task list ready for /dev:3:process-tasks
{if stopped} Review remaining issues manually or run additional iterations
```

## Important Notes

- **Always update the task list file** after each iteration
- **Track iteration count** to prevent infinite loops
- **Count comments accurately** to determine convergence
- **Delete comment files** after integrating (don't leave them)
- **Ask before continuing** at max iterations
- **Be brief** in chat output (detailed work happens in files)

## Example Usage

```
/review:multi-loop thoughts/plans/task-list.md
```

Will run up to 5 iterations of multi-agent review and integration until convergence.
