import type { NormalizedBlock } from "../types";
import { clip, firstLine } from "./content";
import { redact } from "./redact";
import { extractPath } from "./tool-args";
import { sanitizeHeaderItem } from "./format";
import { collapseSkillText } from "./skill-collapse";
import { isProtectedToolName } from "./protected-tools";

const TRUNCATE_USER = 256;
const TRUNCATE_ASSISTANT = 200;
const PROTECTED_TOOL_RESULT_LINE_CHARS = 240;
const PROTECTED_TOOL_RESULT_LEADING_LINES = 2;
const PROTECTED_TOOL_RESULT_SIGNAL_LINES = 60;
const PROTECTED_SIGNAL_HEAD_LINES = 30;
const PROTECTED_SIGNAL_RE = /(?:\bP[123]\b|No issues found|Impact:|Minimal fix:|Path:|File:|Reproducible condition:|Condition:|FINDINGS_TO_RESOLVE|findings? to resolve|\bseverity\b|\breviewer\b)/i;

// ── noise filtering ──

const isNoiseUser = (text: string): boolean => {
  return !text.trim();
};

// ── truncation ──

// Unicode-aware word segmentation via Intl.Segmenter (built-in, zero dependency)
const segmenter = new Intl.Segmenter(undefined, { granularity: "word" });

/** Check if segment is a word (Bun's isWordLike is unreliable for alphanumeric tokens) */
const isWord = (seg: { segment: string; isWordLike: boolean }): boolean =>
  seg.isWordLike || /[\p{L}\p{N}]/u.test(seg.segment);

// Common stop words — don't count toward budget
const STOP_WORDS = new Set([
  "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
  "have", "has", "had", "do", "does", "did", "will", "would", "could",
  "should", "may", "might", "shall", "can", "need", "must",
  "to", "of", "in", "for", "on", "with", "at", "by", "from", "as",
  "into", "through", "during", "before", "after", "above", "below",
  "between", "under", "over",
  "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
  "neither", "each", "every", "all", "any", "few", "more", "most",
  "other", "some", "such", "no",
  "that", "this", "these", "those", "it", "its",
  "i", "me", "my", "we", "our", "you", "your", "he", "him", "his",
  "she", "her", "they", "them", "their", "who", "which", "what",
  "if", "then", "than", "when", "where", "how", "just", "also",
]);

const truncateTokens = (text: string, limit: number): string => {
  const flat = text.replace(/\s+/g, " ").trim();
  let count = 0;
  let lastEnd = 0;
  for (const seg of segmenter.segment(flat)) {
    if (isWord(seg)) {
      if (!STOP_WORDS.has(seg.segment.toLowerCase())) {
        count++;
        if (count > limit) {
          return flat.slice(0, lastEnd).trimEnd() + "...(truncated)";
        }
      }
    }
    lastEnd = seg.index + seg.segment.length;
  }
  return flat;
};

// ── bash command compression ──

const BASH_CAP = 120;
const PIPE_TAIL_RE = /\s*\|\s*(?:head|tail|sort|wc|column|tr|cut|awk|uniq|python3|node|bun)(?:\s[^|]*)?$/;

/** Semantic compression: strip cd prefix, pipe tail formatting, cap length */
const compressBash = (raw: string): string => {
  // Flatten multi-line: take first meaningful line
  let cmd = raw.split("\n").map(l => l.trim()).filter(Boolean)[0] ?? raw;
  // Strip cd <path> && prefix
  cmd = cmd.replace(/^cd\s+\S+\s*&&\s*/, "");
  // Strip pipe tail formatting commands (up to 3 times)
  for (let i = 0; i < 3; i++) {
    const stripped = cmd.replace(PIPE_TAIL_RE, "");
    if (stripped === cmd) break;
    cmd = stripped;
  }
  if (cmd.length > BASH_CAP) {
    return cmd.slice(0, BASH_CAP - 3) + "...";
  }
  return cmd;
};

// ── tool summary ──

const TOOL_SUMMARY_FIELDS: Record<string, string> = {
  Read: "file_path", Edit: "file_path", Write: "file_path",
  read: "file_path", edit: "file_path", write: "file_path",
  Glob: "pattern", Grep: "pattern",
};

const cleanProtectedLine = (line: string): string =>
  redact(clip(sanitizeHeaderItem(line), PROTECTED_TOOL_RESULT_LINE_CHARS));

