import type { CompactionFocus, FileOps, PiMessage } from "../types";
import { normalize } from "./normalize";
import { filterNoise } from "./filter-noise";
import { pruneForSummary } from "./prune";
import { buildSections } from "./build-sections";
import { formatSummary, capBrief, wrapLongLines, sanitizeHeaderItem } from "./format";
import { redact } from "./redact";
import { collapseSkillLines } from "./skill-collapse";

export interface CompileInput {
  messages: PiMessage[];
  previousSummary?: string;
  fileOps?: FileOps;
  compactionFocus?: CompactionFocus;
}

const HEADER_NAMES = ["Session Goal", "Compaction Intent", "Files And Changes", "Outstanding Context", "User Preferences"];
const SEPARATOR = "\n\n---\n\n";
const RECALL_NOTE = "Note: conversation history before this summary is searchable via `vcc_recall`.";

const escapeRegExp = (text: string): string => text.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");

const sectionOf = (text: string, header: string): string => {
  const headerText = text.split(SEPARATOR)[0] ?? "";
  const tagRe = new RegExp(`(^|\\n\\n)\\[${escapeRegExp(header)}\\](?:\\n|$)`);
  const match = headerText.match(tagRe);
  if (!match || match.index === undefined) return "";
  const start = match.index + (match[1]?.length ?? 0);
  const after = headerText.slice(start);
  const bodyStart = after.indexOf("\n");
  if (bodyStart < 0) return "";
  const body = after.slice(bodyStart + 1);
  const nextSection = body.match(/\n\n\[[^\]\n]+\](?:\n|$)/)?.index;
  const end = nextSection !== undefined && nextSection > 0 ? nextSection : undefined;
  return (end ? body.slice(0, end) : body).trim();
};

const briefOf = (text: string): string => {
  const idx = text.indexOf(SEPARATOR);
  if (idx < 0) return "";
  return text.slice(idx + SEPARATOR.length).trim();
};

const sanitizeBulletLine = (line: string): string => {
  const text = line.startsWith("- ") ? line.slice(2) : line;
  const sanitized = sanitizeHeaderItem(text);
  return sanitized ? `- ${sanitized}` : "";
};

const bulletLinesOf = (text: string): string[] => {
  const lines: string[] = [];
  for (const rawLine of text.split("\n")) {
    if (/^\[[^\]\n]+\]$/.test(rawLine)) break;
    if (rawLine.startsWith("- ")) {
      const line = sanitizeBulletLine(rawLine);
      if (line) lines.push(line);
    } else if (/^\s+\S/.test(rawLine) && lines.length > 0) {
      const continuation = sanitizeHeaderItem(rawLine);
      if (continuation) lines[lines.length - 1] += ` ${continuation}`;
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
  if (header === "Outstanding Context" || header === "Compaction Intent") {
    return fresh ? `[${header}]\n${fresh}` : "";
  }

  if (header === "Files And Changes") {
    return mergeFileLines(prev, fresh);
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
  const normalizedBlocks = filterNoise(normalize(input.messages));
  const blocks = pruneForSummary(normalizedBlocks);
  const data = buildSections({ blocks, compactionFocus: input.compactionFocus });
  const fresh = formatSummary(data);
  const merged = input.previousSummary ? mergePrevious(input.previousSummary, fresh) : fresh;
  if (!merged) return "";
  return redact(wrapLongLines(redact(merged)));
};
