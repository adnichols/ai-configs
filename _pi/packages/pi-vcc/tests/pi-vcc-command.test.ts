import { describe, expect, it } from "bun:test";
import { registerPiVccCommand } from "../src/commands/pi-vcc";
import { PI_VCC_COMPACT_INSTRUCTION } from "../src/core/compact-args";

const createHarness = () => {
	const commands: Record<string, any> = {};
	const compactCalls: any[] = [];
	const notifications: any[] = [];
	const sentUserMessages: any[] = [];
	const boundaryRequests: any[] = [];
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
		boundaryRequests,
		setIdle: (value: boolean) => { idle = value; },
		ctx: {
			isIdle: () => idle,
			requestCompactionAtTurnBoundary: (options: any) => { boundaryRequests.push(options); return true; },
			compact: (options: any) => compactCalls.push(options),
			ui: { notify: (message: string, level: string) => notifications.push({ message, level }) },
			sessionManager: {},
		},
	};
};

describe("/pi-vcc command", () => {
	it("requests a manual compaction without restarting the agent run", async () => {
		const harness = createHarness();
		await harness.commands["pi-vcc"].handler("keep:2", harness.ctx);

		expect(harness.compactCalls).toHaveLength(1);
		expect(harness.compactCalls[0].customInstructions).toBe(`${PI_VCC_COMPACT_INSTRUCTION}\nkeep:2`);
	});

	it("uses the safe boundary when invoked during an active run", async () => {
		const harness = createHarness();
		harness.setIdle(false);
		await harness.commands["pi-vcc"].handler("keep:2", harness.ctx);

		expect(harness.compactCalls).toHaveLength(0);
		expect(harness.boundaryRequests).toEqual([{
			reason: "manual",
			customInstructions: `${PI_VCC_COMPACT_INSTRUCTION}\nkeep:2`,
		}]);
	});

	it("shows stats and sends an explicit follow-up only after completion", async () => {
		const harness = createHarness();
		await harness.commands["pi-vcc"].handler("keep:1 inspect the result", harness.ctx);
		harness.compactCalls[0].onComplete?.();

		expect(harness.notifications.at(-1)?.message).toContain("Compacted with pi-vcc");
		expect(harness.sentUserMessages).toEqual([
		{ message: "inspect the result", options: { deliverAs: "steer" } },
		]);
	});

	it("reports failure without submitting a hidden follow-up", async () => {
		const harness = createHarness();
		await harness.commands["pi-vcc"].handler("", harness.ctx);
		harness.compactCalls[0].onError?.(new Error("summary failed"));

		expect(harness.sentUserMessages).toHaveLength(0);
		expect(harness.notifications.at(-1)).toMatchObject({ level: "error" });
	});
});
