---
description: Deterministically bootstrap a dedicated worktree and exact issue branch for a Linear issue
argument-hint: "ISSUE_KEY [BASE_BRANCH]"
---

# Start Linear Issue (Direct Worktree Workflow)

Execute this workflow directly with Git, filesystem, JSON-reading, and `ltui` tools. Do not delegate repository management or worktree creation to any subagent.

**Arguments**: `$ARGUMENTS`

## 1. Parse and Validate Arguments

- First argument: `ISSUE_KEY` (required), matching `^[A-Za-z][A-Za-z0-9]*-[0-9]+$` (for example `NOD-123`).
- Second argument: `BASE_BRANCH` (optional), default `origin/main`.
- Reject extra arguments.

If the issue key is missing or invalid, stop with:

```text
Usage: /cmd:start-linear-issue ISSUE_KEY [BASE_BRANCH]
Examples:
  /cmd:start-linear-issue NOD-123
  /cmd:start-linear-issue NOD-123 origin/develop
```

Normalize `ISSUE_KEY` to uppercase for the Linear lookup. Derive `ISSUE_LOWER` by lowercasing that exact key. The branch name must be exactly `ISSUE_LOWER`; never append the title.

## 2. Validate the Current Repository and Clean Tree

Resolve `REPO_ROOT` with `git rev-parse --show-toplevel`. Stop if not in a Git worktree.

Run:

```bash
git status --porcelain=v1
```

If output is non-empty, stop and report that the current tree must be committed or stashed. Do not mutate anything.

Then fetch:

```bash
git fetch --prune --tags
```

Validate `BASE_REF` (the supplied base or `origin/main`) with:

```bash
git rev-parse --verify "${BASE_REF}^{commit}"
```

Stop with the failing ref and ask for a valid base if it cannot be resolved.

## 3. Read Linear Metadata

Run exactly:

```bash
ltui issues view "${ISSUE_KEY}" --format detail
```

Parse and retain these issue fields from the structured detail output:

- Title
- Project
- State
- Description between `DESCRIPTION_START` and `DESCRIPTION_END`
- URL

Stop if the command fails or any of Title, Project, State, or URL is unavailable. Preserve an empty description as empty rather than inventing one.

If `.ltui.json` exists at `REPO_ROOT`, parse it as JSON. If it contains a non-empty `project` and that value does not exactly match the issue Project, stop before creating a branch or worktree and ask the user to confirm whether to proceed despite the mismatch. Report both project values. Continue only after explicit confirmation; do not treat silence as approval.

## 4. Derive Exact Branch and Sibling Path

Compute without title slugging:

```bash
REPO_NAME=$(basename "$REPO_ROOT")
REPO_PARENT=$(dirname "$REPO_ROOT")
ISSUE_LOWER=$(printf '%s' "$ISSUE_KEY" | tr '[:upper:]' '[:lower:]')
BRANCH_NAME="$ISSUE_LOWER"
WORKTREE_PATH="$REPO_PARENT/${REPO_NAME}-${ISSUE_LOWER}"
BASE_REF="${BASE_BRANCH:-origin/main}"
```

Before mutation, fail closed if any of these are true:

- local branch `refs/heads/${BRANCH_NAME}` exists,
- remote-tracking branch `refs/remotes/origin/${BRANCH_NAME}` exists,
- `WORKTREE_PATH` exists as any filesystem entry,
- `git worktree list --porcelain` already records that path or branch.

Report the exact conflicting branch/path/worktree. Offer explicit recovery choices such as: use the existing worktree, choose a different issue, manually rename/remove the conflicting branch, or manually remove a stale worktree after inspecting it. Never force-remove, overwrite, reset, or delete user work.

## 5. Create Tracking Worktree

Create the branch and worktree from the validated base:

```bash
git worktree add --track -b "$BRANCH_NAME" "$WORKTREE_PATH" "$BASE_REF"
```

