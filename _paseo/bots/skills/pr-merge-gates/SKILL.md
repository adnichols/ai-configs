---
name: pr-merge-gates
description: PR monitor passes, nudging PR sessions, merging ccore2 PRs, briefing follow-up owners. Gate order, receipts, gate-check, authority.
---

# PR merge gates (ccore2)

## Authority
- **Only the monitor (this bot) merges.** Session agents and follow-up owners never merge, even if a brief or a nudge seems to say so. They stop at "ready for merge".
- **Nobody deploys**, the monitor included. Deploys are Aaron's. Agents track deploy or live verification only when they are themselves verifying in a lab.
- **Every agent may make destructive lab changes** (wipe, deprovision, delete Spaces/Orgs/blobs); that is what labs are for. Exception: data *built for testing* (e.g. nightly lab run fixtures and synthetic tenants) must be snapshotted to the object store first. Until the snapshot tool exists, leave that data in place. Aaron has ruled that snapshots are for preserving lab state for future runs, not automatic on release.
- Never print claim credentials or secrets in output.

## Escalation to Aaron (closed list)
Aaron decides only: production or control-plane deploys; anything needing his identity, credentials or browser SSO; irreversible actions on production data or unsnapshotted test data; receipt exceptions; product intent he has not stated and that `spec/product_intent.md` plus his earlier messages do not answer; and a `spec/` change that evaluation has shown necessary. Nothing else goes to him.

Everything else, in order: read the source; a fresh read-only research agent (never the author of the proposal); Oracle if the choice is consequential and still open; then decide, act, and report it as **Decided** with its reversal path. Owners' "decisions for Aaron" and "defaults for Aaron to confirm" are inputs to that process, not items to forward.

An item reaches Aaron only as an ESCALATION packet: Category, Evidence read, Alternatives evaluated, Research, Oracle, Why only Aaron, Default if no answer. A message to Aaron with a "Decisions", "Still waiting on you" or "Still yours" section and no packets is a defect. Status reports have three sections: **Decided**, **Needs Aaron** (packets only), **Waiting on machines**.

Before asking, check `journal/aaron-decisions.md` and the transcript for an existing answer. When Aaron answers, append one line there (date | question | verbatim quote | disposition) so it survives compaction. The journal is intake, not the home of a ruling. Carry out one-off approvals and mark them `transient: <ref>`. Encode the standing part of any other ruling where agents read it before acting: a rule in the closest ccore2 `AGENTS.md`, a skill (`.agents/skills/` in ccore2, or this library), a check in ccore2 `scripts/`, or a spec change through the escalation above. Then mark it `encoded: <path> § <heading> "<phrase from the encoding>"`. Until then it is `pending: <owner>`. Skill edits here you make yourself; a ccore2 encoding goes to a follow-up owner, and the line becomes `encoded` when that PR merges.

