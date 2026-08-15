import { readFileSync } from "fs";
import type { Message } from "@earendil-works/pi-ai";
import { isLegacyContinuationMessage } from "./custom-message-classifier";
import { renderMessage, type RenderedEntry } from "./render-entries";

export interface LoadedMessages {
  rendered: RenderedEntry[];
  rawMessages: Message[];
}

export const loadAllMessages = (sessionFile: string, full: boolean): LoadedMessages => {
  const content = readFileSync(sessionFile, "utf-8");
  const entries: any[] = [];
  for (const line of content.split("\n")) {
    if (!line.trim()) continue;
    try { entries.push(JSON.parse(line)); } catch {}
  }
  const messageEntries = entries.filter((e) => e.type === "message" && e.message);
  const rendered = messageEntries.map((e, i) => {
    const renderedMessage = renderMessage(e.message, i, full);
    if (!isLegacyContinuationMessage(e.message)) return renderedMessage;
    return {
      ...renderedMessage,
      role: "legacy_continuation",
      summary: `[historical pi-vcc continuation] ${renderedMessage.summary}`,
    };
  });
  const rawMessages = messageEntries.map((e) => e.message);
  return { rendered, rawMessages };
};
