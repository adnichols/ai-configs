import { describe, expect, test } from "bun:test";

import percentageCompaction, {
  COMPACTION_NUDGE_PERCENT,
  COMPACTION_STRONG_NUDGE_PERCENT,
  HARD_AUTO_COMPACTION_PERCENT,
  PI_VCC_LOAD_MARKER,
  PI_VCC_MANUAL_BYPASS_MARKER,
} from "../_pi/extensions/percentage-compaction";

type HandlerMap = Record<string, (event: any, ctx: any) => any>;
type CommandMap = Record<string, { description: string; handler: (args: string, ctx: any) => any }>;
type ToolMap = Record<string, any>;

const setup = (
  percent: number | null | (() => number | null) = COMPACTION_NUDGE_PERCENT + 1,
  piVccLoaded = true,
  options: { sendMessageThrows?: boolean; authority?: "legacy" | "coordinator" } = {},
) => {
  (globalThis as any)[PI_VCC_LOAD_MARKER] = piVccLoaded;
  process.env.PI_VCC_CONTINUATION_AUTHORITY = options.authority ?? "legacy";

  const handlers: HandlerMap = {};
  const commands: CommandMap = {};
  const tools: ToolMap = {};
  const notifications: Array<{ message: string; level: string }> = [];
  const compactCalls: Array<any> = [];
  const sentMessages: Array<{ message: any; options: any }> = [];
  const appendedEntries: Array<{ customType: string; data: any }> = [];
  const emittedEvents: Array<{ channel: string; data: any }> = [];
  let remainingSendMessageFailures = options.sendMessageThrows ? Number.POSITIVE_INFINITY : 0;
  if (typeof (options as any).sendMessageFailures === "number") {
    remainingSendMessageFailures = (options as any).sendMessageFailures;
  }

  const ctx = {
    ui: {
      notify: (message: string, level: string) => {
        notifications.push({ message, level });
      },
    },
    compact: (options?: any) => {
      compactCalls.push(options ?? {});
    },
    getContextUsage: () => {
      const currentPercent = typeof percent === "function" ? percent() : percent;
      return currentPercent === null ? null : { percent: currentPercent, contextWindow: 272000 };
    },
  };

  percentageCompaction({
    on: (event: string, handler: (event: any, ctx: any) => any) => {
      handlers[event] = handler;
    },
    registerCommand: (name: string, command: any) => {
      commands[name] = command;
    },
    registerTool: (tool: any) => {
      tools[tool.name] = tool;
    },
    appendEntry: (customType: string, data: any) => {
      appendedEntries.push({ customType, data });
    },
    events: {
      emit: (channel: string, data: any) => emittedEvents.push({ channel, data }),
      on: () => () => {},
    },
    sendMessage: (message: any, messageOptions: any) => {
      if (remainingSendMessageFailures > 0) {
        remainingSendMessageFailures -= 1;
        throw new Error("send failed");
      }
      sentMessages.push({ message, options: messageOptions });
    },
  } as any);

  return { handlers, commands, tools, notifications, compactCalls, sentMessages, appendedEntries, emittedEvents, ctx };
};

const assistantStop = { message: { role: "assistant", stopReason: "stop" }, toolResults: [] };
const assistantStopWithText = (text: string) => ({
  message: { role: "assistant", stopReason: "stop", content: [{ type: "text", text }] },
  toolResults: [],
});
const toolResult = (
  toolCallId = "tc_1",
  toolName = "compact_context",
  text = "queued",
  isError = false,
) => ({
  role: "toolResult",
  toolCallId,
  toolName,
  content: [{ type: "text", text }],
  isError,
  timestamp: Date.now(),
});
const assistantToolUse = (toolCount = 1, toolResults = [toolResult()]) => ({
  message: {
    role: "assistant",
    stopReason: "toolUse",
    content: Array.from({ length: toolCount }, (_, i) => ({
      type: "toolCall",
      id: i === 0 ? "tc_1" : `tc_${i + 1}`,
      name: i === 0 ? "compact_context" : "read",
      arguments: {},
    })),
  },
  toolResults,
});
const userTurn = (text = "new request") => ({
  message: { role: "user", content: text },
  toolResults: [],
});
const delay = (ms = 75) => new Promise((resolve) => setTimeout(resolve, ms));

