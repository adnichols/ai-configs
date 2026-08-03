#!/usr/bin/env node

import assert from "node:assert/strict";
import { EventEmitter } from "node:events";
import { mkdir, mkdtemp, rm, writeFile } from "node:fs/promises";
import { createHash } from "node:crypto";
import { createServer } from "node:net";
import { tmpdir } from "node:os";
import path from "node:path";
import { pathToFileURL } from "node:url";

const tempDir = await mkdtemp(path.join(tmpdir(), "herdr-agent-state-test-"));
const socketPath = path.join(tempDir, "herdr.sock");
const reports = [];
let socketAttempts = 0;
let droppedResponses = 0;

const server = createServer((socket) => {
  let buffer = "";
  socket.on("data", (chunk) => {
    buffer += chunk.toString("utf8");
    const newline = buffer.indexOf("\n");
    if (newline === -1) return;
    socketAttempts += 1;
    reports.push(JSON.parse(buffer.slice(0, newline)));
    if (droppedResponses > 0) {
      droppedResponses -= 1;
      socket.end();
      return;
    }
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
process.env.HERDR_PI_MAX_SEND_RETRIES = "3";
process.env.HERDR_PI_BACKGROUND_PROCESS_IGNORE = "custom-idle";
process.env.HERDR_OPERATOR_WAIT_DIR = path.join(tempDir, "operator-wait");
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
let sessionPath = "/tmp/test-session.jsonl";
let sessionId = "test-session";
const sessionEntries = [];
const ctx = {
  mode: "tui",
  hasUI: true,
  hasPendingMessages: () => false,
  isIdle: () => parentIdle,
  sessionManager: {
    getSessionFile: () => sessionPath,
    getSessionId: () => sessionId,
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

function lastStateReport() {
  return reports.filter((report) => report.method === "pane.report_agent").at(-1);
}

function sessionReports() {
  return reports.filter((report) => report.method === "pane.report_agent_session");
}

function releaseReports() {
  return reports.filter((report) => report.method === "pane.release_agent");
}

const operatorMarkerPath = path.join(
  process.env.HERDR_OPERATOR_WAIT_DIR,
  `${createHash("sha256").update(process.env.HERDR_PANE_ID, "utf8").digest("hex")}.json`,
);

function operatorMarker(message, overrides = {}) {
  return {
    paneId: "test-pane",
    message,
    setAt: "2026-08-02T20:00:00Z",
    kind: "generic",
    notifyOnSet: true,
    ...overrides,
  };
}

async function writeOperatorMarker(value) {
  await mkdir(process.env.HERDR_OPERATOR_WAIT_DIR, { recursive: true });
  await writeFile(operatorMarkerPath, typeof value === "string" ? value : `${JSON.stringify(value)}\n`);
}

async function waitForState(state, timeoutMs = 1000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (lastState() === state) return;
    await delay(5);
  }
  assert.fail(`timed out waiting for ${state}; states=${stateReports().join(",")}`);
}

async function waitFor(condition, message, timeoutMs = 1000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (condition()) return;
    await delay(5);
  }
  assert.fail(message);
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
  // A peer can receive a report then close before its JSON-RPC response. That
  // is not delivery confirmation: every RPC, including session handoffs, must
  // retry so a lost session reference cannot strand the pane's ownership.
  droppedResponses = 1;
  await pi.emit("session_start", { reason: "startup" }, ctx);
  await waitForState("idle");
  await waitFor(
    () => sessionReports().length >= 2,
    "early EOF must retry the session handoff report",
  );
  assert.equal(sessionReports().at(-1)?.params.session_start_source, "startup");

  // State reports retain the same protection before the queue's own retries.
  // Pi can change the active session during a continuation, so agent_start
  // must refresh both the session handoff and its following state report.
  sessionPath = "/tmp/refreshed-session.jsonl";
  sessionId = "refreshed-session";
  const sessionsBeforeAgentStart = sessionReports().length;
  const statesBeforeAgentStart = stateReports().length;
  await pi.emit("agent_start", {}, ctx);
  await waitForState("working");
  await waitFor(
    () => sessionReports().length > sessionsBeforeAgentStart,
    "agent start must refresh Herdr's current session reference",
  );
  await waitFor(
    () => stateReports().length > statesBeforeAgentStart,
    "agent start must publish state with the refreshed session reference",
  );
  assert.equal(sessionReports().at(-1)?.params.agent_session_path, sessionPath);
  assert.equal(lastStateReport()?.params.agent_session_path, sessionPath);
  const statesBeforeEarlyEof = stateReports().length;
  droppedResponses = 1;
  pi.events.emit("herdr:blocked", { active: true, label: "Retry state report" });
  await waitFor(
    () => stateReports().length >= statesBeforeEarlyEof + 2,
    "early EOF must retry the state report",
  );
  pi.events.emit("herdr:blocked", { active: false, label: "Retry state report" });
  await waitForState("working");
  await pi.emit("agent_settled", {}, ctx);
  await waitForState("idle");

  // A valid workflow-owned marker latches the authoritative Pi reporter blocked,
  // both while Pi is otherwise idle and while a foreground turn is active.
  await writeOperatorMarker(operatorMarker("Approve implementation", { kind: "approval" }));
  await waitForState("blocked");
  assert.equal(lastStateReport()?.params.message, "Approve implementation");
  await pi.emit("agent_start", {}, ctx);
  await delay(30);
  assert.equal(lastState(), "blocked", "operator wait must outrank foreground working");
  await pi.emit("agent_settled", {}, ctx);
  await rm(operatorMarkerPath);
  await waitForState("idle");

  // Malformed and cross-pane markers fail open instead of blocking or throwing.
  await writeOperatorMarker("{not json");
  await delay(30);
  assert.equal(lastState(), "idle");
  await writeOperatorMarker(operatorMarker("wrong target", { paneId: "different-pane" }));
  await delay(30);
  assert.equal(lastState(), "idle");
  for (const invalid of [
    { paneId: "test-pane", message: "incomplete" },
    operatorMarker("wrong kind", { kind: "other" }),
    operatorMarker("wrong notify", { notifyOnSet: "yes" }),
    operatorMarker("wrong time", { setAt: "yesterday" }),
  ]) {
    await writeOperatorMarker(invalid);
    await delay(30);
    assert.equal(lastState(), "idle", `schema-invalid marker must fail open: ${JSON.stringify(invalid)}`);
  }
  await rm(operatorMarkerPath);

  // Existing nested Pi UI blocked ownership remains higher priority than the marker.
  await writeOperatorMarker(operatorMarker("Workflow wait"));
  await waitForState("blocked");
  pi.events.emit("herdr:blocked", { active: true, label: "Pi UI: confirm" });
  await delay(20);
  assert.equal(lastStateReport()?.params.message, "Pi UI: confirm");
  await rm(operatorMarkerPath);
  await delay(20);
  assert.equal(lastState(), "blocked", "removing marker must not clear nested Pi UI block");
  pi.events.emit("herdr:blocked", { active: false, label: "Pi UI: confirm" });
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
  assert.equal(sessionReports().at(-1)?.params.session_start_source, "reload");

  // Pi also replaces the extension runtime for /new, /resume, and /fork.
  // None of these handoffs may release pane ownership; the new runtime must
  // report its source and continue to publish state. Missing reasons fail safe.
  for (const reason of ["new", "resume", "fork", undefined]) {
    const releasesBeforeReplacement = releaseReports().length;
    await pi.emit("session_shutdown", reason === undefined ? {} : { reason }, ctx);
    await delay(20);
    assert.equal(
      releaseReports().length,
      releasesBeforeReplacement,
      `${reason ?? "missing"} shutdown must retain Herdr authority`,
    );

    const sessionsBeforeReplacementStart = sessionReports().length;
    const replacementExtensionUrl = new URL(extensionUrl.href);
    replacementExtensionUrl.searchParams.set(`replacement-${reason ?? "missing"}`, String(Date.now()));
    const { default: installReplacementExtension } = await import(replacementExtensionUrl.href);
    pi = new MockPi();
    installReplacementExtension(pi);
    await pi.emit("session_start", reason === undefined ? {} : { reason }, ctx);
    await waitFor(
      () => sessionReports().length > sessionsBeforeReplacementStart,
      `${reason ?? "missing"} session start must republish its session reference`,
    );
    const replacementSession = sessionReports().at(-1);
    if (reason === undefined) {
      assert.equal(
        Object.hasOwn(replacementSession?.params ?? {}, "session_start_source"),
        false,
        "a missing Pi lifecycle reason must not be misrepresented as a replacement source",
      );
    } else {
      assert.equal(
        replacementSession?.params.session_start_source,
        reason,
        `${reason} session start must identify its handoff source`,
      );
    }
    await pi.emit("agent_start", {}, ctx);
    await waitForState("working");
    await pi.emit("agent_settled", {}, ctx);
    await waitForState("idle");
  }

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

  // explore_subagent launches Pi as an RPC child and historically copied this
  // terminal's HERDR_* identity. Its extension context hasUI flag is true in
  // RPC mode, but it must not install lifecycle hooks or release the parent.
  const childReportsBefore = reports.length;
  process.env.PI_EXPLORE_SUBAGENT_CHILD = "1";
  const childExtensionUrl = new URL(extensionUrl.href);
  childExtensionUrl.searchParams.set("explore-child", String(Date.now()));
  const { default: installChildExtension } = await import(childExtensionUrl.href);
  const childPi = new MockPi();
  installChildExtension(childPi);
  assert.equal(childPi.handlers.size, 0, "explore RPC child must not register Herdr lifecycle hooks");
  await childPi.emit("session_start", { reason: "startup" }, ctx);
  await childPi.emit("session_shutdown", { reason: "quit" }, ctx);
  await delay(20);
  assert.equal(reports.length, childReportsBefore, "explore RPC child must not report or release the parent pane");
  delete process.env.PI_EXPLORE_SUBAGENT_CHILD;

  // The RPC command-line mode is an independent guard for any future child
  // launcher that does not provide explore_subagent's explicit marker.
  const argvBeforeRpcGuard = [...process.argv];
  process.argv.push("--mode", "rpc");
  const rpcExtensionUrl = new URL(extensionUrl.href);
  rpcExtensionUrl.searchParams.set("rpc-child", String(Date.now()));
  const { default: installRpcExtension } = await import(rpcExtensionUrl.href);
  const rpcPi = new MockPi();
  installRpcExtension(rpcPi);
  assert.equal(rpcPi.handlers.size, 0, "generic RPC child must not register Herdr lifecycle hooks");
  process.argv.splice(0, process.argv.length, ...argvBeforeRpcGuard);

  // Pi's RPC, JSON, and print contexts can inherit HERDR_* identity even when
  // no explicit child marker or --mode argument is present. They must not
  // claim, update, or release the terminal pane.
  const reportsBeforeHeadlessModes = reports.length;
  for (const mode of ["rpc", "json", "print"]) {
    const modeExtensionUrl = new URL(extensionUrl.href);
    modeExtensionUrl.searchParams.set(`mode-${mode}`, String(Date.now()));
    const { default: installModeExtension } = await import(modeExtensionUrl.href);
    const modePi = new MockPi();
    installModeExtension(modePi);
    await modePi.emit("session_start", { reason: "startup" }, { ...ctx, mode, hasUI: true });
    await modePi.emit("agent_start", {}, { ...ctx, mode, hasUI: true });
    await modePi.emit("session_shutdown", { reason: "quit" }, { ...ctx, mode, hasUI: true });
  }
  await delay(20);
  assert.equal(reports.length, reportsBeforeHeadlessModes, "non-TUI modes must not report or release the pane");

  const releasesBeforeQuit = releaseReports().length;
  await pi.emit("session_shutdown", { reason: "quit" }, ctx);
  await pi.emit("session_shutdown", { reason: "quit" }, ctx);
  await delay(20);
  assert.equal(releaseReports().length, releasesBeforeQuit + 1, "quit must release exactly once");
  assert.deepEqual(releaseReports().at(-1)?.params, {
    pane_id: "test-pane",
    source: "herdr:pi",
    agent: "pi",
    seq: releaseReports().at(-1)?.params.seq,
  });
  console.log(`ok - Herdr agent state lifecycle (${stateReports().join(" -> ")})`);
} finally {
  await new Promise((resolve) => server.close(resolve));
  await rm(tempDir, { recursive: true, force: true });
}
