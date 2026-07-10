export const CONTINUATION_PROTOCOL_NAME = "pi-vcc-continuation" as const;
export const CONTINUATION_PROTOCOL_VERSION = 1 as const;
export const CONTINUATION_MESSAGE_CUSTOM_TYPE = "pi-vcc-continuation" as const;
export const CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE = "pi-vcc-continuation-request" as const;
export const CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE = "pi-vcc-continuation-snapshot" as const;
export const CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE = "pi-vcc-continuation-outcome" as const;

export const CONTINUATION_ORIGINS = [
  "package-command",
  "compact_context",
  "hard-backstop",
  "host-threshold",
  "host-overflow",
] as const;
export type ContinuationOrigin = typeof CONTINUATION_ORIGINS[number];

export const CONTINUATION_REASONS = [
  "compacted",
  "no-safe-cut",
  "cancelled",
  "failed",
] as const;
export type ContinuationReason = typeof CONTINUATION_REASONS[number];

export const CONTINUATION_RESUME_POLICIES = ["active", "terminal", "auto"] as const;
export type ContinuationResumePolicy = typeof CONTINUATION_RESUME_POLICIES[number];

export const CONTINUATION_INITIATORS = [
  "package-pi-vcc",
  "package-compact-now",
  "compact_context",
  "hard-backstop",
  "host-threshold",
  "host-overflow",
] as const;
export type ContinuationInitiator = typeof CONTINUATION_INITIATORS[number];

export const CONTINUATION_ATTEMPT_OUTCOMES = ["compacted", "no-safe-cut", "cancellation", "failure"] as const;
export type ContinuationAttemptOutcome = typeof CONTINUATION_ATTEMPT_OUTCOMES[number];

export interface ContinuationInitiatorOutcome {
  initiator: ContinuationInitiator;
  outcome: ContinuationAttemptOutcome;
  origin: ContinuationOrigin;
  reason: ContinuationReason;
}

export const adaptContinuationInitiatorOutcome = (
  initiator: ContinuationInitiator,
  outcome: ContinuationAttemptOutcome,
): ContinuationInitiatorOutcome => {
  const origin: ContinuationOrigin = initiator === "package-pi-vcc" || initiator === "package-compact-now"
    ? "package-command"
    : initiator;
  const reason: ContinuationReason = outcome === "cancellation" ? "cancelled"
    : outcome === "failure" ? "failed"
      : outcome;
  return { initiator, outcome, origin, reason };
};

export const CONTINUATION_STATES = [
  "created",
  "waiting_tools",
  "submitted",
  "consumed",
  "progressed",
  "retrying",
  "settled",
  "superseded",
  "failed_loudly",
] as const;
export type ContinuationState = typeof CONTINUATION_STATES[number];

export const CONTINUATION_TERMINAL_STATES = ["settled", "superseded", "failed_loudly"] as const;
export type ContinuationTerminalState = typeof CONTINUATION_TERMINAL_STATES[number];

export const CONTINUATION_TERMINAL_REASONS = [
  "progressed_then_agent_settled",
  "real_user_input",
  "independent_input",
  "session_replaced",
  "explicitly_stopped",
  "deadline_expired",
  "retry_limit_exhausted",
  "host_unavailable",
  "invalid_persistence",
  "reload_rehydrate_failed",
  "unrecoverable_error",
] as const;
export type ContinuationTerminalReason = typeof CONTINUATION_TERMINAL_REASONS[number];
export type ContinuationSupersedeReason = Extract<
  ContinuationTerminalReason,
  "real_user_input" | "independent_input" | "session_replaced" | "explicitly_stopped"
>;
export type ContinuationFailureReason = Exclude<
  ContinuationTerminalReason,
  "progressed_then_agent_settled" | ContinuationSupersedeReason
>;

export interface ContinuationLifecycleEpochs {
  session: number;
  input: number;
  agent: number;
  turn: number;
  message: number;
  settlement: number;
}

