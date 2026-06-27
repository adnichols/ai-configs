import type { NormalizedBlock } from "../types";

export interface CommitInfo {
  hash: string;
  subject: string;
  files: string[];
}

const GIT_COMMAND_RE = /\bgit\s+(?:commit|show|log)\b/;
const COMMIT_MSG_RE = /git\s+commit[^\n]*?-m\s+(?:"((?:[^"\\]|\\.)*)"|'((?:[^'\\]|\\.)*)')/;
const BRACKET_COMMIT_RE = /^\[[^\]]*\s+([0-9a-f]{7,40})[^\]]*\]\s+([^\n]+)$/gm;
const FULL_COMMIT_RE = /^commit\s+([0-9a-f]{7,40})\b[^\n]*\n[\s\S]*?^\s{4}([^\n]+)$/gm;
const ONELINE_COMMIT_RE = /^([0-9a-f]{7,40})\s+([^\n]+)$/gm;
const FILE_RE = /(?:^|[\s"'`])((?:\.?\.?\/)?[\w.@-]+(?:\/[\w.@-]+)+\.[\w-]+)/g;

const cleanSubject = (text: string): string => text.replace(/\\"/g, '"').replace(/\\'/g, "'").trim();

const subjectFromCommand = (command: string): string | undefined => {
  const match = command.match(COMMIT_MSG_RE);
  const subject = cleanSubject(match?.[1] ?? match?.[2] ?? "");
  return subject || undefined;
};

const extractFiles = (text: string): string[] => {
  const files: string[] = [];
  for (const match of text.matchAll(FILE_RE)) {
    const file = match[1].replace(/^\.\//, "");
    if (!files.includes(file)) files.push(file);
    if (files.length >= 5) break;
  }
  return files;
};

const pushCommit = (commits: CommitInfo[], hash: string, subject: string, output: string, command: string) => {
  const normalizedHash = hash.slice(0, 12);
  if (commits.some((commit) => commit.hash === normalizedHash)) return;
  commits.push({
    hash: normalizedHash,
    subject: (subject.trim() || subjectFromCommand(command) || "session commit").slice(0, 120),
    files: extractFiles(output),
  });
};

const appendCommitsFromOutput = (commits: CommitInfo[], command: string, output: string) => {
  if (!GIT_COMMAND_RE.test(command)) return;

  for (const match of output.matchAll(BRACKET_COMMIT_RE)) {
    pushCommit(commits, match[1], match[2], output, command);
  }

  for (const match of output.matchAll(FULL_COMMIT_RE)) {
    pushCommit(commits, match[1], match[2], output, command);
  }

  if (/\bgit\s+log\b/.test(command)) {
    for (const match of output.matchAll(ONELINE_COMMIT_RE)) {
      pushCommit(commits, match[1], match[2], output, command);
    }
  }
};

export const extractCommits = (blocks: NormalizedBlock[], limit = 8): CommitInfo[] => {
  const commits: CommitInfo[] = [];
  for (let i = 0; i < blocks.length; i++) {
    const block = blocks[i];

    if (block.kind === "bash") {
      if (block.exitCode && block.exitCode !== 0) continue;
      appendCommitsFromOutput(commits, block.command, block.output);
      continue;
    }

    if (block.kind !== "tool_call" || block.name !== "bash") continue;
    const command = typeof block.args.command === "string" ? block.args.command : "";
    if (!GIT_COMMAND_RE.test(command)) continue;

    for (let j = i + 1; j < Math.min(blocks.length, i + 8); j++) {
      const result = blocks[j];
      if (result.kind !== "tool_result") continue;
      if (block.toolCallId && result.toolCallId && result.toolCallId !== block.toolCallId) continue;
      if (result.isError) break;
      appendCommitsFromOutput(commits, command, result.text);
      break;
    }
  }
  return commits.slice(-limit);
};

export const formatCommits = (commits: CommitInfo[]): string[] =>
  commits.map((commit) => {
    const files = commit.files.length ? ` (files: ${commit.files.join(", ")})` : "";
    return `${commit.hash.slice(0, 7)}: ${commit.subject}${files}`;
  });
