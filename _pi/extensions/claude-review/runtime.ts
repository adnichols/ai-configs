import { spawn, spawnSync } from "node:child_process";
import { closeSync, existsSync, mkdirSync, openSync, readFileSync, readdirSync, statSync, writeFileSync } from "node:fs";
import { mkdir, realpath, stat, unlink } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { randomUUID } from "node:crypto";

export const REVIEW_TIMEOUT_SECONDS = 3600;
export const SMOKE_TIMEOUT_SECONDS = 120;
export const REVIEW_WATCHDOG_MS = 4_200_000;
export const SMOKE_WATCHDOG_MS = 300_000;
const DEFAULT_KILL_GRACE_MS = 2_000;
const MAX_SUMMARY_CHARS = 5_000;

export type ClaudeReviewAction = "start" | "smoke";
export type ClaudeReviewStatus = "running" | "succeeded" | "failed" | "timed_out" | "cancelled";

export interface LaunchRequest {
  action: ClaudeReviewAction;
  cwd: string;
  promptFile?: string;
  output: string;
  reviewName: string;
}

export interface StartRequest {
  action: ClaudeReviewAction;
  cwd: string;
  promptFile?: string;
  output: string;
}

export interface JobSnapshot {
  jobId: string;
  action: ClaudeReviewAction;
  status: ClaudeReviewStatus;
  classification?: string;
  summary: string;
  cwd: string;
  promptFile?: string;
  output: string;
  stdoutLog: string;
  stderrLog: string;
  stateFile: string;
  pid?: number;
  startedAt: string;
  completedAt?: string;
  exitCode?: number | null;
  signal?: NodeJS.Signals | null;
}

export interface CompletionEvent extends JobSnapshot {}

interface ManagerOptions {
  launcherPath: string;
  cacheDir: string;
  pythonExecutable?: string;
  onComplete?: (event: CompletionEvent) => void | Promise<void>;
  reviewWatchdogMs?: number;
  smokeWatchdogMs?: number;
  killGraceMs?: number;
  maxCompletedJobs?: number;
  spawnImpl?: typeof spawn;
  cleanupTmuxImpl?: (reviewName: string, pid: number | undefined) => void;
  now?: () => Date;
  makeId?: () => string;
}

interface InternalJob extends JobSnapshot {
  reviewName: string;
  child?: ReturnType<typeof spawn>;
  stdoutFd?: number;
  stderrFd?: number;
  watchdog?: ReturnType<typeof setTimeout>;
  forceKillTimer?: ReturnType<typeof setTimeout>;
  requestedTerminalStatus?: "timed_out" | "cancelled";
  suppressNotification: boolean;
  finalized: boolean;
  notificationSent: boolean;
  done: Promise<JobSnapshot>;
  resolveDone: (job: JobSnapshot) => void;
}

export function buildLauncherArgs(request: LaunchRequest): string[] {
  if (request.action === "smoke") {
    return [
      "--smoke",
      "--cwd", request.cwd,
      "--output", request.output,
      "--review-name", request.reviewName,
      "--timeout-seconds", String(SMOKE_TIMEOUT_SECONDS),
    ];
  }
  if (!request.promptFile) throw new Error("promptFile is required for Claude review jobs");
  return [
    "--cwd", request.cwd,
    "--prompt-file", request.promptFile,
    "--output", request.output,
    "--review-name", request.reviewName,
    "--timeout-seconds", String(REVIEW_TIMEOUT_SECONDS),
  ];
}

export function classifyArtifact(action: ClaudeReviewAction, text: string): { ok: boolean; classification: string } {
  const normalized = text.replace(/\r/g, "");
  const firstCode = normalized.match(/^\s*(CLAUDE_[A-Z0-9_]+)/)?.[1];
  if (firstCode && firstCode !== "CLAUDE_REVIEW_SMOKE_READY" && firstCode !== "CLAUDE_REVIEW_LAUNCHER_METADATA") {
    return { ok: false, classification: firstCode };
  }
  if (action === "smoke") {
    const ok = normalized.includes("CLAUDE_REVIEW_SMOKE_READY")
      && /^socket=.+$/m.test(normalized)
      && /^session=.+$/m.test(normalized);
    return { ok, classification: ok ? "CLAUDE_REVIEW_SMOKE_READY" : "CLAUDE_REVIEW_ARTIFACT_INVALID" };
  }
  const metadataIndex = normalized.indexOf("CLAUDE_REVIEW_LAUNCHER_METADATA");
  const answer = metadataIndex >= 0 ? normalized.slice(0, metadataIndex).replace(/---\s*$/, "").trim() : "";
  const ok = metadataIndex >= 0 && /^VERDICT:\s*\S+/m.test(answer);
  return { ok, classification: ok ? "CLAUDE_REVIEW_SUCCEEDED" : "CLAUDE_REVIEW_ARTIFACT_INVALID" };
}

