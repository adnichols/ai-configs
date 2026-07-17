import {
  CONTINUATION_MESSAGE_CUSTOM_TYPE,
  CONTINUATION_PROTOCOL_NAME,
  CONTINUATION_PROTOCOL_VERSION,
  CONTINUATION_TERMINAL_STATES,
  type ContinuationAssistantResult,
  type ContinuationFailureReason,
  type ContinuationLifecycleEpochs,
  type ContinuationOrigin,
  type ContinuationReason,
  type ContinuationResumePolicy,
  type ContinuationState,
  type ContinuationSupersedeReason,
  type ContinuationTransactionSnapshot,
  isMatchingContinuationDetails,
} from "./continuation-protocol";

export interface CreateContinuationTransactionInput {
  transactionId: string; origin: ContinuationOrigin; reason: ContinuationReason; compactionId?: string; attemptId: string;
  requestId?: string; originatingRequestId?: string; resumePolicy: ContinuationResumePolicy; createdAt: number; deadlineMs: number;
  pendingToolCount?: number; retryLimit?: number; epochs?: Partial<ContinuationLifecycleEpochs>;
}

export type ContinuationEvent =
  | { type: "activate"; at: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "tools_pending"; at: number; pendingToolCount: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "tools_ready"; at: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "submitted"; at: number; acceptanceDeadlineAt?: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "durable_acceptance"; at: number; details: unknown; progressDeadlineAt?: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "message_start"; at: number; message: unknown; progressDeadlineAt?: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "assistant_result"; at: number; result: ContinuationAssistantResult; pendingToolCount?: number; progressDeadlineAt?: number; toolStallDeadlineAt?: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "tool_progress"; at: number; pendingToolCount: number; progressDeadlineAt?: number; toolStallDeadlineAt?: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "agent_start"; at: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "turn_start"; at: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "agent_settled"; at: number; nextRetryAt?: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "retry_ready"; at: number; nextRetryAt: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "acceptance_deadline"; at: number; nextRetryAt?: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "progress_deadline"; at: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "progress_deadline_deferred"; at: number; progressDeadlineAt: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "tool_stall"; at: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "deadline"; at: number; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "supersede"; at: number; reason: ContinuationSupersedeReason; epochs?: Partial<ContinuationLifecycleEpochs> }
  | { type: "fail"; at: number; reason: ContinuationFailureReason; epochs?: Partial<ContinuationLifecycleEpochs> };

export type ContinuationDecision = "none" | "submit" | "retry" | "fail_loudly" | "settled" | "superseded" | "warn_stalled";
export type ContinuationTransitionDisposition = "applied" | "idempotent" | "ignored_stale" | "ignored_invalid";
export interface ContinuationTransitionResult { snapshot: ContinuationTransactionSnapshot; disposition: ContinuationTransitionDisposition; decision: ContinuationDecision; reason: string }

const ZERO_EPOCHS: ContinuationLifecycleEpochs = { session: 0, input: 0, agent: 0, turn: 0, message: 0, settlement: 0 };
const mergeEpochs = (current: ContinuationLifecycleEpochs, incoming?: Partial<ContinuationLifecycleEpochs>): ContinuationLifecycleEpochs => ({
  session: incoming?.session ?? current.session, input: incoming?.input ?? current.input, agent: incoming?.agent ?? current.agent,
  turn: incoming?.turn ?? current.turn, message: incoming?.message ?? current.message, settlement: incoming?.settlement ?? current.settlement,
});
const regresses = (current: ContinuationLifecycleEpochs, incoming?: Partial<ContinuationLifecycleEpochs>) => incoming ? Object.entries(incoming).some(([key, value]) => value !== undefined && value < current[key as keyof ContinuationLifecycleEpochs]) : false;
const sameEpochs = (current: ContinuationLifecycleEpochs, incoming?: Partial<ContinuationLifecycleEpochs>) => !incoming || Object.entries(incoming).every(([key, value]) => value === undefined || value === current[key as keyof ContinuationLifecycleEpochs]);
const terminal = (state: ContinuationState): state is "settled" | "superseded" | "failed_loudly" => CONTINUATION_TERMINAL_STATES.includes(state as never);
const output = (snapshot: ContinuationTransactionSnapshot, disposition: ContinuationTransitionDisposition, decision: ContinuationDecision, reason: string): ContinuationTransitionResult => ({ snapshot, disposition, decision, reason });
const changed = (snapshot: ContinuationTransactionSnapshot, event: ContinuationEvent, updates: Partial<ContinuationTransactionSnapshot>): ContinuationTransactionSnapshot => ({ ...snapshot, ...updates, epochs: mergeEpochs(snapshot.epochs, event.epochs), phaseEpoch: (snapshot.phaseEpoch ?? 0) + 1 });
const readMessage = (message: unknown): { customType?: unknown; details?: unknown } | undefined => typeof message === "object" && message !== null ? message as { customType?: unknown; details?: unknown } : undefined;

