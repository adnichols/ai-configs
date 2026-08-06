import { describe, expect, it } from "bun:test";
import { continuationLogRecordFor, CONTINUATION_LOG_KEYS, isStrictContinuationLogRecord } from "../src/core/log-schema";
import { createContinuationTransaction } from "../src/core/continuation";

const snapshot = createContinuationTransaction({
  transactionId: "tx-secret",
  origin: "compact_context",
  reason: "failed",
  compactionId: "compact-1",
  attemptId: "attempt-1",
  requestId: "request-1",
  originatingRequestId: "request-1",
  resumePolicy: "active",
  createdAt: 10,
  deadlineMs: 100,
  pendingToolCount: 2,
});

describe("continuation log schema", () => {
  it("emits exact allowlisted keys and excludes secret-bearing content", () => {
    const record = continuationLogRecordFor("created", snapshot, 20);
    expect(isStrictContinuationLogRecord(record)).toBe(true);
    expect(Object.keys(record).every((key) => CONTINUATION_LOG_KEYS.includes(key as any))).toBe(true);
    const json = JSON.stringify(record);
    expect(json).not.toContain("preserve");
    expect(json).not.toContain("message content");
    expect(json).not.toContain("toolCallId");
    expect(json).not.toContain("sk-secret-bearing-value");
  });

  it("rejects unknown privacy-sensitive fields", () => {
    const record = continuationLogRecordFor("failed", snapshot, 20);
    expect(isStrictContinuationLogRecord({ ...record, error: "Bearer secret" })).toBe(false);
    expect(isStrictContinuationLogRecord({ ...record, preserve: "password=secret" })).toBe(false);
  });

  it("rejects non-enum resume policies including auto", () => {
    const record = continuationLogRecordFor("created", snapshot, 20);
    expect(isStrictContinuationLogRecord({ ...record, resumePolicy: "auto" })).toBe(false);
    expect(isStrictContinuationLogRecord({ ...record, resumePolicy: "later" })).toBe(false);
    expect(isStrictContinuationLogRecord({ ...record, resumePolicy: "terminal" })).toBe(true);
  });
});
