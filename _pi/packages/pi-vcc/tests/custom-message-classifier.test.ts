import { describe, expect, it } from "bun:test";
import { createContinuationTransaction, transitionContinuation } from "../src/core/continuation";
import { continuationMessageDetailsFor } from "../src/core/continuation-protocol";
import {
  MODEL_DRIVING_CUSTOM_MESSAGE_TYPES,
  STATUS_ONLY_CUSTOM_MESSAGE_TYPES,
  classifyCustomMessageIntent,
} from "../src/core/custom-message-classifier";

const submitted = () => transitionContinuation(createContinuationTransaction({
  transactionId: "tx-classifier",
  origin: "compact_context",
  reason: "compacted",
  attemptId: "attempt-classifier",
  resumePolicy: "active",
  createdAt: 10,
  deadlineMs: 15_000,
}), {
  type: "submitted",
  at: 20,
  acceptanceDeadlineAt: 15_020,
}).snapshot;

describe("custom-message intent classifier", () => {
  it("classifies only the transaction-matching continuation as continuation", () => {
    const snapshot = submitted();
    expect(classifyCustomMessageIntent({
      role: "custom",
      customType: "pi-vcc-continuation",
      details: continuationMessageDetailsFor(snapshot),
    }, snapshot)).toBe("continuation");
    expect(classifyCustomMessageIntent({
      role: "custom",
      customType: "pi-vcc-continuation",
      details: { ...continuationMessageDetailsFor(snapshot), submissionCount: 99 },
    }, snapshot)).toBe("independent");
  });

  it("keeps only explicit and allowlisted status messages neutral", () => {
    const snapshot = submitted();
    for (const customType of STATUS_ONLY_CUSTOM_MESSAGE_TYPES) {
      expect(classifyCustomMessageIntent({ role: "custom", customType }, snapshot)).toBe("status");
    }
    expect(classifyCustomMessageIntent({
      role: "custom",
      customType: "subagent-heartbeat",
      details: { piVccInputIntent: "status" },
    }, snapshot)).toBe("status");
  });

  it("fails closed for model-driving, explicit replacement, and unknown messages", () => {
    const snapshot = submitted();
    for (const customType of MODEL_DRIVING_CUSTOM_MESSAGE_TYPES) {
      expect(classifyCustomMessageIntent({ role: "custom", customType }, snapshot)).toBe("independent");
    }
    for (const piVccInputIntent of ["independent", "replace-continuation"]) {
      expect(classifyCustomMessageIntent({
        role: "custom",
        customType: "producer",
        details: { piVccInputIntent },
      }, snapshot)).toBe("independent");
    }
    expect(classifyCustomMessageIntent({ role: "custom", customType: "unknown" }, snapshot)).toBe("independent");
    expect(classifyCustomMessageIntent({ role: "custom", customType: "ad-process:update", details: { piVccInputIntent: "independent" } }, snapshot)).toBe("independent");
  });
});