export interface ContinuationMessageDetails {
  protocol: typeof CONTINUATION_PROTOCOL_NAME;
  version: typeof CONTINUATION_PROTOCOL_VERSION;
  transactionId: string;
  attemptId: string;
  compactionId?: string;
  requestId?: string;
  originatingRequestId?: string;
}

export type ContinuationAssistantResult = "progress" | "error" | "aborted";

export interface ContinuationTransactionSnapshot {
  protocol: typeof CONTINUATION_PROTOCOL_NAME;
  version: typeof CONTINUATION_PROTOCOL_VERSION;
  transactionId: string;
  origin: ContinuationOrigin;
  reason: ContinuationReason;
  compactionId?: string;
  attemptId: string;
  requestId?: string;
  originatingRequestId?: string;
  resumePolicy: ContinuationResumePolicy;
  state: ContinuationState;
  createdAt: number;
  deadlineAt: number;
  pendingToolCount: number;
  submissionCount: number;
  retryCount: number;
  retryLimit: number;
  epochs: ContinuationLifecycleEpochs;
  consumedEpochs?: ContinuationLifecycleEpochs;
  lastAssistantResult?: ContinuationAssistantResult;
  terminalReason?: ContinuationTerminalReason;
}

export interface ContinuationRequestWire {
  protocol: typeof CONTINUATION_PROTOCOL_NAME;
  version: typeof CONTINUATION_PROTOCOL_VERSION;
  kind: "request";
  snapshot: ContinuationTransactionSnapshot;
}

export interface ContinuationSnapshotWire {
  protocol: typeof CONTINUATION_PROTOCOL_NAME;
  version: typeof CONTINUATION_PROTOCOL_VERSION;
  kind: "snapshot";
  snapshot: ContinuationTransactionSnapshot;
}

export interface ContinuationOutcomeWire {
  protocol: typeof CONTINUATION_PROTOCOL_NAME;
  version: typeof CONTINUATION_PROTOCOL_VERSION;
  kind: "outcome";
  transactionId: string;
  terminalState: ContinuationTerminalState;
  terminalReason: ContinuationTerminalReason;
  snapshot: ContinuationTransactionSnapshot;
}

export type ContinuationWire = ContinuationRequestWire | ContinuationSnapshotWire | ContinuationOutcomeWire;

export interface ContinuationCustomEntryLike {
  id?: string;
  type: string;
  customType?: string;
  data?: unknown;
}

export interface ReconciledContinuationEntries {
  pending: ContinuationTransactionSnapshot[];
  terminal: ContinuationOutcomeWire[];
  invalidEntryIds: string[];
  duplicateRequestTransactionIds: string[];
  orphanSnapshotTransactionIds: string[];
  orphanOutcomeTransactionIds: string[];
}

const hasExactKeys = (value: Record<string, unknown>, required: readonly string[], optional: readonly string[] = []): boolean => {
  const allowed = new Set([...required, ...optional]);
  return required.every((key) => Object.prototype.hasOwnProperty.call(value, key))
    && Object.keys(value).every((key) => allowed.has(key));
};

const isRecord = (value: unknown): value is Record<string, unknown> =>
  typeof value === "object" && value !== null && !Array.isArray(value);

const isFiniteNonNegativeInteger = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value) && Number.isInteger(value) && value >= 0;

const isFiniteTimestamp = (value: unknown): value is number =>
  typeof value === "number" && Number.isFinite(value) && value >= 0;

const isNonEmptyString = (value: unknown): value is string =>
  typeof value === "string" && value.length > 0;

const isOneOf = <T extends readonly string[]>(values: T, value: unknown): value is T[number] =>
  typeof value === "string" && (values as readonly string[]).includes(value);

export const isContinuationLifecycleEpochs = (value: unknown): value is ContinuationLifecycleEpochs => {
  if (!isRecord(value) || !hasExactKeys(value, ["session", "input", "agent", "turn", "message", "settlement"])) {
    return false;
  }
  return isFiniteNonNegativeInteger(value.session)
    && isFiniteNonNegativeInteger(value.input)
    && isFiniteNonNegativeInteger(value.agent)
    && isFiniteNonNegativeInteger(value.turn)
    && isFiniteNonNegativeInteger(value.message)
    && isFiniteNonNegativeInteger(value.settlement);
};

