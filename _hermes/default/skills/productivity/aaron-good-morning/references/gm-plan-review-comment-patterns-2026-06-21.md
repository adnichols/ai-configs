# GM plan-review comment patterns, 2026-06-21

Lessons from a Good Morning HTML artifact reviewed through plan-reviewer.

## Agent signals

- Reviewer feedback may identify old C-Core signals that should stop appearing. Use `ccore signal get <id> --json` to fetch `current_version_id`, then cancel stale signals with `ccore signal cancel <id> --expected-current-version-id <version_id> --json`.
- After cancellation, remove the item from the GM HTML and add a short note that it was cancelled so future `/gm` scans should not resurface it.
- For decision-candidate signals, do not only point to old Obsidian logs. Check C-Core equivalents:
  - `ccore query <space> "<decision/topic>" --limit 10 --json`
  - `ccore doc show <document_id> --space <space> --include-content`
  - `ccore decision list <space> --query "<topic>"`
- If a C-Core item exists only as a `decision_candidate` plus `signal`, say so explicitly and state whether an immutable `decision_record` exists.

## Recent inputs / transcripts

- If a transcript appears in Recent Inputs and the reviewer asks for context, summarize directly in the HTML artifact: how the call went, main topics, product/commercial fit signals, and follow-ups.

## Coding sessions

- Do not leave idle/incomplete coding sessions as a bare path list when reviewer asks for detail.
- Evidence sources, in order:
  1. AoE session list/status/capture for exact session IDs and last visible transcript.
  2. Plan/discovery artifacts in each session path.
  3. `git status --short --branch` and recent `git log` to identify untracked plans, reports, PR state, or release commits.
  4. **Cross-repo git merge inventory** — AoE session records alone are NOT sufficient for the Completed/Shipped section. Always run `git log --since="<yesterday> 00:00:00" --until="<today> 00:00:00" --merges --oneline --all` against every repo under `~/code/` that has a `.git` directory (heddle, plan-reviewer, doct, ccore-utils, agent-of-empires, etc.). This catches shipped PRs that AoE session state misses. Without this step the Completed/Shipped section will be inaccurate and Aaron will flag it.
- For each shipped PR, include: repo, PR number, title, branch, merge timestamp, merge commit hash, commit count, key files/surfaces touched, Linear issue linkage if any, and outcome summary.
- For each incomplete/idle session, include: session name, path, evidence source, where it left off, readiness state, untracked/modified artifacts, and next step/blocker.
- If Aaron labels an item as a placeholder/parking-lot, mark it as not moving forward and remove it from default resume recommendations.

## 2026-06-25 correction: incomplete Completed/Shipped inventory

- The initial GM run for Jun 25 stated "No sessions with new commits since Jun 24" but git logs showed 4 PRs merged in heddle and 7 PRs merged in plan-reviewer on Jun 24.
- Root cause: the Completed/Shipped section was built from AoE session records only, without scanning git merge logs across repos under `~/code/`.
- Fix: added evidence source 4 (cross-repo git merge inventory) above. Future GM runs must scan git logs in all repos under `~/code/` before writing the Completed/Shipped section.

## Plan-review claim recovery

- If a claim expires before ack, try to reclaim or check queue state. If resolve succeeds and returns resolved status, report the ack issue tersely and continue watching.
