Test evidence: pending failure continuation blocks replacement compaction until safe at test :433–:465 (overflow + willRetry both blocked; continuation only sent once outstanding tool ids drain via assistantStop);
  safe-delivery gate at code :389–:391 and :655
  Status: Satisfied
  ────────────────────────────────────────
  Race family / plan requirement: 4. Non-no-cut scheduled failure/cancel must ratchet lastAutoCompactionPercent so a same-percent follow-up turn does not immediately reschedule hard backstop
  Code evidence: onError non-no-cut branch ratchets at :483 before enqueuing continuation; and session_before_compact also ratchets defensively at :763/:772/:794/:803/:814/:828/:836; turn-side gate at :696 uses
  isStaleAutoCompactionPercent + user-message gate
  Test evidence: same-percent hard-backstop failure retry is suppressed after continuation delivery at test :577–:598 (provider failed at 96.2% → continuation sent → next turn does not reschedule); integrated race test
  :348–:376 confirms same-percent core call is also canceled
  Status: Satisfied
  ────────────────────────────────────────
  Race family / plan requirement: No-cut recovery preserves interrupted turn ownership and drains pending tool ids before delivery
  Code evidence: queueNoCutContinuation gated on interruptedActiveTurn (:293); noCutContinuationIsSafe requires empty pending ids or isCompletedAssistantResponse (:312–:314); tool ids drained in clearDeliveredNoCutTools
  (:307–:310)
  Test evidence: Tests at :467–:485, :487–:500, :502–:513, :515–:537, :539–:560 cover active/idle/user/manual/compact_context variants and retry+permanent failure paths
  Status: Satisfied
  ────────────────────────────────────────
  Race family / plan requirement: Same-percent no-cut suppression until usage rises or new user message
  Code evidence: noCutRetryState set at :468–:473; turn-side gate at :699–:704; core-side gate at :822–:834; message_end bumps userMessageCount at :732; session_compact clears retry state at :736
  Test evidence: same floored no-cut percent is suppressed until usage rises or a user speaks at test :600–:629; core auto-compaction honors same floored no-cut suppression at :670–:697; successful core compaction clears

  no-cut retry suppression at :699–:714
  Status: Satisfied
  ────────────────────────────────────────
  Race family / plan requirement: Model-visible no-cut continuation does not re-arm retry as a real user turn
  Code evidence: message_end handler filters on typeof event.message.customType !== "string" at :732
  Test evidence: model-visible no-cut continuation does not re-arm retry suppression as user input at test :631–:644
  Status: Satisfied
  ────────────────────────────────────────
  Race family / plan requirement: pi-vcc-missing safety on the scheduled/overflow paths
  Code evidence: isPiVccLoaded() checked in triggerCompaction (:419) and session_before_compact entry (:743); overflow/willRetry short-circuit only reachable AFTER the missing-pi-vcc guard has fired
  Test evidence: core overflow retries bypass the extension hard threshold gate only when pi-vcc is loaded at test :819–:847
  Status: Satisfied

  Findings

  None in scope. The four previously-fixed regression families are covered by both the runtime guards and the newly added tests; the 46-test bun suite plus the 23-test _pi/packages/pi-vcc before-compact suite exercise
  every branch cited in the coverage table above.

  Notes on scope-adjacent items I explicitly considered and rejected as out of this diff:

  - finishCompaction clearing pendingModelCompaction on failure (:230–:240) means a queued compact_context intent is dropped if the concurrent hard-backstop attempt fails/cancels. This is orthogonal to the race families
  in the plan (no lost continuation, no repeated visible loop). Classification: OUT_OF_SCOPE_FOLLOW_UP — do not treat as a review finding.
  - Same-percent equality in isStaleAutoCompactionPercent relies on identical float representation between the turn-side ratchet and the next getContextUsage() reading. In practice both callers use the value returned
  from the same ctx.getContextUsage() and the tests cover the observed values (96.2, 80.123456, 80.75), so no regression risk from this diff. Classification: OUT_OF_SCOPE_FOLLOW_UP if you ever want a floor-based
  comparison.
  - No-cut vs. non-no-cut continuation flows share the same 50 ms / 100 ms / 5 s delivery constants but write to distinct pendingNoCutContinuation / pendingCompactionContinuation slots and the safe-to-send predicates
  each only consult their own slot, so the two flows cannot cross-suppress. Classification: IN_PLAN (already required, already satisfied).

  VERDICT: PASS_SCOPED

---
CLAUDE_REVIEW_LAUNCHER_METADATA
socket=claude-review-claude-pi-vcc-race-review3-3196356-529fa9c7025d
session=review
window=claude-review
model=claude-opus-4-7
effort=xhigh
transcript=thoughts/validation/pre-pr-reviews/2026-07-08-pi-vcc-race-claude-rerun2.md.transcript.txt
readiness_regex=❯
clear_boundary=prompt-cleared marker/sentinel extraction after submit
history_limit=50000
capture_depth=50000
