import { appendFileSync, mkdirSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const candidate = resolve(
  process.env.PI_VCC_CANDIDATE_PATH ?? "_pi/packages/pi-vcc",
);
const extensionPath = resolve(
  process.env.PI_VCC_EXTENSION_PATH ??
    "_pi/extensions/percentage-compaction.ts",
);
const root = resolve(process.env.PI_VCC_SOAK_ROOT ?? ".");
const count = Number(process.env.PI_VCC_SOAK_COMPACTIONS ?? "10");
const protocol = await import(
  pathToFileURL(join(candidate, "src/core/continuation-protocol.ts")).href
);
const { createContinuationCoordinator } = await import(
  pathToFileURL(join(candidate, "src/core/coordinator.ts")).href
);
const { registerBeforeCompactHook } = await import(
  pathToFileURL(join(candidate, "src/hooks/before-compact.ts")).href
);
const { default: percentageCompaction, PI_VCC_LOAD_MARKER } = await import(
  pathToFileURL(extensionPath).href
);

mkdirSync(join(root, "sessions"), { recursive: true });
mkdirSync(join(root, "logs"), { recursive: true });
process.env.PI_VCC_LOG_PATH = join(root, "logs", "pi-vcc.jsonl");
process.env.PI_VCC_CONTINUATION_AUTHORITY = "coordinator";
(globalThis as any)[PI_VCC_LOAD_MARKER] = true;

type HandlerMap = Record<string, Array<(event: any, ctx: any) => any>>;
type TimerRecord = { callback: () => void; due: number; cancelled: boolean };

let handlers: HandlerMap = {};
const wakeHandlers = new Map<string, Set<(data: unknown) => void>>();
const entries: any[] = [];
const sessionPath = join(root, "sessions", "soak-session.jsonl");
const sent: any[] = [];
const sendAttempts: any[] = [];
const notifications: any[] = [];
const timers: TimerRecord[] = [];
let now = Date.now();
let syncFailures = 0;

const ctx = {
  isIdle: () => true,
  sessionManager: { getBranch: () => entries },
  ui: {
    notify: (message: string, level: string) =>
      notifications.push({ message, level }),
  },
} as any;

const appendSessionEntry = (customType: string, data: unknown) => {
  const entry = {
    id: `entry-${entries.length + 1}`,
    type: "custom",
    customType,
    data,
  };
  entries.push(entry);
  appendFileSync(sessionPath, `${JSON.stringify(entry)}\n`);
};
const appendBranchMessage = (message: unknown) => {
  const entry = {
    id: `entry-${entries.length + 1}`,
    type: "message",
    message,
  };
  entries.push(entry);
  appendFileSync(sessionPath, `${JSON.stringify(entry)}\n`);
};
const transactionSnapshots = (transactionId: string) => entries.filter(
  (entry) =>
    entry.customType === protocol.CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE &&
    entry.data?.snapshot?.transactionId === transactionId,
);
const transactionLogRecords = (transactionId: string) => {
  try {
    return readFileSync(process.env.PI_VCC_LOG_PATH!, "utf8")
      .trim()
      .split("\n")
      .filter(Boolean)
      .map((line) => JSON.parse(line))
      .filter((record) => record.transactionId === transactionId);
  } catch {
    return [];
  }
};

const pi = {
  on: (event: string, handler: any) => {
    const eventHandlers = handlers[event] ?? [];
    eventHandlers.push(handler);
    handlers[event] = eventHandlers;
  },
  appendEntry: appendSessionEntry,
  sendMessage: (message: unknown, options: unknown) => {
    sendAttempts.push({ message, options });
    if (syncFailures > 0) {
      syncFailures -= 1;
      throw new Error("soak synchronous send failure");
    }
    sent.push({ message, options });
    const entry = {
      id: `entry-${entries.length + 1}`,
      type: "message",
      message,
    };
    entries.push(entry);
    appendFileSync(sessionPath, `${JSON.stringify(entry)}\n`);
  },
  events: {
    on: (channel: string, handler: (data: unknown) => void) => {
      const channelHandlers = wakeHandlers.get(channel) ?? new Set();
      channelHandlers.add(handler);
      wakeHandlers.set(channel, channelHandlers);
      return () => channelHandlers.delete(handler);
    },
    emit: (channel: string, data: unknown) => {
      for (const handler of wakeHandlers.get(channel) ?? []) handler(data);
    },
  },
} as any;

const createCoordinator = () => {
  const next = createContinuationCoordinator(pi, {
    authority: "coordinator",
    now: () => now,
    retryDelayMs: 5,
    setTimer: (callback: () => void, delay: number) => {
      const timer = { callback, due: now + delay, cancelled: false };
      timers.push(timer);
      return timer as any;
    },
    clearTimer: (timer: TimerRecord) => {
      timer.cancelled = true;
    },
  });
  registerBeforeCompactHook(pi, next);
  return next;
};
let coordinator = createCoordinator();

const emit = (event: string, payload: any = {}) => {
  for (const handler of handlers[event] ?? [])
    handler({ type: event, ...payload }, ctx);
};
const advance = (time: number) => {
  now = time;
};
const replaceCoordinator = (reason: "reload" | "new" | "resume" | "fork") => {
  handlers = {};
  coordinator = createCoordinator();
  emit("session_start", { reason });
};
const fireDue = () => {
  const due = timers.filter((timer) => !timer.cancelled && timer.due <= now);
  for (const timer of due) {
    timer.cancelled = true;
    timer.callback();
  }
};
const active = () => coordinator.getPending();
const persistDurableAcceptance = (snapshot: any) => {
  const details = protocol.continuationMessageDetailsFor(snapshot);
  const durableDelivery = {
    id: `entry-${entries.length + 1}`,
    type: "custom_message",
    customType: protocol.CONTINUATION_MESSAGE_CUSTOM_TYPE,
    content: "Continue after compaction",
    details,
  };
  entries.push(durableDelivery);
  appendFileSync(sessionPath, `${JSON.stringify(durableDelivery)}\n`);
  return details;
};
const consumeProgressSettle = () => {
  const snapshot = active();
  if (snapshot?.state !== "submitted")
    throw new Error(`expected submitted transaction, got ${snapshot?.state}`);
  const details = persistDurableAcceptance(snapshot);
  emit("message_start", {
    message: {
      role: "custom",
      customType: protocol.CONTINUATION_MESSAGE_CUSTOM_TYPE,
      details,
    },
  });
  emit("message_end", { message: { role: "assistant", stopReason: "stop" } });
  emit("agent_settled");
};
const request = (index: number, overrides: Record<string, unknown> = {}) =>
  coordinator.request(
    {
      initiator:
        index % 3 === 0
          ? "compact_context"
          : index % 3 === 1
            ? "hard-backstop"
            : "package-pi-vcc",
      outcome:
        index % 4 === 1
          ? "cancellation"
          : index % 4 === 2
            ? "no-safe-cut"
            : index % 4 === 3
              ? "failure"
              : "compacted",
      attemptId: `attempt-${index}`,
      requestId: `request-${index}`,
      originatingRequestId: `request-${index}`,
      resumePolicy: "active",
      transactionId: `soak-tx-${index}`,
      deadlineMs: 100,
      retryLimit: 2,
      ...overrides,
    },
    ctx,
  );

emit("session_start", { reason: "startup" });
if ([...wakeHandlers.values()].some((listeners) => listeners.size !== 1)) {
  throw new Error(
    "coordinator did not install exactly one listener per wake channel",
  );
}

// Load and execute the selected standalone extension. Drive its compact-now publisher path
// and require request-before-wake plus terminal outcome parity without a continuation send.
const standaloneHandlers: Record<string, (event: any, context: any) => any> =
  {};
const standaloneCommands: Record<string, any> = {};
const standaloneEntries: any[] = [];
const standaloneActions: string[] = [];
let standaloneCompact: any;
percentageCompaction({
  on: (event: string, handler: any) => {
    standaloneHandlers[event] = handler;
  },
  registerCommand: (name: string, command: any) => {
    standaloneCommands[name] = command;
  },
  registerTool: () => {},
  appendEntry: (customType: string, data: unknown) => {
    standaloneActions.push(`append:${customType}`);
    standaloneEntries.push({ customType, data });
    appendSessionEntry(customType, data);
  },
  events: {
    on: () => () => {},
    emit: (channel: string, data: unknown) => {
      standaloneActions.push(`emit:${channel}`);
      pi.events.emit(channel, data);
    },
  },
  sendMessage: () => {
    throw new Error("standalone terminal command must not send continuation");
  },
} as any);
const standaloneCtx = {
  compact: (options: unknown) => {
    standaloneCompact = options;
  },
  getContextUsage: () => ({ percent: 20, contextWindow: 272_000 }),
  ui: { notify: () => {} },
};
await standaloneHandlers.session_start?.({}, standaloneCtx);
await standaloneHandlers.agent_start?.({}, standaloneCtx);
await standaloneCommands["compact-now"].handler("", standaloneCtx);
const packageBeforeCompact = handlers.session_before_compact?.at(-1);
const packageSessionCompact = handlers.session_compact?.at(-1);
if (!packageBeforeCompact || !packageSessionCompact)
  throw new Error("package compaction ownership handlers were not registered");
const packageCompaction = await packageBeforeCompact(
  {
    customInstructions: standaloneCompact.customInstructions,
    preparation: {
      previousSummary: undefined,
      tokensBefore: 100,
      fileOps: { read: [], written: [], edited: [] },
    },
    branchEntries: [
      { id: "standalone-u1", type: "message", message: { role: "user", content: "compact" } },
      { id: "standalone-a1", type: "message", message: { role: "assistant", content: "working", stopReason: "stop" } },
      { id: "standalone-u2", type: "message", message: { role: "user", content: "continue" } },
      { id: "standalone-a2", type: "message", message: { role: "assistant", content: "working", stopReason: "stop" } },
    ],
    reason: "manual",
  },
  ctx,
);
now = Date.now() + 1_000;
standaloneCompact.onComplete();
await packageSessionCompact(
  {
    compactionEntry: { id: "standalone-compact", details: packageCompaction.compaction.details },
    reason: "manual",
  },
  ctx,
);
if (standaloneEntries.length !== 0) {
  throw new Error("standalone compact-now callback published instead of session_compact");
}
const standaloneRequest = entries.find(
  (entry) =>
    entry.customType === protocol.CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE &&
    entry.data.snapshot.attemptId === "compact-now-1",
);
if (
  standaloneRequest?.data?.outcomeHint !== "compacted" ||
  standaloneRequest?.data?.snapshot?.resumePolicy !== "terminal"
) {
  throw new Error("session_compact omitted compact-now terminal policy/outcome hint");
}
const standaloneTransactionId = standaloneRequest.data.snapshot.transactionId;
const standaloneOutcome = entries.find(
  (entry) =>
    entry.customType === protocol.CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE &&
    entry.data.transactionId === standaloneTransactionId,
);
if (
  standaloneOutcome?.data.terminalState !== "superseded" ||
  standaloneOutcome?.data.terminalReason !== "explicitly_stopped"
) {
  throw new Error("coordinator did not own standalone terminal outcome");
}

// A completed compact_context boundary is deliberately held until the next
// agent_settled event. Pi's public idle flag can flip before Agent.activeRun
// clears during compaction, so direct submission here would re-enter the agent.
const activeCompactContext = await packageBeforeCompact(
  {
    customInstructions: '__PI_VCC_MANUAL_BYPASS__\n{"source":"compact_context","boundary":"after_test_loop","reason":"soak active continuation","resumePolicy":"active","attemptId":"soak-active-compact-context","requestId":"soak-active-compact-context-request"}',
    preparation: {
      previousSummary: undefined,
      tokensBefore: 100,
      fileOps: { read: [], written: [], edited: [] },
    },
    branchEntries: [
      { id: "active-u1", type: "message", message: { role: "user", content: "complete the phase" } },
      { id: "active-a1", type: "message", message: { role: "assistant", content: "phase complete", stopReason: "stop" } },
      { id: "active-u2", type: "message", message: { role: "user", content: "continue" } },
      { id: "active-a2", type: "message", message: { role: "assistant", content: "ready to compact", stopReason: "stop" } },
    ],
    reason: "manual",
  },
  ctx,
);
await packageSessionCompact(
  {
    compactionEntry: { id: "soak-active-compact-context-entry", details: activeCompactContext.compaction.details },
    reason: "manual",
  },
  ctx,
);
const activeCompactContextRequest = () => entries.find(
  (entry) =>
    entry.customType === protocol.CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE &&
    entry.data.snapshot.attemptId === "soak-active-compact-context",
);
if (activeCompactContextRequest()) {
  throw new Error("active compact_context submitted before post-compaction agent settlement");
}
emit("agent_settled");
if (!activeCompactContextRequest() || active()?.transactionId !== activeCompactContextRequest().data.snapshot.transactionId) {
  throw new Error("active compact_context did not submit after post-compaction agent settlement");
}
consumeProgressSettle();

// Actual coordinator fault matrix.
const sentBeforeFaultMatrix = sent.length;
request(0, { pendingToolCount: 2 });
emit("tool_execution_end", { toolCallId: "unrelated", toolName: "read" });
if (sent.length !== sentBeforeFaultMatrix || active()?.pendingToolCount !== 2)
  throw new Error("unrelated tool completion released continuation");
appendSessionEntry(
  protocol.CONTINUATION_SAFETY_READY_ENTRY_CUSTOM_TYPE,
  protocol.createContinuationSafetyReadyWire({
    transactionId: "soak-tx-0",
    attemptId: "attempt-0",
    requestId: "request-0",
  }),
);
pi.events.emit("pi-vcc:continuation-safety-ready", {
  transactionId: "soak-tx-0",
});
consumeProgressSettle();

request(1);
emit("agent_settled");
if (active()?.state !== "retrying")
  throw new Error("void send no-consumption did not re-arm");
advance(now + 5);
fireDue();
consumeProgressSettle();

syncFailures = 1;
request(2);
if (active()?.state !== "retrying")
  throw new Error("sync throw did not schedule bounded retry");
advance(now + 5);
fireDue();
consumeProgressSettle();

request(3);
let snapshot = active()!;
persistDurableAcceptance(snapshot);
emit("message_start", {
  message: {
    role: "custom",
    customType: protocol.CONTINUATION_MESSAGE_CUSTOM_TYPE,
    details: protocol.continuationMessageDetailsFor(snapshot),
  },
});
emit("message_end", { message: { role: "assistant", stopReason: "error" } });
emit("agent_settled");
advance(now + 5);
fireDue();
consumeProgressSettle();

request(4);
snapshot = active()!;
persistDurableAcceptance(snapshot);
emit("message_start", {
  message: {
    role: "custom",
    customType: protocol.CONTINUATION_MESSAGE_CUSTOM_TYPE,
    details: protocol.continuationMessageDetailsFor(snapshot),
  },
});
emit("message_end", { message: { role: "assistant", stopReason: "aborted" } });
emit("agent_settled");
advance(now + 5);
fireDue();
consumeProgressSettle();

request(5);
pi.events.emit("pi-vcc:continuation-requested", {
  transactionId: "lost-or-duplicate",
});
pi.events.emit("pi-vcc:continuation-requested", { transactionId: "soak-tx-5" });
consumeProgressSettle();

request(6);
request(7);
if (active()?.transactionId !== "soak-tx-6")
  throw new Error("pending order was not durable");
consumeProgressSettle();
if (active()?.transactionId !== "soak-tx-7")
  throw new Error("second pending request did not start automatically");
consumeProgressSettle();

request(8);
emit("session_shutdown", { reason: "reload" });
if ([...wakeHandlers.values()].some((listeners) => listeners.size !== 0))
  throw new Error("reload did not remove listeners");
replaceCoordinator("reload");
if ([...wakeHandlers.values()].some((listeners) => listeners.size !== 1))
  throw new Error("reload replacement did not restore exactly one listener");
consumeProgressSettle();

request(9);
request(10);
emit("session_shutdown", { reason: "new" });
const replacementOutcomes = entries.filter(
  (entry) =>
    entry.customType === protocol.CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE &&
    ["soak-tx-9", "soak-tx-10"].includes(entry.data.transactionId),
);
if (
  replacementOutcomes.length !== 2 ||
  replacementOutcomes.some(
    (entry) => entry.data.terminalReason !== "session_replaced",
  )
) {
  throw new Error(
    "session replacement did not terminalize every pending request",
  );
}
const replacementSessionStart = entries.length;
replaceCoordinator("new");
if ([...wakeHandlers.values()].some((listeners) => listeners.size !== 1))
  throw new Error("new-session replacement did not restore exactly one listener");

const highFrequencyTransactionId = "soak-high-frequency-checkpoint";
const highFrequency = request(10_000, {
  transactionId: highFrequencyTransactionId,
  attemptId: `${highFrequencyTransactionId}-attempt`,
  requestId: `${highFrequencyTransactionId}-request`,
  originatingRequestId: `${highFrequencyTransactionId}-request`,
});
const highFrequencyDetails = persistDurableAcceptance(highFrequency);
emit("message_start", {
  message: {
    role: "custom",
    customType: protocol.CONTINUATION_MESSAGE_CUSTOM_TYPE,
    details: highFrequencyDetails,
  },
});
const highFrequencyToolMessage = {
  role: "assistant",
  stopReason: "toolUse",
  content: [{ type: "toolCall", id: "soak-high-frequency-tool", name: "bash" }],
};
appendBranchMessage(highFrequencyToolMessage);
emit("message_end", { message: highFrequencyToolMessage });
const highFrequencyOrigin = now;
const highFrequencySnapshotsBefore = transactionSnapshots(highFrequencyTransactionId).length;
const highFrequencyLogsBefore = transactionLogRecords(highFrequencyTransactionId).length;
for (let offset = 100; offset < 30_000; offset += 100) {
  advance(highFrequencyOrigin + offset);
  emit("tool_execution_update", { toolCallId: "soak-high-frequency-tool", toolName: "bash" });
}
if (
  transactionSnapshots(highFrequencyTransactionId).length !== highFrequencySnapshotsBefore ||
  transactionLogRecords(highFrequencyTransactionId).length !== highFrequencyLogsBefore
) {
  throw new Error("high-frequency liveness persisted before its checkpoint boundary");
}
advance(highFrequencyOrigin + 30_000);
emit("tool_execution_update", { toolCallId: "soak-high-frequency-tool", toolName: "bash" });
if (
  transactionSnapshots(highFrequencyTransactionId).length !== highFrequencySnapshotsBefore + 1 ||
  transactionLogRecords(highFrequencyTransactionId).length !== highFrequencyLogsBefore + 1
) {
  throw new Error("high-frequency liveness did not persist exactly once at the checkpoint boundary");
}
advance(highFrequencyOrigin + 30_001);
emit("tool_execution_end", { toolCallId: "soak-high-frequency-tool", toolName: "bash" });
emit("agent_settled");
if (
  transactionSnapshots(highFrequencyTransactionId).length !== highFrequencySnapshotsBefore + 3 ||
  transactionLogRecords(highFrequencyTransactionId).length !== highFrequencyLogsBefore + 3
) {
  throw new Error("high-frequency material transitions exceeded the bounded snapshot/log formula");
}

const reloadTransactionId = "soak-active-tool-reload-grace";
let reloadSnapshot = request(10_001, {
  transactionId: reloadTransactionId,
  attemptId: `${reloadTransactionId}-attempt`,
  requestId: `${reloadTransactionId}-request`,
  originatingRequestId: `${reloadTransactionId}-request`,
});
const reloadDetails = persistDurableAcceptance(reloadSnapshot);
emit("message_start", {
  message: {
    role: "custom",
    customType: protocol.CONTINUATION_MESSAGE_CUSTOM_TYPE,
    details: reloadDetails,
  },
});
const reloadToolMessage = {
  role: "assistant",
  stopReason: "toolUse",
  content: [{ type: "toolCall", id: "soak-reload-tool", name: "bash" }],
};
appendBranchMessage(reloadToolMessage);
emit("message_end", { message: reloadToolMessage });
const reloadOrigin = now;
advance(reloadOrigin + 100);
emit("tool_execution_update", { toolCallId: "soak-reload-tool", toolName: "bash" });
const reloadSnapshotsBefore = transactionSnapshots(reloadTransactionId).length;
const reloadLogsBefore = transactionLogRecords(reloadTransactionId).length;
const staleTimers = timers.filter((timer) => !timer.cancelled);
emit("session_shutdown", { reason: "reload" });
advance(reloadOrigin + 200);
replaceCoordinator("reload");
reloadSnapshot = active()!;
if (
  reloadSnapshot.transactionId !== reloadTransactionId ||
  reloadSnapshot.toolStallDeadlineAt !== now + 900_000 ||
  transactionSnapshots(reloadTransactionId).length !== reloadSnapshotsBefore ||
  transactionLogRecords(reloadTransactionId).length !== reloadLogsBefore
) {
  throw new Error("first active-tool reload did not grant an unpersisted fresh stall interval");
}
for (const staleTimer of staleTimers) staleTimer.callback();
if (active()?.toolStallDeadlineAt !== now + 900_000) {
  throw new Error("stale pre-reload timer changed restored active-tool liveness");
}
emit("session_shutdown", { reason: "reload" });
advance(reloadOrigin + 400);
replaceCoordinator("reload");
reloadSnapshot = active()!;
if (
  reloadSnapshot.transactionId !== reloadTransactionId ||
  reloadSnapshot.toolStallDeadlineAt !== now + 900_000 ||
  transactionSnapshots(reloadTransactionId).length !== reloadSnapshotsBefore ||
  transactionLogRecords(reloadTransactionId).length !== reloadLogsBefore
) {
  throw new Error("repeated active-tool reload did not preserve the bounded grace contract");
}
emit("tool_execution_end", { toolCallId: "soak-reload-tool", toolName: "bash" });
emit("agent_settled");
if (
  transactionSnapshots(reloadTransactionId).length !== reloadSnapshotsBefore + 2 ||
  transactionLogRecords(reloadTransactionId).length !== reloadLogsBefore + 2
) {
  throw new Error("active-tool reload completion did not flush only material transitions");
}

for (let index = 11; index < count + 11; index += 1) {
  request(index);
  consumeProgressSettle();
}

const outcomes = entries.slice(replacementSessionStart).filter(
  (entry) =>
    entry.customType === protocol.CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
);
if (outcomes.length < count)
  throw new Error(
    `expected at least ${count} terminal transactions, got ${outcomes.length}`,
  );
if (
  sent.some(
    (entry) =>
      entry.options?.deliverAs !== "steer" ||
      entry.options?.triggerTurn !== true,
  )
) {
  throw new Error("coordinator used a non-steer delivery mode");
}
if (sendAttempts.length <= sent.length) {
  throw new Error("sync throw fault was not exercised");
}

console.log(
  `pi-vcc continuation soak: ${outcomes.length} terminal coordinator transactions using ${candidate}`,
);
console.log(`standalone=${extensionPath}`);
console.log(`log=${process.env.PI_VCC_LOG_PATH}`);
