import { mkdirSync } from "node:fs";
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

const handlers: HandlerMap = {};
const wakeHandlers = new Map<string, Set<(data: unknown) => void>>();
const entries: any[] = [];
const sent: any[] = [];
const sendAttempts: any[] = [];
const notifications: any[] = [];
const timers: TimerRecord[] = [];
let now = 1_000;
let syncFailures = 0;

const ctx = {
  sessionManager: { getBranch: () => entries },
  ui: {
    notify: (message: string, level: string) =>
      notifications.push({ message, level }),
  },
} as any;

const pi = {
  on: (event: string, handler: any) => {
    const eventHandlers = handlers[event] ?? [];
    eventHandlers.push(handler);
    handlers[event] = eventHandlers;
  },
  appendEntry: (customType: string, data: unknown) =>
    entries.push({
      id: `entry-${entries.length + 1}`,
      type: "custom",
      customType,
      data,
    }),
  sendMessage: (message: unknown, options: unknown) => {
    sendAttempts.push({ message, options });
    if (syncFailures > 0) {
      syncFailures -= 1;
      throw new Error("soak synchronous send failure");
    }
    sent.push({ message, options });
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

const coordinator = createContinuationCoordinator(pi, {
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

const emit = (event: string, payload: any = {}) => {
  for (const handler of handlers[event] ?? [])
    handler({ type: event, ...payload }, ctx);
};
const advance = (time: number) => {
  now = time;
};
const fireDue = () => {
  const due = timers.filter((timer) => !timer.cancelled && timer.due <= now);
  for (const timer of due) {
    timer.cancelled = true;
    timer.callback();
  }
};
const active = () => coordinator.getPending();
const consumeProgressSettle = () => {
  const snapshot = active();
  if (snapshot?.state !== "submitted")
    throw new Error(`expected submitted transaction, got ${snapshot?.state}`);
  emit("message_start", {
    message: {
      role: "custom",
      customType: protocol.CONTINUATION_MESSAGE_CUSTOM_TYPE,
      details: protocol.continuationMessageDetailsFor(snapshot),
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
  },
  events: {
    on: () => () => {},
    emit: (channel: string) => standaloneActions.push(`emit:${channel}`),
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
standaloneCompact.onComplete();
if (
  standaloneEntries.map((entry) => entry.customType).join(",") !==
  `${protocol.CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE},${protocol.CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE}`
) {
  throw new Error(
    "standalone compact-now did not publish request/outcome parity",
  );
}
if (
  standaloneActions[0] !==
    `append:${protocol.CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE}` ||
  standaloneActions[1] !== "emit:pi-vcc:continuation-requested"
) {
  throw new Error("standalone request-before-wake ordering failed");
}

// Actual coordinator fault matrix.
request(0, { pendingToolCount: 2 });
emit("tool_execution_end", { toolCallId: "unrelated", toolName: "read" });
if (sent.length !== 0 || active()?.pendingToolCount !== 2)
  throw new Error("unrelated tool completion released continuation");
entries.push({
  id: `entry-${entries.length + 1}`,
  type: "custom",
  customType: protocol.CONTINUATION_SAFETY_READY_ENTRY_CUSTOM_TYPE,
  data: protocol.createContinuationSafetyReadyWire({
    transactionId: "soak-tx-0",
    attemptId: "attempt-0",
    requestId: "request-0",
  }),
});
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
emit("session_start", { reason: "reload" });
if ([...wakeHandlers.values()].some((listeners) => listeners.size !== 1))
  throw new Error("reload did not restore exactly one listener");
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
entries.length = 0;
emit("session_start", { reason: "new" });

for (let index = 11; index < count + 11; index += 1) {
  request(index);
  consumeProgressSettle();
}

const outcomes = entries.filter(
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
