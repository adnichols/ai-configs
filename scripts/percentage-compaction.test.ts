import { describe, expect, test } from "bun:test";

import percentageCompaction, {
  COMPACTION_THRESHOLD_PERCENT,
  PI_VCC_LOAD_MARKER,
  PI_VCC_MANUAL_BYPASS_MARKER,
} from "../_pi/extensions/percentage-compaction";

type HandlerMap = Record<string, (event: any, ctx: any) => any>;
type CommandMap = Record<string, { description: string; handler: (args: string, ctx: any) => any }>;

const setup = (percent: number | (() => number) = COMPACTION_THRESHOLD_PERCENT + 1, piVccLoaded = true) => {
  (globalThis as any)[PI_VCC_LOAD_MARKER] = piVccLoaded;

  const handlers: HandlerMap = {};
  const commands: CommandMap = {};
  const notifications: Array<{ message: string; level: string }> = [];
  const compactCalls: Array<any> = [];

  const ctx = {
    ui: {
      notify: (message: string, level: string) => {
        notifications.push({ message, level });
      },
    },
    compact: (options?: any) => {
      compactCalls.push(options ?? {});
    },
    getContextUsage: () => ({
      percent: typeof percent === "function" ? percent() : percent,
      contextWindow: 272000,
    }),
  };

  percentageCompaction({
    on: (event: string, handler: (event: any, ctx: any) => any) => {
      handlers[event] = handler;
    },
    registerCommand: (name: string, command: any) => {
      commands[name] = command;
    },
  } as any);

  return { handlers, commands, notifications, compactCalls, ctx };
};

describe("percentage-compaction extension", () => {
  test("proactively compacts at threshold on a safe assistant boundary", async () => {
    const { handlers, compactCalls, notifications, ctx } = setup(60.4);

    await handlers.turn_end?.(
      { message: { role: "assistant", stopReason: "stop" } },
      ctx,
    );

    expect(compactCalls).toHaveLength(1);
    expect(compactCalls[0]?.customInstructions).toBe(PI_VCC_MANUAL_BYPASS_MARKER);
    expect(notifications.some((entry) => entry.message.includes("Auto-compacting at 60%"))).toBe(true);
  });

  test("interrupts the current tool-using turn at the next turn boundary", async () => {
    const { handlers, compactCalls, notifications, ctx } = setup(61.2);

    await handlers.turn_end?.(
      { message: { role: "assistant", stopReason: "toolUse" } },
      ctx,
    );

    expect(compactCalls).toHaveLength(1);
    expect(compactCalls[0]?.customInstructions).toBe(PI_VCC_MANUAL_BYPASS_MARKER);
    expect(notifications.some((entry) => entry.message.includes("Interrupting agent for pi-vcc compaction"))).toBe(true);
  });

  test("ratchets auto-compaction until context usage reports a new value", async () => {
    let percent = 60.123456;
    const { handlers, compactCalls, ctx } = setup(() => percent);

    await handlers.turn_end?.(
      { message: { role: "assistant", stopReason: "stop" } },
      ctx,
    );
    compactCalls[0].onComplete();

    await handlers.turn_end?.(
      { message: { role: "assistant", stopReason: "stop" } },
      ctx,
    );

    expect(compactCalls).toHaveLength(1);

    percent = 60.123457;
    await handlers.turn_end?.(
      { message: { role: "assistant", stopReason: "stop" } },
      ctx,
    );

    expect(compactCalls).toHaveLength(2);
  });

  test("core auto-compaction is blocked for the same post-compaction usage value", async () => {
    const { handlers, compactCalls, notifications, ctx } = setup(61.234567);

    await handlers.turn_end?.(
      { message: { role: "assistant", stopReason: "stop" } },
      ctx,
    );
    compactCalls[0].onComplete();

    const result = await handlers.session_before_compact?.(
      { customInstructions: undefined },
      ctx,
    );

    expect(result).toEqual({ cancel: true });
    expect(notifications.some((entry) => entry.message.includes("usage is unchanged at 61.234567%"))).toBe(true);
  });

  test("manual compact-now bypasses the threshold gate", async () => {
    const { commands, handlers, compactCalls, ctx } = setup(20);

    await commands["compact-now"].handler("keep goals", ctx);

    expect(compactCalls).toHaveLength(1);
    expect(compactCalls[0]?.customInstructions).toBe("keep goals");

    const result = await handlers.session_before_compact?.(
      { customInstructions: "keep goals" },
      ctx,
    );

    expect(result).toBeUndefined();
  });

  test("core auto-compaction is still blocked below threshold without bypass", async () => {
    const { handlers, ctx } = setup(59.9);

    const result = await handlers.session_before_compact?.(
      { customInstructions: undefined },
      ctx,
    );

    expect(result).toEqual({ cancel: true });
  });

  test("bypass marker allows pi-vcc compaction below threshold", async () => {
    const { handlers, ctx } = setup(59.9);

    const result = await handlers.session_before_compact?.(
      { customInstructions: PI_VCC_MANUAL_BYPASS_MARKER },
      ctx,
    );

    expect(result).toBeUndefined();
  });

  test("marker compaction is canceled when pi-vcc is not loaded", async () => {
    const { handlers, compactCalls, notifications, ctx } = setup(61.2, false);

    await handlers.turn_end?.(
      { message: { role: "assistant", stopReason: "stop" } },
      ctx,
    );

    expect(compactCalls).toHaveLength(0);
    expect(notifications.some((entry) => entry.level === "error" && entry.message.includes("Pi-vcc is not loaded"))).toBe(true);

    const result = await handlers.session_before_compact?.(
      { customInstructions: PI_VCC_MANUAL_BYPASS_MARKER },
      ctx,
    );

    expect(result).toEqual({ cancel: true });
  });
});
