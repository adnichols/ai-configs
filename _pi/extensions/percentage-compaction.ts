import type {
  ExtensionAPI,
  ExtensionContext,
  SessionBeforeCompactEvent,
  TurnEndEvent,
} from "@mariozechner/pi-coding-agent";

// Configure your threshold here (0-100)
export const COMPACTION_THRESHOLD_PERCENT = 60;
export const PI_VCC_MANUAL_BYPASS_MARKER = "__PI_VCC_MANUAL_BYPASS__";
export const PI_VCC_LOAD_MARKER = "__ADN_PI_VCC_LOADED__";

const isPiVccLoaded = () => Boolean((globalThis as any)[PI_VCC_LOAD_MARKER]);

const notifyMissingPiVcc = (ctx: ExtensionContext) => {
  ctx.ui.notify(
    "Pi-vcc is not loaded; canceling compaction to avoid unsafe default compaction. Run ./install.sh --pi and restart Pi.",
    "error",
  );
};

const isCompletedAssistantResponse = (message: TurnEndEvent["message"]) => {
  if (message.role !== "assistant") return false;
  return !("stopReason" in message && message.stopReason === "toolUse");
};

export default function (pi: ExtensionAPI) {
  let warnedAtThreshold = false;
  let allowNextManualCompaction = false;
  let compactionInFlight = false;
  let awaitingPostCompactionUsage = false;
  let lastAssistantWasOverThreshold = false;

  const finishCompaction = () => {
    allowNextManualCompaction = false;
    compactionInFlight = false;
    warnedAtThreshold = false;
  };

  const markCompacted = () => {
    finishCompaction();
    awaitingPostCompactionUsage = true;
    lastAssistantWasOverThreshold = false;
  };

  const triggerCompaction = (
    ctx: ExtensionContext,
    options: {
      customInstructions?: string;
      bypassThreshold?: boolean;
      startMessage: string;
      completionMessage: string;
    },
  ) => {
    if (compactionInFlight) return;
    if (!isPiVccLoaded()) {
      notifyMissingPiVcc(ctx);
      return;
    }

    if (options.bypassThreshold) {
      allowNextManualCompaction = true;
    }
    compactionInFlight = true;
    ctx.ui.notify(options.startMessage, "info");
    ctx.compact({
      customInstructions: options.customInstructions,
      onComplete: () => {
        finishCompaction();
        ctx.ui.notify(options.completionMessage, "info");
      },
      onError: (err: Error) => {
        finishCompaction();
        if (err.message === "Already compacted" || err.message === "Nothing to compact (session too small)") {
          ctx.ui.notify("Nothing to compact", "info");
        } else {
          ctx.ui.notify(`Compaction failed: ${err.message}`, "error");
        }
      },
    });
  };

  // Register /compact-now command for manual triggering
  pi.registerCommand("compact-now", {
    description: "Trigger compaction immediately with optional custom instructions",
    handler: async (args, ctx: ExtensionContext) => {
      const customInstructions = args.trim() || undefined;
      triggerCompaction(ctx, {
        customInstructions,
        bypassThreshold: true,
        startMessage: "Compacting context...",
        completionMessage: "Compaction complete",
      });
    },
  });

  // Register /compact-status command to check current usage
  pi.registerCommand("compact-status", {
    description: "Show current context usage percentage",
    handler: async (_args, ctx: ExtensionContext) => {
      const usage = ctx.getContextUsage();
      if (!usage || usage.percent === null) {
        ctx.ui.notify("Context usage: unknown", "warning");
        return;
      }
      ctx.ui.notify(
        `Context: ${Math.floor(usage.percent)}% of ${usage.contextWindow.toLocaleString()} tokens ` +
          `(threshold: ${COMPACTION_THRESHOLD_PERCENT}%)`,
        "info",
      );
    },
  });

  // Monitor context usage at every LLM/tool turn boundary. If the threshold is
  // crossed during a tool-driven agent run, compact immediately after the current
  // tool turn instead of waiting for the whole user prompt to finish; pi-vcc will
  // resume the agent after the in-flight compaction completes.
  pi.on("turn_end", async (event: TurnEndEvent, ctx: ExtensionContext) => {
    const isAssistantWithUsage =
      event.message.role === "assistant" && Boolean((event.message as any).usage);

    if (awaitingPostCompactionUsage) {
      if (!isAssistantWithUsage) return;
      awaitingPostCompactionUsage = false;
    }

    const usage = ctx.getContextUsage();
    if (!usage || usage.percent === null) return;

    const currentPercent = Math.floor(usage.percent);
    const threshold = COMPACTION_THRESHOLD_PERCENT;

    if (isAssistantWithUsage) {
      lastAssistantWasOverThreshold = currentPercent >= threshold;
    } else if (!lastAssistantWasOverThreshold) {
      return;
    }

    if (currentPercent < threshold) {
      warnedAtThreshold = false;
      return;
    }

    if (compactionInFlight) return;

    warnedAtThreshold = true;
    const completedResponse = isCompletedAssistantResponse(event.message);
    triggerCompaction(ctx, {
      customInstructions: PI_VCC_MANUAL_BYPASS_MARKER,
      bypassThreshold: true,
      startMessage: completedResponse
        ? `✓ Auto-compacting at ${currentPercent}% (threshold: ${threshold}%)`
        : `↻ Context at ${currentPercent}% (threshold: ${threshold}%). Interrupting agent for pi-vcc compaction...`,
      completionMessage: "Compacted with pi-vcc",
    });
  });

  pi.on("session_compact", async () => {
    markCompacted();
  });

  // Intercept core auto-compaction - gate it by the percentage threshold.
  pi.on("session_before_compact", async (event: SessionBeforeCompactEvent, ctx: ExtensionContext) => {
    const usage = ctx.getContextUsage();
    if (!usage || usage.percent === null) return;

    const manualPiVccBypass = event.customInstructions?.startsWith(PI_VCC_MANUAL_BYPASS_MARKER) ?? false;
    if (allowNextManualCompaction || manualPiVccBypass) {
      allowNextManualCompaction = false;
      if (!isPiVccLoaded()) {
        notifyMissingPiVcc(ctx);
        return { cancel: true };
      }
      ctx.ui.notify(
        `✓ Compaction bypassed ${COMPACTION_THRESHOLD_PERCENT}% threshold at ${Math.floor(usage.percent)}%`,
        "info",
      );
      return;
    }

    if (usage.percent < COMPACTION_THRESHOLD_PERCENT) {
      ctx.ui.notify(
        `⏸️ Delayed auto-compaction: ${Math.floor(usage.percent)}% < ${COMPACTION_THRESHOLD_PERCENT}% threshold`,
        "info",
      );
      return { cancel: true };
    }

    if (!isPiVccLoaded()) {
      notifyMissingPiVcc(ctx);
      return { cancel: true };
    }

    ctx.ui.notify(
      `✓ Auto-compacting at ${Math.floor(usage.percent)}% (threshold: ${COMPACTION_THRESHOLD_PERCENT}%)`,
      "info",
    );
  });
}
