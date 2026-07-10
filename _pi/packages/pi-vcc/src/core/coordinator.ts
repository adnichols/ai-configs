import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import {
  CONTINUATION_MESSAGE_CUSTOM_TYPE,
  CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
  CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
  CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE,
  adaptContinuationInitiatorOutcome,
  continuationMessageDetailsFor,
  createContinuationOutcomeWire,
  createContinuationRequestWire,
  createContinuationSnapshotWire,
  reconcileContinuationEntries,
  type ContinuationAttemptOutcome,
  type ContinuationInitiator,
  type ContinuationLifecycleEpochs,
  type ContinuationResumePolicy,
  type ContinuationState,
  type ContinuationTransactionSnapshot,
} from "./continuation-protocol";
import {
  createContinuationTransaction,
  isContinuationTerminal,
  transitionContinuation,
  type ContinuationEvent,
} from "./continuation";
import { getPiVccLogPath, logContinuationTransaction, logPiVccEvent } from "./log";

export const CONTINUATION_WAKE_EVENT = "pi-vcc:continuation-requested";
export const CONTINUATION_AUTHORITY_ENV = "PI_VCC_CONTINUATION_AUTHORITY";
const CONTINUATION_PROMPT =
  "Pi-vcc interrupted active work for compaction or recovery. Continue from the preserved state and resume the next concrete step; use vcc_recall if details from before compaction are needed.";
const DEFAULT_DEADLINE_MS = 60_000;
const DEFAULT_RETRY_LIMIT = 2;
const DEFAULT_RETRY_DELAY_MS = 100;

export type ContinuationAuthority = "coordinator" | "legacy";

export interface ContinuationRequestInput {
  initiator: ContinuationInitiator;
  outcome: ContinuationAttemptOutcome;
  attemptId: string;
  compactionId?: string;
  requestId?: string;
  originatingRequestId?: string;
  resumePolicy?: ContinuationResumePolicy;
  pendingToolCount?: number;
  deadlineMs?: number;
  retryLimit?: number;
  transactionId?: string;
}

export interface ContinuationCoordinatorOptions {
  authority?: ContinuationAuthority;
  now?: () => number;
  setTimer?: (callback: () => void, delayMs: number) => ReturnType<typeof setTimeout>;
  clearTimer?: (timer: ReturnType<typeof setTimeout>) => void;
  retryDelayMs?: number;
}

export interface ContinuationCoordinator {
  authority: ContinuationAuthority;
  request(input: ContinuationRequestInput, ctx: ExtensionContext): ContinuationTransactionSnapshot;
  reconcile(ctx: ExtensionContext): void;
  getPending(): ContinuationTransactionSnapshot | undefined;
  dispose(): void;
}

const transactionIdFor = (input: ContinuationRequestInput, now: number): string =>
  input.transactionId ?? `vcc-${now.toString(36)}-${input.attemptId}`;

const logEventForState = (state: ContinuationState) => {
  if (state === "failed_loudly") return "failed" as const;
  return state;
};

const readAuthority = (): ContinuationAuthority =>
  process.env[CONTINUATION_AUTHORITY_ENV]?.trim().toLowerCase() === "legacy" ? "legacy" : "coordinator";

const isRealUserMessage = (message: any): boolean =>
  message?.role === "user" && typeof message?.customType !== "string";

const isIndependentConsumedInput = (message: any): boolean =>
  (message?.role === "custom" && message.customType !== CONTINUATION_MESSAGE_CUSTOM_TYPE)
  || message?.role === "user";

const classifyAssistantResult = (message: any): "progress" | "error" | "aborted" | undefined => {
  if (message?.role !== "assistant") return undefined;
  if (message.stopReason === "error") return "error";
  if (message.stopReason === "aborted") return "aborted";
  return "progress";
};