export const createContinuationTransaction = (input: CreateContinuationTransactionInput): ContinuationTransactionSnapshot => {
  if (!input.transactionId || !input.attemptId) throw new TypeError("Continuation IDs must be non-empty");
  if (!Number.isFinite(input.createdAt) || input.createdAt < 0 || !Number.isFinite(input.deadlineMs) || input.deadlineMs < 0) throw new TypeError("Continuation timestamps must be non-negative");
  const pendingToolCount = input.pendingToolCount ?? 0; const retryLimit = input.retryLimit ?? 2;
  if (!Number.isInteger(pendingToolCount) || pendingToolCount < 0 || !Number.isInteger(retryLimit) || retryLimit < 0) throw new TypeError("Continuation counts must be non-negative integers");
  return {
    protocol: CONTINUATION_PROTOCOL_NAME, version: CONTINUATION_PROTOCOL_VERSION, transactionId: input.transactionId, origin: input.origin, reason: input.reason,
    ...(input.compactionId ? { compactionId: input.compactionId } : {}), attemptId: input.attemptId, ...(input.requestId ? { requestId: input.requestId } : {}),
    ...(input.originatingRequestId ? { originatingRequestId: input.originatingRequestId } : {}), resumePolicy: input.resumePolicy, state: "created",
    createdAt: input.createdAt, queuedAt: input.createdAt, deadlineAt: input.createdAt + input.deadlineMs, phaseEpoch: 0, pendingToolCount,
    submissionCount: 0, retryCount: 0, retryLimit, epochs: mergeEpochs(ZERO_EPOCHS, input.epochs),
  };
};

const retryOrFail = (
  snapshot: ContinuationTransactionSnapshot,
  event: Extract<ContinuationEvent, { type: "agent_settled" | "acceptance_deadline" }>,
  reason: string,
) => {
  const nextRetryCount = snapshot.retryCount + 1;
  if (nextRetryCount > snapshot.retryLimit) {
    return output(
      changed(snapshot, event, {
        state: "failed_loudly",
        terminalReason: "retry_limit_exhausted",
        acceptanceDeadlineAt: undefined,
        progressDeadlineAt: undefined,
        toolStallDeadlineAt: undefined,
        nextRetryAt: undefined,
      }),
      "applied",
      "fail_loudly",
      reason,
    );
  }
  return output(
    changed(snapshot, event, {
      state: "retrying",
      retryCount: nextRetryCount,
      consumedEpochs: undefined,
      acceptedAt: undefined,
      submittedAt: undefined,
      acceptanceDeadlineAt: undefined,
      lastProgressAt: undefined,
      progressDeadlineAt: undefined,
      toolStallDeadlineAt: undefined,
      nextRetryAt: event.nextRetryAt ?? event.at,
      lastAssistantResult: undefined,
      pendingToolCount: 0,
    }),
    "applied",
    "retry",
    reason,
  );
};

