import type {
	ExtensionAPI,
	ExtensionContext,
} from "@earendil-works/pi-coding-agent";
import {
	getSupportedThinkingLevels,
	type ModelThinkingLevel,
} from "@earendil-works/pi-ai";

export type ThinkingDirection = -1 | 1;

export function nextThinkingLevel(
	levels: readonly ModelThinkingLevel[],
	current: ModelThinkingLevel,
	direction: ThinkingDirection,
): ModelThinkingLevel | undefined {
	if (levels.length === 0) return undefined;

	const currentIndex = levels.indexOf(current);
	const startIndex = currentIndex >= 0 ? currentIndex : 0;
	const nextIndex = Math.max(
		0,
		Math.min(levels.length - 1, startIndex + direction),
	);
	return levels[nextIndex];
}

export default function thinkingShortcuts(pi: ExtensionAPI): void {
	const changeThinking = (
		ctx: ExtensionContext,
		direction: ThinkingDirection,
	): void => {
		if (!ctx.model?.reasoning) {
			ctx.ui.notify("Current model does not support thinking", "warning");
			return;
		}

		const levels = getSupportedThinkingLevels(ctx.model);
		const current = pi.getThinkingLevel();
		const next = nextThinkingLevel(levels, current, direction);

		if (!next || next === current) {
			ctx.ui.notify(`Thinking already at ${current}`, "info");
			return;
		}

		pi.setThinkingLevel(next);
		ctx.ui.notify(`Thinking: ${pi.getThinkingLevel()}`, "info");
	};

	pi.registerShortcut("alt+,", {
		description: "Decrease thinking level",
		handler: async (ctx) => changeThinking(ctx, -1),
	});

	pi.registerShortcut("alt+.", {
		description: "Increase thinking level",
		handler: async (ctx) => changeThinking(ctx, 1),
	});
}
