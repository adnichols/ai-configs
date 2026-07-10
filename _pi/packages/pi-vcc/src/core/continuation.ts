import {
  CONTINUATION_MESSAGE_CUSTOM_TYPE,
  CONTINUATION_PROTOCOL_NAME,
  CONTINUATION_PROTOCOL_VERSION,
  CONTINUATION_TERMINAL_STATES,
  type ContinuationAssistantResult,
  type ContinuationLifecycleEpochs,
  type ContinuationFailureReason,
  type ContinuationOrigin,
  type ContinuationReason,
  type ContinuationResumePolicy,
  type ContinuationSupersedeReason,
  type ContinuationState,
  type ContinuationTransactionSnapshot,
  isMatchingContinuationDetails,
} from "./continuation-protocol";

export interface CreateContinuationTransactionInput {
  transactionId: string;
  origin: ContinuationOrigin;
  reason: ContinuationReason;
  compactionId?: string;
  attemptId: string;
  requestId?: string;
  originatingRequestId?: string;
  resumePolicy: ContinuationResumePolicy;
  createdAt: number;
  deadlineMs: number;
  pendingToolCount?: number;
  retryLimit?: number;
  epochs?: Partial<ContinuationLifecycleEpochs>;
}

export type ContinuationEvent =
  | { type: "tools_pending"; at: number; pendingToolCount: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "tools_ready"; at: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "submitted"; at: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "message_start"; at: number; message: unknown; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "assistant_result"; at: number; result: ContinuationAssistantResult; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "agent_start"; at: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "turn_start"; at: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "agent_settled"; at: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "deadline"; at: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "supersede"; at: number; reason: ContinuationSupersedeReason; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "fail"; at: number; reason: ContinuationFailureReason; epochs?: Partial<ContinuationLifecycleEpochs> };

export type ContinuationDecision = "none" | "submit" | "retry" | "fail_loudly" | "settled" | "superseded";
export type ContinuationTransitionDisposition = "applied" | "idempotent" | "ignored_stale" | "ignored_invalid";

export interface ContinuationTransitionResult {
  snapshot: ContinuationTransactionSnapshot;
  disposition: ContinuationTransitionDisposition;
  decision: ContinuationDecision;
  reason: string;
}

const ZERO_EPOCHS: ContinuationLifecycleEpochs = {
  session: 0,
  input: 0,
  agent: 0,
  turn: 0,
  message: 0,
  settlement: 0,
};

const cloneEpochs = (epochs: ContinuationLifecycleEpochs): ContinuationLifecycleEpochs => ({ ...epochs });

const mergeEpochs = (
  current: ContinuationLifecycleEpochs,
  incoming: Partial<ContinuationLifecycleEpochs> | undefined,
): ContinuationLifecycleEpochs => ({
  session: incoming?.session ?? current.session,
  input: incoming?.input ?? current.input,
  agent: incoming?.agent ?? current.agent,
  turn: incoming?.turn ?? current.turn,
  message: incoming?.message ?? current.message,
  settlement: incoming?.settlement ?? current.settlement,
});

const hasEpochRegression = (
  current: ContinuationLifecycleEpochs,
  incoming: Partial<ContinuationLifecycleEpochs> | undefined,
): boolean => {
  if (!incoming) return false;
  return Object.entries(incoming).some(([key, value]) => {
    if (value === undefined) return false;
    return value < current[key as keyof ContinuationLifecycleEpochs];
  });
};

const sameEpochs = (
  current: ContinuationLifecycleEpochs,
  incoming: Partial<ContinuationLifecycleEpochs> | undefined,
): boolean => !incoming || Object.entries(incoming).every(([key, value]) =>
  value === undefined || value === current[key as keyof ContinuationLifecycleEpochs]);

const isTerminal = (state: ContinuationState): state is "settled" | "superseded" | "failed_loudly" =>
  CONTINUATION_TERMINAL_STATES.includes(state as "settled" | "superseded" | "failed_loudly");

const result = (
  snapshot: ContinuationTransactionSnapshot,
  disposition: ContinuationTransitionDisposition,
  decision: ContinuationDecision,
  reason: string,
): ContinuationTransitionResult => ({ snapshot, disposition, decision, reason });

const withEventEpochs = (
  snapshot: ContinuationTransactionSnapshot,
  event: ContinuationEvent,
): ContinuationTransactionSnapshot => ({
  ...snapshot,
  epochs: mergeEpochs(snapshot.epochs, event.epochs),
});

const retryOrFail = (
  snapshot: ContinuationTransactionSnapshot,
  event: ContinuationEvent,
  reason: string,
): ContinuationTransitionResult => {
  const updated = withEventEpochs(snapshot, event);
  const deadlineExpired = event.at >= snapshot.deadlineAt;
  const nextRetryCount = snapshot.retryCount + 1;
  const retryExhausted = nextRetryCount > snapshot.retryLimit;
  if (deadlineExpired || retryExhausted) {
    return result({
      ...updated,
      state: "failed_loudly",
      terminalReason: deadlineExpired ? "deadline_expired" : "retry_limit_exhausted",
    }, "applied", "fail_loudly", reason);
  }
  return result({
    ...updated,
    state: "retrying",
    retryCount: nextRetryCount,
    consumedEpochs: undefined,
    lastAssistantResult: undefined,
  }, "applied", "retry", reason);
};