export const isContinuationMessageDetails = (value: unknown): value is ContinuationMessageDetails => {
  if (!isRecord(value) || !hasExactKeys(
    value,
    ["protocol", "version", "transactionId", "attemptId"],
    ["compactionId", "requestId", "originatingRequestId"],
  )) return false;

  return value.protocol === CONTINUATION_PROTOCOL_NAME
    && value.version === CONTINUATION_PROTOCOL_VERSION
    && isNonEmptyString(value.transactionId)
    && isNonEmptyString(value.attemptId)
    && (value.compactionId === undefined || isNonEmptyString(value.compactionId))
    && (value.requestId === undefined || isNonEmptyString(value.requestId))
    && (value.originatingRequestId === undefined || isNonEmptyString(value.originatingRequestId));
};

export const continuationMessageDetailsFor = (
  snapshot: ContinuationTransactionSnapshot,
): ContinuationMessageDetails => ({
  protocol: CONTINUATION_PROTOCOL_NAME,
  version: CONTINUATION_PROTOCOL_VERSION,
  transactionId: snapshot.transactionId,
  attemptId: snapshot.attemptId,
  ...(snapshot.compactionId ? { compactionId: snapshot.compactionId } : {}),
  ...(snapshot.requestId ? { requestId: snapshot.requestId } : {}),
  ...(snapshot.originatingRequestId ? { originatingRequestId: snapshot.originatingRequestId } : {}),
});

export const isMatchingContinuationDetails = (
  snapshot: ContinuationTransactionSnapshot,
  value: unknown,
): value is ContinuationMessageDetails => {
  if (!isContinuationMessageDetails(value)) return false;
  return value.transactionId === snapshot.transactionId
    && value.attemptId === snapshot.attemptId
    && value.compactionId === snapshot.compactionId
    && value.requestId === snapshot.requestId
    && value.originatingRequestId === snapshot.originatingRequestId;
};

export const isContinuationTransactionSnapshot = (value: unknown): value is ContinuationTransactionSnapshot => {
  if (!isRecord(value) || !hasExactKeys(
    value,
    [
      "protocol", "version", "transactionId", "origin", "reason", "attemptId", "resumePolicy", "state",
      "createdAt", "deadlineAt", "pendingToolCount", "submissionCount", "retryCount", "retryLimit", "epochs",
    ],
    [
      "compactionId", "requestId", "originatingRequestId", "consumedEpochs", "lastAssistantResult",
      "terminalReason",
    ],
  )) return false;

  if (value.protocol !== CONTINUATION_PROTOCOL_NAME
    || value.version !== CONTINUATION_PROTOCOL_VERSION
    || !isNonEmptyString(value.transactionId)
    || !isOneOf(CONTINUATION_ORIGINS, value.origin)
    || !isOneOf(CONTINUATION_REASONS, value.reason)
    || !isNonEmptyString(value.attemptId)
    || !isOneOf(CONTINUATION_RESUME_POLICIES, value.resumePolicy)
    || !isOneOf(CONTINUATION_STATES, value.state)
    || !isFiniteTimestamp(value.createdAt)
    || !isFiniteTimestamp(value.deadlineAt)
    || value.deadlineAt < value.createdAt
    || !isFiniteNonNegativeInteger(value.pendingToolCount)
    || !isFiniteNonNegativeInteger(value.submissionCount)
    || !isFiniteNonNegativeInteger(value.retryCount)
    || !isFiniteNonNegativeInteger(value.retryLimit)
    || !isContinuationLifecycleEpochs(value.epochs)) return false;

  return (value.compactionId === undefined || isNonEmptyString(value.compactionId))
    && (value.requestId === undefined || isNonEmptyString(value.requestId))
    && (value.originatingRequestId === undefined || isNonEmptyString(value.originatingRequestId))
    && (value.consumedEpochs === undefined || isContinuationLifecycleEpochs(value.consumedEpochs))
    && (value.lastAssistantResult === undefined || isOneOf(["progress", "error", "aborted"] as const, value.lastAssistantResult))
    && (value.terminalReason === undefined || isOneOf(CONTINUATION_TERMINAL_REASONS, value.terminalReason))
    && (!isOneOf(CONTINUATION_TERMINAL_STATES, value.state) || isOneOf(CONTINUATION_TERMINAL_REASONS, value.terminalReason))
    && (isOneOf(CONTINUATION_TERMINAL_STATES, value.state) || value.terminalReason === undefined);
};

