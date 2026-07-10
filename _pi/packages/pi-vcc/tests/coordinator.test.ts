import { describe, expect, it } from "bun:test";
import { createContinuationCoordinator } from "../src/core/coordinator";
import {
  CONTINUATION_MESSAGE_CUSTOM_TYPE,
  CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
  CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
  continuationMessageDetailsFor,
} from "../src/core/continuation-protocol";

const setup = (authority: "coordinator" | "legacy" = "coordinator") => {
  const handlers: Record<string, Array<(event: any, ctx: any) => any>> = {};
  const wakeHandlers = new Set<(data: unknown) => void>();
  const entries: any[] = [];
  const sent: any[] = [];
  const notifications: any[] = [];
  let clock = 100;
  const timers: Array<{ callback: () => void; delay: number; cancelled: boolean }> = [];
  const ctx = {
    sessionManager: { getBranch: () => entries },
    ui: { notify: (message: string, level: string) => notifications.push({ message, level }) },
  } as any;
  const pi = {
    on: (event: string, handler: any) => { (handlers[event] ??= []).push(handler); },
    appendEntry: (customType: string, data: any) => entries.push({
      id: `entry-${entries.length + 1}`,
      type: "custom",
      customType,
      data,
    }),
    sendMessage: (message: any, options: any) => sent.push({ message, options }),
    events: {
      on: (_channel: string, handler: any) => { wakeHandlers.add(handler); return () => wakeHandlers.delete(handler); },
      emit: (_channel: string, data: unknown) => { for (const handler of wakeHandlers) handler(data); },
    },
  } as any;
  const coordinator = createContinuationCoordinator(pi, {
    authority,
    now: () => clock,
    setTimer: (callback, delay) => {
      const timer = { callback, delay, cancelled: false };
      timers.push(timer);
      return timer as any;
    },
    clearTimer: (timer: any) => { timer.cancelled = true; },
    retryDelayMs: 5,
  });
  const emit = (event: string, payload: any = {}) => {
    for (const handler of handlers[event] ?? []) handler({ type: event, ...payload }, ctx);
  };
  const advance = (value: number) => { clock = value; };
  return { coordinator, handlers, wakeHandlers, entries, sent, notifications, timers, ctx, emit, advance, pi };
};

const request = (h: ReturnType<typeof setup>, overrides: Record<string, unknown> = {}) => h.coordinator.request({
  initiator: "compact_context",
  outcome: "compacted",
  attemptId: "attempt-1",
  requestId: "request-1",
  originatingRequestId: "request-1",
  resumePolicy: "active",
  deadlineMs: 100,
  retryLimit: 1,
  transactionId: "tx-1",
  ...overrides,
}, h.ctx);

describe("continuation coordinator", () => {
  it("registers one wake listener and persists request before submission", () => {
    const h = setup();
    request(h);
    expect(h.wakeHandlers.size).toBe(1);
    expect(h.entries[0].customType).toBe(CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE);
    expect(h.sent).toHaveLength(1);
    expect(h.sent[0].options).toEqual({ triggerTurn: true, deliverAs: "steer" });
    expect(h.sent[0].options.deliverAs).not.toBe("nextTurn");
  });

  it("shadow/rollback authority never sends", () => {
    const h = setup("legacy");
    request(h);
    expect(h.entries[0].customType).toBe(CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE);
    expect(h.sent).toHaveLength(0);
  });

  it("requires matching consumption, progress, then settlement", () => {
    const h = setup();
    const snapshot = request(h);
    h.emit("message_start", {
      message: {
        role: "custom",
        customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
        details: continuationMessageDetailsFor(snapshot),
      },
    });
    h.emit("message_end", { message: { role: "assistant", stopReason: "stop" } });
    h.emit("agent_settled");
    expect(h.coordinator.getPending()?.state).toBe("settled");
    expect(h.entries.at(-1).customType).toBe(CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE);
  });

  it.each(["error", "aborted"])("retries terminal assistant %s after consumption", (stopReason) => {
    const h = setup();
    const snapshot = request(h);
    h.emit("message_start", { message: { role: "custom", customType: CONTINUATION_MESSAGE_CUSTOM_TYPE, details: continuationMessageDetailsFor(snapshot) } });
    h.emit("message_end", { message: { role: "assistant", stopReason } });
    h.emit("agent_settled");
    expect(h.sent).toHaveLength(2);
    expect(h.coordinator.getPending()?.retryCount).toBe(1);
  });

  it("settlement without consumption re-arms then exhausts", () => {
    const h = setup();
    request(h);
    h.emit("agent_settled");
    expect(h.sent).toHaveLength(2);
    h.advance(200);
    h.emit("agent_settled");
    expect(h.coordinator.getPending()?.state).toBe("failed_loudly");
    expect(h.notifications.at(-1)?.message).toContain("Manual action");
  });

  it("deadline includes pending tool wait and warns without raw IDs", () => {
    const h = setup();
    request(h, { pendingToolCount: 3 });
    expect(h.sent).toHaveLength(0);
    h.advance(200);
    h.timers.find((timer) => !timer.cancelled)?.callback();
    expect(h.coordinator.getPending()?.state).toBe("failed_loudly");
    expect(h.notifications.at(-1)?.message).toContain("pending-tools=3");
    expect(h.notifications.at(-1)?.message).not.toContain("tool-id-secret");
  });

  it("real user and independent input supersede before matching consumption", () => {
    const realUser = setup();
    request(realUser);
    realUser.emit("input", { source: "interactive", text: "continue" });
    realUser.emit("message_start", { message: { role: "user", content: "continue" } });
    expect(realUser.coordinator.getPending()?.terminalReason).toBe("real_user_input");

    const independent = setup();
    request(independent);
    independent.emit("message_start", { message: { role: "custom", customType: "goal-extension", details: {} } });
    expect(independent.coordinator.getPending()?.terminalReason).toBe("independent_input");
  });

  it("lost/duplicate wakes reconcile branch authority without duplicate submissions", () => {
    const h = setup();
    request(h);
    h.pi.events.emit("pi-vcc:continuation-requested", { untrusted: true });
    h.pi.events.emit("pi-vcc:continuation-requested", { transactionId: "wrong" });
    expect(h.sent).toHaveLength(1);
  });

  it("reload preserves durable pending state and replacement prevents stale send", () => {
    const before = setup();
    request(before);
    before.emit("session_shutdown", { reason: "reload" });
    expect(before.wakeHandlers.size).toBe(0);

    const replacement = setup();
    replacement.entries.push(...structuredClone(before.entries));
    replacement.emit("session_start", { reason: "reload" });
    expect(replacement.coordinator.getPending()?.transactionId).toBe("tx-1");

    const switched = setup();
    request(switched);
    switched.emit("session_shutdown", { reason: "new" });
    const sentBefore = switched.sent.length;
    switched.timers.forEach((timer) => timer.callback());
    expect(switched.sent).toHaveLength(sentBefore);
    expect(switched.coordinator.getPending()?.terminalReason).toBe("session_replaced");
  });
});
