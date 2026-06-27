import type { SectionData } from "../sections";

const section = (title: string, items: string[] = []): string => {
  if (items.length === 0) return "";
  const body = items.map((i) => `- ${i}`).join("\n");
  return `[${title}]\n${body}`;
};

const BRIEF_MAX_LINES = 120;
const TUI_SAFE_LINE_CHARS = 120;

const wrapLine = (line: string, maxChars: number): string[] => {
  if (line.length <= maxChars) return [line];

  const indent = line.match(/^\s*(?:[-*]\s+|\d+\.\s+)?/)?.[0] ?? "";
  const continuationIndent = indent ? " ".repeat(Math.min(indent.length, 8)) : "";
  const wrapped: string[] = [];
  let remaining = line;
  let prefix = "";

  while (prefix.length + remaining.length > maxChars) {
    const available = Math.max(20, maxChars - prefix.length);
    let splitAt = remaining.lastIndexOf(" ", available);
    if (splitAt < Math.floor(available * 0.5)) splitAt = available;

    wrapped.push(prefix + remaining.slice(0, splitAt).trimEnd());
    remaining = remaining.slice(splitAt).trimStart();
    prefix = continuationIndent;
  }

  if (remaining) wrapped.push(prefix + remaining);
  return wrapped;
};

export const wrapLongLines = (text: string, maxChars = TUI_SAFE_LINE_CHARS): string =>
  text.split("\n").flatMap((line) => wrapLine(line, maxChars)).join("\n");

export const capBrief = (text: string): string => {
  const lines = text.split("\n");
  if (lines.length <= BRIEF_MAX_LINES) return text;
  const omitted = lines.length - BRIEF_MAX_LINES;
  const kept = lines.slice(-BRIEF_MAX_LINES);
  const firstHeader = kept.findIndex((l) => /^\[.+\]/.test(l));
  const clean = firstHeader > 0 ? kept.slice(firstHeader) : kept;
  return `...(${omitted} earlier lines omitted)\n\n${clean.join("\n")}`;
};

export const formatSummary = (data: SectionData): string => {
  const headerParts = [
    section("Session Goal", data.sessionGoal),
    section("Compaction Intent", data.compactionIntent),
    section("Files And Changes", data.filesAndChanges),
    section("Outstanding Context", data.outstandingContext),
    section("Commits", data.commits),
    section("User Preferences", data.userPreferences),
  ].filter(Boolean);

  const parts: string[] = [];
  if (headerParts.length > 0) {
    parts.push(headerParts.join("\n\n"));
  }
  if (data.briefTranscript) {
    parts.push(capBrief(data.briefTranscript));
  }

  return parts.join("\n\n---\n\n");
};
