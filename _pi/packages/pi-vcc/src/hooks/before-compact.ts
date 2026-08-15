import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { convertToLlm, estimateTokens } from "@earendil-works/pi-coding-agent";
import { readFileSync, writeFileSync } from "fs";
import { join } from "path";
import { homedir } from "os";
import { compile } from "../core/summarize";
import { logPiVccEvent } from "../core/log";
import { parseKeepAndPrompt, PI_VCC_COMPACT_INSTRUCTION } from "../core/compact-args";
import type { PiVccCompactionDetails } from "../details";
import type { CompactionFocus, CompactionReason, NoCutClassification } from "../types";

export { PI_VCC_COMPACT_INSTRUCTION } from "../core/compact-args";

const CONFIG_PATH = join(homedir(), ".pi", "agent", "pi-vcc-config.json");

export interface CompactionStats {
	summarized: number;
	kept: number;
	keptTokensEst: number;
	reason?: CompactionReason;
	willRetry?: boolean;
}

let lastStats: CompactionStats | null = null;
let lastNoCutClassification: NoCutClassification | null = null;
export const getLastCompactionStats = () => lastStats;
export const getLastNoCutClassification = () => lastNoCutClassification;

export interface PiVccConfig {
	debug?: boolean;
}

const loadConfig = (): PiVccConfig => {
	try {
		return JSON.parse(readFileSync(CONFIG_PATH, "utf-8"));
	} catch {
		return {};
	}
};

const dbg = (config: PiVccConfig, data: Record<string, unknown>) => {
	if (!config.debug) return;
	try {
		writeFileSync("/tmp/pi-vcc-debug.json", JSON.stringify(data, null, 2));
	} catch {}
};

const readCompactionEventContext = (event: unknown): { reason?: CompactionReason; willRetry: boolean } => {
	const raw = event as { reason?: unknown; willRetry?: unknown };
	const reason = raw.reason === "manual" || raw.reason === "threshold" || raw.reason === "overflow"
		? raw.reason
		: undefined;
	return { reason, willRetry: raw.willRetry === true };
};

const parseExplicitKeep = (customInstructions?: string): number | undefined => {
	const trimmed = customInstructions?.trim();
	if (!trimmed?.startsWith(PI_VCC_COMPACT_INSTRUCTION)) return undefined;
	const parsed = parseKeepAndPrompt(trimmed.slice(PI_VCC_COMPACT_INSTRUCTION.length));
	return parsed.keepUserTurnsExplicit && parsed.keepUserTurns !== null
		? parsed.keepUserTurns
		: undefined;
};

const parseCompactionFocus = (customInstructions?: string): CompactionFocus | undefined => {
	const trimmed = customInstructions?.trim();
	if (!trimmed?.startsWith(PI_VCC_COMPACT_INSTRUCTION)) return undefined;
	const payload = trimmed.slice(PI_VCC_COMPACT_INSTRUCTION.length).trim();
	const jsonStart = payload.indexOf("{");
	if (jsonStart < 0) return undefined;
	try {
		const parsed = JSON.parse(payload.slice(jsonStart));
		if (!parsed || typeof parsed !== "object" || typeof parsed.source !== "string") return undefined;
		const focus: CompactionFocus = { source: parsed.source.trim().slice(0, 500) };
		for (const key of ["reason", "boundary", "preserve"] as const) {
			if (typeof parsed[key] === "string" && parsed[key].trim()) focus[key] = parsed[key].trim().slice(0, 500);
		}
		return focus;
	} catch {
		return undefined;
	}
};

const previewContent = (content: unknown): string => {
	if (typeof content === "string") return content.slice(0, 300);
	if (Array.isArray(content)) {
		return content
			.map((c: any) => {
				if (c?.type === "text") return c.text ?? "";
				if (c?.type === "toolCall") return `[toolCall:${c.name}]`;
				if (c?.type === "thinking") return "[thinking]";
				if (c?.type === "image") return `[image:${c.mimeType}]`;
				return `[${c?.type ?? "unknown"}]`;
			})
			.join("\n")
			.slice(0, 300);
	}
	return "";
};

