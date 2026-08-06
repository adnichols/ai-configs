import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";
import type { CompactionResumeIntent } from "../types";
import { classifyCustomMessageIntent } from "./custom-message-classifier";
import { createContinuationTransaction, isContinuationTerminal, transitionContinuation, type ContinuationEvent } from "./continuation";
import {
  adaptContinuationInitiatorOutcome,
  CONTINUATION_MESSAGE_CUSTOM_TYPE,
  CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
  CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
  CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE,
  type ContinuationAttemptOutcome,
  type ContinuationInitiator,
  type ContinuationLifecycleEpochs,
  type ContinuationMessageDetails,
  type ContinuationResumePolicy,
  type ContinuationState,
  type ContinuationTransactionSnapshot,
  continuationMessageDetailsFor,
  createContinuationOutcomeWire,
  createContinuationRequestWire,
  createContinuationSnapshotWire,
  isMatchingContinuationDetails,
  reconcileContinuationEntries,
} from "./continuation-protocol";
import { getPiVccLogPath, logContinuationTransaction, logPiVccError, logPiVccEvent } from "./log";

export const CONTINUATION_WAKE_EVENT = "pi-vcc:continuation-requested";
export const CONTINUATION_SAFETY_READY_WAKE_EVENT = "pi-vcc:continuation-safety-ready";
export const CONTINUATION_AUTHORITY_ENV = "PI_VCC_CONTINUATION_AUTHORITY";
export const DEFAULT_ACCEPTANCE_DEADLINE_MS = 15_000;
export const DEFAULT_IDLE_PROGRESS_DEADLINE_MS = 60_000;
export const DEFAULT_TOOL_STALL_DEADLINE_MS = 900_000;
export const DEFAULT_TOOL_LIVENESS_CHECKPOINT_MS = 30_000;
export const DEFAULT_RETRY_DELAYS_MS = [1_000, 2_000] as const;
const DEFAULT_RETRY_LIMIT = 2;
const CONTINUATION_PROMPT = "Pi-vcc interrupted active work for compaction or recovery. Continue from the preserved state and resume the next concrete step; use vcc_recall if details from before compaction are needed.";

export type ContinuationAuthority = "coordinator";
export interface ContinuationRequestInput {
  initiator: ContinuationInitiator; outcome: ContinuationAttemptOutcome; attemptId: string; compactionId?: string; requestId?: string;
  originatingRequestId?: string; resumePolicy: ContinuationResumePolicy; pendingToolCount?: number; deadlineMs?: number; retryLimit?: number; transactionId?: string;
}
export interface ContinuationFacadeRequest extends Omit<ContinuationRequestInput, "resumePolicy"> {
  resumeIntent: CompactionResumeIntent;
}
export interface ContinuationFacade {
  request(input: ContinuationFacadeRequest, ctx: ExtensionContext): ContinuationTransactionSnapshot;
  getPending(): ContinuationTransactionSnapshot | undefined;
}
export const continuationResumePolicyFor = (intent: CompactionResumeIntent): ContinuationResumePolicy =>
  intent === "active" ? "active" : "terminal";
export interface ContinuationCoordinatorOptions {
  authority?: ContinuationAuthority; now?: () => number;
  setTimer?: (callback: () => void, delayMs: number) => ReturnType<typeof setTimeout>;
  clearTimer?: (timer: ReturnType<typeof setTimeout>) => void;
  retryDelayMs?: number; retryDelaysMs?: readonly number[]; acceptanceDeadlineMs?: number; idleProgressDeadlineMs?: number; toolStallDeadlineMs?: number; toolLivenessCheckpointMs?: number;
  onSessionReplacement?: (reason: "reload" | "new" | "resume" | "fork") => void;
}
export interface ContinuationCoordinator {
  authority: ContinuationAuthority;
  request(input: ContinuationRequestInput, ctx: ExtensionContext): ContinuationTransactionSnapshot;
  reconcile(ctx: ExtensionContext): void;
  getPending(): ContinuationTransactionSnapshot | undefined;
  getNextToolLivenessCheckpointAt(): number | undefined;
  dispose(): void;
}

const transactionIdFor = (input: ContinuationRequestInput, at: number) => input.transactionId ?? `vcc-${at.toString(36)}-${input.attemptId}`;
const logEventForState = (state: ContinuationState) =>
  state === "failed_loudly" ? "failed" as const : state;
