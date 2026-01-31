---
description: Launch parallel multi-agent task list review (Qwen, Kimi, DeepSeek)
argument-hint: <path to task list>
---

# Multi-Agent Task List Review

Orchestrate parallel task list reviews from Qwen3-Thinking, Kimi K2, and DeepSeek.

**Task list to review:** $ARGUMENTS

## Process

### 1. Validate Input

First, verify the task list file exists:
- Read the task list to confirm it's accessible
- Determine the **Source Specification** path using one of:

- YAML frontmatter key `spec:` (preferred)
- A "Source Specification:" line in the document body (fallback)
- Verify the source specification file exists and is readable
- Generate unique comment file paths for each reviewer:
  - `{task_path}.review-qwen.md`
  - `{task_path}.review-kimi.md`
  - `{task_path}.review-deepseek.md`

### 2. Check for Existing Review Files

Verify that no previous review session is in progress:
- Check if any `{task_path}.review-*.md` files already exist
- If found, warn the user that a previous review may be incomplete
- Get user confirmation before overwriting existing review files

### 3. Launch Parallel Reviews

Launch ALL THREE reviewers in parallel using a single message with multiple Task tool calls:

**Qwen3-Thinking Reviewer:**
```
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

**Kimi K2 Reviewer:**
```
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

**DeepSeek Reviewer:**
```
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

### 4. Wait for Completion

Wait for all three Task agents to complete. They will return when finished.

### 5. Extract Review Data

Read the comment files and count comments by reviewer:

```python
# Read comment files
qwen_content = read_file(qwen_comment_file) if file_exists(qwen_comment_file) else ""
kimi_content = read_file(kimi_comment_file) if file_exists(kimi_comment_file) else ""
deepseek_content = read_file(deepseek_comment_file) if file_exists(deepseek_comment_file) else ""

# Count comments per reviewer
qwen_count = qwen_content.count("[REVIEW:Qwen Reviewer]")
kimi_count = kimi_content.count("[REVIEW:Kimi Reviewer]")
deepseek_count = deepseek_content.count("[REVIEW:DeepSeek Reviewer]")
```

### 6. Identify Overlapping Concerns

Analyze comment line numbers to identify overlapping concerns from multiple reviewers:

```python
# Extract line numbers from comment format
def extract_lines(comment_content):
    pattern = r'\[REVIEW:(.*?)\] LINE (\d+):'
    return sorted([int(line) for _, line in re.findall(pattern, comment_content)])

qwen_lines = extract_lines(qwen_content)
kimi_lines = extract_lines(kimi_content)
deepseek_lines = extract_lines(deepseek_content)

# Find overlapping line ranges (within 50 lines)
overlap_threshold = 50
overlaps = []
for qwen_line in qwen_lines:
    for kimi_line in kimi_lines:
        if abs(qwen_line - kimi_line) < overlap_threshold:
            overlaps.append({
                "line_range": f"{min(qwen_line, kimi_line)}-{max(qwen_line, kimi_line)}",
                "reviewers": ["Qwen Reviewer", "Kimi Reviewer"]
            })

# Check Qwen<->DeepSeek overlaps
for qwen_line in qwen_lines:
    for deepseek_line in deepseek_lines:
        if abs(qwen_line - deepseek_line) < overlap_threshold:
            overlaps.append({
                "line_range": f"{min(qwen_line, deepseek_line)}-{max(qwen_line, deepseek_line)}",
                "reviewers": ["Qwen Reviewer", "DeepSeek Reviewer"]
            })

# Check Kimi<->DeepSeek overlaps
for kimi_line in kimi_lines:
    for deepseek_line in deepseek_lines:
        if abs(kimi_line - deepseek_line) < overlap_threshold:
            overlaps.append({
                "line_range": f"{min(kimi_line, deepseek_line)}-{max(kimi_line, deepseek_line)}",
                "reviewers": ["Kimi Reviewer", "DeepSeek Reviewer"]
            })

# Remove duplicates (same line range with same reviewers)
unique_overlaps = []
seen = set()
for overlap in overlaps:
    key = (overlap['line_range'], tuple(sorted(overlap['reviewers'])))
    if key not in seen:
        seen.add(key)
        unique_overlaps.append(overlap)
```

### 7. Report Results

After all reviewers complete, provide a summary:

```markdown
## Multi-Agent Task List Review Complete

**Task List:** {task-path}
**Source Specification:** {spec-path}
**Review Date:** {YYYY-MM-DD}

### Reviewer Status
| Reviewer | Status | Comments Added |
|----------|--------|----------------|
| Qwen3-Thinking  | {OK/Failed} | {N} |
| Kimi K2  | {OK/Failed} | {N} |
| DeepSeek | {OK/Failed} | {N} |

**Total Comments:** {N}

### Overlapping Concerns
{List line ranges where 2+ reviewers provided feedback in same area}

### Comment Categories
- INCORRECT: {N}
- SCOPE DRIFT: {N}
- MISINTERPRETATION: {N}
- CONTRADICTION: {N}
- WRONG REFERENCE: {N}

### Next Steps
Run `/review:tasks-integrate {task-path}` to:
- Integrate all corrections into the task list
- Resolve open questions
- Clean up comment files
```

## Error Handling

- If one reviewer fails, continue with others
- Report which reviewers completed successfully
- Integration can proceed with partial reviews (2 of 3 is acceptable)
- If source specification cannot be found or read, halt and inform user
- If comment files cannot be created, halt and inform user
- Original task list file is never modified during review

## Timeout Considerations

- Each Task agent uses default timeout
- No explicit timeout handling needed
- Parallel execution minimizes total wait time

---

## Next Command

After reviews complete, run:
```
/review:tasks-integrate <path to task list>
```

This command integrates all corrections into the task list and prepares it for implementation.
