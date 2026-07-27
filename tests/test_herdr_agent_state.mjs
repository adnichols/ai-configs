#!/usr/bin/env node

import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { mkdtemp, rm } from "node:fs/promises";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const tempDir = await mkdtemp(path.join(tmpdir(), "herdr-agent-state-test-"));
const socketPath = path.join(tempDir, "herdr.sock");
const reports = [];

const server = createServer((socket) => {
  let buffer = "";
  socket.on("data", (chunk) => {
    buffer += chunk.toString("utf8");
    const newline = buffer.indexOf("\n");
    if (newline === -1) return;
    reports.push(JSON.parse(buffer.slice(0, newline)));
    socket.end('{"ok":true}\n');
  });
});

await new Promise((resolve, reject) => {
  server.once("error", reject);
  server.listen(socketPath, resolve);
});

process.env.HERDR_ENV = "1";
process.env.HERDR_SOCKET_PATH = socketPath;
process.env.HERDR_PANE_ID = "test-pane";
process.env.HERDR_PI_IDLE_DEBOUNCE_MS = "10";
process.env.HERDR_PI_RETRY_GRACE_MS = "20";
process.env.HERDR_PI_RECONCILE_MS = "10";
process.env.HERDR_PI_HEARTBEAT_MS = "0";
process.env.HERDR_PI_SEND_RETRY_DELAY_MS = "1";
process.env.HERDR_PI_BACKGROUND_PROCESS_IGNORE = "custom-idle";
delete process.env.HERDR_PI_BACKGROUND_PROCESS_MODE;
delete process.env.HERDR_PI_COUNT_BACKGROUND_PROCESSES;

class MockPi {
  constructor() {
    this.events = new EventEmitter();
    this.handlers = new Map();
  }

  on(name, handler) {
    const handlers = this.handlers.get(name) ?? [];
    handlers.push(handler);
    this.handlers.set(name, handlers);
  }

  async emit(name, event = {}, ctx) {
    for (const handler of this.handlers.get(name) ?? []) {
      await handler(event, ctx);
    }
  }
}

let pi = new MockPi();
let parentIdle = false;
const sessionEntries = [];
const ctx = {
  hasUI: true,
  hasPendingMessages: () => false,
  isIdle: () => parentIdle,
  sessionManager: {
    getSessionFile: () => "/tmp/test-session.jsonl",
    getSessionId: () => "test-session",
    getBranch: () => sessionEntries,
  },
  ui: {},
};

const extensionUrl = pathToFileURL(path.resolve("_pi/extensions/herdr-agent-state.ts"));
const { default: installExtension } = await import(extensionUrl.href);
installExtension(pi);

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function stateReports() {
  return reports
    .filter((report) => report.method === "pane.report_agent")
    .map((report) => report.params.state);
}

function lastState() {
  return stateReports().at(-1);
}

async function waitForState(state, timeoutMs = 1000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (lastState() === state) return;
    await delay(5);
  }
  assert.fail(`timed out waiting for ${state}; states=${stateReports().join(",")}`);
}

async function startProcess({ id, name, command }) {
  await pi.emit("tool_result", {
    toolName: "process",
    input: { action: "start", name, command },
    details: {
      process: {
        id,
        name,
        command,
        pid: process.pid,
        status: "running",
      },
    },
  }, ctx);
}

function vccEntry(customType, state, transactionId = "vcc-test") {
  return {
    type: "custom",
    customType,
    data: {
      protocol: "pi-vcc-continuation",
      version: 2,
      kind: customType === "pi-vcc-continuation-outcome" ? "outcome" : "snapshot",
      snapshot: {
        protocol: "pi-vcc-continuation",
        version: 2,
        transactionId,
        state,
      },
    },
  };
}

