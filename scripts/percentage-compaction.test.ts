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
  } = {},
) => {
  const handlers: Record<string, (event: any, ctx: any) => any> = {};
  const commands: Record<string, any> = {};
  const tools: Record<string, any> = {};
  const notifications: Array<{ message: string; level: string }> = [];
  const compactCalls: any[] = [];
  const providerRequests: any[] = [];
  const customMessages: any[] = [];
  const controller = new AbortController();
  let idle = options.idle ?? false;
  const loaded = options.loaded ?? true;
  (globalThis as any)[PI_VCC_LOAD_MARKER] = loaded ? { status: "active" } : undefined;

  const ctx: any = {
    mode: "tui",
    hasUI: true,
    cwd: process.cwd(),
    model: options.model,
    signal: controller.signal,
    isIdle: () => idle,
    ui: { notify: (message: string, level: string) => notifications.push({ message, level }) },
    getContextUsage: () => percent === null ? null : {
      percent,
      contextWindow: options.model?.contextWindow ?? 272_000,
      tokens: options.tokens ?? Math.round((percent / 100) * (options.model?.contextWindow ?? 272_000)),
    },
    compact: (request: any) => compactCalls.push(request ?? {}),
  };

  percentageCompaction({
    on: (event: string, handler: any) => { handlers[event] = handler; },
    registerCommand: (name: string, command: any) => { commands[name] = command; },
    registerTool: (tool: any) => { tools[tool.name] = tool; },
    sendMessage: (message: any, request: any) => customMessages.push({ message, request }),
  } as any);

  return {
    handlers,
    commands,
    tools,
    notifications,
    compactCalls,
    providerRequests,
    customMessages,
    controller,
    ctx,
    setIdle(value: boolean) { idle = value; },
  };
};

const requestSemanticCompaction = async (runtime: ReturnType<typeof setup>, preserve = "keep failure evidence") =>
  runtime.tools.compact_context.execute(
    "tool-1",
    { reason: "after tests", boundary: "after_test_loop", preserve },
    runtime.controller.signal,
    undefined,
    runtime.ctx,
  );

