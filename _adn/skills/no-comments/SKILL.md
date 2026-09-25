---
name: no-comments
description: Run the independent Comment Sicko review and fix accepted comment findings.
---

ADN_RUNTIME_MARKER:no-comments:46756f89270d7e7dcb8c28c90fd0f957ade4ce2c

# No comments

Use the caller's named files or diff. Otherwise use the candidate diff against the base branch, default `main`, including staged and unstaged changes. Preserve unrelated work.

1. In OMP, use the native `task` tool with `agent: "comment-sicko"`. Do not pass a model override. Give exact paths or the comparison base, the comment-review lens, read-only authority, available verification evidence, and the PASS / FINDINGS / INCOMPLETE verdict contract. Wait for its report. Do not call Cursor `Task` or request `subagent_type`.
2. Check each finding against surrounding code and callers. Reject scope escapes and deletions of legal text, public API documentation, compatibility rationale, or unexplained constraints. Investigate ambiguous warnings and suppressions before removing them. Missing review evidence is INCOMPLETE, never a pass.
3. The driving agent applies accepted removals and the smallest authorized root-cause fixes. If a constraint can be encoded in types, validation, or a test within scope, do so and remove the redundant comment. Keep an accurate comment when encoding is deferred. Do not widen the task into an architectural rewrite.
4. Run affected checks after code changes. Report removals, corrections, kept constraints, verification, and unresolved findings. A review with nothing to remove is a valid result.