export const createContinuationCoordinator = (
  pi: ExtensionAPI,
  options: ContinuationCoordinatorOptions = {},
): ContinuationCoordinator => {
  const authority = options.authority ?? readAuthority();
  const now = options.now ?? Date.now;
  const setTimer = options.setTimer ?? setTimeout;
  const clearTimer = options.clearTimer ?? clearTimeout;
  const retryDelayMs = options.retryDelayMs ?? DEFAULT_RETRY_DELAY_MS;
  let current: ContinuationTransactionSnapshot | undefined;
  let watchdog: ReturnType<typeof setTimeout> | undefined;
  let lastContext: ExtensionContext | undefined;
  let disposed = false;
  let shuttingDownForReload = false;
  let epochs: ContinuationLifecycleEpochs = {
    session: 0,
    input: 0,
    agent: 0,
    turn: 0,
    message: 0,
    settlement: 0,
  };

  const cancelTimer = () => {
    if (watchdog !== undefined) clearTimer(watchdog);
    watchdog = undefined;
  };

  const persistSnapshot = (snapshot: ContinuationTransactionSnapshot) => {
    pi.appendEntry(CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE, createContinuationSnapshotWire(snapshot));
    logContinuationTransaction(logEventForState(snapshot.state), snapshot, now());
  };

  const persistOutcome = (snapshot: ContinuationTransactionSnapshot) => {
    pi.appendEntry(CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE, createContinuationOutcomeWire(snapshot));
  };

  const warnFailure = (snapshot: ContinuationTransactionSnapshot, ctx: ExtensionContext) => {
    const identifiers = [
      `transaction=${snapshot.transactionId}`,
      `attempt=${snapshot.attemptId}`,
      snapshot.compactionId ? `compaction=${snapshot.compactionId}` : undefined,
    ].filter(Boolean).join(" ");
    ctx.ui.notify(
      `Pi-vcc continuation failed (${identifiers}; retries=${snapshot.retryCount}; pending-tools=${snapshot.pendingToolCount}). ` +
      `See ${getPiVccLogPath()}. Manual action: send “continue” after checking the interrupted task state.`,
      "warning",
    );
  };

  const armTimer = (snapshot: ContinuationTransactionSnapshot, delayOverride?: number) => {
    cancelTimer();
    if (disposed || isContinuationTerminal(snapshot)) return;
    const delay = delayOverride ?? Math.max(0, snapshot.deadlineAt - now());
    watchdog = setTimer(() => {
      watchdog = undefined;
      if (!current || current.transactionId !== snapshot.transactionId || isContinuationTerminal(current)) return;
      apply({ type: "deadline", at: Math.max(now(), current.deadlineAt), epochs }, lastContext);
    }, delay);
  };

  const submit = (ctx: ExtensionContext) => {
    if (!current || isContinuationTerminal(current) || current.pendingToolCount > 0 || disposed) return;
    if (authority !== "coordinator") {
      armTimer(current);
      return;
    }
    const submitted = transitionContinuation(current, { type: "submitted", at: now(), epochs });
    if (submitted.disposition !== "applied") return;
    current = submitted.snapshot;
    persistSnapshot(current);
    try {
      pi.sendMessage({
        customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
        content: CONTINUATION_PROMPT,
        display: false,
        details: continuationMessageDetailsFor(current),
      }, { triggerTurn: true, deliverAs: "steer" });
    } catch {
      // A synchronous throw is submission failure evidence; async host rejection is detected by no consumption.
      const retry = transitionContinuation(current, { type: "agent_settled", at: now(), epochs });
      current = retry.snapshot;
      persistSnapshot(current);
      if (retry.decision === "retry") armTimer(current, retryDelayMs);
      else if (retry.decision === "fail_loudly") {
        persistOutcome(current);
        warnFailure(current, ctx);
      }
      return;
    }
    armTimer(current);
  };

  const apply = (event: ContinuationEvent, ctx = lastContext) => {
    if (!current || disposed) return;
    const result = transitionContinuation(current, event);
    if (result.disposition === "ignored_invalid" || result.disposition === "ignored_stale") return;
    current = result.snapshot;
    if (result.disposition === "applied") persistSnapshot(current);
    if (isContinuationTerminal(current)) {
      cancelTimer();
      persistOutcome(current);
      if (current.state === "failed_loudly" && ctx) warnFailure(current, ctx);
      return;
    }
    if ((result.decision === "retry" || result.decision === "submit") && ctx) {
      if (result.decision === "retry") armTimer(current, retryDelayMs);
      else submit(ctx);
      return;
    }
    armTimer(current);
  };

  const reconcile = (ctx: ExtensionContext) => {
    if (disposed) return;
    lastContext = ctx;
    const entries = ctx.sessionManager.getBranch() as any[];
    const reconciled = reconcileContinuationEntries(entries);
    if (reconciled.invalidEntryIds.length > 0) {
      logPiVccEvent("continuation_invalid_entries", { count: reconciled.invalidEntryIds.length });
    }
    const pending = reconciled.pending[0];
    if (!pending) {
      if (!current || isContinuationTerminal(current)) cancelTimer();
      current = undefined;
      return;
    }
    current = pending;
    epochs = { ...epochs, ...pending.epochs };
    if (now() >= current.deadlineAt) {
      apply({ type: "deadline", at: now(), epochs }, ctx);
      return;
    }
    if (current.state === "waiting_tools" || current.pendingToolCount > 0) {
      armTimer(current);
      return;
    }
    if (current.state === "consumed" || current.state === "progressed" || current.state === "submitted") {
      armTimer(current);
      return;
    }
    submit(ctx);
  };

  const request = (input: ContinuationRequestInput, ctx: ExtensionContext) => {
    lastContext = ctx;
    if (current && !isContinuationTerminal(current)) return current;
    const createdAt = now();
    const adapted = adaptContinuationInitiatorOutcome(input.initiator, input.outcome);
    const snapshot = createContinuationTransaction({
      transactionId: transactionIdFor(input, createdAt),
      origin: adapted.origin,
      reason: adapted.reason,
      ...(input.compactionId ? { compactionId: input.compactionId } : {}),
      attemptId: input.attemptId,
      ...(input.requestId ? { requestId: input.requestId } : {}),
      ...(input.originatingRequestId ? { originatingRequestId: input.originatingRequestId } : {}),
      resumePolicy: input.resumePolicy ?? "active",
      createdAt,
      deadlineMs: input.deadlineMs ?? DEFAULT_DEADLINE_MS,
      pendingToolCount: input.pendingToolCount ?? 0,
      retryLimit: input.retryLimit ?? DEFAULT_RETRY_LIMIT,
      epochs,
    });
    pi.appendEntry(CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE, createContinuationRequestWire(snapshot));
    current = snapshot;
    logContinuationTransaction("created", snapshot, createdAt);
    if (snapshot.resumePolicy === "terminal") {
      apply({ type: "supersede", at: createdAt, reason: "explicitly_stopped", epochs }, ctx);
    } else if (snapshot.pendingToolCount > 0) {
      const waiting = transitionContinuation(snapshot, {
        type: "tools_pending",
        at: createdAt,
        pendingToolCount: snapshot.pendingToolCount,
        epochs,
      });
      current = waiting.snapshot;
      persistSnapshot(current);
      armTimer(current);
    } else {
      submit(ctx);
    }
    return current;
  };

  let wakeUnsubscribe = pi.events.on(CONTINUATION_WAKE_EVENT, () => {
    if (lastContext) reconcile(lastContext);
  });

  pi.on("session_start", (event, ctx) => {
    epochs.session += 1;
    lastContext = ctx;
    if (shuttingDownForReload) {
      wakeUnsubscribe = pi.events.on(CONTINUATION_WAKE_EVENT, () => {
        if (lastContext) reconcile(lastContext);
      });
    }
    shuttingDownForReload = false;
    reconcile(ctx);
  });
  pi.on("agent_start", () => { epochs.agent += 1; });
  pi.on("turn_start", () => { epochs.turn += 1; });
  pi.on("input", (event, ctx) => {
    lastContext = ctx;
    if (!current || isContinuationTerminal(current) || event.source === "extension") return;
    epochs.input += 1;
    apply({ type: "supersede", at: now(), reason: "real_user_input", epochs }, ctx);
  });
  pi.on("tool_execution_end", (_event, ctx) => {
    lastContext = ctx;
    if (!current || current.state !== "waiting_tools" || current.pendingToolCount <= 0) return;
    const pendingToolCount = current.pendingToolCount - 1;
    if (pendingToolCount === 0) {
      current = { ...current, pendingToolCount: 0 };
      apply({ type: "tools_ready", at: now(), epochs }, ctx);
    } else {
      apply({ type: "tools_pending", at: now(), pendingToolCount, epochs }, ctx);
    }
  });
  pi.on("message_start", (event, ctx) => {
    epochs.message += 1;
    lastContext = ctx;
    if (!current || isContinuationTerminal(current)) return;
    const message = event.message as any;
    if (isRealUserMessage(message)) {
      apply({ type: "supersede", at: now(), reason: "real_user_input", epochs }, ctx);
      return;
    }
    const matching = message?.role === "custom"
      && message.customType === CONTINUATION_MESSAGE_CUSTOM_TYPE
      && message.details?.transactionId === current.transactionId;
    if (!matching && isIndependentConsumedInput(message)) {
      epochs.input += 1;
      apply({ type: "supersede", at: now(), reason: "independent_input", epochs }, ctx);
      return;
    }
    apply({ type: "message_start", at: now(), message, epochs }, ctx);
  });
  pi.on("message_end", (event, ctx) => {
    lastContext = ctx;
    const result = classifyAssistantResult((event as any).message);
    if (result) apply({ type: "assistant_result", at: now(), result, epochs }, ctx);
  });
  pi.on("agent_end", (event, ctx) => {
    lastContext = ctx;
    const messages = (event as any).messages;
    const result = classifyAssistantResult(Array.isArray(messages) ? messages.at(-1) : undefined);
    if (result && current?.state === "consumed") apply({ type: "assistant_result", at: now(), result, epochs }, ctx);
  });
  pi.on("agent_settled", (_event, ctx) => {
    epochs.settlement += 1;
    lastContext = ctx;
    apply({ type: "agent_settled", at: now(), epochs }, ctx);
    if (current?.state === "retrying") submit(ctx);
  });
  pi.on("session_shutdown", (event, ctx) => {
    cancelTimer();
    wakeUnsubscribe();
    lastContext = ctx;
    if (!current || isContinuationTerminal(current)) return;
    if (event.reason === "reload") {
      shuttingDownForReload = true;
      persistSnapshot(current);
      return;
    }
    apply({ type: "supersede", at: now(), reason: "session_replaced", epochs: { ...epochs, session: epochs.session + 1 } }, ctx);
  });

  return {
    authority,
    request,
    reconcile,
    getPending: () => current,
    dispose: () => {
      if (disposed) return;
      disposed = true;
      cancelTimer();
      if (!shuttingDownForReload) wakeUnsubscribe();
    },
  };
};
