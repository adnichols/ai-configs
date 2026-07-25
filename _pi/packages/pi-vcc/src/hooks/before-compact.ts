import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { convertToLlm, estimateTokens } from "@earendil-works/pi-coding-agent";
import { readFileSync, writeFileSync } from "fs";
import { join } from "path";
import { homedir } from "os";
import { compile } from "../core/summarize";
import { logPiVccEvent } from "../core/log";
import type { ContinuationCoordinator } from "../core/coordinator";
import { parseKeepAndPrompt, PI_VCC_COMPACT_INSTRUCTION } from "../core/compact-args";
import type { PiVccCompactionDetails } from "../details";
import type { CompactionIntent, CompactionReason, NoCutClassification } from "../types";

export { PI_VCC_COMPACT_INSTRUCTION } from "../core/compact-args";

const CONFIG_PATH = join(homedir(), ".pi", "agent", "pi-vcc-config.json");
const MIN_MESSAGES_TO_COMPACT = 3;
const AGENT_ONLY_FALLBACK_TAIL_MESSAGES = 4;
const DEFAULT_KEEP_RECENT_TOKENS = 20_000;

export interface CompactionStats {
  summarized: number;
  kept: number;
  keptTokensEst: number;
  reason?: CompactionReason;
  willRetry?: boolean;
  compactionIntent?: CompactionIntent;
}

let lastStats: CompactionStats | null = null;
let lastNoCutClassification: NoCutClassification | null = null;
export const getLastCompactionStats = () => lastStats;
export const getLastNoCutClassification = () => lastNoCutClassification;

const hasNonMessageEntriesAfter = (branchEntries: any[], firstKeptEntryId: string): boolean => {
  const keptIdx = branchEntries.findIndex((e: any) => e.id === firstKeptEntryId);
  if (keptIdx < 0) return false;
  return branchEntries.slice(keptIdx).some((e: any) => e.type !== "message");
};

export interface PiVccConfig {
  debug?: boolean;
}

const loadConfig = (): PiVccConfig => {
  try { return JSON.parse(readFileSync(CONFIG_PATH, "utf-8")); } catch { return {}; }
};

const dbg = (config: PiVccConfig, data: Record<string, unknown>) => {
  if (!config.debug) return;
  try { writeFileSync("/tmp/pi-vcc-debug.json", JSON.stringify(data, null, 2)); } catch {}
};

const readCompactionEventContext = (event: unknown): { reason?: CompactionReason; willRetry: boolean } => {
  const raw = event as { reason?: unknown; willRetry?: unknown };
  const reason = raw.reason === "manual" || raw.reason === "threshold" || raw.reason === "overflow"
    ? raw.reason
    : undefined;
  return { reason, willRetry: raw.willRetry === true };
};

const parseCompactionIntent = (customInstructions?: string): CompactionIntent | undefined => {
  const trimmed = customInstructions?.trim();
  if (!trimmed?.startsWith(PI_VCC_COMPACT_INSTRUCTION)) return undefined;
  const payload = trimmed.slice(PI_VCC_COMPACT_INSTRUCTION.length).trim();
  const jsonStart = payload.indexOf("{");
  if (jsonStart < 0) return undefined;
  try {
    const parsed = JSON.parse(payload.slice(jsonStart));
    if (!parsed || typeof parsed !== "object") return undefined;
    const intent: CompactionIntent = {};
    for (const key of ["source", "reason", "boundary", "preserve", "requestId", "attemptId", "transactionId", "resumePolicy"] as const) {
      const value = parsed[key];
      const cleaned = typeof value === "string" ? value.replace(/\s+/g, " ").trim() : "";
      if (cleaned) intent[key] = cleaned.slice(0, 500) as never;
    }
    return Object.keys(intent).length ? intent : undefined;
  } catch {
    return undefined;
  }
};

