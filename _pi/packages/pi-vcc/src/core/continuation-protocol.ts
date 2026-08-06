export const CONTINUATION_PROTOCOL_NAME = "pi-vcc-continuation" as const;
export const CONTINUATION_PROTOCOL_VERSION = 2 as const;
export const CONTINUATION_LEGACY_PROTOCOL_VERSION = 1 as const;
export type ContinuationProtocolVersion = 1 | 2;
export const CONTINUATION_MESSAGE_CUSTOM_TYPE = "pi-vcc-continuation" as const;
export const CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE = "pi-vcc-continuation-request" as const;
export const CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE = "pi-vcc-continuation-snapshot" as const;
export const CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE = "pi-vcc-continuation-outcome" as const;
export const CONTINUATION_SAFETY_READY_ENTRY_CUSTOM_TYPE = "pi-vcc-continuation-safety-ready" as const;

export const CONTINUATION_ORIGINS = ["package-command", "compact_context", "hard-backstop", "host-threshold", "host-overflow"] as const;
export type ContinuationOrigin = (typeof CONTINUATION_ORIGINS)[number];
export const CONTINUATION_REASONS = ["compacted", "no-safe-cut", "cancelled", "failed"] as const;
export type ContinuationReason = (typeof CONTINUATION_REASONS)[number];
export const CONTINUATION_RESUME_POLICIES = ["active", "terminal"] as const;
export type ContinuationResumePolicy = (typeof CONTINUATION_RESUME_POLICIES)[number];
export const CONTINUATION_INITIATORS = ["package-pi-vcc", "package-compact-now", "compact_context", "hard-backstop", "host-threshold", "host-overflow"] as const;
export type ContinuationInitiator = (typeof CONTINUATION_INITIATORS)[number];
export const CONTINUATION_ATTEMPT_OUTCOMES = ["compacted", "no-safe-cut", "cancellation", "failure"] as const;
export type ContinuationAttemptOutcome = (typeof CONTINUATION_ATTEMPT_OUTCOMES)[number];

export interface ContinuationInitiatorOutcome {
  initiator: ContinuationInitiator;
  outcome: ContinuationAttemptOutcome;
  origin: ContinuationOrigin;
  reason: ContinuationReason;
}

export const adaptContinuationInitiatorOutcome = (initiator: ContinuationInitiator, outcome: ContinuationAttemptOutcome): ContinuationInitiatorOutcome => ({
  initiator,
  outcome,
  origin: initiator === "package-pi-vcc" || initiator === "package-compact-now" ? "package-command" : initiator,
  reason: outcome === "cancellation" ? "cancelled" : outcome === "failure" ? "failed" : outcome,
});

export const CONTINUATION_STATES = ["created", "waiting_tools", "submitted", "consumed", "progressed", "stalled", "retrying", "settled", "superseded", "failed_loudly"] as const;
export type ContinuationState = (typeof CONTINUATION_STATES)[number];
export const CONTINUATION_TERMINAL_STATES = ["settled", "superseded", "failed_loudly"] as const;
export type ContinuationTerminalState = (typeof CONTINUATION_TERMINAL_STATES)[number];
export const CONTINUATION_TERMINAL_REASONS = ["progressed_then_agent_settled", "real_user_input", "independent_input", "session_replaced", "explicitly_stopped", "deadline_expired", "retry_limit_exhausted", "host_unavailable", "invalid_persistence", "reload_rehydrate_failed", "unrecoverable_error"] as const;
export type ContinuationTerminalReason = (typeof CONTINUATION_TERMINAL_REASONS)[number];
export type ContinuationSupersedeReason = Extract<ContinuationTerminalReason, "real_user_input" | "independent_input" | "session_replaced" | "explicitly_stopped">;
export type ContinuationFailureReason = Exclude<ContinuationTerminalReason, "progressed_then_agent_settled" | ContinuationSupersedeReason>;

