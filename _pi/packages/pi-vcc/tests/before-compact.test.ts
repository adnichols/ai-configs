import { describe, expect, it } from "bun:test";
import { getLastCompactionStats, getLastNoCutClassification, registerBeforeCompactHook } from "../src/hooks/before-compact";
import { PI_VCC_COMPACT_INSTRUCTION } from "../src/core/compact-args";

const messageEntry = (id: string, message: any) => ({
	type: "message",
	id,
	parentId: null,
	timestamp: new Date().toISOString(),
	message,
});

const user = (text: string) => ({ role: "user", content: text, timestamp: Date.now() });
const assistant = (text: string, stopReason = "stop") => ({
	role: "assistant",
	content: [{ type: "text", text }],
	stopReason,
	provider: "faux",
	model: "faux-1",
	api: "faux",
	usage: { input: 1, output: 1, cacheRead: 0, cacheWrite: 0, totalTokens: 2 },
	timestamp: Date.now(),
});
const toolCall = (id: string) => ({
	role: "assistant",
	content: [{ type: "toolCall", id, name: "bash", arguments: { command: "echo ok" } }],
	stopReason: "toolUse",
	provider: "faux",
	model: "faux-1",
	api: "faux",
	usage: { input: 1, output: 1, cacheRead: 0, cacheWrite: 0, totalTokens: 2 },
	timestamp: Date.now(),
});
const toolResult = (id: string) => ({
	role: "toolResult",
	toolCallId: id,
	toolName: "bash",
	content: [{ type: "text", text: "ok" }],
	isError: false,
	timestamp: Date.now(),
});

const preparation = (overrides: Record<string, unknown> = {}) => ({
	firstKeptEntryId: "kept-user",
	messagesToSummarize: [user("old request"), assistant("old answer")],
	turnPrefixMessages: [],
	isSplitTurn: false,
	tokensBefore: 500,
	previousSummary: undefined,
	fileOps: { read: new Set<string>(), written: new Set<string>(), edited: new Set<string>() },
	settings: { enabled: true, reserveTokens: 100, keepRecentTokens: 200 },
	...overrides,
});

const register = () => {
	const handlers: Record<string, (event: any, ctx?: any) => any> = {};
	registerBeforeCompactHook({
		on: (name: string, handler: any) => {
			handlers[name] = handler;
		},
	} as any);
	return handlers;
};

describe("pi-vcc before-compact hook", () => {
	it("uses the host preparation and keeps the native retained entry", async () => {
		const handlers = register();
		const result = await handlers.session_before_compact({
			preparation: preparation(),
			branchEntries: [
				messageEntry("old-user", user("old request")),
				messageEntry("old-assistant", assistant("old answer")),
				messageEntry("kept-user", user("new request")),
				messageEntry("kept-assistant", assistant("new answer")),
			],
			reason: "threshold",
			willRetry: false,
		});

		expect(result?.compaction.firstKeptEntryId).toBe("kept-user");
		expect(result?.compaction.summary).toContain("old request");
		expect(getLastCompactionStats()).toMatchObject({ summarized: 2, kept: 2 });
		expect(getLastNoCutClassification()).toBeNull();
	});

	it("includes a native split-turn prefix while preserving the host cut", async () => {
		const handlers = register();
		const result = await handlers.session_before_compact({
			preparation: preparation({
			messagesToSummarize: [user("old request")],
			turnPrefixMessages: [toolCall("tc-1")],
			firstKeptEntryId: "kept-result",
			isSplitTurn: true,
			}),
			branchEntries: [
				messageEntry("old-user", user("old request")),
				messageEntry("prefix-call", toolCall("tc-1")),
				messageEntry("kept-result", toolResult("tc-1")),
			],
			reason: "threshold",
		});

		expect(result?.compaction.firstKeptEntryId).toBe("kept-result");
		expect(result?.compaction.details.sourceMessageCount).toBe(2);
	});

	it("uses an explicit keep:N cut only when requested", async () => {
		const handlers = register();
		const entries = [
			messageEntry("u1", user("first")),
			messageEntry("a1", assistant("first answer")),
			messageEntry("u2", user("second")),
			messageEntry("a2", assistant("second answer")),
			messageEntry("u3", user("third")),
			messageEntry("a3", assistant("third answer")),
		];
		const result = await handlers.session_before_compact({
			preparation: preparation({ messagesToSummarize: [user("host native prefix")] }),
			branchEntries: entries,
			customInstructions: `${PI_VCC_COMPACT_INSTRUCTION}\nkeep:1`,
			reason: "manual",
		});

		expect(result?.compaction.firstKeptEntryId).toBe("u3");
		expect(result?.compaction.summary).toContain("second answer");
	});

	it("records semantic focus without creating continuation metadata", async () => {
		const handlers = register();
		const result = await handlers.session_before_compact({
			preparation: preparation(),
			branchEntries: [
				messageEntry("old-user", user("old request")),
				messageEntry("old-assistant", assistant("old answer")),
				messageEntry("kept-user", user("new request")),
			],
			customInstructions: `${PI_VCC_COMPACT_INSTRUCTION}\n${JSON.stringify({ source: "compact_context", boundary: "after_test_loop", preserve: "keep test failures" })}`,
			reason: "manual",
		});

		expect(result?.compaction.summary).toContain("[Compaction Intent]");
		expect(result?.compaction.details).toMatchObject({ compactor: "pi-vcc", version: 2 });
		expect(Object.keys(result?.compaction.details ?? {})).not.toContain("transactionId");
	});

	it("cancels an explicit keep request when it cannot form a safe cut", async () => {
		const handlers = register();
		const result = await handlers.session_before_compact({
			preparation: preparation(),
			branchEntries: [messageEntry("only", user("one message"))],
			customInstructions: `${PI_VCC_COMPACT_INSTRUCTION}\nkeep:1`,
			reason: "manual",
		});

		expect(result).toEqual({ cancel: true });
		expect(getLastNoCutClassification()?.reason).toBe("tiny_session");
	});
});
