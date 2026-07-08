import type {
  ExtensionAPI,
  ExtensionContext,
  SessionBeforeCompactEvent,
  TurnEndEvent,
} from "@mariozechner/pi-coding-agent";
export const COMPACTION_NUDGE_PERCENT = 60;
export const COMPACTION_STRONG_NUDGE_PERCENT = 75;
export const HARD_AUTO_COMPACTION_PERCENT = 80;
export const FAILURE_DELAY_TURNS = 1;
export const COMPACTION_THRESHOLD_PERCENT = COMPACTION_NUDGE_PERCENT;
export const PI_VCC_MANUAL_BYPASS_MARKER = "__PI_VCC_MANUAL_BYPASS__";
export const PI_VCC_LOAD_MARKER = "__ADN_PI_VCC_LOADED__";

type NudgeBand = "soft" | "strong";
type Boundary = "subtask_complete" | "before_topic_switch" | "after_test_loop" | "manual_recovery";

interface PendingModelCompaction {
  reason: string;
  boundary: Boundary;
  preserve?: string;
  requestedTurn: number;
  toolCallId?: string;
  toolBatchId?: number;
  sawSiblingTools: boolean;
}

interface PendingNoCutContinuation {
  reason: "already_compacted" | "session_too_small";
  usagePercent?: number;
  flooredPercent?: number;
  pendingToolCallIds: Set<string>;
  queuedTurn: number;
  attempts: number;
  startedAt?: number;
  timer?: ReturnType<typeof setTimeout>;
  lastError?: string;
}

interface InterruptedCompactionTurn {
  interrupted: boolean;
  pendingToolCallIds: Set<string>;
  reason: "hard_backstop" | "compact_context" | "core_deferred" | "compaction_error";
}

interface PendingCompactionContinuation {
  attemptId: number;
  reason: "cancelled" | "failed";
  interrupted: InterruptedCompactionTurn;
  queuedTurn: number;
  attempts: number;
  startedAt?: number;
  timer?: ReturnType<typeof setTimeout>;
  lastError?: string;
}

type CompactionOwner = "pi-vcc" | "core" | undefined;

interface NoCutRecoveryOptions {
  interruptedActiveTurn: boolean;
  pendingToolCallIds: () => string[];
  usagePercent?: number;
}

interface NoCutRetryState {
  flooredPercent: number;
  usagePercent?: number;
  userMessageCount: number;
  reason: "already_compacted" | "session_too_small";
}

const NO_CUT_CONTINUATION_DELAY_MS = 50;
const NO_CUT_CONTINUATION_MAX_WAIT_MS = 5000;
const NO_CUT_CONTINUATION_RETRY_MS = 100;
const COMPACTION_CONTINUATION_DELAY_MS = NO_CUT_CONTINUATION_DELAY_MS;
const COMPACTION_CONTINUATION_MAX_WAIT_MS = NO_CUT_CONTINUATION_MAX_WAIT_MS;
const COMPACTION_CONTINUATION_RETRY_MS = NO_CUT_CONTINUATION_RETRY_MS;

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

const isInterruptedAgentWork = (message: TurnEndEvent["message"]) =>
  (message.role === "assistant" && "stopReason" in message && message.stopReason === "toolUse") ||
  message.role === "toolResult";

const isStaleAutoCompactionPercent = (percent: number, lastPercent: number | undefined) =>
  lastPercent !== undefined && percent === lastPercent;

const clampText = (value: unknown, max = 500): string | undefined => {
  if (typeof value !== "string") return undefined;
  const trimmed = value.trim();
  return trimmed ? trimmed.slice(0, max) : undefined;
};

const messageText = (message: any): string => {
  const content = message?.content;
  if (typeof content === "string") return content;
  if (Array.isArray(content)) {
    return content.map((part) => {
      if (typeof part?.text === "string") return part.text;
      if (typeof part?.content === "string") return part.content;
      return "";
    }).join("\n");
  }
  return "";
};

const hasFailureOutput = (message: any): boolean => {
  if (message?.role !== "toolResult") return false;
  if (message.isError === true) return true;
  const text = messageText(message);
  return /\b(nonzero|failed|failure|error|exception|tests? failed|exit code [1-9])\b/i.test(text);
};

