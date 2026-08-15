import { describe, expect, it } from "bun:test";
import { registerPiVccCommand } from "../src/commands/pi-vcc";
import { PI_VCC_COMPACT_INSTRUCTION } from "../src/core/compact-args";

const createHarness = () => {
	const commands: Record<string, any> = {};
	const compactCalls: any[] = [];
	const notifications: any[] = [];
	const sentUserMessages: any[] = [];
	let idle = true;
	registerPiVccCommand({
		registerCommand: (name: string, command: any) => { commands[name] = command; },
		sendUserMessage: (message: string, options: any) => sentUserMessages.push({ message, options }),
	} as any);
	return {
		commands,
		compactCalls,
		notifications,
		sentUserMessages,
		setIdle: (value: boolean) => { idle = value; },
		ctx: {
			isIdle: () => idle,
			compact: (options: any) => compactCalls.push(options),
			ui: { notify: (message: string, level: string) => notifications.push({ message, level }) },
			sessionManager: {},
		},
	};
};

describe("/pi-vcc command", () => {
	it("compacts immediately only while idle", async () => {
		const harness = createHarness();
		await harness.commands["pi-vcc"].handler("keep:2", harness.ctx);

		expect(harness.compactCalls).toHaveLength(1);
		expect(harness.compactCalls[0].customInstructions).toBe(`${PI_VCC_COMPACT_INSTRUCTION}\nkeep:2`);
	});

	it("refuses active-run invocation instead of using a fork API or aborting", async () => {
		const harness = createHarness();
		harness.setIdle(false);
		await harness.commands["pi-vcc"].handler("keep:2", harness.ctx);

		expect(harness.compactCalls).toHaveLength(0);
		expect(harness.notifications.at(-1)?.message).toContain("only runs while Pi is idle");
		expect(harness.sentUserMessages).toHaveLength(0);
	});

	it("treats trailing text as compaction focus and never sends a follow-up", async () => {
		const harness = createHarness();
		await harness.commands["pi-vcc"].handler("keep:1 preserve the failing test evidence", harness.ctx);
		harness.compactCalls[0].onComplete?.();

		expect(harness.compactCalls[0].customInstructions).toContain("keep:1");
		expect(harness.compactCalls[0].customInstructions).toContain("preserve the failing test evidence");
		expect(harness.notifications.at(-1)?.message).toContain("Compacted with pi-vcc");
		expect(harness.sentUserMessages).toHaveLength(0);
	});

	it("reports failure without submitting a hidden follow-up", async () => {
		const harness = createHarness();
		await harness.commands["pi-vcc"].handler("", harness.ctx);
		harness.compactCalls[0].onError?.(new Error("summary failed"));

		expect(harness.sentUserMessages).toHaveLength(0);
		expect(harness.notifications.at(-1)).toMatchObject({ level: "error" });
	});
});
