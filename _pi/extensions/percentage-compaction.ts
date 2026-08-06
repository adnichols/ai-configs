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
import type { ContinuationFacade } from "../packages/pi-vcc/src/core/coordinator";
import type { ContinuationAttemptOutcome, ContinuationInitiator } from "../packages/pi-vcc/src/core/continuation-protocol";
import type { CompactionResumeIntent } from "../packages/pi-vcc/src/types";
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
interface PendingModelCompaction {
	requestId: string;
	attemptId: string;
	reason: string;
	boundary: Boundary;
	resumeIntent: "active";
	preserve?: string;
	requestedTurn: number;
	toolCallId?: string;
	toolBatchId?: number;
	sawSiblingTools: boolean;
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

type CompactionOwner = "pi-vcc" | "core" | undefined;

interface NoCutRetryState {
	flooredPercent: number;
	usagePercent?: number;
	userMessageCount: number;
	reason: "already_compacted" | "session_too_small";
}

const DEFAULT_PI_VCC_LOG_PATH = join(homedir(), ".pi", "logs", "pi-vcc.jsonl");
const getPiVccLogPath = () =>
	process.env.PI_VCC_LOG_PATH?.trim() || DEFAULT_PI_VCC_LOG_PATH;
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

const buildIntentInstructions = (pending: PendingModelCompaction) =>
	`${PI_VCC_MANUAL_BYPASS_MARKER}\n${JSON.stringify({
		source: "compact_context",
		reason: pending.reason,
		boundary: pending.boundary,
		resumeIntent: pending.resumeIntent,
		requestId: pending.requestId,
		attemptId: pending.attemptId,
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

const continuationFacade = (): ContinuationFacade | undefined =>
	((globalThis as any)[PI_VCC_LOAD_MARKER] as { continuation?: ContinuationFacade } | undefined)?.continuation;

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
	let lastFailureTurn: number | undefined;
	let lastCompactionReason = "none";
	let agentGeneration = 0;
	let agentActive = false;
	let awaitingPostCompactionAssistantResponse = false;
	let turnCounter = 0;
	let lastToolBatchId = 0;
	let lastAssistantToolCallCount = 0;
	const observedAssistantToolMessageSignatures = new WeakMap<object, string>();
	let outstandingAssistantToolCallIds = new Set<string>();
	let userMessageCount = 0;
	let noCutRetryState: NoCutRetryState | undefined;
	let activeCompactionOwner: CompactionOwner;
	let scheduledPiVccCompaction: ReturnType<typeof setTimeout> | undefined;
	let nextCompactionAttemptId = 0;
	let currentCompactionAttemptId: number | undefined;
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

	const finishCompaction = (
		options: { compacted?: boolean; originatingRequestId?: string; clearPending?: boolean } = {},
	) => {
		compactionInFlight = false;
		activeCompactionOwner = undefined;
		currentCompactionAttemptId = undefined;
		if (
			options.clearPending ||
			(options.originatingRequestId && pendingModelCompaction?.requestId === options.originatingRequestId)
		) pendingModelCompaction = undefined;
		lastNudgePercentBand = undefined;
		if (scheduledPiVccCompaction) {
			clearTimeout(scheduledPiVccCompaction);
			scheduledPiVccCompaction = undefined;
		}
		if (options.compacted) awaitingPostCompactionAssistantResponse = true;
	};

	interface TriggerOptions {
		customInstructions?: string;
		startMessage: string;
		completionMessage: string;
		ratchetPercent?: number;
		reason: string;
		interruptedTurn?: InterruptedCompactionTurn;
		initiator: ContinuationInitiator;
		resumeIntent: CompactionResumeIntent;
		originatingRequestId?: string;
		attemptId?: string;
		sourceResponseComplete?: boolean;
		scheduledAgentGeneration?: number;
		resolveIntentAtStart?: boolean;
	}

	const resolvedIntentAtStart = (options: TriggerOptions): CompactionResumeIntent => {
		if (!options.resolveIntentAtStart) return options.resumeIntent;
		if (pendingModelCompaction) return "active";
		if (options.interruptedTurn?.interrupted) return "active";
		if (options.sourceResponseComplete === false) return "active";
		if (
			options.sourceResponseComplete === true &&
			options.scheduledAgentGeneration !== undefined &&
			agentGeneration > options.scheduledAgentGeneration &&
			agentActive
		) return "active";
		return "none";
	};

	const triggerCompaction = (ctx: ExtensionContext, original: TriggerOptions) => {
		if (compactionInFlight) return false;
		const continuation = continuationFacade();
		if (!isPiVccLoaded() || !continuation) {
			notifyMissingPiVcc(ctx);
			return false;
		}

		const internalAttemptId = ++nextCompactionAttemptId;
		const attemptId = original.attemptId ?? String(internalAttemptId);
		const resumeIntent = resolvedIntentAtStart(original);
		const options = { ...original, attemptId, resumeIntent };
		const customInstructions = options.customInstructions ??
			`${PI_VCC_MANUAL_BYPASS_MARKER}\n${JSON.stringify({
				source: options.initiator,
				attemptId,
				resumeIntent,
				...(options.originatingRequestId ? { requestId: options.originatingRequestId } : {}),
			})}`;

		compactionInFlight = true;
		activeCompactionOwner = "pi-vcc";
		currentCompactionAttemptId = internalAttemptId;
		lastCompactionReason = options.reason;
		ctx.ui.notify(options.startMessage, "info");
		ctx.compact({
			customInstructions,
			onComplete: () => ignoreStaleContextCallback("compaction_complete", () => {
				if (!runtimeActive || currentCompactionAttemptId !== internalAttemptId) return;
				if (options.ratchetPercent !== undefined) lastAutoCompactionPercent = options.ratchetPercent;
				noCutRetryState = undefined;
				finishCompaction({ compacted: true, originatingRequestId: options.originatingRequestId });
				ctx.ui.notify(options.completionMessage, "info");
			}),
			onError: (err: Error) => ignoreStaleContextCallback("compaction_error", () => {
				if (!runtimeActive || currentCompactionAttemptId !== internalAttemptId) return;
				const noCutReason = err.message === "Already compacted"
					? "already_compacted"
					: err.message === "Nothing to compact (session too small)"
						? "session_too_small"
						: undefined;
				if (options.ratchetPercent !== undefined) {
					lastAutoCompactionPercent = options.ratchetPercent;
					if (noCutReason) noCutRetryState = {
						flooredPercent: Math.floor(options.ratchetPercent),
						usagePercent: options.ratchetPercent,
						userMessageCount,
						reason: noCutReason,
					};
				}
				awaitingPostCompactionAssistantResponse = false;
				finishCompaction({ originatingRequestId: options.originatingRequestId });
				const outcome: ContinuationAttemptOutcome = noCutReason
					? "no-safe-cut"
					: err.message === "Compaction cancelled"
						? "cancellation"
						: "failure";
				continuation.request({
					initiator: options.initiator,
					outcome,
					attemptId,
					requestId: options.originatingRequestId,
					originatingRequestId: options.originatingRequestId,
					resumeIntent,
					pendingToolCount: resumeIntent === "active" ? options.interruptedTurn?.pendingToolCallIds.size ?? 0 : 0,
				}, ctx);
				if (noCutReason) {
					ctx.ui.notify("No safe compaction cut available; continuation is coordinator-owned.", "info");
					return;
				}
				logPiVccError("compaction_failed", err, {
					reason: options.reason,
					attemptId,
					resumeIntent,
					pendingToolCount: options.interruptedTurn?.pendingToolCallIds.size ?? 0,
					usagePercent: options.ratchetPercent,
				});
				ctx.ui.notify(`Compaction failed: ${err.message}; continuation is coordinator-owned. Logged to ${getPiVccLogPath()}.`, "warning");
			}),
		});
		return true;
	};

	const schedulePiVccCompaction = (ctx: ExtensionContext, options: TriggerOptions) => {
		if (compactionInFlight || scheduledPiVccCompaction || activeCompactionOwner) return false;
		activeCompactionOwner = "pi-vcc";
		const scheduled = {
			...options,
			scheduledAgentGeneration: options.scheduledAgentGeneration ?? agentGeneration,
		};
		scheduledPiVccCompaction = setTimeout(() => {
			ignoreStaleContextCallback("scheduled_compaction", () => {
				scheduledPiVccCompaction = undefined;
				if (!runtimeActive) { activeCompactionOwner = undefined; return; }
				if (compactionInFlight) return;
				if (activeCompactionOwner !== "pi-vcc") { activeCompactionOwner = undefined; return; }
				const pending = pendingModelCompaction;
				const escalated = pending ? {
					...scheduled,
					initiator: "compact_context" as const,
					attemptId: pending.attemptId,
					originatingRequestId: pending.requestId,
					customInstructions: buildIntentInstructions(pending),
					resumeIntent: "active" as const,
					reason: "compact_context",
				} : scheduled;
				const started = triggerCompaction(ctx, escalated);
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
			},
		},
		async execute(toolCallId: string, params: any) {
			const reason = clampText(params.reason, 240) ?? "semantic boundary";
			const boundary = params.boundary as Boundary;
			const preserve = clampText(params.preserve, 500);
			const requestId = `compact-context-${Date.now().toString(36)}-${toolCallId}`;
			const attemptId = `${requestId}-attempt`;
			const observedBatchContainsTool =
				outstandingAssistantToolCallIds.has(toolCallId);
			pendingModelCompaction = {
				requestId,
				attemptId,
				reason,
				boundary,
				resumeIntent: "active",
				preserve,
				toolCallId,
				requestedTurn: turnCounter,
				toolBatchId: observedBatchContainsTool
					? lastToolBatchId
					: undefined,
				sawSiblingTools:
					observedBatchContainsTool && lastAssistantToolCallCount > 1,
			};
			return {
				content: [{
					type: "text",
					text: "compact_context queued. Compaction will run after same-batch siblings settle, then this active workflow will continue exactly once.",
				}],
				details: { ...pendingModelCompaction, willResume: true },
			};
		},
	});

	pi.registerCommand("compact-now", {
		description:
			"Trigger compaction immediately with optional custom instructions",
		handler: async (args, ctx: ExtensionContext) => {
			const customInstructions = args.trim();
			const usage = ctx.getContextUsage();
			const attemptId = `compact-now-${nextCompactionAttemptId + 1}`;
			triggerCompaction(ctx, {
				initiator: "package-compact-now",
				resumeIntent: "none",
				attemptId,
				customInstructions: `${PI_VCC_MANUAL_BYPASS_MARKER}\n${JSON.stringify({
					source: "package-compact-now",
					attemptId,
					transactionId: `vcc-command-${attemptId}`,
					resumeIntent: "none",
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
		const overflowRetryResponse =
			isContextOverflowResponse(event.message, ctx) &&
			overflowRequiresRetry(event.message);
		const sourceResponseComplete = completedResponse && !overflowRetryResponse;
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
		if (hasFailureOutput(event.message) || turnToolResults.some(hasFailureOutput)) {
			lastFailureTurn = turnCounter;
		}

		const usage = ctx.getContextUsage();
		const usagePercent = usage?.percent ?? undefined;

		const deliveredIds = deliveredToolCallIds(event);
		for (const id of deliveredIds) outstandingAssistantToolCallIds.delete(id);
		if (completedResponse) outstandingAssistantToolCallIds.clear();

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
			triggerCompaction(ctx, {
				initiator: "compact_context",
				resumeIntent: "active",
				attemptId: pending.attemptId,
				originatingRequestId: pending.requestId,
				customInstructions: buildIntentInstructions(pending),
				startMessage: `✓ Compacting at semantic boundary: ${pending.boundary}`,
				completionMessage: "Compacted with pi-vcc",
				ratchetPercent: usagePercent ?? undefined,
				reason: "compact_context",
				interruptedTurn: snapshotInterruptedCompactionTurn(event, "compact_context", ctx),
			});
			return;
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
				const started = schedulePiVccCompaction(ctx, {
					initiator: "hard-backstop",
					resumeIntent: completedResponse ? "none" : "active",
					resolveIntentAtStart: true,
					sourceResponseComplete: completedResponse,
					scheduledAgentGeneration: agentGeneration,
					startMessage: completedResponse
						? `✓ Auto-compacting Grok context at ${tokens.toLocaleString()} tokens (trigger: ${GROK_COMPACTION_TRIGGER_TOKENS.toLocaleString()})`
						: `↻ Grok context at ${tokens.toLocaleString()} tokens (trigger: ${GROK_COMPACTION_TRIGGER_TOKENS.toLocaleString()}). Interrupting agent for pi-vcc compaction...`,
					completionMessage: "Compacted with pi-vcc",
					ratchetPercent: usagePercent,
					reason: "grok_context_ceiling",
					interruptedTurn: snapshotInterruptedCompactionTurn(
						event,
						"hard_backstop",
						ctx,
					),
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
				resumeIntent: completedResponse ? "none" : "active",
				resolveIntentAtStart: true,
				sourceResponseComplete: completedResponse,
				scheduledAgentGeneration: agentGeneration,
				startMessage: completedResponse
					? `✓ Auto-compacting at ${currentPercent}% (hard backstop: ${HARD_AUTO_COMPACTION_PERCENT}%)`
					: `↻ Context at ${currentPercent}% (hard backstop: ${HARD_AUTO_COMPACTION_PERCENT}%). Interrupting agent for pi-vcc compaction...`,
				completionMessage: "Compacted with pi-vcc",
				ratchetPercent: usagePercent,
				reason: "hard_backstop",
				interruptedTurn: snapshotInterruptedCompactionTurn(
					event,
					"hard_backstop",
					ctx,
				),
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
			resumeIntent: needsRetry ? "active" : "none",
			startMessage: needsRetry
				? "↻ Provider reported context overflow. Interrupting agent for pi-vcc compaction and retry..."
				: "✓ Provider response exceeded its context window. Compacting with pi-vcc...",
			completionMessage: "Compacted with pi-vcc after context overflow",
			ratchetPercent: usagePercent,
			reason: "overflow",
			interruptedTurn: {
				interrupted: needsRetry,
				pendingToolCallIds: new Set(),
				reason: "core_deferred",
			},
		});
	});

	pi.on("agent_start", () => {
		agentGeneration += 1;
		agentActive = true;
	});
	pi.on("agent_settled", () => {
		agentActive = false;
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
		if (scheduledPiVccCompaction) {
			clearTimeout(scheduledPiVccCompaction);
			scheduledPiVccCompaction = undefined;
		}
		compactionInFlight = false;
		activeCompactionOwner = undefined;
		currentCompactionAttemptId = undefined;
		pendingModelCompaction = undefined;
		agentActive = false;
	});

	pi.on("session_compact", async () => {
		noCutRetryState = undefined;
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
