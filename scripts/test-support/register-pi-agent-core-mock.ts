import { mock } from "bun:test";

const estimateTokens = (message: any): number => {
	if (message?.usage?.totalTokens != null) return 0;
	const content = message?.content;
	if (typeof content === "string") return Math.ceil(content.length / 4);
	if (!Array.isArray(content)) return 0;
	const chars = content.reduce((sum: number, part: any) => {
		if (typeof part?.text === "string") return sum + part.text.length;
		if (typeof part?.thinking === "string") return sum + part.thinking.length;
		if (part?.type === "toolCall") {
			return (
				sum +
				String(part.name ?? "").length +
				JSON.stringify(part.arguments ?? "").length
			);
		}
		return sum;
	}, 0);
	return Math.ceil(chars / 4);
};

const estimateContextTokens = (messages: any[]) => {
	for (let i = messages.length - 1; i >= 0; i--) {
		const usage = messages[i]?.usage;
		if (messages[i]?.role === "assistant" && usage?.totalTokens != null) {
			let trailingTokens = 0;
			for (let j = i + 1; j < messages.length; j++) {
				trailingTokens += estimateTokens(messages[j]);
			}
			return {
				tokens: usage.totalTokens + trailingTokens,
				usageTokens: usage.totalTokens,
				trailingTokens,
				lastUsageIndex: i,
			};
		}
	}
	let estimated = 0;
	for (const message of messages) estimated += estimateTokens(message);
	return {
		tokens: estimated,
		usageTokens: 0,
		trailingTokens: estimated,
		lastUsageIndex: null,
	};
};

export const registerPiAgentCoreMock = (): void => {
	mock.module("@earendil-works/pi-agent-core", () => ({
		estimateContextTokens,
		estimateTokens,
	}));
};