export interface ContinuationLifecycleEpochs { session: number; input: number; agent: number; turn: number; message: number; settlement: number }
export interface ContinuationMessageDetails {
  protocol: typeof CONTINUATION_PROTOCOL_NAME;
  version: ContinuationProtocolVersion;
  transactionId: string;
  attemptId: string;
  submissionCount: number;
  compactionId?: string;
  requestId?: string;
  originatingRequestId?: string;
}
export type ContinuationAssistantResult = "progress" | "error" | "aborted";

export interface ContinuationTransactionSnapshot {
  protocol: typeof CONTINUATION_PROTOCOL_NAME;
  version: ContinuationProtocolVersion;
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
  /** Compatibility/logging alias. V2 timers use the phase-specific fields below. */
  deadlineAt: number;
  queuedAt?: number;
  activatedAt?: number;
  submittedAt?: number;
  acceptanceDeadlineAt?: number;
  acceptedAt?: number;
  lastProgressAt?: number;
  progressDeadlineAt?: number;
  toolStallDeadlineAt?: number;
  nextRetryAt?: number;
  phaseEpoch?: number;
  pendingToolCount: number;
  submissionCount: number;
  retryCount: number;
  retryLimit: number;
  epochs: ContinuationLifecycleEpochs;
  consumedEpochs?: ContinuationLifecycleEpochs;
  lastAssistantResult?: ContinuationAssistantResult;
  terminalReason?: ContinuationTerminalReason;
  stalledWarningIssued?: boolean;
}

export interface ContinuationRequestWire { protocol: typeof CONTINUATION_PROTOCOL_NAME; version: ContinuationProtocolVersion; kind: "request"; snapshot: ContinuationTransactionSnapshot; outcomeHint?: ContinuationAttemptOutcome }
export interface ContinuationSnapshotWire { protocol: typeof CONTINUATION_PROTOCOL_NAME; version: ContinuationProtocolVersion; kind: "snapshot"; snapshot: ContinuationTransactionSnapshot }
export interface ContinuationOutcomeWire { protocol: typeof CONTINUATION_PROTOCOL_NAME; version: ContinuationProtocolVersion; kind: "outcome"; transactionId: string; terminalState: ContinuationTerminalState; terminalReason: ContinuationTerminalReason; snapshot: ContinuationTransactionSnapshot }
export interface ContinuationSafetyReadyWire { protocol: typeof CONTINUATION_PROTOCOL_NAME; version: ContinuationProtocolVersion; kind: "safety-ready"; transactionId: string; attemptId: string; requestId?: string }
export type ContinuationWire = ContinuationRequestWire | ContinuationSnapshotWire | ContinuationOutcomeWire | ContinuationSafetyReadyWire;

export interface ContinuationCustomEntryLike { id?: string; type: string; customType?: string; data?: unknown; details?: unknown; message?: unknown; timestamp?: number | string }
export interface DurableContinuationAcceptance { entryId: string; details: ContinuationMessageDetails; timestamp?: number }
export interface ReconciledContinuationEntries {
  pending: ContinuationTransactionSnapshot[];
  terminal: ContinuationOutcomeWire[];
  snapshots: ContinuationTransactionSnapshot[];
  safetyReady: ContinuationSafetyReadyWire[];
  durableAcceptances: DurableContinuationAcceptance[];
  invalidEntryIds: string[];
  duplicateRequestTransactionIds: string[];
  orphanSnapshotTransactionIds: string[];
  orphanOutcomeTransactionIds: string[];
  orphanSafetyReadyTransactionIds: string[];
}

const record = (value: unknown): value is Record<string, unknown> => typeof value === "object" && value !== null && !Array.isArray(value);
const nonempty = (value: unknown): value is string => typeof value === "string" && value.length > 0;
const integer = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value) && Number.isInteger(value) && value >= 0;
const timestamp = (value: unknown): value is number => typeof value === "number" && Number.isFinite(value) && value >= 0;
const oneOf = <T extends readonly string[]>(values: T, value: unknown): value is T[number] => typeof value === "string" && (values as readonly string[]).includes(value);
const version = (value: unknown): value is ContinuationProtocolVersion => value === 1 || value === 2;
const exact = (value: Record<string, unknown>, required: readonly string[], optional: readonly string[] = []) => {
  const allowed = new Set([...required, ...optional]);
  return required.every((key) => Object.hasOwn(value, key)) && Object.keys(value).every((key) => allowed.has(key));
};
const parseJson = (value: unknown): unknown => {
  if (typeof value !== "string") return value;
  try { return JSON.parse(value); } catch { return undefined; }
};