describe("percentage-compaction extension", () => {
  test("does not auto-compact at 60%; sends a model-visible soft nudge", async () => {
    const { handlers, compactCalls, sentMessages, notifications, ctx } = setup(60.4);

    await handlers.turn_end?.(assistantStop, ctx);

    expect(compactCalls).toHaveLength(0);
    expect(sentMessages).toHaveLength(1);
    expect(sentMessages[0].message.customType).toBe("compaction-nudge");
    expect(sentMessages[0].message.content).toContain("compact_context");
    expect(sentMessages[0].message.content).toContain("not an instruction to compact immediately");
    expect(sentMessages[0].options).toEqual({ deliverAs: "steer", triggerTurn: true });
    expect(notifications.some((entry) => entry.message.includes("soft nudge"))).toBe(true);
  });

  test("does not auto-compact at 75%; sends one rate-limited strong nudge", async () => {
    const { handlers, compactCalls, sentMessages, ctx } = setup(75.2);

    await handlers.turn_end?.(assistantStop, ctx);
    await handlers.turn_end?.(assistantStop, ctx);

    expect(compactCalls).toHaveLength(0);
    expect(sentMessages).toHaveLength(1);
    expect(sentMessages[0].message.details.band).toBe("strong");
    expect(sentMessages[0].message.content).toContain(`${HARD_AUTO_COMPACTION_PERCENT}% is the hard automatic backstop`);
  });

  test("compact_context queues marker plus JSON intent for the next safe post-tool boundary", async () => {
    const { handlers, tools, compactCalls, ctx } = setup(65);

    const result = await tools.compact_context.execute("tc_1", {
      reason: "finished test loop",
      boundary: "after_test_loop",
      preserve: "keep failing test names",
    });
    expect(result.content[0].text).toContain("queued");

    await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1")]), ctx);

    expect(compactCalls).toHaveLength(1);
    expect(compactCalls[0].customInstructions).toContain(PI_VCC_MANUAL_BYPASS_MARKER);
    expect(compactCalls[0].customInstructions).toContain('"source":"compact_context"');
    expect(compactCalls[0].customInstructions).toContain('"boundary":"after_test_loop"');
    expect(compactCalls[0].customInstructions).toContain('"preserve":"keep failing test names"');
  });

  test("compact_context can be model-requested below the nudge threshold", async () => {
    const { handlers, tools, compactCalls, ctx } = setup(40);

    await tools.compact_context.execute("tc_1", {
      reason: "explicit semantic boundary",
      boundary: "subtask_complete",
    });
    await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1")]), ctx);

    expect(compactCalls).toHaveLength(1);
    expect(compactCalls[0].customInstructions).toContain('"reason":"explicit semantic boundary"');
  });

  test("compact_context still runs when context usage is unknown", async () => {
    const { handlers, tools, compactCalls, ctx } = setup(null);

    await tools.compact_context.execute("tc_1", {
      reason: "provider lacks telemetry",
      boundary: "subtask_complete",
    });
    await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1")]), ctx);

    expect(compactCalls).toHaveLength(1);
    expect(compactCalls[0].customInstructions).toContain('"reason":"provider lacks telemetry"');
  });

  test("compact_context defers after fresh failure output until an assistant interprets it", async () => {
    const { handlers, tools, compactCalls, ctx } = setup(65);

    await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_fail", "bash", "Image not found", true)]), ctx);
    await tools.compact_context.execute("tc_1", {
      reason: "after failing tests",
      boundary: "after_test_loop",
    });
    await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1", "compact_context", "compact queued")]), ctx);

    expect(compactCalls).toHaveLength(0);

    await handlers.turn_end?.(assistantStopWithText("I interpreted the test error and the failure is understood."), ctx);
    expect(compactCalls).toHaveLength(1);
  });

  test("failed model-visible nudge delivery is retried instead of marked delivered", async () => {
    const { handlers, sentMessages, notifications, ctx } = setup(60.4, true, { sendMessageThrows: true });

    await handlers.turn_end?.(assistantStop, ctx);
    await handlers.turn_end?.(assistantStop, ctx);

    expect(sentMessages).toHaveLength(0);
    expect(notifications.filter((entry) => entry.message.includes("nudge delivery failed"))).toHaveLength(2);
  });

  test("compact_context mixed tool batches defer until a later completed assistant boundary", async () => {
    const { handlers, tools, compactCalls, ctx } = setup(65);

    await tools.compact_context.execute("tc_1", {
      reason: "maybe compact",
      boundary: "subtask_complete",
    });

    await handlers.turn_end?.(assistantToolUse(2, [
      toolResult("tc_1", "compact_context", "compact queued"),
      toolResult("tc_2", "read", "sibling output that must be interpreted"),
    ]), ctx);
    expect(compactCalls).toHaveLength(0);

    await handlers.turn_end?.(assistantStop, ctx);
    expect(compactCalls).toHaveLength(1);
  });

  test("compact_context mixed tool batches defer in real assistant-tool-result order", async () => {
    const { handlers, tools, compactCalls, ctx } = setup(65);

    await handlers.turn_end?.(assistantToolUse(2, []), ctx);
    await tools.compact_context.execute("tc_1", {
      reason: "maybe compact",
      boundary: "subtask_complete",
    });
    await handlers.turn_end?.({
      message: toolResult("tc_1", "compact_context", "compact queued"),
      toolResults: [
        toolResult("tc_1", "compact_context", "compact queued"),
        toolResult("tc_2", "read", "sibling output that must be interpreted"),
      ],
    }, ctx);
    expect(compactCalls).toHaveLength(0);

    await handlers.turn_end?.(assistantStop, ctx);
    expect(compactCalls).toHaveLength(1);
  });

  test("compact_context detects sibling batches when execute precedes assistant toolUse turn_end", async () => {
    const { handlers, tools, compactCalls, ctx } = setup(65);

    await tools.compact_context.execute("tc_1", {
      reason: "maybe compact",
      boundary: "subtask_complete",
    });
    await handlers.turn_end?.(assistantToolUse(2, []), ctx);
    await handlers.turn_end?.({
      message: toolResult("tc_1", "compact_context", "compact queued"),
      toolResults: [],
    }, ctx);
    await handlers.turn_end?.({
      message: toolResult("tc_2", "read", "sibling output that must be interpreted"),
      toolResults: [],
    }, ctx);
    expect(compactCalls).toHaveLength(0);

    await handlers.turn_end?.(assistantStopWithText("I interpreted the sibling output."), ctx);
    expect(compactCalls).toHaveLength(1);
  });

  test("compact_context ignores unrelated tool results before its own result", async () => {
    const { handlers, tools, compactCalls, ctx } = setup(65);

    await tools.compact_context.execute("tc_1", {
      reason: "maybe compact",
      boundary: "subtask_complete",
    });
    await handlers.turn_end?.({
      message: toolResult("tc_other", "read", "unrelated output"),
      toolResults: [],
    }, ctx);
    expect(compactCalls).toHaveLength(0);

    await handlers.turn_end?.({
      message: toolResult("tc_1", "compact_context", "compact queued"),
      toolResults: [],
    }, ctx);
    expect(compactCalls).toHaveLength(1);
  });

  test("hard backstop schedules, not immediate-compacts", async () => {
    let percent = 80.123456;
    const { handlers, compactCalls, ctx } = setup(() => percent);

    await handlers.turn_end?.(assistantStop, ctx);
    expect(compactCalls).toHaveLength(0);
    await delay(0);
    expect(compactCalls).toHaveLength(1);
    expect(compactCalls[0].customInstructions).toBeUndefined();
    compactCalls[0].onComplete();

    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(1);

    percent = 80.123457;
    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(2);
  });

  test("compaction failure sends one continuation for an interrupted turn", async () => {
    const { handlers, compactCalls, sentMessages, notifications, ctx } = setup(96.2);

    await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1", "read", "source")]), ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(1);
    compactCalls[0].onError(new Error("Cannot read properties of undefined (reading 'signal')"));
    await delay();

    expect(sentMessages).toHaveLength(1);
    expect(sentMessages[0].message.customType).toBe("pi-vcc-continuation");
    expect(sentMessages[0].message.details.reason).toBe("failed");
    expect(sentMessages[0].options).toEqual({ deliverAs: "steer", triggerTurn: true });
    expect(notifications.some((entry) => entry.level === "warning" && entry.message.includes("continuing interrupted turn"))).toBe(true);
  });

  test("compaction cancelled sends one continuation for an interrupted turn", async () => {
    const { handlers, compactCalls, sentMessages, ctx } = setup(96.2);

    await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1", "read", "source")]), ctx);
    await delay(0);
    compactCalls[0].onError(new Error("Compaction cancelled"));
    compactCalls[0].onError(new Error("Compaction cancelled"));
    await delay();

    expect(sentMessages).toHaveLength(1);
    expect(sentMessages[0].message.customType).toBe("pi-vcc-continuation");
    expect(sentMessages[0].message.details.reason).toBe("cancelled");
  });

  test("completed assistant response does not continue after compaction failure", async () => {
    const { handlers, compactCalls, sentMessages, ctx } = setup(96.2);

    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    compactCalls[0].onError(new Error("Cannot read properties of undefined (reading 'signal')"));
    await delay();

    expect(sentMessages).toHaveLength(0);
  });

  test("integrated observed race recovers once and suppresses same-percent retry", async () => {
    const { handlers, compactCalls, sentMessages, notifications, ctx } = setup(96.2);

    await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1", "read", "source")]), ctx);
    expect(compactCalls).toHaveLength(0);

    const coreResult = await handlers.session_before_compact?.({ customInstructions: undefined }, ctx);
    expect(coreResult).toEqual({ cancel: true });
    expect(notifications.some((entry) => entry.message.includes("pi-vcc already scheduled 96%"))).toBe(true);

    await delay(0);
    expect(compactCalls).toHaveLength(1);
    compactCalls[0].onError(new Error("Compaction cancelled"));
    compactCalls[0].onError(new Error("Cannot read properties of undefined (reading 'signal')"));
    compactCalls[0].onError(new Error("Cannot read properties of undefined (reading 'signal')"));
    await delay();

    expect(sentMessages).toHaveLength(1);
    expect(sentMessages[0].message.customType).toBe("pi-vcc-continuation");
    expect(sentMessages[0].message.details.reason).toBe("cancelled");

    await handlers.turn_end?.(assistantToolUse(1, []), ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(1);

    const samePercentCoreResult = await handlers.session_before_compact?.({ customInstructions: undefined }, ctx);
    expect(samePercentCoreResult).toEqual({ cancel: true });
    expect(compactCalls).toHaveLength(1);
  });

  test("stale error callbacks cannot clear a newer compaction attempt", async () => {
    let percent = 96.2;
    const { handlers, compactCalls, sentMessages, ctx } = setup(() => percent);

    await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1", "read", "source")]), ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(1);
    const staleOnError = compactCalls[0].onError;
    compactCalls[0].onComplete();

    percent = 50;
    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(1);

    percent = 97.0;
    await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_2", "read", "source")]), ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(2);

    staleOnError(new Error("Cannot read properties of undefined (reading 'signal')"));
    expect(sentMessages).toHaveLength(0);

    compactCalls[1].onError(new Error("Compaction cancelled"));
    await delay();
    expect(sentMessages).toHaveLength(0);

    percent = 97.1;
    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(3);
  });

  test("scheduled pi-vcc compaction cancels core overflow and willRetry attempts", async () => {
    const overflow = setup(96.2);
    await overflow.handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1", "read", "source")]), overflow.ctx);
    const overflowResult = await overflow.handlers.session_before_compact?.(
      { customInstructions: undefined, reason: "overflow" },
      overflow.ctx,
    );
    expect(overflowResult).toEqual({ cancel: true });
    await delay(0);
    expect(overflow.compactCalls).toHaveLength(1);

    const willRetry = setup(96.2);
    await willRetry.handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1", "read", "source")]), willRetry.ctx);
    const retryResult = await willRetry.handlers.session_before_compact?.(
      { customInstructions: undefined, willRetry: true },
      willRetry.ctx,
    );
    expect(retryResult).toEqual({ cancel: true });
    await delay(0);
    expect(willRetry.compactCalls).toHaveLength(1);
  });

  test("pending failure continuation blocks replacement compaction until safe", async () => {
    const { handlers, compactCalls, sentMessages, ctx } = setup(96.2);

    await handlers.turn_end?.(assistantToolUse(2, []), ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(1);
    compactCalls[0].onError(new Error("Compaction cancelled"));
    await delay();
    expect(sentMessages).toHaveLength(0);

    await handlers.turn_end?.(assistantToolUse(1, []), ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(1);
    expect(sentMessages).toHaveLength(0);

    const overflowResult = await handlers.session_before_compact?.(
      { customInstructions: undefined, reason: "overflow" },
      ctx,
    );
    expect(overflowResult).toEqual({ cancel: true });
    const retryResult = await handlers.session_before_compact?.(
      { customInstructions: undefined, willRetry: true },
      ctx,
    );
    expect(retryResult).toEqual({ cancel: true });
    expect(compactCalls).toHaveLength(1);
    expect(sentMessages).toHaveLength(0);

    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    expect(sentMessages).toHaveLength(1);
    expect(sentMessages[0].message.customType).toBe("pi-vcc-continuation");
  });

  test("active hard-backstop no-cut sends one continuation and clears state", async () => {
    const { handlers, compactCalls, sentMessages, notifications, ctx } = setup(96.2);

    await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1", "read", "source")]), ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(1);
    compactCalls[0].onError(new Error("Nothing to compact (session too small)"));
    await delay();

    expect(sentMessages).toHaveLength(1);
    expect(sentMessages[0].message.customType).toBe("pi-vcc-no-cut-continuation");
    expect(sentMessages[0].message.content).toContain("no safe compaction cut was available");
    expect(sentMessages[0].options).toEqual({ deliverAs: "steer", triggerTurn: true });
    expect(notifications.some((entry) => entry.message.includes("No safe compaction cut available"))).toBe(true);

    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(1);
  });

  test("hard-backstop no-cut defers continuation until pending tool results are delivered", async () => {
    const { handlers, compactCalls, sentMessages, ctx } = setup(96.2);

    await handlers.turn_end?.(assistantToolUse(2, []), ctx);
    await delay(0);
    await handlers.turn_end?.({ message: toolResult("tc_1", "compact_context", "queued"), toolResults: [] }, ctx);
    compactCalls[0].onError(new Error("Nothing to compact (session too small)"));
    await delay();
    expect(sentMessages).toHaveLength(0);

    await handlers.turn_end?.({ message: toolResult("tc_2", "read", "source"), toolResults: [] }, ctx);
    await delay();
    expect(sentMessages).toHaveLength(1);
  });

  test("no-cut continuation retries once then succeeds", async () => {
    const { handlers, compactCalls, sentMessages, notifications, ctx } = setup(96.2, true, { sendMessageFailures: 1 } as any);

    await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1", "read", "source")]), ctx);
    await delay(0);
    compactCalls[0].onError(new Error("Nothing to compact (session too small)"));
    await delay(700);

    expect(sentMessages).toHaveLength(1);
    expect(sentMessages[0].message.details.deliveryAttempts).toBe(2);
    expect(notifications.some((entry) => entry.message.includes("delivery failed after"))).toBe(false);
  });

  test("permanent no-cut continuation delivery failure warns without stuck compaction", async () => {
    const originalDateNow = Date.now;
    let now = 0;
    Date.now = () => {
      now += 6000;
      return now;
    };
    try {
      const { handlers, compactCalls, notifications, ctx } = setup(96.2, true, { sendMessageThrows: true });

      await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1", "read", "source")]), ctx);
      await delay(0);
      compactCalls[0].onError(new Error("Nothing to compact (session too small)"));
      await delay();

      expect(notifications.some((entry) => entry.level === "warning" && entry.message.includes("No-cut continuation delivery failed"))).toBe(true);
      await handlers.turn_end?.(assistantStop, ctx);
      await delay(0);
      expect(compactCalls).toHaveLength(1);
    } finally {
      Date.now = originalDateNow;
    }
  });

  test("idle hard-backstop no-cut does not auto-resume", async () => {
    const { handlers, compactCalls, sentMessages, ctx } = setup(96.2);

    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    compactCalls[0].onError(new Error("Nothing to compact (session too small)"));
    await delay();

    expect(sentMessages).toHaveLength(0);
  });

  test("user-message hard-backstop no-cut does not auto-resume", async () => {
    const { handlers, compactCalls, sentMessages, ctx } = setup(96.2);

    await handlers.turn_end?.(userTurn("new instruction"), ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(1);
    compactCalls[0].onError(new Error("Nothing to compact (session too small)"));
    await delay();

    expect(sentMessages).toHaveLength(0);
  });

  test("manual and compact_context no-cut do not auto-resume", async () => {
    const manual = setup(96.2);
    await manual.commands["compact-now"].handler("", manual.ctx);
    manual.compactCalls[0].onError(new Error("Nothing to compact (session too small)"));
    await delay();
    expect(manual.sentMessages).toHaveLength(0);

    const model = setup(96.2);
    await model.tools.compact_context.execute("tc_1", { reason: "boundary", boundary: "after_test_loop" });
    await model.handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1")]), model.ctx);
    model.compactCalls[0].onError(new Error("Nothing to compact (session too small)"));
    await delay();
    expect(model.sentMessages).toHaveLength(0);
  });

  test("same-percent hard-backstop failure retry is suppressed after continuation delivery", async () => {
    const { handlers, compactCalls, sentMessages, ctx } = setup(96.2);

    await handlers.turn_end?.(assistantToolUse(1, []), ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(1);

    compactCalls[0].onError(new Error("provider failed"));
    await handlers.turn_end?.({
      message: toolResult("tc_1", "read", "source"),
      toolResults: [],
    }, ctx);
    await delay(0);

    expect(sentMessages).toHaveLength(1);
    expect(sentMessages[0].message.customType).toBe("pi-vcc-continuation");
    expect(compactCalls).toHaveLength(1);

    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(1);
  });

  test("same floored no-cut percent is suppressed until usage rises or a user speaks", async () => {
    let percent = 96.2;
    const { handlers, compactCalls, ctx } = setup(() => percent);

    await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1", "read", "source")]), ctx);
    await delay(0);
    compactCalls[0].onError(new Error("Nothing to compact (session too small)"));
    await delay();

    percent = 95.9;
    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(1);

    percent = 96.9;
    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(1);

    percent = 97.0;
    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(2);

    compactCalls[1].onError(new Error("Nothing to compact (session too small)"));
    await handlers.message_end?.(userTurn("new instruction"), ctx);
    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(3);
  });

  test("model-visible no-cut continuation does not re-arm retry suppression as user input", async () => {
    const { handlers, compactCalls, sentMessages, ctx } = setup(96.2);

    await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1", "read", "source")]), ctx);
    await delay(0);
    compactCalls[0].onError(new Error("Nothing to compact (session too small)"));
    await delay();
    expect(sentMessages).toHaveLength(1);

    await handlers.message_end?.({ message: { role: "user", customType: "pi-vcc-no-cut-continuation" } }, ctx);
    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(1);
  });

  test("no-cut reset allows later interrupted hard-backstop attempt", async () => {
    let percent = 96.2;
    const { handlers, compactCalls, ctx } = setup(() => percent);

    await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1", "read", "source")]), ctx);
    await delay(0);
    compactCalls[0].onError(new Error("Nothing to compact (session too small)"));
    await delay();

    percent = 97.0;
    await handlers.turn_end?.(assistantToolUse(1, []), ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(2);
  });

  test("core auto-compaction is canceled above hard threshold unless extension-managed", async () => {
    const { handlers, notifications, ctx } = setup(96.9);

    const result = await handlers.session_before_compact?.({ customInstructions: undefined }, ctx);

    expect(result).toEqual({ cancel: true });
    expect(notifications.some((entry) => entry.message.includes("repo-managed hard backstop handles 96%"))).toBe(true);
  });

  test("core auto-compaction honors same floored no-cut suppression", async () => {
    let percent = 96.2;
    const { handlers, compactCalls, notifications, ctx } = setup(() => percent);

    await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1", "read", "source")]), ctx);
    await delay(0);
    compactCalls[0].onError(new Error("Nothing to compact (session too small)"));
    await delay();

    percent = 96.9;
    const suppressed = await handlers.session_before_compact?.({ customInstructions: undefined }, ctx);
    expect(suppressed).toEqual({ cancel: true });
    expect(notifications.some((entry) => entry.message.includes("no safe cut was available at 96%"))).toBe(true);

    await handlers.message_end?.(userTurn("new instruction"), ctx);
    percent = 96.2;
    await handlers.turn_end?.(assistantStop, ctx);
    const extensionManaged = await handlers.session_before_compact?.({ customInstructions: undefined }, ctx);
    expect(extensionManaged).toEqual({ cancel: true });
    expect(notifications.some((entry) => entry.message.includes("pi-vcc already scheduled 96%"))).toBe(true);
    await delay(0);
    expect(compactCalls).toHaveLength(2);

    compactCalls[1].onError(new Error("Nothing to compact (session too small)"));
    percent = 97.0;
    const rearmedByUsage = await handlers.session_before_compact?.({ customInstructions: undefined }, ctx);
    expect(rearmedByUsage).toEqual({ cancel: true });
  });

  test("successful core compaction clears no-cut retry suppression", async () => {
    let percent = 96.2;
    const { handlers, compactCalls, ctx } = setup(() => percent);

    await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1", "read", "source")]), ctx);
    await delay(0);
    compactCalls[0].onError(new Error("Nothing to compact (session too small)"));
    await delay();

    await handlers.session_compact?.({}, ctx);
    percent = 80.5;
    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);

    expect(compactCalls).toHaveLength(2);
  });

  test("new compaction attempt clears stale pending no-cut continuation", async () => {
    let percent = 96.2;
    const { handlers, compactCalls, sentMessages, ctx } = setup(() => percent);

    await handlers.turn_end?.(assistantToolUse(2, []), ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(1);
    compactCalls[0].onError(new Error("Nothing to compact (session too small)"));
    await delay();
    expect(sentMessages).toHaveLength(0);

    percent = 97.0;
    await handlers.turn_end?.(assistantToolUse(1, []), ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(2);

    await handlers.turn_end?.({
      message: toolResult("tc_1", "compact_context", "queued"),
      toolResults: [toolResult("tc_2", "read", "source")],
    }, ctx);
    await delay();

    expect(sentMessages).toHaveLength(0);
  });

  test("does not compact during post-compaction tool turns even when usage changes", async () => {
    let percent = 80.123456;
    const { handlers, compactCalls, ctx } = setup(() => percent);

    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    compactCalls[0].onComplete();

    percent = 80.5;
    await handlers.turn_end?.(assistantToolUse(), ctx);
    await delay(0);

    expect(compactCalls).toHaveLength(1);

    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(2);
  });

  test("core auto-compaction waits for a post-compaction assistant response", async () => {
    let percent = 80.123456;
    const { handlers, compactCalls, notifications, ctx } = setup(() => percent);

    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    compactCalls[0].onComplete();

    percent = 80.5;
    const result = await handlers.session_before_compact?.(
      { customInstructions: undefined },
      ctx,
    );

    expect(result).toEqual({ cancel: true });
    expect(notifications.some((entry) => entry.message.includes("waiting for the next assistant response"))).toBe(true);
  });

  test("core auto-compaction is blocked for the same post-compaction usage value", async () => {
    const { handlers, compactCalls, notifications, ctx } = setup(80.123456);

    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    compactCalls[0].onComplete();
    await handlers.turn_end?.(assistantStop, ctx);

    const result = await handlers.session_before_compact?.(
      { customInstructions: undefined },
      ctx,
    );

    expect(result).toEqual({ cancel: true });
    expect(notifications.some((entry) => entry.message.includes("usage is unchanged at 80.123456%"))).toBe(true);
  });

  test("fresh failure output suppresses nudges but not hard backstop", async () => {
    const { handlers, sentMessages, compactCalls, ctx } = setup(75);

    await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_fail", "bash", "tests failed with error", true)]), ctx);
    expect(sentMessages).toHaveLength(0);
    expect(compactCalls).toHaveLength(0);

    const hard = setup(80.5);
    await hard.handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_fail", "bash", "tests failed with error", true)]), hard.ctx);
    await delay(0);
    expect(hard.compactCalls).toHaveLength(1);
  });

  test("core auto-compaction is blocked below hard threshold without bypass", async () => {
    const { handlers, ctx } = setup(79.9);

    const result = await handlers.session_before_compact?.(
      { customInstructions: undefined },
      ctx,
    );

    expect(result).toEqual({ cancel: true });
  });

  test("core overflow retries bypass the extension hard threshold gate only when pi-vcc is loaded", async () => {
    const { handlers, ctx } = setup(79.9);

    const overflowReason = await handlers.session_before_compact?.(
      { customInstructions: undefined, reason: "overflow" },
      ctx,
    );
    const willRetry = await handlers.session_before_compact?.(
      { customInstructions: undefined, willRetry: true },
      ctx,
    );

    expect(overflowReason).toBeUndefined();
    expect(willRetry).toBeUndefined();

    const missing = setup(79.9, false);
    const missingOverflow = await missing.handlers.session_before_compact?.(
      { customInstructions: undefined, reason: "overflow" },
      missing.ctx,
    );
    const missingRetry = await missing.handlers.session_before_compact?.(
      { customInstructions: undefined, willRetry: true },
      missing.ctx,
    );

    expect(missingOverflow).toEqual({ cancel: true });
    expect(missingRetry).toEqual({ cancel: true });
    expect(missing.notifications.filter((entry) => entry.message.includes("Pi-vcc is not loaded"))).toHaveLength(2);
  });

  test("manual compact-now prefixes optional instructions with the bypass marker", async () => {
    const { commands, handlers, compactCalls, ctx } = setup(20);

    await commands["compact-now"].handler("keep goals", ctx);
    expect(compactCalls).toHaveLength(1);
    expect(compactCalls[0]?.customInstructions).toBe(`${PI_VCC_MANUAL_BYPASS_MARKER}\nkeep goals`);

    const result = await handlers.session_before_compact?.(
      { customInstructions: compactCalls[0]?.customInstructions },
      ctx,
    );
    expect(result).toBeUndefined();
  });

  test("manual compact-now and marker bypass allow pi-vcc compaction below hard threshold", async () => {
    const { commands, handlers, compactCalls, ctx } = setup(20);

    await commands["compact-now"].handler("", ctx);
    expect(compactCalls).toHaveLength(1);
    expect(compactCalls[0]?.customInstructions).toBe(PI_VCC_MANUAL_BYPASS_MARKER);

    const result = await handlers.session_before_compact?.(
      { customInstructions: PI_VCC_MANUAL_BYPASS_MARKER },
      ctx,
    );
    expect(result).toBeUndefined();
  });

  test("status reports nudge, strong, hard backstop, and last reason", async () => {
    const { commands, notifications, ctx } = setup(66);

    await commands["compact-status"].handler("", ctx);

    expect(notifications.at(-1)?.message).toContain("nudge: 60%");
    expect(notifications.at(-1)?.message).toContain("strong: 75%");
    expect(notifications.at(-1)?.message).toContain("hard auto: 80%");
  });

  test("marker compaction is canceled when pi-vcc is not loaded", async () => {
    const { handlers, compactCalls, notifications, ctx } = setup(80.2, false);

    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);

    expect(compactCalls).toHaveLength(0);
    expect(notifications.some((entry) => entry.level === "error" && entry.message.includes("Pi-vcc is not loaded"))).toBe(true);

    const result = await handlers.session_before_compact?.(
      { customInstructions: PI_VCC_MANUAL_BYPASS_MARKER },
      ctx,
    );

    expect(result).toEqual({ cancel: true });
  });

  test("unknown usage compaction is still canceled when pi-vcc is not loaded", async () => {
    const { handlers, notifications, ctx } = setup(() => null as any, false);

    const result = await handlers.session_before_compact?.(
      { customInstructions: undefined },
      ctx,
    );

    expect(result).toEqual({ cancel: true });
    expect(notifications.some((entry) => entry.level === "error" && entry.message.includes("Pi-vcc is not loaded"))).toBe(true);
  });

  test("coordinator authority publishes durable request before advisory wake and never sends legacy continuation", async () => {
    const { handlers, compactCalls, sentMessages, appendedEntries, emittedEvents, ctx } = setup(96.2, true, { authority: "coordinator" });

    await handlers.turn_end?.(assistantToolUse(1, [toolResult("tc_1", "read", "source")]), ctx);
    await delay(0);
    compactCalls[0].onError(new Error("Compaction cancelled"));

    expect(sentMessages.filter((entry) => entry.message.customType === "pi-vcc-continuation")).toHaveLength(0);
    expect(appendedEntries).toHaveLength(1);
    expect(appendedEntries[0].customType).toBe("pi-vcc-continuation-request");
    expect(emittedEvents).toHaveLength(1);
    expect(emittedEvents[0].channel).toBe("pi-vcc:continuation-requested");
    expect(appendedEntries[0].data.snapshot.transactionId).toBe(emittedEvents[0].data.transactionId);
    expect(appendedEntries[0].data.snapshot.origin).toBe("hard-backstop");
    expect(appendedEntries[0].data.snapshot.reason).toBe("cancelled");
  });

  test("compact_context resume policy is persisted and active/terminal/auto semantics are deterministic", async () => {
    const active = setup(65, true, { authority: "coordinator" });
    const activeResult = await active.tools.compact_context.execute("tc_active", {
      reason: "done",
      boundary: "subtask_complete",
      resumePolicy: "active",
    });
    expect(activeResult.details.resumePolicy).toBe("active");
    expect(activeResult.details.willResume).toBe(true);

    const terminal = setup(65, true, { authority: "coordinator" });
    const terminalResult = await terminal.tools.compact_context.execute("tc_terminal", {
      reason: "continue remaining work",
      boundary: "after_test_loop",
      resumePolicy: "terminal",
    });
    expect(terminalResult.details.willResume).toBe(false);

    const auto = setup(65, true, { authority: "coordinator" });
    const autoResult = await auto.tools.compact_context.execute("tc_auto", {
      reason: "done",
      boundary: "after_test_loop",
    });
    expect(autoResult.details.resumePolicy).toBe("auto");
    expect(autoResult.details.willResume).toBe(true);
    expect(activeResult.details.requestId).not.toBe(terminalResult.details.requestId);
  });

  test("mismatched hard-backstop completion cannot erase pending compact_context request", async () => {
    let percent = 81;
    const { handlers, tools, compactCalls, ctx } = setup(() => percent, true, { authority: "coordinator" });
    const queued = await tools.compact_context.execute("tc_request", {
      reason: "remaining work",
      boundary: "subtask_complete",
      resumePolicy: "active",
    });

    await handlers.turn_end?.(assistantToolUse(2, []), ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(1);
    compactCalls[0].onComplete();

    percent = 65;
    await handlers.turn_end?.({ message: toolResult("tc_request"), toolResults: [] }, ctx);
    await handlers.turn_end?.(assistantStop, ctx);
    expect(compactCalls).toHaveLength(2);
    expect(compactCalls[1].customInstructions).toContain(queued.details.requestId);
  });

  test("event matrix prevents repeated hard-backstop compaction across tool loops", async () => {
    let percent = 80.25;
    const { handlers, compactCalls, ctx } = setup(() => percent);

    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(1);
    compactCalls[0].onComplete();

    percent = 80.75;
    for (let i = 0; i < 3; i += 1) {
      const coreResult = await handlers.session_before_compact?.(
        { customInstructions: undefined },
        ctx,
      );
      expect(coreResult).toEqual({ cancel: true });

      await handlers.turn_end?.(assistantToolUse(), ctx);
      await delay(0);
    }
    expect(compactCalls).toHaveLength(1);

    percent = 80.751;
    await handlers.turn_end?.(assistantStop, ctx);
    await delay(0);
    expect(compactCalls).toHaveLength(2);
  });
});
