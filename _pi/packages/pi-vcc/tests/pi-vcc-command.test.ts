import { afterAll, beforeAll, describe, expect, it, mock } from "bun:test";
import { mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";

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
  const requests: any[] = [];
  const notifications: any[] = [];
  const sentUserMessages: any[] = [];
  const pi = {
    registerCommand: (_name: string, value: any) => {
      command = value;
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
  registerPiVccCommand(pi, coordinator);
  return {
    invoke: async (args = "") => command.handler(args, ctx),
    getCompactOptions: () => compactOptions,
    requests,
    notifications,
    sentUserMessages,
  };
};

describe("package /pi-vcc command protocol parity", () => {
  it("publishes active success through the coordinator", async () => {
    const h = await setup();
    await h.invoke("");
    h.getCompactOptions().onComplete();
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

  it("uses terminal policy with a direct follow-up and does not create a continuation turn", async () => {
    const h = await setup();
    await h.invoke("-- continue with the requested follow-up");
    h.getCompactOptions().onComplete();
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