export const isContinuationLifecycleEpochs = (value: unknown): value is ContinuationLifecycleEpochs => record(value) && exact(value, ["session", "input", "agent", "turn", "message", "settlement"]) && Object.values(value).every(integer);

export const isContinuationMessageDetails = (value: unknown): value is ContinuationMessageDetails => record(value) && exact(value, ["protocol", "version", "transactionId", "attemptId", "submissionCount"], ["compactionId", "requestId", "originatingRequestId"]) && value.protocol === CONTINUATION_PROTOCOL_NAME && version(value.version) && nonempty(value.transactionId) && nonempty(value.attemptId) && integer(value.submissionCount) && value.submissionCount > 0 && (value.compactionId === undefined || nonempty(value.compactionId)) && (value.requestId === undefined || nonempty(value.requestId)) && (value.originatingRequestId === undefined || nonempty(value.originatingRequestId));

export const continuationMessageDetailsFor = (snapshot: ContinuationTransactionSnapshot): ContinuationMessageDetails => ({
  protocol: CONTINUATION_PROTOCOL_NAME,
  version: CONTINUATION_PROTOCOL_VERSION,
  transactionId: snapshot.transactionId,
  attemptId: snapshot.attemptId,
  submissionCount: snapshot.submissionCount,
  ...(snapshot.compactionId ? { compactionId: snapshot.compactionId } : {}),
  ...(snapshot.requestId ? { requestId: snapshot.requestId } : {}),
  ...(snapshot.originatingRequestId ? { originatingRequestId: snapshot.originatingRequestId } : {}),
});

export const isMatchingContinuationDetails = (snapshot: ContinuationTransactionSnapshot, value: unknown): value is ContinuationMessageDetails => isContinuationMessageDetails(value) && value.transactionId === snapshot.transactionId && value.attemptId === snapshot.attemptId && value.submissionCount === snapshot.submissionCount && value.compactionId === snapshot.compactionId && value.requestId === snapshot.requestId && value.originatingRequestId === snapshot.originatingRequestId;

const TIMING_KEYS = ["queuedAt", "activatedAt", "submittedAt", "acceptanceDeadlineAt", "acceptedAt", "lastProgressAt", "progressDeadlineAt", "toolStallDeadlineAt", "nextRetryAt"] as const;
export const isContinuationTransactionSnapshot = (value: unknown): value is ContinuationTransactionSnapshot => {
  if (!record(value)) return false;
  const required = ["protocol", "version", "transactionId", "origin", "reason", "attemptId", "resumePolicy", "state", "createdAt", "deadlineAt", "pendingToolCount", "submissionCount", "retryCount", "retryLimit", "epochs"];
  const optional = ["compactionId", "requestId", "originatingRequestId", "consumedEpochs", "lastAssistantResult", "terminalReason", "phaseEpoch", "stalledWarningIssued", ...TIMING_KEYS];
  if (!exact(value, required, optional) || value.protocol !== CONTINUATION_PROTOCOL_NAME || !version(value.version) || !nonempty(value.transactionId) || !oneOf(CONTINUATION_ORIGINS, value.origin) || !oneOf(CONTINUATION_REASONS, value.reason) || !nonempty(value.attemptId) || !oneOf(CONTINUATION_RESUME_POLICIES, value.resumePolicy) || !oneOf(CONTINUATION_STATES, value.state) || !timestamp(value.createdAt) || !timestamp(value.deadlineAt) || !integer(value.pendingToolCount) || !integer(value.submissionCount) || !integer(value.retryCount) || !integer(value.retryLimit) || !isContinuationLifecycleEpochs(value.epochs)) return false;
  if (value.version === 2 && (!integer(value.phaseEpoch) || !timestamp(value.queuedAt))) return false;
  if (TIMING_KEYS.some((key) => value[key] !== undefined && !timestamp(value[key]))) return false;
  if (value.compactionId !== undefined && !nonempty(value.compactionId)) return false;
  if (value.requestId !== undefined && !nonempty(value.requestId)) return false;
  if (value.originatingRequestId !== undefined && !nonempty(value.originatingRequestId)) return false;
  if (value.consumedEpochs !== undefined && !isContinuationLifecycleEpochs(value.consumedEpochs)) return false;
  if (value.lastAssistantResult !== undefined && !oneOf(["progress", "error", "aborted"] as const, value.lastAssistantResult)) return false;
  const terminal = oneOf(CONTINUATION_TERMINAL_STATES, value.state);
  return terminal ? oneOf(CONTINUATION_TERMINAL_REASONS, value.terminalReason) : value.terminalReason === undefined;
};

