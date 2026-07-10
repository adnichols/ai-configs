import { describe, expect, it } from "bun:test";
import {
  CONTINUATION_MESSAGE_CUSTOM_TYPE,
  CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
  CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
  CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE,
  continuationMessageDetailsFor,
  createContinuationOutcomeWire,
  createContinuationRequestWire,
  createContinuationSnapshotWire,
  reconcileContinuationEntries,
  type ContinuationCustomEntryLike,
  type ContinuationTransactionSnapshot,
} from "../../src/core/continuation-protocol";
import {
  createContinuationTransaction,
  transitionContinuation,
  type ContinuationEvent,
} from "../../src/core/continuation";

type LifecycleHandler = (event: any) => void;

class HostFaithfulHarness {
  entries: ContinuationCustomEntryLike[] = [];
  sent: Array<{ message: any; options: any }> = [];
  snapshot?: ContinuationTransactionSnapshot;
  private handlers = new Map<string, Set<LifecycleHandler>>();
  private wakeHandlers = new Set<() => void>();

  create() {
    const snapshot = createContinuationTransaction({
      transactionId: "tx-runtime",
      origin: "compact_context",
      reason: "compacted",
      compactionId: "compact-runtime",
      attemptId: "attempt-runtime",
      requestId: "request-runtime",
      originatingRequestId: "request-runtime",
      resumePolicy: "active",
      createdAt: 100,
      deadlineMs: 1_000,
      retryLimit: 1,
      epochs: { session: 1 },
    });
    this.appendEntry(CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE, createContinuationRequestWire(snapshot));
    this.snapshot = snapshot;
    return snapshot;
  }

  appendEntry(customType: string, data: unknown) {
    this.entries.push({ id: `entry-${this.entries.length + 1}`, type: "custom", customType, data });
  }

  sendMessage(message: unknown, options: unknown): void {
    this.sent.push({ message, options });
  }

  submit(at: number) {
    if (!this.snapshot) throw new Error("No active transaction");
    const transition = transitionContinuation(this.snapshot, { type: "submitted", at, epochs: { message: 1 } });
    this.snapshot = transition.snapshot;
    this.appendEntry(CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE, createContinuationSnapshotWire(this.snapshot));
    this.sendMessage({
      customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
      content: "Continue after compaction",
      display: false,
      details: continuationMessageDetailsFor(this.snapshot),
    }, { triggerTurn: true, deliverAs: "steer" });
    return transition;
  }

  apply(event: ContinuationEvent) {
    if (!this.snapshot) throw new Error("No active transaction");
    const transition = transitionContinuation(this.snapshot, event);
    this.snapshot = transition.snapshot;
    this.appendEntry(CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE, createContinuationSnapshotWire(this.snapshot));
    if (["settled", "superseded", "failed_loudly"].includes(this.snapshot.state)) {
      this.appendEntry(CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE, createContinuationOutcomeWire(this.snapshot));
    }
    return transition;
  }

  on(event: string, handler: LifecycleHandler) {
    const handlers = this.handlers.get(event) ?? new Set<LifecycleHandler>();
    handlers.add(handler);
    this.handlers.set(event, handlers);
    return () => handlers.delete(handler);
  }

  emit(event: string, payload: any) {
    for (const handler of this.handlers.get(event) ?? []) handler(payload);
  }

  subscribeWake(handler: () => void) {
    this.wakeHandlers.add(handler);
    return () => this.wakeHandlers.delete(handler);
  }

  wake() {
    for (const handler of this.wakeHandlers) handler();
  }

  listenerCount() {
    return this.wakeHandlers.size;
  }

  reconcile() {
    const reconciled = reconcileContinuationEntries(this.entries);
    this.snapshot = reconciled.pending[0];
    return reconciled;
  }
}

const matchingMessage = (snapshot: ContinuationTransactionSnapshot) => ({
  role: "custom",
  customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
  content: "Continue after compaction",
  display: false,
  details: continuationMessageDetailsFor(snapshot),
  timestamp: 130,
});