const readAuthority = (): ContinuationAuthority => {
  const value = process.env[CONTINUATION_AUTHORITY_ENV]?.trim().toLowerCase();
  if (value && value !== "coordinator") throw new Error(`${CONTINUATION_AUTHORITY_ENV}=${value} is unsupported; restore the archived release for rollback`);
  return "coordinator";
};
const isRealUserMessage = (message: any) => message?.role === "user" && typeof message?.customType !== "string";
const mergeEpochMax = (a: ContinuationLifecycleEpochs, b: ContinuationLifecycleEpochs): ContinuationLifecycleEpochs => ({ session: Math.max(a.session, b.session), input: Math.max(a.input, b.input), agent: Math.max(a.agent, b.agent), turn: Math.max(a.turn, b.turn), message: Math.max(a.message, b.message), settlement: Math.max(a.settlement, b.settlement) });
const withEpochBaseline = (snapshot: ContinuationTransactionSnapshot, baseline: ContinuationLifecycleEpochs): ContinuationTransactionSnapshot => ({ ...snapshot, epochs: mergeEpochMax(baseline, snapshot.epochs), ...(snapshot.consumedEpochs ? { consumedEpochs: mergeEpochMax(mergeEpochMax(baseline, snapshot.epochs), snapshot.consumedEpochs) } : {}) });
const assistantResult = (message: any): "progress" | "error" | "aborted" | undefined => {
  if (message?.role !== "assistant") return undefined;
  if (message.stopReason === "error") return "error";
  if (message.stopReason === "aborted") return "aborted";
  if (message.stopReason === "stop" || message.stopReason === "toolUse") return "progress";
  return undefined;
};
const toolCallIds = (message: any): string[] => Array.isArray(message?.content)
  ? message.content.flatMap((part: any) => (part?.type === "toolCall" || part?.type === "toolUse") && typeof part.id === "string" && part.id.length > 0 ? [part.id] : [])
  : [];
const toolCallCount = (message: any) => Array.isArray(message?.content) ? message.content.filter((part: any) => part?.type === "toolCall" || part?.type === "toolUse").length : 0;
const entryMessage = (entry: any) => entry?.type === "message" ? entry.message : undefined;
interface RestoredToolCorrelation {
  confirmed: Set<string>;
  ambiguous: Set<string>;
}

const restoredOutstandingToolIds = (entries: readonly any[], snapshot: ContinuationTransactionSnapshot): RestoredToolCorrelation => {
  const discovered: string[] = [];
  const discoveredSet = new Set<string>();
  const completed = new Set<string>();
  let continuationSeen = false;
  for (const entry of entries) {
    const topLevelCustomMessage = entry?.type === "custom_message"
      ? { role: "custom", customType: entry.customType, details: entry.details ?? entry.data?.details }
      : undefined;
    if (topLevelCustomMessage?.customType === CONTINUATION_MESSAGE_CUSTOM_TYPE && isMatchingContinuationDetails(snapshot, topLevelCustomMessage.details)) continuationSeen = true;
    const message = entryMessage(entry);
    if (!continuationSeen) continue;
    const boundaryMessage = message ?? topLevelCustomMessage;
    if (isRealUserMessage(boundaryMessage)) break;
    if (boundaryMessage?.role === "custom" && classifyCustomMessageIntent(boundaryMessage, snapshot) === "independent") break;
    if (!message) continue;
    if (message.role === "assistant") {
      for (const id of toolCallIds(message)) {
        if (discoveredSet.has(id)) continue;
        discoveredSet.add(id);
        discovered.push(id);
      }
    }
    if (message.role === "toolResult" && typeof message.toolCallId === "string" && discoveredSet.has(message.toolCallId)) completed.add(message.toolCallId);
  }
  const outstanding = discovered.filter((id) => !completed.has(id));
  if (outstanding.length < snapshot.pendingToolCount) return { confirmed: new Set(), ambiguous: new Set() };
  if (outstanding.length === snapshot.pendingToolCount) return { confirmed: new Set(outstanding), ambiguous: new Set() };
  // Pi emits parallel tool completions as they finish but persists their result
  // messages only after the whole batch completes in assistant source order.
  // A smaller persisted pending count can therefore prove that some calls
  // finished without proving which ones. Keep those durable call IDs as
  // candidates only: a later matching lifecycle event can disambiguate one,
  // while unrelated IDs remain non-authoritative and the transaction stalls.
  return { confirmed: new Set(), ambiguous: new Set(outstanding) };
};
const toTimestamp = (value: number | undefined, fallback: number) => value !== undefined && Number.isFinite(value) ? value : fallback;
const requirePositiveIntegerOption = (name: string, value: number, minimum = 1) => {
  if (!Number.isFinite(value) || !Number.isInteger(value) || value < minimum) {
    const minimumDescription = minimum === 1 ? "a finite positive integer" : `a finite integer >= ${minimum}`;
    throw new TypeError(`${name} must be ${minimumDescription} milliseconds; received ${String(value)}`);
  }
};
export const continuationLivenessCheckpointOrigin = (snapshot: ContinuationTransactionSnapshot) => snapshot.lastProgressAt ?? snapshot.acceptedAt ?? snapshot.createdAt;

