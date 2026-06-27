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

const isStaleAutoCompactionPercent = (percent: number, lastPercent: number | undefined) =>
  lastPercent !== undefined && percent === lastPercent;

export default function (pi: ExtensionAPI) {
  let compactionInFlight = false;
  let lastAutoCompactionPercent: number | undefined;
  let awaitingPostCompactionAssistantResponse = false;

  const finishCompaction = (options: { compacted?: boolean } = {}) => {
    compactionInFlight = false;
    if (options.compacted) awaitingPostCompactionAssistantResponse = true;
  };

  const triggerCompaction = (
    ctx: ExtensionContext,
    options: {
      customInstructions?: string;
      startMessage: string;
      completionMessage: string;
      ratchetPercent?: number;
    },
  ) => {
    if (compactionInFlight) return false;
    if (!isPiVccLoaded()) {
      notifyMissingPiVcc(ctx);
      return false;
    }

    compactionInFlight = true;
    ctx.ui.notify(options.startMessage, "info");
    ctx.compact({
      customInstructions: options.customInstructions,
      onComplete: () => {
        if (options.ratchetPercent !== undefined) lastAutoCompactionPercent = options.ratchetPercent;
        finishCompaction({ compacted: true });
        ctx.ui.notify(options.completionMessage, "info");
      },
      onError: (err: Error) => {
        finishCompaction();
        if (err.message === "Already compacted" || err.message === "Nothing to compact (session too small)") {
          if (options.ratchetPercent !== undefined) lastAutoCompactionPercent = options.ratchetPercent;
          ctx.ui.notify("Nothing to compact", "info");
        } else {
          ctx.ui.notify(`Compaction failed: ${err.message}`, "error");
        }
      },
    });
    return true;
  };

  // Register /compact-now command for manual triggering
  pi.registerCommand("compact-now", {
    description: "Trigger compaction immediately with optional custom instructions",
    handler: async (args, ctx: ExtensionContext) => {
      const customInstructions = args.trim();
      const usage = ctx.getContextUsage();
      triggerCompaction(ctx, {
        customInstructions: customInstructions
          ? `${PI_VCC_MANUAL_BYPASS_MARKER}\n${customInstructions}`
          : PI_VCC_MANUAL_BYPASS_MARKER,
        startMessage: "Compacting context...",
        completionMessage: "Compaction complete",
        ratchetPercent: usage?.percent ?? undefined,
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

  // Monitor context usage at LLM turn boundaries. Only compact after a completed
  // assistant response; compacting after tool-use turns interrupts active agent
  // work and depends on continuation recovery to avoid a visible pause.
  pi.on("turn_end", async (event: TurnEndEvent, ctx: ExtensionContext) => {
    const usage = ctx.getContextUsage();
    if (!usage || usage.percent === null) return;

    const usagePercent = usage.percent;
    const currentPercent = Math.floor(usagePercent);
    const threshold = COMPACTION_THRESHOLD_PERCENT;
    const completedResponse = isCompletedAssistantResponse(event.message);

    if (usagePercent < threshold) {
      lastAutoCompactionPercent = undefined;
      awaitingPostCompactionAssistantResponse = false;
      return;
    }

    if (compactionInFlight) return;
    if (!completedResponse) return;
    if (awaitingPostCompactionAssistantResponse) {
      awaitingPostCompactionAssistantResponse = false;
    }
    if (isStaleAutoCompactionPercent(usagePercent, lastAutoCompactionPercent)) return;

    triggerCompaction(ctx, {
      customInstructions: PI_VCC_MANUAL_BYPASS_MARKER,
      startMessage: `✓ Auto-compacting at ${currentPercent}% (threshold: ${threshold}%)`,
      completionMessage: "Compacted with pi-vcc",
      ratchetPercent: usagePercent,
    });
  });

  pi.on("session_compact", async () => {
    finishCompaction({ compacted: true });
  });

  // Intercept core auto-compaction - gate it by the percentage threshold.
  pi.on("session_before_compact", async (event: SessionBeforeCompactEvent, ctx: ExtensionContext) => {
    const usage = ctx.getContextUsage();
    if (!usage || usage.percent === null) return;

    const manualPiVccBypass = event.customInstructions?.startsWith(PI_VCC_MANUAL_BYPASS_MARKER) ?? false;
    if (manualPiVccBypass) {
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
      lastAutoCompactionPercent = undefined;
      awaitingPostCompactionAssistantResponse = false;
      ctx.ui.notify(
        `⏸️ Delayed auto-compaction: ${Math.floor(usage.percent)}% < ${COMPACTION_THRESHOLD_PERCENT}% threshold`,
        "info",
      );
      return { cancel: true };
    }

    if (awaitingPostCompactionAssistantResponse) {
      ctx.ui.notify(
        "⏸️ Delayed auto-compaction: waiting for the next assistant response after the last pi-vcc compaction",
        "info",
      );
      return { cancel: true };
    }

    if (isStaleAutoCompactionPercent(usage.percent, lastAutoCompactionPercent)) {
      ctx.ui.notify(
        `⏸️ Delayed auto-compaction: context usage is unchanged at ${usage.percent}% since the last pi-vcc compaction`,
        "info",
      );
      return { cancel: true };
    }

    if (!isPiVccLoaded()) {
      notifyMissingPiVcc(ctx);
      return { cancel: true };
    }

    lastAutoCompactionPercent = usage.percent;
    awaitingPostCompactionAssistantResponse = true;
    ctx.ui.notify(
      `✓ Auto-compacting at ${Math.floor(usage.percent)}% (threshold: ${COMPACTION_THRESHOLD_PERCENT}%)`,
      "info",
    );
  });
}
