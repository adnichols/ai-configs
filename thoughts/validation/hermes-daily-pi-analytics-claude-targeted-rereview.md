Targeted rereview — Hermes Daily Pi Analytics Morning Review

  Completed checks

  - Re-read the full plan HTML and the prior Claude review (F1–F7) plus AGENTS.md.
  - Deployment (F1/F2): Confirmed hermes_config_sync.py has no --component flag today (main() only accepts export|verify|install) and install_all/verify still operate on the whole bundle. The plan now scopes the fix as
  new work ("Extend scripts/hermes_config_sync.py with a tested --component pi-analytics-collector install mode... validates paths against _hermes/default/manifest.json") rather than invoking the currently-broken profile
  path. That resolves F1/F2 as stated: it's a buildable extension, not a call to a nonexistent mechanism, and merging into the host's existing gateway removes the unsupervised-second-process problem.
  - Retention (F3): D5/AC-8 now explicitly disclaim automatic C-Core deletion and retention-success claims; matches ccore doc having no delete verb. Resolved, no incoherence.
  - Signal semantics (F5): signal_key/evidence_snapshot_id hash definitions in D4 are deterministic and, combined with "display state is keyed by signal_key" vs. "decision ledger keyed by ... evidence snapshot ID," are
  internally consistent with the dismiss/episode semantics in BDD-8 (episode state must be tracked per signal_key, independent of the day-specific evidence hash — plan doesn't claim otherwise). Resolved.
  - Cross-host/recovery (F7): Verification section replaces "sync healthy" with an exact disposable-report readback (title/schema/hash/content) plus the enumerated last-run.json states and --status --json command.
  Resolved.
  - Private space naming: plan no longer suggests renaming to "Personal" and the review record explicitly rejects that prior suggestion. Not re-litigated per instructions.
  - Action ingress/authority (F4) — checked against live repo evidence. Grepped doct-agent-commands.md, doct-plan-comment-dispatcher-pattern.md, SKILL.md, and the three existing live listener scripts
  (gm_plan_comment_listener.py, doct_document_comment_listener.py, hermes_pr_codex_plan_comment_listener.py) for any author/user-identity field on a plan-comment claim. None exists: every listener's claim_parts() only
  extracts threadId/claimId with multiple speculative key fallbacks, and the CLI reference only ever describes "reviewer context," thread-id, claim-id — never a per-comment author/user ID.

  Findings

  Unresolved readiness blocker — P4's author-identity check has no grounded field to validate against. The plan's P4 Work section requires: "Validate thread.comments[-1].authorType == "user" and authorUserId against the
  configured immutable Aaron Doct user ID." Tests-first also lists "unauthorized" as a distinct rejection case from wrong-document/version/hash/card. But no script, skill doc, or CLI reference anywhere in this repo names
  authorType/authorUserId (or any equivalent) on a Doct plan-comment claim payload — the routing half of the old F4 gap (submitAction: agent vs conversation, real and documented) is now solid, but the author half is
  asserted with specific field names that have zero grounding in the current Doct API surface as reflected in every existing listener in this codebase. AC-6 ("authored by Aaron") is load-bearing for the whole P4 security
  model, so this isn't cosmetic: if the payload doesn't actually expose a stable per-user ID, the check as scoped can't be built, and the plan doesn't flag this as an open dependency (P4's "Open questions" says "None").
  This needs either a confirmed real field name (e.g., via doct-agent context/a live payload capture) or an explicit documented fallback rationale (e.g., single-tenant workspace ⇒ routed-queue authenticity is
  sufficient) before P4 is truly execution-ready.

  Secondary/minor — component cron-merge semantics aren't specified and the only existing merge primitive would misbehave if reused naively. merge_cron_jobs() (hermes_config_sync.py:453-477) builds its output entirely
  from incoming["jobs"], carrying over only certain runtime fields from matching existing IDs — it does not preserve destination jobs that aren't present in incoming. The plan's "merges only the named collector job ID
  into the target Hermes home" requires an additive merge (add one job, keep all of dever's pre-existing unrelated jobs untouched), which is a different function than the one that exists today. This is buildable as new
  code (consistent with "P2 is future work"), but P2's test list doesn't include a case asserting pre-existing unrelated jobs on the target host survive install — worth adding explicitly so an implementer doesn't wire
  the new component path through the existing full-replace merge_cron_jobs and silently wipe dever's other jobs.

  Remaining checks

  None required to reach a verdict — the P4 author-identity gap is sufficient on its own, and I did not find a live .py/doc source for mbp's Good Morning orchestrator here either (same host-access limitation as the prior
  review), which doesn't change the outcome.

  Assessment

  Five of the six re-checked areas (deployment/rollout mechanism, retention truthfulness, signal identity, cross-host recovery, and the routing half of action ingress) are now coherently fixed and don't reintroduce a
  regression. The sixth — author-identity validation inside P4's action-authority design — still rests on invented field names with no support anywhere in this repo's Doct integration code or docs, which is the same
  category of problem (asserting a mechanism that isn't confirmed to exist) as the original F1/F3 blockers, just relocated to a different phase. That's enough to withhold an execution-ready verdict.

  VERDICT: PLAN_NEEDS_REVISION

---
CLAUDE_REVIEW_LAUNCHER_METADATA
socket=claude-review-claude-review-ed79544880d5-1134006-072e3a98b8a0
session=review
window=claude-review
model=claude-sonnet-5
effort=xhigh
transcript=/home/anichols/code/ai-configs/thoughts/validation/hermes-daily-pi-analytics-claude-targeted-rereview.md.transcript.txt
claude_session_id=06d61b36-f46e-4901-bea3-79dd7e21e935
session_record=/home/anichols/.claude/projects/-home-anichols-code-ai-configs/06d61b36-f46e-4901-bea3-79dd7e21e935.jsonl
readiness_regex=❯
clear_boundary=baseline-relative marker/sentinel occurrence diff after submit
history_limit=50000
capture_depth=50000
