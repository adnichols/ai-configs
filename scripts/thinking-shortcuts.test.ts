import { beforeAll, describe, expect, mock, test } from "bun:test";

const supportedLevels = ["off", "low", "medium", "high"] as const;

mock.module("@earendil-works/pi-ai", () => ({
	getSupportedThinkingLevels: () => [...supportedLevels],
}));

let thinkingShortcuts: typeof import("../_pi/extensions/thinking-shortcuts").default;
let nextThinkingLevel: typeof import("../_pi/extensions/thinking-shortcuts").nextThinkingLevel;

beforeAll(async () => {
	({ default: thinkingShortcuts, nextThinkingLevel } = await import(
		"../_pi/extensions/thinking-shortcuts"
	));
});

type ShortcutHandler = (ctx: any) => Promise<void>;

function setup(initialLevel = "medium", reasoning = true) {
	let currentLevel = initialLevel;
	const shortcuts = new Map<string, ShortcutHandler>();
	const notifications: Array<{ message: string; level: string }> = [];

	thinkingShortcuts({
		getThinkingLevel: () => currentLevel,
		setThinkingLevel: (level: string) => {
			currentLevel = level;
		},
		registerShortcut: (key: string, options: { handler: ShortcutHandler }) => {
			shortcuts.set(key, options.handler);
		},
	} as any);

	const ctx = {
		model: { reasoning },
		ui: {
			notify: (message: string, level: string) => {
				notifications.push({ message, level });
			},
		},
	};

	return {
		ctx,
		shortcuts,
		notifications,
		getLevel: () => currentLevel,
	};
}

describe("thinking shortcut level selection", () => {
	test("moves in both directions", () => {
		expect(nextThinkingLevel(supportedLevels, "medium", -1)).toBe("low");
		expect(nextThinkingLevel(supportedLevels, "medium", 1)).toBe("high");
	});

	test("stops at the supported boundaries", () => {
		expect(nextThinkingLevel(supportedLevels, "off", -1)).toBe("off");
		expect(nextThinkingLevel(supportedLevels, "high", 1)).toBe("high");
	});
});

describe("thinking shortcut registration", () => {
	test("Alt+, decreases and Alt+. increases thinking", async () => {
		const state = setup();
		expect([...state.shortcuts.keys()].sort()).toEqual(["alt+,", "alt+."]);

		await state.shortcuts.get("alt+,")!(state.ctx);
		expect(state.getLevel()).toBe("low");
		expect(state.notifications.at(-1)?.message).toBe("Thinking: low");

		await state.shortcuts.get("alt+.")!(state.ctx);
		expect(state.getLevel()).toBe("medium");
		expect(state.notifications.at(-1)?.message).toBe("Thinking: medium");
	});

	test("does not change a non-reasoning model", async () => {
		const state = setup("off", false);
		await state.shortcuts.get("alt+.")!(state.ctx);
		expect(state.getLevel()).toBe("off");
		expect(state.notifications.at(-1)).toEqual({
			message: "Current model does not support thinking",
			level: "warning",
		});
	});
});
