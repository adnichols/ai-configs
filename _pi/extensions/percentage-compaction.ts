import { appendFileSync, mkdirSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import type { AssistantMessage } from "@earendil-works/pi-ai/compat";
import { isContextOverflow } from "@earendil-works/pi-ai/compat";
import type {
	AgentEndEvent,
	ExtensionAPI,
	ExtensionContext,
	ModelSelectEvent,
	SessionBeforeCompactEvent,
	TurnEndEvent,
} from "@earendil-works/pi-coding-agent";
import {
	formatGrokThresholdStatus,
	GROK_ADVERTISED_CONTEXT_WINDOW,
	GROK_COMPACTION_TRIGGER_TOKENS,
	GROK_CONTEXT_CEILING_TOKENS,
	grokCompactionTriggerReached,
	isGrokContextCeilingModel,
} from "../lib/grok-context-ceiling-policy";
export const COMPACTION_NUDGE_PERCENT = 60;
export const COMPACTION_STRONG_NUDGE_PERCENT = 75;
export const HARD_AUTO_COMPACTION_PERCENT = 80;
export const FAILURE_DELAY_TURNS = 1;
export const COMPACTION_THRESHOLD_PERCENT = COMPACTION_NUDGE_PERCENT;
export const PI_VCC_MANUAL_BYPASS_MARKER = "__PI_VCC_MANUAL_BYPASS__";
export const PI_VCC_LOAD_MARKER = "__ADN_PI_VCC_LOADED__";

type NudgeBand = "soft" | "strong";
type Boundary =
	| "subtask_complete"
	| "before_topic_switch"
	| "after_test_loop"
	| "manual_recovery";
type ResumePolicy = "active" | "terminal" | "auto";
type ContinuationOutcome =
	| "compacted"
	| "no-safe-cut"
	| "cancellation"
	| "failure";
type ContinuationInitiator =
	| "package-compact-now"
	| "compact_context"
	| "hard-backstop"
	| "host-overflow";

interface PendingModelCompaction {
	requestId: string;
	reason: string;
	boundary: Boundary;
	resumePolicy: ResumePolicy;
	preserve?: string;
	requestedTurn: number;
	toolCallId?: string;
	toolBatchId?: number;
	sawSiblingTools: boolean;
}

interface PendingNoCutContinuation {
	reason: "already_compacted" | "session_too_small";
	usagePercent?: number;
	flooredPercent?: number;
	pendingToolCallIds: Set<string>;
	queuedTurn: number;
	attempts: number;
	startedAt?: number;
	timer?: ReturnType<typeof setTimeout>;
	lastError?: string;
}

interface InterruptedCompactionTurn {
	interrupted: boolean;
	pendingToolCallIds: Set<string>;
	reason:
		| "hard_backstop"
		| "compact_context"
		| "core_deferred"
		| "compaction_error";
}

interface PendingCompactionContinuation {
	attemptId: number;
	originatingRequestId?: string;
	reason: "cancelled" | "failed";
	interrupted: InterruptedCompactionTurn;
	queuedTurn: number;
	attempts: number;
	startedAt?: number;
	timer?: ReturnType<typeof setTimeout>;
	lastError?: string;
}

type CompactionOwner = "pi-vcc" | "core" | undefined;

interface NoCutRecoveryOptions {
	interruptedActiveTurn: boolean;
	pendingToolCallIds: () => string[];
	usagePercent?: number;
}

interface NoCutRetryState {
	flooredPercent: number;
	usagePercent?: number;
	userMessageCount: number;
	reason: "already_compacted" | "session_too_small";
}

const NO_CUT_CONTINUATION_DELAY_MS = 50;
const NO_CUT_CONTINUATION_MAX_WAIT_MS = 5000;
const NO_CUT_CONTINUATION_RETRY_MS = 100;
const COMPACTION_CONTINUATION_DELAY_MS = NO_CUT_CONTINUATION_DELAY_MS;
const COMPACTION_CONTINUATION_MAX_WAIT_MS = NO_CUT_CONTINUATION_MAX_WAIT_MS;
const COMPACTION_CONTINUATION_RETRY_MS = NO_CUT_CONTINUATION_RETRY_MS;
const DEFAULT_PI_VCC_LOG_PATH = join(homedir(), ".pi", "logs", "pi-vcc.jsonl");
const getPiVccLogPath = () =>
	process.env.PI_VCC_LOG_PATH?.trim() || DEFAULT_PI_VCC_LOG_PATH;
const CONTINUATION_PROTOCOL_NAME = "pi-vcc-continuation" as const;
const CONTINUATION_PROTOCOL_VERSION = 2 as const;
const CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE = "pi-vcc-continuation-request";
const CONTINUATION_SAFETY_READY_ENTRY_CUSTOM_TYPE =
	"pi-vcc-continuation-safety-ready";
const CONTINUATION_WAKE_EVENT = "pi-vcc:continuation-requested";
const CONTINUATION_SAFETY_READY_WAKE_EVENT = "pi-vcc:continuation-safety-ready";
const CONTINUATION_AUTHORITY_ENV = "PI_VCC_STANDALONE_CONTINUATION_AUTHORITY";
const CONTINUATION_DEADLINE_MS = 15_000;
const CONTINUATION_RETRY_LIMIT = 2;

// Keep this diagnostic sanitizer in sync with _pi/packages/pi-vcc/src/core/log.ts.
const SECRET_KEY_PATTERN =
	/(^|[_-])(token|secret|authorization|password|api[_-]?key|apikey)($|[_-])/i;
const SECRET_VALUE_PATTERN =
	/\b(Bearer\s+)[A-Za-z0-9._~+/=-]+|\b(sk-[A-Za-z0-9_-]{12,})\b/g;

const scrubLogText = (value: string): string =>
	value.length > 4000
		? `${value.slice(0, 4000).replace(SECRET_VALUE_PATTERN, "$1[redacted]")}…[truncated]`
		: value.replace(SECRET_VALUE_PATTERN, "$1[redacted]");

const serializeLogError = (err: unknown) => {
	if (err instanceof Error) {
		return {
			name: err.name,
			message: scrubLogText(err.message),
			stack: err.stack ? scrubLogText(err.stack) : undefined,
		};
	}
	return { message: scrubLogText(String(err)) };
};

const safePiVccLogJson = (value: unknown): unknown => {
	if (value instanceof Error) return serializeLogError(value);
	if (typeof value === "string") return scrubLogText(value);
	if (Array.isArray(value)) return value.map(safePiVccLogJson);
	if (value instanceof Set) return [...value].map(safePiVccLogJson);
	if (value instanceof Map) {
		return Object.fromEntries(
			[...value].map(([key, raw]) => [String(key), safePiVccLogJson(raw)]),
		);
	}
	if (!value || typeof value !== "object") return value;
	const output: Record<string, unknown> = {};
	for (const [key, raw] of Object.entries(value as Record<string, unknown>)) {
		if (SECRET_KEY_PATTERN.test(key)) {
			output[key] = "[redacted]";
			continue;
		}
		output[key] = safePiVccLogJson(raw);
	}
	return output;
};

const logPiVccEvent = (event: string, data: Record<string, unknown> = {}) => {
	try {
		const logPath = getPiVccLogPath();
		mkdirSync(dirname(logPath), { recursive: true });
		appendFileSync(
			logPath,
			`${JSON.stringify({
				timestamp: new Date().toISOString(),
				event,
				cwd: process.cwd(),
				...(safePiVccLogJson(data) as Record<string, unknown>),
			})}\n`,
		);
	} catch {}
};

const logPiVccError = (
	event: string,
	err: unknown,
	data: Record<string, unknown> = {},
) => {
	logPiVccEvent(event, { ...data, error: err });
};

const STALE_EXTENSION_CONTEXT_PREFIX =
	"This extension ctx is stale after session replacement or reload.";

const isStaleExtensionContextError = (err: unknown): boolean =>
	err instanceof Error && err.message.startsWith(STALE_EXTENSION_CONTEXT_PREFIX);

const isPiVccLoaded = () => Boolean((globalThis as any)[PI_VCC_LOAD_MARKER]);

const notifyMissingPiVcc = (ctx: ExtensionContext) => {
	ctx.ui.notify(
		"Pi-vcc is not loaded; canceling compaction to avoid unsafe default compaction. Run ./install.sh --pi and restart Pi.",
		"error",
	);
};

const isCompletedAssistantResponse = (message: TurnEndEvent["message"]) => {
	if (message.role !== "assistant") return false;
	return !("stopReason" in message && message.stopReason === "toolUse");
};

const isUsablePostCompactionAssistantResponse = (
	message: TurnEndEvent["message"],
) => {
	if (message.role !== "assistant") return false;
	if (!("stopReason" in message)) return true;
	return message.stopReason !== "error" && message.stopReason !== "aborted";
};

const isInterruptedAgentWork = (message: TurnEndEvent["message"]) =>
	(message.role === "assistant" &&
		"stopReason" in message &&
		message.stopReason === "toolUse") ||
	message.role === "toolResult";

const contextWindowFor = (ctx: ExtensionContext): number | undefined =>
	(ctx.model as { contextWindow?: number } | undefined)?.contextWindow ??
	ctx.getContextUsage()?.contextWindow;

const isContextOverflowResponse = (
	message: unknown,
	ctx: ExtensionContext,
): boolean => {
	if ((message as { role?: string } | undefined)?.role !== "assistant")
		return false;
	const assistant = message as {
		provider?: string;
		model?: string;
		stopReason?: string;
		usage?: { input?: number; cacheRead?: number; output?: number };
	};
	const model = ctx.model as { provider?: string; id?: string } | undefined;
	if (
		!model ||
		assistant.provider !== model.provider ||
		assistant.model !== model.id
	)
		return false;
	if (
		(assistant.stopReason === "stop" || assistant.stopReason === "length") &&
		!assistant.usage
	)
		return false;
	return isContextOverflow(message as AssistantMessage, contextWindowFor(ctx));
};

const overflowRequiresRetry = (message: unknown): boolean =>
	(message as { stopReason?: string } | undefined)?.stopReason !== "stop";

const buildOverflowResumeMessage = () =>
	"Pi VCC recovered from a provider context-overflow response. Retry the interrupted request from the compacted state; do not repeat an oversized request.";

const isStaleAutoCompactionPercent = (
	percent: number,
	lastPercent: number | undefined,
) => lastPercent !== undefined && percent === lastPercent;

const clampText = (value: unknown, max = 500): string | undefined => {
	if (typeof value !== "string") return undefined;
	const trimmed = value.trim();
	return trimmed ? trimmed.slice(0, max) : undefined;
};

const messageText = (message: any): string => {
	const content = message?.content;
	if (typeof content === "string") return content;
	if (Array.isArray(content)) {
		return content
			.map((part) => {
				if (typeof part?.text === "string") return part.text;
				if (typeof part?.content === "string") return part.content;
				return "";
			})
			.join("\n");
	}
	return "";
};

const hasFailureOutput = (message: any): boolean => {
	if (message?.role !== "toolResult") return false;
	if (message.isError === true) return true;
	const text = messageText(message);
	return /\b(nonzero|failed|failure|error|exception|tests? failed|exit code [1-9])\b/i.test(
		text,
	);
};

const toolCallCount = (message: any): number => {
	if (message?.role !== "assistant" || !Array.isArray(message?.content))
		return 0;
	return message.content.filter((part: any) => part?.type === "toolCall")
		.length;
};

const assistantToolCallIds = (message: any): string[] => {
	if (message?.role !== "assistant" || !Array.isArray(message?.content))
		return [];
	return message.content
		.filter(
			(part: any) => part?.type === "toolCall" && typeof part?.id === "string",
		)
		.map((part: any) => part.id);
};

const assistantToolBatchIncludes = (
	message: any,
	toolCallId: string | undefined,
): boolean => {
	if (
		!toolCallId ||
		message?.role !== "assistant" ||
		!Array.isArray(message?.content)
	)
		return false;
	return message.content.some(
		(part: any) => part?.type === "toolCall" && part?.id === toolCallId,
	);
};

const toolResultMatches = (
	result: any,
	toolCallId: string | undefined,
): boolean => Boolean(toolCallId && result?.toolCallId === toolCallId);

const deliveredToolCallIds = (event: TurnEndEvent): string[] => {
	const ids = new Set<string>();
	const add = (result: any) => {
		if (typeof result?.toolCallId === "string") ids.add(result.toolCallId);
	};
	add(event.message);
	if (Array.isArray(event.toolResults)) event.toolResults.forEach(add);
	return [...ids];
};

const buildIntentInstructions = (
	pending: PendingModelCompaction,
	attemptId: string,
) =>
	`${PI_VCC_MANUAL_BYPASS_MARKER}\n${JSON.stringify({
		source: "compact_context",
		reason: pending.reason,
		boundary: pending.boundary,
		resumePolicy: pending.resumePolicy,
		requestId: pending.requestId,
		attemptId,
		...(pending.preserve ? { preserve: pending.preserve } : {}),
	})}`;

const canRunPendingCompaction = (
	pending: PendingModelCompaction,
	event: TurnEndEvent,
	pendingToolResultDelivered: boolean,
) => {
	if (pending.sawSiblingTools)
		return isCompletedAssistantResponse(event.message);
	if (pendingToolResultDelivered) return true;
	return isCompletedAssistantResponse(event.message);
};

const TERMINAL_SUBTASK_TEXT =
	/\b(done|completed?|final|handoff|PR ready|branch clean|mergeable|awaiting user|blocked|stopped?|do not continue|no auto-resume)\b/i;
const ACTIVE_SUBTASK_TEXT =
	/\b(continue|next steps?|next:|remaining|active|open todos?|run-plan active|in_progress|still running)\b/i;

const shouldResumeAfterCompactContext = (
	pending: PendingModelCompaction,
): boolean => {
	if (pending.resumePolicy === "active") return true;
	if (pending.resumePolicy === "terminal") return false;
	if (
		pending.boundary === "after_test_loop" ||
		pending.boundary === "before_topic_switch" ||
		pending.boundary === "manual_recovery"
	) {
		return true;
	}

	const text = `${pending.reason}\n${pending.preserve ?? ""}`;
	if (TERMINAL_SUBTASK_TEXT.test(text)) return false;

	return ACTIVE_SUBTASK_TEXT.test(text);
};

const buildResumeMessage = (pending: PendingModelCompaction) =>
	`Pi VCC compaction completed for an active ${pending.boundary} workflow. Continue from the preserved state. ` +
	"If the preserved state says the task is complete, blocked, stopped, or awaiting user input, report that instead of doing more work.";

const continuationAuthority = (): "coordinator" | "legacy" => {
	const configured = process.env[CONTINUATION_AUTHORITY_ENV]?.trim().toLowerCase();
	if (!configured) return "coordinator";
	if (configured === "coordinator" || configured === "legacy") return configured;
	throw new Error(
		`${CONTINUATION_AUTHORITY_ENV}=${configured} is unsupported; expected coordinator or legacy`,
	);
};

const continuationAdapter = (
	initiator: ContinuationInitiator,
	outcome: ContinuationOutcome,
) => ({
	origin:
		initiator === "compact_context"
			? "compact_context"
			: initiator === "hard-backstop"
				? "hard-backstop"
				: initiator === "host-overflow"
					? "host-overflow"
					: "package-command",
	reason:
		outcome === "cancellation"
			? "cancelled"
			: outcome === "failure"
				? "failed"
				: outcome,
});

const logContinuationTransaction = (
	event: "created",
	snapshot: Record<string, any>,
	now: number,
) => {
	try {
		const epochs = snapshot.epochs as Record<string, number>;
		const record = {
			timestampEpoch: now,
			event,
			transactionId: snapshot.transactionId,
			...(snapshot.compactionId ? { compactionId: snapshot.compactionId } : {}),
			attemptId: snapshot.attemptId,
			...(snapshot.requestId ? { requestId: snapshot.requestId } : {}),
			...(snapshot.originatingRequestId
				? { originatingRequestId: snapshot.originatingRequestId }
				: {}),
			origin: snapshot.origin,
			reason: snapshot.reason,
			resumePolicy: snapshot.resumePolicy,
			state: snapshot.state,
			retryCount: snapshot.retryCount,
			retryLimit: snapshot.retryLimit,
			submissionCount: snapshot.submissionCount,
			elapsedMs: Math.max(0, now - snapshot.createdAt),
			deadlineAt: snapshot.deadlineAt,
			pendingToolCount: snapshot.pendingToolCount,
			sessionEpoch: epochs.session,
			inputEpoch: epochs.input,
			agentEpoch: epochs.agent,
			turnEpoch: epochs.turn,
			messageEpoch: epochs.message,
			settlementEpoch: epochs.settlement,
		};
		const logPath = getPiVccLogPath();
		mkdirSync(dirname(logPath), { recursive: true });
		appendFileSync(logPath, `${JSON.stringify(record)}\n`);
	} catch {}
};

const publishContinuationRequest = (
	pi: ExtensionAPI,
	options: {
		initiator: ContinuationInitiator;
		outcome: ContinuationOutcome;
		attemptId: string;
		requestId?: string;
		originatingRequestId?: string;
		resumePolicy: ResumePolicy;
		pendingToolCount: number;
		transactionId?: string;
		epochs?: Partial<{
			session: number;
			input: number;
			agent: number;
			turn: number;
			message: number;
			settlement: number;
		}>;
	},
) => {
	const createdAt = Date.now();
	const transactionId =
		options.transactionId ??
		`vcc-${createdAt.toString(36)}-${options.attemptId}`;
	const adapted = continuationAdapter(options.initiator, options.outcome);
	const snapshot = {
		protocol: CONTINUATION_PROTOCOL_NAME,
		version: CONTINUATION_PROTOCOL_VERSION,
		transactionId,
		origin: adapted.origin,
		reason: adapted.reason,
		attemptId: options.attemptId,
		...(options.requestId ? { requestId: options.requestId } : {}),
		...(options.originatingRequestId
			? { originatingRequestId: options.originatingRequestId }
			: {}),
		resumePolicy: options.resumePolicy,
		state: "created",
		createdAt,
		queuedAt: createdAt,
		deadlineAt: createdAt + CONTINUATION_DEADLINE_MS,
		phaseEpoch: 0,
		pendingToolCount: options.pendingToolCount,
		submissionCount: 0,
		retryCount: 0,
		retryLimit: CONTINUATION_RETRY_LIMIT,
		epochs: {
			session: options.epochs?.session ?? 0,
			input: options.epochs?.input ?? 0,
			agent: options.epochs?.agent ?? 0,
			turn: options.epochs?.turn ?? 0,
			message: options.epochs?.message ?? 0,
			settlement: options.epochs?.settlement ?? 0,
		},
	};
	const wire = {
		protocol: CONTINUATION_PROTOCOL_NAME,
		version: CONTINUATION_PROTOCOL_VERSION,
		kind: "request",
		snapshot,
		outcomeHint: options.outcome,
	};
	pi.appendEntry(CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE, wire);
	pi.events.emit(CONTINUATION_WAKE_EVENT, {
		transactionId,
		attemptId: options.attemptId,
		requestId: options.requestId,
	});
	logContinuationTransaction("created", snapshot, createdAt);
	return { transactionId, snapshot };
};

const publishContinuationSafetyReady = (
	pi: ExtensionAPI,
	transaction: { transactionId: string; snapshot: Record<string, any> },
) => {
	const wire = {
		protocol: CONTINUATION_PROTOCOL_NAME,
		version: CONTINUATION_PROTOCOL_VERSION,
		kind: "safety-ready",
		transactionId: transaction.transactionId,
		attemptId: transaction.snapshot.attemptId,
		...(transaction.snapshot.requestId
			? { requestId: transaction.snapshot.requestId }
			: {}),
	};
	pi.appendEntry(CONTINUATION_SAFETY_READY_ENTRY_CUSTOM_TYPE, wire);
	pi.events.emit(CONTINUATION_SAFETY_READY_WAKE_EVENT, {
		transactionId: transaction.transactionId,
		attemptId: transaction.snapshot.attemptId,
		requestId: transaction.snapshot.requestId,
	});
};

export default function (pi: ExtensionAPI) {
	let runtimeActive = true;
	const ignoreStaleContextCallback = (
		operation: string,
		callback: () => void,
	): void => {
		try {
			callback();
		} catch (err) {
			if (!isStaleExtensionContextError(err)) throw err;
			logPiVccEvent("stale_context_callback_ignored", { operation });
		}
	};
	let compactionInFlight = false;
	let lastAutoCompactionPercent: number | undefined;
	let lastNudgePercentBand: NudgeBand | undefined;
	let lastNudgeTurn: number | undefined;
	let pendingModelCompaction: PendingModelCompaction | undefined;
	let currentContinuationTransaction:
		| { transactionId: string; snapshot: Record<string, any> }
		| undefined;
	let currentContinuationPendingToolCallIds = new Set<string>();
	const safetyReadyTransactions = new Set<string>();
	const continuationEpochs = {
		session: 0,
		input: 0,
		agent: 0,
		turn: 0,
		message: 0,
		settlement: 0,
	};
	let lastFailureTurn: number | undefined;
	let lastCompactionReason = "none";
	let uninterpretedFailure = false;
	let awaitingPostCompactionAssistantResponse = false;
	let turnCounter = 0;
	let lastToolBatchId = 0;
	let lastAssistantToolCallCount = 0;
	const observedAssistantToolMessageSignatures = new WeakMap<object, string>();
	let outstandingAssistantToolCallIds = new Set<string>();
	let userMessageCount = 0;
	let pendingNoCutContinuation: PendingNoCutContinuation | undefined;
	let noCutRetryState: NoCutRetryState | undefined;
	let activeCompactionOwner: CompactionOwner;
	let scheduledPiVccCompaction: ReturnType<typeof setTimeout> | undefined;
	let nextCompactionAttemptId = 0;
	let currentCompactionAttemptId: number | undefined;
	let pendingCompactionContinuation: PendingCompactionContinuation | undefined;
	let deliveredCompactionContinuationAttemptId: number | undefined;
	let activeModelProvider: string | undefined;
	let activeModelId: string | undefined;
	let lastGrokAutoCompactionTokens: number | undefined;

	const activeGrokIdentity = () => ({
		provider: activeModelProvider ?? undefined,
		modelId: activeModelId ?? undefined,
	});

	const isActiveGrokModel = (ctx: ExtensionContext) =>
		isGrokContextCeilingModel(activeGrokIdentity()) ||
		isGrokContextCeilingModel({
			provider: (ctx.model as { provider?: string } | undefined)?.provider,
			modelId: ctx.model?.id,
		});

	const resolveGrokUsageTokens = (usage: {
		percent: number;
		contextWindow: number;
		tokens?: number;
	}) =>
		usage.tokens ?? Math.round((usage.percent / 100) * usage.contextWindow);

	const isStaleGrokAutoCompactionTokens = (
		tokens: number,
		lastTokens: number | undefined,
	) => lastTokens !== undefined && tokens === lastTokens;

	const resetGrokLatchState = () => {
		lastGrokAutoCompactionTokens = undefined;
		lastAutoCompactionPercent = undefined;
		lastNudgePercentBand = undefined;
		noCutRetryState = undefined;
	};

	const syncActiveModel = (model: { provider?: string; id?: string } | undefined) => {
		const nextProvider = model?.provider;
		const nextModelId = model?.id;
		if (
			nextProvider === activeModelProvider &&
			nextModelId === activeModelId
		) {
			return;
		}
		activeModelProvider = nextProvider;
		activeModelId = nextModelId;
		resetGrokLatchState();
	};

	const clearPendingNoCutContinuation = () => {
		if (pendingNoCutContinuation?.timer)
			clearTimeout(pendingNoCutContinuation.timer);
		pendingNoCutContinuation = undefined;
	};

	const clearPendingCompactionContinuation = () => {
		if (pendingCompactionContinuation?.timer)
			clearTimeout(pendingCompactionContinuation.timer);
		pendingCompactionContinuation = undefined;
	};

	const finishCompaction = (
		options: {
			compacted?: boolean;
			originatingRequestId?: string;
			clearPending?: boolean;
		} = {},
	) => {
		compactionInFlight = false;
		activeCompactionOwner = undefined;
		currentCompactionAttemptId = undefined;
		if (
			options.clearPending ||
			(options.originatingRequestId &&
				pendingModelCompaction?.requestId === options.originatingRequestId)
		) {
			pendingModelCompaction = undefined;
		}
		lastNudgePercentBand = undefined;
		if (scheduledPiVccCompaction) {
			clearTimeout(scheduledPiVccCompaction);
			scheduledPiVccCompaction = undefined;
		}
		if (options.compacted) awaitingPostCompactionAssistantResponse = true;
	};

	const buildNoCutContinuationMessage = (pending: PendingNoCutContinuation) =>
		`Pi VCC hard-backstop compaction was skipped because no safe compaction cut was available (${pending.reason}). ` +
		"Continue from where you left off; do not summarize this recovery message unless it changes the task state.";

	const sendPendingNoCutContinuation = (ctx: ExtensionContext) => {
		if (!runtimeActive) return;
		const pending = pendingNoCutContinuation;
		if (!pending) return;
		if (!pending.startedAt) pending.startedAt = Date.now();
		pending.attempts += 1;
		try {
			pi.sendMessage(
				{
					customType: "pi-vcc-no-cut-continuation",
					content: buildNoCutContinuationMessage(pending),
					display: true,
					details: {
						reason: pending.reason,
						usagePercent: pending.usagePercent,
						flooredPercent: pending.flooredPercent,
						queuedTurn: pending.queuedTurn,
						deliveryAttempts: pending.attempts,
						pendingToolCount: pending.pendingToolCallIds.size,
					},
				},
				{ deliverAs: "steer", triggerTurn: true },
			);
			if (pending.timer) clearTimeout(pending.timer);
			pendingNoCutContinuation = undefined;
		} catch (err) {
			if (isStaleExtensionContextError(err)) {
				if (pending.timer) clearTimeout(pending.timer);
				pendingNoCutContinuation = undefined;
				logPiVccEvent("stale_context_callback_ignored", {
					operation: "no_cut_continuation_delivery",
				});
				return;
			}
			pending.lastError = (err as Error).message;
			const elapsed = Date.now() - pending.startedAt;
			if (elapsed < NO_CUT_CONTINUATION_MAX_WAIT_MS) {
				if (pending.timer) clearTimeout(pending.timer);
				pending.timer = setTimeout(
					() => sendPendingNoCutContinuation(ctx),
					NO_CUT_CONTINUATION_RETRY_MS,
				);
				return;
			}
			if (pending.timer) clearTimeout(pending.timer);
			logPiVccEvent("no_cut_continuation_delivery_failed", {
				reason: pending.reason,
				usagePercent: pending.usagePercent,
				flooredPercent: pending.flooredPercent,
				attempts: pending.attempts,
				lastError: pending.lastError,
				pendingToolCount: pending.pendingToolCallIds.size,
			});
			ctx.ui.notify(
				`No-cut continuation delivery failed after ${pending.attempts} attempts: ${pending.lastError}. Continue manually from the interrupted turn. Logged to ${getPiVccLogPath()}.`,
				"warning",
			);
			pendingNoCutContinuation = undefined;
		}
	};

	const queueNoCutContinuation = (
		ctx: ExtensionContext,
		reason: PendingNoCutContinuation["reason"],
		recovery: NoCutRecoveryOptions,
	) => {
		if (
			!runtimeActive ||
			!recovery.interruptedActiveTurn ||
			pendingNoCutContinuation
		)
			return;
		pendingNoCutContinuation = {
			reason,
			usagePercent: recovery.usagePercent,
			flooredPercent:
				recovery.usagePercent === undefined
					? undefined
					: Math.floor(recovery.usagePercent),
			pendingToolCallIds: new Set(recovery.pendingToolCallIds()),
			queuedTurn: turnCounter,
			attempts: 0,
		};
		if (pendingNoCutContinuation.pendingToolCallIds.size === 0) {
			pendingNoCutContinuation.timer = setTimeout(
				() => sendPendingNoCutContinuation(ctx),
				NO_CUT_CONTINUATION_DELAY_MS,
			);
		}
	};

	const clearDeliveredNoCutTools = (event: TurnEndEvent) => {
		if (!pendingNoCutContinuation) return;
		for (const id of deliveredToolCallIds(event))
			pendingNoCutContinuation.pendingToolCallIds.delete(id);
	};

	const noCutContinuationIsSafe = (event: TurnEndEvent) =>
		Boolean(pendingNoCutContinuation) &&
		(pendingNoCutContinuation.pendingToolCallIds.size === 0 ||
			isCompletedAssistantResponse(event.message));

	const buildCompactionContinuationMessage = (
		pending: PendingCompactionContinuation,
	) =>
		`Pi-vcc compaction did not complete cleanly (${pending.reason}), but the interrupted turn should continue. ` +
		"Continue from where you left off; use vcc_recall if needed.";

	const sendPendingCompactionContinuation = (ctx: ExtensionContext) => {
		if (!runtimeActive) return;
		const pending = pendingCompactionContinuation;
		if (!pending) return;
		if (!pending.startedAt) pending.startedAt = Date.now();
		pending.attempts += 1;
		try {
			pi.sendMessage(
				{
					customType: "pi-vcc-continuation",
					content: buildCompactionContinuationMessage(pending),
					display: false,
					details: {
						compactor: "pi-vcc",
						reason: pending.reason,
						attemptId: pending.attemptId,
						interruptedReason: pending.interrupted.reason,
						queuedTurn: pending.queuedTurn,
						deliveryAttempts: pending.attempts,
						pendingToolCount: pending.interrupted.pendingToolCallIds.size,
					},
				},
				{ deliverAs: "steer", triggerTurn: true },
			);
			if (pending.timer) clearTimeout(pending.timer);
			deliveredCompactionContinuationAttemptId = pending.attemptId;
			pendingCompactionContinuation = undefined;
		} catch (err) {
			if (isStaleExtensionContextError(err)) {
				if (pending.timer) clearTimeout(pending.timer);
				pendingCompactionContinuation = undefined;
				logPiVccEvent("stale_context_callback_ignored", {
					operation: "compaction_continuation_delivery",
				});
				return;
			}
			pending.lastError = (err as Error).message;
			const elapsed = Date.now() - pending.startedAt;
			if (elapsed < COMPACTION_CONTINUATION_MAX_WAIT_MS) {
				if (pending.timer) clearTimeout(pending.timer);
				pending.timer = setTimeout(
					() => sendPendingCompactionContinuation(ctx),
					COMPACTION_CONTINUATION_RETRY_MS,
				);
				return;
			}
			if (pending.timer) clearTimeout(pending.timer);
			logPiVccEvent("compaction_continuation_delivery_failed", {
				attemptId: pending.attemptId,
				reason: pending.reason,
				interruptedReason: pending.interrupted.reason,
				attempts: pending.attempts,
				lastError: pending.lastError,
				pendingToolCount: pending.interrupted.pendingToolCallIds.size,
			});
			ctx.ui.notify(
				`Compaction continuation delivery failed after ${pending.attempts} attempts: ${pending.lastError}. Continue manually from the interrupted turn. Logged to ${getPiVccLogPath()}.`,
				"warning",
			);
			pendingCompactionContinuation = undefined;
		}
	};

	const queueCompactionContinuation = (
		ctx: ExtensionContext,
		attemptId: number,
		reason: PendingCompactionContinuation["reason"],
		interrupted: InterruptedCompactionTurn | undefined,
	) => {
		if (!runtimeActive || !interrupted?.interrupted) return;
		if (deliveredCompactionContinuationAttemptId === attemptId) return;
		if (pendingCompactionContinuation?.attemptId === attemptId) return;
		pendingCompactionContinuation = {
			attemptId,
			reason,
			interrupted,
			queuedTurn: turnCounter,
			attempts: 0,
		};
		if (interrupted.pendingToolCallIds.size === 0) {
			pendingCompactionContinuation.timer = setTimeout(
				() => sendPendingCompactionContinuation(ctx),
				COMPACTION_CONTINUATION_DELAY_MS,
			);
		}
	};

	const clearDeliveredCompactionContinuationTools = (event: TurnEndEvent) => {
		if (!pendingCompactionContinuation) return;
		for (const id of deliveredToolCallIds(event))
			pendingCompactionContinuation.interrupted.pendingToolCallIds.delete(id);
	};

	const compactionContinuationIsSafe = (event: TurnEndEvent) =>
		Boolean(pendingCompactionContinuation) &&
		(pendingCompactionContinuation.interrupted.pendingToolCallIds.size === 0 ||
			isCompletedAssistantResponse(event.message));

	const snapshotInterruptedCompactionTurn = (
		event: TurnEndEvent,
		reason: InterruptedCompactionTurn["reason"],
		ctx: ExtensionContext,
	): InterruptedCompactionTurn => {
		const completedResponse = isCompletedAssistantResponse(event.message);
		const overflowRetry =
			isContextOverflowResponse(event.message, ctx) &&
			overflowRequiresRetry(event.message);
		return {
			interrupted:
				overflowRetry ||
				(!completedResponse && isInterruptedAgentWork(event.message)),
			pendingToolCallIds: new Set(
				completedResponse && !overflowRetry
					? []
					: [...outstandingAssistantToolCallIds],
			),
			reason,
		};
	};

	const publishRequest = (
		options: Parameters<typeof publishContinuationRequest>[1],
	) =>
		publishContinuationRequest(pi, { ...options, epochs: continuationEpochs });

	const rememberCurrentTransaction = (
		transaction: { transactionId: string; snapshot: Record<string, any> },
		pendingToolCallIds: Iterable<string> = [],
	) => {
		currentContinuationTransaction = transaction;
		currentContinuationPendingToolCallIds = new Set(pendingToolCallIds);
		return transaction;
	};

	const publishSafetyReadyIfMatched = () => {
		const transaction = currentContinuationTransaction;
		if (!transaction || safetyReadyTransactions.has(transaction.transactionId))
			return;
		if (currentContinuationPendingToolCallIds.size > 0) return;
		publishContinuationSafetyReady(pi, transaction);
		safetyReadyTransactions.add(transaction.transactionId);
	};

	const publishTerminalCommandRequest = (
		options: Parameters<typeof publishContinuationRequest>[1],
	) => rememberCurrentTransaction(publishRequest(options));

	const triggerCompaction = (
		ctx: ExtensionContext,
		options: {
			customInstructions?: string;
			startMessage: string;
			completionMessage: string;
			ratchetPercent?: number;
			reason: string;
			resumeMessage?: string;
			noCutRecovery?: NoCutRecoveryOptions;
			interruptedTurn?: InterruptedCompactionTurn;
			initiator: ContinuationInitiator;
			resumePolicy: ResumePolicy;
			originatingRequestId?: string;
		},
	) => {
		if (compactionInFlight) return false;
		if (!isPiVccLoaded()) {
			notifyMissingPiVcc(ctx);
			return false;
		}

		if (continuationAuthority() === "legacy") {
			clearPendingNoCutContinuation();
			clearPendingCompactionContinuation();
		}
		compactionInFlight = true;
		activeCompactionOwner = "pi-vcc";
		const attemptId = ++nextCompactionAttemptId;
		currentContinuationTransaction = undefined;
		currentContinuationPendingToolCallIds.clear();
		currentCompactionAttemptId = attemptId;
		deliveredCompactionContinuationAttemptId = undefined;
		lastCompactionReason = options.reason;
		ctx.ui.notify(options.startMessage, "info");
		ctx.compact({
			customInstructions: options.customInstructions,
			onComplete: () =>
				ignoreStaleContextCallback("compaction_complete", () => {
				if (!runtimeActive || currentCompactionAttemptId !== attemptId) return;
				if (options.ratchetPercent !== undefined)
					lastAutoCompactionPercent = options.ratchetPercent;
				noCutRetryState = undefined;
				finishCompaction({
					compacted: true,
					originatingRequestId: options.originatingRequestId,
				});
				ctx.ui.notify(options.completionMessage, "info");
				if (options.resumePolicy !== "terminal" && options.resumeMessage) {
					if (continuationAuthority() === "legacy") {
						try {
							pi.sendMessage(
								{
									customType: "compaction-resume",
									content: options.resumeMessage,
									display: true,
									details: { reason: options.reason },
								},
								{ deliverAs: "followUp", triggerTurn: true },
							);
						} catch (err) {
							logPiVccError("post_compaction_resume_delivery_failed", err, {
								reason: options.reason,
								attemptId,
							});
							ctx.ui.notify(
								`Post-compaction resume delivery failed: ${(err as Error).message}. Logged to ${getPiVccLogPath()}.`,
								"warning",
							);
						}
					} else {
						rememberCurrentTransaction(
							publishRequest({
								initiator: options.initiator,
								outcome: "compacted",
								attemptId: String(attemptId),
								requestId: options.originatingRequestId,
								originatingRequestId: options.originatingRequestId,
								resumePolicy: options.resumePolicy,
								pendingToolCount:
									options.interruptedTurn?.pendingToolCallIds.size ?? 0,
							}),
							options.interruptedTurn?.pendingToolCallIds,
						);
						publishSafetyReadyIfMatched();
					}
				}
			}),
			onError: (err: Error) =>
				ignoreStaleContextCallback("compaction_error", () => {
				if (!runtimeActive) return;
				const ownsCurrentAttempt = currentCompactionAttemptId === attemptId;
				const noCutReason =
					err.message === "Already compacted"
						? "already_compacted"
						: err.message === "Nothing to compact (session too small)"
							? "session_too_small"
							: undefined;
				if (noCutReason) {
					if (!ownsCurrentAttempt) return;
					if (options.ratchetPercent !== undefined) {
						lastAutoCompactionPercent = options.ratchetPercent;
						noCutRetryState = {
							flooredPercent: Math.floor(options.ratchetPercent),
							usagePercent: options.ratchetPercent,
							userMessageCount,
							reason: noCutReason,
						};
					}
					awaitingPostCompactionAssistantResponse = false;
				}
				if (ownsCurrentAttempt)
					finishCompaction({
						originatingRequestId: options.originatingRequestId,
					});
				if (
					options.resumePolicy === "terminal" &&
					continuationAuthority() === "coordinator"
				) {
					publishTerminalCommandRequest({
						initiator: options.initiator,
						outcome: noCutReason
							? "no-safe-cut"
							: err.message === "Compaction cancelled"
								? "cancellation"
								: "failure",
						attemptId: String(attemptId),
						requestId: options.originatingRequestId,
						originatingRequestId: options.originatingRequestId,
						resumePolicy: "terminal",
						pendingToolCount: 0,
					});
				}
				if (noCutReason) {
					ctx.ui.notify(
						"No safe compaction cut available; continuing session.",
						"info",
					);
					if (options.noCutRecovery && continuationAuthority() === "legacy") {
						queueNoCutContinuation(ctx, noCutReason, options.noCutRecovery);
					} else if (
						continuationAuthority() === "coordinator" &&
						options.resumePolicy !== "terminal" &&
						options.interruptedTurn?.interrupted
					) {
						rememberCurrentTransaction(
							publishRequest({
								initiator: options.initiator,
								outcome: "no-safe-cut",
								attemptId: String(attemptId),
								requestId: options.originatingRequestId,
								originatingRequestId: options.originatingRequestId,
								resumePolicy: options.resumePolicy,
								pendingToolCount:
									options.interruptedTurn.pendingToolCallIds.size,
							}),
							options.interruptedTurn.pendingToolCallIds,
						);
						publishSafetyReadyIfMatched();
					}
				} else {
					if (!ownsCurrentAttempt) return;
					if (options.ratchetPercent !== undefined)
						lastAutoCompactionPercent = options.ratchetPercent;
					const reason =
						err.message === "Compaction cancelled" ? "cancelled" : "failed";
					logPiVccError("compaction_failed", err, {
						reason: options.reason,
						attemptId,
						compactionErrorReason: reason,
						interruptedTurn: options.interruptedTurn
							? {
									interrupted: options.interruptedTurn.interrupted,
									reason: options.interruptedTurn.reason,
									pendingToolCount:
										options.interruptedTurn.pendingToolCallIds.size,
								}
							: undefined,
						usagePercent: options.ratchetPercent,
					});
					ctx.ui.notify(
						`Compaction failed: ${err.message}; continuing interrupted turn if needed. Logged to ${getPiVccLogPath()}.`,
						"warning",
					);
					if (continuationAuthority() === "legacy")
						queueCompactionContinuation(
							ctx,
							attemptId,
							reason,
							options.interruptedTurn,
						);
					else if (
						options.resumePolicy !== "terminal" &&
						options.interruptedTurn?.interrupted
					) {
						rememberCurrentTransaction(
							publishRequest({
								initiator: options.initiator,
								outcome: reason === "cancelled" ? "cancellation" : "failure",
								attemptId: String(attemptId),
								requestId: options.originatingRequestId,
								originatingRequestId: options.originatingRequestId,
								resumePolicy: options.resumePolicy,
								pendingToolCount:
									options.interruptedTurn.pendingToolCallIds.size,
							}),
							options.interruptedTurn.pendingToolCallIds,
						);
						publishSafetyReadyIfMatched();
					}
				}
			}),
		});
		return true;
	};

	const schedulePiVccCompaction = (
		ctx: ExtensionContext,
		options: Parameters<typeof triggerCompaction>[1],
	) => {
		if (compactionInFlight || scheduledPiVccCompaction || activeCompactionOwner)
			return false;
		activeCompactionOwner = "pi-vcc";
		scheduledPiVccCompaction = setTimeout(() => {
			ignoreStaleContextCallback("scheduled_compaction", () => {
				scheduledPiVccCompaction = undefined;
				if (!runtimeActive) {
					activeCompactionOwner = undefined;
					return;
				}
				if (compactionInFlight) return;
				if (activeCompactionOwner !== "pi-vcc") {
					activeCompactionOwner = undefined;
					return;
				}
				const started = triggerCompaction(ctx, options);
				if (!started) activeCompactionOwner = undefined;
			});
		}, 0);
		return true;
	};

	const sendModelNudge = (
		ctx: ExtensionContext,
		usagePercent: number,
		band: NudgeBand,
	) => {
		if (lastNudgePercentBand === band) return;
		if (
			lastFailureTurn !== undefined &&
			turnCounter - lastFailureTurn <= FAILURE_DELAY_TURNS
		)
			return;

		const currentPercent = Math.floor(usagePercent);
		const content =
			band === "strong"
				? `Context is at ${currentPercent}% (strong nudge band ${COMPACTION_STRONG_NUDGE_PERCENT}-${HARD_AUTO_COMPACTION_PERCENT - 1}%). compact_context is available when you reach a safe semantic boundary. 60%/75% are nudges only, not instructions to compact immediately; ${HARD_AUTO_COMPACTION_PERCENT}% is the hard automatic backstop.`
				: `Context is at ${currentPercent}% (soft nudge band ${COMPACTION_NUDGE_PERCENT}-${COMPACTION_STRONG_NUDGE_PERCENT - 1}%). compact_context is available after a subtask resolves, before switching topics, or after a test/debug loop has been interpreted. This is not an instruction to compact immediately; ${HARD_AUTO_COMPACTION_PERCENT}% is the hard automatic backstop.`;

		try {
			pi.sendMessage(
				{
					customType: "compaction-nudge",
					content,
					display: true,
					details: {
						usagePercent,
						band,
						hardBackstopPercent: HARD_AUTO_COMPACTION_PERCENT,
					},
				},
				{ deliverAs: "steer", triggerTurn: true },
			);
			lastNudgePercentBand = band;
			lastNudgeTurn = turnCounter;
			ctx.ui.notify(content, band === "strong" ? "warning" : "info");
		} catch (err) {
			logPiVccError("compaction_nudge_delivery_failed", err, {
				usagePercent,
				band,
			});
			ctx.ui.notify(
				`Compaction nudge delivery failed; will retry next turn: ${(err as Error).message}. Logged to ${getPiVccLogPath()}.`,
				"warning",
			);
		}
	};

	pi.registerTool({
		name: "compact_context",
		label: "Compact Context",
		description:
			"Queue pi-vcc semantic-boundary compaction after the current tool result is delivered safely.",
		promptSnippet: "Queue semantic-boundary context compaction with pi-vcc",
		promptGuidelines: [
			"Use compact_context after a subtask resolves, before switching topics, after a test/debug loop has been interpreted, or when context is becoming noisy.",
			"Do not use compact_context mid-tool-chain, mid-derivation, immediately after fresh failure output, or while critical raw evidence has not been summarized.",
		],
		parameters: {
			type: "object",
			required: ["reason", "boundary"],
			properties: {
				reason: { type: "string", description: "Short reason for compaction" },
				preserve: {
					type: "string",
					description: "Optional short instructions for facts to preserve",
				},
				boundary: {
					type: "string",
					enum: [
						"subtask_complete",
						"before_topic_switch",
						"after_test_loop",
						"manual_recovery",
					],
				},
				resumePolicy: {
					type: "string",
					enum: ["active", "terminal", "auto"],
					description:
						"Whether successful compaction should resume active work; defaults to auto",
				},
			},
		},
		async execute(toolCallId: string, params: any) {
			const reason = clampText(params.reason, 240) ?? "semantic boundary";
			const boundary = params.boundary as Boundary;
			const preserve = clampText(params.preserve, 500);
			const resumePolicy = (params.resumePolicy ?? "auto") as ResumePolicy;
			const requestId = `compact-context-${Date.now().toString(36)}-${toolCallId}`;
			const observedBatchContainsTool =
				outstandingAssistantToolCallIds.has(toolCallId);
			pendingModelCompaction = {
				requestId,
				reason,
				boundary,
				resumePolicy,
				preserve,
				toolCallId,
				requestedTurn: turnCounter,
				toolBatchId: observedBatchContainsTool
					? lastToolBatchId
					: undefined,
				sawSiblingTools:
					observedBatchContainsTool && lastAssistantToolCallCount > 1,
			};
			const willResume = shouldResumeAfterCompactContext(
				pendingModelCompaction,
			);
			return {
				content: [
					{
						type: "text",
						text: willResume
							? "compact_context queued. Compaction will run after the current tool batch reaches a safe boundary, then nudge this active workflow to continue."
							: "compact_context queued. Compaction will run after the current tool batch reaches a safe boundary. No auto-resume requested.",
					},
				],
				details: { ...pendingModelCompaction, willResume },
			};
		},
	});

	pi.registerCommand("compact-now", {
		description:
			"Trigger compaction immediately with optional custom instructions",
		handler: async (args, ctx: ExtensionContext) => {
			const customInstructions = args.trim();
			const usage = ctx.getContextUsage();
			triggerCompaction(ctx, {
				initiator: "package-compact-now",
				resumePolicy: "terminal",
				customInstructions: `${PI_VCC_MANUAL_BYPASS_MARKER}\n${JSON.stringify({
				source: "package-compact-now",
				attemptId: `compact-now-${nextCompactionAttemptId + 1}`,
				transactionId: `vcc-command-compact-now-${nextCompactionAttemptId + 1}`,
				resumePolicy: "terminal",
				...(customInstructions ? { preserve: customInstructions } : {}),
			})}`,
				startMessage: "Compacting context...",
				completionMessage: "Compaction complete",
				ratchetPercent: usage?.percent ?? undefined,
				reason: "manual",
			});
		},
	});

	pi.registerCommand("compact-status", {
		description: "Show current context usage and semantic compaction status",
		handler: async (_args, ctx: ExtensionContext) => {
			const usage = ctx.getContextUsage();
			if (!usage || usage.percent === null) {
				ctx.ui.notify("Context usage: unknown", "warning");
				return;
			}
			if (isActiveGrokModel(ctx)) {
				const tokens = resolveGrokUsageTokens(usage);
				ctx.ui.notify(
					`Context: ${tokens.toLocaleString()} / ${GROK_ADVERTISED_CONTEXT_WINDOW.toLocaleString()} tokens (${Math.floor(usage.percent)}%). ` +
						`${formatGrokThresholdStatus()}; last compaction: ${lastCompactionReason}`,
					"info",
				);
				return;
			}
			ctx.ui.notify(
				`Context: ${Math.floor(usage.percent)}% of ${usage.contextWindow.toLocaleString()} tokens ` +
					`(nudge: ${COMPACTION_NUDGE_PERCENT}%, strong: ${COMPACTION_STRONG_NUDGE_PERCENT}%, hard auto: ${HARD_AUTO_COMPACTION_PERCENT}%, ` +
					`last nudge: ${lastNudgePercentBand ?? "none"}${lastNudgeTurn !== undefined ? `@turn ${lastNudgeTurn}` : ""}, last compaction: ${lastCompactionReason})`,
				"info",
			);
		},
	});

	pi.on("model_select", async (event: ModelSelectEvent) => {
		syncActiveModel(event.model);
	});

	const observeAssistantToolBatch = (message: any) => {
		if (
			message?.role !== "assistant" ||
			message?.stopReason !== "toolUse"
		)
			return;

		const toolCallIds = assistantToolCallIds(message);
		const signature = toolCallIds.join("\u0000");
		if (observedAssistantToolMessageSignatures.get(message) === signature) return;
		observedAssistantToolMessageSignatures.set(message, signature);
		lastToolBatchId += 1;
		lastAssistantToolCallCount = toolCallCount(message);
		outstandingAssistantToolCallIds = new Set(toolCallIds);
		if (
			pendingModelCompaction &&
			assistantToolBatchIncludes(message, pendingModelCompaction.toolCallId)
		) {
			pendingModelCompaction.toolBatchId = lastToolBatchId;
			pendingModelCompaction.sawSiblingTools =
				lastAssistantToolCallCount > 1;
		}
	};

	pi.on("turn_end", async (event: TurnEndEvent, ctx: ExtensionContext) => {
		turnCounter += 1;

		const completedResponse = isCompletedAssistantResponse(event.message);
		const turnToolResults = Array.isArray(event.toolResults)
			? event.toolResults
			: [];
		const pendingToolResultDelivered = Boolean(
			pendingModelCompaction?.toolCallId &&
				(toolResultMatches(event.message, pendingModelCompaction.toolCallId) ||
					turnToolResults.some((result: any) =>
						toolResultMatches(result, pendingModelCompaction?.toolCallId),
					)),
		);

		observeAssistantToolBatch(event.message);
		if (
			hasFailureOutput(event.message) ||
			turnToolResults.some(hasFailureOutput)
		) {
			lastFailureTurn = turnCounter;
			uninterpretedFailure = true;
		} else if (completedResponse) {
			uninterpretedFailure = false;
		}

		const usage = ctx.getContextUsage();
		const usagePercent = usage?.percent ?? undefined;

		const deliveredIds = deliveredToolCallIds(event);
		for (const id of deliveredIds) {
			outstandingAssistantToolCallIds.delete(id);
			currentContinuationPendingToolCallIds.delete(id);
		}
		if (completedResponse) {
			outstandingAssistantToolCallIds.clear();
			currentContinuationPendingToolCallIds.clear();
		}
		publishSafetyReadyIfMatched();
		if (continuationAuthority() === "legacy") {
			clearDeliveredNoCutTools(event);
			clearDeliveredCompactionContinuationTools(event);
			if (noCutContinuationIsSafe(event)) sendPendingNoCutContinuation(ctx);
			if (compactionContinuationIsSafe(event))
				sendPendingCompactionContinuation(ctx);
			if (pendingCompactionContinuation) return;
		}

		if (compactionInFlight || scheduledPiVccCompaction) return;

		if (awaitingPostCompactionAssistantResponse) {
			if (!isUsablePostCompactionAssistantResponse(event.message)) return;
			awaitingPostCompactionAssistantResponse = false;
		}

		if (
			pendingModelCompaction &&
			canRunPendingCompaction(
				pendingModelCompaction,
				event,
				pendingToolResultDelivered,
			)
		) {
			const pending = pendingModelCompaction;
			if (!uninterpretedFailure || pending.boundary === "manual_recovery") {
				const attemptToken = `compact-context-${nextCompactionAttemptId + 1}`;
				triggerCompaction(ctx, {
					initiator: "compact_context",
					resumePolicy: pending.resumePolicy,
					originatingRequestId: pending.requestId,
					customInstructions: buildIntentInstructions(pending, attemptToken),
					startMessage: `✓ Compacting at semantic boundary: ${pending.boundary}`,
					completionMessage: "Compacted with pi-vcc",
					ratchetPercent: usagePercent ?? undefined,
					reason: "compact_context",
					resumeMessage: shouldResumeAfterCompactContext(pending)
						? buildResumeMessage(pending)
						: undefined,
					interruptedTurn: snapshotInterruptedCompactionTurn(
						event,
						"compact_context",
						ctx,
					),
				});
				return;
			}
		}

		if (usagePercent === undefined || usagePercent === null) return;

		const currentPercent = Math.floor(usagePercent);

		if (isActiveGrokModel(ctx)) {
			const grokUsage = usage;
			if (!grokUsage) return;
			const tokens = resolveGrokUsageTokens(grokUsage);
			const grokResetTokens = Math.floor(
				(COMPACTION_NUDGE_PERCENT / 100) * GROK_ADVERTISED_CONTEXT_WINDOW,
			);

			if (tokens < grokResetTokens) {
				lastGrokAutoCompactionTokens = undefined;
				lastAutoCompactionPercent = undefined;
				lastNudgePercentBand = undefined;
				awaitingPostCompactionAssistantResponse = false;
				noCutRetryState = undefined;
				return;
			}

			if (grokCompactionTriggerReached(tokens)) {
				if (
					isStaleGrokAutoCompactionTokens(
						tokens,
						lastGrokAutoCompactionTokens,
					) &&
					(!noCutRetryState ||
						userMessageCount === noCutRetryState.userMessageCount)
				)
					return;
				if (
					noCutRetryState &&
					currentPercent <= noCutRetryState.flooredPercent &&
					userMessageCount === noCutRetryState.userMessageCount
				) {
					return;
				}
				const started = triggerCompaction(ctx, {
					initiator: "hard-backstop",
					resumePolicy: "active",
					startMessage: completedResponse
						? `✓ Auto-compacting Grok context at ${tokens.toLocaleString()} tokens (trigger: ${GROK_COMPACTION_TRIGGER_TOKENS.toLocaleString()})`
						: `↻ Grok context at ${tokens.toLocaleString()} tokens (trigger: ${GROK_COMPACTION_TRIGGER_TOKENS.toLocaleString()}). Interrupting agent for pi-vcc compaction...`,
					completionMessage: "Compacted with pi-vcc",
					resumeMessage:
						isContextOverflowResponse(event.message, ctx) &&
						overflowRequiresRetry(event.message)
							? buildOverflowResumeMessage()
							: undefined,
					ratchetPercent: usagePercent,
					reason: "grok_context_ceiling",
					interruptedTurn: snapshotInterruptedCompactionTurn(
						event,
						"hard_backstop",
						ctx,
					),
					noCutRecovery: {
						interruptedActiveTurn: isInterruptedAgentWork(event.message),
						pendingToolCallIds: () =>
							completedResponse ? [] : [...outstandingAssistantToolCallIds],
						usagePercent,
					},
				});
				if (started) lastGrokAutoCompactionTokens = tokens;
				return;
			}

			return;
		}

		if (usagePercent < COMPACTION_NUDGE_PERCENT) {
			lastAutoCompactionPercent = undefined;
			lastNudgePercentBand = undefined;
			awaitingPostCompactionAssistantResponse = false;
			noCutRetryState = undefined;
			return;
		}

		if (usagePercent >= HARD_AUTO_COMPACTION_PERCENT) {
			if (
				isStaleAutoCompactionPercent(usagePercent, lastAutoCompactionPercent) &&
				(!noCutRetryState ||
					userMessageCount === noCutRetryState.userMessageCount)
			)
				return;
			if (
				noCutRetryState &&
				currentPercent <= noCutRetryState.flooredPercent &&
				userMessageCount === noCutRetryState.userMessageCount
			) {
				return;
			}
			schedulePiVccCompaction(ctx, {
				initiator: "hard-backstop",
				resumePolicy: "active",
				startMessage: completedResponse
					? `✓ Auto-compacting at ${currentPercent}% (hard backstop: ${HARD_AUTO_COMPACTION_PERCENT}%)`
					: `↻ Context at ${currentPercent}% (hard backstop: ${HARD_AUTO_COMPACTION_PERCENT}%). Interrupting agent for pi-vcc compaction...`,
				completionMessage: "Compacted with pi-vcc",
				resumeMessage:
					isContextOverflowResponse(event.message, ctx) &&
					overflowRequiresRetry(event.message)
						? buildOverflowResumeMessage()
						: undefined,
				ratchetPercent: usagePercent,
				reason: "hard_backstop",
				interruptedTurn: snapshotInterruptedCompactionTurn(
					event,
					"hard_backstop",
					ctx,
				),
				noCutRecovery: {
					interruptedActiveTurn: isInterruptedAgentWork(event.message),
					pendingToolCallIds: () =>
						completedResponse ? [] : [...outstandingAssistantToolCallIds],
					usagePercent,
				},
			});
			return;
		}

		if (usagePercent >= COMPACTION_STRONG_NUDGE_PERCENT) {
			sendModelNudge(ctx, usagePercent, "strong");
			return;
		}

		sendModelNudge(ctx, usagePercent, "soft");
	});

	// When Pi auto-compaction is disabled, its core overflow path is disabled too.
	// Own that recovery at agent_end so the same pi-vcc compactor handles both
	// percentage backstops and provider-reported context ceilings. If core
	// auto-compaction is still enabled, scheduling first lets session_before_compact
	// cancel the competing core overflow attempt before this timer starts.
	pi.on("agent_end", (event: AgentEndEvent, ctx: ExtensionContext) => {
		const message = [...event.messages]
			.reverse()
			.find((candidate) => candidate.role === "assistant");
		if (!message || !isContextOverflowResponse(message, ctx)) return;
		if (compactionInFlight || scheduledPiVccCompaction) return;
		if (!isPiVccLoaded()) {
			notifyMissingPiVcc(ctx);
			return;
		}

		const needsRetry = overflowRequiresRetry(message);
		const usagePercent = ctx.getContextUsage()?.percent ?? undefined;
		logPiVccEvent("host_overflow_detected", {
			stopReason: message.stopReason,
			needsRetry,
			usagePercent,
			errorMessage: message.errorMessage,
		});
		schedulePiVccCompaction(ctx, {
			initiator: "host-overflow",
			resumePolicy: "active",
			startMessage: needsRetry
				? "↻ Provider reported context overflow. Interrupting agent for pi-vcc compaction and retry..."
				: "✓ Provider response exceeded its context window. Compacting with pi-vcc...",
			completionMessage: "Compacted with pi-vcc after context overflow",
			resumeMessage: needsRetry ? buildOverflowResumeMessage() : undefined,
			ratchetPercent: usagePercent,
			reason: "overflow",
			interruptedTurn: {
				interrupted: needsRetry,
				pendingToolCallIds: new Set(),
				reason: "core_deferred",
			},
			noCutRecovery: {
				interruptedActiveTurn: needsRetry,
				pendingToolCallIds: () => [],
				usagePercent,
			},
		});
	});

	pi.on("agent_start", () => {
		continuationEpochs.agent += 1;
	});
	pi.on("turn_start", () => {
		continuationEpochs.turn += 1;
	});
	pi.on("message_start", () => {
		continuationEpochs.message += 1;
	});
	pi.on("agent_settled", () => {
		continuationEpochs.settlement += 1;
	});
	pi.on("input", (event: any) => {
		if (event?.source !== "extension") continuationEpochs.input += 1;
	});
	pi.on("session_start", () => {
		continuationEpochs.session += 1;
	});
	pi.on("message_end", async (event: any) => {
		// message_end fires after the model has declared the complete tool batch
		// but before those tools execute. Capture it here so compact_context does
		// not inherit sibling metadata from the preceding batch while waiting for
		// the later turn_end lifecycle callback.
		observeAssistantToolBatch(event?.message);
		if (
			event?.message?.role === "user" &&
			typeof event.message.customType !== "string"
		)
			userMessageCount += 1;
	});

	pi.on("session_shutdown", async () => {
		runtimeActive = false;
		clearPendingNoCutContinuation();
		clearPendingCompactionContinuation();
		if (scheduledPiVccCompaction) {
			clearTimeout(scheduledPiVccCompaction);
			scheduledPiVccCompaction = undefined;
		}
		compactionInFlight = false;
		activeCompactionOwner = undefined;
		currentCompactionAttemptId = undefined;
		pendingModelCompaction = undefined;
		currentContinuationTransaction = undefined;
		currentContinuationPendingToolCallIds.clear();
		safetyReadyTransactions.clear();
	});

	pi.on("session_compact", async () => {
		noCutRetryState = undefined;
		if (continuationAuthority() === "legacy") {
			clearPendingNoCutContinuation();
			clearPendingCompactionContinuation();
		}
		finishCompaction({ compacted: true });
	});

	pi.on(
		"session_before_compact",
		async (event: SessionBeforeCompactEvent, ctx: ExtensionContext) => {
			if (!isPiVccLoaded()) {
				notifyMissingPiVcc(ctx);
				return { cancel: true };
			}

			const rawEvent = event as { reason?: unknown; willRetry?: unknown };
			const usage = ctx.getContextUsage();
			const usagePercent = usage?.percent ?? undefined;

			const manualPiVccBypass =
				event.customInstructions?.startsWith(PI_VCC_MANUAL_BYPASS_MARKER) ??
				false;
			if (manualPiVccBypass) {
				if (!usage || usage.percent === null) return;
				ctx.ui.notify(
					`✓ Compaction bypassed ${HARD_AUTO_COMPACTION_PERCENT}% hard backstop at ${Math.floor(usage.percent)}%`,
					"info",
				);
				return;
			}

			if (pendingCompactionContinuation) {
				if (usagePercent !== undefined)
					lastAutoCompactionPercent = usagePercent;
				ctx.ui.notify(
					`⏸️ Delayed auto-compaction: waiting to continue interrupted pi-vcc attempt ${pendingCompactionContinuation.attemptId}`,
					"info",
				);
				return { cancel: true };
			}

			if (scheduledPiVccCompaction) {
				if (usagePercent !== undefined)
					lastAutoCompactionPercent = usagePercent;
				ctx.ui.notify(
					`⏸️ Delayed auto-compaction: pi-vcc already scheduled ${usagePercent == null ? "unknown-usage" : `${Math.floor(usagePercent)}%`} compaction recovery`,
					"info",
				);
				return { cancel: true };
			}

			if (!usage || usage.percent === null) return;

			if (
				(rawEvent.reason === "overflow" ||
					rawEvent.reason === "context_ceiling" ||
					rawEvent.willRetry === true) &&
				!manualPiVccBypass
			) {
				return;
			}

			if (compactionInFlight) {
				lastAutoCompactionPercent = usage.percent;
				awaitingPostCompactionAssistantResponse = true;
				lastCompactionReason = isActiveGrokModel(ctx)
					? "grok_context_ceiling"
					: "core_hard_backstop";
				if (isActiveGrokModel(ctx)) {
					const tokens = resolveGrokUsageTokens(usage);
					ctx.ui.notify(
						`✓ Auto-compacting Grok context at ${tokens.toLocaleString()} tokens (trigger: ${GROK_COMPACTION_TRIGGER_TOKENS.toLocaleString()})`,
						"info",
					);
				} else {
					ctx.ui.notify(
						`✓ Auto-compacting at ${Math.floor(usage.percent)}% (hard backstop: ${HARD_AUTO_COMPACTION_PERCENT}%)`,
						"info",
					);
				}
				return;
			}

			if (usage.percent < HARD_AUTO_COMPACTION_PERCENT) {
				if (isActiveGrokModel(ctx)) {
					const tokens = resolveGrokUsageTokens(usage);
					if (grokCompactionTriggerReached(tokens)) {
						lastAutoCompactionPercent = usage.percent;
						return;
					}
				}
				lastAutoCompactionPercent = undefined;
				ctx.ui.notify(
					`⏸️ Delayed auto-compaction: ${Math.floor(usage.percent)}% < ${HARD_AUTO_COMPACTION_PERCENT}% hard backstop`,
					"info",
				);
				return { cancel: true };
			}

			if (awaitingPostCompactionAssistantResponse) {
				lastAutoCompactionPercent = usage.percent;
				ctx.ui.notify(
					"⏸️ Delayed auto-compaction: waiting for the next assistant response after the last pi-vcc compaction",
					"info",
				);
				return { cancel: true };
			}

			if (
				isStaleAutoCompactionPercent(usage.percent, lastAutoCompactionPercent)
			) {
				lastAutoCompactionPercent = usage.percent;
				ctx.ui.notify(
					`⏸️ Delayed auto-compaction: context usage is unchanged at ${usage.percent}% since the last pi-vcc compaction`,
					"info",
				);
				return { cancel: true };
			}

			const currentPercent = Math.floor(usage.percent);
			if (
				noCutRetryState &&
				currentPercent <= noCutRetryState.flooredPercent &&
				userMessageCount === noCutRetryState.userMessageCount
			) {
				lastAutoCompactionPercent = usage.percent;
				ctx.ui.notify(
					`⏸️ Delayed auto-compaction: no safe cut was available at ${noCutRetryState.flooredPercent}%; waiting for higher usage or a new user message`,
					"info",
				);
				return { cancel: true };
			}

			lastAutoCompactionPercent = usage.percent;
			ctx.ui.notify(
				`⏸️ Delayed auto-compaction: repo-managed hard backstop handles ${Math.floor(usage.percent)}% compaction with no-cut recovery`,
				"info",
			);
			return { cancel: true };
		},
	);
}
