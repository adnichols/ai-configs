import type {
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
	grokCompactionTriggerReached,
	isGrokContextCeilingModel,
} from "../lib/grok-context-ceiling-policy";

export const COMPACTION_NUDGE_PERCENT = 60;
export const COMPACTION_STRONG_NUDGE_PERCENT = 75;
export const HARD_AUTO_COMPACTION_PERCENT = 80;
export const COMPACTION_THRESHOLD_PERCENT = COMPACTION_NUDGE_PERCENT;
export const PI_VCC_MANUAL_BYPASS_MARKER = "__PI_VCC_MANUAL_BYPASS__";
export const PI_VCC_LOAD_MARKER = "__ADN_PI_VCC_LOADED__";

type NudgeBand = "soft" | "strong";
type Boundary = "subtask_complete" | "before_topic_switch" | "after_test_loop" | "manual_recovery";

type PendingCompaction = {
	customInstructions: string;
	source: "tool" | "command";
	reason: string;
	boundary?: Boundary;
	preserve?: string;
};

const isPiVccLoaded = () => Boolean((globalThis as any)[PI_VCC_LOAD_MARKER]);

const notifyMissingPiVcc = (ctx: ExtensionContext) => {
	ctx.ui.notify(
		"Pi-vcc is not loaded; canceling compaction to avoid unsafe default compaction. Run ./install.sh --pi and restart Pi.",
		"error",
	);
};

const clampText = (value: unknown, max = 500): string | undefined => {
	if (typeof value !== "string") return undefined;
	const trimmed = value.trim();
	return trimmed ? trimmed.slice(0, max) : undefined;
};

const contextWindowFor = (ctx: ExtensionContext): number | undefined =>
	(ctx.model as { contextWindow?: number } | undefined)?.contextWindow ?? ctx.getContextUsage()?.contextWindow;

const resolveGrokUsageTokens = (usage: { percent: number; contextWindow: number; tokens?: number }) =>
	usage.tokens ?? Math.round((usage.percent / 100) * usage.contextWindow);

