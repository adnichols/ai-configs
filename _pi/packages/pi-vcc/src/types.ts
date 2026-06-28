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

export interface CompactionIntent {
  source?: string;
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
