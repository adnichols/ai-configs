import { describe, expect, test } from "bun:test";

import {
	estimateGrokProviderRequestTokens,
	GROK_COMPACTION_TRIGGER_TOKENS,
	GROK_CONTEXT_CEILING_MODEL_ID,
	GROK_CONTEXT_CEILING_PROVIDER,
	GROK_CONTEXT_CEILING_TOKENS,
	GROK_OUTPUT_RESERVATION_TOKENS,
	grokCompactionTriggerReached,
	grokProviderCeilingReached,
	isGrokContextCeilingModel,
} from "../_pi/lib/grok-context-ceiling-policy";

const userMessage = (text: string) => ({
	role: "user" as const,
	content: [{ type: "text" as const, text }],
});

const assistantWithUsage = (totalTokens: number) => ({
	role: "assistant" as const,
	content: [{ type: "text" as const, text: "ok" }],
	usage: {
		input: totalTokens - 10,
		output: 10,
		cacheRead: 0,
		cacheWrite: 0,
		totalTokens,
		cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
	},
});

describe("grok-context-ceiling-policy identity", () => {
	test("matches exact opencode/grok-4.5 pair only", () => {
		expect(
			isGrokContextCeilingModel({
				provider: GROK_CONTEXT_CEILING_PROVIDER,
				modelId: GROK_CONTEXT_CEILING_MODEL_ID,
			}),
		).toBe(true);
		expect(
			isGrokContextCeilingModel({
				provider: "grok",
				modelId: GROK_CONTEXT_CEILING_MODEL_ID,
			}),
		).toBe(false);
		expect(
			isGrokContextCeilingModel({
				provider: GROK_CONTEXT_CEILING_PROVIDER,
				modelId: "grok-4.3",
			}),
		).toBe(false);
		expect(isGrokContextCeilingModel(undefined)).toBe(false);
	});
});

describe("grok-context-ceiling-policy thresholds", () => {
	test("exports single canonical boundary constants", () => {
		expect(GROK_COMPACTION_TRIGGER_TOKENS).toBe(180_000);
		expect(GROK_CONTEXT_CEILING_TOKENS).toBe(200_000);
	});

	test("trigger and ceiling boundaries are exclusive at 179999 and inclusive at 180000/200000", () => {
		expect(grokCompactionTriggerReached(179_999)).toBe(false);
		expect(grokCompactionTriggerReached(180_000)).toBe(true);
		expect(grokProviderCeilingReached(199_999)).toBe(false);
		expect(grokProviderCeilingReached(200_000)).toBe(true);
	});
});

describe("estimateGrokProviderRequestTokens", () => {
	test("includes trailing messages, tools, system prompt, and output reservation", () => {
		const baseMessages = [
			userMessage("hello"),
			assistantWithUsage(150_000),
			userMessage("follow up"),
		];
		const withoutExtras = estimateGrokProviderRequestTokens({
			messages: baseMessages,
			outputReservationTokens: 0,
		});
		const withExtras = estimateGrokProviderRequestTokens({
			messages: baseMessages,
			systemPrompt: "system ".repeat(100),
			tools: [{ name: "read", description: "read files", parameters: {} }],
			outputReservationTokens: GROK_OUTPUT_RESERVATION_TOKENS,
		});
		expect(withExtras).toBeGreaterThan(withoutExtras);
		expect(withExtras - withoutExtras).toBeGreaterThan(
			GROK_OUTPUT_RESERVATION_TOKENS,
		);
	});

	test("boundary samples align with trigger and ceiling constants", () => {
		const reservation = GROK_OUTPUT_RESERVATION_TOKENS;
		const atTrigger = estimateGrokProviderRequestTokens({
			messages: [assistantWithUsage(GROK_COMPACTION_TRIGGER_TOKENS - reservation - 1)],
			outputReservationTokens: reservation,
		});
		const atCeiling = estimateGrokProviderRequestTokens({
			messages: [assistantWithUsage(GROK_CONTEXT_CEILING_TOKENS - reservation - 1)],
			outputReservationTokens: reservation,
		});
		expect(atTrigger).toBeGreaterThanOrEqual(GROK_COMPACTION_TRIGGER_TOKENS - 2);
		expect(atTrigger).toBeLessThan(GROK_COMPACTION_TRIGGER_TOKENS + 5);
		expect(atCeiling).toBeGreaterThanOrEqual(GROK_CONTEXT_CEILING_TOKENS - 2);
		expect(atCeiling).toBeLessThan(GROK_CONTEXT_CEILING_TOKENS + 5);
	});
});