export default function (pi: ExtensionAPI) {
	let runtimeActive = true;
	let pendingCompaction: PendingCompaction | undefined;
	let runAborted = false;
	let lastNudgePercentBand: NudgeBand | undefined;
	let lastHardBackstopPercent: number | undefined;
	let activeModelProvider: string | undefined;
	let activeModelId: string | undefined;
	let lastGrokBackstopTokens: number | undefined;

	const activeGrokIdentity = () => ({ provider: activeModelProvider, modelId: activeModelId });
	const isActiveGrokModel = (ctx: ExtensionContext) =>
		isGrokContextCeilingModel(activeGrokIdentity()) ||
		isGrokContextCeilingModel({
			provider: (ctx.model as { provider?: string } | undefined)?.provider,
			modelId: ctx.model?.id,
		});

	const clearPendingCompaction = () => {
		pendingCompaction = undefined;
	};

	const resetThresholdLatches = () => {
		lastNudgePercentBand = undefined;
		lastHardBackstopPercent = undefined;
		lastGrokBackstopTokens = undefined;
	};

	const queueSettledCompaction = (ctx: ExtensionContext, request: PendingCompaction): boolean => {
		if (!runtimeActive || !isPiVccLoaded() || ctx.signal?.aborted) {
			if (!isPiVccLoaded()) notifyMissingPiVcc(ctx);
			return false;
		}
		// Coalesce to the newest semantic request. There is one in-memory intent,
		// never a queue and never persisted work to rehydrate after Escape/reload.
		pendingCompaction = request;
		return true;
	};

	const sendModelNudge = (ctx: ExtensionContext, usagePercent: number, band: NudgeBand) => {
		if (lastNudgePercentBand === band) return;
		const currentPercent = Math.floor(usagePercent);
		const content = band === "strong"
			? `Context is at ${currentPercent}% (strong nudge band ${COMPACTION_STRONG_NUDGE_PERCENT}-${HARD_AUTO_COMPACTION_PERCENT - 1}%). Use compact_context at a safe semantic boundary; pi-vcc will compact after the current run settles, while native Pi owns urgent overflow recovery.`
			: `Context is at ${currentPercent}% (soft nudge band ${COMPACTION_NUDGE_PERCENT}-${COMPACTION_STRONG_NUDGE_PERCENT - 1}%). Use compact_context after a subtask resolves; it records idle maintenance and never starts a continuation turn.`;
		lastNudgePercentBand = band;
		ctx.ui.notify(content, band === "strong" ? "warning" : "info");
	};

	pi.registerTool({
		name: "compact_context",
		label: "Compact Context",
		description: "Request pi-vcc compaction after the current agent run fully settles.",
		promptSnippet: "Queue settled-run semantic compaction with pi-vcc",
		promptGuidelines: [
			"Use compact_context after a subtask resolves, before switching topics, after a test/debug loop has been interpreted, or when context is becoming noisy.",
			"The request does not interrupt or restart the active run; pi-vcc compacts only after the run settles and the next genuine user request continues from compacted history.",
			"Do not use compact_context mid-tool-chain or while critical raw failure evidence has not been summarized.",
		],
		parameters: {
			type: "object",
			required: ["reason", "boundary"],
			properties: {
				reason: { type: "string", description: "Short reason for compaction" },
				preserve: { type: "string", description: "Optional short instructions for facts to preserve" },
				boundary: {
					type: "string",
					enum: ["subtask_complete", "before_topic_switch", "after_test_loop", "manual_recovery"],
				},
			},
		},
		async execute(toolCallId: string, params: any, _signal: AbortSignal | undefined, _onUpdate: unknown, ctx: ExtensionContext) {
			const reason = clampText(params.reason, 240) ?? "semantic boundary";
			const boundary = params.boundary as Boundary;
			const preserve = clampText(params.preserve, 500);
			const customInstructions = `${PI_VCC_MANUAL_BYPASS_MARKER}\n${JSON.stringify({
				source: "compact_context",
				reason,
				boundary,
				...(preserve ? { preserve } : {}),
			})}`;
			const accepted = queueSettledCompaction(ctx, {
				customInstructions,
				source: "tool",
				reason,
				boundary,
				preserve,
			});
			return {
				content: [{
					type: "text",
					text: accepted
						? "compact_context accepted. Pi-vcc will compact after the current run settles; it will not interrupt or start a continuation turn."
						: "compact_context could not be accepted because the run is stopping or pi-vcc is unavailable.",
				}],
				details: { accepted, reason, boundary, preserve, toolCallId },
			};
		},
	});

	pi.registerCommand("compact-now", {
		description: "Compact immediately when idle, otherwise compact after the current run settles",
		handler: async (args, ctx: ExtensionContext) => {
			const instructions = args.trim();
			if (!ctx.isIdle()) {
				const customInstructions = instructions
					? `${PI_VCC_MANUAL_BYPASS_MARKER}\n${instructions}`
					: PI_VCC_MANUAL_BYPASS_MARKER;
				const accepted = queueSettledCompaction(ctx, {
					customInstructions,
					source: "command",
					reason: instructions || "manual settled-run compaction",
				});
				ctx.ui.notify(
					accepted ? "Compaction queued for after the current run settles" : "Compaction request rejected",
					accepted ? "info" : "warning",
				);
				return;
			}
			if (!isPiVccLoaded()) {
				notifyMissingPiVcc(ctx);
				return;
			}
			ctx.compact({
				customInstructions: instructions ? `${PI_VCC_MANUAL_BYPASS_MARKER}\n${instructions}` : PI_VCC_MANUAL_BYPASS_MARKER,
				onComplete: () => ctx.ui.notify("Compaction complete", "info"),
				onError: (err) => ctx.ui.notify(`Compaction failed: ${err.message}`, "warning"),
			});
		},
	});

	pi.registerCommand("compact-status", {
		description: "Show current context usage and settled-run compaction status",
		handler: async (_args, ctx: ExtensionContext) => {
			const usage = ctx.getContextUsage();
			if (!usage || usage.percent === null) {
				ctx.ui.notify("Context usage: unknown", "warning");
				return;
			}
			if (isActiveGrokModel(ctx)) {
				const tokens = resolveGrokUsageTokens(usage);
				ctx.ui.notify(
					`Context: ${tokens.toLocaleString()} / ${GROK_ADVERTISED_CONTEXT_WINDOW.toLocaleString()} tokens (${Math.floor(usage.percent)}%). ${formatGrokThresholdStatus()} Semantic requests compact after settlement; native Pi owns urgent recovery.`,
					"info",
				);
				return;
			}
			ctx.ui.notify(
				`Context: ${Math.floor(usage.percent)}% of ${(contextWindowFor(ctx) ?? usage.contextWindow).toLocaleString()} tokens (nudges: ${COMPACTION_NUDGE_PERCENT}/${COMPACTION_STRONG_NUDGE_PERCENT}%; semantic compaction runs after settlement; native Pi owns overflow recovery)`,
				"info",
			);
		},
	});

	pi.on("model_select", async (event: ModelSelectEvent) => {
		if (event.model.provider === activeModelProvider && event.model.id === activeModelId) return;
		activeModelProvider = event.model.provider;
		activeModelId = event.model.id;
		resetThresholdLatches();
	});

	pi.on("agent_start", () => {
		// Pending intent must never leak into a later user run. Under the normal
		// path agent_settled already consumed it before another run can start.
		clearPendingCompaction();
		runAborted = false;
		resetThresholdLatches();
	});

	pi.on("turn_end", async (event: TurnEndEvent, ctx: ExtensionContext) => {
		if (!runtimeActive) return;
		if (event.message.role === "assistant" && event.message.stopReason === "aborted") {
			runAborted = true;
			clearPendingCompaction();
			return;
		}
		if (ctx.signal?.aborted) {
			runAborted = true;
			clearPendingCompaction();
			return;
		}

		const usage = ctx.getContextUsage();
		const usagePercent = usage?.percent;
		if (usagePercent === undefined || usagePercent === null) return;

		if (isActiveGrokModel(ctx)) {
			const tokens = resolveGrokUsageTokens(usage);
			if (tokens < Math.floor((COMPACTION_NUDGE_PERCENT / 100) * GROK_ADVERTISED_CONTEXT_WINDOW)) {
				lastGrokBackstopTokens = undefined;
				lastNudgePercentBand = undefined;
				return;
			}
			if (grokCompactionTriggerReached(tokens) && tokens !== lastGrokBackstopTokens) {
				lastGrokBackstopTokens = tokens;
				ctx.ui.notify(
					`Context reached ${tokens.toLocaleString()} tokens (configured trigger: ${GROK_COMPACTION_TRIGGER_TOKENS.toLocaleString()}). Native Pi owns urgent threshold/overflow recovery; pi-vcc will not create a continuation turn.`,
					"warning",
				);
			}
			return;
		}

		if (usagePercent < COMPACTION_NUDGE_PERCENT) {
			resetThresholdLatches();
			return;
		}
		if (usagePercent >= HARD_AUTO_COMPACTION_PERCENT) {
			if (lastHardBackstopPercent === usagePercent) return;
			lastHardBackstopPercent = usagePercent;
			ctx.ui.notify(`Context is at ${Math.floor(usagePercent)}%.`, "warning");
			return;
		}
		if (usagePercent >= COMPACTION_STRONG_NUDGE_PERCENT) {
			sendModelNudge(ctx, usagePercent, "strong");
			return;
		}
		sendModelNudge(ctx, usagePercent, "soft");
	});

	pi.on("agent_settled", async (_event, ctx: ExtensionContext) => {
		if (!runtimeActive || runAborted) {
			clearPendingCompaction();
			runAborted = false;
			return;
		}
		const request = pendingCompaction;
		clearPendingCompaction();
		if (!request) return;
		if (!isPiVccLoaded()) {
			notifyMissingPiVcc(ctx);
			return;
		}
		if (!ctx.isIdle() || ctx.signal?.aborted) {
			ctx.ui.notify("Skipped queued compaction because the session did not settle cleanly", "warning");
			return;
		}

		ctx.compact({
			customInstructions: request.customInstructions,
			onComplete: () => {
				ctx.ui.notify("Settled-run compaction complete; the next genuine user request will use compacted context", "info");
			},
			onError: (err) => {
				ctx.ui.notify(`Settled-run compaction stopped: ${err.message}. No continuation was queued.`, "warning");
			},
		});
	});

	pi.on("session_compact", () => {
		// Native threshold/overflow/manual compaction already satisfied any
		// semantic maintenance request. Never compact twice at settlement.
		clearPendingCompaction();
	});

	pi.on("session_before_compact", async (event: SessionBeforeCompactEvent, ctx: ExtensionContext) => {
		event.signal?.addEventListener("abort", () => {
			clearPendingCompaction();
		}, { once: true });
		if (!isPiVccLoaded()) {
			notifyMissingPiVcc(ctx);
			return { cancel: true };
		}
		return;
	});

	const discardRuntimeIntent = () => {
		clearPendingCompaction();
		runAborted = true;
	};

	pi.on("session_before_switch", discardRuntimeIntent);
	pi.on("session_before_fork", discardRuntimeIntent);
	pi.on("session_shutdown", async () => {
		runtimeActive = false;
		discardRuntimeIntent();
		resetThresholdLatches();
	});
}
