---
name: adversarial-fix-review
description: Use when adn-mode or the bug-fix playbook requires a second-model review of a claimed fix. Spawn a different-family reviewer who must prove the claim from artifacts, not the implementer's summary.
disable-model-invocation: true
---

# Adversarial fix review

A claimed fix is not done until a second reviewer, on a different model family, independently proves three things:

1. The bug still exists without this change.
2. This change is necessary.
3. The fix actually works.

The implementer's summary, brief, ticket comment, or self-written test is the claim, not the evidence.

Do not use **interrogate** for this. Interrogate checks whether the code matches the stated intent. It does not check whether the intent is true.

Do not use **autoreview** for this. Autoreview is static code review of a diff.

## When

- You are about to say a bug is fixed.
- You are about to say a change is necessary.
- You are about to hand a fix to another agent, worktree, or PR. Run this *before* writing the brief.
- You received a brief that tells you to commit or open a PR for someone else's fix. You are the second reviewer. Re-derive the claim. If you cannot prove it, refuse.

Skip only when the operator already accepted the change as necessary in this conversation with a stated reason, or when the edit has no behavior claim (private rename, comment-only).

## Packet

Give the reviewer:

- One sentence claim. Example: "list/resolve/signal-create still 409s for actor_id X after the 1602 hub repair."
- Paths, not pasted file bodies.
- The diff path or `git diff` range.
- Ticket IDs, commands, and bundle IDs the implementer cites.
- The original repro, if any.

Do not give:

- The implementer's narrative as proof.
- A conclusion to rubber-stamp.
- Permission to treat a new test helper as evidence that production still hits the bug.

## Reviewer

Read-only. Different model family from the implementer.

- **OMP.** If the implementer is Grok, spawn `reviewer-kimi`. If the implementer is Kimi, spawn `reviewer` (Terra). Do not spawn the implementer's model.
- **Pi.** Spawn the repository `reviewer` subagent when the implementer is not Terra. If the implementer is Terra, ask Oracle only the necessity question. Oracle is advisory and cannot rubber-stamp.
- **Cursor.** Same family split: Kimi reviewer for Grok parents, Terra or Grok for Kimi parents.

The reviewer must:

1. Re-read the cited code and tickets. A function that *would* fail if a bad state existed is not proof that the bad state exists.
2. Check whether the failing test constructs a state the production path already rejects. If the test only fails after a new helper plants that state, it does not prove the bug is live.
3. Demand post-repair evidence when a related fix already shipped. An open ticket in the same cluster is not that evidence.
4. Run or re-run the cheapest command that would fail if the claim is false. If that command cannot be run, say so and return `NOT PROVEN`.
5. Answer only with one verdict (`NECESSARY`, `UNNECESSARY`, or `NOT PROVEN`) plus the artifact paths and command output that support it.

## After return

The coordinating agent may not upgrade `NOT PROVEN` or `UNNECESSARY` to `NECESSARY` from conversation memory, a brief it wrote, or "we already discussed this."

- `NECESSARY`: continue. Keep the reviewer's evidence in the PR.
- `UNNECESSARY`: do not open the PR. Do not hand the change to another agent. Revert or drop it unless the operator overrides.
- `NOT PROVEN`: do not open the PR. Do not spawn another agent to land it. Get the missing evidence or drop the change.

## Reply

Verdict, the three answers, the commands run, and whether a PR or handoff is allowed.
