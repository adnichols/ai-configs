import { mkdtemp, rm } from "fs/promises";
import { join } from "path";
import { tmpdir } from "os";
import { afterAll, beforeAll, describe, expect, it, mock } from "bun:test";
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

let previousPiVccLogPath: string | undefined;
let piVccLogTestDir: string | undefined;

beforeAll(async () => {
  previousPiVccLogPath = process.env.PI_VCC_LOG_PATH;
  piVccLogTestDir = await mkdtemp(join(tmpdir(), "pi-vcc-log-test-"));
  process.env.PI_VCC_LOG_PATH = join(piVccLogTestDir, "pi-vcc.jsonl");
});

afterAll(async () => {
  if (previousPiVccLogPath === undefined) delete process.env.PI_VCC_LOG_PATH;
  else process.env.PI_VCC_LOG_PATH = previousPiVccLogPath;
  if (piVccLogTestDir) await rm(piVccLogTestDir, { recursive: true, force: true });
});

const getRegisteredHandlers = async (
  isIdle: boolean | (() => boolean) = true,
  sendMessageImpl?: (message: any, options: any) => void,
) => {
  const { registerBeforeCompactHook } = await import("../src/hooks/before-compact");
  const handlers: Record<string, Array<(event: any, ctx?: any) => any>> = {};
  const sentUserMessages: Array<{ content: string; options: any }> = [];
  const sentMessages: Array<{ message: any; options: any }> = [];
  const ctx = { isIdle: () => (typeof isIdle === "function" ? isIdle() : isIdle) };

  const pi = {
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
  } as any;
  registerBeforeCompactHook(pi, {
    authority: "coordinator",
    request: (_input: any, _ctx: any) => {
      const details = _input;
      try {
        pi.sendMessage({
          customType: "pi-vcc-continuation",
          content: "Pi-vcc compacted the active in-flight conversation. Continue and use vcc_recall if needed.",
          display: false,
          details,
        }, { triggerTurn: true, deliverAs: "steer" });
      } catch {}
      return details;
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

const compactionEntry = (id: string, firstKeptEntryId: string) => ({ id, type: "compaction", firstKeptEntryId });

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

  it("falls back to compacting long post-compaction agent-only tails", async () => {
    const handler = await getBeforeCompactHandler();
    const result = handler({
      preparation: basePreparation,
      branchEntries: [
        messageEntry("1", userMsg("Old request")),
        messageEntry("2", assistantText("Old answer")),
        compactionEntry("c1", "3"),
        messageEntry("3", assistantText("Kept prior summary boundary.")),
        messageEntry("4", assistantWithToolCall("Read", { path: "a.ts" }, "tc_a")),
        messageEntry("5", toolResult("Read", "hook source", false, "tc_a")),
        messageEntry("6", assistantText("Interpreted hook source.")),
        messageEntry("7", assistantWithToolCall("Read", { path: "b.ts" }, "tc_b")),
        messageEntry("8", toolResult("Read", "test source", false, "tc_b")),
        messageEntry("9", assistantText("Ready to patch.")),
      ],
      reason: "threshold",
    });

    expect(result.cancel).toBeUndefined();
    expect(result.compaction.firstKeptEntryId).toBe("6");
    expect(result.compaction.summary).toContain("Kept prior summary boundary.");
    expect(result.compaction.summary).toContain('Read "a.ts"');
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

  it("does not cut when a fallback boundary would orphan a tool result without a matching call", async () => {
    const handler = await getBeforeCompactHandler();
    const result = handler({
      preparation: basePreparation,
      branchEntries: [
        messageEntry("1", userMsg("Investigate the compaction bug")),
        messageEntry("2", assistantText("I found the hook.")),
        messageEntry("3", assistantText("More analysis.")),
        messageEntry("4", assistantText("More setup.")),
        messageEntry("5", toolResult("Read", "orphaned source", false, "tc_missing")),
        messageEntry("6", assistantWithToolCall("Read", { path: "b.ts" }, "tc_b")),
        messageEntry("7", toolResult("Read", "test source", false, "tc_b")),
        messageEntry("8", assistantText("The fallback cannot safely keep an orphaned tool result.")),
      ],
      customInstructions: "__PI_VCC_MANUAL_BYPASS__",
    });

    expect(result).toEqual({ cancel: true });
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
      appendEntry: () => {},
      events: { on: () => () => {}, emit: () => {} },
    } as any);

    expect((globalThis as any)[PI_VCC_LOAD_MARKER]).toBe(true);
  });
});

describe("compaction intent and overflow fallback", () => {
  it("parses marker plus JSON intent into summary and details", async () => {
    const handler = await getBeforeCompactHandler();
    const result = handler({
      preparation: basePreparation,
      branchEntries: compactableEntries(),
      customInstructions: '__PI_VCC_MANUAL_BYPASS__\n{"source":"compact_context","reason":"done","boundary":"subtask_complete","preserve":"keep tests"}',
    });

    expect(result.cancel).toBeUndefined();
    expect(result.compaction.summary).toContain("[Compaction Intent]");
    expect(result.compaction.summary).toContain("reason=done");
    expect(result.compaction.summary).toContain("preserve=keep tests");
    expect(result.compaction.details.compactionIntent).toEqual({
      source: "compact_context",
      reason: "done",
      boundary: "subtask_complete",
      preserve: "keep tests",
    });
  });

  it("ignores malformed marker JSON payload but keeps marker behavior", async () => {
    const handler = await getBeforeCompactHandler();
    const result = handler({
      preparation: basePreparation,
      branchEntries: compactableEntries(),
      customInstructions: '__PI_VCC_MANUAL_BYPASS__\n{"source":"compact_context"',
    });

    expect(result.cancel).toBeUndefined();
    expect(result.compaction.summary).not.toContain("[Compaction Intent]");
    expect(result.compaction.details.compactionIntent).toBeUndefined();
  });

  it("lets core retry overflow compaction when pi-vcc cannot form a cut", async () => {
    const handler = await getBeforeCompactHandler();
    const result = handler({
      preparation: basePreparation,
      branchEntries: [messageEntry("1", userMsg("too small"))],
      reason: "overflow",
      willRetry: true,
    });

    expect(result).toBeUndefined();
  });

  it("classifies tiny no-cut sessions for diagnosis", async () => {
    const { registerBeforeCompactHook, getLastNoCutClassification } = await import("../src/hooks/before-compact");
    const handlers: Record<string, Array<(event: any) => any>> = {};
    registerBeforeCompactHook({
      on: (eventName: string, callback: (event: any) => any) => {
        handlers[eventName] ??= [];
        handlers[eventName].push(callback);
      },
      sendMessage: () => {},
    } as any);

    const result = handlers.session_before_compact[0]({
      preparation: basePreparation,
      branchEntries: [messageEntry("1", userMsg("too small"))],
      reason: "overflow",
      willRetry: true,
    });

    expect(result).toBeUndefined();
    expect(getLastNoCutClassification()).toMatchObject({
      reason: "tiny_session",
      liveMessageCount: 1,
      hadPreviousCompaction: false,
      activeTurnInferred: false,
      compactionReason: "overflow",
      willRetry: true,
    });
  });

  it("classifies post-compaction tails that are too short", async () => {
    const { registerBeforeCompactHook, getLastNoCutClassification } = await import("../src/hooks/before-compact");
    const handlers: Record<string, Array<(event: any) => any>> = {};
    registerBeforeCompactHook({
      on: (eventName: string, callback: (event: any) => any) => {
        handlers[eventName] ??= [];
        handlers[eventName].push(callback);
      },
      sendMessage: () => {},
    } as any);

    const result = handlers.session_before_compact[0]({
      preparation: basePreparation,
      branchEntries: [
        messageEntry("1", userMsg("old")),
        messageEntry("2", assistantText("old response")),
        compactionEntry("c1", "3"),
        messageEntry("3", assistantText("kept tail")),
        messageEntry("4", assistantText("short tail")),
      ],
      reason: "threshold",
    });

    expect(result).toBeUndefined();
    expect(getLastNoCutClassification()).toMatchObject({
      reason: "post_compaction_tail_too_short",
      liveMessageCount: 2,
      hadPreviousCompaction: true,
      latestLiveRole: "assistant",
      compactionReason: "threshold",
    });
  });

  it("classifies active-turn no-safe-cut cancellations", async () => {
    const { registerBeforeCompactHook, getLastNoCutClassification } = await import("../src/hooks/before-compact");
    const handlers: Record<string, Array<(event: any) => any>> = {};
    registerBeforeCompactHook({
      on: (eventName: string, callback: (event: any) => any) => {
        handlers[eventName] ??= [];
        handlers[eventName].push(callback);
      },
      sendMessage: () => {},
    } as any);

    const result = handlers.session_before_compact[0]({
      preparation: basePreparation,
      branchEntries: [
        messageEntry("1", userMsg("old")),
        messageEntry("2", assistantWithToolCall("Read", { path: "a.ts" }, "tc_a")),
        messageEntry("3", toolResult("Read", "source", false, "tc_a")),
      ],
      customInstructions: "__PI_VCC_MANUAL_BYPASS__\nkeep:2",
    });

    expect(result).toEqual({ cancel: true });
    expect(getLastNoCutClassification()).toMatchObject({
      reason: "active_turn_no_safe_cut",
      liveMessageCount: 3,
      hadPreviousCompaction: false,
      latestLiveRole: "toolResult",
      activeTurnInferred: true,
    });
  });

  it("lets the hard backstop fall back when pi-vcc cannot form a cut", async () => {
    const handler = await getBeforeCompactHandler();
    const result = handler({
      preparation: basePreparation,
      branchEntries: [messageEntry("1", userMsg("too small"))],
      reason: "threshold",
    });

    expect(result).toBeUndefined();
  });

  it("cancels instead of ignoring trailing keep after manual JSON-like instructions", async () => {
    const handler = await getBeforeCompactHandler();
    const result = handler({
      preparation: basePreparation,
      branchEntries: compactableEntries(),
      customInstructions: '__PI_VCC_MANUAL_BYPASS__\npreserve {"ticket":"ADN"} keep:2',
    });

    expect(result).toEqual({ cancel: true });
  });

  it("cancels instead of falling back when explicit keep would keep all user turns", async () => {
    const handler = await getBeforeCompactHandler();
    const result = handler({
      preparation: basePreparation,
      branchEntries: compactableEntries(),
      customInstructions: "__PI_VCC_MANUAL_BYPASS__\nkeep:2",
    });

    expect(result).toEqual({ cancel: true });
  });
});

describe("active compaction continuation", () => {
  it("logs session compactions for central observability", async () => {
    const logPath = process.env.PI_VCC_LOG_PATH;
    if (!logPath) throw new Error("PI_VCC_LOG_PATH test override was not configured");
    const beforeLog = Bun.file(logPath);
    const before = await beforeLog.exists() ? await beforeLog.text() : "";
    const { handlers, ctx } = await getRegisteredHandlers();

    handlers.session_compact[0]({
      type: "session_compact",
      compactionEntry: {
        id: "test-compaction-id",
        details: {
          compactor: "pi-vcc",
          version: 1,
          sections: ["Session Goal"],
          sourceMessageCount: 5,
          previousSummaryUsed: false,
          interruptedInFlightTurn: false,
          requiresContinuation: false,
          reason: "manual",
          willRetry: false,
        },
      },
      fromExtension: true,
      reason: "manual",
      willRetry: false,
    }, ctx);

    const after = await Bun.file(logPath).text();
    const appended = after.slice(before.length).trim().split("\n").filter(Boolean).map((line) => JSON.parse(line));
    expect(appended.some((entry) => entry.event === "session_compact" && entry.compactionEntryId === "test-compaction-id")).toBe(true);
  });

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

  it("does not claim delivery when coordinator submission throws synchronously", async () => {
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

    expect(attempts).toBe(1);
    expect(sentMessages).toHaveLength(0);
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

  it("preserves active-turn state after canceled compaction", async () => {
    const { handlers } = await getRegisteredHandlers();

    handlers.agent_start[0]({ type: "agent_start" });
    const canceled = handlers.session_before_compact[0]({
      preparation: basePreparation,
      branchEntries: [messageEntry("1", userMsg("too small"))],
      customInstructions: "__PI_VCC_MANUAL_BYPASS__",
    });
    expect(canceled).toEqual({ cancel: true });

    const result = handlers.session_before_compact[0]({
      preparation: basePreparation,
      branchEntries: compactableEntries(),
    });
    expect(result.compaction.details.interruptedInFlightTurn).toBe(true);
    expect(result.compaction.details.requiresContinuation).toBe(true);
  });
});
