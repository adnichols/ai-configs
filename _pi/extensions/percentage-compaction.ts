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
	let lastAutoCompactionPercent: number | undefined;
	let lastNudgePercentBand: NudgeBand | undefined;
	let activeModelProvider: string | undefined;
	let activeModelId: string | undefined;
	let lastGrokAutoCompactionTokens: number | undefined;

	const activeGrokIdentity = () => ({ provider: activeModelProvider, modelId: activeModelId });
	const isActiveGrokModel = (ctx: ExtensionContext) =>
		isGrokContextCeilingModel(activeGrokIdentity()) ||
		isGrokContextCeilingModel({
			provider: (ctx.model as { provider?: string } | undefined)?.provider,
			modelId: ctx.model?.id,
		});

	const resetThresholdLatches = () => {
		lastAutoCompactionPercent = undefined;
		lastNudgePercentBand = undefined;
		lastGrokAutoCompactionTokens = undefined;
	};

	const requestBoundaryCompaction = (
		ctx: ExtensionContext,
		reason: "manual" | "threshold",
		customInstructions?: string,
	): boolean => {
		if (!runtimeActive || !isPiVccLoaded() || ctx.signal?.aborted) {
			if (!isPiVccLoaded()) notifyMissingPiVcc(ctx);
			return false;
		}
		return ctx.requestCompactionAtTurnBoundary({ reason, customInstructions });
	};

	const sendModelNudge = (ctx: ExtensionContext, usagePercent: number, band: NudgeBand) => {
		if (lastNudgePercentBand === band) return;
		const currentPercent = Math.floor(usagePercent);
		const content = band === "strong"
			? `Context is at ${currentPercent}% (strong nudge band ${COMPACTION_STRONG_NUDGE_PERCENT}-${HARD_AUTO_COMPACTION_PERCENT - 1}%). Use compact_context at a safe semantic boundary; ${HARD_AUTO_COMPACTION_PERCENT}% is the automatic backstop.`
			: `Context is at ${currentPercent}% (soft nudge band ${COMPACTION_NUDGE_PERCENT}-${COMPACTION_STRONG_NUDGE_PERCENT - 1}%). Use compact_context after a subtask resolves, before switching topics, or after a test/debug loop has been interpreted.`;
		lastNudgePercentBand = band;
		ctx.ui.notify(content, band === "strong" ? "warning" : "info");
	};

	pi.registerTool({
		name: "compact_context",
		label: "Compact Context",
		description: "Request pi-vcc semantic-boundary compaction after the current tool turn completes.",
		promptSnippet: "Queue semantic-boundary context compaction with pi-vcc",
		promptGuidelines: [
			"Use compact_context after a subtask resolves, before switching topics, after a test/debug loop has been interpreted, or when context is becoming noisy.",
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
			const accepted = requestBoundaryCompaction(ctx, "manual", customInstructions);
			return {
				content: [{
					type: "text",
					text: accepted
						? "compact_context accepted. Pi-vcc will compact at the next safe turn boundary without starting a second run."
						: "compact_context could not be accepted because the agent is idle, stopping, or pi-vcc is unavailable.",
				}],
				details: { accepted, reason, boundary, preserve, toolCallId },
			};
		},
	});

	pi.registerCommand("compact-now", {
		description: "Trigger compaction immediately when idle, or request it at the active turn boundary",
		handler: async (args, ctx: ExtensionContext) => {
			const customInstructions = args.trim();
			if (!ctx.isIdle()) {
				const accepted = requestBoundaryCompaction(ctx, "manual", customInstructions || undefined);
				ctx.ui.notify(accepted ? "Compaction requested for the current turn boundary" : "Compaction request rejected", accepted ? "info" : "warning");
				return;
			}
			if (!isPiVccLoaded()) {
				notifyMissingPiVcc(ctx);
				return;
			}
			ctx.compact({
				customInstructions: customInstructions ? `${PI_VCC_MANUAL_BYPASS_MARKER}\n${customInstructions}` : PI_VCC_MANUAL_BYPASS_MARKER,
				onComplete: () => ctx.ui.notify("Compaction complete", "info"),
				onError: (err) => ctx.ui.notify(`Compaction failed: ${err.message}`, "warning"),
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
					`Context: ${tokens.toLocaleString()} / ${GROK_ADVERTISED_CONTEXT_WINDOW.toLocaleString()} tokens (${Math.floor(usage.percent)}%). ${formatGrokThresholdStatus()}`,
					"info",
				);
				return;
			}
			ctx.ui.notify(
				`Context: ${Math.floor(usage.percent)}% of ${(contextWindowFor(ctx) ?? usage.contextWindow).toLocaleString()} tokens (nudges: ${COMPACTION_NUDGE_PERCENT}/${COMPACTION_STRONG_NUDGE_PERCENT}%, hard backstop: ${HARD_AUTO_COMPACTION_PERCENT}%)`,
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
		// A new user run may legitimately add enough context to need another request.
		lastAutoCompactionPercent = undefined;
		lastNudgePercentBand = undefined;
	});

	pi.on("turn_end", async (_event: TurnEndEvent, ctx: ExtensionContext) => {
		if (!runtimeActive || ctx.signal?.aborted) return;
		const usage = ctx.getContextUsage();
		const usagePercent = usage?.percent;
		if (usagePercent === undefined || usagePercent === null) return;

		if (isActiveGrokModel(ctx)) {
			const tokens = resolveGrokUsageTokens(usage);
			if (tokens < Math.floor((COMPACTION_NUDGE_PERCENT / 100) * GROK_ADVERTISED_CONTEXT_WINDOW)) {
				lastGrokAutoCompactionTokens = undefined;
				lastAutoCompactionPercent = undefined;
				lastNudgePercentBand = undefined;
				return;
			}
			if (grokCompactionTriggerReached(tokens) && tokens !== lastGrokAutoCompactionTokens) {
				if (requestBoundaryCompaction(ctx, "threshold")) {
					lastGrokAutoCompactionTokens = tokens;
					ctx.ui.notify(
						`Auto-compaction requested at ${tokens.toLocaleString()} tokens (trigger: ${GROK_COMPACTION_TRIGGER_TOKENS.toLocaleString()})`,
						"warning",
					);
				}
			}
			return;
		}

		if (usagePercent < COMPACTION_NUDGE_PERCENT) {
			lastAutoCompactionPercent = undefined;
			lastNudgePercentBand = undefined;
			return;
		}
		if (usagePercent >= HARD_AUTO_COMPACTION_PERCENT) {
			if (lastAutoCompactionPercent === usagePercent) return;
			if (requestBoundaryCompaction(ctx, "threshold")) {
				lastAutoCompactionPercent = usagePercent;
				ctx.ui.notify(
					`Auto-compaction requested at ${Math.floor(usagePercent)}% (hard backstop: ${HARD_AUTO_COMPACTION_PERCENT}%)`,
					"warning",
				);
			}
			return;
		}
		if (usagePercent >= COMPACTION_STRONG_NUDGE_PERCENT) {
			sendModelNudge(ctx, usagePercent, "strong");
			return;
		}
		sendModelNudge(ctx, usagePercent, "soft");
	});

	pi.on("session_before_compact", async (event: SessionBeforeCompactEvent, ctx: ExtensionContext) => {
		if (!isPiVccLoaded()) {
			notifyMissingPiVcc(ctx);
			return { cancel: true };
		}
		// The pi-vcc hook owns summary construction. This extension only requests
		// the boundary; it must never turn threshold maintenance into an aborting
		// fallback or a second agent run.
		if (event.customInstructions?.startsWith(PI_VCC_MANUAL_BYPASS_MARKER)) return;
		return;
	});

	pi.on("session_shutdown", async () => {
		runtimeActive = false;
		lastAutoCompactionPercent = undefined;
		lastNudgePercentBand = undefined;
		lastGrokAutoCompactionTokens = undefined;
	});
}
