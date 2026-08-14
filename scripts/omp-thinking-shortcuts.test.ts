import { beforeAll, describe, expect, test } from "bun:test";

let thinkingShortcuts: typeof import("../_omp/extensions/thinking-shortcuts").default;
let nextThinkingLevel: typeof import("../_omp/extensions/thinking-shortcuts").nextThinkingLevel;

beforeAll(async () => {
	({ default: thinkingShortcuts, nextThinkingLevel } = await import("../_omp/extensions/thinking-shortcuts"));
});

const supportedLevels = ["off", "low", "medium", "high"] as const;

describe("OMP thinking shortcuts", () => {
	test("moves in both directions and stops at supported boundaries", () => {
		expect(nextThinkingLevel(supportedLevels, "medium", -1)).toBe("low");
		expect(nextThinkingLevel(supportedLevels, "medium", 1)).toBe("high");
		expect(nextThinkingLevel(supportedLevels, "off", -1)).toBe("off");
		expect(nextThinkingLevel(supportedLevels, "high", 1)).toBe("high");
	});

	test("registers Option-comma and Option-period handlers", async () => {
		let currentLevel = "medium";
		const shortcuts = new Map<string, { handler: (ctx: unknown) => void }>();
		const notifications: string[] = [];
		const pi = {
			registerShortcut(key: string, options: { handler: (ctx: unknown) => void }) {
				shortcuts.set(key, options);
			},
			getThinkingLevel: () => currentLevel,
			setThinkingLevel(level: string) {
				currentLevel = level;
			},
		};

		thinkingShortcuts(pi as never);
		const context = {
			model: { reasoning: true, thinking: { efforts: [...supportedLevels] } },
			ui: { notify: (message: string) => notifications.push(message) },
		};

		await shortcuts.get("alt+,")?.handler(context);
		expect(currentLevel).toBe("low");
		await shortcuts.get("alt+.")?.handler(context);
		expect(currentLevel).toBe("medium");
		expect(notifications).toEqual(["Thinking: low", "Thinking: medium"]);
	});

	test("warns for models without controllable thinking", async () => {
		const notifications: string[] = [];
		const registered = new Map<string, { handler: (ctx: unknown) => void }>();
		const registeringPi = {
			getThinkingLevel: () => "medium",
			setThinkingLevel() {},
			registerShortcut(key: string, options: { handler: (ctx: unknown) => void }) {
				registered.set(key, options);
			},
		};
		thinkingShortcuts(registeringPi as never);
		const context = {
			model: { reasoning: false },
			ui: { notify: (message: string) => notifications.push(message) },
		};
		await registered.get("alt+.")?.handler(context);
		expect(notifications).toEqual(["Current model does not support thinking"]);
	});
});
