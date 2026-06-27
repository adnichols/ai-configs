import { describe, expect, it, mock } from "bun:test";
import {
  assistantText,
  assistantWithToolCall,
  toolResult,
  userMsg,
} from "./fixtures";

mock.module("@earendil-works/pi-coding-agent", () => ({
  convertToLlm: (messages: any[]) => messages,
}));

mock.module("typebox", () => ({
  Type: {
    Object: () => ({}),
    Optional: (schema: unknown) => schema,
    String: () => ({}),
    Array: () => ({}),
    Number: () => ({}),
  },
}));

const getRegisteredHandlers = async (
  isIdle: boolean | (() => boolean) = true,
  sendMessageImpl?: (message: any, options: any) => void,
) => {
  const { registerBeforeCompactHook } = await import("../src/hooks/before-compact");
  const handlers: Record<string, Array<(event: any, ctx?: any) => any>> = {};
  const sentUserMessages: Array<{ content: string; options: any }> = [];
  const sentMessages: Array<{ message: any; options: any }> = [];
  const ctx = { isIdle: () => (typeof isIdle === "function" ? isIdle() : isIdle) };

  registerBeforeCompactHook({
    on: (eventName: string, callback: (event: any, ctx?: any) => any) => {
      handlers[eventName] ??= [];
      handlers[eventName].push(callback);
    },
    sendUserMessage: (content: string, options: any) => {
      sentUserMessages.push({ content, options });
    },
    sendMessage: (message: any, options: any) => {
      if (sendMessageImpl) return sendMessageImpl(message, options);
      sentMessages.push({ message, options });
    },
  } as any);

  return { handlers, sentUserMessages, sentMessages, ctx };
};

const getBeforeCompactHandler = async () => {
  const { handlers } = await getRegisteredHandlers();
  const handler = handlers.session_before_compact?.[0];
  if (!handler) throw new Error("session_before_compact handler was not registered");
  return handler;
};

const messageEntry = (id: string, message: any) => ({ id, type: "message", message });

const basePreparation = {
  previousSummary: undefined,
  tokensBefore: 1234,
  fileOps: {
    read: [],
    written: [],
    edited: [],
  },
};

const compactableEntries = () => [
  messageEntry("1", userMsg("Investigate the compaction bug")),
  messageEntry("2", assistantText("I found the hook.")),
  messageEntry("3", userMsg("Follow-up request")),
  messageEntry("4", assistantText("Working on it.")),
];

const delay = (ms = 75) => new Promise((resolve) => setTimeout(resolve, ms));

describe("before-compact cut policy", () => {
  it("falls back to compacting long agent-only tails", async () => {
    const handler = await getBeforeCompactHandler();
    const result = handler({
      preparation: basePreparation,
      branchEntries: [
        messageEntry("1", userMsg("Investigate the compaction bug")),
        messageEntry("2", assistantText("I found the hook.")),
        messageEntry("3", assistantWithToolCall("Read", { path: "a.ts" }, "tc_a")),
        messageEntry("4", toolResult("Read", "hook source", false, "tc_a")),
        messageEntry("5", assistantText("The cut policy only keeps a last user boundary.")),
        messageEntry("6", assistantWithToolCall("Read", { path: "b.ts" }, "tc_b")),
        messageEntry("7", toolResult("Read", "test source", false, "tc_b")),
        messageEntry("8", assistantText("We should keep a recent non-user tail instead.")),
      ],
    });

    expect(result.cancel).toBeUndefined();
    expect(result.compaction.firstKeptEntryId).toBe("5");
    expect(result.compaction.summary).toContain("Investigate the compaction bug");
    expect(result.compaction.summary).toContain("I found the hook.");
  });

  it("keeps the matching assistant tool call live when fallback would start at a tool result", async () => {
    const handler = await getBeforeCompactHandler();
    const result = handler({
      preparation: basePreparation,
      branchEntries: [
        messageEntry("1", userMsg("Investigate the compaction bug")),
        messageEntry("2", assistantText("I found the hook.")),
        messageEntry("3", assistantWithToolCall("Read", { path: "a.ts" }, "tc_a")),
        messageEntry("4", toolResult("Read", "hook source", false, "tc_a")),
        messageEntry("5", assistantWithToolCall("Read", { path: "b.ts" }, "tc_b")),
        messageEntry("6", toolResult("Read", "test source", false, "tc_b")),
        messageEntry("7", assistantText("The fallback should keep the pair intact.")),
      ],
    });

    expect(result.cancel).toBeUndefined();
    expect(result.compaction.firstKeptEntryId).toBe("3");
  });

  it("still prefers the latest user boundary when one exists", async () => {
    const handler = await getBeforeCompactHandler();
    const result = handler({
      preparation: basePreparation,
      branchEntries: [
        messageEntry("1", userMsg("First request")),
        messageEntry("2", assistantText("Handled the first request.")),
        messageEntry("3", userMsg("Follow-up request")),
        messageEntry("4", assistantWithToolCall("Read", { path: "followup.ts" }, "tc_followup")),
        messageEntry("5", toolResult("Read", "followup source", false, "tc_followup")),
        messageEntry("6", assistantText("Working on the follow-up.")),
      ],
    });

    expect(result.cancel).toBeUndefined();
    expect(result.compaction.firstKeptEntryId).toBe("3");
    expect(result.compaction.summary).toContain("First request");
    expect(result.compaction.summary).not.toContain("Follow-up request");
  });
});