export const isContinuationRequestWire = (value: unknown): value is ContinuationRequestWire =>
  isRecord(value)
  && hasExactKeys(value, ["protocol", "version", "kind", "snapshot"])
  && value.protocol === CONTINUATION_PROTOCOL_NAME
  && value.version === CONTINUATION_PROTOCOL_VERSION
  && value.kind === "request"
  && isContinuationTransactionSnapshot(value.snapshot)
  && value.snapshot.state === "created";

export const isContinuationSnapshotWire = (value: unknown): value is ContinuationSnapshotWire =>
  isRecord(value)
  && hasExactKeys(value, ["protocol", "version", "kind", "snapshot"])
  && value.protocol === CONTINUATION_PROTOCOL_NAME
  && value.version === CONTINUATION_PROTOCOL_VERSION
  && value.kind === "snapshot"
  && isContinuationTransactionSnapshot(value.snapshot);

export const isContinuationOutcomeWire = (value: unknown): value is ContinuationOutcomeWire =>
  isRecord(value)
  && hasExactKeys(value, ["protocol", "version", "kind", "transactionId", "terminalState", "terminalReason", "snapshot"])
  && value.protocol === CONTINUATION_PROTOCOL_NAME
  && value.version === CONTINUATION_PROTOCOL_VERSION
  && value.kind === "outcome"
  && isNonEmptyString(value.transactionId)
  && isOneOf(CONTINUATION_TERMINAL_STATES, value.terminalState)
  && isOneOf(CONTINUATION_TERMINAL_REASONS, value.terminalReason)
  && isContinuationTransactionSnapshot(value.snapshot)
  && value.snapshot.transactionId === value.transactionId
  && value.snapshot.state === value.terminalState
  && value.snapshot.terminalReason === value.terminalReason;

export const isContinuationWire = (value: unknown): value is ContinuationWire =>
  isContinuationRequestWire(value) || isContinuationSnapshotWire(value) || isContinuationOutcomeWire(value);

const parseJson = (value: unknown): unknown => {
  if (typeof value !== "string") return value;
  try {
    return JSON.parse(value);
  } catch {
    return undefined;
  }
};

export const parseContinuationRequest = (value: unknown): ContinuationRequestWire | undefined => {
  const parsed = parseJson(value);
  return isContinuationRequestWire(parsed) ? parsed : undefined;
};

export const parseContinuationSnapshot = (value: unknown): ContinuationSnapshotWire | undefined => {
  const parsed = parseJson(value);
  return isContinuationSnapshotWire(parsed) ? parsed : undefined;
};

export const parseContinuationOutcome = (value: unknown): ContinuationOutcomeWire | undefined => {
  const parsed = parseJson(value);
  return isContinuationOutcomeWire(parsed) ? parsed : undefined;
};

export const serializeContinuationWire = (wire: ContinuationWire): string => {
  if (!isContinuationWire(wire)) throw new TypeError("Invalid pi-vcc continuation wire payload");
  return JSON.stringify(wire);
};

export const createContinuationRequestWire = (
  snapshot: ContinuationTransactionSnapshot,
): ContinuationRequestWire => {
  const wire: ContinuationRequestWire = {
    protocol: CONTINUATION_PROTOCOL_NAME,
    version: CONTINUATION_PROTOCOL_VERSION,
    kind: "request",
    snapshot,
  };
  if (!isContinuationRequestWire(wire)) throw new TypeError("Continuation request requires a valid created snapshot");
  return wire;
};