const wireBase = (value: unknown, kind: string): value is Record<string, unknown> => record(value) && value.protocol === CONTINUATION_PROTOCOL_NAME && version(value.version) && value.kind === kind;
const matchingWireSnapshotVersion = (value: Record<string, unknown>) =>
  record(value.snapshot) && value.version === value.snapshot.version;
export const isContinuationRequestWire = (value: unknown): value is ContinuationRequestWire => wireBase(value, "request") && exact(value, ["protocol", "version", "kind", "snapshot"], ["outcomeHint"]) && matchingWireSnapshotVersion(value) && isContinuationTransactionSnapshot(value.snapshot) && value.snapshot.state === "created" && (value.outcomeHint === undefined || oneOf(CONTINUATION_ATTEMPT_OUTCOMES, value.outcomeHint));
export const isContinuationSnapshotWire = (value: unknown): value is ContinuationSnapshotWire => wireBase(value, "snapshot") && exact(value, ["protocol", "version", "kind", "snapshot"]) && matchingWireSnapshotVersion(value) && isContinuationTransactionSnapshot(value.snapshot);
export const isContinuationOutcomeWire = (value: unknown): value is ContinuationOutcomeWire => wireBase(value, "outcome") && exact(value, ["protocol", "version", "kind", "transactionId", "terminalState", "terminalReason", "snapshot"]) && matchingWireSnapshotVersion(value) && nonempty(value.transactionId) && oneOf(CONTINUATION_TERMINAL_STATES, value.terminalState) && oneOf(CONTINUATION_TERMINAL_REASONS, value.terminalReason) && isContinuationTransactionSnapshot(value.snapshot) && value.snapshot.transactionId === value.transactionId && value.snapshot.state === value.terminalState && value.snapshot.terminalReason === value.terminalReason;
export const isContinuationSafetyReadyWire = (value: unknown): value is ContinuationSafetyReadyWire => wireBase(value, "safety-ready") && exact(value, ["protocol", "version", "kind", "transactionId", "attemptId"], ["requestId"]) && nonempty(value.transactionId) && nonempty(value.attemptId) && (value.requestId === undefined || nonempty(value.requestId));
export const isContinuationWire = (value: unknown): value is ContinuationWire => isContinuationRequestWire(value) || isContinuationSnapshotWire(value) || isContinuationOutcomeWire(value) || isContinuationSafetyReadyWire(value);
const adaptPersistedSnapshot = (value: unknown): unknown => {
  if (!record(value)) return value;
  if (value.version !== CONTINUATION_LEGACY_PROTOCOL_VERSION || value.resumePolicy !== "auto") return value;
  if (value.origin !== "compact_context") return value;
  return { ...value, resumePolicy: "active" };
};
const adaptPersistedWire = (value: unknown): unknown => {
  if (!record(value) || !record(value.snapshot)) return value;
  // Envelope and snapshot versions must agree before adaptation. A V2 envelope
  // carrying a V1 auto snapshot is invalid persistence, not a dual-read form.
  if (value.version !== value.snapshot.version) return value;
  return { ...value, snapshot: adaptPersistedSnapshot(value.snapshot) };
};
export const parseContinuationRequest = (value: unknown) => { const parsed = adaptPersistedWire(parseJson(value)); return isContinuationRequestWire(parsed) ? parsed : undefined; };
export const parseContinuationSnapshot = (value: unknown) => { const parsed = adaptPersistedWire(parseJson(value)); return isContinuationSnapshotWire(parsed) ? parsed : undefined; };
export const parseContinuationOutcome = (value: unknown) => { const parsed = adaptPersistedWire(parseJson(value)); return isContinuationOutcomeWire(parsed) ? parsed : undefined; };
export const parseContinuationSafetyReady = (value: unknown) => { const parsed = parseJson(value); return isContinuationSafetyReadyWire(parsed) ? parsed : undefined; };
export const serializeContinuationWire = (wire: ContinuationWire) => { if (!isContinuationWire(wire)) throw new TypeError("Invalid pi-vcc continuation wire payload"); return JSON.stringify(wire); };

