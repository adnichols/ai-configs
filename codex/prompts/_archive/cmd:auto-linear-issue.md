---
description: Fully execute a Linear issue autonomously from worktree setup through PR submission. Usage: ISSUE_KEY [BASE_BRANCH]
---

Stand up a dedicated worktree for the given Linear issue and carry the fix to completion with minimal operator interaction. Accept the Linear issue key as the first argument (for example `NOD-123`). Optionally accept a second argument that overrides the default base branch (`origin/main`).

Also follow this repository's `AGENTS.md` for project-specific branching, testing, and deployment rules.

Linear issue: $ARGUMENTS

## Inputs & Preconditions

- Require at least one argument; fail fast with clear usage guidance if missing.
- Verify the repository root (`git rev-parse --show-toplevel`) has no staged or unstaged changes; halt and ask the operator to clean up if dirty.
- Run `git fetch --prune --tags` before branching to avoid stale bases.
- Retrieve full Linear issue metadata via ltui (title, description, project, status, labels) using `ltui issues view <ISSUE_KEY> --format detail`.
- If `.ltui.json` exists in the repo root and specifies a `project`, verify the issue belongs to that project; warn if not but allow proceeding with confirmation.
- If no project is configured, skip project validation.
- Parse the detail output to extract all fields and the Linear issue URL for later status updates and PR descriptions.

## Branch & Worktree Creation

1. Branch name: `issue/<issue-key-lower>`.
3. Compute repo root and parent; define worktree path `<repo-parent>/<repo-name>-<issue-key-lower>`. Never nest under an existing Git repository.
   - If the path already exists as a worktree for this branch, prune/reset via `git worktree remove --force` or fast-forward.
   - If the path exists but is unrelated, halt and ask the operator how to proceed.
   - Validate the target path is outside any Git repo (`git -C <path> rev-parse` should fail).
4. Create the worktree: `git worktree add --track -b <branch> <worktree-path> <base-ref>` where `<base-ref>` defaults to `origin/main` or the supplied override.
5. Inside the new worktree, set upstream tracking and confirm `git status` is clean.

## Propagate Local Configuration

- Discover ignored-but-present assets to mirror into the worktree:
  - All `.env*` variants (e.g., `.env`, `.env.local`, `.env.test.local`, `.env.development`)
  - `.envrc`
  - `*.local` or `*.local.*` under `config/`, `settings/`, `scripts/`
  - `*.private.*`, `docker-compose.override.yml`, `package-lock.private.json`
- Use `find` plus `git check-ignore -vq` to detect candidates; copy with `rsync -avh --relative` and preserve permissions (`chmod --reference`).
- Re-run `direnv allow` when `.envrc` is copied. Log every copied path; warn (not fail) if expected env files mentioned in docs are missing.
- <critical_instruction>Change directory into the new worktree - ALL future work should take place inside the worktree </critical>

## Linear Context Capture

- Create `tasks/<issue-key-lower>.md` in the worktree summarizing issue metadata, acceptance criteria, branch, worktree path, base ref, and timestamp.
- Track open questions and assumptions in the note as work progresses.

## Autonomous Execution Flow

1. **Orientation**
   - Parse the Linear description, attachments, and comments into explicit requirements, acceptance criteria, non-goals, and test expectations.
   - Identify referenced files, components, or endpoints via `rg`, repository docs, or previous commits.
   - Draft a short execution plan (tasks, validations) in the worktree note; keep it updated.
2. **Implementation Loop**
   - Execute tasks sequentially using repo standards (consult `CLAUDE.md`, `TESTING.md`, `AGENTS.md`).
   - Implement code changes directly in the worktree; do not pause for human approval unless blocked.
   - Maintain incremental commits logically grouped or a single commit at the end per repo conventions.
3. **Validation**
   - Run required checks (tests, linters, builds). Prioritize commands specified in repo docs or the Linear issue.
   - If a check fails, remediate and rerun until clean or until three attempts fail; on repeated failure, pause and surface diagnostics to the operator while leaving the workspace intact.
4. **Documentation & Status Updates**
   - Update the worktree note with implementation summary, commands run, and remaining risks.
   - Post a draft update to Linear using `ltui issues comment <ISSUE_KEY> --body "<comment-text>"` summarizing progress when major milestones complete or a blocker arises.

## Completion & Hand-off

- Stage and commit changes using a conventional commit message referencing the Linear key (e.g., `git commit -m "fix: resolve <short description>" -m "Refs <ISSUE_KEY>"`).
- Push the branch (`git push -u origin <branch>`). Handle force-push only if branch already exists and operator consent is implicit.
- Auto-create a pull request (GitHub CLI or equivalent) with:
  - Title `[<ISSUE_KEY>] <Linear title>`
  - Body including summary, validation commands, checklist of acceptance criteria, and Linear issue URL.
- Transition the Linear issue state to "In Review" using `ltui issues update <ISSUE_KEY> --state "In Review"` and add a comment linking the PR with `ltui issues comment <ISSUE_KEY> --body "PR: <url>"` or `ltui issues link <ISSUE_KEY> --url <pr-url> --title "PR #<number>"`.
- Present a final Codex summary: branch, PR URL, test results, remaining concerns. If work is incomplete, clearly outline blockers and leave the issue in the appropriate Linear state without creating a PR.
- Keep the primary repo pristine aside from worktree metadata and pushed branch.