type EntryWithMessage = { entry: { id: string; type: string }; message: any };

const hasMatchingToolCall = (message: any, toolCallId: string): boolean =>
	message?.role === "assistant" && Array.isArray(message.content) &&
	message.content.some((item: any) => item?.type === "toolCall" && item.id === toolCallId);

const liveMessagesSinceLastCompaction = (branchEntries: any[]): EntryWithMessage[] => {
	let firstKeptEntryId: string | undefined;
	for (let i = branchEntries.length - 1; i >= 0; i--) {
		if (branchEntries[i].type === "compaction") {
			firstKeptEntryId = branchEntries[i].firstKeptEntryId;
			break;
		}
	}

	let foundKept = !firstKeptEntryId;
	const liveMessages: EntryWithMessage[] = [];
	for (const entry of branchEntries) {
		if (!foundKept && entry.id === firstKeptEntryId) foundKept = true;
		if (!foundKept) continue;
		if (entry.type === "message" && entry.message) liveMessages.push({ entry, message: entry.message });
	}
	return liveMessages;
};

const findMatchingToolCallIndex = (messages: EntryWithMessage[], toolCallId: string, beforeIdx: number): number => {
	for (let i = beforeIdx; i >= 0; i--) {
		if (hasMatchingToolCall(messages[i]?.message, toolCallId)) return i;
		if (messages[i]?.message?.role === "user") break;
	}
	return -1;
};

const keptTailHasOrphanedToolResult = (messages: EntryWithMessage[], cutIdx: number): boolean => {
	for (let i = cutIdx; i < messages.length; i++) {
		const message = messages[i]?.message;
		if (message?.role !== "toolResult" || !message.toolCallId) continue;
		if (findMatchingToolCallIndex(messages, message.toolCallId, i - 1) < cutIdx) return true;
	}
	return false;
};

/** The only remaining custom cut: an explicit `/pi-vcc keep:N` request. */
const buildExplicitCut = (
	branchEntries: any[],
	keepUserTurns: number,
): { messages: any[]; firstKeptEntryId: string } | null => {
	const liveMessages = liveMessagesSinceLastCompaction(branchEntries);
	const userIndices = liveMessages.reduce<number[]>((indices, item, index) => {
		if (item.message.role === "user") indices.push(index);
		return indices;
	}, []);
	const normalizedKeep = Number.isFinite(keepUserTurns) ? Math.max(1, Math.floor(keepUserTurns)) : 1;
	const cutIdx = userIndices[userIndices.length - normalizedKeep] ?? -1;
	if (cutIdx <= 0 || cutIdx >= liveMessages.length) return null;
	if (keptTailHasOrphanedToolResult(liveMessages, cutIdx)) return null;
	return {
		messages: liveMessages.slice(0, cutIdx).map((item) => item.message),
		firstKeptEntryId: liveMessages[cutIdx].entry.id,
	};
};

const classifyNoCut = (
	branchEntries: any[],
	eventContext: { reason?: CompactionReason; willRetry: boolean },
): NoCutClassification => {
	const liveMessages = liveMessagesSinceLastCompaction(branchEntries);
	const latest = liveMessages.at(-1)?.message;
	const activeTurnInferred = latest?.role === "assistant" && latest.stopReason === "toolUse" ||
		latest?.role === "toolResult" && liveMessages.some((item) => hasMatchingToolCall(item.message, latest.toolCallId));
	return {
		reason: liveMessages.length < 3 ? "tiny_session" : activeTurnInferred ? "active_turn_no_safe_cut" : "unknown_no_safe_cut",
		hadPreviousCompaction: branchEntries.some((entry) => entry.type === "compaction"),
		liveMessageCount: liveMessages.length,
		latestLiveRole: latest?.role,
		activeTurnInferred,
		compactionReason: eventContext.reason,
		willRetry: eventContext.willRetry,
	};
};