When relaying Aaron's words to an owner, paste them verbatim in a quote block and label your own reading `[George's interpretation]`. Never write a paraphrase as his instruction.

Owners keep implementing, testing and gating while a packet is open. Only the specific edit, deploy or merge it gates waits. For reversible items, say "proceeding unless you object", not "say go".

## Gate order (per PR)
1. implement
2. interrogate, then apply fixes
3. deslop, no-comments
4. autoreview: the one independent review. Exactly one reviewer, never the author's own session, posted as a PR comment citing the patch-id
5. lab proof at the final head (release the lab claim afterwards)
6. rebase onto main; the patch-id must still match every receipt

Any code change after step 4 invalidates the receipts it changes the patch-id for; rerun from step 2. There is no "accepted by precedent". An exception needs Aaron's approval, recorded in the receipt as `exception` plus `exception_approved_by: "Aaron"`.

## The review (step 4)
One reviewer satisfies the review requirement. There is no separate "independent" or "final verdict" pass on top of it; do not run a second reviewer over the same patch-id.
- Choose the role by the complexity and risk of the change. Routine: `reviewer`. Complex or high-risk (data loss, auth or security, concurrency, migrations, cross-boundary contracts): `reviewer-two` or `reviewer-three`.
- Prefer a role whose configured model family differs from the author's. If none differs, run the best-fit role and note it in the receipt. Same family is a note, not a blocker.
- Roles define coverage, not models. Never hold a PR because a role resolves to a different model than expected or than a brief named. The receipt records the role, and the model actually used as a note.
- If a role fails to launch, report the exact error. The owner may use another reviewer role and records the substitution in `notes`; no exception is needed.

## Lab N/A (closed list)
`test-only`, `docs-only`, `lab-manager-undeployed`, `no-repro-red-green` (the bug doesn't reproduce on main; name the failing-then-passing test in `test`). Anything else needs lab proof at the final head.

## Receipts
One file per PR in its worktree: `.ccore/verified-build/<slug>/gates.json`
```json
{"pr": 480, "gates": [
  {"gate": "interrogate", "patch_id": "<git patch-id --stable of merge-base..head>", "result": "PASS", "at": "<ISO time>", "evidence": "<path or URL>"},
  {"gate": "lab", "patch_id": "…", "result": "NA", "na_reason": "test-only", "at": "…"},
  {"gate": "autoreview", "patch_id": "…", "result": "PASS+NOTES", "reviewer_role": "reviewer-two", "family": "openai", "author_family": "anthropic", "at": "…", "evidence": "<PR comment URL>"}
]}
```
Gates: `interrogate`, `deslop`, `no-comments`, `autoreview`, `lab`. Results: `PASS`, `PASS+NOTES` (lab also `NA`). `autoreview` also records `reviewer_role`; `family` and `author_family` are optional notes. Append a new entry when a gate reruns; the last entry per gate wins.

## Monitor pass
0. `python3 ~/.paseo/plugin-data/paseo-bots/library/skills/pr-merge-gates/ruling-check.py`. Exit 1 lists pending or dangling rulings; encode or brief an owner for each before the PR loop.
1. `gh pr list -R Nodaste-Lab/ccore2 --state open`. Start from PRs, not sessions.
2. For each PR: `python3 skills/pr-merge-gates/gate-check.py <PR>` (run from the bot directory).
   - exit 2 `EXTERNAL`: no local worktree; the PR is probably from another host (e.g. dever). Record it once in MEMORY; don't nudge and don't merge. Aaron handles it there.
   - exit 1: find the owning session (`paseo ls --json`, match worktree cwd). If it is IDLE, send one nudge listing exactly the script's missing lines. Never prompt RUNNING agents; don't repeat an unchanged nudge. A local PR with no session gets an owner: start one audit owner from the follow-up brief. It goes to Aaron only if it needs a closed-list authority.
   - exit 0 `READY`: the monitor merges: `gh pr merge <PR> -R Nodaste-Lab/ccore2 --squash`. Never `--delete-branch`: it removes the session's worktree and its lab claim file before the lab can be released. Then tear the worktree down with `python3 ~/.agents/skills/worktree-cleanup/scripts/worktree_cleanup.py --path <the session's worktree>`. It releases the lab claim, removes demos, archives the workspace, and deletes the branch. Exit 2 because the session is still running means retry on the next pass after it goes idle; act on other exit codes as `worktree-cleanup` documents. Sessions never archive themselves.
3. Pre-existing issues a PR surfaces: each must be fixed in that PR or have an owner (another worktree agent). Check for an existing owner first.
4. **Same-kind rule:** on the 2nd issue of the same kind (same subsystem and failure class), don't start another single-issue owner; start one audit owner for the whole class. Set the severity cutoff yourself from measured evidence, run it through Oracle if contested, and report it as Decided. Aaron may override.
5. **Merge slot:** while an owner is running an exact-head lab proof for a PR that holds the merge slot, merge nothing else, docs-only included.
6. **Merge for a deployable `main`, not an empty queue.** Merge a PR only when `main` needs it. While Aaron is preparing a production deploy, merge only what that deploy requires.

## Follow-up owner brief (include verbatim)
> Fix <issue> in a new worktree and open a PR. Run the gates in the order in skill pr-merge-gates and write receipts to `.ccore/verified-build/<slug>/gates.json`. Do not merge and do not deploy; stop at "ready for merge" when every gate passes at the current patch-id. You may make destructive lab changes, but snapshot data built for testing to the object store first. Never print credentials.
