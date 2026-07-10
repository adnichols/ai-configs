import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import {
	buildPiVccCustomInstructions,
	parseKeepAndPrompt,
} from "../core/compact-args";
import type { ContinuationCoordinator } from "../core/coordinator";
import { logPiVccError, logPiVccEvent, PI_VCC_LOG_PATH } from "../core/log";
import { getLastCompactionStats } from "../hooks/before-compact";

const formatTokens = (n: number): string => {
	if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
	return String(n);
};

export const registerPiVccCommand = (
	pi: ExtensionAPI,
	coordinator: ContinuationCoordinator,
) => {
	pi.registerCommand("pi-vcc", {
		description: "Compact conversation with pi-vcc structured summary",
		handler: async (args, ctx) => {
			const { followUpPrompt, keepUserTurns } = parseKeepAndPrompt(args);
			const attemptId = `package-${Date.now().toString(36)}`;
			ctx.compact({
				customInstructions: buildPiVccCustomInstructions(
					keepUserTurns,
					JSON.stringify({
						source: "package-pi-vcc",
						attemptId,
						resumePolicy: followUpPrompt ? "terminal" : "active",
					}),
				),
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
					coordinator.request(
						{
							initiator: "package-pi-vcc",
							outcome: "compacted",
							attemptId,
							resumePolicy: followUpPrompt ? "terminal" : "active",
						},
						ctx,
					);
					if (followUpPrompt) {
						try {
							pi.sendUserMessage(followUpPrompt, { deliverAs: "steer" });
						} catch (err) {
							logPiVccError("manual_follow_up_failed", err, { attemptId });
						}
					}
				},
				onError: (err) => {
					const legacyOutcome =
						err.message === "Compaction cancelled"
							? "cancellation"
							: err.message === "Already compacted" ||
									err.message === "Nothing to compact (session too small)"
								? "no-safe-cut"
								: "failure";
					if (
						legacyOutcome === "cancellation" ||
						legacyOutcome === "no-safe-cut"
					) {
						ctx.ui.notify("Nothing to compact", "info");
					} else {
						logPiVccError("manual_compaction_failed", err, {
							logPath: PI_VCC_LOG_PATH,
						});
						ctx.ui.notify(
							`Compaction failed: ${err.message} (logged to ${PI_VCC_LOG_PATH})`,
							"error",
						);
					}
					coordinator.request(
						{
							initiator: "package-pi-vcc",
							outcome: legacyOutcome,
							attemptId,
							resumePolicy: followUpPrompt ? "terminal" : "active",
						},
						ctx,
					);
				},
			});
		},
	});
};