describe("percentage compaction settled-run maintenance", () => {
  test("compact_context records intent without aborting or compacting the active run", async () => {
    const runtime = setup(42);
    const result = await requestSemanticCompaction(runtime);

    expect(result.details).toMatchObject({ accepted: true, boundary: "after_test_loop" });
    expect(result.content[0].text).toContain("after the current run settles");
    expect(runtime.controller.signal.aborted).toBe(false);
    expect(runtime.compactCalls).toHaveLength(0);
    expect(runtime.customMessages).toHaveLength(0);
  });

  test("compacts once after a normal run settles and remains terminal", async () => {
    const runtime = setup(42);
    await requestSemanticCompaction(runtime);

    await runtime.handlers.turn_end({ message: { role: "assistant", stopReason: "stop" } }, runtime.ctx);
    expect(runtime.compactCalls).toHaveLength(0);

    runtime.setIdle(true);
    await runtime.handlers.agent_settled({}, runtime.ctx);

    expect(runtime.compactCalls).toHaveLength(1);
    expect(runtime.compactCalls[0].customInstructions).toContain(PI_VCC_MANUAL_BYPASS_MARKER);
    expect(runtime.compactCalls[0].customInstructions).toContain("keep failure evidence");
    expect(runtime.customMessages).toHaveLength(0);
    expect(runtime.providerRequests).toHaveLength(0);

    await runtime.handlers.agent_settled({}, runtime.ctx);
    expect(runtime.compactCalls).toHaveLength(1);
  });

  test("coalesces repeated semantic requests instead of creating a queue", async () => {
    const runtime = setup(42);
    await requestSemanticCompaction(runtime, "preserve first");
    await requestSemanticCompaction(runtime, "preserve latest");
    runtime.setIdle(true);

    await runtime.handlers.agent_settled({}, runtime.ctx);

    expect(runtime.compactCalls).toHaveLength(1);
    expect(runtime.compactCalls[0].customInstructions).toContain("preserve latest");
    expect(runtime.compactCalls[0].customInstructions).not.toContain("preserve first");
  });

  test("an aborted assistant turn clears pending maintenance", async () => {
    const runtime = setup(42);
    await requestSemanticCompaction(runtime);
    await runtime.handlers.turn_end({ message: { role: "assistant", stopReason: "aborted" } }, runtime.ctx);
    runtime.setIdle(true);

    await runtime.handlers.agent_settled({}, runtime.ctx);

    expect(runtime.compactCalls).toHaveLength(0);
    expect(runtime.customMessages).toHaveLength(0);
  });

  test("successful native compaction satisfies pending semantic maintenance", async () => {
    const runtime = setup(HARD_AUTO_COMPACTION_PERCENT);
    await requestSemanticCompaction(runtime);
    await runtime.handlers.session_compact({ compactionEntry: { details: {} } }, runtime.ctx);
    runtime.setIdle(true);

    await runtime.handlers.agent_settled({}, runtime.ctx);

    expect(runtime.compactCalls).toHaveLength(0);
  });

  test("aborting native compaction clears pending maintenance", async () => {
    const runtime = setup(42);
    await requestSemanticCompaction(runtime);
    const compactionController = new AbortController();
    await runtime.handlers.session_before_compact({
      customInstructions: undefined,
      signal: compactionController.signal,
    }, runtime.ctx);
    compactionController.abort();
    runtime.setIdle(true);

    await runtime.handlers.agent_settled({}, runtime.ctx);

    expect(runtime.compactCalls).toHaveLength(0);
  });

  test("hard threshold is informational and leaves recovery to native Pi", async () => {
    const runtime = setup(HARD_AUTO_COMPACTION_PERCENT);
    await runtime.handlers.turn_end({ message: { role: "assistant", stopReason: "toolUse" } }, runtime.ctx);
    await runtime.handlers.turn_end({ message: { role: "assistant", stopReason: "toolUse" } }, runtime.ctx);

    expect(runtime.compactCalls).toHaveLength(0);
    expect(runtime.notifications.at(-1)).toEqual({ message: `Context is at ${HARD_AUTO_COMPACTION_PERCENT}%.`, level: "warning" });
  });

  test("soft and strong bands are informational nudges only", async () => {
    const soft = setup(COMPACTION_NUDGE_PERCENT);
    await soft.handlers.turn_end({ message: { role: "assistant", stopReason: "stop" } }, soft.ctx);
    expect(soft.compactCalls).toHaveLength(0);
    expect(soft.notifications.at(-1)?.message).toContain("soft nudge band");

    const strong = setup(COMPACTION_STRONG_NUDGE_PERCENT);
    await strong.handlers.turn_end({ message: { role: "assistant", stopReason: "stop" } }, strong.ctx);
    expect(strong.compactCalls).toHaveLength(0);
    expect(strong.notifications.at(-1)?.message).toContain("strong nudge band");
  });

  test("active compact-now records intent while idle compact-now compacts immediately", async () => {
    const active = setup(42, { idle: false });
    await active.commands["compact-now"].handler("preserve the current task", active.ctx);
    expect(active.compactCalls).toHaveLength(0);
    active.setIdle(true);
    await active.handlers.agent_settled({}, active.ctx);
    expect(active.compactCalls).toHaveLength(1);
    expect(active.compactCalls[0].customInstructions).toContain("preserve the current task");

    const idle = setup(42, { idle: true });
    await idle.commands["compact-now"].handler("preserve the current task", idle.ctx);
    expect(idle.compactCalls).toEqual([{
      customInstructions: `${PI_VCC_MANUAL_BYPASS_MARKER}\npreserve the current task`,
      onComplete: expect.any(Function),
      onError: expect.any(Function),
    }]);
  });

  test("missing pi-vcc cancels host compaction and refuses semantic intent", async () => {
    const runtime = setup(90, { loaded: false });
    const toolResult = await requestSemanticCompaction(runtime);
    const result = await runtime.handlers.session_before_compact({
      customInstructions: undefined,
      signal: new AbortController().signal,
    }, runtime.ctx);

    expect(toolResult.details.accepted).toBe(false);
    expect(result).toEqual({ cancel: true });
    expect(runtime.compactCalls).toHaveLength(0);
    expect(runtime.notifications.at(-1)?.message).toContain("Pi-vcc is not loaded");
  });

  test("Grok threshold is informational and uses native Pi recovery", async () => {
    const runtime = setup(90, {
      model: { provider: "opencode", id: "grok-4.5", contextWindow: GROK_ADVERTISED_CONTEXT_WINDOW },
      tokens: GROK_COMPACTION_TRIGGER_TOKENS,
    });
    await runtime.handlers.turn_end({ message: { role: "assistant", stopReason: "toolUse" } }, runtime.ctx);

    expect(runtime.compactCalls).toHaveLength(0);
    expect(runtime.notifications.at(-1)?.message).toContain("Native Pi");
  });

  test("shutdown and session replacement discard pending maintenance", async () => {
    const shutdown = setup(42);
    await requestSemanticCompaction(shutdown);
    await shutdown.handlers.session_shutdown({}, shutdown.ctx);
    shutdown.setIdle(true);
    await shutdown.handlers.agent_settled({}, shutdown.ctx);
    expect(shutdown.compactCalls).toHaveLength(0);

    const switched = setup(42);
    await requestSemanticCompaction(switched);
    await switched.handlers.session_before_switch({}, switched.ctx);
    switched.setIdle(true);
    await switched.handlers.agent_settled({}, switched.ctx);
    expect(switched.compactCalls).toHaveLength(0);
  });

  test("production surfaces use released Pi APIs and contain no continuation sender", async () => {
    const productionFiles = [
      "_pi/extensions/percentage-compaction.ts",
      "_pi/packages/pi-vcc/src/commands/pi-vcc.ts",
      "_pi/packages/pi-vcc/index.ts",
      "scripts/pi-vcc-real-host-integration.ts",
    ];
    const forbidden = [
      "requestCompactionAtTurnBoundary",
      "sendUserMessage(",
      "triggerTurn:",
      "deliverAs: \"followUp\"",
      "ContinuationCoordinator",
      "continuationFacade",
    ];

    for (const path of productionFiles) {
      const source = await Bun.file(path).text();
      for (const token of forbidden) expect(source, `${path} contains ${token}`).not.toContain(token);
    }
  });
});