describe("package load marker", () => {
  it("marks pi-vcc as loaded for repo-managed compaction guards", async () => {
    const { default: registerPiVcc, PI_VCC_LOAD_MARKER } = await import("../index");
    delete (globalThis as any)[PI_VCC_LOAD_MARKER];

    registerPiVcc({
      on: () => {},
      registerCommand: () => {},
      registerTool: () => {},
    } as any);

    expect((globalThis as any)[PI_VCC_LOAD_MARKER]).toBe(true);
  });
});

describe("active compaction continuation", () => {
  it("resumes the agent after compacting an in-flight turn", async () => {
    const { handlers, sentUserMessages, sentMessages, ctx } = await getRegisteredHandlers();

    handlers.agent_start[0]({ type: "agent_start" });
    const result = handlers.session_before_compact[0]({
      preparation: basePreparation,
      branchEntries: compactableEntries(),
    });

    expect(result.compaction.details.interruptedInFlightTurn).toBe(true);
    expect(result.compaction.details.requiresContinuation).toBe(true);

    handlers.session_compact[0]({
      type: "session_compact",
      compactionEntry: { details: result.compaction.details },
      fromExtension: true,
    }, ctx);
    await delay();

    expect(sentUserMessages).toHaveLength(0);
    expect(sentMessages).toHaveLength(1);
    expect(sentMessages[0].message.customType).toBe("pi-vcc-continuation");
    expect(sentMessages[0].message.display).toBe(false);
    expect(sentMessages[0].message.content).toContain("Pi-vcc compacted the active in-flight conversation.");
    expect(sentMessages[0].message.content).toContain("vcc_recall");
    expect(sentMessages[0].options).toEqual({ triggerTurn: true, deliverAs: "steer" });
  });

  it("infers an in-flight turn when compaction follows a tool result", async () => {
    const { handlers, sentMessages, ctx } = await getRegisteredHandlers();

    const result = handlers.session_before_compact[0]({
      preparation: basePreparation,
      branchEntries: [
        messageEntry("1", userMsg("Initial work")),
        messageEntry("2", assistantText("Finished that step.")),
        messageEntry("3", assistantWithToolCall("Read", { path: "a.ts" }, "tc_a")),
        messageEntry("4", toolResult("Read", "a source", false, "tc_a")),
        messageEntry("5", assistantWithToolCall("Bash", { command: "npm test" }, "tc_b")),
        messageEntry("6", toolResult("Bash", "tests passed", false, "tc_b")),
      ],
    });

    expect(result.compaction.details.interruptedInFlightTurn).toBe(true);
    expect(result.compaction.details.requiresContinuation).toBe(true);

    handlers.session_compact[0]({
      type: "session_compact",
      compactionEntry: { details: result.compaction.details },
      fromExtension: true,
    }, ctx);
    await delay();

    expect(sentMessages).toHaveLength(1);
    expect(sentMessages[0].message.content).toContain("Pi-vcc compacted the active in-flight conversation.");
    expect(sentMessages[0].options).toEqual({ triggerTurn: true, deliverAs: "steer" });
  });

  it("queues continuation even when Pi never reports idle", async () => {
    const { handlers, sentMessages, ctx } = await getRegisteredHandlers(false);

    handlers.agent_start[0]({ type: "agent_start" });
    const result = handlers.session_before_compact[0]({
      preparation: basePreparation,
      branchEntries: compactableEntries(),
    });

    expect(result.compaction.details.interruptedInFlightTurn).toBe(true);

    handlers.session_compact[0]({
      type: "session_compact",
      compactionEntry: { details: result.compaction.details },
      fromExtension: true,
    }, ctx);
    await delay();

    expect(sentMessages).toHaveLength(1);
    expect(sentMessages[0].options).toEqual({ triggerTurn: true, deliverAs: "steer" });
  });

  it("retries continuation delivery when sendMessage briefly fails", async () => {
    const sentMessages: Array<{ message: any; options: any }> = [];
    let attempts = 0;
    const { handlers, ctx } = await getRegisteredHandlers(true, (message, options) => {
      attempts += 1;
      if (attempts === 1) throw new Error("session not ready");
      sentMessages.push({ message, options });
    });

    handlers.agent_start[0]({ type: "agent_start" });
    const result = handlers.session_before_compact[0]({
      preparation: basePreparation,
      branchEntries: compactableEntries(),
    });

    handlers.session_compact[0]({
      type: "session_compact",
      compactionEntry: { details: result.compaction.details },
      fromExtension: true,
    }, ctx);
    await delay(200);

    expect(attempts).toBeGreaterThanOrEqual(2);
    expect(sentMessages).toHaveLength(1);
    expect(sentMessages[0].message.customType).toBe("pi-vcc-continuation");
  });

  it("does not prompt after the assistant has finished the turn", async () => {
    const { handlers, sentMessages, ctx } = await getRegisteredHandlers();

    handlers.agent_start[0]({ type: "agent_start" });
    handlers.message_end[0]({ type: "message_end", message: assistantText("Done.") });

    const result = handlers.session_before_compact[0]({
      preparation: basePreparation,
      branchEntries: compactableEntries(),
    });

    expect(result.compaction.details.interruptedInFlightTurn).toBe(false);

    handlers.session_compact[0]({
      type: "session_compact",
      compactionEntry: { details: result.compaction.details },
      fromExtension: true,
    }, ctx);
    await delay();

    expect(sentMessages).toHaveLength(0);
  });

  it("does not prompt after ordinary idle compaction", async () => {
    const { handlers, sentMessages, ctx } = await getRegisteredHandlers();

    const result = handlers.session_before_compact[0]({
      preparation: basePreparation,
      branchEntries: compactableEntries(),
    });

    expect(result.compaction.details.interruptedInFlightTurn).toBe(false);

    handlers.session_compact[0]({
      type: "session_compact",
      compactionEntry: { details: result.compaction.details },
      fromExtension: true,
    }, ctx);
    await delay();

    expect(sentMessages).toHaveLength(0);
  });

  it("does not send a continuation when core will retry the interrupted turn", async () => {
    const { handlers, sentMessages, ctx } = await getRegisteredHandlers();

    handlers.agent_start[0]({ type: "agent_start" });
    const result = handlers.session_before_compact[0]({
      preparation: basePreparation,
      branchEntries: compactableEntries(),
    });

    expect(result.compaction.details.interruptedInFlightTurn).toBe(true);
    expect(result.compaction.details.requiresContinuation).toBe(true);

    handlers.session_compact[0]({
      type: "session_compact",
      compactionEntry: { details: result.compaction.details },
      fromExtension: true,
      willRetry: true,
    }, ctx);
    await delay();

    expect(sentMessages).toHaveLength(0);
  });
});