const readCustomMessage = (message: unknown): { customType?: unknown; details?: unknown } | undefined =>
  typeof message === "object" && message !== null
    ? message as { customType?: unknown; details?: unknown }
    : undefined;

export const createContinuationTransaction = (
  input: CreateContinuationTransactionInput,
): ContinuationTransactionSnapshot => {
  if (!input.transactionId || !input.attemptId) throw new TypeError("Continuation IDs must be non-empty");
  if (!Number.isFinite(input.createdAt) || input.createdAt < 0) throw new TypeError("createdAt must be a non-negative timestamp");
  if (!Number.isFinite(input.deadlineMs) || input.deadlineMs < 0) throw new TypeError("deadlineMs must be non-negative");
  const pendingToolCount = input.pendingToolCount ?? 0;
  const retryLimit = input.retryLimit ?? 2;
  if (!Number.isInteger(pendingToolCount) || pendingToolCount < 0) throw new TypeError("pendingToolCount must be a non-negative integer");
  if (!Number.isInteger(retryLimit) || retryLimit < 0) throw new TypeError("retryLimit must be a non-negative integer");

  return {
    protocol: CONTINUATION_PROTOCOL_NAME,
    version: CONTINUATION_PROTOCOL_VERSION,
    transactionId: input.transactionId,
    origin: input.origin,
    reason: input.reason,
    ...(input.compactionId ? { compactionId: input.compactionId } : {}),
    attemptId: input.attemptId,
    ...(input.requestId ? { requestId: input.requestId } : {}),
    ...(input.originatingRequestId ? { originatingRequestId: input.originatingRequestId } : {}),
    resumePolicy: input.resumePolicy,
    state: "created",
    createdAt: input.createdAt,
    deadlineAt: input.createdAt + input.deadlineMs,
    pendingToolCount,
    submissionCount: 0,
    retryCount: 0,
    retryLimit,
    epochs: mergeEpochs(ZERO_EPOCHS, input.epochs),
  };
};

