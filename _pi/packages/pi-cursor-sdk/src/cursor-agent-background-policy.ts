/**
 * Cursor Grok/Composer foreground `Agent` calls share the parent MCP CallTool
 * AbortSignal. Spurious bridge cancels mark the child stopped ("STOPPED BY THE
 * USER") and abort the parent turn. Background Agent launches do not wire that
 * parent abort into the child.
 */

export const CURSOR_AGENT_BACKGROUND_POLICY_MODELS = ["grok", "composer"] as const;

export function normalizeCursorSdkModelId(modelId: string | undefined): string {
	return (modelId ?? "").trim().toLowerCase();
}

/** True for Cursor SDK model ids such as grok-4.5 / composer-2.5 / composer-2-5. */
export function isCursorGrokOrComposerModelId(modelId: string | undefined): boolean {
	const normalized = normalizeCursorSdkModelId(modelId);
	if (!normalized) return false;
	// Strip optional provider prefix if a pi-style id ever reaches this path.
	const bare = normalized.includes("/") ? normalized.slice(normalized.lastIndexOf("/") + 1) : normalized;
	return CURSOR_AGENT_BACKGROUND_POLICY_MODELS.some(
		(token) => bare === token || bare.startsWith(`${token}-`) || bare.startsWith(`${token}_`),
	);
}

export function shouldForcePiAgentBackground(modelId: string | undefined): boolean {
	return isCursorGrokOrComposerModelId(modelId);
}

export function isPiAgentToolName(piToolName: string): boolean {
	return piToolName === "Agent";
}

/**
 * Force `run_in_background: true` for bridged `Agent` when the parent Cursor
 * model is Grok or Composer. Leaves other tools and models unchanged.
 */
export function applyForcedAgentBackgroundArgs(
	piToolName: string,
	args: Record<string, unknown>,
	modelId: string | undefined,
): { args: Record<string, unknown>; forced: boolean } {
	if (!isPiAgentToolName(piToolName) || !shouldForcePiAgentBackground(modelId)) {
		return { args, forced: false };
	}
	if (args.run_in_background === true) {
		return { args, forced: false };
	}
	return {
		args: { ...args, run_in_background: true },
		forced: true,
	};
}

export function getCursorGrokComposerAgentBackgroundGuidanceText(): string {
	return [
		"Cursor Grok/Composer Agent policy:",
		"For pi__Agent (and Agent), always set run_in_background: true.",
		"The bridge also forces background for Agent on these models so a cancelled MCP CallTool cannot mark the child stopped.",
		"After Agent returns a background agent id, call get_subagent_result / pi__get_subagent_result with wait: true for that id before treating the review as complete.",
		"Do not rely on the deferred completion notification alone for required reviews.",
	].join("\n");
}
