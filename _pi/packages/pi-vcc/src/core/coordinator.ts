import type {
	ExtensionAPI,
	ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import {
	type ContinuationEvent,
	createContinuationTransaction,
	isContinuationTerminal,
	transitionContinuation,
} from "./continuation";
import {
	adaptContinuationInitiatorOutcome,
	CONTINUATION_MESSAGE_CUSTOM_TYPE,
	CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
	CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
	CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE,
	type ContinuationAttemptOutcome,
	type ContinuationInitiator,
	type ContinuationLifecycleEpochs,
	type ContinuationResumePolicy,
	type ContinuationState,
	type ContinuationTransactionSnapshot,
	continuationMessageDetailsFor,
	createContinuationOutcomeWire,
	createContinuationRequestWire,
	createContinuationSnapshotWire,
	reconcileContinuationEntries,
} from "./continuation-protocol";
import {
	getPiVccLogPath,
	logContinuationTransaction,
	logPiVccEvent,
} from "./log";

export const CONTINUATION_WAKE_EVENT = "pi-vcc:continuation-requested";
export const CONTINUATION_SAFETY_READY_WAKE_EVENT =
	"pi-vcc:continuation-safety-ready";
export const CONTINUATION_AUTHORITY_ENV = "PI_VCC_CONTINUATION_AUTHORITY";
const CONTINUATION_PROMPT =
	"Pi-vcc interrupted active work for compaction or recovery. Continue from the preserved state and resume the next concrete step; use vcc_recall if details from before compaction are needed.";
const DEFAULT_DEADLINE_MS = 60_000;
const DEFAULT_RETRY_LIMIT = 2;
const DEFAULT_RETRY_DELAY_MS = 100;

export type ContinuationAuthority = "coordinator";

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
	setTimer?: (
		callback: () => void,
		delayMs: number,
	) => ReturnType<typeof setTimeout>;
	clearTimer?: (timer: ReturnType<typeof setTimeout>) => void;
	retryDelayMs?: number;
}

export interface ContinuationCoordinator {
	authority: ContinuationAuthority;
	request(
		input: ContinuationRequestInput,
		ctx: ExtensionContext,
	): ContinuationTransactionSnapshot;
	reconcile(ctx: ExtensionContext): void;
	getPending(): ContinuationTransactionSnapshot | undefined;
	dispose(): void;
}

const transactionIdFor = (
	input: ContinuationRequestInput,
	now: number,
): string =>
	input.transactionId ?? `vcc-${now.toString(36)}-${input.attemptId}`;

const logEventForState = (state: ContinuationState) => {
	if (state === "failed_loudly") return "failed" as const;
	return state;
};

const readAuthority = (): ContinuationAuthority => {
	const configured = process.env[CONTINUATION_AUTHORITY_ENV]?.trim().toLowerCase();
	if (configured && configured !== "coordinator") throw new Error(`${CONTINUATION_AUTHORITY_ENV}=${configured} is unsupported; restore the archived release for rollback`);
	return "coordinator";
};

const isRealUserMessage = (message: any): boolean =>
	message?.role === "user" && typeof message?.customType !== "string";

const isIndependentConsumedInput = (message: any): boolean =>
	(message?.role === "custom" &&
		message.customType !== CONTINUATION_MESSAGE_CUSTOM_TYPE) ||
	message?.role === "user";

const classifyAssistantResult = (
	message: any,
): "progress" | "error" | "aborted" | undefined => {
	if (message?.role !== "assistant") return undefined;
	if (message.stopReason === "error") return "error";
	if (message.stopReason === "aborted") return "aborted";
	if (message.stopReason === "stop") return "progress";
	return undefined;
};

const mergeEpochMax = (
	current: ContinuationLifecycleEpochs,
	incoming: ContinuationLifecycleEpochs,
): ContinuationLifecycleEpochs => ({
	session: Math.max(current.session, incoming.session),
	input: Math.max(current.input, incoming.input),
	agent: Math.max(current.agent, incoming.agent),
	turn: Math.max(current.turn, incoming.turn),
	message: Math.max(current.message, incoming.message),
	settlement: Math.max(current.settlement, incoming.settlement),
});

