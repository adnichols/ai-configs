---
description: Run a review-only change review using Claude Code through the canonical private-tmux interactive launcher
argument-hint: '[--claude-smoke] <existing-plan-path | plan slug | legacy: <spec> <tasks> | legacy: <directory containing spec.md and tasks.md>'
---

# Change Review via Claude Code

Run a read-only Claude Code review through the shared canonical launcher. Do not launch Claude Code directly from this prompt. Do not use `interactive_shell` for Claude, direct `process`/`bash` snippets, `claude -p` [FORBIDDEN-EXAMPLE], `claude --print` [FORBIDDEN-EXAMPLE], prompt piping, or any fallback transport.

Documents to review: $ARGUMENTS

## Smoke mode

If `$ARGUMENTS` is exactly `--claude-smoke`, run this from the current Pi prompt context and stop after reporting the result:

```bash
python3 "$HOME/.agents/skills/claude-code-review/scripts/claude_interactive_review.py" --smoke --cwd "$PWD" --review-name pi-review-change-smoke --output /tmp/pi-claude-review-smoke.txt
```

Pass condition:

```bash
rg -n -e CLAUDE_REVIEW_SMOKE_READY -e socket -e session /tmp/pi-claude-review-smoke.txt
```

Smoke failure is a prerequisite/auth/readiness blocker from the real Pi caller context. Preserve the output and inspect command. Do not retry with a different Claude transport.

## Review mode

This command is review-only and must use the canonical Claude Code launcher, which pins required Claude Code reviews to Opus 4.8 on Extra High.

Your reviewer name is `CLAUDE`.

Use this inline-comment-compatible format for material plan findings in Claude's returned review text:

```text
[REVIEW:CLAUDE] Your critical feedback here [/REVIEW]
```

To respond to other reviewers in returned review text:

```text
[REVIEW:CLAUDE] RE: [OtherReviewer] - Your response [/REVIEW]
```

The launcher is review-output-only. Claude must not edit the plan file directly; if inline plan comments are needed, report copyable `[REVIEW:CLAUDE] ... [/REVIEW]` comments in `/tmp/pi-claude-review-output.md`.

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
2. Write the Claude review prompt to `/tmp/pi-claude-review-prompt.txt`.
3. Run the shared launcher from the exact central path below as a single-line command, with no shell line continuations.
4. Read `/tmp/pi-claude-review-output.md` after completion and validate whether Claude found blocker-level issues.

```bash
python3 "$HOME/.agents/skills/claude-code-review/scripts/claude_interactive_review.py" --cwd "$PWD" --prompt-file /tmp/pi-claude-review-prompt.txt --output /tmp/pi-claude-review-output.md --review-name pi-review-change-claude --timeout-seconds 900
```

The prompt written to `/tmp/pi-claude-review-prompt.txt` should instruct Claude Code to:

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

After the launcher exits:

- read `/tmp/pi-claude-review-output.md`,
- if it begins with a classified launcher failure, report that blocker and the inspect/transcript path,
- otherwise inspect the plan and confirm structure remains intact,
- confirm any returned Claude comment suggestions use `[REVIEW:CLAUDE]`,
- report only material findings.

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
