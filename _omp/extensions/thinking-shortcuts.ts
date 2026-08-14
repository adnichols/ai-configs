import type { ExtensionAPI, ExtensionContext } from "@oh-my-pi/pi-coding-agent";
import type { ThinkingLevel } from "@oh-my-pi/pi-agent-core";

export type ThinkingDirection = -1 | 1;

export function nextThinkingLevel(
	levels: readonly ThinkingLevel[],
	current: ThinkingLevel | undefined,
	direction: ThinkingDirection,
): ThinkingLevel | undefined {
	if (levels.length === 0) return undefined;
	const currentIndex = current === undefined ? -1 : levels.indexOf(current);
	const startIndex = currentIndex >= 0 ? currentIndex : 0;
	const nextIndex = Math.max(0, Math.min(levels.length - 1, startIndex + direction));
	return levels[nextIndex];
}

function changeThinking(
	pi: ExtensionAPI,
	ctx: ExtensionContext,
	direction: ThinkingDirection,
): void {
	if (!ctx.model?.reasoning) {
		ctx.ui.notify("Current model does not support thinking", "warning");
		return;
	}

	const levels = ["off", ...(ctx.model.thinking?.efforts ?? [])] as readonly ThinkingLevel[];
	const current = pi.getThinkingLevel();
	const next = nextThinkingLevel(levels, current, direction);
	if (!next || next === current) {
		ctx.ui.notify(`Thinking already at ${current ?? "off"}`, "info");
		return;
	}

	pi.setThinkingLevel(next);
	ctx.ui.notify(`Thinking: ${pi.getThinkingLevel() ?? next}`, "info");
}

export default function thinkingShortcuts(pi: ExtensionAPI): void {
	pi.registerShortcut("alt+,", {
		description: "Decrease thinking level",
		handler: (ctx) => changeThinking(pi, ctx, -1),
	});
	pi.registerShortcut("alt+.", {
		description: "Increase thinking level",
		handler: (ctx) => changeThinking(pi, ctx, 1),
	});
}