const protectedToolResultLines = (text: string): string[] => {
  const lines = text
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const signalLines = lines.filter((entry) => PROTECTED_SIGNAL_RE.test(entry)).map(cleanProtectedLine);
  const selected = signalLines.length > PROTECTED_TOOL_RESULT_SIGNAL_LINES
    ? [
        ...signalLines.slice(0, PROTECTED_SIGNAL_HEAD_LINES),
        `[${signalLines.length - PROTECTED_TOOL_RESULT_SIGNAL_LINES} protected finding/status lines omitted; use vcc_recall for full review output]`,
        ...signalLines.slice(-(PROTECTED_TOOL_RESULT_SIGNAL_LINES - PROTECTED_SIGNAL_HEAD_LINES)),
      ]
    : signalLines;

  for (const line of lines.slice(0, PROTECTED_TOOL_RESULT_LEADING_LINES)) {
    const clipped = cleanProtectedLine(line);
    if (!selected.includes(clipped)) selected.push(clipped);
  }
  return selected;
};

const toolOneLiner = (name: string, args: Record<string, unknown>): string => {
  const field = TOOL_SUMMARY_FIELDS[name];
  if (field && typeof args[field] === "string") {
    return `* ${name} "${sanitizeHeaderItem(args[field] as string)}"`;
  }
  const path = extractPath(args);
  if (path) return `* ${name} "${sanitizeHeaderItem(path)}"`;
  if (name === "bash" || name === "Bash") {
    const raw = (args.command ?? args.description ?? "") as string;
    const cmd = compressBash(raw);
    return `* ${name} "${redact(cmd)}"`;
  }
  if (typeof args.query === "string") {
    return `* ${name} "${clip(sanitizeHeaderItem(args.query as string), 60)}"`;
  }
  return `* ${name}`;
};

export interface BriefLine {
  /** Section header like "[user]", "[assistant]", "[tool_error] bash" */
  header: string;
  /** Content lines for this section */
  lines: string[];
}

/** Structured transcript entry for JSON output */
export interface TranscriptEntry {
  role: "user" | "assistant" | "tool_error" | "tool_result";
  text?: string;
  tool?: string;
  cmd?: string;
  ref?: string;
  /** Collapse count when identical tool calls are grouped */
  count?: number;
}

/**
 * Build BriefLine sections from NormalizedBlocks.
 */