function bounded(text: string): string {
  if (text.length <= MAX_SUMMARY_CHARS) return text;
  return `${text.slice(0, MAX_SUMMARY_CHARS)}\n[summary truncated; read the artifact/log for full output]`;
}

function safeRead(file: string): string {
  try {
    return readFileSync(file, "utf8");
  } catch {
    return "";
  }
}

function snapshot(job: InternalJob): JobSnapshot {
  return {
    jobId: job.jobId,
    action: job.action,
    status: job.status,
    classification: job.classification,
    summary: job.summary,
    cwd: job.cwd,
    promptFile: job.promptFile,
    output: job.output,
    stdoutLog: job.stdoutLog,
    stderrLog: job.stderrLog,
    stateFile: job.stateFile,
    pid: job.pid,
    startedAt: job.startedAt,
    completedAt: job.completedAt,
    exitCode: job.exitCode,
    signal: job.signal,
  };
}

async function resolveExistingDirectory(value: string, label: string): Promise<string> {
  const resolved = path.resolve(value);
  let info;
  try {
    info = await stat(resolved);
  } catch {
    throw new Error(`${label} does not exist: ${resolved}`);
  }
  if (!info.isDirectory()) throw new Error(`${label} is not a directory: ${resolved}`);
  return realpath(resolved);
}

async function resolveExistingFile(value: string, label: string): Promise<string> {
  const resolved = path.resolve(value);
  let info;
  try {
    info = await stat(resolved);
  } catch {
    throw new Error(`${label} does not exist: ${resolved}`);
  }
  if (!info.isFile()) throw new Error(`${label} is not a file: ${resolved}`);
  return realpath(resolved);
}

export function cleanupPrivateTmuxSockets(
  reviewName: string,
  pid: number | undefined,
  options: {
    socketDir?: string;
    tmuxExecutable?: string;
    spawnSyncImpl?: typeof spawnSync;
  } = {},
): void {
  if (!pid || typeof process.getuid !== "function") return;
  const base = options.socketDir ?? path.join(process.env.TMUX_TMPDIR ?? os.tmpdir(), `tmux-${process.getuid()}`);
  const prefix = `claude-review-${reviewName.replace(/[^A-Za-z0-9_.-]+/g, "-").replace(/^-+|-+$/g, "")}-${pid}-`;
  let names: string[];
  try { names = readdirSync(base); } catch { return; }
  const run = options.spawnSyncImpl ?? spawnSync;
  for (const name of names) {
    if (!name.startsWith(prefix)) continue;
    try {
      run(options.tmuxExecutable ?? "tmux", ["-L", name, "kill-server"], {
        stdio: "ignore",
        timeout: 5_000,
        shell: false,
      });
    } catch { /* socket is already gone or tmux is unavailable */ }
  }
}

function killProcessTree(job: InternalJob, signal: NodeJS.Signals): void {
  const child = job.child;
  if (!child || child.exitCode !== null || child.signalCode !== null) return;
  try {
    if (process.platform !== "win32" && child.pid) {
      process.kill(-child.pid, signal);
    } else {
      child.kill(signal);
    }
  } catch {
    try { child.kill(signal); } catch { /* already gone */ }
  }
}

export class ClaudeReviewJobManager {
  private readonly launcherPath: string;
  private readonly cacheDir: string;
  private readonly pythonExecutable: string;
  private readonly onComplete?: ManagerOptions["onComplete"];
  private readonly reviewWatchdogMs: number;
  private readonly smokeWatchdogMs: number;
  private readonly killGraceMs: number;
  private readonly maxCompletedJobs: number;
  private readonly spawnImpl: typeof spawn;
  private readonly cleanupTmuxImpl: (reviewName: string, pid: number | undefined) => void;
  private readonly now: () => Date;
  private readonly makeId: () => string;
  private readonly jobs = new Map<string, InternalJob>();
  private readonly activeOutputs = new Map<string, string>();
  private shuttingDown = false;

