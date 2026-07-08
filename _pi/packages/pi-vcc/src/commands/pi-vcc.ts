import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { getLastCompactionStats } from "../hooks/before-compact";
import { buildPiVccCustomInstructions, parseKeepAndPrompt } from "../core/compact-args";
import { PI_VCC_LOG_PATH, logPiVccError, logPiVccEvent } from "../core/log";

const formatTokens = (n: number): string => {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
};

export const registerPiVccCommand = (pi: ExtensionAPI) => {
  pi.registerCommand("pi-vcc", {
    description: "Compact conversation with pi-vcc structured summary",
    handler: async (args, ctx) => {
      const { followUpPrompt, keepUserTurns } = parseKeepAndPrompt(args);
      ctx.compact({
        customInstructions: buildPiVccCustomInstructions(keepUserTurns),
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
          if (followUpPrompt) {
            try {
              void Promise.resolve(pi.sendUserMessage(followUpPrompt)).catch(() => {});
            } catch {}
          }
        },
        onError: (err) => {
          if (err.message === "Compaction cancelled" || err.message === "Already compacted") {
            ctx.ui.notify("Nothing to compact", "info");
          } else {
            logPiVccError("manual_compaction_failed", err, { logPath: PI_VCC_LOG_PATH });
            ctx.ui.notify(`Compaction failed: ${err.message} (logged to ${PI_VCC_LOG_PATH})`, "error");
          }
        },
      });
    },
  });
};