export const createContinuationCoordinator = (pi: ExtensionAPI, options: ContinuationCoordinatorOptions = {}): ContinuationCoordinator => {
  const authority = options.authority ?? readAuthority(); const now = options.now ?? Date.now; const setTimer = options.setTimer ?? setTimeout; const clearTimer = options.clearTimer ?? clearTimeout;
  const acceptanceMs = options.acceptanceDeadlineMs ?? DEFAULT_ACCEPTANCE_DEADLINE_MS;
  const progressMs = options.idleProgressDeadlineMs ?? DEFAULT_IDLE_PROGRESS_DEADLINE_MS;
  const toolStallMs = options.toolStallDeadlineMs ?? DEFAULT_TOOL_STALL_DEADLINE_MS;
  const configuredToolLivenessCheckpointMs = options.toolLivenessCheckpointMs ?? DEFAULT_TOOL_LIVENESS_CHECKPOINT_MS;
  requirePositiveIntegerOption("toolStallDeadlineMs", toolStallMs, 2);
  requirePositiveIntegerOption("toolLivenessCheckpointMs", configuredToolLivenessCheckpointMs);
  const toolLivenessCheckpointMs = Math.min(configuredToolLivenessCheckpointMs, Math.floor(toolStallMs / 2));
  const retryDelays = options.retryDelayMs === undefined ? options.retryDelaysMs ?? DEFAULT_RETRY_DELAYS_MS : [options.retryDelayMs, options.retryDelayMs];
  let current: ContinuationTransactionSnapshot | undefined; let lastTerminal: ContinuationTransactionSnapshot | undefined; let timer: ReturnType<typeof setTimeout> | undefined;
  let lastContext: ExtensionContext | undefined; let disposed = false; let sessionShutDown = false; let wakeUnsubscribe: (() => void) | undefined; let safetyWakeUnsubscribe: (() => void) | undefined;
  let retryReadyTransactionId: string | undefined;
  let durableTransactionId: string | undefined;
  let durablePhaseEpoch = -1;
  let nextToolLivenessCheckpointAt: number | undefined;
  let epochs: ContinuationLifecycleEpochs = { session: 0, input: 0, agent: 0, turn: 0, message: 0, settlement: 0 };
  const acceptanceBudgets = new Map<string, number>();
  const activeToolCallIds = new Set<string>();
  const ambiguousToolCallIds = new Set<string>();
  const clearToolCorrelation = () => { activeToolCallIds.clear(); ambiguousToolCallIds.clear(); };
  const restoreToolCorrelation = (ctx: ExtensionContext, snapshot: ContinuationTransactionSnapshot) => {
    clearToolCorrelation();
    if (snapshot.pendingToolCount === 0) return;
    const restored = restoredOutstandingToolIds(ctx.sessionManager.getBranch() as any[], snapshot);
    for (const id of restored.confirmed) activeToolCallIds.add(id);
    for (const id of restored.ambiguous) ambiguousToolCallIds.add(id);
  };
  const confirmAmbiguousTool = (id: string) => {
    if (!ambiguousToolCallIds.delete(id)) return false;
    activeToolCallIds.add(id);
    if (current && activeToolCallIds.size >= current.pendingToolCount) ambiguousToolCallIds.clear();
    return true;
  };
  const rememberAcceptanceBudget = (snapshot: ContinuationTransactionSnapshot) => {
    if (acceptanceBudgets.has(snapshot.transactionId)) return;
    const persistedBudget = snapshot.version === 2 &&
      snapshot.submittedAt !== undefined &&
      snapshot.acceptanceDeadlineAt !== undefined
      ? snapshot.acceptanceDeadlineAt - snapshot.submittedAt
      : snapshot.version === 2 && snapshot.state === "created"
        ? snapshot.deadlineAt - snapshot.createdAt
        : acceptanceMs;
    acceptanceBudgets.set(snapshot.transactionId, Math.max(0, persistedBudget));
  };

  const cancelTimer = () => { if (timer !== undefined) clearTimer(timer); timer = undefined; };
  const rememberDurableSnapshot = (snapshot: ContinuationTransactionSnapshot) => {
    durableTransactionId = snapshot.transactionId;
    durablePhaseEpoch = snapshot.phaseEpoch ?? 0;
    nextToolLivenessCheckpointAt = continuationLivenessCheckpointOrigin(snapshot) + toolLivenessCheckpointMs;
  };
  const persistSnapshot = (snapshot: ContinuationTransactionSnapshot) => {
    pi.appendEntry(CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE, createContinuationSnapshotWire(snapshot));
    logContinuationTransaction(logEventForState(snapshot.state), snapshot, now());
    rememberDurableSnapshot(snapshot);
  };
  const persistOutcome = (snapshot: ContinuationTransactionSnapshot) => pi.appendEntry(CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE, createContinuationOutcomeWire(snapshot));
  const warnFailure = (snapshot: ContinuationTransactionSnapshot, _previous: ContinuationState, ctx: ExtensionContext) => ctx.ui.notify(`Pi-vcc continuation failed (transaction=${snapshot.transactionId}; attempt=${snapshot.attemptId}; retries=${snapshot.retryCount}/${snapshot.retryLimit}; reason=${snapshot.terminalReason}). Inspect: jq -c 'select(.transactionId=="${snapshot.transactionId}")' ${getPiVccLogPath()}. Manual recovery: return to this Pi session, inspect the interrupted task state, then send “continue” once.`, "warning");
  const warnStalled = (snapshot: ContinuationTransactionSnapshot, ctx: ExtensionContext) => ctx.ui.notify(`Pi-vcc continuation stalled with ${snapshot.pendingToolCount} outstanding tool(s) (transaction=${snapshot.transactionId}). Ownership is retained and queued continuation work is paused. Recovery action: allow the tool to finish or send new input to supersede this continuation.`, "warning");

  const subscribeWakes = () => {
    wakeUnsubscribe?.(); safetyWakeUnsubscribe?.(); const wake = () => { if (lastContext) reconcile(lastContext); };
    wakeUnsubscribe = pi.events.on(CONTINUATION_WAKE_EVENT, wake); safetyWakeUnsubscribe = pi.events.on(CONTINUATION_SAFETY_READY_WAKE_EVENT, wake);
  };
  const unsubscribeWakes = () => { wakeUnsubscribe?.(); safetyWakeUnsubscribe?.(); wakeUnsubscribe = undefined; safetyWakeUnsubscribe = undefined; };

  const finishTerminal = (ctx: ExtensionContext | undefined, previous: ContinuationState) => {
    if (!current || !isContinuationTerminal(current)) return; const done = current; lastTerminal = done; cancelTimer(); persistOutcome(done);
    if (done.state === "failed_loudly" && ctx) warnFailure(done, previous, ctx); current = undefined; if (ctx && !disposed && !sessionShutDown) activateNext(ctx);
  };

  const armCurrentTimer = () => {
    cancelTimer(); if (!current || disposed || sessionShutDown || isContinuationTerminal(current) || current.state === "stalled") return;
    let deadline: number | undefined; let type: "acceptance_deadline" | "progress_deadline" | "tool_stall" | "retry" | undefined;
    if (current.state === "retrying") { deadline = current.nextRetryAt; type = "retry"; }
    else if (current.acceptedAt === undefined && current.state === "submitted") { deadline = current.acceptanceDeadlineAt; type = "acceptance_deadline"; }
    else if (current.pendingToolCount > 0) { deadline = current.toolStallDeadlineAt; type = "tool_stall"; }
    else if (current.acceptedAt !== undefined) { deadline = current.progressDeadlineAt; type = "progress_deadline"; }
    if (deadline === undefined || type === undefined) return;
    const transactionId = current.transactionId; const phaseEpoch = current.phaseEpoch ?? 0;
    let scheduledTimer: ReturnType<typeof setTimeout>;
    scheduledTimer = setTimer(() => {
      if (timer !== scheduledTimer) return;
      timer = undefined;
      if (!current || current.transactionId !== transactionId || (current.phaseEpoch ?? 0) !== phaseEpoch || disposed || sessionShutDown) return;
      const at = Math.max(now(), deadline!);
      if (type === "retry" && lastContext) {
        if (!current || current.transactionId !== transactionId) return;
        if (retryReadyTransactionId !== transactionId && !lastContext.isIdle()) return;
        retryReadyTransactionId = transactionId;
        submit(lastContext);
        return;
      }
      if (type === "acceptance_deadline" && lastContext) {
        reconcileDurableAcceptance(lastContext);
        if (!current || current.transactionId !== transactionId || current.acceptedAt !== undefined) return;
        retryReadyTransactionId = undefined;
        const delay = retryDelays[Math.min(current.retryCount, retryDelays.length - 1)] ?? retryDelays.at(-1) ?? 0;
        apply({ type, at, nextRetryAt: at + delay, epochs }, lastContext); return;
      }
      if (type === "progress_deadline" && lastContext && !lastContext.isIdle()) {
        apply({ type: "progress_deadline_deferred", at, progressDeadlineAt: at + progressMs, epochs }, lastContext);
        return;
      }
      apply({ type, at, epochs } as ContinuationEvent, lastContext);
    }, Math.max(0, deadline - now()));
    timer = scheduledTimer;
  };

  const apply = (event: ContinuationEvent, ctx = lastContext, durability: "immediate" | "tool_liveness_checkpoint" = "immediate") => {
    if (!current || disposed) return; const before = current; const previous = before.state; const result = transitionContinuation(before, event);
    if (result.disposition === "ignored_invalid" || result.disposition === "ignored_stale") return;
    current = result.snapshot;
    if (current.state === "retrying" || isContinuationTerminal(current)) clearToolCorrelation();
    if (current.acceptedAt !== undefined || isContinuationTerminal(current)) {
      retryReadyTransactionId = undefined;
    }
    if (result.disposition === "applied") {
      const onlyLivenessRefresh =
        durability === "tool_liveness_checkpoint" &&
        event.type === "tool_progress" &&
        before.state === "progressed" &&
        current.state === "progressed" &&
        before.pendingToolCount === current.pendingToolCount &&
        current.pendingToolCount > 0 &&
        before.lastAssistantResult === current.lastAssistantResult;
      const checkpointDue = nextToolLivenessCheckpointAt === undefined || event.at >= nextToolLivenessCheckpointAt;
      if (!onlyLivenessRefresh || checkpointDue) persistSnapshot(current);
    }
    if (isContinuationTerminal(current)) { finishTerminal(ctx, previous); return; }
    if (result.decision === "warn_stalled") { if (ctx) warnStalled(current, ctx); cancelTimer(); return; }
    if (result.decision === "submit" && ctx) { submit(ctx); return; }
    armCurrentTimer();
  };

  const reconcileDurableAcceptance = (ctx: ExtensionContext) => {
    // A retrying snapshot still carries the ordinal of the failed submission.
    // Only reconcile after submit() advances submissionCount, otherwise the
    // durable message from that failed ordinal can be consumed a second time
    // during backoff and suppress the retry.
    if (!current || current.acceptedAt !== undefined || current.state !== "submitted") return;
    const reconciled = reconcileContinuationEntries(ctx.sessionManager.getBranch() as any[]);
    const match = reconciled.durableAcceptances.find((entry) => isMatchingContinuationDetails(current!, entry.details));
    if (!match) return;
    const acceptedAt = Math.max(current.submittedAt ?? current.createdAt, toTimestamp(match.timestamp, now()));
    apply({ type: "durable_acceptance", at: acceptedAt, details: match.details, progressDeadlineAt: acceptedAt + progressMs, epochs }, ctx);
  };

  const submit = (ctx: ExtensionContext) => {
    if (!current || isContinuationTerminal(current) || current.pendingToolCount > 0 || disposed || sessionShutDown) return;
    const at = now();
    retryReadyTransactionId = undefined;
    rememberAcceptanceBudget(current);
    const acceptanceBudget = acceptanceBudgets.get(current.transactionId) ?? acceptanceMs;
    const transition = transitionContinuation(current, { type: "submitted", at, acceptanceDeadlineAt: at + acceptanceBudget, epochs });
    if (transition.disposition !== "applied") return; current = transition.snapshot; persistSnapshot(current);
    try { pi.sendMessage({ customType: CONTINUATION_MESSAGE_CUSTOM_TYPE, content: CONTINUATION_PROMPT, display: false, details: continuationMessageDetailsFor(current) }, { triggerTurn: true, deliverAs: "steer" }); }
    catch {
      retryReadyTransactionId = current.transactionId;
      const delay = retryDelays[Math.min(current.retryCount, retryDelays.length - 1)] ?? retryDelays.at(-1) ?? 0;
      apply({ type: "acceptance_deadline", at: current.acceptanceDeadlineAt!, nextRetryAt: at + delay, epochs }, ctx); return;
    }
    reconcileDurableAcceptance(ctx); armCurrentTimer();
  };

  const sameSubmissionIdentity = (left: ContinuationTransactionSnapshot, right: ContinuationTransactionSnapshot) =>
    left.transactionId === right.transactionId &&
    left.attemptId === right.attemptId &&
    left.submissionCount === right.submissionCount &&
    left.compactionId === right.compactionId &&
    left.requestId === right.requestId &&
    left.originatingRequestId === right.originatingRequestId;
  const canFoldV1RetryAcceptance = (snapshot: ContinuationTransactionSnapshot, history: readonly ContinuationTransactionSnapshot[]) => {
    const submissionHistory = history.filter((candidate) => sameSubmissionIdentity(snapshot, candidate));
    const acceptedFailure = submissionHistory.some((candidate) =>
      candidate.lastAssistantResult === "error" || candidate.lastAssistantResult === "aborted");
    if (acceptedFailure) return false;
    const acceptedEvidence = snapshot.acceptedAt !== undefined || submissionHistory.some((candidate) =>
      candidate.acceptedAt !== undefined || candidate.state === "consumed" || candidate.state === "progressed" || candidate.state === "stalled");
    if (acceptedEvidence) return false;
    return submissionHistory.some((candidate) => candidate.state === "submitted" && candidate.acceptedAt === undefined);
  };

  const adaptRehydrated = (
    snapshot: ContinuationTransactionSnapshot,
    ctx: ExtensionContext,
    durable: readonly { details: ContinuationMessageDetails; timestamp?: number }[],
    history: readonly ContinuationTransactionSnapshot[],
  ) => {
    let adapted = withEpochBaseline(snapshot, epochs); const at = now();
    if (adapted.version === 1) {
      adapted = { ...adapted, version: 2, queuedAt: adapted.createdAt, phaseEpoch: adapted.phaseEpoch ?? 0 };
      const match = durable.find((entry) => isMatchingContinuationDetails(adapted, entry.details));
      if (adapted.state === "submitted" && match) {
        const acceptedAt = Math.max(adapted.createdAt, toTimestamp(match.timestamp, at));
        adapted = { ...adapted, state: "consumed", acceptedAt, acceptanceDeadlineAt: undefined, progressDeadlineAt: acceptedAt + progressMs, deadlineAt: acceptedAt + progressMs, phaseEpoch: (adapted.phaseEpoch ?? 0) + 1 };
      } else if (adapted.state === "submitted") adapted = { ...adapted, submittedAt: at, acceptanceDeadlineAt: at + acceptanceMs, deadlineAt: at + acceptanceMs, phaseEpoch: (adapted.phaseEpoch ?? 0) + 1 };
      else if (adapted.state === "consumed" || adapted.state === "progressed") {
        const hasOutstandingTools = adapted.pendingToolCount > 0;
        adapted = {
          ...adapted,
          acceptedAt: adapted.acceptedAt ?? at,
          lastProgressAt: adapted.state === "progressed" ? adapted.lastProgressAt ?? at : adapted.lastProgressAt,
          progressDeadlineAt: hasOutstandingTools ? undefined : at + progressMs,
          toolStallDeadlineAt: hasOutstandingTools ? at + toolStallMs : undefined,
          deadlineAt: hasOutstandingTools ? at + toolStallMs : at + progressMs,
          phaseEpoch: (adapted.phaseEpoch ?? 0) + 1,
        };
      }
      else if (adapted.state === "retrying" && match && canFoldV1RetryAcceptance(adapted, history)) {
        const acceptedAt = Math.max(adapted.createdAt, toTimestamp(match.timestamp, at));
        adapted = { ...adapted, state: "consumed", acceptedAt, acceptanceDeadlineAt: undefined, nextRetryAt: undefined, progressDeadlineAt: acceptedAt + progressMs, deadlineAt: acceptedAt + progressMs, phaseEpoch: (adapted.phaseEpoch ?? 0) + 1 };
      } else if (adapted.state === "retrying") { const delay = retryDelays[Math.min(adapted.retryCount - 1, retryDelays.length - 1)] ?? 0; adapted = { ...adapted, acceptedAt: undefined, nextRetryAt: at + delay, phaseEpoch: (adapted.phaseEpoch ?? 0) + 1 }; }
      persistSnapshot(adapted);
    }
    if (adapted.activatedAt === undefined) { adapted = { ...adapted, activatedAt: at, phaseEpoch: (adapted.phaseEpoch ?? 0) + 1 }; persistSnapshot(adapted); }
    if (
      snapshot.version === 2 &&
      adapted.acceptedAt !== undefined &&
      adapted.pendingToolCount > 0 &&
      adapted.state !== "stalled" &&
      !isContinuationTerminal(adapted)
    ) {
      const toolStallDeadlineAt = at + toolStallMs;
      adapted = { ...adapted, toolStallDeadlineAt, deadlineAt: toolStallDeadlineAt, phaseEpoch: (adapted.phaseEpoch ?? 0) + 1 };
    }
    return adapted;
  };

  const activateNext = (ctx: ExtensionContext) => {
    if (disposed || sessionShutDown) return; const reconciled = reconcileContinuationEntries(ctx.sessionManager.getBranch() as any[]); const pending = reconciled.pending[0];
    if (!pending) {
      current = undefined;
      durableTransactionId = undefined;
      durablePhaseEpoch = -1;
      nextToolLivenessCheckpointAt = undefined;
      cancelTimer();
      return;
    }
    rememberDurableSnapshot(pending);
    if (isContinuationTerminal(pending)) {
      current = withEpochBaseline(pending, epochs);
      epochs = mergeEpochMax(epochs, current.epochs);
      finishTerminal(ctx, pending.state);
      return;
    }
    rememberAcceptanceBudget(pending);
    restoreToolCorrelation(ctx, pending);
    current = adaptRehydrated(pending, ctx, reconciled.durableAcceptances, reconciled.snapshots); epochs = mergeEpochMax(epochs, current.epochs);
    if (current.resumePolicy === "terminal") { apply({ type: "supersede", at: now(), reason: "explicitly_stopped", epochs }, ctx); return; }
    if (current.state === "created" && current.pendingToolCount === 0) { submit(ctx); return; }
    if (current.pendingToolCount > 0 && current.acceptedAt === undefined && current.state !== "waiting_tools") { apply({ type: "tools_pending", at: now(), pendingToolCount: current.pendingToolCount, epochs }, ctx); return; }
    const ready = reconciled.safetyReady.find((candidate) => candidate.transactionId === current!.transactionId && candidate.attemptId === current!.attemptId && candidate.requestId === current!.requestId);
    if (ready && current.acceptedAt === undefined && current.pendingToolCount > 0) { current = { ...current, pendingToolCount: 0 }; apply({ type: "tools_ready", at: now(), epochs }, ctx); return; }
    reconcileDurableAcceptance(ctx); armCurrentTimer();
  };

  const reconcile = (ctx: ExtensionContext) => {
    if (disposed || sessionShutDown) return; lastContext = ctx; const reconciled = reconcileContinuationEntries(ctx.sessionManager.getBranch() as any[]);
    if (reconciled.invalidEntryIds.length) logPiVccEvent("continuation_invalid_entries", { count: reconciled.invalidEntryIds.length });
    const activeTransactionId = current && !isContinuationTerminal(current) ? current.transactionId : undefined;
    const pending = activeTransactionId ? reconciled.pending.find((entry) => entry.transactionId === activeTransactionId) : undefined;
    if (!pending) { activateNext(ctx); return; }
    rememberAcceptanceBudget(pending);

    // Durable acceptance and safety-ready messages are authoritative without a
    // matching snapshot. Fold those narrow events against the exact live state
    // before deciding whether the durable snapshot itself has advanced.
    reconcileDurableAcceptance(ctx);
    if (!current || current.transactionId !== activeTransactionId || isContinuationTerminal(current)) return;
    const ready = reconciled.safetyReady.find((candidate) => candidate.transactionId === current!.transactionId && candidate.attemptId === current!.attemptId && candidate.requestId === current!.requestId);
    if (ready && current.acceptedAt === undefined && current.pendingToolCount > 0) { current = { ...current, pendingToolCount: 0 }; apply({ type: "tools_ready", at: now(), epochs }, ctx); return; }

    const pendingPhaseEpoch = pending.phaseEpoch ?? 0;
    const hasNewerDurableSnapshot = durableTransactionId !== pending.transactionId || pendingPhaseEpoch > durablePhaseEpoch;
    if (!hasNewerDurableSnapshot) return;

    rememberDurableSnapshot(pending);
    restoreToolCorrelation(ctx, pending);
    current = adaptRehydrated(withEpochBaseline(pending, epochs), ctx, reconciled.durableAcceptances, reconciled.snapshots);
    epochs = mergeEpochMax(epochs, current.epochs);
    if (isContinuationTerminal(current)) { finishTerminal(ctx, current.state); return; }
    reconcileDurableAcceptance(ctx);
    armCurrentTimer();
  };

  const reconcileBeforeLifecycle = (ctx: ExtensionContext) => {
    if (!current || current.acceptedAt !== undefined || isContinuationTerminal(current)) return;
    reconcileDurableAcceptance(ctx);
  };

  const markRetryReady = (ctx: ExtensionContext) => {
    if (!current || current.state !== "retrying" || retryReadyTransactionId === current.transactionId) return;
    retryReadyTransactionId = current.transactionId;
    const delay = retryDelays[Math.max(0, Math.min(current.retryCount - 1, retryDelays.length - 1))] ?? retryDelays.at(-1) ?? 0;
    apply({ type: "retry_ready", at: now(), nextRetryAt: now() + delay, epochs }, ctx);
  };

  const request = (input: ContinuationRequestInput, ctx: ExtensionContext) => {
    lastContext = ctx; const at = now(); const adapted = adaptContinuationInitiatorOutcome(input.initiator, input.outcome);
    const budget = input.deadlineMs ?? acceptanceMs;
    const snapshot = createContinuationTransaction({ transactionId: transactionIdFor(input, at), origin: adapted.origin, reason: adapted.reason, ...(input.compactionId ? { compactionId: input.compactionId } : {}), attemptId: input.attemptId, ...(input.requestId ? { requestId: input.requestId } : {}), ...(input.originatingRequestId ? { originatingRequestId: input.originatingRequestId } : {}), resumePolicy: input.resumePolicy, createdAt: at, deadlineMs: budget, pendingToolCount: input.pendingToolCount ?? 0, retryLimit: input.retryLimit ?? DEFAULT_RETRY_LIMIT, epochs });
    acceptanceBudgets.set(snapshot.transactionId, budget);
    pi.appendEntry(CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE, createContinuationRequestWire(snapshot, input.outcome)); logContinuationTransaction("created", snapshot, at);
    if (!current || isContinuationTerminal(current)) activateNext(ctx);
    return current?.transactionId === snapshot.transactionId ? current : snapshot;
  };

  subscribeWakes();
  pi.on("session_start", (_event, ctx) => { if (disposed) return; sessionShutDown = false; epochs.session += 1; lastContext = ctx; subscribeWakes(); reconcile(ctx); markRetryReady(ctx); });
  pi.on("agent_start", () => { epochs.agent += 1; }); pi.on("turn_start", () => { epochs.turn += 1; });
  pi.on("input", (event, ctx) => { lastContext = ctx; if (!current || isContinuationTerminal(current) || event.source === "extension") return; epochs.input += 1; apply({ type: "supersede", at: now(), reason: "real_user_input", epochs }, ctx); });
  pi.on("message_start", (event, ctx) => {
    epochs.message += 1; lastContext = ctx; if (!current || isContinuationTerminal(current)) return; const message = event.message as any;
    reconcileBeforeLifecycle(ctx);
    if (!current || isContinuationTerminal(current)) return;
    if (isRealUserMessage(message)) { apply({ type: "supersede", at: now(), reason: "real_user_input", epochs }, ctx); return; }
    if (message?.role === "custom") {
      const intent = classifyCustomMessageIntent(message, current);
      if (intent === "status") return;
      if (intent === "independent") { epochs.input += 1; apply({ type: "supersede", at: now(), reason: "independent_input", epochs }, ctx); return; }
    }
    apply({ type: "message_start", at: now(), message, progressDeadlineAt: now() + progressMs, epochs }, ctx);
  });
  pi.on("message_end", (event, ctx) => {
    lastContext = ctx;
    if (!current || isContinuationTerminal(current)) return;
    reconcileBeforeLifecycle(ctx);
    if (!current || isContinuationTerminal(current)) return;
    const message = (event as any).message;
    const result = assistantResult(message);
    if (!result) return;
    if (
      current.acceptedAt === undefined &&
      current.state === "waiting_tools" &&
      result === "progress" &&
      message?.stopReason === "stop"
    ) {
      current = { ...current, pendingToolCount: 0 };
      apply({ type: "tools_ready", at: now(), epochs }, ctx);
      return;
    }
    if (current.acceptedAt === undefined) return;
    const calls = result === "progress" ? toolCallCount(message) : 0;
    if (calls > 0) {
      for (const id of toolCallIds(message)) {
        ambiguousToolCallIds.delete(id);
        activeToolCallIds.add(id);
      }
    }
    const pending = calls > 0 ? current.pendingToolCount + calls : current.pendingToolCount;
    apply({
      type: "assistant_result",
      at: now(),
      result,
      pendingToolCount: pending,
      progressDeadlineAt: now() + progressMs,
      toolStallDeadlineAt: now() + toolStallMs,
      epochs,
    }, ctx);
  });
  pi.on("tool_execution_start", (event, ctx) => {
    lastContext = ctx;
    if (!current || isContinuationTerminal(current)) return;
    reconcileBeforeLifecycle(ctx);
    if (!current || current.acceptedAt === undefined || isContinuationTerminal(current)) return;
    const id = (event as any).toolCallId;
    if (typeof id !== "string" || (!activeToolCallIds.has(id) && !confirmAmbiguousTool(id))) return;
    const pending = Math.max(1, current.pendingToolCount);
    apply({ type: "tool_progress", at: now(), pendingToolCount: pending, toolStallDeadlineAt: now() + toolStallMs, epochs }, ctx);
  });
  pi.on("tool_execution_update", (event, ctx) => {
    lastContext = ctx;
    if (!current || isContinuationTerminal(current)) return;
    reconcileBeforeLifecycle(ctx);
    if (!current || current.acceptedAt === undefined || isContinuationTerminal(current)) return;
    const id = (event as any).toolCallId;
    if (typeof id !== "string" || (!activeToolCallIds.has(id) && !confirmAmbiguousTool(id))) return;
    const at = now();
    apply({ type: "tool_progress", at, pendingToolCount: Math.max(1, current.pendingToolCount), toolStallDeadlineAt: at + toolStallMs, epochs }, ctx, "tool_liveness_checkpoint");
  });
  pi.on("tool_execution_end", (event, ctx) => {
    lastContext = ctx;
    if (!current || isContinuationTerminal(current)) return;
    reconcileBeforeLifecycle(ctx);
    if (!current || current.acceptedAt === undefined || isContinuationTerminal(current)) return;
    const id = (event as any).toolCallId;
    if (typeof id !== "string") return;
    const wasConfirmed = activeToolCallIds.delete(id);
    const wasAmbiguous = ambiguousToolCallIds.delete(id);
    if (!wasConfirmed && !wasAmbiguous) return;
    const pending = Math.max(0, current.pendingToolCount - 1);
    if (pending === 0) clearToolCorrelation();
    else if (activeToolCallIds.size >= pending) ambiguousToolCallIds.clear();
    apply({ type: "tool_progress", at: now(), pendingToolCount: pending, progressDeadlineAt: now() + progressMs, toolStallDeadlineAt: now() + toolStallMs, epochs }, ctx);
  });
  pi.on("agent_end", (event, ctx) => {
    lastContext = ctx;
    if (!current || isContinuationTerminal(current)) return;
    reconcileBeforeLifecycle(ctx);
    if (!current || current.acceptedAt === undefined || isContinuationTerminal(current)) return;
    const messages = (event as any).messages;
    const result = assistantResult(Array.isArray(messages) ? messages.at(-1) : undefined);
    if (result && current.lastAssistantResult !== result) apply({ type: "assistant_result", at: now(), result, pendingToolCount: current.pendingToolCount, progressDeadlineAt: now() + progressMs, toolStallDeadlineAt: now() + toolStallMs, epochs }, ctx);
  });
  pi.on("agent_settled", (_event, ctx) => {
    epochs.settlement += 1;
    lastContext = ctx;
    if (!current) return;
    const transactionId = current.transactionId;
    reconcileDurableAcceptance(ctx);
    if (!current || current.transactionId !== transactionId) return;
    if (current.state === "retrying") {
      markRetryReady(ctx);
      return;
    }
    retryReadyTransactionId = transactionId;
    const delay = retryDelays[Math.min(current.retryCount, retryDelays.length - 1)] ?? retryDelays.at(-1) ?? 0;
    apply({ type: "agent_settled", at: now(), nextRetryAt: now() + delay, epochs }, ctx);
  });
  pi.on("session_shutdown", (event, ctx) => {
    cancelTimer(); unsubscribeWakes(); clearToolCorrelation(); lastContext = ctx; sessionShutDown = true;
    const replacementReason = event.reason === "reload" || event.reason === "new" || event.reason === "resume" || event.reason === "fork"
      ? event.reason
      : undefined;
    if (!replacementReason) return;
    let terminalizationError: unknown;
    let terminalizingTransactionId: string | undefined;
    try {
      if (replacementReason !== "reload") {
        const reconciled = reconcileContinuationEntries(ctx.sessionManager.getBranch() as any[]);
        for (const pending of reconciled.pending) {
          const baseline = withEpochBaseline(pending, { ...epochs, session: epochs.session + 1 });
          const done = transitionContinuation(baseline, { type: "supersede", at: Math.max(now(), baseline.createdAt), reason: "session_replaced", epochs: baseline.epochs }).snapshot;
          if (!isContinuationTerminal(done)) continue;
          terminalizingTransactionId = done.transactionId;
          persistSnapshot(done);
          persistOutcome(done);
          if (current?.transactionId === done.transactionId) current = undefined;
          terminalizingTransactionId = undefined;
        }
      }
    } catch (error) {
      terminalizationError = error;
      logPiVccError("continuation_session_replacement_terminalization_failed", error, {
        reason: replacementReason,
        transactionId: terminalizingTransactionId ?? current?.transactionId,
        logPath: getPiVccLogPath(),
      });
      try {
        ctx.ui.notify(`Pi-vcc could not durably terminalize the replaced session (reason=${replacementReason}; transaction=${terminalizingTransactionId ?? current?.transactionId ?? "unknown"}). The old runtime was released so the replacement can start. Inspect ${getPiVccLogPath()} and the old session before manual recovery.`, "warning");
      } catch {
        // Host replacement must still release ownership if UI reporting fails.
      }
    } finally {
      disposed = true;
      options.onSessionReplacement?.(replacementReason);
    }
    if (terminalizationError !== undefined) throw terminalizationError;
  });

  return {
    authority,
    request,
    reconcile,
    getPending: () => current ?? lastTerminal,
    getNextToolLivenessCheckpointAt: () => nextToolLivenessCheckpointAt,
    dispose: () => { if (disposed) return; disposed = true; cancelTimer(); unsubscribeWakes(); },
  };
};
