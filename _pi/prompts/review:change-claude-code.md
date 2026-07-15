---
description: Run a review-only change review using the deterministic background Claude Code review tool
argument-hint: '[--claude-smoke] <existing-plan-path | plan slug | legacy: <spec> <tasks> | legacy: <directory containing spec.md and tasks.md>'
---

# Change Review via Claude Code

Run a read-only Claude Code review through the `claude_review` tool. Do not launch Claude Code or the canonical Python launcher through `bash`, `process`, `interactive_shell`, raw tmux, prompt piping, or another model provider.

Documents to review: $ARGUMENTS

## Smoke mode

If `$ARGUMENTS` is exactly `--claude-smoke`, call:

```text
claude_review({
  action: "smoke",
  cwd: "$PWD",
  output: "/tmp/pi-claude-review-smoke.txt"
})
```

The tool returns immediately and sends a completion notification while this session remains available. After reload/restart, recover the persisted job with `claude_review` list/status. Then read `/tmp/pi-claude-review-smoke.txt` and require `CLAUDE_REVIEW_SMOKE_READY`, `socket=`, and `session=`. A classified failure is a prerequisite/auth/readiness blocker from the real Pi caller context. Do not retry with a different transport.

## Review mode

This command is review-only. The canonical launcher owns Claude model, effort, interactive TUI, tmux, prompt extraction, and timeout behavior.

Your reviewer name is `CLAUDE`.

Use this inline-comment-compatible format for material plan findings in Claude's returned review text:

```text
[REVIEW:CLAUDE] Your critical feedback here [/REVIEW]
```

To respond to other reviewers in returned review text:

```text
[REVIEW:CLAUDE] RE: [OtherReviewer] - Your response [/REVIEW]
```

Claude must not edit the plan. If inline plan comments are needed, it returns copyable comments in `/tmp/pi-claude-review-output.md`.

## Scope

Review the provided plan as a cohesive unit. Decide whether it is ready to execute within its stated goal and non-goals. Flag only blockers, material risks, or missing decisions that would change execution readiness.

- This command is review-only.
- Do not integrate or rewrite the plan.
- For HTML plans, keep the HTML artifact authoritative and do not convert it to Markdown.
- Only return copyable inline `[REVIEW:CLAUDE] ... [/REVIEW]` comments when blocker-level feedback is needed.
- Do not remove or resolve review comments.
- Do not run follow-up integration commands.
- Do not comment on nice-to-haves, opportunistic cleanup, adjacent surfaces, or extra detail that would not change execution readiness.
- Do not delegate the Claude review to a subagent.

## Resolve inputs

- If `$ARGUMENTS` starts with `@`, strip the leading `@` and treat the rest as workspace-relative.
- If a single argument is an existing plan file, treat it as `plan_path`.
- If a single argument is a slug, resolve it using repo-local active plan guidance. Do not infer a Markdown path.
- Accept legacy `<spec_path> <tasks_path>` or a directory containing `spec.md` and `tasks.md` only when repo-local guidance explicitly allows migration.
- If multiple candidates match or a required file is missing, ask for an explicit plan file path.

## Launch

1. Resolve the plan path.
2. Write the bounded read-only Claude prompt to `/tmp/pi-claude-review-prompt.txt`.
3. Call:

```text
claude_review({
  action: "start",
  cwd: "$PWD",
  promptFile: "/tmp/pi-claude-review-prompt.txt",
  output: "/tmp/pi-claude-review-output.md"
})
```

4. Continue other work; do not poll while this session remains active.
5. On the automatic completion notification, read `/tmp/pi-claude-review-output.md`. If this session was reloaded, replaced, or restarted first, recover the persisted job with `claude_review` list/status and then read the artifact.
6. Treat launcher artifact validity and this workflow's readiness decision as separate checks: a review can be valid transport without using a literal `VERDICT:` line.

The prompt should instruct Claude Code to:

- inspect the target plan,
- look only for blockers, material risks, missing decisions, incorrect references, scope drift, or execution-readiness defects,
- check that unchecked phases are bounded execution slices with `End State`, `Tests first`, `Work`, `Expected files`, and `Verify`,
- flag unresolved `Open Questions` / `Decision Points` in execution-ready plans,
- flag phases that are too large for same-scope execution,
- return copyable inline review comments only where readiness changes materially,
- preserve plan structure and progress state by not editing files,
- not rewrite, integrate, or resolve comments,
- stop after the review summary.

## Validate result

After completion:

- read `/tmp/pi-claude-review-output.md`,
- first validate transport: successful launcher completion, non-empty normalized review text, launcher metadata (`CLAUDE_REVIEW_LAUNCHER_METADATA`, `socket=`, and `session=`), and no classified launcher/provider failure,
- do not require a literal `VERDICT:` line for transport validity; interpret Claude's blocker findings under this command's summary format,
- if the job or artifact reports a classified launcher failure, report that blocker and the inspect/transcript/log paths,
- otherwise inspect the plan and confirm structure remains intact,
- confirm returned Claude comment suggestions use `[REVIEW:CLAUDE]`,
- report only material findings.

A missing or malformed artifact is review infrastructure failure even when the child process exited zero.

## Summary format

```text
## Review Complete

### Claude Material Findings:
- [List blocker-level or readiness-changing Claude findings, or say none]

### Plan Status:
[Ready as scoped / Needs rework]

### Recommendation:
[Proceed as scoped / Major revision needed]
```