export const buildBriefSections = (blocks: NormalizedBlock[]): BriefLine[] => {
  const sections: BriefLine[] = [];
  let lastHeader = "";

  const push = (header: string, line: string) => {
    if (header === lastHeader && sections.length > 0) {
      sections[sections.length - 1].lines.push(line);
      return;
    }
    sections.push({ header, lines: [line] });
    lastHeader = header;
  };

  for (const b of blocks) {
    switch (b.kind) {
      case "user": {
        if (isNoiseUser(b.text)) break;
        const text = truncateTokens(collapseSkillText(b.text), TRUNCATE_USER);
        if (text) {
          const ref = b.sourceIndex != null ? ` (#${b.sourceIndex})` : "";
          push("[user]", text + ref);
        }
        lastHeader = "[user]";
        break;
      }
      case "bash": {
        const cmd = redact(compressBash(b.command));
        const ref = b.sourceIndex != null ? ` (#${b.sourceIndex})` : "";
        if (cmd) {
          push("[user]", `$ ${cmd}${ref}`);
          lastHeader = "[user]";
        }
        break;
      }
      case "assistant": {
        const text = truncateTokens(b.text, TRUNCATE_ASSISTANT);
        if (text) {
          const ref = b.sourceIndex != null ? ` (#${b.sourceIndex})` : "";
          push("[assistant]", text + ref);
        }
        break;
      }
      case "tool_call": {
        const ref = b.sourceIndex != null ? ` (#${b.sourceIndex})` : "";
        const summary = toolOneLiner(b.name, b.args) + ref;
        push("[assistant]", summary);
        break;
      }
      case "tool_result": {
        const ref = b.sourceIndex != null ? ` (#${b.sourceIndex})` : "";
        if (b.isError) {
          const header = `[tool_error] ${b.name}${ref}`;
          push(header, firstLine(b.text, 150));
          lastHeader = header;
        } else if (isProtectedToolName(b.name)) {
          const lines = protectedToolResultLines(b.text);
          if (lines.length > 0) {
            const header = `[tool_result] ${b.name}${ref}`;
            for (const line of lines) push(header, line);
            lastHeader = header;
          }
        }
        break;
      }
      case "thinking":
        break;
    }
  }

  // Collapse consecutive identical tool lines (same text, different #ref)
  for (const sec of sections) {
    if (sec.header !== "[assistant]") continue;
    const out: string[] = [];
    for (const line of sec.lines) {
      if (!line.startsWith("* ")) { out.push(line); continue; }
      const ref = line.match(/\(#(\d+)\)$/)?.[1] ?? "";
      const base = ref ? line.slice(0, -(ref.length + 3)).trimEnd() : line;
      const last = out.length > 0 ? out[out.length - 1] : "";
      const m = last.match(/^(.*) \((#[\d, #]+)\) x(\d+)$/);
      if (m && m[1] === base) {
        out[out.length - 1] = `${base} (${m[2]}, #${ref}) x${parseInt(m[3]) + 1}`;
      } else if (last.match(/\(#\d+\)$/) && last.replace(/\s*\(#\d+\)$/, "") === base) {
        const prevRef = last.match(/\(#(\d+)\)$/)?.[1];
        out[out.length - 1] = `${base} (#${prevRef}, #${ref}) x2`;
      } else {
        out.push(line);
      }
    }
    sec.lines = out;
  }

  return sections;
};

/**
 * Stringify BriefLine sections into text format.
 */
export const stringifyBrief = (sections: BriefLine[]): string => {

  // Emit sections -- suppress blank lines between consecutive tool summaries
  const out: string[] = [];
  for (let i = 0; i < sections.length; i++) {
    const sec = sections[i];
    if (i > 0) {
      const prev = sections[i - 1];
      const prevIsTools = prev.header === "[assistant]" &&
        prev.lines.every((l) => l.startsWith("* "));
      const curIsTools = sec.header === "[assistant]" &&
        sec.lines.every((l) => l.startsWith("* "));
      if (!(prevIsTools && curIsTools)) {
        out.push("");
      }
    }
    out.push(sec.header);
    for (const line of sec.lines) {
      out.push(line);
    }
  }

  return out.join("\n");
};

/** Parse a text line into a structured TranscriptEntry */
const parseToolLine = (line: string): { tool: string; cmd?: string; ref?: string; count?: number } | null => {
  // * bash "cmd" (#5)
  // * bash "cmd" (#1, #3) x2
  // * tilth "query" (#7)
  const m = line.match(/^\* (\S+)\s*(?:"([^"]*)")?\s*(?:\((#[\d, #]+)\))?\s*(?:x(\d+))?$/);
  if (!m) return null;
  return {
    tool: m[1],
    cmd: m[2] || undefined,
    ref: m[3] || undefined,
    count: m[4] ? parseInt(m[4]) : undefined,
  };
};

const extractRef = (text: string): { clean: string; ref?: string } => {
  const m = text.match(/\s*\(#(\d+)\)$/);
  if (!m) return { clean: text };
  return { clean: text.slice(0, m.index).trimEnd(), ref: `#${m[1]}` };
};

/**
 * Convert BriefLine sections to structured TranscriptEntry array for JSON output.
 */
export const sectionsToTranscript = (sections: BriefLine[]): TranscriptEntry[] => {
  const entries: TranscriptEntry[] = [];

  for (const sec of sections) {
    if (sec.header === "[user]") {
      for (const line of sec.lines) {
        const { clean, ref } = extractRef(line);
        entries.push({ role: "user", text: clean, ...(ref && { ref }) });
      }
    } else if (sec.header === "[assistant]") {
      for (const line of sec.lines) {
        if (line.startsWith("* ")) {
          const parsed = parseToolLine(line);
          if (parsed) {
            entries.push({
              role: "assistant",
              tool: parsed.tool,
              ...(parsed.cmd && { cmd: parsed.cmd }),
              ...(parsed.ref && { ref: parsed.ref }),
              ...(parsed.count && { count: parsed.count }),
            });
          } else {
            // Fallback: unparseable tool line
            const { clean, ref } = extractRef(line.slice(2));
            entries.push({ role: "assistant", text: clean, ...(ref && { ref }) });
          }
        } else {
          const { clean, ref } = extractRef(line);
          entries.push({ role: "assistant", text: clean, ...(ref && { ref }) });
        }
      }
    } else if (sec.header.startsWith("[tool_error]") || sec.header.startsWith("[tool_result]")) {
      // [tool_error] bash (#5), [tool_result] get_subagent_result (#5)
      const headerMatch = sec.header.match(/^\[(tool_error|tool_result)\]\s+(\S+)\s*(?:\(#(\d+)\))?/);
      const role = (headerMatch?.[1] ?? "tool_error") as "tool_error" | "tool_result";
      const tool = headerMatch?.[2] ?? "unknown";
      const ref = headerMatch?.[3] ? `#${headerMatch[3]}` : undefined;
      for (const line of sec.lines) {
        entries.push({
          role,
          tool,
          text: line,
          ...(ref && { ref }),
        });
      }
    }
  }

  return entries;
};

/** Convenience: build sections from blocks and stringify to text */
export const compileBrief = (blocks: NormalizedBlock[]): string =>
  stringifyBrief(buildBriefSections(blocks));