  constructor(options: ManagerOptions) {
    this.launcherPath = path.resolve(options.launcherPath);
    this.cacheDir = path.resolve(options.cacheDir);
    this.pythonExecutable = options.pythonExecutable ?? "python3";
    this.onComplete = options.onComplete;
    this.reviewWatchdogMs = options.reviewWatchdogMs ?? REVIEW_WATCHDOG_MS;
    this.smokeWatchdogMs = options.smokeWatchdogMs ?? SMOKE_WATCHDOG_MS;
    this.killGraceMs = options.killGraceMs ?? DEFAULT_KILL_GRACE_MS;
    this.maxCompletedJobs = Math.max(1, options.maxCompletedJobs ?? 100);
    this.spawnImpl = options.spawnImpl ?? spawn;
    this.cleanupTmuxImpl = options.cleanupTmuxImpl ?? cleanupPrivateTmuxSockets;
    this.now = options.now ?? (() => new Date());
    this.makeId = options.makeId ?? (() => randomUUID().replaceAll("-", "").slice(0, 12));
  }

  async start(request: StartRequest): Promise<JobSnapshot> {
    if (this.shuttingDown) throw new Error("Claude review manager is shutting down");
    const cwd = await resolveExistingDirectory(request.cwd, "cwd");
    const promptFile = request.action === "start"
      ? await resolveExistingFile(request.promptFile ?? "", "promptFile")
      : undefined;
    if (!existsSync(this.launcherPath) || !statSync(this.launcherPath).isFile()) {
      throw new Error(`canonical Claude review launcher not found: ${this.launcherPath}. Run ./install.sh --pi`);
    }

    const requestedOutput = path.resolve(cwd, request.output);
    await mkdir(path.dirname(requestedOutput), { recursive: true });
    const output = path.join(await realpath(path.dirname(requestedOutput)), path.basename(requestedOutput));
    const jobId = `claude-review-${this.makeId()}`;
    const reviewName = jobId;
    if (this.activeOutputs.has(output)) {
      throw new Error(`output already has an active Claude review job: ${output}`);
    }
    this.activeOutputs.set(output, jobId);

    const stdoutLog = path.join(this.cacheDir, `${jobId}.stdout.log`);
    const stderrLog = path.join(this.cacheDir, `${jobId}.stderr.log`);
    const stateFile = path.join(this.cacheDir, `${jobId}.json`);
    let stdoutFd: number | undefined;
    let stderrFd: number | undefined;
    try {
      await unlink(output);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") {
        this.activeOutputs.delete(output);
        throw new Error(`cannot clear stale Claude review output before launch: ${output}: ${String(error)}`);
      }
    }
    try {
      mkdirSync(this.cacheDir, { recursive: true });
      stdoutFd = openSync(stdoutLog, "a", 0o600);
      stderrFd = openSync(stderrLog, "a", 0o600);
    } catch (error) {
      if (stdoutFd !== undefined) try { closeSync(stdoutFd); } catch { /* closed */ }
      if (stderrFd !== undefined) try { closeSync(stderrFd); } catch { /* closed */ }
      if (this.activeOutputs.get(output) === jobId) this.activeOutputs.delete(output);
      throw error;
    }
    let resolveDone = (_job: JobSnapshot) => {};
    const done = new Promise<JobSnapshot>((resolve) => { resolveDone = resolve; });
    const job: InternalJob = {
      jobId,
      reviewName,
      action: request.action,
      status: "running",
      summary: `Claude ${request.action === "smoke" ? "smoke" : "review"} running in background`,
      cwd,
      promptFile,
      output,
      stdoutLog,
      stderrLog,
      stateFile,
      startedAt: this.now().toISOString(),
      suppressNotification: false,
      finalized: false,
      notificationSent: false,
      stdoutFd,
      stderrFd,
      done,
      resolveDone,
    };
    this.jobs.set(jobId, job);

    const args = buildLauncherArgs({ action: request.action, cwd, promptFile, output, reviewName });
    let child;
    try {
      child = this.spawnImpl(this.pythonExecutable, [this.launcherPath, ...args], {
        cwd,
        detached: process.platform !== "win32",
        shell: false,
        stdio: ["ignore", stdoutFd, stderrFd],
      });
    } catch (error) {
      await this.finalize(job, null, null, "failed", "CLAUDE_REVIEW_SPAWN_FAILED", String(error));
      throw error;
    }
    job.child = child;
    job.pid = child.pid;

