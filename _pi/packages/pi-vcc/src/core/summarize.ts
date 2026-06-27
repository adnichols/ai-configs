import type { CompactionIntent, FileOps, PiMessage } from "../types";
import { normalize } from "./normalize";
import { filterNoise } from "./filter-noise";
import { pruneForSummary } from "./prune";
import { buildSections } from "./build-sections";
import { formatSummary, capBrief, wrapLongLines } from "./format";
import { redact } from "./redact";
import { collapseSkillLines } from "./skill-collapse";

export interface CompileInput {
  messages: PiMessage[];
  previousSummary?: string;
  fileOps?: FileOps;
  compactionIntent?: CompactionIntent;
}

const HEADER_NAMES = ["Session Goal", "Compaction Intent", "Files And Changes", "Outstanding Context", "Commits", "User Preferences"];
const SEPARATOR = "\n\n---\n\n";
const RECALL_NOTE = "Note: conversation history before this summary is searchable via `vcc_recall`.";

const sectionOf = (text: string, header: string): string => {
  const tag = `[${header}]`;
  const start = text.indexOf(tag);
  if (start < 0) return "";
  const after = text.slice(start);
  const nextSection = HEADER_NAMES
    .filter((h) => h !== header)
    .map((h) => after.indexOf(`[${h}]`))
    .filter((n) => n > 0);
  const nextSep = after.indexOf(SEPARATOR);
  const candidates = [...nextSection, ...(nextSep > 0 ? [nextSep] : [])].sort((a, b) => a - b);
  const end = candidates[0];
  return (end ? after.slice(0, end) : after).trim();
};

const briefOf = (text: string): string => {
  const idx = text.indexOf(SEPARATOR);
  if (idx < 0) return "";
  return text.slice(idx + SEPARATOR.length).trim();
};

const bulletLinesOf = (text: string): string[] => {
  const lines: string[] = [];
  for (const rawLine of text.split("\n")) {
    if (rawLine.startsWith("- ")) {
      lines.push(rawLine);
    } else if (/^\s+\S/.test(rawLine) && lines.length > 0) {
      lines[lines.length - 1] += ` ${rawLine.trim()}`;
    }
  }
  return lines;
};

const mergeFileLines = (prev: string, fresh: string): string => {
  const categories = ["Modified", "Created", "Read"] as const;
  const merged: Record<string, Set<string>> = {};
  for (const cat of categories) merged[cat] = new Set();

  for (const text of [prev, fresh]) {
    for (const line of bulletLinesOf(text)) {
      for (const cat of categories) {
        const prefix = `- ${cat}: `;
        if (!line.startsWith(prefix)) continue;
        let rest = line.slice(prefix.length);
        rest = rest.replace(/\s*\(\+\d+ more\)\s*$/, "");
        for (const p of rest.split(",")) {
          const trimmed = p.trim();
          if (trimmed) merged[cat].add(trimmed);
        }
      }
    }
  }

  for (const p of merged.Modified) merged.Created.delete(p);

  const cap = (set: Set<string>, limit: number) => {
    const arr = [...set];
    if (arr.length <= limit) return arr.join(", ");
    return arr.slice(0, limit).join(", ") + ` (+${arr.length - limit} more)`;
  };

  const lines: string[] = [];
  if (merged.Modified.size > 0) lines.push(`- Modified: ${cap(merged.Modified, 10)}`);
  if (merged.Created.size > 0) lines.push(`- Created: ${cap(merged.Created, 10)}`);
  if (merged.Read.size > 0) lines.push(`- Read: ${cap(merged.Read, 10)}`);
  if (lines.length === 0) return "";
  return `[Files And Changes]\n${lines.join("\n")}`;
};

const mergeHeaderSection = (header: string, prev: string, fresh: string): string => {
  if (header === "Outstanding Context" || header === "Compaction Intent") return fresh;
  if (!prev) return fresh;
  if (!fresh) return prev;

  if (header === "Files And Changes") {
    return mergeFileLines(prev, fresh);
  }

  if (header === "Commits") {
    const combined = [...new Set([...bulletLinesOf(prev), ...bulletLinesOf(fresh)])];
    const capped = combined.length > 8 ? combined.slice(-8) : combined;
    return capped.length ? `[${header}]\n${capped.join("\n")}` : "";
  }

  const isClean = (l: string) => !l.includes("<skill") && !l.includes("</skill");
  const prevLines = bulletLinesOf(prev).filter(isClean);
  const freshLines = bulletLinesOf(fresh).filter(isClean);
  const combined = [...new Set([...prevLines, ...freshLines])];
  const CAP = header === "Session Goal" ? 8 : 15;
  const capped = combined.length > CAP ? combined.slice(-CAP) : combined;
  if (capped.length === 0) return "";
  return `[${header}]\n${capped.join("\n")}`;
};

const sanitizeBrief = (text: string): string => {
  if (!text) return "";
  const lines = collapseSkillLines(text.split("\n"))
    .filter((line) => !line.startsWith(RECALL_NOTE));
  return lines.join("\n").trim();
};

const mergeBriefTranscript = (prev: string, fresh: string): string => {
  const cleanPrev = sanitizeBrief(prev);
  const cleanFresh = sanitizeBrief(fresh);
  if (!cleanPrev) return cleanFresh;
  if (!cleanFresh) return cleanPrev;
  return cleanPrev + "\n\n" + cleanFresh;
};

const mergePrevious = (prev: string, fresh: string): string => {
  const headers = HEADER_NAMES
    .map((header) => {
      const freshSec = sectionOf(fresh, header);
      const prevSec = sectionOf(prev, header);
      return mergeHeaderSection(header, prevSec, freshSec);
    })
    .filter(Boolean);

  const prevBrief = briefOf(prev);
  const freshBrief = briefOf(fresh);
  const mergedBrief = mergeBriefTranscript(prevBrief, freshBrief);

  const parts: string[] = [];
  if (headers.length > 0) {
    parts.push(headers.join("\n\n"));
  }
  if (mergedBrief) {
    parts.push(capBrief(mergedBrief));
  }

  return parts.join(SEPARATOR);
};

export const compile = (input: CompileInput): string => {
  const blocks = pruneForSummary(filterNoise(normalize(input.messages)));
  const data = buildSections({ blocks, compactionIntent: input.compactionIntent });
  const fresh = formatSummary(data);
  const merged = input.previousSummary ? mergePrevious(input.previousSummary, fresh) : fresh;
  if (!merged) return "";
  return redact(wrapLongLines(redact(merged)));
};
