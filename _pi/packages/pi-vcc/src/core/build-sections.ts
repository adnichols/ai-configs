import type { CompactionIntent, NormalizedBlock } from "../types";
import { clip, firstLine, nonEmptyLines } from "./content";
import type { SectionData } from "../sections";
import { extractGoals } from "../extract/goals";
import { extractFiles } from "../extract/files";
import { extractPreferences } from "../extract/preferences";
import { buildBriefSections, sectionsToTranscript, stringifyBrief } from "./brief";

export interface BuildSectionsInput {
  blocks: NormalizedBlock[];
  compactionIntent?: CompactionIntent;
}

const BLOCKER_RE =
  /\b(fail(ed|s|ure|ing)?|broken|cannot|can't|won't work|does not work|doesn't work|still (broken|failing|wrong)|blocked|blocker|not (fixed|resolved|working)|crash(es|ed|ing)?)\b/i;

const extractOutstandingContext = (blocks: NormalizedBlock[]): string[] => {
  const items: string[] = [];
  const tail = blocks.slice(-20);

  for (const b of tail) {
    if (b.kind === "tool_result" && b.isError) {
      items.push(`[${b.name}] ${firstLine(b.text, 150)}`);
      continue;
    }

    if (b.kind === "assistant" || b.kind === "user") {
      for (const line of nonEmptyLines(b.text)) {
        if (!BLOCKER_RE.test(line)) continue;
        if (line.length < 15) continue;
        const clipped = b.kind === "user" ? `[user] ${clip(line, 150)}` : clip(line, 150);
        if (!items.includes(clipped)) items.push(clipped);
        break;
      }
    }
  }

  return items.slice(0, 5);
};

const formatFileActivity = (blocks: NormalizedBlock[]): string[] => {
  const act = extractFiles(blocks);
  // Dedup: if already Modified, drop from Created (file existed before)
  for (const p of act.modified) act.created.delete(p);
  const lines: string[] = [];
  const cap = (set: Set<string>, limit: number) => {
    const arr = [...set];
    if (arr.length <= limit) return arr.join(", ");
    return arr.slice(0, limit).join(", ") + ` (+${arr.length - limit} more)`;
  };
  if (act.modified.size > 0) lines.push(`Modified: ${cap(act.modified, 10)}`);
  if (act.created.size > 0) lines.push(`Created: ${cap(act.created, 10)}`);
  if (act.read.size > 0) lines.push(`Read: ${cap(act.read, 10)}`);
  return lines;
};

const intentText = (value?: string): string | undefined => {
  const cleaned = value?.replace(/\s+/g, " ").trim();
  return cleaned ? clip(cleaned, 500) : undefined;
};

const formatCompactionIntent = (intent?: CompactionIntent): string[] => {
  if (!intent) return [];
  const source = intentText(intent.source);
  const boundary = intentText(intent.boundary);
  const reason = intentText(intent.reason);
  const preserve = intentText(intent.preserve);
  const parts = [
    source ? `source=${source}` : "",
    boundary ? `boundary=${boundary}` : "",
    reason ? `reason=${reason}` : "",
    preserve ? `preserve=${preserve}` : "",
  ].filter(Boolean);
  return parts.length ? [parts.join("; ")] : [];
};

export const buildSections = (input: BuildSectionsInput): SectionData => {
  const { blocks } = input;
  const briefSections = buildBriefSections(blocks);
  return {
    sessionGoal: extractGoals(blocks),
    compactionIntent: formatCompactionIntent(input.compactionIntent),
    outstandingContext: extractOutstandingContext(blocks),
    filesAndChanges: formatFileActivity(blocks),
    userPreferences: extractPreferences(blocks),
    briefTranscript: stringifyBrief(briefSections),
    transcriptEntries: sectionsToTranscript(briefSections),
  };
};
