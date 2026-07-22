import assert from "node:assert/strict";
import test from "node:test";
import { outcomeGuidance } from "../runtime.ts";

function job(overrides = {}) {
  return { jobId: "j", jobNonce: "n", action: "start", reviewType: "implementation-review", verdictProfile: "pre-pr-implementation", status: "failed", classification: "CODEX_REVIEW_ARTIFACT_INVALID", summary: "", cwd: "/repo", output: "/review.md", stdoutLog: "/stdout", stderrLog: "/stderr", stateFile: "/state", reservationFile: "/reserve", stagingOutput: "/staging", launcherStatus: "/status", startedAt: new Date().toISOString(), deliveryId: "d", deliveryState: "pending", deliveryAttempts: 0, ...overrides };
}

test("verdict guidance names exact workflow budget and next action", () => {
  assert.match(outcomeGuidance(job({ status: "succeeded", classification: "CODEX_REVIEW_SUCCEEDED", verdict: "CLEAN_FOR_PR" })), /Retry budget: none.*continue to the next required workflow gate/s);
  assert.match(outcomeGuidance(job({ status: "succeeded", classification: "CODEX_REVIEW_SUCCEEDED", verdict: "FINDINGS_TO_RESOLVE" })), /post-fix targeted-rereview budget.*resolve or disposition/s);
  assert.match(outcomeGuidance(job({ status: "succeeded", classification: "CODEX_REVIEW_SUCCEEDED", verdict: "BLOCKED_BY_QUESTION" })), /none until the required decision is resolved.*surface the exact question/s);
  assert.match(outcomeGuidance(job({ status: "succeeded", classification: "CODEX_REVIEW_SUCCEEDED", verdict: "REVIEW_INCOMPLETE_RERUN_NEEDED" })), /one narrowed incomplete-coverage follow-up for this reviewer\/cycle/);
  assert.match(outcomeGuidance(job({ status: "succeeded", classification: "CODEX_REVIEW_SUCCEEDED", verdictProfile: "reviewed-html-plan", verdict: "REVIEW_INCOMPLETE_RERUN_NEEDED" })), /recommended required slice.*convergence\/product\/tooling stop condition/);
  assert.match(outcomeGuidance(job({ status: "succeeded", classification: "CODEX_REVIEW_SUCCEEDED", verdictProfile: "generic-implementation", verdict: "REVIEW_INCOMPLETE_RERUN_NEEDED" })), /caller-owned/);
});

test("terminal failure guidance is classification-specific and never invents retries", () => {
  const cases = [
    ["CODEX_REVIEW_ARTIFACT_INVALID", /single narrower unusable-output rerun allowance/],
    ["CODEX_REVIEW_LAUNCHER_PROTOCOL_INVALID", /only after protocol diagnosis\/repair/],
    ["CODEX_AUTH_UNAVAILABLE", /repair credentials, run codex_review smoke/],
    ["CODEX_REVIEW_CODEX_EXIT_NONZERO", /no unsupported provider cause is claimed/],
    ["CODEX_REVIEW_STATE_PERSIST_FAILED", /original verdict is not authoritative/],
    ["CODEX_REVIEW_INTERRUPTED", /startup reconciliation interrupted/],
  ];
  for (const [classification, pattern] of cases) assert.match(outcomeGuidance(job({ classification })), pattern);
  assert.match(outcomeGuidance(job({ status: "timed_out", classification: "CODEX_REVIEW_OUTER_TIMEOUT" })), /TERM-to-KILL cleanup.*consumes that allowance/s);
  assert.match(outcomeGuidance(job({ status: "cancelled", classification: "CODEX_REVIEW_CANCELLED", cancellationReason: "user" })), /no automatic rerun.*restart that same gate/s);
});