const keptTailStats = (branchEntries: any[], firstKeptEntryId: string) => {
	const keptIdx = branchEntries.findIndex((entry) => entry.id === firstKeptEntryId);
	const keptEntries = keptIdx >= 0
		? branchEntries.slice(keptIdx).filter((entry) => entry.type === "message" && entry.message)
		: [];
	return {
		kept: keptEntries.length,
		keptTokensEst: keptEntries.reduce((sum, entry) => sum + estimateTokens(entry.message), 0),
		keptEntries,
	};
};

export const registerBeforeCompactHook = (pi: ExtensionAPI) => {
	pi.on("session_compact", (event) => {
		const details = event.compactionEntry.details as PiVccCompactionDetails | undefined;
		if (details?.compactor !== "pi-vcc") return;
		logPiVccEvent("session_compact", {
			compactionEntryId: event.compactionEntry.id,
			reason: event.reason,
			willRetry: event.willRetry,
			sourceMessageCount: details.sourceMessageCount,
		});
	});

	pi.on("session_before_compact", async (event) => {
		const { preparation, branchEntries, customInstructions } = event;
		const eventContext = readCompactionEventContext(event);
		const explicitKeep = parseExplicitKeep(customInstructions);
		const compactionFocus = parseCompactionFocus(customInstructions);
		const config = loadConfig();

		let firstKeptEntryId = preparation.firstKeptEntryId;
		let agentMessages = [
			...(preparation.messagesToSummarize ?? []),
			...(preparation.turnPrefixMessages ?? []),
		];
		if (explicitKeep !== undefined) {
			const ownCut = buildExplicitCut(branchEntries as any[], explicitKeep);
			if (!ownCut) {
				lastNoCutClassification = classifyNoCut(branchEntries as any[], eventContext);
				logPiVccEvent("no_safe_cut", { classification: lastNoCutClassification, explicitKeep });
				dbg(config, { usedExplicitCut: false, noCutClassification: lastNoCutClassification });
				return { cancel: true };
			}
			firstKeptEntryId = ownCut.firstKeptEntryId;
			agentMessages = ownCut.messages;
		}

		if (agentMessages.length === 0) {
			lastNoCutClassification = classifyNoCut(branchEntries as any[], eventContext);
			logPiVccEvent("no_safe_cut", { classification: lastNoCutClassification, explicitKeep });
			return { cancel: true };
		}

		lastNoCutClassification = null;
		const messages = convertToLlm(agentMessages);
		const tail = keptTailStats(branchEntries as any[], firstKeptEntryId);
		lastStats = {
			summarized: agentMessages.length,
			kept: tail.kept,
			keptTokensEst: tail.keptTokensEst,
			reason: eventContext.reason,
			willRetry: eventContext.willRetry,
		};

		const summary = compile({
			messages,
			previousSummary: preparation.previousSummary,
			compactionFocus,
			fileOps: {
				readFiles: [...preparation.fileOps.read],
				modifiedFiles: [...preparation.fileOps.written, ...preparation.fileOps.edited],
			},
		});
		const details: PiVccCompactionDetails = {
			compactor: "pi-vcc",
			version: 2,
			sections: [...summary.matchAll(/^\[(.+?)\]/gm)].map((match) => match[1]),
			sourceMessageCount: agentMessages.length,
			previousSummaryUsed: Boolean(preparation.previousSummary),
			reason: eventContext.reason,
			willRetry: eventContext.willRetry,
		};

		dbg(config, {
			usedExplicitCut: explicitKeep !== undefined,
			messagesToSummarize: agentMessages.length,
			messagesPreviewHead: agentMessages.slice(0, 3).map((message: any) => ({ role: message.role, preview: previewContent(message.content) })),
			messagesPreviewTail: agentMessages.slice(-3).map((message: any) => ({ role: message.role, preview: previewContent(message.content) })),
			firstKeptEntryId,
			tokensBefore: preparation.tokensBefore,
			summaryLength: summary.length,
			compaction: { reason: eventContext.reason, willRetry: eventContext.willRetry, explicitKeep },
		});

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