const v2Snapshot = (snapshot: ContinuationTransactionSnapshot): ContinuationTransactionSnapshot => ({ ...snapshot, version: CONTINUATION_PROTOCOL_VERSION, queuedAt: snapshot.queuedAt ?? snapshot.createdAt, phaseEpoch: snapshot.phaseEpoch ?? 0 });
export const createContinuationRequestWire = (snapshot: ContinuationTransactionSnapshot, outcomeHint?: ContinuationAttemptOutcome): ContinuationRequestWire => {
  const current = v2Snapshot(snapshot);
  const wire: ContinuationRequestWire = { protocol: CONTINUATION_PROTOCOL_NAME, version: CONTINUATION_PROTOCOL_VERSION, kind: "request", snapshot: current, ...(outcomeHint ? { outcomeHint } : {}) };
  if (!isContinuationRequestWire(wire)) throw new TypeError("Continuation request requires a valid created snapshot");
  return wire;
};
export const createContinuationSnapshotWire = (snapshot: ContinuationTransactionSnapshot): ContinuationSnapshotWire => {
  const wire: ContinuationSnapshotWire = { protocol: CONTINUATION_PROTOCOL_NAME, version: CONTINUATION_PROTOCOL_VERSION, kind: "snapshot", snapshot: v2Snapshot(snapshot) };
  if (!isContinuationSnapshotWire(wire)) throw new TypeError("Continuation snapshot is invalid");
  return wire;
};
export const createContinuationOutcomeWire = (snapshot: ContinuationTransactionSnapshot): ContinuationOutcomeWire => {
  const current = v2Snapshot(snapshot);
  if (!oneOf(CONTINUATION_TERMINAL_STATES, current.state) || !current.terminalReason) throw new TypeError("Continuation outcome requires a terminal snapshot");
  const wire: ContinuationOutcomeWire = { protocol: CONTINUATION_PROTOCOL_NAME, version: CONTINUATION_PROTOCOL_VERSION, kind: "outcome", transactionId: current.transactionId, terminalState: current.state, terminalReason: current.terminalReason, snapshot: current };
  if (!isContinuationOutcomeWire(wire)) throw new TypeError("Continuation outcome is invalid");
  return wire;
};
export const createContinuationSafetyReadyWire = (input: Pick<ContinuationSafetyReadyWire, "transactionId" | "attemptId" | "requestId">): ContinuationSafetyReadyWire => ({ protocol: CONTINUATION_PROTOCOL_NAME, version: CONTINUATION_PROTOCOL_VERSION, kind: "safety-ready", transactionId: input.transactionId, attemptId: input.attemptId, ...(input.requestId ? { requestId: input.requestId } : {}) });