const toolCallCount = (message: any): number => {
  if (message?.role !== "assistant" || !Array.isArray(message?.content)) return 0;
  return message.content.filter((part: any) => part?.type === "toolCall").length;
};

const assistantToolCallIds = (message: any): string[] => {
  if (message?.role !== "assistant" || !Array.isArray(message?.content)) return [];
  return message.content
    .filter((part: any) => part?.type === "toolCall" && typeof part?.id === "string")
    .map((part: any) => part.id);
};

const assistantToolBatchIncludes = (message: any, toolCallId: string | undefined): boolean => {
  if (!toolCallId || message?.role !== "assistant" || !Array.isArray(message?.content)) return false;
  return message.content.some((part: any) => part?.type === "toolCall" && part?.id === toolCallId);
};

const toolResultMatches = (result: any, toolCallId: string | undefined): boolean =>
  Boolean(toolCallId && result?.toolCallId === toolCallId);

const deliveredToolCallIds = (event: TurnEndEvent): string[] => {
  const ids = new Set<string>();
  const add = (result: any) => {
    if (typeof result?.toolCallId === "string") ids.add(result.toolCallId);
  };
  add(event.message);
  if (Array.isArray(event.toolResults)) event.toolResults.forEach(add);
  return [...ids];
};

const buildIntentInstructions = (pending: PendingModelCompaction) =>
  `${PI_VCC_MANUAL_BYPASS_MARKER}\n${JSON.stringify({
    source: "compact_context",
    reason: pending.reason,
    boundary: pending.boundary,
    ...(pending.preserve ? { preserve: pending.preserve } : {}),
  })}`;

const canRunPendingCompaction = (
  pending: PendingModelCompaction,
  event: TurnEndEvent,
  pendingToolResultDelivered: boolean,
) => {
  if (pending.sawSiblingTools) return isCompletedAssistantResponse(event.message);
  if (pendingToolResultDelivered) return true;
  return isCompletedAssistantResponse(event.message);
};

const TERMINAL_SUBTASK_TEXT =
  /\b(done|completed?|final|handoff|PR ready|branch clean|mergeable|awaiting user|blocked|stopped?|do not continue|no auto-resume)\b/i;
const ACTIVE_SUBTASK_TEXT =
  /\b(continue|next steps?|next:|remaining|active|open todos?|run-plan active|in_progress|still running)\b/i;

const shouldResumeAfterCompactContext = (pending: PendingModelCompaction): boolean => {
  if (
    pending.boundary === "after_test_loop" ||
    pending.boundary === "before_topic_switch" ||
    pending.boundary === "manual_recovery"
  ) {
    return true;
  }

  const text = `${pending.reason}\n${pending.preserve ?? ""}`;
  if (TERMINAL_SUBTASK_TEXT.test(text)) return false;

  return ACTIVE_SUBTASK_TEXT.test(text);
};

const buildResumeMessage = (pending: PendingModelCompaction) =>
  `Pi VCC compaction completed for an active ${pending.boundary} workflow. Continue from the preserved state. ` +
  "If the preserved state says the task is complete, blocked, stopped, or awaiting user input, " +
  "report that instead of doing more work.";

