import type { SectionData } from "../sections";

export const sanitizeHeaderItem = (item: string): string => item.replace(/\s+/g, " ").trim();

const section = (title: string, items: string[] = []): string => {
  const cleanItems = items.map(sanitizeHeaderItem).filter(Boolean);
  if (cleanItems.length === 0) return "";
  const body = cleanItems.map((i) => `- ${i}`).join("\n");
  return `[${title}]\n${body}`;
};

const BRIEF_MAX_LINES = 120;
const PROTECTED_BRIEF_PIN_MAX_NON_SIGNAL_LINES = 30;
const PROTECTED_BRIEF_PIN_MAX_SIGNAL_LINES = 100;
const PROTECTED_BRIEF_PIN_SIGNAL_HEAD_LINES = 50;
const PROTECTED_PIN_SIGNAL_RE = /(?:\bP[123]\b|No issues found|Impact:|Minimal fix:|Path:|File:|Reproducible condition:|Condition:|FINDINGS_TO_RESOLVE|findings? to resolve|\bseverity\b|\breviewer\b)/i;
const BRIEF_HEADER_RE = /^\[(?:user|assistant|tool_error|tool_result)\](?:\s|$)/;
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

const omittedProtectedToolResultLines = (allLines: string[], keptStart: number): string[] => {
  const signalPinned: string[] = [];
  const otherPinned: string[] = [];
  for (let i = 0; i < keptStart; i++) {
    if (!/^\[tool_result\]\s+/.test(allLines[i])) continue;
    const section: string[] = [];
    for (let j = i; j < allLines.length; j++) {
      if (j > i && BRIEF_HEADER_RE.test(allLines[j])) break;
      section.push(allLines[j]);
    }
    if (section.length === 0) continue;
    const target = section.some((line) => PROTECTED_PIN_SIGNAL_RE.test(line)) ? signalPinned : otherPinned;
    target.push(...section, "");
  }
  const cappedSignal = signalPinned.length > PROTECTED_BRIEF_PIN_MAX_SIGNAL_LINES
    ? [
        ...signalPinned.slice(0, PROTECTED_BRIEF_PIN_SIGNAL_HEAD_LINES),
        `[${signalPinned.length - PROTECTED_BRIEF_PIN_MAX_SIGNAL_LINES} protected signal lines omitted; use vcc_recall for full review output]`,
        "",
        ...signalPinned.slice(-(PROTECTED_BRIEF_PIN_MAX_SIGNAL_LINES - PROTECTED_BRIEF_PIN_SIGNAL_HEAD_LINES)),
      ]
    : signalPinned;
  return [
    ...cappedSignal,
    ...otherPinned.slice(-PROTECTED_BRIEF_PIN_MAX_NON_SIGNAL_LINES),
  ];
};

export const capBrief = (text: string): string => {
  const lines = text.split("\n");
  if (lines.length <= BRIEF_MAX_LINES) return text;
  const omitted = lines.length - BRIEF_MAX_LINES;
  const keptStart = lines.length - BRIEF_MAX_LINES;
  const kept = lines.slice(keptStart);
  const firstHeader = kept.findIndex((l) => BRIEF_HEADER_RE.test(l));
  const clean = firstHeader > 0 ? kept.slice(firstHeader) : kept;
  const pinned = omittedProtectedToolResultLines(lines, keptStart);
  const pinNotice = pinned.length > 0 ? "; protected tool results pinned" : "";
  const pinnedText = pinned.length > 0 ? `${pinned.join("\n").trimEnd()}\n\n` : "";
  return `...(${omitted} earlier lines omitted${pinNotice})\n\n${pinnedText}${clean.join("\n")}`;
};

export const formatSummary = (data: SectionData): string => {
  const headerParts = [
    section("Session Goal", data.sessionGoal),
    section("Compaction Intent", data.compactionIntent),
    section("Files And Changes", data.filesAndChanges),
    section("Outstanding Context", data.outstandingContext),
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