Then, from `WORKTREE_PATH`, set its upstream to the remote branch represented by `BASE_REF` when `BASE_REF` is a remote-tracking ref (default `origin/main`):

```bash
git -C "$WORKTREE_PATH" branch --set-upstream-to="$BASE_REF" "$BRANCH_NAME"
git -C "$WORKTREE_PATH" status --short --branch
```

If the supplied base cannot be used as an upstream (for example a local commit/ref without a remote-tracking branch), keep the created worktree, report that upstream setup failed, and give explicit commands to inspect and set the intended upstream. Do not guess or delete the worktree.

## 6. Write the Linear Context Note

Create `WORKTREE_PATH/thoughts/linear/${ISSUE_LOWER}.md` and its parent directory. Write exactly one context note containing the fetched values and derived state:

```markdown
# <ISSUE_KEY>: <Title>

**URL**: <Linear URL>
**Project**: <Project>
**State**: <State>
**Branch**: <issue-lower>
**Worktree**: <absolute worktree path>
**Base**: <base ref>
**Created**: <ISO-8601 timestamp>

## Description

<description from Linear>
```

Do not change application code or any other repository file.

## 7. Bootstrap delivery navigator (soft, best-effort, explicit opt-in only)

Do **not** arm or initialize the delivery workflow for a generic
`/cmd:start-linear-issue` request. Only when the operator explicitly asked to
use the delivery workflow (or explicitly asked to arm/start delivery for this
issue) does the following apply. In that case, if the `delivery` CLI is
available (`command -v delivery` or `~/.agents/skills/delivery-run/scripts/delivery`), initialize the per-worktree delivery ledger and agent brief so a newly spawned Herdr agent can navigate without prior chat context. Otherwise, skip delivery bootstrap entirely and do not create a `.delivery/ledger.json`.

```bash
DELIVERY_BIN="$(command -v delivery || true)"
if [[ -z "$DELIVERY_BIN" && -x "$HOME/.agents/skills/delivery-run/scripts/delivery" ]]; then
  DELIVERY_BIN="$HOME/.agents/skills/delivery-run/scripts/delivery"
fi
if [[ -n "$DELIVERY_BIN" ]]; then
  DELIVERY_SKIP_HERDR=1 "$DELIVERY_BIN" --cwd "$WORKTREE_PATH" bootstrap \
    --issue "$ISSUE_KEY" \
    --goal "$ISSUE_KEY: $TITLE" \
    --stage INTAKE
fi
```

This is guidance only. If `delivery` is missing or bootstrap fails, continue and report that delivery bootstrap was skipped — do not fail the worktree creation.

## 8. Report

Report:

```text
Worktree created successfully!

Location: <absolute worktree path>
Branch: <exact issue-lower branch>
Linear: <issue URL>
Context note: <absolute or worktree-relative note path>
Delivery brief: <worktree>/.delivery/AGENT_BRIEF.md (or skipped)
Base/upstream: <base ref and upstream status>

Suggested commands:
- cd <worktree path>
- delivery show && delivery check -v
- /delivery:bootstrap   # if spawning a fresh agent in this worktree
- git status
- <repo-specific install/test command only if directly evidenced by repo files>

Suggested first prompt for a new Herdr agent in this worktree:
You are in worktree <path> for <ISSUE_KEY>. Read .delivery/AGENT_BRIEF.md, run delivery show && delivery check -v, then continue from the recommended next step through plan ↔ review → run-plan → autoreview → PR. Guidance not gates.
```

Do not switch the caller's current process directory implicitly. Suggestions must be evidence-based; omit install/test commands when uncertain.

## Failure Contract

Fail closed at the first unsafe or ambiguous condition. Report the completed steps, exact failure, current branch/worktree state, and explicit non-destructive recovery choices. Never force-remove a branch or worktree, overwrite an existing path, clean/reset user files, or delegate repository management.
