Final bounded rereview — Hermes Daily Pi Analytics Morning Review

  Scope: author-identity grounding (P4) and additive component safety (P2) only, per instructions. No files edited. Prior resolved findings (F1/F2/F3/F5/F7, private-space naming) not re-litigated.

  Completed checks

  - Author-identity grounding (P4): Searched beyond repo-tracked docs/scripts (which is as far as the prior targeted rereview looked) into local runtime artifacts. Found
  /home/anichols/.hermes/tmp/doct-plan-comments/claim-3.json and claim-4.json — real captured doct-agent plans agent next/plans listen responses (type: "plan-review.agent.next.v1") from an actual prior plan-review
  session (2026-07-04, "Plan: Pi Benchmark Harness on Dever," workspace 759bfae3-...). Both files contain, verbatim: routingMetadata.submitAction: "agent" (at both item. and thread. level) and, inside thread.comments[],
  authorType: "user" and authorUserId: "user_37aF7JpbASxjCDYaiXUDADaRHJw" — the exact same user ID cited in this round's evidence packet, appearing identically across two independent comment threads. This is genuine
  live-API evidence, not an invented field name: the schema the prior review couldn't find in committed docs/scripts does exist in the real Doct claim payload returned by the very CLI commands (plans agent next, plans
  listen --jsonl) P4 is built on. This resolves the blocker from the targeted rereview.
  - Minor precision note (non-blocking): the plan's "Current implementation reality" bullet says the dispatch was "captured for this plan." The artifacts substantiating the field names actually belong to a different,
  earlier plan-review thread (Pi Benchmark Harness), not this plan's own listener session. The schema is the same generic Doct claim-payload shape used for any plan, so the grounding claim holds — the fields are real —
  but the provenance wording overstates specificity. Worth a small wording fix (e.g., "a captured Doct plan-comment dispatch" rather than "captured for this plan"), not a readiness gate.
  - Additive component safety (P2): Re-read merge_cron_jobs() (scripts/hermes_config_sync.py:453-477) directly. Confirmed it builds merged["jobs"] entirely from incoming["jobs"], carrying over only listed runtime fields
  for matching IDs — it does not preserve destination jobs absent from incoming, exactly as previously characterized. The plan's current P2 Work section now explicitly forbids reusing this function unmodified ("must not
  reuse the existing full-bundle merge_cron_jobs behavior if that would replace the destination job set") and requires a new additive merge; Tests-first now includes "additive cron merge preserves unrelated destination
  jobs and runtime fields byte-for-byte," and the Verify block adds "On dever, assert every pre-existing unrelated cron job remains unchanged." This is buildable new code against a correctly diagnosed existing function,
  with an explicit test closing the "silently wipe dever's other jobs" risk flagged last round. Resolved.
  - Manifest/export sequencing sanity check: confirmed build_manifest(root, src_home) only uses src_home for a cosmetic metadata string and hashes the already-staged bundle tree — so a source-only refresh-manifest action
  (no live Hermes-home read) is a coherent, buildable extension of existing code, not a call into a nonexistent live-only path. Consistent with the plan's sequencing claim (refresh-manifest → verify → component install;
  full export forbidden on dever, permitted only after mbp's authoritative full install/verify).

  Findings

  None blocking. One cosmetic/non-blocking note:

  - category: precision — file: thoughts/plans/hermes-daily-pi-analytics-morning-review.html (line 35, "reality" section) — summary: "captured for this plan" overstates the provenance of the observed
  authorType/authorUserId payload shape; the actual corroborating artifact is from an unrelated earlier plan-review thread using the same generic Doct dispatch schema. — failure_scenario: none functionally — an
  implementer reading this literally might go looking for a payload capture specific to this plan's own listener and not find one, causing brief confusion, but the schema itself is correctly grounded and implementable as
  specified.

  Remaining checks

  None required — both items this round was bounded to (author-identity grounding, additive component cron-merge safety) are now substantiated against real evidence (a live captured Doct claim payload and the actual
  merge_cron_jobs source), and no new blocker surfaced.

  Assessment

  The previously unresolved P4 author-identity blocker is now grounded in genuine local evidence: real Doct plan-comment claim payloads on this machine show authorType, authorUserId, and routingMetadata.submitAction
  exist exactly as the plan requires, including the specific user ID the plan's identity check would validate against. The P2 additive-merge safety gap is now explicit in Tests-first and Verify, correctly scoped as new
  code rather than reuse of the destructive existing merge_cron_jobs. Manifest-refresh/export sequencing is a coherent extension of existing code. No newly introduced regression or invented mechanism was found in this
  bounded pass.

  VERDICT: PLAN_EXECUTION_READY

---
CLAUDE_REVIEW_LAUNCHER_METADATA
socket=claude-review-claude-review-0cd5060af5c4-1209258-8d8ed5696cce
session=review
window=claude-review
model=claude-sonnet-5
effort=xhigh
transcript=/home/anichols/code/ai-configs/thoughts/validation/hermes-daily-pi-analytics-claude-final-rereview.md.transcript.txt
claude_session_id=9f013f70-c322-4e71-a03a-9a850d7afc4a
session_record=/home/anichols/.claude/projects/-home-anichols-code-ai-configs/9f013f70-c322-4e71-a03a-9a850d7afc4a.jsonl
readiness_regex=❯
clear_boundary=baseline-relative marker/sentinel occurrence diff after submit
history_limit=50000
capture_depth=50000
