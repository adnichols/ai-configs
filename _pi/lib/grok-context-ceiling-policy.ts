import {
	estimateContextTokens,
	estimateTokens,
	type AgentMessage,
} from "@earendil-works/pi-agent-core";

export const GROK_CONTEXT_CEILING_PROVIDER = "opencode" as const;
export const GROK_CONTEXT_CEILING_MODEL_ID = "grok-4.5" as const;
export const GROK_COMPACTION_TRIGGER_TOKENS = 180_000;
export const GROK_CONTEXT_CEILING_TOKENS = 200_000;
export const GROK_ADVERTISED_CONTEXT_WINDOW = 200_000;
/** Pi's default max output tokens; the grok-4.5 model override no longer lowers it. */
export const GROK_DEFAULT_MAX_TOKENS = 16_384;
/** Matches Pi default compaction reserveTokens until P0 reads shared settings. */
export const GROK_OUTPUT_RESERVATION_TOKENS = 16_384;

export interface GrokModelIdentity {
	provider?: string;
	modelId?: string;
}

export interface GrokProviderRequestEstimateInput {
	messages: AgentMessage[];
	systemPrompt?: string;
	tools?: unknown[];
	outputReservationTokens?: number;
}

export const isGrokContextCeilingModel = (
	identity: GrokModelIdentity | undefined,
): boolean =>
	Boolean(
		identity &&
			identity.provider === GROK_CONTEXT_CEILING_PROVIDER &&
			identity.modelId === GROK_CONTEXT_CEILING_MODEL_ID,
	);

export const grokContextUsagePercent = (
	tokens: number,
	contextWindow = GROK_ADVERTISED_CONTEXT_WINDOW,
): number => (tokens / contextWindow) * 100;

const estimateToolDefinitionTokens = (tools: unknown[] | undefined): number => {
	if (!tools?.length) return 0;
	return Math.ceil(JSON.stringify(tools).length / 4);
};

const estimateSystemPromptTokens = (systemPrompt: string | undefined): number => {
	if (!systemPrompt) return 0;
	return Math.ceil(systemPrompt.length / 4);
};

/**
 * Canonical post-transform provider request estimate for Grok 4.5.
 * Trailing-aware message tokens + system prompt + tool defs + output reservation.
 */
export const estimateGrokProviderRequestTokens = (
	input: GrokProviderRequestEstimateInput,
): number => {
	const messageEstimate = estimateContextTokens(input.messages);
	const outputReservation =
		input.outputReservationTokens ?? GROK_OUTPUT_RESERVATION_TOKENS;
	return (
		messageEstimate.tokens +
		estimateSystemPromptTokens(input.systemPrompt) +
		estimateToolDefinitionTokens(input.tools) +
		outputReservation
	);
};

/** Extension turn-boundary estimate from ctx.getContextUsage().tokens when available. */
export const estimateGrokTurnBoundaryTokens = (
	messages: AgentMessage[],
	reportedTokens: number | null | undefined,
): number => {
	if (reportedTokens !== null && reportedTokens !== undefined) {
		return reportedTokens;
	}
	return estimateContextTokens(messages).tokens;
};

export const formatGrokThresholdStatus = (): string =>
	`Grok 4.5 policy: pi-vcc at ${GROK_COMPACTION_TRIGGER_TOKENS.toLocaleString()} tokens, provider-request ceiling ${GROK_CONTEXT_CEILING_TOKENS.toLocaleString()} tokens`;

export const grokCompactionTriggerReached = (tokens: number): boolean =>
	tokens >= GROK_COMPACTION_TRIGGER_TOKENS;

export const grokProviderCeilingReached = (tokens: number): boolean =>
	tokens >= GROK_CONTEXT_CEILING_TOKENS;

/** Re-export for boundary tests that need per-message estimation. */
export { estimateTokens };