const parseKeepOptions = (customInstructions?: string): { keepUserTurns: number; explicit: boolean } => {
  const trimmed = customInstructions?.trim();
  if (!trimmed?.startsWith(PI_VCC_COMPACT_INSTRUCTION)) return { keepUserTurns: 1, explicit: false };
  const payload = trimmed.slice(PI_VCC_COMPACT_INSTRUCTION.length);
  const parsed = parseKeepAndPrompt(payload);
  const fallback = parsed.keepUserTurnsExplicit ? parsed : parseKeepAndPrompt(payload.replace(/\{[\s\S]*$/, ""));
  return { keepUserTurns: fallback.keepUserTurns ?? 1, explicit: fallback.keepUserTurnsExplicit };
};

const previewContent = (content: unknown): string => {
  if (typeof content === "string") return content.slice(0, 300);
  if (Array.isArray(content)) {
    return content
      .map((c: any) => {
        if (c?.type === "text") return c.text ?? "";
        if (c?.type === "toolCall") return `[toolCall:${c.name}]`;
        if (c?.type === "thinking") return `[thinking]`;
        if (c?.type === "image") return `[image:${c.mimeType}]`;
        return `[${c?.type ?? "unknown"}]`;
      })
      .join("\n")
      .slice(0, 300);
  }
  return "";
};

interface EntryWithMessage {
  entry: { id: string; type: string };
  message: { role: string; content: unknown; toolCallId?: string };
}

const hasMatchingToolCall = (message: any, toolCallId: string): boolean => {
  if (message?.role !== "assistant" || !Array.isArray(message?.content)) return false;
  return message.content.some((item: any) => item?.type === "toolCall" && item.id === toolCallId);
};

const findMatchingToolCallIndex = (liveMessages: EntryWithMessage[], toolCallId: string, beforeIdx: number): number => {
  for (let i = beforeIdx; i >= 0; i--) {
    if (hasMatchingToolCall(liveMessages[i]?.message, toolCallId)) return i;
    if (liveMessages[i]?.message?.role === "user") break;
  }
  return -1;
};

const adjustCutIdxForToolResult = (liveMessages: EntryWithMessage[], cutIdx: number): number | null => {
  if (cutIdx <= 0) return cutIdx;

  const firstKeptMessage = liveMessages[cutIdx]?.message;
  if (firstKeptMessage?.role !== "toolResult" || !firstKeptMessage.toolCallId) return cutIdx;

  const matchingIdx = findMatchingToolCallIndex(liveMessages, firstKeptMessage.toolCallId, cutIdx - 1);
  return matchingIdx >= 0 ? matchingIdx : null;
};

const estimateTailTokens = (liveMessages: EntryWithMessage[], cutIdx: number): number =>
  liveMessages.slice(cutIdx).reduce((sum, entry) => sum + estimateTokens(entry.message as any), 0);

const findTokenBoundedCutIdx = (liveMessages: EntryWithMessage[], keepRecentTokens: number): number | null => {
  const budget = Number.isFinite(keepRecentTokens)
    ? Math.max(1, Math.floor(keepRecentTokens))
    : DEFAULT_KEEP_RECENT_TOKENS;
  let cutIdx: number | null = null;
  let retainedTokens = 0;

  for (let i = liveMessages.length - 1; i > 0; i--) {
    const nextTokens = estimateTokens(liveMessages[i].message as any);
    if (retainedTokens > 0 && retainedTokens + nextTokens > budget && cutIdx !== null) break;
    retainedTokens += nextTokens;
    if (liveMessages[i].message.role !== "toolResult") cutIdx = i;
    if (retainedTokens >= budget && cutIdx !== null) break;
  }

  return cutIdx;
};

const keptTailHasOrphanedToolResult = (liveMessages: EntryWithMessage[], cutIdx: number): boolean => {
  for (let i = cutIdx; i < liveMessages.length; i++) {
    const message = liveMessages[i]?.message;
    if (message.role !== "toolResult" || !message.toolCallId) continue;
    if (findMatchingToolCallIndex(liveMessages, message.toolCallId, i - 1) < cutIdx) return true;
  }
  return false;
};

const liveMessagesSinceLastCompaction = (branchEntries: any[]): EntryWithMessage[] => {
  return readLiveMessagesSinceLastCompaction(branchEntries).liveMessages;
};

const readLiveMessagesSinceLastCompaction = (branchEntries: any[]): {
  liveMessages: EntryWithMessage[];
  firstKeptEntryId?: string;
  hadPreviousCompaction: boolean;
} => {
  let lastKeptId: string | undefined;
  for (let i = branchEntries.length - 1; i >= 0; i--) {
    if (branchEntries[i].type === "compaction") {
      lastKeptId = branchEntries[i].firstKeptEntryId;
      break;
    }
  }

  const liveMessages: EntryWithMessage[] = [];
  let foundKept = !lastKeptId;
  for (const e of branchEntries) {
    if (!foundKept && e.id === lastKeptId) foundKept = true;
    if (!foundKept) continue;
    if (e.type === "compaction") continue;
    if (e.type === "message" && e.message) {
      liveMessages.push({ entry: e, message: e.message });
    }
  }
  return { liveMessages, firstKeptEntryId: lastKeptId, hadPreviousCompaction: Boolean(lastKeptId) };
};

const inferActiveTurnFromMessages = (liveMessages: EntryWithMessage[]): boolean => {
  const latest = liveMessages[liveMessages.length - 1]?.message as any;
  if (!latest) return false;

  if (latest.role === "assistant") return latest.stopReason === "toolUse";
  if (latest.role !== "toolResult" || !latest.toolCallId) return false;

  for (let i = liveMessages.length - 2; i >= 0; i--) {
    const message = liveMessages[i]?.message as any;
    if (hasMatchingToolCall(message, latest.toolCallId)) return true;
    if (message?.role === "user") return false;
  }

  return false;
};

const inferActiveTurnFromBranchEntries = (branchEntries: any[]): boolean =>
  inferActiveTurnFromMessages(liveMessagesSinceLastCompaction(branchEntries));

const classifyNoCut = (
  branchEntries: any[],
  eventContext: { reason?: CompactionReason; willRetry: boolean },
): NoCutClassification => {
  const { liveMessages, firstKeptEntryId, hadPreviousCompaction } = readLiveMessagesSinceLastCompaction(branchEntries);
  const latestLiveRole = liveMessages[liveMessages.length - 1]?.message?.role;
  const activeTurnInferred = inferActiveTurnFromMessages(liveMessages);
  const reason = liveMessages.length < MIN_MESSAGES_TO_COMPACT
    ? hadPreviousCompaction
      ? "post_compaction_tail_too_short"
      : "tiny_session"
    : activeTurnInferred
      ? "active_turn_no_safe_cut"
      : "unknown_no_safe_cut";
  return {
    reason,
    hadPreviousCompaction,
    liveMessageCount: liveMessages.length,
    latestLiveRole,
    activeTurnInferred,
    firstKeptEntryId,
    compactionReason: eventContext.reason,
    willRetry: eventContext.willRetry,
  };
};

function buildOwnCut(
  branchEntries: any[],
  keepUserTurns = 1,
  keepUserTurnsExplicit = false,
  keepRecentTokens = DEFAULT_KEEP_RECENT_TOKENS,
): { messages: any[]; firstKeptEntryId: string } | null {
  const liveMessages = liveMessagesSinceLastCompaction(branchEntries);

  if (liveMessages.length < MIN_MESSAGES_TO_COMPACT) return null;

  const normalizedKeepUserTurns = Number.isFinite(keepUserTurns) ? Math.max(1, Math.floor(keepUserTurns)) : 1;
  const userIndices = liveMessages.reduce<number[]>((acc, entry, index) => {
    if (entry.message.role === "user") acc.push(index);
    return acc;
  }, []);

  let cutIdx = userIndices[userIndices.length - normalizedKeepUserTurns] ?? -1;

  if (
    !keepUserTurnsExplicit &&
    estimateTailTokens(liveMessages, Math.max(0, cutIdx)) > keepRecentTokens
  ) {
    const boundedCutIdx = findTokenBoundedCutIdx(liveMessages, keepRecentTokens);
    if (boundedCutIdx === null) return null;
    cutIdx = boundedCutIdx;
  }

  if (cutIdx <= 0) {
    if (keepUserTurnsExplicit) return null;
    if (liveMessages.length <= AGENT_ONLY_FALLBACK_TAIL_MESSAGES) return null;
    cutIdx = liveMessages.length - AGENT_ONLY_FALLBACK_TAIL_MESSAGES;
    const adjustedCutIdx = adjustCutIdxForToolResult(liveMessages, cutIdx);
    if (adjustedCutIdx === null) return null;
    cutIdx = adjustedCutIdx;
  }

  if (cutIdx <= 0) return null;
  if (keptTailHasOrphanedToolResult(liveMessages, cutIdx)) return null;

  return {
    messages: liveMessages.slice(0, cutIdx).map((e) => e.message),
    firstKeptEntryId: liveMessages[cutIdx].entry.id,
  };
}

export const registerBeforeCompactHook = (pi: ExtensionAPI, coordinator: ContinuationCoordinator) => {
  let agentTurnActive = false;
  let activeAgentFinishedResponse = false;

  pi.on("agent_start", () => {
    agentTurnActive = true;
    activeAgentFinishedResponse = false;
  });

  pi.on("message_end", (event) => {
    const message = event.message as { role?: string; stopReason?: string };
    if (message.role === "assistant" && message.stopReason !== "toolUse") {
      activeAgentFinishedResponse = true;
    }
  });

  pi.on("agent_end", () => {
    agentTurnActive = false;
    activeAgentFinishedResponse = false;
  });

  pi.on("session_compact", (event, ctx) => {
    const details = event.compactionEntry.details as PiVccCompactionDetails | undefined;
    if (details?.compactor !== "pi-vcc") return;
    logPiVccEvent("session_compact", {
      compactionEntryId: event.compactionEntry.id,
      reason: details.reason ?? event.reason,
      willRetry: details.willRetry ?? event.willRetry,
      interruptedInFlightTurn: details.interruptedInFlightTurn,
      requiresContinuation: details.requiresContinuation,
      sourceMessageCount: details.sourceMessageCount,
      retainedNonMessageEntries: details.retainedNonMessageEntries,
    });
    const commandOrigin = details.compactionIntent?.source === "package-pi-vcc" || details.compactionIntent?.source === "package-compact-now";
    // compact_context runs at a completed semantic boundary, so it is normally
    // not an interrupted turn. An explicit active policy is still a durable
    // request to resume the task after the context replacement.
    const activeCompactContext =
      details.compactionIntent?.source === "compact_context" &&
      details.continuationResumePolicy === "active";
    if (!commandOrigin && !activeCompactContext && !details.interruptedInFlightTurn) return;
    if (event.willRetry === true || (!commandOrigin && !activeCompactContext && details.requiresContinuation === false)) return;
    coordinator.request({
      initiator: details.compactionIntent?.source === "package-compact-now" ? "package-compact-now"
        : details.compactionIntent?.source === "compact_context" ? "compact_context"
        : details.reason === "threshold" ? "host-threshold"
          : details.reason === "overflow" ? "host-overflow"
            : "package-pi-vcc",
      outcome: "compacted",
      attemptId: details.continuationAttemptId ?? details.compactionIntent?.attemptId ?? event.compactionEntry.id,
      compactionId: event.compactionEntry.id,
      requestId: details.continuationRequestId ?? details.compactionIntent?.requestId,
      originatingRequestId: details.continuationRequestId ?? details.compactionIntent?.requestId,
      resumePolicy: details.continuationResumePolicy ?? details.compactionIntent?.resumePolicy ?? "active",
      transactionId: details.continuationTransactionId ?? details.compactionIntent?.transactionId,
    }, ctx);
  });

  pi.on("session_before_compact", (event) => {
    const { preparation, branchEntries, customInstructions } = event;
    const eventContext = readCompactionEventContext(event);
    const { reason, willRetry } = eventContext;
    const compactionIntent = parseCompactionIntent(customInstructions);
    const compactingActiveTurn =
      (agentTurnActive && !activeAgentFinishedResponse) || inferActiveTurnFromBranchEntries(branchEntries as any[]);

    const keepOptions = parseKeepOptions(customInstructions);
    const ownCut = buildOwnCut(
      branchEntries as any[],
      keepOptions.keepUserTurns,
      keepOptions.explicit,
      preparation.settings?.keepRecentTokens ?? DEFAULT_KEEP_RECENT_TOKENS,
    );
    if (!ownCut) {
      const piVccBypass = customInstructions?.startsWith(PI_VCC_COMPACT_INSTRUCTION) ?? false;
      lastNoCutClassification = classifyNoCut(branchEntries as any[], eventContext);
      dbg(loadConfig(), { usedOwnCut: false, noCutClassification: lastNoCutClassification });
      logPiVccEvent("no_safe_cut", {
        classification: lastNoCutClassification,
        cancel: piVccBypass || !(reason === "manual" || reason === "threshold" || reason === "overflow" || willRetry),
      });
      if (!piVccBypass && (reason === "manual" || reason === "threshold" || reason === "overflow" || willRetry)) return;
      return { cancel: true };
    }

    lastNoCutClassification = null;

    if (compactingActiveTurn) agentTurnActive = false;

    const agentMessages = ownCut.messages;
    const firstKeptEntryId = ownCut.firstKeptEntryId;
    const messages = convertToLlm(agentMessages);
    const retainedNonMessageEntries = hasNonMessageEntriesAfter(branchEntries as any[], firstKeptEntryId);

    const keptIdx = (branchEntries as any[]).findIndex((e: any) => e.id === firstKeptEntryId);
    const keptEntries = keptIdx >= 0
      ? (branchEntries as any[]).slice(keptIdx).filter((e: any) => e.type === "message")
      : [];
    lastStats = {
      summarized: agentMessages.length,
      kept: keptEntries.length,
      keptTokensEst: estimateTailTokens(
        keptEntries.map((entry: any) => ({ entry, message: entry.message })),
        0,
      ),
      reason,
      willRetry,
      compactionIntent,
    };

    const config = loadConfig();
    const summary = compile({
      messages,
      previousSummary: preparation.previousSummary,
      compactionIntent,
      fileOps: {
        readFiles: [...preparation.fileOps.read],
        modifiedFiles: [...preparation.fileOps.written, ...preparation.fileOps.edited],
      },
    });

    const branchIds = branchEntries.map((e: any) => e.id);
    const cutIdx = branchIds.indexOf(firstKeptEntryId);
    const cutWindow = cutIdx >= 0
      ? branchEntries.slice(Math.max(0, cutIdx - 3), Math.min(branchEntries.length, cutIdx + 3)).map((e: any) => ({
          id: e.id,
          type: e.type,
          role: e.type === "message" ? e.message?.role : undefined,
          preview: e.type === "message" ? previewContent(e.message?.content) : undefined,
        }))
      : [];

    dbg(config, {
      usedOwnCut: true,
      messagesToSummarize: agentMessages.length,
      messagesPreviewHead: agentMessages.slice(0, 3).map((m: any) => ({ role: m.role, preview: previewContent(m.content) })),
      messagesPreviewTail: agentMessages.slice(-3).map((m: any) => ({ role: m.role, preview: previewContent(m.content) })),
      convertedMessages: messages.length,
      firstKeptEntryId,
      cutWindow,
      tokensBefore: preparation.tokensBefore,
      summaryLength: summary.length,
      summaryPreview: summary.slice(0, 500),
      sections: [...summary.matchAll(/^\[(.+?)\]/gm)].map((m) => m[1]),
      compaction: { reason, willRetry, compactionIntent, retainedNonMessageEntries },
    });

    if (retainedNonMessageEntries) {
      logPiVccEvent("retained_non_message_entries_after_cut", {
        firstKeptEntryId,
        reason,
        willRetry,
        sourceMessageCount: agentMessages.length,
        interruptedInFlightTurn: compactingActiveTurn,
        compactionIntent,
      });
    }

    const details: PiVccCompactionDetails = {
      compactor: "pi-vcc",
      version: 1,
      sections: [...summary.matchAll(/^\[(.+?)\]/gm)].map((m) => m[1]),
      sourceMessageCount: agentMessages.length,
      previousSummaryUsed: Boolean(preparation.previousSummary),
      interruptedInFlightTurn: compactingActiveTurn,
      requiresContinuation: compactingActiveTurn && event.willRetry !== true,
      reason,
      willRetry,
      compactionIntent,
      retainedNonMessageEntries,
      continuationAttemptId: compactionIntent?.attemptId,
      continuationRequestId: compactionIntent?.requestId,
      continuationTransactionId: compactionIntent?.transactionId,
      continuationResumePolicy: compactionIntent?.resumePolicy,
    };

    return {
      compaction: {
        summary,
        details,
        tokensBefore: preparation.tokensBefore,
        firstKeptEntryId,
      },
    };
  });
};