export const createContinuationSnapshotWire = (
  snapshot: ContinuationTransactionSnapshot,
): ContinuationSnapshotWire => {
  const wire: ContinuationSnapshotWire = {
    protocol: CONTINUATION_PROTOCOL_NAME,
    version: CONTINUATION_PROTOCOL_VERSION,
    kind: "snapshot",
    snapshot,
  };
  if (!isContinuationSnapshotWire(wire)) throw new TypeError("Continuation snapshot is invalid");
  return wire;
};

export const createContinuationOutcomeWire = (
  snapshot: ContinuationTransactionSnapshot,
): ContinuationOutcomeWire => {
  if (!isOneOf(CONTINUATION_TERMINAL_STATES, snapshot.state) || !snapshot.terminalReason) {
    throw new TypeError("Continuation outcome requires a terminal snapshot");
  }
  const wire: ContinuationOutcomeWire = {
    protocol: CONTINUATION_PROTOCOL_NAME,
    version: CONTINUATION_PROTOCOL_VERSION,
    kind: "outcome",
    transactionId: snapshot.transactionId,
    terminalState: snapshot.state,
    terminalReason: snapshot.terminalReason,
    snapshot,
  };
  if (!isContinuationOutcomeWire(wire)) throw new TypeError("Continuation outcome is invalid");
  return wire;
};

export const reconcileContinuationEntries = (
  entries: readonly ContinuationCustomEntryLike[],
): ReconciledContinuationEntries => {
  const requests = new Map<string, ContinuationTransactionSnapshot>();
  const requestOrder: string[] = [];
  const latestSnapshots = new Map<string, ContinuationTransactionSnapshot>();
  const outcomes = new Map<string, ContinuationOutcomeWire>();
  const invalidEntryIds: string[] = [];
  const duplicateRequestTransactionIds = new Set<string>();
  const seenSnapshots = new Set<string>();
  const seenOutcomes = new Set<string>();

  entries.forEach((entry, index) => {
    if (entry.type !== "custom") return;
    const entryId = entry.id ?? `index:${index}`;
    if (entry.customType === CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE) {
      const request = parseContinuationRequest(entry.data);
      if (!request) {
        invalidEntryIds.push(entryId);
        return;
      }
      const id = request.snapshot.transactionId;
      if (requests.has(id)) duplicateRequestTransactionIds.add(id);
      else {
        requests.set(id, request.snapshot);
        requestOrder.push(id);
      }
      return;
    }
    if (entry.customType === CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE) {
      const snapshot = parseContinuationSnapshot(entry.data);
      if (!snapshot) {
        invalidEntryIds.push(entryId);
        return;
      }
      latestSnapshots.set(snapshot.snapshot.transactionId, snapshot.snapshot);
      seenSnapshots.add(snapshot.snapshot.transactionId);
      return;
    }
    if (entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE) {
      const outcome = parseContinuationOutcome(entry.data);
      if (!outcome) {
        invalidEntryIds.push(entryId);
        return;
      }
      if (!outcomes.has(outcome.transactionId)) outcomes.set(outcome.transactionId, outcome);
      seenOutcomes.add(outcome.transactionId);
    }
  });

  const pending = requestOrder
    .filter((transactionId) => !outcomes.has(transactionId))
    .map((transactionId) => latestSnapshots.get(transactionId) ?? requests.get(transactionId)!);

  return {
    pending,
    terminal: requestOrder.flatMap((transactionId) => {
      const outcome = outcomes.get(transactionId);
      return outcome ? [outcome] : [];
    }),
    invalidEntryIds,
    duplicateRequestTransactionIds: [...duplicateRequestTransactionIds],
    orphanSnapshotTransactionIds: [...seenSnapshots].filter((transactionId) => !requests.has(transactionId)),
    orphanOutcomeTransactionIds: [...seenOutcomes].filter((transactionId) => !requests.has(transactionId)),
  };
};