    child.once("error", (error) => {
      void this.finalize(job, null, null, "failed", "CLAUDE_REVIEW_SPAWN_FAILED", String(error));
    });
    child.once("exit", (code, signal) => {
      void this.handleExit(job, code, signal);
    });

    const watchdogMs = request.action === "smoke" ? this.smokeWatchdogMs : this.reviewWatchdogMs;
    job.watchdog = setTimeout(() => {
      if (job.finalized) return;
      job.requestedTerminalStatus = "timed_out";
      killProcessTree(job, "SIGTERM");
      job.forceKillTimer = setTimeout(() => killProcessTree(job, "SIGKILL"), this.killGraceMs);
    }, watchdogMs);
    job.watchdog.unref?.();

    return snapshot(job);
  }

  status(jobId: string): JobSnapshot | undefined {
    const job = this.jobs.get(jobId);
    return job ? snapshot(job) : undefined;
  }

  list(): JobSnapshot[] {
    return [...this.jobs.values()]
      .sort((a, b) => a.startedAt.localeCompare(b.startedAt))
      .map(snapshot);
  }

  async cancel(jobId: string): Promise<boolean> {
    const job = this.jobs.get(jobId);
    if (!job || job.finalized || job.status !== "running") return false;
    job.requestedTerminalStatus = "cancelled";
    killProcessTree(job, "SIGTERM");
    job.forceKillTimer = setTimeout(() => killProcessTree(job, "SIGKILL"), this.killGraceMs);
    return true;
  }

  async shutdown(): Promise<void> {
    this.shuttingDown = true;
    const active = [...this.jobs.values()].filter((job) => !job.finalized && job.status === "running");
    await Promise.all(active.map(async (job) => {
      job.suppressNotification = true;
      await this.cancel(job.jobId);
      await job.done;
    }));
  }

  private async handleExit(job: InternalJob, code: number | null, signal: NodeJS.Signals | null): Promise<void> {
    if (job.finalized) return;
    if (job.requestedTerminalStatus === "timed_out") {
      this.cleanupTmuxImpl(job.reviewName, job.pid);
      await this.finalize(job, code, signal, "timed_out", "CLAUDE_REVIEW_OUTER_TIMEOUT", `Outer watchdog timed out; private tmux cleanup attempted; output=${job.output}`);
      return;
    }
    if (job.requestedTerminalStatus === "cancelled") {
      this.cleanupTmuxImpl(job.reviewName, job.pid);
      await this.finalize(job, code, signal, "cancelled", "CLAUDE_REVIEW_CANCELLED", `Claude review job was cancelled and private tmux cleanup was attempted; output=${job.output}`);
      return;
    }

    const artifactExists = existsSync(job.output);
    const artifact = artifactExists ? safeRead(job.output) : "";
    if (code === 0) {
      if (!artifactExists) {
        await this.finalize(job, code, signal, "failed", "CLAUDE_REVIEW_ARTIFACT_MISSING", `Launcher exited zero but did not create output=${job.output}`);
        return;
      }
      const result = classifyArtifact(job.action, artifact);
      if (!result.ok) {
        await this.finalize(job, code, signal, "failed", result.classification, bounded(artifact || `Invalid output=${job.output}`));
        return;
      }
      await this.finalize(job, code, signal, "succeeded", result.classification, `Claude ${job.action === "smoke" ? "smoke" : "review"} succeeded; output=${job.output}`);
      return;
    }

    if (artifactExists) {
      const result = classifyArtifact(job.action, artifact);
      const classification = result.ok ? "CLAUDE_REVIEW_PROCESS_FAILED" : result.classification;
      await this.finalize(job, code, signal, "failed", classification, bounded(artifact));
      return;
    }
    const stderr = safeRead(job.stderrLog);
    const stdout = safeRead(job.stdoutLog);
    await this.finalize(
      job,
      code,
      signal,
      "failed",
      "CLAUDE_REVIEW_PROCESS_FAILED",
      bounded(`Launcher exited ${code ?? "without code"} and produced no artifact.\nstdout=${job.stdoutLog}\nstderr=${job.stderrLog}\n${stderr || stdout}`),
    );
  }

  private async finalize(
    job: InternalJob,
    code: number | null,
    signal: NodeJS.Signals | null,
    status: ClaudeReviewStatus,
    classification: string,
    summary: string,
  ): Promise<void> {
    if (job.finalized) return;
    job.finalized = true;
    if (job.watchdog) clearTimeout(job.watchdog);
    if (job.forceKillTimer) clearTimeout(job.forceKillTimer);
    if (job.stdoutFd !== undefined) { try { closeSync(job.stdoutFd); } catch { /* closed */ } job.stdoutFd = undefined; }
    if (job.stderrFd !== undefined) { try { closeSync(job.stderrFd); } catch { /* closed */ } job.stderrFd = undefined; }
    job.status = status;
    job.classification = classification;
    job.summary = bounded(`${summary}\nstdout=${job.stdoutLog}\nstderr=${job.stderrLog}`);
    job.completedAt = this.now().toISOString();
    job.exitCode = code;
    job.signal = signal;
    if (this.activeOutputs.get(job.output) === job.jobId) this.activeOutputs.delete(job.output);
    job.child = undefined;
    const result = snapshot(job);
    try {
      writeFileSync(job.stateFile, `${JSON.stringify(result, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
    } catch (error) {
      job.summary = bounded(`${job.summary}\nstate persistence failed: ${String(error)}`);
    }
    job.resolveDone(snapshot(job));
    if (!job.notificationSent) {
      job.notificationSent = true;
      if (!job.suppressNotification) {
        try { await this.onComplete?.(snapshot(job)); } catch { /* state file and status remain available */ }
      }
    }
    this.pruneCompletedHistory();
  }

  private pruneCompletedHistory(): void {
    const completed = [...this.jobs.values()]
      .filter((candidate) => candidate.finalized)
      .sort((a, b) => (a.completedAt ?? a.startedAt).localeCompare(b.completedAt ?? b.startedAt));
    for (const stale of completed.slice(0, Math.max(0, completed.length - this.maxCompletedJobs))) {
      this.jobs.delete(stale.jobId);
    }
  }
}

const REVIEW_INTENT_RE = /\b(?:read-only\s+)?(?:pre-?pr|implementation|code|plan|change|diff)?\s*review\b|\b(?:audit|find\s+bugs?|security\s+findings?)\b|\bCLEAN_FOR_PR\b|\bFINDINGS_TO_RESOLVE\b/i;
const DIRECT_CLAUDE_RE = /\bclaude(?:\s|$)/i;
const LAUNCHER_REFERENCE_RE = /claude_interactive_review\.py\b/i;
const BENIGN_LAUNCHER_REFERENCE_RE = /^\s*(?:rg|grep|find|ls|stat|readlink|cat|sed|cmp|diff|head|tail|wc|sha256sum|shasum|git\s+(?:grep|diff|show|log))\b/i;

function launcherReferenceIsExecution(command: string): boolean {
  if (!LAUNCHER_REFERENCE_RE.test(command)) return false;
  if (/(?:&|\|\||[;|]|\$\(|[<>]\(|`|\n)/.test(command)) return true;
  if (/^\s*find\b/i.test(command) && /-(?:exec|execdir|ok|okdir)\b/i.test(command)) return true;
  if (/^\s*rg\b/i.test(command) && /--pre(?:=|\s|$)/i.test(command)) return true;
  return !BENIGN_LAUNCHER_REFERENCE_RE.test(command);
}

