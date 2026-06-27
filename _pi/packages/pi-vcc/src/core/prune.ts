import type { NormalizedBlock } from "../types";

const ERROR_PRUNE_AFTER_TURNS = 4;
const ERROR_INPUT_PRUNE_THRESHOLD_CHARS = 2000;
const MAX_PRUNED_TOOL_RESULT_CHARS = 1200;

const PROTECTED_TOOL_NAMES = new Set([
  "todo",
  "Agent",
  "get_subagent_result",
  "spawn_council",
  "read_council_stream",
  "plan-review",
]);

interface ToolCallInfo {
  key: string;
  index: number;
}

const stableJson = (value: unknown): string => {
  if (value == null || typeof value !== "object") return JSON.stringify(value);
  if (Array.isArray(value)) return `[${value.map(stableJson).join(",")}]`;
  const record = value as Record<string, unknown>;
  return `{${Object.keys(record).sort().map((key) => `${JSON.stringify(key)}:${stableJson(record[key])}`).join(",")}}`;
};

const firstErrorLine = (text: string): string => {
  const line = text.split("\n").find((entry) => /error|failed|exception|nonzero|exit/i.test(entry));
  return (line ?? text.split("\n")[0] ?? "").trim();
};

const isProtected = (name: string) => PROTECTED_TOOL_NAMES.has(name) || /review|subagent/i.test(name);

const toolKey = (block: NormalizedBlock): string | null =>
  block.kind === "tool_call" ? `${block.name}:${stableJson(block.args)}` : null;

const summarizeLargeResult = (text: string): string => {
  if (text.length <= MAX_PRUNED_TOOL_RESULT_CHARS) return text;
  const lines = text.split("\n").filter(Boolean);
  const error = lines.find((line) => /error|failed|exception|nonzero|exit/i.test(line));
  const status = [...lines].reverse().find((line) => /done|success|passed|failed|error|exit|completed/i.test(line));
  const paths = lines.filter((line) => /(?:^|[\s"'`])(?:\.?\.?\/)?[\w.-]+(?:\/[\w.@-]+)+/.test(line)).slice(0, 6);
  const pieces = [
    text.slice(0, Math.floor(MAX_PRUNED_TOOL_RESULT_CHARS * 0.65)).trimEnd(),
    "[Large tool result pruned]",
    error ? `first error/status: ${error.trim()}` : "",
    status && status !== error ? `final status: ${status.trim()}` : "",
    paths.length ? `paths: ${paths.join(" | ")}` : "",
  ].filter(Boolean);
  return pieces.join("\n").slice(0, MAX_PRUNED_TOOL_RESULT_CHARS);
};

export const pruneForSummary = (blocks: NormalizedBlock[]): NormalizedBlock[] => {
  const latestByKey = new Map<string, number>();
  const callById = new Map<string, ToolCallInfo>();

  for (let i = 0; i < blocks.length; i++) {
    const key = toolKey(blocks[i]);
    if (!key) continue;
    latestByKey.set(key, i);
    const block = blocks[i];
    if (block.kind === "tool_call" && block.toolCallId) {
      callById.set(block.toolCallId, { key, index: i });
    }
  }

  let summarizedTurns = 0;
  const pruned: NormalizedBlock[] = [];

  for (const block of blocks) {
    if (block.kind === "user" || block.kind === "assistant") summarizedTurns++;

    if (block.kind !== "tool_result") {
      pruned.push(block);
      continue;
    }

    if (isProtected(block.name)) {
      pruned.push(block);
      continue;
    }

    const associatedCall = block.toolCallId ? callById.get(block.toolCallId) : undefined;
    if (associatedCall && latestByKey.get(associatedCall.key) !== associatedCall.index) {
      const latestIndex = latestByKey.get(associatedCall.key);
      pruned.push({
        ...block,
        isError: false,
        text: `[Older duplicate tool result pruned; latest result kept at #${latestIndex ?? "unknown"}]`,
      });
      continue;
    }

    if (block.isError && block.text.length > ERROR_INPUT_PRUNE_THRESHOLD_CHARS && summarizedTurns > ERROR_PRUNE_AFTER_TURNS) {
      pruned.push({
        ...block,
        text: `[Bulky failed tool output pruned after ${ERROR_PRUNE_AFTER_TURNS} turns; error evidence preserved] ${firstErrorLine(block.text)}`,
      });
    } else {
      pruned.push({ ...block, text: summarizeLargeResult(block.text) });
    }
  }

  return pruned;
};
