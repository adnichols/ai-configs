import type { Message } from "@earendil-works/pi-ai";

const ts = Date.now();
const assistBase = {
  api: "messages" as any,
  provider: "anthropic" as any,
  model: "test",
  usage: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
  timestamp: ts,
};

export const userMsg = (text: string): Message => ({
  role: "user",
  content: text,
  timestamp: ts,
});

export const assistantText = (text: string): Message => ({
  role: "assistant",
  content: [{ type: "text", text }],
  ...assistBase,
  stopReason: "stop",
});

export const assistantWithThinking = (
  text: string,
  thinking: string,
): Message => ({
  role: "assistant",
  content: [
    { type: "thinking", thinking },
    { type: "text", text },
  ],
  ...assistBase,
  stopReason: "stop",
});

export const assistantWithToolCall = (
  name: string,
  args: Record<string, unknown>,
  toolCallId = "tc_1",
): Message => ({
  role: "assistant",
  content: [{ type: "toolCall", id: toolCallId, name, arguments: args }],
  ...assistBase,
  stopReason: "toolUse",
});

// Tombstone left behind when an in-flight request is aborted (hard-backstop
// interrupt or user escape): persisted as an assistant message with no
// content and stopReason "aborted" directly after the last tool result.
export const assistantAborted = (): Message => ({
  role: "assistant",
  content: [],
  ...assistBase,
  stopReason: "aborted" as any,
});

export const toolResult = (
  name: string,
  text: string,
  isError = false,
  toolCallId = "tc_1",
): Message => ({
  role: "toolResult",
  toolCallId,
  toolName: name,
  content: [{ type: "text", text }],
  isError,
  timestamp: ts,
});
