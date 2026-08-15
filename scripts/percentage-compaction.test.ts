import { describe, expect, test } from "bun:test";

import percentageCompaction, {
  COMPACTION_NUDGE_PERCENT,
  COMPACTION_STRONG_NUDGE_PERCENT,
  HARD_AUTO_COMPACTION_PERCENT,
  PI_VCC_LOAD_MARKER,
  PI_VCC_MANUAL_BYPASS_MARKER,
} from "../_pi/extensions/percentage-compaction";
import {
  GROK_ADVERTISED_CONTEXT_WINDOW,
  GROK_COMPACTION_TRIGGER_TOKENS,
} from "../_pi/lib/grok-context-ceiling-policy";

const setup = (
  percent: number | null,
  options: {
    loaded?: boolean;
    idle?: boolean;
    model?: { provider?: string; id?: string; contextWindow?: number };
    tokens?: number;
    requestAccepted?: boolean;
  } = {},
) => {
  const handlers: Record<string, (event: any, ctx: any) => any> = {};
  const commands: Record<string, any> = {};
  const tools: Record<string, any> = {};
  const notifications: Array<{ message: string; level: string }> = [];
  const requests: any[] = [];
  const compactCalls: any[] = [];
  const controller = new AbortController();
  const loaded = options.loaded ?? true;
  (globalThis as any)[PI_VCC_LOAD_MARKER] = loaded ? { status: "active" } : undefined;

  const ctx: any = {
    mode: "tui",
    hasUI: true,
    cwd: process.cwd(),
    model: options.model,
    signal: controller.signal,
    isIdle: () => options.idle ?? false,
    ui: { notify: (message: string, level: string) => notifications.push({ message, level }) },
    getContextUsage: () => percent === null ? null : {
      percent,
      contextWindow: options.model?.contextWindow ?? 272_000,
      tokens: options.tokens ?? Math.round((percent / 100) * (options.model?.contextWindow ?? 272_000)),
    },
    requestCompactionAtTurnBoundary: (request: any) => {
      requests.push(request);
      return options.requestAccepted ?? true;
    },
    compact: (request: any) => compactCalls.push(request ?? {}),
  };

  percentageCompaction({
    on: (event: string, handler: any) => { handlers[event] = handler; },
    registerCommand: (name: string, command: any) => { commands[name] = command; },
    registerTool: (tool: any) => { tools[tool.name] = tool; },
  } as any);

  return { handlers, commands, tools, notifications, requests, compactCalls, controller, ctx };
};

describe("percentage compaction boundary requests", () => {
  test("compact_context requests one semantic boundary compaction without starting work", async () => {
    const runtime = setup(42);
    const result = await runtime.tools.compact_context.execute(
      "tool-1",
      { reason: "after tests", boundary: "after_test_loop", preserve: "keep failure evidence" },
      runtime.controller.signal,
      undefined,
      runtime.ctx,
    );

    expect(result.details).toMatchObject({ accepted: true, boundary: "after_test_loop" });
    expect(runtime.requests).toHaveLength(1);
    expect(runtime.requests[0]).toMatchObject({ reason: "manual" });
    expect(runtime.requests[0].customInstructions).toContain(PI_VCC_MANUAL_BYPASS_MARKER);
    expect(runtime.requests[0].customInstructions).toContain("keep failure evidence");
    expect(runtime.compactCalls).toHaveLength(0);
  });

  test("hard threshold requests boundary compaction once per usage value", async () => {
    const runtime = setup(HARD_AUTO_COMPACTION_PERCENT);
    await runtime.handlers.turn_end({ message: { role: "assistant", stopReason: "toolUse" } }, runtime.ctx);
    await runtime.handlers.turn_end({ message: { role: "assistant", stopReason: "toolUse" } }, runtime.ctx);

    expect(runtime.requests).toEqual([{ reason: "threshold", customInstructions: undefined }]);
    expect(runtime.notifications.at(-1)?.message).toContain("hard backstop");
  });

  test("terminal threshold maintenance never sends a follow-up message", async () => {
    const runtime = setup(HARD_AUTO_COMPACTION_PERCENT);
    await runtime.handlers.turn_end({ message: { role: "assistant", stopReason: "stop" } }, runtime.ctx);

    expect(runtime.requests).toHaveLength(1);
    expect(runtime.compactCalls).toHaveLength(0);
  });

  test("soft and strong bands are informational nudges only", async () => {
    const soft = setup(COMPACTION_NUDGE_PERCENT);
    await soft.handlers.turn_end({ message: { role: "assistant", stopReason: "stop" } }, soft.ctx);
    expect(soft.requests).toHaveLength(0);
    expect(soft.notifications.at(-1)?.message).toContain("soft nudge band");

    const strong = setup(COMPACTION_STRONG_NUDGE_PERCENT);
    await strong.handlers.turn_end({ message: { role: "assistant", stopReason: "stop" } }, strong.ctx);
    expect(strong.requests).toHaveLength(0);
    expect(strong.notifications.at(-1)?.message).toContain("strong nudge band");
  });

  test("active compact-now uses the boundary request and idle compact-now remains terminal", async () => {
    const active = setup(42, { idle: false });
    await active.commands["compact-now"].handler("preserve the current task", active.ctx);
    expect(active.requests).toEqual([{
      reason: "manual",
      customInstructions: "preserve the current task",
    }]);
    expect(active.compactCalls).toHaveLength(0);

    const idle = setup(42, { idle: true });
    await idle.commands["compact-now"].handler("preserve the current task", idle.ctx);
    expect(idle.requests).toHaveLength(0);
    expect(idle.compactCalls).toEqual([{
      customInstructions: `${PI_VCC_MANUAL_BYPASS_MARKER}\npreserve the current task`,
      onComplete: expect.any(Function),
      onError: expect.any(Function),
    }]);
  });

  test("missing pi-vcc cancels host compaction and does not request a boundary", async () => {
    const runtime = setup(90, { loaded: false });
    const result = await runtime.handlers.session_before_compact({ customInstructions: undefined }, runtime.ctx);
    expect(result).toEqual({ cancel: true });
    expect(runtime.requests).toHaveLength(0);
    expect(runtime.notifications.at(-1)?.message).toContain("Pi-vcc is not loaded");
  });

  test("Grok uses its absolute token trigger with the same boundary API", async () => {
    const runtime = setup(90, {
      model: { provider: "opencode", id: "grok-4.5", contextWindow: GROK_ADVERTISED_CONTEXT_WINDOW },
      tokens: GROK_COMPACTION_TRIGGER_TOKENS,
    });
    await runtime.handlers.turn_end({ message: { role: "assistant", stopReason: "toolUse" } }, runtime.ctx);
    expect(runtime.requests).toEqual([{ reason: "threshold", customInstructions: undefined }]);
  });

  test("shutdown prevents later threshold requests", async () => {
    const runtime = setup(HARD_AUTO_COMPACTION_PERCENT);
    await runtime.handlers.session_shutdown({}, runtime.ctx);
    await runtime.handlers.turn_end({ message: { role: "assistant", stopReason: "toolUse" } }, runtime.ctx);
    expect(runtime.requests).toHaveLength(0);
  });
});