const withEpochBaseline = (
	snapshot: ContinuationTransactionSnapshot,
	baseline: ContinuationLifecycleEpochs,
): ContinuationTransactionSnapshot => {
	const merged = mergeEpochMax(baseline, snapshot.epochs);
	const consumedEpochs = snapshot.consumedEpochs
		? mergeEpochMax(merged, snapshot.consumedEpochs)
		: undefined;
	return {
		...snapshot,
		epochs: merged,
		...(consumedEpochs ? { consumedEpochs } : {}),
	};
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
	let lastTerminal: ContinuationTransactionSnapshot | undefined;
	let timer: ReturnType<typeof setTimeout> | undefined;
	let lastContext: ExtensionContext | undefined;
	let disposed = false;
	let sessionShutDown = false;
	let epochs: ContinuationLifecycleEpochs = {
		session: 0,
		input: 0,
		agent: 0,
		turn: 0,
		message: 0,
		settlement: 0,
	};
	let wakeUnsubscribe: (() => void) | undefined;
	let safetyWakeUnsubscribe: (() => void) | undefined;
	const queuedBehindActive = new Set<string>();

	const cancelTimer = () => {
		if (timer !== undefined) clearTimer(timer);
		timer = undefined;
	};

	const persistSnapshot = (snapshot: ContinuationTransactionSnapshot) => {
		pi.appendEntry(
			CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE,
			createContinuationSnapshotWire(snapshot),
		);
		logContinuationTransaction(
			logEventForState(snapshot.state),
			snapshot,
			now(),
		);
	};

	const persistOutcome = (snapshot: ContinuationTransactionSnapshot) => {
		pi.appendEntry(
			CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE,
			createContinuationOutcomeWire(snapshot),
		);
	};

	const warnFailure = (
		snapshot: ContinuationTransactionSnapshot,
		lastLifecycleState: ContinuationState,
		ctx: ExtensionContext,
	) => {
		const identifiers = [
			`transaction=${snapshot.transactionId}`,
			`attempt=${snapshot.attemptId}`,
			snapshot.compactionId ? `compaction=${snapshot.compactionId}` : undefined,
		]
			.filter(Boolean)
			.join(" ");
		const epochSummary = [
			`session:${snapshot.epochs.session}`,
			`input:${snapshot.epochs.input}`,
			`agent:${snapshot.epochs.agent}`,
			`turn:${snapshot.epochs.turn}`,
			`message:${snapshot.epochs.message}`,
			`settlement:${snapshot.epochs.settlement}`,
		].join(",");
		ctx.ui.notify(
			`Pi-vcc continuation failed (${identifiers}; retries=${snapshot.retryCount}; pending-tools=${snapshot.pendingToolCount}; ` +
				`last-state=${lastLifecycleState}; epochs=${epochSummary}). See ${getPiVccLogPath()}. ` +
				`Manual action: send “continue” after checking the interrupted task state.`,
			"warning",
		);
	};

	const subscribeWakes = () => {
		wakeUnsubscribe?.();
		safetyWakeUnsubscribe?.();
		const wake = () => {
			if (lastContext) reconcile(lastContext);
		};
		wakeUnsubscribe = pi.events.on(CONTINUATION_WAKE_EVENT, wake);
		safetyWakeUnsubscribe = pi.events.on(
			CONTINUATION_SAFETY_READY_WAKE_EVENT,
			wake,
		);
	};

	const unsubscribeWakes = () => {
		wakeUnsubscribe?.();
		safetyWakeUnsubscribe?.();
		wakeUnsubscribe = undefined;
		safetyWakeUnsubscribe = undefined;
	};

	const armDeadline = (snapshot: ContinuationTransactionSnapshot) => {
		cancelTimer();
		if (disposed || sessionShutDown || isContinuationTerminal(snapshot)) return;
		timer = setTimer(
			() => {
				timer = undefined;
				if (
					!current ||
					current.transactionId !== snapshot.transactionId ||
					isContinuationTerminal(current)
				)
					return;
				apply(
					{ type: "deadline", at: Math.max(now(), current.deadlineAt), epochs },
					lastContext,
				);
			},
			Math.max(0, snapshot.deadlineAt - now()),
		);
	};

	const armRetry = (snapshot: ContinuationTransactionSnapshot) => {
		cancelTimer();
		if (disposed || sessionShutDown || isContinuationTerminal(snapshot)) return;
		const remaining = snapshot.deadlineAt - now();
		if (remaining <= 0) {
			apply({ type: "deadline", at: now(), epochs }, lastContext);
			return;
		}
		timer = setTimer(
			() => {
				timer = undefined;
				if (
					!current ||
					current.transactionId !== snapshot.transactionId ||
					isContinuationTerminal(current)
				)
					return;
				if (now() >= current.deadlineAt) {
					apply({ type: "deadline", at: now(), epochs }, lastContext);
					return;
				}
				if (lastContext) submit(lastContext);
			},
			Math.min(retryDelayMs, remaining),
		);
	};

	const rememberQueuedBehindActive = (
		pending: readonly ContinuationTransactionSnapshot[],
		activeTransactionId = pending[0]?.transactionId,
	) => {
		const activeIndex = pending.findIndex(
			(snapshot) => snapshot.transactionId === activeTransactionId,
		);
		if (activeIndex < 0) return;
		for (const snapshot of pending.slice(activeIndex + 1))
			queuedBehindActive.add(snapshot.transactionId);
	};

	const activateNext = (ctx: ExtensionContext) => {
		if (disposed || sessionShutDown) return;
		const reconciled = reconcileContinuationEntries(
			ctx.sessionManager.getBranch() as any[],
		);
		rememberQueuedBehindActive(reconciled.pending);
		const pending = reconciled.pending[0];
		if (!pending) {
			current = undefined;
			cancelTimer();
			return;
		}

		current = withEpochBaseline(pending, epochs);
		epochs = mergeEpochMax(epochs, current.epochs);
		if (current.resumePolicy === "terminal") {
			apply(
				{ type: "supersede", at: now(), reason: "explicitly_stopped", epochs },
				ctx,
			);
			return;
		}
		if (current.state === "progressed") {
			cancelTimer();
			return;
		}
		const wasQueuedBehindActive = queuedBehindActive.delete(
			current.transactionId,
		);
		if (
			now() >= current.deadlineAt &&
			current.submissionCount === 0 &&
			wasQueuedBehindActive
		) {
			const deadlineMs = current.deadlineAt - current.createdAt;
			current = { ...current, deadlineAt: now() + deadlineMs };
			persistSnapshot(current);
		}
		if (now() >= current.deadlineAt) {
			apply({ type: "deadline", at: now(), epochs }, ctx);
			return;
		}

		const ready = reconciled.safetyReady.find(
			(candidate) =>
				candidate.transactionId === current?.transactionId &&
				candidate.attemptId === current.attemptId &&
				candidate.requestId === current.requestId,
		);
		if (
			(current.state === "waiting_tools" || current.pendingToolCount > 0) &&
			ready
		) {
			current = { ...current, pendingToolCount: 0 };
			apply({ type: "tools_ready", at: now(), epochs }, ctx);
			return;
		}
		if (current.pendingToolCount > 0 && current.state !== "waiting_tools") {
			apply(
				{
					type: "tools_pending",
					at: now(),
					pendingToolCount: current.pendingToolCount,
					epochs,
				},
				ctx,
			);
			return;
		}
		if (current.state === "waiting_tools") {
			armDeadline(current);
			return;
		}
		if (current.state === "consumed" || current.state === "submitted") {
			armDeadline(current);
			return;
		}
		submit(ctx);
	};

	const finishTerminal = (
		ctx: ExtensionContext | undefined,
		lastLifecycleState: ContinuationState,
	) => {
		if (!current || !isContinuationTerminal(current)) return;
		const terminal = current;
		lastTerminal = terminal;
		cancelTimer();
		persistOutcome(terminal);
		if (terminal.state === "failed_loudly" && ctx)
			warnFailure(terminal, lastLifecycleState, ctx);
		current = undefined;
		if (ctx && !sessionShutDown && !disposed) activateNext(ctx);
	};

	const handleSubmissionFailure = (ctx: ExtensionContext) => {
		if (!current) return;
		const retry = transitionContinuation(current, {
			type: "agent_settled",
			at: now(),
			epochs,
		});
		current = retry.snapshot;
		if (retry.disposition === "applied") persistSnapshot(current);
		if (isContinuationTerminal(current)) finishTerminal(ctx, "submitted");
		else if (retry.decision === "retry") armRetry(current);
		else armDeadline(current);
	};

	const submit = (ctx: ExtensionContext) => {
		if (
			!current ||
			isContinuationTerminal(current) ||
			current.pendingToolCount > 0 ||
			disposed ||
			sessionShutDown
		)
			return;
		const submitted = transitionContinuation(current, {
			type: "submitted",
			at: now(),
			epochs,
		});
		if (submitted.disposition !== "applied") return;
		current = submitted.snapshot;
		persistSnapshot(current);
		try {
			pi.sendMessage(
				{
					customType: CONTINUATION_MESSAGE_CUSTOM_TYPE,
					content: CONTINUATION_PROMPT,
					display: false,
					details: continuationMessageDetailsFor(current),
				},
				{ triggerTurn: true, deliverAs: "steer" },
			);
		} catch {
			handleSubmissionFailure(ctx);
			return;
		}
		armDeadline(current);
	};

	const apply = (event: ContinuationEvent, ctx = lastContext) => {
		if (!current || disposed) return;
		const previousState = current.state;
		const result = transitionContinuation(current, event);
		if (
			result.disposition === "ignored_invalid" ||
			result.disposition === "ignored_stale"
		)
			return;
		current = result.snapshot;
		if (result.disposition === "applied") persistSnapshot(current);
		if (isContinuationTerminal(current)) {
			finishTerminal(ctx, previousState);
			return;
		}
		if (result.decision === "retry") {
			armRetry(current);
			return;
		}
		if (result.decision === "submit" && ctx) {
			submit(ctx);
			return;
		}
		if (current.state === "progressed") {
			cancelTimer();
			return;
		}
		armDeadline(current);
	};

	const reconcile = (ctx: ExtensionContext) => {
		if (disposed || sessionShutDown) return;
		lastContext = ctx;
		const reconciled = reconcileContinuationEntries(
			ctx.sessionManager.getBranch() as any[],
		);
		if (reconciled.invalidEntryIds.length > 0) {
			logPiVccEvent("continuation_invalid_entries", {
				count: reconciled.invalidEntryIds.length,
			});
		}
		const currentPending =
			current && !isContinuationTerminal(current)
				? reconciled.pending.find(
						(snapshot) => snapshot.transactionId === current?.transactionId,
					)
				: undefined;
		if (currentPending) {
			rememberQueuedBehindActive(
				reconciled.pending,
				currentPending.transactionId,
			);
			current = withEpochBaseline(currentPending, epochs);
			epochs = mergeEpochMax(epochs, current.epochs);
			const ready = reconciled.safetyReady.find(
				(candidate) =>
					candidate.transactionId === current?.transactionId &&
					candidate.attemptId === current.attemptId &&
					candidate.requestId === current.requestId,
			);
			if (
				(current.state === "waiting_tools" || current.pendingToolCount > 0) &&
				ready
			) {
				current = { ...current, pendingToolCount: 0 };
				apply({ type: "tools_ready", at: now(), epochs }, ctx);
			}
			return;
		}
		activateNext(ctx);
	};

	const request = (input: ContinuationRequestInput, ctx: ExtensionContext) => {
		lastContext = ctx;
		const createdAt = now();
		const hasActiveTransaction = Boolean(
			current && !isContinuationTerminal(current),
		);
		const adapted = adaptContinuationInitiatorOutcome(
			input.initiator,
			input.outcome,
		);
		const deadlineMs = input.deadlineMs ?? DEFAULT_DEADLINE_MS;
		const snapshot = createContinuationTransaction({
			transactionId: transactionIdFor(input, createdAt),
			origin: adapted.origin,
			reason: adapted.reason,
			...(input.compactionId ? { compactionId: input.compactionId } : {}),
			attemptId: input.attemptId,
			...(input.requestId ? { requestId: input.requestId } : {}),
			...(input.originatingRequestId
				? { originatingRequestId: input.originatingRequestId }
				: {}),
			resumePolicy: input.resumePolicy ?? "active",
			createdAt,
			deadlineMs,
			pendingToolCount: input.pendingToolCount ?? 0,
			retryLimit: input.retryLimit ?? DEFAULT_RETRY_LIMIT,
			epochs,
		});
		if (hasActiveTransaction) queuedBehindActive.add(snapshot.transactionId);
		pi.appendEntry(
			CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE,
			createContinuationRequestWire(snapshot, input.outcome),
		);
		logContinuationTransaction("created", snapshot, createdAt);
		if (!current || isContinuationTerminal(current)) activateNext(ctx);
		return snapshot;
	};

	subscribeWakes();

	pi.on("session_start", (_event, ctx) => {
		sessionShutDown = false;
		epochs.session += 1;
		lastContext = ctx;
		subscribeWakes();
		reconcile(ctx);
	});
	pi.on("agent_start", () => {
		epochs.agent += 1;
	});
	pi.on("turn_start", () => {
		epochs.turn += 1;
	});
	pi.on("input", (event, ctx) => {
		lastContext = ctx;
		if (
			!current ||
			isContinuationTerminal(current) ||
			event.source === "extension"
		)
			return;
		epochs.input += 1;
		apply(
			{ type: "supersede", at: now(), reason: "real_user_input", epochs },
			ctx,
		);
	});
	pi.on("message_start", (event, ctx) => {
		epochs.message += 1;
		lastContext = ctx;
		if (!current || isContinuationTerminal(current)) return;
		const message = event.message as any;
		if (isRealUserMessage(message)) {
			apply(
				{ type: "supersede", at: now(), reason: "real_user_input", epochs },
				ctx,
			);
			return;
		}
		const matching =
			message?.role === "custom" &&
			message.customType === CONTINUATION_MESSAGE_CUSTOM_TYPE &&
			message.details?.transactionId === current.transactionId;
		if (!matching && isIndependentConsumedInput(message)) {
			epochs.input += 1;
			apply(
				{ type: "supersede", at: now(), reason: "independent_input", epochs },
				ctx,
			);
			return;
		}
		apply({ type: "message_start", at: now(), message, epochs }, ctx);
	});
	pi.on("message_end", (event, ctx) => {
		lastContext = ctx;
		const result = classifyAssistantResult((event as any).message);
		if (!result || !current || isContinuationTerminal(current)) return;
		if (
			result === "progress" &&
			(current.state === "waiting_tools" || current.pendingToolCount > 0)
		) {
			current = { ...current, pendingToolCount: 0 };
			persistSnapshot(current);
			apply({ type: "tools_ready", at: now(), epochs }, ctx);
			return;
		}
		apply({ type: "assistant_result", at: now(), result, epochs }, ctx);
	});
	pi.on("agent_end", (event, ctx) => {
		lastContext = ctx;
		const messages = (event as any).messages;
		const result = classifyAssistantResult(
			Array.isArray(messages) ? messages.at(-1) : undefined,
		);
		if (!result || !current || isContinuationTerminal(current)) return;
		if (
			result === "progress" &&
			(current.state === "waiting_tools" || current.pendingToolCount > 0)
		) {
			current = { ...current, pendingToolCount: 0 };
			persistSnapshot(current);
			apply({ type: "tools_ready", at: now(), epochs }, ctx);
			return;
		}
		if (current.state === "consumed")
			apply({ type: "assistant_result", at: now(), result, epochs }, ctx);
	});
	pi.on("agent_settled", (_event, ctx) => {
		epochs.settlement += 1;
		lastContext = ctx;
		apply({ type: "agent_settled", at: now(), epochs }, ctx);
	});
	pi.on("session_shutdown", (event, ctx) => {
		cancelTimer();
		unsubscribeWakes();
		lastContext = ctx;
		sessionShutDown = true;
		if (event.reason === "reload") return;

		const reconciled = reconcileContinuationEntries(
			ctx.sessionManager.getBranch() as any[],
		);
		for (const pending of reconciled.pending) {
			const baseline = withEpochBaseline(pending, {
				...epochs,
				session: epochs.session + 1,
			});
			const terminal = transitionContinuation(baseline, {
				type: "supersede",
				at: Math.max(now(), baseline.createdAt),
				reason: "session_replaced",
				epochs: baseline.epochs,
			}).snapshot;
			if (!isContinuationTerminal(terminal)) continue;
			persistSnapshot(terminal);
			persistOutcome(terminal);
			if (current?.transactionId === terminal.transactionId)
				current = undefined;
		}
	});

	return {
		authority,
		request,
		reconcile,
		getPending: () => current ?? lastTerminal,
		dispose: () => {
			if (disposed) return;
			disposed = true;
			cancelTimer();
			unsubscribeWakes();
		},
	};
};
