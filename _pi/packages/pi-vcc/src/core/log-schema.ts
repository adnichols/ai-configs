import type {
  ContinuationOrigin,
  ContinuationReason,
  ContinuationResumePolicy,
  ContinuationState,
  ContinuationTerminalReason,
  ContinuationTerminalState,
  ContinuationTransactionSnapshot,
} from "./continuation-protocol";

export const CONTINUATION_LOG_EVENTS = [
  "created",
  "waiting_tools",
  "submitted",
  "consumed",
  "progressed",
  "stalled",
  "settled",
  "superseded",
  "retrying",
  "failed",
] as const;
export type ContinuationLogEvent = typeof CONTINUATION_LOG_EVENTS[number];

export const CONTINUATION_LOG_KEYS = [
  "timestampEpoch",
  "event",
  "transactionId",
  "compactionId",
  "attemptId",
  "requestId",
  "originatingRequestId",
  "origin",
  "reason",
  "resumePolicy",
  "state",
  "outcome",
  "terminalReason",
  "retryCount",
  "retryLimit",
  "submissionCount",
  "elapsedMs",
  "deadlineAt",
  "pendingToolCount",
  "sessionEpoch",
  "inputEpoch",
  "agentEpoch",
  "turnEpoch",
  "messageEpoch",
  "settlementEpoch",
  "phaseEpoch",
  "queuedAt",
  "activatedAt",
  "submittedAt",
  "acceptanceDeadlineAt",
  "acceptedAt",
  "lastProgressAt",
  "progressDeadlineAt",
  "toolStallDeadlineAt",
  "nextRetryAt",
] as const;
export type ContinuationLogKey = typeof CONTINUATION_LOG_KEYS[number];

export interface ContinuationLogRecord {
  timestampEpoch: number;
  event: ContinuationLogEvent;
  transactionId: string;
  compactionId?: string;
  attemptId: string;
  requestId?: string;
  originatingRequestId?: string;
  origin: ContinuationOrigin;
  reason: ContinuationReason;
  resumePolicy: ContinuationResumePolicy;
  state: ContinuationState;
  outcome?: ContinuationTerminalState;
  terminalReason?: ContinuationTerminalReason;
  retryCount: number;
  retryLimit: number;
  submissionCount: number;
  elapsedMs: number;
  deadlineAt: number;
  pendingToolCount: number;
  sessionEpoch: number;
  inputEpoch: number;
  agentEpoch: number;
  turnEpoch: number;
  messageEpoch: number;
  settlementEpoch: number;
  phaseEpoch: number;
  queuedAt?: number;
  activatedAt?: number;
  submittedAt?: number;
  acceptanceDeadlineAt?: number;
  acceptedAt?: number;
  lastProgressAt?: number;
  progressDeadlineAt?: number;
  toolStallDeadlineAt?: number;
  nextRetryAt?: number;
}

export const continuationLogRecordFor = (
  event: ContinuationLogEvent,
  snapshot: ContinuationTransactionSnapshot,
  now: number,
): ContinuationLogRecord => ({
  timestampEpoch: now,
  event,
  transactionId: snapshot.transactionId,
  ...(snapshot.compactionId ? { compactionId: snapshot.compactionId } : {}),
  attemptId: snapshot.attemptId,
  ...(snapshot.requestId ? { requestId: snapshot.requestId } : {}),
  ...(snapshot.originatingRequestId ? { originatingRequestId: snapshot.originatingRequestId } : {}),
  origin: snapshot.origin,
  reason: snapshot.reason,
  resumePolicy: snapshot.resumePolicy,
  state: snapshot.state,
  ...(["settled", "superseded", "failed_loudly"].includes(snapshot.state)
    ? { outcome: snapshot.state as ContinuationTerminalState }
    : {}),
  ...(snapshot.terminalReason ? { terminalReason: snapshot.terminalReason } : {}),
  retryCount: snapshot.retryCount,
  retryLimit: snapshot.retryLimit,
  submissionCount: snapshot.submissionCount,
  elapsedMs: Math.max(0, now - snapshot.createdAt),
  deadlineAt: snapshot.deadlineAt,
  pendingToolCount: snapshot.pendingToolCount,
  sessionEpoch: snapshot.epochs.session,
  inputEpoch: snapshot.epochs.input,
  agentEpoch: snapshot.epochs.agent,
  turnEpoch: snapshot.epochs.turn,
  messageEpoch: snapshot.epochs.message,
  settlementEpoch: snapshot.epochs.settlement,
  phaseEpoch: snapshot.phaseEpoch ?? 0,
  ...(snapshot.queuedAt === undefined ? {} : { queuedAt: snapshot.queuedAt }),
  ...(snapshot.activatedAt === undefined ? {} : { activatedAt: snapshot.activatedAt }),
  ...(snapshot.submittedAt === undefined ? {} : { submittedAt: snapshot.submittedAt }),
  ...(snapshot.acceptanceDeadlineAt === undefined ? {} : { acceptanceDeadlineAt: snapshot.acceptanceDeadlineAt }),
  ...(snapshot.acceptedAt === undefined ? {} : { acceptedAt: snapshot.acceptedAt }),
  ...(snapshot.lastProgressAt === undefined ? {} : { lastProgressAt: snapshot.lastProgressAt }),
  ...(snapshot.progressDeadlineAt === undefined ? {} : { progressDeadlineAt: snapshot.progressDeadlineAt }),
  ...(snapshot.toolStallDeadlineAt === undefined ? {} : { toolStallDeadlineAt: snapshot.toolStallDeadlineAt }),
  ...(snapshot.nextRetryAt === undefined ? {} : { nextRetryAt: snapshot.nextRetryAt }),
});

export const isStrictContinuationLogRecord = (value: unknown): value is ContinuationLogRecord => {
  if (!value || typeof value !== "object" || Array.isArray(value)) return false;
  const record = value as Record<string, unknown>;
  const allowed = new Set<string>(CONTINUATION_LOG_KEYS);
  if (Object.keys(record).some((key) => !allowed.has(key))) return false;
  return typeof record.timestampEpoch === "number"
    && CONTINUATION_LOG_EVENTS.includes(record.event as ContinuationLogEvent)
    && typeof record.transactionId === "string"
    && typeof record.attemptId === "string"
    && typeof record.origin === "string"
    && typeof record.reason === "string"
    && typeof record.resumePolicy === "string"
    && typeof record.state === "string"
    && typeof record.retryCount === "number"
    && typeof record.retryLimit === "number"
    && typeof record.submissionCount === "number"
    && typeof record.elapsedMs === "number"
    && typeof record.deadlineAt === "number"
    && typeof record.pendingToolCount === "number"
    && typeof record.sessionEpoch === "number"
    && typeof record.inputEpoch === "number"
    && typeof record.agentEpoch === "number"
    && typeof record.turnEpoch === "number"
    && typeof record.messageEpoch === "number"
    && typeof record.settlementEpoch === "number"
    && typeof record.phaseEpoch === "number";
};