export const transitionContinuation = (
  snapshot: ContinuationTransactionSnapshot,
  event: ContinuationEvent,
): ContinuationTransitionResult => {
  if (!Number.isFinite(event.at) || event.at < snapshot.createdAt) {
    return result(snapshot, "ignored_stale", "none", "event_before_transaction_creation");
  }
  if (hasEpochRegression(snapshot.epochs, event.epochs)) {
    return result(snapshot, "ignored_stale", "none", "lifecycle_epoch_regression");
  }
  if (isTerminal(snapshot.state)) {
    if (event.type === "supersede" && snapshot.state === "superseded" && event.reason === snapshot.terminalReason) {
      return result(snapshot, "idempotent", "superseded", "duplicate_terminal_event");
    }
    if (event.type === "fail" && snapshot.state === "failed_loudly" && event.reason === snapshot.terminalReason) {
      return result(snapshot, "idempotent", "fail_loudly", "duplicate_terminal_event");
    }
    if (event.type === "agent_settled" && snapshot.state === "settled") {
      return result(snapshot, "idempotent", "settled", "duplicate_terminal_event");
    }
    return result(snapshot, "ignored_invalid", "none", "transaction_already_terminal");
  }

  if (event.type === "deadline") {
    if (event.at < snapshot.deadlineAt) return result(snapshot, "ignored_stale", "none", "deadline_not_reached");
    return result({
      ...withEventEpochs(snapshot, event),
      state: "failed_loudly",
      terminalReason: "deadline_expired",
    }, "applied", "fail_loudly", "absolute_deadline_expired");
  }

  if (event.type === "supersede") {
    return result({
      ...withEventEpochs(snapshot, event),
      state: "superseded",
      terminalReason: event.reason,
    }, "applied", "superseded", "superseding_real_work_or_session_replacement");
  }

  if (event.type === "fail") {
    return result({
      ...withEventEpochs(snapshot, event),
      state: "failed_loudly",
      terminalReason: event.reason,
    }, "applied", "fail_loudly", "explicit_terminal_failure");
  }

  if (event.type === "agent_start" || event.type === "turn_start") {
    if (sameEpochs(snapshot.epochs, event.epochs)) {
      return result(snapshot, "idempotent", "none", "diagnostic_lifecycle_event");
    }
    return result(withEventEpochs(snapshot, event), "applied", "none", "diagnostic_lifecycle_event");
  }

  if (event.type === "tools_pending") {
    if (!Number.isInteger(event.pendingToolCount) || event.pendingToolCount <= 0) {
      return result(snapshot, "ignored_invalid", "none", "pending_tool_count_must_be_positive");
    }
    if (snapshot.state === "consumed" || snapshot.state === "progressed") {
      return result(snapshot, "ignored_invalid", "none", "cannot_wait_for_tools_after_consumption");
    }
    if (snapshot.state === "waiting_tools" && snapshot.pendingToolCount === event.pendingToolCount && sameEpochs(snapshot.epochs, event.epochs)) {
      return result(snapshot, "idempotent", "none", "duplicate_tools_pending");
    }
    return result({
      ...withEventEpochs(snapshot, event),
      state: "waiting_tools",
      pendingToolCount: event.pendingToolCount,
    }, "applied", "none", "waiting_for_outstanding_tools");
  }

  if (event.type === "tools_ready") {
    if (snapshot.state !== "waiting_tools") {
      return snapshot.pendingToolCount === 0
        ? result(snapshot, "idempotent", "submit", "tools_already_ready")
        : result(snapshot, "ignored_invalid", "none", "tools_ready_outside_waiting_state");
    }
    return result({
      ...withEventEpochs(snapshot, event),
      state: snapshot.retryCount > 0 ? "retrying" : "created",
      pendingToolCount: 0,
    }, "applied", "submit", "tool_safety_reached");
  }

  if (event.type === "submitted") {
    if (snapshot.pendingToolCount > 0 || snapshot.state === "waiting_tools") {
      return result(snapshot, "ignored_invalid", "none", "cannot_submit_with_pending_tools");
    }
    if (snapshot.state === "submitted") {
      return result(snapshot, "idempotent", "none", "duplicate_submission_acceptance");
    }
    if (snapshot.state !== "created" && snapshot.state !== "retrying") {
      return result(snapshot, "ignored_invalid", "none", "submission_not_allowed_from_current_state");
    }
    return result({
      ...withEventEpochs(snapshot, event),
      state: "submitted",
      submissionCount: snapshot.submissionCount + 1,
    }, "applied", "none", "submission_accepted_without_delivery_claim");
  }

  if (event.type === "message_start") {
    const message = readCustomMessage(event.message);
    const matches = message?.customType === CONTINUATION_MESSAGE_CUSTOM_TYPE
      && isMatchingContinuationDetails(snapshot, message.details);
    if (!matches) return result(snapshot, "ignored_invalid", "none", "message_does_not_match_transaction");
    if (snapshot.state === "consumed" || snapshot.state === "progressed") {
      return result(snapshot, "idempotent", "none", "duplicate_matching_message_start");
    }
    if (snapshot.state !== "submitted") {
      return result(snapshot, "ignored_invalid", "none", "matching_message_not_submitted_by_transaction");
    }
    const epochs = mergeEpochs(snapshot.epochs, event.epochs);
    return result({
      ...snapshot,
      state: "consumed",
      epochs,
      consumedEpochs: cloneEpochs(epochs),
      lastAssistantResult: undefined,
    }, "applied", "none", "matching_continuation_consumed");
  }

  if (event.type === "assistant_result") {
    if (snapshot.state === "progressed" && event.result === "progress") {
      return result(snapshot, "idempotent", "none", "duplicate_assistant_progress");
    }
    if (snapshot.state !== "consumed") {
      return result(snapshot, "ignored_invalid", "none", "assistant_result_requires_consumption");
    }
    if (event.result === "progress") {
      return result({
        ...withEventEpochs(snapshot, event),
        state: "progressed",
        lastAssistantResult: "progress",
      }, "applied", "none", "non_terminal_assistant_progress_observed");
    }
    if (snapshot.lastAssistantResult === event.result && sameEpochs(snapshot.epochs, event.epochs)) {
      return result(snapshot, "idempotent", "none", "duplicate_terminal_assistant_result");
    }
    return result({
      ...withEventEpochs(snapshot, event),
      lastAssistantResult: event.result,
    }, "applied", "none", "terminal_assistant_result_observed");
  }

  if (event.type === "agent_settled") {
    if (snapshot.state === "progressed") {
      return result({
        ...withEventEpochs(snapshot, event),
        state: "settled",
        terminalReason: "progressed_then_agent_settled",
      }, "applied", "settled", "successful_continuation_settlement");
    }
    if (snapshot.state === "consumed" && (snapshot.lastAssistantResult === "error" || snapshot.lastAssistantResult === "aborted")) {
      return retryOrFail(snapshot, event, `settled_after_${snapshot.lastAssistantResult}`);
    }
    if (snapshot.state === "submitted") {
      return retryOrFail(snapshot, event, "settled_without_matching_consumption");
    }
    if (snapshot.state === "created" || snapshot.state === "waiting_tools" || snapshot.state === "retrying") {
      return retryOrFail(snapshot, event, "settled_before_submission_or_consumption");
    }
  }

  return result(snapshot, "ignored_invalid", "none", "event_not_allowed_from_current_state");
};

export const isContinuationTerminal = (snapshot: ContinuationTransactionSnapshot): boolean =>
  isTerminal(snapshot.state);