const customMessage = (entry: ContinuationCustomEntryLike): { details?: unknown; timestamp?: number } | undefined => {
  if (entry.type === "custom_message" && entry.customType === CONTINUATION_MESSAGE_CUSTOM_TYPE) return { details: entry.details ?? (record(entry.data) ? entry.data.details : undefined), timestamp: typeof entry.timestamp === "number" ? entry.timestamp : undefined };
  if (entry.type === "message" && record(entry.message) && entry.message.role === "custom" && entry.message.customType === CONTINUATION_MESSAGE_CUSTOM_TYPE) return { details: entry.message.details, timestamp: typeof entry.message.timestamp === "number" ? entry.message.timestamp : undefined };
  return undefined;
};

export const reconcileContinuationEntries = (entries: readonly ContinuationCustomEntryLike[]): ReconciledContinuationEntries => {
  const requests = new Map<string, ContinuationTransactionSnapshot>();
  const requestOrder: string[] = [];
  const latest = new Map<string, ContinuationTransactionSnapshot>();
  const outcomes = new Map<string, ContinuationOutcomeWire>();
  const ready = new Map<string, ContinuationSafetyReadyWire>();
  const durableAcceptances: DurableContinuationAcceptance[] = [];
  const snapshots: ContinuationTransactionSnapshot[] = [];
  const invalidEntryIds: string[] = [];
  const duplicate = new Set<string>();
  const seenSnapshots = new Set<string>(); const seenOutcomes = new Set<string>(); const seenReady = new Set<string>();
  const seenEntryIds = new Set<string>();
  entries.forEach((entry, index) => {
    const entryId = entry.id ?? `index:${index}`;
    if (entry.id && seenEntryIds.has(entry.id)) return;
    if (entry.id) seenEntryIds.add(entry.id);
    const message = customMessage(entry);
    if (message) {
      if (isContinuationMessageDetails(message.details)) durableAcceptances.push({ entryId, details: message.details, ...(message.timestamp === undefined ? {} : { timestamp: message.timestamp }) });
      else invalidEntryIds.push(entryId);
      return;
    }
    if (entry.type !== "custom") return;
    if (entry.customType === CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE) {
      const wire = parseContinuationRequest(entry.data); if (!wire) { invalidEntryIds.push(entryId); return; }
      const id = wire.snapshot.transactionId; if (requests.has(id)) duplicate.add(id); else { requests.set(id, wire.snapshot); requestOrder.push(id); } return;
    }
    if (entry.customType === CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE) { const wire = parseContinuationSnapshot(entry.data); if (!wire) { invalidEntryIds.push(entryId); return; } snapshots.push(wire.snapshot); latest.set(wire.snapshot.transactionId, wire.snapshot); seenSnapshots.add(wire.snapshot.transactionId); return; }
    if (entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE) { const wire = parseContinuationOutcome(entry.data); if (!wire) { invalidEntryIds.push(entryId); return; } if (!outcomes.has(wire.transactionId)) outcomes.set(wire.transactionId, wire); seenOutcomes.add(wire.transactionId); return; }
    if (entry.customType === CONTINUATION_SAFETY_READY_ENTRY_CUSTOM_TYPE) { const wire = parseContinuationSafetyReady(entry.data); if (!wire) { invalidEntryIds.push(entryId); return; } ready.set(wire.transactionId, wire); seenReady.add(wire.transactionId); }
  });
  return {
    pending: requestOrder.flatMap((id) => outcomes.has(id) ? [] : [latest.get(id) ?? requests.get(id)!]),
    terminal: requestOrder.flatMap((id) => outcomes.get(id) ? [outcomes.get(id)!] : []),
    snapshots,
    safetyReady: requestOrder.flatMap((id) => ready.get(id) ? [ready.get(id)!] : []),
    durableAcceptances,
    invalidEntryIds,
    duplicateRequestTransactionIds: [...duplicate],
    orphanSnapshotTransactionIds: [...seenSnapshots].filter((id) => !requests.has(id)),
    orphanOutcomeTransactionIds: [...seenOutcomes].filter((id) => !requests.has(id)),
    orphanSafetyReadyTransactionIds: [...seenReady].filter((id) => !requests.has(id)),
  };
};
