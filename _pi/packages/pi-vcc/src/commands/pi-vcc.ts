import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { buildPiVccCustomInstructions, parseKeepAndPrompt } from "../core/compact-args";
import { logPiVccError, logPiVccEvent, PI_VCC_LOG_PATH } from "../core/log";
import { getLastCompactionStats } from "../hooks/before-compact";

const formatTokens = (n: number): string => (n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n));

export const registerPiVccCommand = (pi: ExtensionAPI) => {
	pi.registerCommand("pi-vcc", {
		description: "Compact conversation with pi-vcc structured summary",
		handler: async (args, ctx) => {
			const { followUpPrompt: focusPrompt, keepUserTurns } = parseKeepAndPrompt(args);
			const customInstructions = buildPiVccCustomInstructions(
				keepUserTurns,
				focusPrompt ? JSON.stringify({ source: "pi-vcc-command", preserve: focusPrompt }) : undefined,
			);
			if (!ctx.isIdle()) {
				ctx.ui.notify(
					"/pi-vcc only runs while Pi is idle. Use compact_context to request settled-run maintenance without aborting the active response.",
					"warning",
				);
				return;
			}
			ctx.compact({
				customInstructions,
				onComplete: () => {
					const stats = getLastCompactionStats();
					logPiVccEvent("manual_compaction_complete", { stats });
					if (stats) {
						ctx.ui.notify(
							`Compacted ${stats.summarized} msgs | Kept last ${stats.kept} msgs [~${formatTokens(stats.keptTokensEst)} toks]`,
							"info",
						);
					} else {
						ctx.ui.notify("Compacted with pi-vcc", "info");
					}
				},
				onError: (error) => {
					logPiVccError("manual_compaction_failed", error, { logPath: PI_VCC_LOG_PATH });
					ctx.ui.notify(`Compaction failed: ${error.message} (logged to ${PI_VCC_LOG_PATH})`, "error");
				},
			});
		},
	});
};
