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
  options: { sendMessageThrows?: boolean } = {},
) => {
  (globalThis as any)[PI_VCC_LOAD_MARKER] = piVccLoaded;

  const handlers: HandlerMap = {};
  const commands: CommandMap = {};
  const tools: ToolMap = {};
  const notifications: Array<{ message: string; level: string }> = [];
  const compactCalls: Array<any> = [];
  const sentMessages: Array<{ message: any; options: any }> = [];

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
    sendMessage: (message: any, messageOptions: any) => {
      if (options.sendMessageThrows) throw new Error("send failed");
      sentMessages.push({ message, options: messageOptions });
    },
  } as any);

  return { handlers, commands, tools, notifications, compactCalls, sentMessages, ctx };
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

  test("hard backstop auto-compacts at 80% and ratchets unchanged usage", async () => {
    let percent = 80.123456;
    const { handlers, compactCalls, ctx } = setup(() => percent);

    await handlers.turn_end?.(assistantStop, ctx);
    expect(compactCalls).toHaveLength(1);
    expect(compactCalls[0].customInstructions).toBeUndefined();
    compactCalls[0].onComplete();

    await handlers.turn_end?.(assistantStop, ctx);
    expect(compactCalls).toHaveLength(1);

    percent = 80.123457;
    await handlers.turn_end?.(assistantStop, ctx);
    expect(compactCalls).toHaveLength(2);
  });

  test("does not compact during post-compaction tool turns even when usage changes", async () => {
    let percent = 80.123456;
    const { handlers, compactCalls, ctx } = setup(() => percent);

    await handlers.turn_end?.(assistantStop, ctx);
    compactCalls[0].onComplete();

    percent = 80.5;
    await handlers.turn_end?.(assistantToolUse(), ctx);

    expect(compactCalls).toHaveLength(1);

    await handlers.turn_end?.(assistantStop, ctx);
    expect(compactCalls).toHaveLength(2);
  });

  test("core auto-compaction waits for a post-compaction assistant response", async () => {
    let percent = 80.123456;
    const { handlers, compactCalls, notifications, ctx } = setup(() => percent);

    await handlers.turn_end?.(assistantStop, ctx);
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

  test("event matrix prevents repeated hard-backstop compaction across tool loops", async () => {
    let percent = 80.25;
    const { handlers, compactCalls, ctx } = setup(() => percent);

    await handlers.turn_end?.(assistantStop, ctx);
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
    }
    expect(compactCalls).toHaveLength(1);

    await handlers.turn_end?.(assistantStop, ctx);
    expect(compactCalls).toHaveLength(2);
  });
});
