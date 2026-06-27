import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { convertToLlm } from "@earendil-works/pi-coding-agent";
import { readFileSync, writeFileSync } from "fs";
import { join } from "path";
import { homedir } from "os";
import { compile } from "../core/summarize";
import type { PiVccCompactionDetails } from "../details";

const CONFIG_PATH = join(homedir(), ".pi", "agent", "pi-vcc-config.json");
const MIN_MESSAGES_TO_COMPACT = 3;
const AGENT_ONLY_FALLBACK_TAIL_MESSAGES = 4;
const CONTINUE_AFTER_COMPACTION_PROMPT =
  "Pi-vcc compacted the active in-flight conversation. Continue from where you left off; use vcc_recall if you need details from before compaction, and resume the next concrete step without summarizing the compaction.";
const CONTINUE_AFTER_COMPACTION_DELAY_MS = 50;
const CONTINUE_AFTER_COMPACTION_MAX_WAIT_MS = 5000;
const CONTINUE_AFTER_COMPACTION_RETRY_MS = 100;

export interface CompactionStats {
  summarized: number;
  kept: number;
  keptTokensEst: number;
}

let lastStats: CompactionStats | null = null;
export const getLastCompactionStats = () => lastStats;

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

const adjustCutIdxForToolResult = (liveMessages: EntryWithMessage[], cutIdx: number): number => {
  if (cutIdx <= 0) return cutIdx;

  const firstKeptMessage = liveMessages[cutIdx]?.message;
  if (firstKeptMessage?.role !== "toolResult" || !firstKeptMessage.toolCallId) return cutIdx;

  for (let i = cutIdx - 1; i >= 0; i--) {
    if (hasMatchingToolCall(liveMessages[i]?.message, firstKeptMessage.toolCallId)) return i;
    if (liveMessages[i]?.message?.role === "user") break;
  }

  return cutIdx;
};

const liveMessagesSinceLastCompaction = (branchEntries: any[]): EntryWithMessage[] => {
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
  return liveMessages;
};

const inferActiveTurnFromBranchEntries = (branchEntries: any[]): boolean => {
  const liveMessages = liveMessagesSinceLastCompaction(branchEntries);
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

function buildOwnCut(branchEntries: any[]): { messages: any[]; firstKeptEntryId: string } | null {
  const liveMessages = liveMessagesSinceLastCompaction(branchEntries);

  if (liveMessages.length < MIN_MESSAGES_TO_COMPACT) return null;

  let cutIdx = -1;
  for (let i = liveMessages.length - 1; i > 0; i--) {
    if (liveMessages[i].message.role === "user") {
      cutIdx = i;
      break;
    }
  }

  if (cutIdx <= 0) {
    if (liveMessages.length <= AGENT_ONLY_FALLBACK_TAIL_MESSAGES) return null;
    cutIdx = liveMessages.length - AGENT_ONLY_FALLBACK_TAIL_MESSAGES;
    cutIdx = adjustCutIdxForToolResult(liveMessages, cutIdx);
  }

  if (cutIdx <= 0) return null;

  return {
    messages: liveMessages.slice(0, cutIdx).map((e) => e.message),
    firstKeptEntryId: liveMessages[cutIdx].entry.id,
  };
}

export const registerBeforeCompactHook = (pi: ExtensionAPI) => {
  let agentTurnActive = false;
  let activeAgentFinishedResponse = false;
  let continueTimer: ReturnType<typeof setTimeout> | undefined;

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

  pi.on("session_compact", (event) => {
    const details = event.compactionEntry.details as PiVccCompactionDetails | undefined;
    if (details?.compactor !== "pi-vcc") return;
    if (!details.interruptedInFlightTurn) return;
    if (event.willRetry === true || details.requiresContinuation === false) return;
    if (continueTimer) return;

    const startedAt = Date.now();
    const sendContinuation = () => {
      try {
        continueTimer = undefined;
        pi.sendMessage(
          {
            customType: "pi-vcc-continuation",
            content: CONTINUE_AFTER_COMPACTION_PROMPT,
            display: false,
            details: { compactor: "pi-vcc" },
          },
          { triggerTurn: true, deliverAs: "steer" },
        );
      } catch {
        if (Date.now() - startedAt < CONTINUE_AFTER_COMPACTION_MAX_WAIT_MS) {
          continueTimer = setTimeout(sendContinuation, CONTINUE_AFTER_COMPACTION_RETRY_MS);
        } else {
          continueTimer = undefined;
        }
      }
    };

    continueTimer = setTimeout(sendContinuation, CONTINUE_AFTER_COMPACTION_DELAY_MS);
  });

  pi.on("session_before_compact", (event) => {
    const { preparation, branchEntries } = event;
    const compactingActiveTurn =
      (agentTurnActive && !activeAgentFinishedResponse) || inferActiveTurnFromBranchEntries(branchEntries as any[]);
    if (compactingActiveTurn) agentTurnActive = false;

    const ownCut = buildOwnCut(branchEntries as any[]);
    if (!ownCut) return { cancel: true };

    const agentMessages = ownCut.messages;
    const firstKeptEntryId = ownCut.firstKeptEntryId;
    const messages = convertToLlm(agentMessages);

    const keptIdx = (branchEntries as any[]).findIndex((e: any) => e.id === firstKeptEntryId);
    const keptEntries = keptIdx >= 0
      ? (branchEntries as any[]).slice(keptIdx).filter((e: any) => e.type === "message")
      : [];
    const keptChars = keptEntries.reduce((sum: number, e: any) => {
      const c = e.message?.content;
      if (typeof c === "string") return sum + c.length;
      if (Array.isArray(c)) {
        return sum + c.reduce((s: number, p: any) => {
          if (p.text) return s + p.text.length;
          if (p.type === "toolCall") return s + (p.name?.length ?? 0) + (typeof p.input === "string" ? p.input.length : JSON.stringify(p.input ?? "").length);
          if (p.type === "toolResult") return s + (typeof p.content === "string" ? p.content.length : JSON.stringify(p.content ?? "").length);
          return s;
        }, 0);
      }
      return sum;
    }, 0);
    lastStats = {
      summarized: agentMessages.length,
      kept: keptEntries.length,
      keptTokensEst: Math.round(keptChars / 4),
    };

    const config = loadConfig();
    const summary = compile({
      messages,
      previousSummary: preparation.previousSummary,
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
    });

    const details: PiVccCompactionDetails = {
      compactor: "pi-vcc",
      version: 1,
      sections: [...summary.matchAll(/^\[(.+?)\]/gm)].map((m) => m[1]),
      sourceMessageCount: agentMessages.length,
      previousSummaryUsed: Boolean(preparation.previousSummary),
      interruptedInFlightTurn: compactingActiveTurn,
      requiresContinuation: compactingActiveTurn && event.willRetry !== true,
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
