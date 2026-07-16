import { afterAll, beforeAll, describe, expect, it, mock } from "bun:test";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

mock.module("@earendil-works/pi-coding-agent", () => ({
  convertToLlm: (messages: any[]) => messages,
  estimateTokens: (message: any) => {
    const content = message?.content;
    if (typeof content === "string") return Math.ceil(content.length / 4);
    if (!Array.isArray(content)) return 0;
    return Math.ceil(content.reduce((sum: number, part: any) => sum + String(part?.text ?? "").length, 0) / 4);
  },
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

let previousLogPath: string | undefined;
let logDir = "";

beforeAll(async () => {
  previousLogPath = process.env.PI_VCC_LOG_PATH;
  logDir = await mkdtemp(join(tmpdir(), "pi-vcc-command-test-"));
  process.env.PI_VCC_LOG_PATH = join(logDir, "pi-vcc.jsonl");
});

afterAll(async () => {
  if (previousLogPath === undefined) delete process.env.PI_VCC_LOG_PATH;
  else process.env.PI_VCC_LOG_PATH = previousLogPath;
  await rm(logDir, { recursive: true, force: true });
});

const setup = async () => {
  let command: any;
  let compactOptions: any;
  const handlers: Record<string, Array<(event: any, ctx?: any) => any>> = {};
  const requests: any[] = [];
  const notifications: any[] = [];
  const sentUserMessages: any[] = [];
  const pi = {
    registerCommand: (_name: string, value: any) => {
      command = value;
    },
    on: (eventName: string, callback: (event: any, ctx?: any) => any) => {
      handlers[eventName] ??= [];
      handlers[eventName].push(callback);
    },
    sendUserMessage: (content: string, options: any) =>
      sentUserMessages.push({ content, options }),
  } as any;
  const coordinator = {
    request: (input: any) => {
      requests.push(input);
      return input;
    },
  } as any;
  const ctx = {
    compact: (value: any) => {
      compactOptions = value;
    },
    ui: {
      notify: (message: string, level: string) =>
        notifications.push({ message, level }),
    },
  } as any;
  const { registerPiVccCommand } = await import("../src/commands/pi-vcc");
  const { registerBeforeCompactHook } = await import("../src/hooks/before-compact");
  registerPiVccCommand(pi, coordinator);
  registerBeforeCompactHook(pi, coordinator);

  const completeThroughSessionCompact = async () => {
    const before = handlers.session_before_compact?.[0];
    const compacted = handlers.session_compact?.[0];
    if (!before || !compacted) throw new Error("compaction handlers were not registered");
    const result = await before({
      customInstructions: compactOptions.customInstructions,
      preparation: {
        previousSummary: undefined,
        tokensBefore: 100,
        fileOps: { read: [], written: [], edited: [] },
      },
      branchEntries: [
        { id: "u1", type: "message", message: { role: "user", content: "Do the work" } },
        { id: "a1", type: "message", message: { role: "assistant", content: [{ type: "text", text: "Working" }], stopReason: "stop" } },
        { id: "u2", type: "message", message: { role: "user", content: "Continue" } },
        { id: "a2", type: "message", message: { role: "assistant", content: [{ type: "text", text: "Still working" }], stopReason: "stop" } },
      ],
      reason: "manual",
    }, ctx);
    compactOptions.onComplete();
    await compacted({
      compactionEntry: { id: "compact-1", details: result.compaction.details },
      reason: "manual",
    }, ctx);
  };

  return {
    invoke: async (args = "") => command.handler(args, ctx),
    completeThroughSessionCompact,
    getCompactOptions: () => compactOptions,
    requests,
    notifications,
    sentUserMessages,
  };
};

describe("package /pi-vcc command protocol parity", () => {
  it("publishes active success through session_compact exactly once", async () => {
    const h = await setup();
    await h.invoke("");
    await h.completeThroughSessionCompact();
    expect(h.requests).toHaveLength(1);
    expect(h.requests[0]).toMatchObject({
      initiator: "package-pi-vcc",
      outcome: "compacted",
      resumePolicy: "active",
    });
  });

  it.each([
    [new Error("Compaction cancelled"), "cancellation"],
    [new Error("Already compacted"), "no-safe-cut"],
    [new Error("Nothing to compact (session too small)"), "no-safe-cut"],
    [new Error("provider failed"), "failure"],
  ])("publishes %s through the coordinator", async (error, outcome) => {
    const h = await setup();
    await h.invoke("");
    h.getCompactOptions().onError(error);
    expect(h.requests).toHaveLength(1);
    expect(h.requests[0]).toMatchObject({
      initiator: "package-pi-vcc",
      outcome,
      resumePolicy: "active",
    });
  });

  it("uses terminal policy with a direct follow-up and one session_compact publication", async () => {
    const h = await setup();
    await h.invoke("-- continue with the requested follow-up");
    await h.completeThroughSessionCompact();
    expect(h.requests).toHaveLength(1);
    expect(h.requests[0]).toMatchObject({
      initiator: "package-pi-vcc",
      outcome: "compacted",
      resumePolicy: "terminal",
    });
    expect(h.sentUserMessages).toHaveLength(1);
    expect(h.sentUserMessages[0].options).toEqual({ deliverAs: "steer" });
  });
});