export const transitionContinuation = (snapshot: ContinuationTransactionSnapshot, event: ContinuationEvent): ContinuationTransitionResult => {
  if (!Number.isFinite(event.at) || event.at < snapshot.createdAt) return output(snapshot, "ignored_stale", "none", "event_before_transaction_creation");
  if (regresses(snapshot.epochs, event.epochs)) return output(snapshot, "ignored_stale", "none", "lifecycle_epoch_regression");
  if (terminal(snapshot.state)) {
    const duplicate = (event.type === "supersede" && snapshot.state === "superseded" && event.reason === snapshot.terminalReason) || (event.type === "fail" && snapshot.state === "failed_loudly" && event.reason === snapshot.terminalReason) || (event.type === "agent_settled" && snapshot.state === "settled");
    return output(snapshot, duplicate ? "idempotent" : "ignored_invalid", duplicate ? snapshot.state === "settled" ? "settled" : snapshot.state === "superseded" ? "superseded" : "fail_loudly" : "none", duplicate ? "duplicate_terminal_event" : "transaction_already_terminal");
  }
  if (event.type === "supersede") return output(changed(snapshot, event, { state: "superseded", terminalReason: event.reason, acceptanceDeadlineAt: undefined, progressDeadlineAt: undefined, toolStallDeadlineAt: undefined, nextRetryAt: undefined }), "applied", "superseded", "superseding_real_work_or_session_replacement");
  if (event.type === "fail") return output(changed(snapshot, event, { state: "failed_loudly", terminalReason: event.reason, acceptanceDeadlineAt: undefined, progressDeadlineAt: undefined, toolStallDeadlineAt: undefined, nextRetryAt: undefined }), "applied", "fail_loudly", "explicit_terminal_failure");
  if (event.type === "activate") {
    if (snapshot.activatedAt !== undefined) return output(snapshot, "idempotent", "none", "already_activated");
    return output(changed(snapshot, event, { activatedAt: event.at }), "applied", "none", "activated_with_full_budget");
  }
  if (event.type === "agent_start" || event.type === "turn_start") return sameEpochs(snapshot.epochs, event.epochs) ? output(snapshot, "idempotent", "none", "diagnostic_lifecycle_event") : output(changed(snapshot, event, {}), "applied", "none", "diagnostic_lifecycle_event");
  if (event.type === "retry_ready") {
    if (snapshot.state !== "retrying") return output(snapshot, "ignored_invalid", "none", "retry_readiness_outside_retry_wait");
    if (snapshot.nextRetryAt === event.nextRetryAt && sameEpochs(snapshot.epochs, event.epochs)) return output(snapshot, "idempotent", "retry", "duplicate_retry_readiness");
    return output(changed(snapshot, event, { nextRetryAt: event.nextRetryAt }), "applied", "retry", "host_ready_retry_backoff_started");
  }
  if (event.type === "tools_pending") {
    if (!Number.isInteger(event.pendingToolCount) || event.pendingToolCount <= 0 || snapshot.acceptedAt !== undefined) return output(snapshot, "ignored_invalid", "none", "pending_tool_count_invalid_for_phase");
    if (snapshot.state === "waiting_tools" && snapshot.pendingToolCount === event.pendingToolCount && sameEpochs(snapshot.epochs, event.epochs)) return output(snapshot, "idempotent", "none", "duplicate_tools_pending");
    return output(changed(snapshot, event, { state: "waiting_tools", pendingToolCount: event.pendingToolCount }), "applied", "none", "waiting_for_outstanding_tools");
  }
  if (event.type === "tools_ready") {
    if (snapshot.state !== "waiting_tools") return snapshot.pendingToolCount === 0 ? output(snapshot, "idempotent", "submit", "tools_already_ready") : output(snapshot, "ignored_invalid", "none", "tools_ready_outside_waiting_state");
    return output(changed(snapshot, event, { state: snapshot.retryCount > 0 ? "retrying" : "created", pendingToolCount: 0 }), "applied", "submit", "tool_safety_reached");
  }
  if (event.type === "submitted") {
    if (snapshot.pendingToolCount > 0 || snapshot.state === "waiting_tools") return output(snapshot, "ignored_invalid", "none", "cannot_submit_with_pending_tools");
    if (snapshot.state === "submitted") return output(snapshot, "idempotent", "none", "duplicate_submission_acceptance");
    if (snapshot.state !== "created" && snapshot.state !== "retrying") return output(snapshot, "ignored_invalid", "none", "submission_not_allowed_from_current_state");
    return output(changed(snapshot, event, { state: "submitted", activatedAt: snapshot.activatedAt ?? event.at, submittedAt: event.at, acceptanceDeadlineAt: event.acceptanceDeadlineAt ?? snapshot.deadlineAt, deadlineAt: event.acceptanceDeadlineAt ?? snapshot.deadlineAt, nextRetryAt: undefined, submissionCount: snapshot.submissionCount + 1 }), "applied", "none", "submission_recorded_without_delivery_claim");
  }
  if (event.type === "durable_acceptance" || event.type === "message_start") {
    const details = event.type === "durable_acceptance" ? event.details : readMessage(event.message)?.customType === CONTINUATION_MESSAGE_CUSTOM_TYPE ? readMessage(event.message)?.details : undefined;
    if (!isMatchingContinuationDetails(snapshot, details)) return output(snapshot, "ignored_invalid", "none", "message_does_not_match_transaction");
    if (snapshot.acceptedAt !== undefined || snapshot.state === "consumed" || snapshot.state === "progressed" || snapshot.state === "stalled") return output(snapshot, "idempotent", "none", "duplicate_matching_acceptance");
    if (snapshot.state !== "submitted" && snapshot.state !== "retrying") return output(snapshot, "ignored_invalid", "none", "matching_message_not_submitted_by_transaction");
    const epochs = mergeEpochs(snapshot.epochs, event.epochs);
    return output({ ...changed(snapshot, event, { state: "consumed", acceptedAt: event.at, acceptanceDeadlineAt: undefined, progressDeadlineAt: event.progressDeadlineAt, deadlineAt: event.progressDeadlineAt ?? snapshot.deadlineAt, lastAssistantResult: undefined }), consumedEpochs: { ...epochs } }, "applied", "none", event.type === "durable_acceptance" ? "matching_continuation_durably_accepted" : "matching_continuation_message_started");
  }
  if (event.type === "assistant_result" || event.type === "tool_progress") {
    if (snapshot.acceptedAt === undefined) return output(snapshot, "ignored_invalid", "none", "progress_requires_durable_acceptance");
    if (event.type === "assistant_result" && event.result === "progress" && snapshot.state === "progressed" && sameEpochs(snapshot.epochs, event.epochs)) return output(snapshot, "idempotent", "none", "duplicate_assistant_progress");
    if (event.type === "assistant_result" && event.result !== "progress") {
      if (snapshot.lastAssistantResult === event.result && sameEpochs(snapshot.epochs, event.epochs)) return output(snapshot, "idempotent", "none", "duplicate_terminal_assistant_result");
      return output(changed(snapshot, event, { lastAssistantResult: event.result }), "applied", "none", "terminal_assistant_result_observed");
    }
    const pendingToolCount = event.pendingToolCount ?? snapshot.pendingToolCount;
    const updates: Partial<ContinuationTransactionSnapshot> = { state: "progressed", lastProgressAt: event.at, lastAssistantResult: "progress", pendingToolCount, progressDeadlineAt: pendingToolCount === 0 ? event.progressDeadlineAt : undefined, toolStallDeadlineAt: pendingToolCount > 0 ? event.toolStallDeadlineAt : undefined, deadlineAt: (pendingToolCount > 0 ? event.toolStallDeadlineAt : event.progressDeadlineAt) ?? snapshot.deadlineAt, stalledWarningIssued: false };
    return output(changed(snapshot, event, updates), "applied", "none", snapshot.state === "stalled" ? "correlated_progress_resumed_stalled_transaction" : "post_acceptance_progress_observed");
  }
  if (event.type === "tool_stall") {
    if (snapshot.pendingToolCount <= 0 || snapshot.acceptedAt === undefined || snapshot.toolStallDeadlineAt === undefined || event.at < snapshot.toolStallDeadlineAt) return output(snapshot, "ignored_stale", "none", "tool_stall_deadline_not_reached");
    if (snapshot.state === "stalled") return output(snapshot, "idempotent", "none", "already_stalled");
    return output(changed(snapshot, event, { state: "stalled", toolStallDeadlineAt: undefined, stalledWarningIssued: true }), "applied", "warn_stalled", "outstanding_tool_hard_silence");
  }
  if (event.type === "progress_deadline_deferred") {
    if (
      snapshot.pendingToolCount > 0 ||
      snapshot.acceptedAt === undefined ||
      snapshot.progressDeadlineAt === undefined ||
      event.at < snapshot.progressDeadlineAt ||
      !Number.isFinite(event.progressDeadlineAt) ||
      event.progressDeadlineAt <= event.at
    ) return output(snapshot, "ignored_stale", "none", "progress_deadline_deferral_invalid");
    return output(changed(snapshot, event, { progressDeadlineAt: event.progressDeadlineAt, deadlineAt: event.progressDeadlineAt }), "applied", "none", "active_host_progress_deadline_deferred");
  }
  if (event.type === "progress_deadline") {
    if (snapshot.pendingToolCount > 0 || snapshot.progressDeadlineAt === undefined || event.at < snapshot.progressDeadlineAt) return output(snapshot, "ignored_stale", "none", "progress_deadline_not_reached");
    return output(changed(snapshot, event, { state: "failed_loudly", terminalReason: "deadline_expired", progressDeadlineAt: undefined }), "applied", "fail_loudly", "active_progress_inactivity_expired");
  }
  if (event.type === "acceptance_deadline") {
    if (snapshot.acceptedAt !== undefined || snapshot.acceptanceDeadlineAt === undefined || event.at < snapshot.acceptanceDeadlineAt) return output(snapshot, "ignored_stale", "none", "acceptance_deadline_not_reached");
    return retryOrFail(snapshot, event, "durable_acceptance_not_observed");
  }
  if (event.type === "deadline") {
    if (event.at < snapshot.deadlineAt) return output(snapshot, "ignored_stale", "none", "deadline_not_reached");
    if (snapshot.state === "submitted") return retryOrFail(snapshot, { type: "acceptance_deadline", at: event.at, nextRetryAt: event.at, epochs: event.epochs }, "legacy_deadline_expired_before_acceptance");
    return output(changed(snapshot, event, { state: "failed_loudly", terminalReason: "deadline_expired" }), "applied", "fail_loudly", "legacy_deadline_expired");
  }
  if (event.type === "agent_settled") {
    if (snapshot.state === "progressed" && snapshot.lastAssistantResult === "progress" && snapshot.pendingToolCount === 0) return output(changed(snapshot, event, { state: "settled", terminalReason: "progressed_then_agent_settled", progressDeadlineAt: undefined, toolStallDeadlineAt: undefined }), "applied", "settled", "successful_continuation_settlement");
    if (snapshot.state === "stalled") return output(snapshot, "ignored_invalid", "none", "stalled_transaction_retains_ownership");
    if (snapshot.state === "retrying") return output(snapshot, "idempotent", "retry", "retry_already_recorded_waiting_for_readiness");
    if ((snapshot.state === "consumed" || snapshot.state === "progressed") && (snapshot.lastAssistantResult === "error" || snapshot.lastAssistantResult === "aborted")) return retryOrFail(snapshot, event, `settled_after_${snapshot.lastAssistantResult}`);
    if (["submitted", "created", "waiting_tools", "consumed"].includes(snapshot.state)) return retryOrFail(snapshot, event, "settled_without_successful_progress");
  }
  return output(snapshot, "ignored_invalid", "none", "event_not_allowed_from_current_state");
};

export const isContinuationTerminal = (snapshot: ContinuationTransactionSnapshot) => terminal(snapshot.state);