export default function (pi: ExtensionAPI) {
  let compactionInFlight = false;
  let lastAutoCompactionPercent: number | undefined;
  let lastNudgePercentBand: NudgeBand | undefined;
  let lastNudgeTurn: number | undefined;
  let pendingModelCompaction: PendingModelCompaction | undefined;
  let lastFailureTurn: number | undefined;
  let lastCompactionReason = "none";
  let uninterpretedFailure = false;
  let awaitingPostCompactionAssistantResponse = false;
  let turnCounter = 0;
  let lastToolBatchId = 0;
  let lastAssistantToolCallCount = 0;
  let outstandingAssistantToolCallIds = new Set<string>();
  let userMessageCount = 0;
  let pendingNoCutContinuation: PendingNoCutContinuation | undefined;
  let noCutRetryState: NoCutRetryState | undefined;
  let activeCompactionOwner: CompactionOwner;
  let scheduledPiVccCompaction: ReturnType<typeof setTimeout> | undefined;
  let nextCompactionAttemptId = 0;
  let currentCompactionAttemptId: number | undefined;
  let pendingCompactionContinuation: PendingCompactionContinuation | undefined;
  let deliveredCompactionContinuationAttemptId: number | undefined;

  const clearPendingNoCutContinuation = () => {
    if (pendingNoCutContinuation?.timer) clearTimeout(pendingNoCutContinuation.timer);
    pendingNoCutContinuation = undefined;
  };

  const clearPendingCompactionContinuation = () => {
    if (pendingCompactionContinuation?.timer) clearTimeout(pendingCompactionContinuation.timer);
    pendingCompactionContinuation = undefined;
  };

  const finishCompaction = (options: { compacted?: boolean } = {}) => {
    compactionInFlight = false;
    activeCompactionOwner = undefined;
    currentCompactionAttemptId = undefined;
    pendingModelCompaction = undefined;
    lastNudgePercentBand = undefined;
    if (scheduledPiVccCompaction) {
      clearTimeout(scheduledPiVccCompaction);
      scheduledPiVccCompaction = undefined;
    }
    if (options.compacted) awaitingPostCompactionAssistantResponse = true;
  };

  const buildNoCutContinuationMessage = (pending: PendingNoCutContinuation) =>
    `Pi VCC hard-backstop compaction was skipped because no safe compaction cut was available (${pending.reason}). ` +
    "Continue from where you left off; do not summarize this recovery message unless it changes the task state.";

  const sendPendingNoCutContinuation = (ctx: ExtensionContext) => {
    const pending = pendingNoCutContinuation;
    if (!pending) return;
    if (!pending.startedAt) pending.startedAt = Date.now();
    pending.attempts += 1;
    try {
      pi.sendMessage(
        {
          customType: "pi-vcc-no-cut-continuation",
          content: buildNoCutContinuationMessage(pending),
          display: true,
          details: {
            reason: pending.reason,
            usagePercent: pending.usagePercent,
            flooredPercent: pending.flooredPercent,
            queuedTurn: pending.queuedTurn,
            deliveryAttempts: pending.attempts,
            pendingToolResultCount: pending.pendingToolCallIds.size,
          },
        },
        { deliverAs: "steer", triggerTurn: true },
      );
      if (pending.timer) clearTimeout(pending.timer);
      pendingNoCutContinuation = undefined;
    } catch (err) {
      pending.lastError = (err as Error).message;
      const elapsed = Date.now() - pending.startedAt;
      if (elapsed < NO_CUT_CONTINUATION_MAX_WAIT_MS) {
        if (pending.timer) clearTimeout(pending.timer);
        pending.timer = setTimeout(() => sendPendingNoCutContinuation(ctx), NO_CUT_CONTINUATION_RETRY_MS);
        return;
      }
      if (pending.timer) clearTimeout(pending.timer);
      ctx.ui.notify(
        `No-cut continuation delivery failed after ${pending.attempts} attempts: ${pending.lastError}. Continue manually from the interrupted turn.`,
        "warning",
      );
      pendingNoCutContinuation = undefined;
    }
  };

  const queueNoCutContinuation = (
    ctx: ExtensionContext,
    reason: PendingNoCutContinuation["reason"],
    recovery: NoCutRecoveryOptions,
  ) => {
    if (!recovery.interruptedActiveTurn || pendingNoCutContinuation) return;
    pendingNoCutContinuation = {
      reason,
      usagePercent: recovery.usagePercent,
      flooredPercent: recovery.usagePercent === undefined ? undefined : Math.floor(recovery.usagePercent),
      pendingToolCallIds: new Set(recovery.pendingToolCallIds()),
      queuedTurn: turnCounter,
      attempts: 0,
    };
    if (pendingNoCutContinuation.pendingToolCallIds.size === 0) {
      pendingNoCutContinuation.timer = setTimeout(() => sendPendingNoCutContinuation(ctx), NO_CUT_CONTINUATION_DELAY_MS);
    }
  };

  const clearDeliveredNoCutTools = (event: TurnEndEvent) => {
    if (!pendingNoCutContinuation) return;
    for (const id of deliveredToolCallIds(event)) pendingNoCutContinuation.pendingToolCallIds.delete(id);
  };

  const noCutContinuationIsSafe = (event: TurnEndEvent) =>
    Boolean(pendingNoCutContinuation) &&
    (pendingNoCutContinuation.pendingToolCallIds.size === 0 || isCompletedAssistantResponse(event.message));

  const buildCompactionContinuationMessage = (pending: PendingCompactionContinuation) =>
    `Pi-vcc compaction did not complete cleanly (${pending.reason}), but the interrupted turn should continue. ` +
    "Continue from where you left off; use vcc_recall if needed.";

  const sendPendingCompactionContinuation = (ctx: ExtensionContext) => {
    const pending = pendingCompactionContinuation;
    if (!pending) return;
    if (!pending.startedAt) pending.startedAt = Date.now();
    pending.attempts += 1;
    try {
      pi.sendMessage(
        {
          customType: "pi-vcc-continuation",
          content: buildCompactionContinuationMessage(pending),
          display: false,
          details: {
            compactor: "pi-vcc",
            reason: pending.reason,
            attemptId: pending.attemptId,
            interruptedReason: pending.interrupted.reason,
            queuedTurn: pending.queuedTurn,
            deliveryAttempts: pending.attempts,
            pendingToolResultCount: pending.interrupted.pendingToolCallIds.size,
          },
        },
        { deliverAs: "steer", triggerTurn: true },
      );
      if (pending.timer) clearTimeout(pending.timer);
      deliveredCompactionContinuationAttemptId = pending.attemptId;
      pendingCompactionContinuation = undefined;
    } catch (err) {
      pending.lastError = (err as Error).message;
      const elapsed = Date.now() - pending.startedAt;
      if (elapsed < COMPACTION_CONTINUATION_MAX_WAIT_MS) {
        if (pending.timer) clearTimeout(pending.timer);
        pending.timer = setTimeout(() => sendPendingCompactionContinuation(ctx), COMPACTION_CONTINUATION_RETRY_MS);
        return;
      }
      if (pending.timer) clearTimeout(pending.timer);
      ctx.ui.notify(
        `Compaction continuation delivery failed after ${pending.attempts} attempts: ${pending.lastError}. Continue manually from the interrupted turn.`,
        "warning",
      );
      pendingCompactionContinuation = undefined;
    }
  };

  const queueCompactionContinuation = (
    ctx: ExtensionContext,
    attemptId: number,
    reason: PendingCompactionContinuation["reason"],
    interrupted: InterruptedCompactionTurn | undefined,
  ) => {
    if (!interrupted?.interrupted) return;
    if (deliveredCompactionContinuationAttemptId === attemptId) return;
    if (pendingCompactionContinuation?.attemptId === attemptId) return;
    pendingCompactionContinuation = {
      attemptId,
      reason,
      interrupted,
      queuedTurn: turnCounter,
      attempts: 0,
    };
    if (interrupted.pendingToolCallIds.size === 0) {
      pendingCompactionContinuation.timer = setTimeout(() => sendPendingCompactionContinuation(ctx), COMPACTION_CONTINUATION_DELAY_MS);
    }
  };

  const clearDeliveredCompactionContinuationTools = (event: TurnEndEvent) => {
    if (!pendingCompactionContinuation) return;
    for (const id of deliveredToolCallIds(event)) pendingCompactionContinuation.interrupted.pendingToolCallIds.delete(id);
  };

  const compactionContinuationIsSafe = (event: TurnEndEvent) =>
    Boolean(pendingCompactionContinuation) &&
    (pendingCompactionContinuation.interrupted.pendingToolCallIds.size === 0 || isCompletedAssistantResponse(event.message));

  const snapshotInterruptedCompactionTurn = (
    event: TurnEndEvent,
    reason: InterruptedCompactionTurn["reason"],
  ): InterruptedCompactionTurn => {
    const completedResponse = isCompletedAssistantResponse(event.message);
    return {
      interrupted: !completedResponse && isInterruptedAgentWork(event.message),
      pendingToolCallIds: new Set(completedResponse ? [] : [...outstandingAssistantToolCallIds]),
      reason,
    };
  };

  const triggerCompaction = (
    ctx: ExtensionContext,
    options: {
      customInstructions?: string;
      startMessage: string;
      completionMessage: string;
      ratchetPercent?: number;
      reason: string;
      resumeMessage?: string;
      noCutRecovery?: NoCutRecoveryOptions;
      interruptedTurn?: InterruptedCompactionTurn;
    },
  ) => {
    if (compactionInFlight) return false;
    if (!isPiVccLoaded()) {
      notifyMissingPiVcc(ctx);
      return false;
    }

    clearPendingNoCutContinuation();
    clearPendingCompactionContinuation();
    compactionInFlight = true;
    activeCompactionOwner = "pi-vcc";
    const attemptId = ++nextCompactionAttemptId;
    currentCompactionAttemptId = attemptId;
    deliveredCompactionContinuationAttemptId = undefined;
    lastCompactionReason = options.reason;
    ctx.ui.notify(options.startMessage, "info");
    ctx.compact({
      customInstructions: options.customInstructions,
      onComplete: () => {
        if (currentCompactionAttemptId !== attemptId) return;
        if (options.ratchetPercent !== undefined) lastAutoCompactionPercent = options.ratchetPercent;
        noCutRetryState = undefined;
        finishCompaction({ compacted: true });
        ctx.ui.notify(options.completionMessage, "info");
        if (options.resumeMessage) {
          try {
            pi.sendMessage(
              {
                customType: "compaction-resume",
                content: options.resumeMessage,
                display: true,
                details: { reason: options.reason },
              },
              { deliverAs: "followUp", triggerTurn: true },
            );
          } catch (err) {
            ctx.ui.notify(`Post-compaction resume delivery failed: ${(err as Error).message}`, "warning");
          }
        }
      },
      onError: (err: Error) => {
        const ownsCurrentAttempt = currentCompactionAttemptId === attemptId;
        const noCutReason = err.message === "Already compacted"
          ? "already_compacted"
          : err.message === "Nothing to compact (session too small)"
            ? "session_too_small"
            : undefined;
        if (noCutReason) {
          if (!ownsCurrentAttempt) return;
          if (options.ratchetPercent !== undefined) {
            lastAutoCompactionPercent = options.ratchetPercent;
            noCutRetryState = {
              flooredPercent: Math.floor(options.ratchetPercent),
              usagePercent: options.ratchetPercent,
              userMessageCount,
              reason: noCutReason,
            };
          }
          awaitingPostCompactionAssistantResponse = false;
        }
        if (ownsCurrentAttempt) finishCompaction();
        if (noCutReason) {
          ctx.ui.notify("No safe compaction cut available; continuing session.", "info");
          if (options.noCutRecovery) queueNoCutContinuation(ctx, noCutReason, options.noCutRecovery);
        } else {
          if (!ownsCurrentAttempt) return;
          if (options.ratchetPercent !== undefined) lastAutoCompactionPercent = options.ratchetPercent;
          const reason = err.message === "Compaction cancelled" ? "cancelled" : "failed";
          ctx.ui.notify(`Compaction failed: ${err.message}; continuing interrupted turn if needed.`, "warning");
          queueCompactionContinuation(ctx, attemptId, reason, options.interruptedTurn);
        }
      },
    });
    return true;
  };

  const schedulePiVccCompaction = (
    ctx: ExtensionContext,
    options: Parameters<typeof triggerCompaction>[1],
  ) => {
    if (compactionInFlight || scheduledPiVccCompaction || activeCompactionOwner) return false;
    activeCompactionOwner = "pi-vcc";
    scheduledPiVccCompaction = setTimeout(() => {
      scheduledPiVccCompaction = undefined;
      if (compactionInFlight) return;
      if (activeCompactionOwner !== "pi-vcc") {
        activeCompactionOwner = undefined;
        return;
      }
      const started = triggerCompaction(ctx, options);
      if (!started) activeCompactionOwner = undefined;
    }, 0);
    return true;
  };

  const sendModelNudge = (ctx: ExtensionContext, usagePercent: number, band: NudgeBand) => {
    if (lastNudgePercentBand === band) return;
    if (lastFailureTurn !== undefined && turnCounter - lastFailureTurn <= FAILURE_DELAY_TURNS) return;

    const currentPercent = Math.floor(usagePercent);
    const content = band === "strong"
      ? `Context is at ${currentPercent}% (strong nudge band ${COMPACTION_STRONG_NUDGE_PERCENT}-${HARD_AUTO_COMPACTION_PERCENT - 1}%). compact_context is available when you reach a safe semantic boundary. 60%/75% are nudges only, not instructions to compact immediately; ${HARD_AUTO_COMPACTION_PERCENT}% is the hard automatic backstop.`
      : `Context is at ${currentPercent}% (soft nudge band ${COMPACTION_NUDGE_PERCENT}-${COMPACTION_STRONG_NUDGE_PERCENT - 1}%). compact_context is available after a subtask resolves, before switching topics, or after a test/debug loop has been interpreted. This is not an instruction to compact immediately; ${HARD_AUTO_COMPACTION_PERCENT}% is the hard automatic backstop.`;

    try {
      pi.sendMessage(
        {
          customType: "compaction-nudge",
          content,
          display: true,
          details: { usagePercent, band, hardBackstopPercent: HARD_AUTO_COMPACTION_PERCENT },
        },
        { deliverAs: "steer", triggerTurn: true },
      );
      lastNudgePercentBand = band;
      lastNudgeTurn = turnCounter;
      ctx.ui.notify(content, band === "strong" ? "warning" : "info");
    } catch (err) {
      ctx.ui.notify(`Compaction nudge delivery failed; will retry next turn: ${(err as Error).message}`, "warning");
    }
  };

  pi.registerTool({
    name: "compact_context",
    label: "Compact Context",
    description: "Queue pi-vcc semantic-boundary compaction after the current tool result is delivered safely.",
    promptSnippet: "Queue semantic-boundary context compaction with pi-vcc",
    promptGuidelines: [
      "Use compact_context after a subtask resolves, before switching topics, after a test/debug loop has been interpreted, or when context is becoming noisy.",
      "Do not use compact_context mid-tool-chain, mid-derivation, immediately after fresh failure output, or while critical raw evidence has not been summarized.",
    ],
    parameters: {
      type: "object",
      required: ["reason", "boundary"],
      properties: {
        reason: { type: "string", description: "Short reason for compaction" },
        preserve: { type: "string", description: "Optional short instructions for facts to preserve" },
        boundary: {
          type: "string",
          enum: ["subtask_complete", "before_topic_switch", "after_test_loop", "manual_recovery"],
        },
      },
    },
    async execute(toolCallId: string, params: any) {
      const reason = clampText(params.reason, 240) ?? "semantic boundary";
      const boundary = params.boundary as Boundary;
      const preserve = clampText(params.preserve, 500);
      pendingModelCompaction = {
        reason,
        boundary,
        preserve,
        toolCallId,
        requestedTurn: turnCounter,
        toolBatchId: lastToolBatchId,
        sawSiblingTools: lastAssistantToolCallCount > 1,
      };
      const willResume = shouldResumeAfterCompactContext(pendingModelCompaction);
      return {
        content: [{
          type: "text",
          text: willResume
            ? "compact_context queued. Compaction will run after the current tool batch reaches a safe boundary, then nudge this active workflow to continue."
            : "compact_context queued. Compaction will run after the current tool batch reaches a safe boundary. No auto-resume requested.",
        }],
        details: { ...pendingModelCompaction, willResume },
      };
    },
  });

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
        reason: "manual",
      });
    },
  });

  pi.registerCommand("compact-status", {
    description: "Show current context usage and semantic compaction status",
    handler: async (_args, ctx: ExtensionContext) => {
      const usage = ctx.getContextUsage();
      if (!usage || usage.percent === null) {
        ctx.ui.notify("Context usage: unknown", "warning");
        return;
      }
      ctx.ui.notify(
        `Context: ${Math.floor(usage.percent)}% of ${usage.contextWindow.toLocaleString()} tokens ` +
          `(nudge: ${COMPACTION_NUDGE_PERCENT}%, strong: ${COMPACTION_STRONG_NUDGE_PERCENT}%, hard auto: ${HARD_AUTO_COMPACTION_PERCENT}%, ` +
          `last nudge: ${lastNudgePercentBand ?? "none"}${lastNudgeTurn !== undefined ? `@turn ${lastNudgeTurn}` : ""}, last compaction: ${lastCompactionReason})`,
        "info",
      );
    },
  });

  pi.on("turn_end", async (event: TurnEndEvent, ctx: ExtensionContext) => {
    turnCounter += 1;

    const completedResponse = isCompletedAssistantResponse(event.message);
    const turnToolResults = Array.isArray(event.toolResults) ? event.toolResults : [];
    const pendingToolResultDelivered = Boolean(
      pendingModelCompaction?.toolCallId &&
        (toolResultMatches(event.message, pendingModelCompaction.toolCallId) ||
          turnToolResults.some((result: any) => toolResultMatches(result, pendingModelCompaction?.toolCallId))),
    );

    if (event.message.role === "assistant" && "stopReason" in event.message && event.message.stopReason === "toolUse") {
      lastToolBatchId += 1;
      lastAssistantToolCallCount = toolCallCount(event.message);
      outstandingAssistantToolCallIds = new Set(assistantToolCallIds(event.message));
      if (pendingModelCompaction && assistantToolBatchIncludes(event.message, pendingModelCompaction.toolCallId)) {
        pendingModelCompaction.toolBatchId = lastToolBatchId;
        pendingModelCompaction.sawSiblingTools = lastAssistantToolCallCount > 1;
      }
    }
    if (hasFailureOutput(event.message) || turnToolResults.some(hasFailureOutput)) {
      lastFailureTurn = turnCounter;
      uninterpretedFailure = true;
    } else if (completedResponse) {
      uninterpretedFailure = false;
    }

    const usage = ctx.getContextUsage();
    const usagePercent = usage?.percent ?? undefined;

    for (const id of deliveredToolCallIds(event)) outstandingAssistantToolCallIds.delete(id);
    if (completedResponse) outstandingAssistantToolCallIds.clear();
    clearDeliveredNoCutTools(event);
    clearDeliveredCompactionContinuationTools(event);
    if (noCutContinuationIsSafe(event)) sendPendingNoCutContinuation(ctx);
    if (compactionContinuationIsSafe(event)) sendPendingCompactionContinuation(ctx);
    if (pendingCompactionContinuation) return;

    if (compactionInFlight || scheduledPiVccCompaction) return;

    if (awaitingPostCompactionAssistantResponse) {
      if (!completedResponse) return;
      awaitingPostCompactionAssistantResponse = false;
    }

    if (pendingModelCompaction && canRunPendingCompaction(pendingModelCompaction, event, pendingToolResultDelivered)) {
      const pending = pendingModelCompaction;
      if (!uninterpretedFailure || pending.boundary === "manual_recovery") {
        pendingModelCompaction = undefined;
        triggerCompaction(ctx, {
          customInstructions: buildIntentInstructions(pending),
          startMessage: `✓ Compacting at semantic boundary: ${pending.boundary}`,
          completionMessage: "Compacted with pi-vcc",
          ratchetPercent: usagePercent ?? undefined,
          reason: "compact_context",
          resumeMessage: shouldResumeAfterCompactContext(pending) ? buildResumeMessage(pending) : undefined,
          interruptedTurn: snapshotInterruptedCompactionTurn(event, "compact_context"),
        });
        return;
      }
    }

    if (usagePercent === undefined || usagePercent === null) return;

    const currentPercent = Math.floor(usagePercent);

    if (usagePercent < COMPACTION_NUDGE_PERCENT) {
      lastAutoCompactionPercent = undefined;
      lastNudgePercentBand = undefined;
      awaitingPostCompactionAssistantResponse = false;
      noCutRetryState = undefined;
      return;
    }

    if (usagePercent >= HARD_AUTO_COMPACTION_PERCENT) {
      if (
        isStaleAutoCompactionPercent(usagePercent, lastAutoCompactionPercent) &&
        (!noCutRetryState || userMessageCount === noCutRetryState.userMessageCount)
      ) return;
      if (
        noCutRetryState &&
        currentPercent <= noCutRetryState.flooredPercent &&
        userMessageCount === noCutRetryState.userMessageCount
      ) {
        return;
      }
      schedulePiVccCompaction(ctx, {
        startMessage: completedResponse
          ? `✓ Auto-compacting at ${currentPercent}% (hard backstop: ${HARD_AUTO_COMPACTION_PERCENT}%)`
          : `↻ Context at ${currentPercent}% (hard backstop: ${HARD_AUTO_COMPACTION_PERCENT}%). Interrupting agent for pi-vcc compaction...`,
        completionMessage: "Compacted with pi-vcc",
        ratchetPercent: usagePercent,
        reason: "hard_backstop",
        interruptedTurn: snapshotInterruptedCompactionTurn(event, "hard_backstop"),
        noCutRecovery: {
          interruptedActiveTurn: isInterruptedAgentWork(event.message),
          pendingToolCallIds: () => completedResponse ? [] : [...outstandingAssistantToolCallIds],
          usagePercent,
        },
      });
      return;
    }

    if (usagePercent >= COMPACTION_STRONG_NUDGE_PERCENT) {
      sendModelNudge(ctx, usagePercent, "strong");
      return;
    }

    sendModelNudge(ctx, usagePercent, "soft");
  });

  pi.on("message_end", async (event: any) => {
    if (event?.message?.role === "user" && typeof event.message.customType !== "string") userMessageCount += 1;
  });

  pi.on("session_compact", async () => {
    noCutRetryState = undefined;
    clearPendingNoCutContinuation();
    clearPendingCompactionContinuation();
    finishCompaction({ compacted: true });
  });

  pi.on("session_before_compact", async (event: SessionBeforeCompactEvent, ctx: ExtensionContext) => {
    if (!isPiVccLoaded()) {
      notifyMissingPiVcc(ctx);
      return { cancel: true };
    }

    const usage = ctx.getContextUsage();
    if (!usage || usage.percent === null) return;

    const manualPiVccBypass = event.customInstructions?.startsWith(PI_VCC_MANUAL_BYPASS_MARKER) ?? false;
    if (manualPiVccBypass) {
      ctx.ui.notify(
        `✓ Compaction bypassed ${HARD_AUTO_COMPACTION_PERCENT}% hard backstop at ${Math.floor(usage.percent)}%`,
        "info",
      );
      return;
    }

    const rawEvent = event as { reason?: unknown; willRetry?: unknown };

    if (pendingCompactionContinuation) {
      lastAutoCompactionPercent = usage.percent;
      ctx.ui.notify(
        `⏸️ Delayed auto-compaction: waiting to continue interrupted pi-vcc attempt ${pendingCompactionContinuation.attemptId}`,
        "info",
      );
      return { cancel: true };
    }

    if (scheduledPiVccCompaction) {
      lastAutoCompactionPercent = usage.percent;
      ctx.ui.notify(
        `⏸️ Delayed auto-compaction: pi-vcc already scheduled ${Math.floor(usage.percent)}% compaction recovery`,
        "info",
      );
      return { cancel: true };
    }

    if ((rawEvent.reason === "overflow" || rawEvent.willRetry === true) && !manualPiVccBypass) {
      return;
    }

    if (usage.percent < HARD_AUTO_COMPACTION_PERCENT) {
      lastAutoCompactionPercent = undefined;
      ctx.ui.notify(
        `⏸️ Delayed auto-compaction: ${Math.floor(usage.percent)}% < ${HARD_AUTO_COMPACTION_PERCENT}% hard backstop`,
        "info",
      );
      return { cancel: true };
    }

    if (awaitingPostCompactionAssistantResponse) {
      lastAutoCompactionPercent = usage.percent;
      ctx.ui.notify(
        "⏸️ Delayed auto-compaction: waiting for the next assistant response after the last pi-vcc compaction",
        "info",
      );
      return { cancel: true };
    }

    if (compactionInFlight) {
      lastAutoCompactionPercent = usage.percent;
      awaitingPostCompactionAssistantResponse = true;
      lastCompactionReason = "core_hard_backstop";
      ctx.ui.notify(
        `✓ Auto-compacting at ${Math.floor(usage.percent)}% (hard backstop: ${HARD_AUTO_COMPACTION_PERCENT}%)`,
        "info",
      );
      return;
    }

    if (isStaleAutoCompactionPercent(usage.percent, lastAutoCompactionPercent)) {
      lastAutoCompactionPercent = usage.percent;
      ctx.ui.notify(
        `⏸️ Delayed auto-compaction: context usage is unchanged at ${usage.percent}% since the last pi-vcc compaction`,
        "info",
      );
      return { cancel: true };
    }

    const currentPercent = Math.floor(usage.percent);
    if (
      noCutRetryState &&
      currentPercent <= noCutRetryState.flooredPercent &&
      userMessageCount === noCutRetryState.userMessageCount
    ) {
      lastAutoCompactionPercent = usage.percent;
      ctx.ui.notify(
        `⏸️ Delayed auto-compaction: no safe cut was available at ${noCutRetryState.flooredPercent}%; waiting for higher usage or a new user message`,
        "info",
      );
      return { cancel: true };
    }

    lastAutoCompactionPercent = usage.percent;
    ctx.ui.notify(
      `⏸️ Delayed auto-compaction: repo-managed hard backstop handles ${Math.floor(usage.percent)}% compaction with no-cut recovery`,
      "info",
    );
    return { cancel: true };
  });
}