export function isForbiddenDirectReviewToolCall(toolName: string, input: unknown): boolean {
  if (!input || typeof input !== "object") return false;
  const data = input as Record<string, unknown>;
  if (toolName === "bash" || toolName === "process") {
    const command = typeof data.command === "string" ? data.command : "";
    if (launcherReferenceIsExecution(command)) return true;
    return DIRECT_CLAUDE_RE.test(command) && REVIEW_INTENT_RE.test(command);
  }
  if (toolName !== "interactive_shell") return false;
  const command = typeof data.command === "string" ? data.command : "";
  if (launcherReferenceIsExecution(command)) return true;
  if (DIRECT_CLAUDE_RE.test(command) && REVIEW_INTENT_RE.test(command)) return true;
  const spawnRequest = data.spawn && typeof data.spawn === "object" ? data.spawn as Record<string, unknown> : undefined;
  return spawnRequest?.agent === "claude"
    && typeof spawnRequest.prompt === "string"
    && REVIEW_INTENT_RE.test(spawnRequest.prompt);
}

export function defaultLauncherPath(): string {
  return path.join(os.homedir(), ".agents", "skills", "claude-code-review", "scripts", "claude_interactive_review.py");
}

export function defaultCacheDir(): string {
  return path.join(os.homedir(), ".pi", "agent", "cache", "claude-review");
}
