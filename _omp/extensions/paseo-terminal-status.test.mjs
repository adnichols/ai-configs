import { expect, test } from "bun:test";
import paseoTerminalStatus from "./paseo-terminal-status.ts";

test("Paseo terminal status follows OMP settlement and approval", async () => {
  const states = [];
  const server = Bun.serve({
    hostname: "127.0.0.1",
    port: 0,
    async fetch(request) {
      const body = await request.json();
      states.push(body.state);
      expect(body.terminalId).toBe("test-terminal");
      expect(body.token).toBe("test-token");
      return new Response(null, { status: 204 });
    },
  });
  const keys = ["PASEO_TERMINAL_ID", "PASEO_ACTIVITY_TOKEN", "PASEO_TERMINAL_ACTIVITY_URL", "PASEO_OMP_STATUS_OWNER"];
  const prior = keys.map((key) => process.env[key]);
  process.env.PASEO_TERMINAL_ID = "test-terminal";
  process.env.PASEO_ACTIVITY_TOKEN = "test-token";
  process.env.PASEO_TERMINAL_ACTIVITY_URL = `http://127.0.0.1:${server.port}/api/terminal-activity`;
  delete process.env.PASEO_OMP_STATUS_OWNER;

  try {
    const handlers = new Map();
    paseoTerminalStatus({ on: (name, handler) => handlers.set(name, handler) });
    let idle = false;
    const emit = (name, event = {}) => {
      const handler = handlers.get(name);
      if (!handler) throw new Error(`Missing OMP handler: ${name}`);
      handler(event, { isIdle: () => idle });
    };
    const expectState = async (state) => {
      for (let attempt = 0; attempt < 100; attempt++) {
        if (states.at(-1) === state) return;
        await Bun.sleep(10);
      }
      throw new Error(`Expected ${state}; received ${states.join(", ")}`);
    };

    emit("agent_start");
    await expectState("running");
    emit("agent_end", { willContinue: true });
    await Bun.sleep(20);
    expect(states.at(-1)).toBe("running");
    emit("agent_end", { willContinue: false });
    idle = true;
    await expectState("idle");

    idle = false;
    emit("agent_start");
    await expectState("running");
    emit("tool_approval_requested");
    await expectState("needs-input");
    emit("tool_approval_resolved");
    await expectState("running");
    emit("agent_settled");
    await expectState("idle");

    emit("agent_start");
    await expectState("running");
    emit("tool_execution_start", { toolName: "ask" });
    await expectState("needs-input");
    emit("tool_approval_requested");
    await expectState("needs-input");
    emit("tool_approval_resolved");
    await Bun.sleep(20);
    expect(states.at(-1)).toBe("needs-input");
    emit("tool_execution_end", { toolName: "ask" });
    await expectState("running");
    emit("agent_settled");
    await expectState("idle");
  } finally {
    keys.forEach((key, index) => {
      if (prior[index] === undefined) delete process.env[key];
      else process.env[key] = prior[index];
    });
    server.stop(true);
  }
});