describe("host-faithful continuation lifecycle gate", () => {
  it("models void send acceptance followed by no message_start", () => {
    const host = new HostFaithfulHarness();
    host.create();
    expect(host.submit(120).snapshot.state).toBe("submitted");
    expect(host.sent).toHaveLength(1);
    expect(host.sent[0].options).toEqual({ triggerTurn: true, deliverAs: "steer" });
    expect(host.snapshot?.state).toBe("submitted");
  });

  it("re-arms queue acceptance without consumption when agent_settled fires", () => {
    const host = new HostFaithfulHarness();
    host.create();
    host.submit(120);
    const transition = host.apply({ type: "agent_settled", at: 200, epochs: { settlement: 1 } });
    expect(transition.decision).toBe("retry");
    expect(host.snapshot?.state).toBe("retrying");
  });

  it("attributes consumption deterministically from customType plus transaction details", () => {
    const host = new HostFaithfulHarness();
    host.create();
    host.submit(120);
    const unrelated = host.apply({
      type: "message_start",
      at: 125,
      message: { ...matchingMessage(host.snapshot!), customType: "other-extension" },
      epochs: { message: 2 },
    });
    expect(unrelated.disposition).toBe("ignored_invalid");
    expect(host.snapshot?.state).toBe("submitted");

    const consumed = host.apply({
      type: "message_start",
      at: 130,
      message: matchingMessage(host.snapshot!),
      epochs: { message: 2 },
    });
    expect(consumed.snapshot.state).toBe("consumed");
  });

  it("requires non-error assistant progress before settlement succeeds", () => {
    const host = new HostFaithfulHarness();
    host.create();
    host.submit(120);
    host.apply({ type: "message_start", at: 130, message: matchingMessage(host.snapshot!), epochs: { message: 2 } });
    host.apply({ type: "assistant_result", at: 150, result: "progress", epochs: { message: 3 } });
    const settled = host.apply({ type: "agent_settled", at: 160, epochs: { settlement: 1 } });
    expect(settled.decision).toBe("settled");
    expect(host.snapshot?.state).toBe("settled");
  });

  it.each(["error", "aborted"] as const)("retries terminal assistant %s after matching consumption", (result: "error" | "aborted") => {
    const host = new HostFaithfulHarness();
    host.create();
    host.submit(120);
    host.apply({ type: "message_start", at: 130, message: matchingMessage(host.snapshot!), epochs: { message: 2 } });
    host.apply({ type: "assistant_result", at: 150, result, epochs: { message: 3 } });
    const settled = host.apply({ type: "agent_settled", at: 160, epochs: { settlement: 1 } });
    expect(settled.decision).toBe("retry");
    expect(host.snapshot?.state).toBe("retrying");
  });

  it("supersedes on real user input and prevents delayed matching events from reviving the transaction", () => {
    const host = new HostFaithfulHarness();
    host.create();
    host.submit(120);
    host.apply({ type: "supersede", at: 125, reason: "real_user_input", epochs: { input: 1 } });
    const delayed = host.apply({ type: "message_start", at: 130, message: matchingMessage(host.snapshot!), epochs: { message: 2 } });
    expect(host.snapshot?.state).toBe("superseded");
    expect(delayed.disposition).toBe("ignored_invalid");
  });

  it("persists and reconciles pending work across reload without trusting a wake payload", () => {
    const beforeReload = new HostFaithfulHarness();
    beforeReload.create();
    beforeReload.submit(120);

    const afterReload = new HostFaithfulHarness();
    afterReload.entries = structuredClone(beforeReload.entries);
    const reconciled = afterReload.reconcile();
    expect(reconciled.pending).toHaveLength(1);
    expect(afterReload.snapshot?.state).toBe("submitted");
    expect(afterReload.snapshot?.transactionId).toBe("tx-runtime");
  });

  it("terminalizes replacement sessions durably", () => {
    const host = new HostFaithfulHarness();
    host.create();
    const replaced = host.apply({ type: "supersede", at: 120, reason: "session_replaced", epochs: { session: 2 } });
    expect(replaced.snapshot.state).toBe("superseded");
    const reconciled = host.reconcile();
    expect(reconciled.pending).toEqual([]);
    expect(reconciled.terminal[0]?.terminalReason).toBe("session_replaced");
  });

  it("ignores stale delayed lifecycle events by epoch", () => {
    const host = new HostFaithfulHarness();
    host.create();
    host.submit(120);
    host.apply({ type: "agent_start", at: 125, epochs: { agent: 2 } });
    const stale = host.apply({ type: "turn_start", at: 130, epochs: { agent: 1, turn: 1 } });
    expect(stale.disposition).toBe("ignored_stale");
    expect(host.snapshot?.state).toBe("submitted");
  });

  it("makes lost and duplicate wakes harmless and cleans up listeners on reload", () => {
    const host = new HostFaithfulHarness();
    host.create();
    let reconciliations = 0;
    const unsubscribe = host.subscribeWake(() => {
      reconciliations += 1;
      host.reconcile();
    });
    expect(host.listenerCount()).toBe(1);

    host.wake();
    host.wake();
    expect(reconciliations).toBe(2);
    expect(host.snapshot?.transactionId).toBe("tx-runtime");

    unsubscribe();
    expect(host.listenerCount()).toBe(0);
    const replacementUnsubscribe = host.subscribeWake(() => host.reconcile());
    expect(host.listenerCount()).toBe(1);
    replacementUnsubscribe();
    expect(host.listenerCount()).toBe(0);
  });
});