try {
  await pi.emit("session_start", { reason: "startup" }, ctx);
  await waitForState("idle");

  // Pi reload keeps the same session reference. Releasing Herdr authority on
  // reload suppresses the replacement extension's same-session reports, so a
  // reload shutdown must preserve authority and reload-time session_start must
  // republish the session and idle state.
  const releasesBeforeReload = reports.filter((report) => report.method === "pane.release_agent").length;
  const sessionsBeforeReload = reports.filter((report) => report.method === "pane.report_agent_session").length;
  const statesBeforeReload = stateReports().length;
  await pi.emit("session_shutdown", { reason: "reload" }, ctx);
  await delay(20);
  assert.equal(
    reports.filter((report) => report.method === "pane.release_agent").length,
    releasesBeforeReload,
    "reload must not release same-session Herdr authority",
  );

  // Real Pi reload discards the old extension runner and imports a fresh
  // module instance. Use a cache-busted import and a new MockPi so this test
  // covers the replacement-instance handoff rather than restarting one closure.
  const reloadedExtensionUrl = new URL(extensionUrl.href);
  reloadedExtensionUrl.searchParams.set("reload", String(Date.now()));
  const { default: installReloadedExtension } = await import(reloadedExtensionUrl.href);
  pi = new MockPi();
  installReloadedExtension(pi);
  await pi.emit("session_start", { reason: "reload" }, ctx);
  await delay(30);
  assert.ok(
    reports.filter((report) => report.method === "pane.report_agent_session").length > sessionsBeforeReload,
    "reload-time session_start must republish the session reference",
  );
  assert.ok(stateReports().length > statesBeforeReload, "reload-time session_start must republish state");
  assert.equal(lastState(), "idle", "reload-time session_start must restore idle authority");

  // agent_end is only a low-level boundary. The pane must remain working until
  // the session-level agent_settled event arrives.
  await pi.emit("agent_start", {}, ctx);
  await waitForState("working");
  await pi.emit("agent_end", { messages: [] }, ctx);
  await delay(30);
  assert.equal(lastState(), "working", "agent_end must not publish idle");
  await pi.emit("agent_settled", {}, ctx);
  await waitForState("idle");

  // Pi can report an idle parent context while a foreground tool loop still
  // owns work. The hook must retain agent ownership until agent_settled.
  await pi.emit("agent_start", {}, ctx);
  await waitForState("working");
  parentIdle = true;
  await pi.emit("tool_call", { toolName: "bash" }, ctx);
  await delay(40);
  assert.equal(lastState(), "working", "tool-loop activity must not be cleared by reconciliation");
  parentIdle = false;
  await pi.emit("agent_settled", {}, ctx);
  await waitForState("idle");

  // Default policy is all-except-ignore: an arbitrary live process keeps the
  // pane working after the foreground agent settles.
  await pi.emit("agent_start", {}, ctx);
  await waitForState("working");
  await startProcess({ id: "generic", name: "generic-job", command: "sleep 999" });
  await pi.emit("agent_end", { messages: [] }, ctx);
  await pi.emit("agent_settled", {}, ctx);
  await delay(30);
  assert.equal(lastState(), "working", "generic live process must keep pane working");
  await pi.emit("tool_result", {
    toolName: "process",
    input: { action: "kill", id: "generic" },
  }, ctx);
  await waitForState("idle");

  // Doct's durable comment listener is an explicit passive listener and must
  // not keep the pane marked working.
  await pi.emit("agent_start", {}, ctx);
  await waitForState("working");
  await startProcess({
    id: "doct-listener",
    name: "doct-comments",
    command: "doct-agent plans listen --workspace-id w --document-id d --jsonl",
  });
  await pi.emit("agent_end", { messages: [] }, ctx);
  await pi.emit("agent_settled", {}, ctx);
  await waitForState("idle");

  // Operator-configured literal fragments augment the built-in ignore list.
  await pi.emit("agent_start", {}, ctx);
  await waitForState("working");
  await startProcess({
    id: "custom-listener",
    name: "custom-idle-service",
    command: "custom-service run",
  });
  await pi.emit("agent_end", { messages: [] }, ctx);
  await pi.emit("agent_settled", {}, ctx);
  await waitForState("idle");

  // A retryable provider failure remains working through its grace period and
  // then becomes blocked even though the run has fully settled.
  await pi.emit("agent_start", {}, ctx);
  await waitForState("working");
  await pi.emit("agent_end", {
    messages: [{ role: "assistant", stopReason: "error", errorMessage: "503 service unavailable" }],
  }, ctx);
  await pi.emit("agent_settled", {}, ctx);
  await waitForState("blocked");

  // A new run clears the previous failure and follows the settled boundary.
  await pi.emit("agent_start", {}, ctx);
  await waitForState("working");
  await pi.emit("agent_end", { messages: [] }, ctx);
  await delay(30);
  assert.equal(lastState(), "working", "new run must still wait for agent_settled");
  await pi.emit("agent_settled", {}, ctx);
  await waitForState("idle");

  // Pi-vcc persists its work ownership before it queues the continuation turn.
  // A replacement hook must recover that durable ownership, and release it
  // only when the matching VCC transaction reaches a terminal state.
  sessionEntries.push(vccEntry("pi-vcc-continuation-request", "created"));
  await pi.emit("session_shutdown", { reason: "reload" }, ctx);
  const vccReloadedExtensionUrl = new URL(extensionUrl.href);
  vccReloadedExtensionUrl.searchParams.set("vcc-reload", String(Date.now()));
  const { default: installVccReloadedExtension } = await import(vccReloadedExtensionUrl.href);
  pi = new MockPi();
  installVccReloadedExtension(pi);
  await pi.emit("session_start", { reason: "reload" }, ctx);
  await waitForState("working");
  const terminalVccEntry = vccEntry("pi-vcc-continuation-outcome", "settled");
  sessionEntries.push(terminalVccEntry);
  await pi.emit("entry_appended", { entry: terminalVccEntry }, ctx);
  await waitForState("idle");

  await pi.emit("session_shutdown", { reason: "quit" }, ctx);
  await delay(20);
  assert.ok(reports.some((report) => report.method === "pane.release_agent"));
  console.log(`ok - Herdr agent state lifecycle (${stateReports().join(" -> ")})`);
} finally {
  await new Promise((resolve) => server.close(resolve));
  await rm(tempDir, { recursive: true, force: true });
}
