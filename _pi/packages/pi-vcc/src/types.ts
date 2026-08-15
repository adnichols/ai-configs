import type { Message } from "@earendil-works/pi-ai";

export interface FileOps {
  readFiles?: string[];
  modifiedFiles?: string[];
  createdFiles?: string[];
}

export interface BashExecutionMessage {
  role: "bashExecution";
  command?: string;
  output?: string;
  exitCode?: number;
}

export type PiMessage = Message | BashExecutionMessage;

export type CompactionReason = "manual" | "threshold" | "overflow";

export type NoCutReason =
  | "tiny_session"
  | "already_compacted"
  | "post_compaction_tail_too_short"
  | "active_turn_no_safe_cut"
  | "unknown_no_safe_cut";

export interface NoCutClassification {
  reason: NoCutReason;
  hadPreviousCompaction: boolean;
  liveMessageCount: number;
  latestLiveRole?: string;
  activeTurnInferred: boolean;
  firstKeptEntryId?: string;
  compactionReason?: CompactionReason;
  willRetry?: boolean;
}

export interface CompactionFocus {
  source: string;
  reason?: string;
  boundary?: string;
  preserve?: string;
}

export const isBashExecutionMessage = (msg: PiMessage): msg is BashExecutionMessage =>
  msg.role === "bashExecution";

export type NormalizedBlock =
  | { kind: "user"; text: string; sourceIndex?: number }
  | { kind: "assistant"; text: string; sourceIndex?: number }
  | { kind: "tool_call"; name: string; args: Record<string, unknown>; toolCallId?: string; sourceIndex?: number }
  | { kind: "tool_result"; name: string; text: string; isError: boolean; toolCallId?: string; sourceIndex?: number }
  | { kind: "bash"; command: string; output: string; exitCode: number | undefined; sourceIndex?: number }
  | { kind: "thinking"; text: string; redacted: boolean; sourceIndex?: number };
