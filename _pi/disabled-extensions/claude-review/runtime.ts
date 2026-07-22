import { spawn, spawnSync } from "node:child_process";
import { closeSync, existsSync, mkdirSync, openSync, readFileSync, readdirSync, renameSync, statSync, unlinkSync, writeFileSync } from "node:fs";
import { mkdir, realpath, stat, unlink } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { createHash, randomUUID } from "node:crypto";

import { classifyArtifact as classifyArtifactContract } from "./artifact-contract.mjs";

export const REVIEW_TIMEOUT_SECONDS = 3600;
export const SMOKE_TIMEOUT_SECONDS = 120;
export const REVIEW_WATCHDOG_MS = 4_200_000;
export const SMOKE_WATCHDOG_MS = 300_000;
const DEFAULT_KILL_GRACE_MS = 2_000;
const DEFAULT_POLL_INTERVAL_MS = 100;
const MAX_SUMMARY_CHARS = 5_000;

export type ClaudeReviewAction = "start" | "smoke";
export type ClaudeReviewStatus = "running" | "succeeded" | "failed" | "timed_out" | "cancelled" | "interrupted";

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
  originSessionId?: string;
  originSessionFile?: string;
  onAccepted?: (job: JobSnapshot) => void;
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
  supervisorPid?: number;
  launcherPid?: number;
  heartbeatAt?: string;
  startedAt: string;
  completedAt?: string;
  exitCode?: number | null;
  signal?: NodeJS.Signals | null;
  originSessionId?: string;
  originSessionFile?: string;
}

export interface CompletionEvent extends JobSnapshot {}

interface ManagerOptions {
  launcherPath: string;
  cacheDir: string;
  supervisorPath?: string;
  pythonExecutable?: string;
  nodeExecutable?: string;
  onComplete?: (event: CompletionEvent) => void | Promise<void>;
  deferNotification?: (event: CompletionEvent) => boolean;
  sessionsDir?: string;
  reviewWatchdogMs?: number;
  smokeWatchdogMs?: number;
  killGraceMs?: number;
  pollIntervalMs?: number;
  maxCompletedJobs?: number;
  spawnImpl?: typeof spawn;
  cleanupTmuxImpl?: (reviewName: string, pid: number | undefined) => void;
  now?: () => Date;
  makeId?: () => string;
}

interface InternalJob extends JobSnapshot {
  reviewName: string;
  reservationFile: string;
  notificationFile: string;
  notificationSent: boolean;
  recovered: boolean;
  poller?: ReturnType<typeof setInterval>;
}

interface SupervisorRequest {
  reviewName: string;
  launcherPath: string;
  launcherArgs: string[];
  pythonExecutable: string;
  stateFile: string;
  reservationFile: string;
  watchdogMs: number;
  killGraceMs: number;
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
  return classifyArtifactContract(action, text);
}

function bounded(text: string): string {
  if (text.length <= MAX_SUMMARY_CHARS) return text;
  return `${text.slice(0, MAX_SUMMARY_CHARS)}\n[summary truncated; read the artifact/log for full output]`;
}

function safeRead(file: string): string {
  try { return readFileSync(file, "utf8"); } catch { return ""; }
}

function processExists(pid: number | undefined): boolean {
  if (!pid) return false;
  try { process.kill(pid, 0); return true; } catch { return false; }
}

function supervisorIsHealthy(job: Pick<JobSnapshot, "pid" | "supervisorPid" | "heartbeatAt">): boolean {
  if (!processExists(job.supervisorPid ?? job.pid)) return false;
  const heartbeat = Date.parse(job.heartbeatAt ?? "");
  return Number.isFinite(heartbeat) && Date.now() - heartbeat < 15_000;
}

function killPidTree(pid: number | undefined, signal: NodeJS.Signals): void {
  if (!pid) return;
  try {
    if (process.platform !== "win32") process.kill(-pid, signal);
    else process.kill(pid, signal);
  } catch {
    try { process.kill(pid, signal); } catch { /* already gone */ }
  }
}

function atomicWriteJson(file: string, value: unknown): void {
  const tmp = `${file}.${process.pid}.${randomUUID()}.tmp`;
  writeFileSync(tmp, `${JSON.stringify(value, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
  renameSync(tmp, file);
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
    supervisorPid: job.supervisorPid,
    launcherPid: job.launcherPid,
    heartbeatAt: job.heartbeatAt,
    startedAt: job.startedAt,
    completedAt: job.completedAt,
    exitCode: job.exitCode,
    signal: job.signal,
    originSessionId: job.originSessionId,
    originSessionFile: job.originSessionFile,
  };
}

function isJobSnapshot(value: unknown): value is JobSnapshot {
  if (!value || typeof value !== "object") return false;
  const item = value as Partial<JobSnapshot>;
  const statuses: ClaudeReviewStatus[] = ["running", "succeeded", "failed", "timed_out", "cancelled", "interrupted"];
  return typeof item.jobId === "string"
    && (item.action === "start" || item.action === "smoke")
    && statuses.includes(item.status as ClaudeReviewStatus)
    && typeof item.cwd === "string"
    && typeof item.output === "string"
    && typeof item.stateFile === "string"
    && typeof item.startedAt === "string";
}

async function resolveExistingDirectory(value: string, label: string): Promise<string> {
  const resolved = path.resolve(value);
  let info;
  try { info = await stat(resolved); } catch { throw new Error(`${label} does not exist: ${resolved}`); }
  if (!info.isDirectory()) throw new Error(`${label} is not a directory: ${resolved}`);
  return realpath(resolved);
}

async function resolveExistingFile(value: string, label: string): Promise<string> {
  const resolved = path.resolve(value);
  let info;
  try { info = await stat(resolved); } catch { throw new Error(`${label} does not exist: ${resolved}`); }
  if (!info.isFile()) throw new Error(`${label} is not a file: ${resolved}`);
  return realpath(resolved);
}

export function cleanupPrivateTmuxSockets(
  reviewName: string,
  pid: number | undefined,
  options: { socketDir?: string; socketRoots?: string[]; tmuxExecutable?: string; spawnSyncImpl?: typeof spawnSync } = {},
): void {
  if (!pid || typeof process.getuid !== "function") return;
  const roots = options.socketDir
    ? [path.dirname(options.socketDir)]
    : (options.socketRoots ?? [process.env.TMUX_TMPDIR, os.tmpdir(), "/tmp", "/private/tmp"]).filter((value): value is string => Boolean(value));
  const bases = options.socketDir ? [options.socketDir] : [...new Set(roots.map((root) => path.join(root, `tmux-${process.getuid()}`)))];
  const prefix = `claude-review-${reviewName.replace(/[^A-Za-z0-9_.-]+/g, "-").replace(/^-+|-+$/g, "")}-${pid}-`;
  const run = options.spawnSyncImpl ?? spawnSync;
  const killed = new Set<string>();
  for (const base of bases) {
    let names: string[];
    try { names = readdirSync(base); } catch { continue; }
    for (const name of names) {
      if (!name.startsWith(prefix) || killed.has(name)) continue;
      killed.add(name);
      try {
        run(options.tmuxExecutable ?? "tmux", ["-S", path.join(base, name), "kill-server"], { stdio: "ignore", timeout: 5_000, shell: false });
      } catch { /* socket is already gone or tmux is unavailable */ }
    }
  }
}

export class ClaudeReviewJobManager {
  private readonly launcherPath: string;
  private readonly cacheDir: string;
  private readonly supervisorPath: string;
  private readonly pythonExecutable: string;
  private readonly nodeExecutable: string;
  private readonly onComplete?: ManagerOptions["onComplete"];
  private readonly deferNotification?: ManagerOptions["deferNotification"];
  private readonly sessionsDir: string;
  private readonly reviewWatchdogMs: number;
  private readonly smokeWatchdogMs: number;
  private readonly killGraceMs: number;
  private readonly pollIntervalMs: number;
  private readonly maxCompletedJobs: number;
  private readonly spawnImpl: typeof spawn;
  private readonly cleanupTmuxImpl: (reviewName: string, pid: number | undefined) => void;
  private readonly now: () => Date;
  private readonly makeId: () => string;
  private readonly jobs = new Map<string, InternalJob>();
  private readonly activeOutputs = new Map<string, string>();
  private readonly sessionDeliveryJobIds = new Map<string, Set<string>>();
  private observing = false;
  private activeSessionId?: string;
  private shuttingDown = false;

  constructor(options: ManagerOptions) {
    this.launcherPath = path.resolve(options.launcherPath);
    this.cacheDir = path.resolve(options.cacheDir);
    this.supervisorPath = path.resolve(options.supervisorPath ?? path.join(path.dirname(fileURLToPath(import.meta.url)), "supervisor.mjs"));
    this.pythonExecutable = options.pythonExecutable ?? "python3";
    this.nodeExecutable = options.nodeExecutable ?? process.execPath;
    this.onComplete = options.onComplete;
    this.deferNotification = options.deferNotification;
    this.sessionsDir = options.sessionsDir ?? path.join(os.homedir(), ".pi", "agent", "sessions");
    this.reviewWatchdogMs = options.reviewWatchdogMs ?? REVIEW_WATCHDOG_MS;
    this.smokeWatchdogMs = options.smokeWatchdogMs ?? SMOKE_WATCHDOG_MS;
    this.killGraceMs = options.killGraceMs ?? DEFAULT_KILL_GRACE_MS;
    this.pollIntervalMs = options.pollIntervalMs ?? DEFAULT_POLL_INTERVAL_MS;
    this.maxCompletedJobs = Math.max(1, options.maxCompletedJobs ?? 100);
    this.spawnImpl = options.spawnImpl ?? spawn;
    this.cleanupTmuxImpl = options.cleanupTmuxImpl ?? cleanupPrivateTmuxSockets;
    this.now = options.now ?? (() => new Date());
    this.makeId = options.makeId ?? (() => randomUUID().replaceAll("-", "").slice(0, 12));
    mkdirSync(this.cacheDir, { recursive: true });
    this.recoverPersistedJobs();
  }

  activate(sessionId?: string): void {
    if (sessionId) this.activeSessionId = sessionId;
    if (this.observing || this.shuttingDown) return;
    this.observing = true;
    for (const job of this.jobs.values()) {
      if (job.status === "running") {
        if (!supervisorIsHealthy(job)) this.reconcileInterrupted(job, true);
        if (job.status === "running") this.watch(job);
      } else {
        this.finishObservedJob(job, true);
      }
    }
  }

  async start(request: StartRequest): Promise<JobSnapshot> {
    if (this.shuttingDown) throw new Error("Claude review manager is shutting down");
    const cwd = await resolveExistingDirectory(request.cwd, "cwd");
    const promptFile = request.action === "start" ? await resolveExistingFile(request.promptFile ?? "", "promptFile") : undefined;
    if (!existsSync(this.launcherPath) || !statSync(this.launcherPath).isFile()) {
      throw new Error(`canonical Claude review launcher not found: ${this.launcherPath}. Run ./install.sh --pi`);
    }
    if (!existsSync(this.supervisorPath) || !statSync(this.supervisorPath).isFile()) {
      throw new Error(`Claude review supervisor not found: ${this.supervisorPath}. Run ./install.sh --pi`);
    }

    const requestedOutput = path.resolve(cwd, request.output);
    await mkdir(path.dirname(requestedOutput), { recursive: true });
    const output = path.join(await realpath(path.dirname(requestedOutput)), path.basename(requestedOutput));
    const jobId = `claude-review-${this.makeId()}`;
    const reviewName = jobId;
    const stdoutLog = path.join(this.cacheDir, `${jobId}.stdout.log`);
    const stderrLog = path.join(this.cacheDir, `${jobId}.stderr.log`);
    const stateFile = path.join(this.cacheDir, `${jobId}.state.json`);
    const requestFile = path.join(this.cacheDir, `${jobId}.request.json`);
    const reservationFile = this.reservationPath(output);
    this.reserveOutput(output, jobId, stateFile, reservationFile);

    try {
      await unlink(output);
    } catch (error) {
      if ((error as NodeJS.ErrnoException).code !== "ENOENT") {
        this.releaseReservation(reservationFile, jobId);
        throw new Error(`cannot clear stale Claude review output before launch: ${output}: ${String(error)}`);
      }
    }

    const job: InternalJob = {
      jobId,
      reviewName,
      action: request.action,
      status: "running",
      summary: `Claude ${request.action === "smoke" ? "smoke" : "review"} running under detached supervisor`,
      cwd,
      promptFile,
      output,
      stdoutLog,
      stderrLog,
      stateFile,
      startedAt: this.now().toISOString(),
      originSessionId: request.originSessionId ?? this.activeSessionId,
      originSessionFile: request.originSessionFile ? path.resolve(request.originSessionFile) : undefined,
      reservationFile,
      notificationFile: path.join(this.cacheDir, `${jobId}.notification.lock`),
      notificationSent: false,
      recovered: false,
    };
    atomicWriteJson(stateFile, snapshot(job));
    const supervisorRequest: SupervisorRequest = {
      reviewName,
      launcherPath: this.launcherPath,
      launcherArgs: buildLauncherArgs({ action: request.action, cwd, promptFile, output, reviewName }),
      pythonExecutable: this.pythonExecutable,
      stateFile,
      reservationFile,
      watchdogMs: request.action === "smoke" ? this.smokeWatchdogMs : this.reviewWatchdogMs,
      killGraceMs: this.killGraceMs,
    };
    atomicWriteJson(requestFile, supervisorRequest);

    let supervisor;
    try {
      supervisor = this.spawnImpl(this.nodeExecutable, [this.supervisorPath, requestFile], {
        cwd,
        detached: true,
        shell: false,
        stdio: "ignore",
      });
      await new Promise<void>((resolve, reject) => {
        supervisor!.once("spawn", resolve);
        supervisor!.once("error", reject);
      });
    } catch (error) {
      job.status = "failed";
      job.classification = "CLAUDE_REVIEW_SUPERVISOR_SPAWN_FAILED";
      job.summary = bounded(`${String(error)}\nstdout=${stdoutLog}\nstderr=${stderrLog}`);
      job.completedAt = this.now().toISOString();
      atomicWriteJson(stateFile, snapshot(job));
      this.releaseReservation(reservationFile, jobId);
      throw error;
    }
    supervisor.unref();
    job.pid = supervisor.pid;
    job.supervisorPid = supervisor.pid;
    let ownershipPublished = false;
    for (let attempt = 0; attempt < 50; attempt += 1) {
      try {
        const persisted = JSON.parse(readFileSync(stateFile, "utf8"));
        if (isJobSnapshot(persisted) && persisted.supervisorPid === supervisor.pid) {
          ownershipPublished = true;
          break;
        }
      } catch { /* supervisor has not published its ownership yet */ }
      await new Promise((resolve) => setTimeout(resolve, 5));
    }
    if (!ownershipPublished) {
      try { process.kill(supervisor.pid!, "SIGKILL"); } catch {}
      job.status = "failed";
      job.classification = "CLAUDE_REVIEW_SUPERVISOR_START_TIMEOUT";
      job.summary = bounded(`Detached supervisor did not publish ownership; output=${output}\nstdout=${stdoutLog}\nstderr=${stderrLog}`);
      job.completedAt = this.now().toISOString();
      atomicWriteJson(stateFile, snapshot(job));
      this.releaseReservation(reservationFile, jobId);
      try { unlinkSync(requestFile); } catch {}
      throw new Error(job.summary);
    }
    this.jobs.set(jobId, job);
    this.activeOutputs.set(output, jobId);
    request.onAccepted?.(snapshot(job));
    this.watch(job);
    return snapshot(job);
  }

  status(jobId: string): JobSnapshot | undefined {
    const job = this.jobs.get(jobId);
    if (!job) return undefined;
    this.refresh(job, true);
    return snapshot(job);
  }

  list(): JobSnapshot[] {
    for (const job of this.jobs.values()) this.refresh(job, true);
    return [...this.jobs.values()].sort((a, b) => a.startedAt.localeCompare(b.startedAt)).map(snapshot);
  }

  async cancel(jobId: string): Promise<boolean> {
    const job = this.jobs.get(jobId);
    if (!job) return false;
    this.refresh(job, false);
    if (job.status !== "running") return false;
    const pid = job.supervisorPid ?? job.pid;
    if (!processExists(pid)) {
      this.reconcileInterrupted(job, false);
      return false;
    }
    try { process.kill(pid!, "SIGTERM"); } catch { this.reconcileInterrupted(job, false); return false; }
    return true;
  }

  async shutdown(): Promise<void> {
    this.shuttingDown = true;
    this.observing = false;
    for (const job of this.jobs.values()) {
      if (job.poller) clearInterval(job.poller);
      job.poller = undefined;
    }
  }

  private recoverPersistedJobs(): void {
    let files: string[];
    try {
      files = readdirSync(this.cacheDir).filter((name) => /^claude-review-[^.]+(?:\.state)?\.json$/.test(name));
    } catch { return; }
    const recovered: Array<{ persisted: JobSnapshot; stateFile: string; legacyState: boolean }> = [];
    for (const name of files) {
      const stateFile = path.join(this.cacheDir, name);
      const legacyState = !name.endsWith(".state.json");
      let persisted: unknown;
      try { persisted = JSON.parse(readFileSync(stateFile, "utf8")); } catch { continue; }
      if (isJobSnapshot(persisted)) recovered.push({ persisted, stateFile, legacyState });
    }
    const running = recovered.filter(({ persisted }) => persisted.status === "running");
    const completed = recovered
      .filter(({ persisted }) => persisted.status !== "running")
      .sort((a, b) => (b.persisted.completedAt ?? b.persisted.startedAt).localeCompare(a.persisted.completedAt ?? a.persisted.startedAt))
      .slice(0, this.maxCompletedJobs);
    for (const { persisted, stateFile, legacyState } of [...running, ...completed]) {
      const notificationFile = path.join(this.cacheDir, `${persisted.jobId}.notification.lock`);
      const job: InternalJob = {
        ...persisted,
        reviewName: persisted.jobId,
        supervisorPid: legacyState ? undefined : persisted.supervisorPid,
        launcherPid: persisted.launcherPid ?? (legacyState ? persisted.pid : undefined),
        reservationFile: this.reservationPath(persisted.output),
        notificationFile,
        notificationSent: existsSync(notificationFile) || this.sessionHasDelivery(persisted),
        recovered: true,
      };
      this.jobs.set(job.jobId, job);
      if (job.status === "running") this.activeOutputs.set(job.output, job.jobId);
    }
  }

  private watch(job: InternalJob): void {
    if (!this.observing || job.poller || job.status !== "running") return;
    job.poller = setInterval(() => this.refresh(job, true), this.pollIntervalMs);
    job.poller.unref?.();
  }

  private refresh(job: InternalJob, notify: boolean): void {
    if (job.status !== "running") return;
    let persisted: unknown;
    try { persisted = JSON.parse(readFileSync(job.stateFile, "utf8")); } catch { return; }
    if (!isJobSnapshot(persisted) || persisted.jobId !== job.jobId) return;
    Object.assign(job, persisted);
    if (job.status === "running") {
      if (!supervisorIsHealthy(job)) this.reconcileInterrupted(job, notify);
      return;
    }
    this.finishObservedJob(job, notify);
  }

  private reconcileInterrupted(job: InternalJob, notify: boolean): void {
    if (job.status !== "running") return;
    const artifact = existsSync(job.output) ? safeRead(job.output) : "";
    const classified = artifact ? classifyArtifact(job.action, artifact) : undefined;
    if (job.launcherPid && processExists(job.launcherPid)) {
      killPidTree(job.launcherPid, "SIGTERM");
      this.cleanupTmuxImpl(job.reviewName, job.launcherPid);
      killPidTree(job.launcherPid, "SIGKILL");
    }
    if (classified?.ok) {
      job.status = "succeeded";
      job.classification = classified.classification;
      job.summary = bounded(`Recovered a valid completed launcher artifact after supervisor interruption; output=${job.output}\nstdout=${job.stdoutLog}\nstderr=${job.stderrLog}`);
    } else if (classified && classified.classification !== "CLAUDE_REVIEW_ARTIFACT_INVALID") {
      job.status = "failed";
      job.classification = classified.classification;
      job.summary = bounded(`${artifact}\nstdout=${job.stdoutLog}\nstderr=${job.stderrLog}`);
    } else {
      job.status = "interrupted";
      job.classification = "CLAUDE_REVIEW_INTERRUPTED";
      job.summary = bounded(`Detached supervisor disappeared before a terminal state was persisted; orphan cleanup attempted; output=${job.output}\nstdout=${job.stdoutLog}\nstderr=${job.stderrLog}`);
    }
    job.completedAt = this.now().toISOString();
    job.exitCode = null;
    job.signal = null;
    atomicWriteJson(job.stateFile, snapshot(job));
    this.releaseReservation(job.reservationFile, job.jobId);
    this.finishObservedJob(job, notify);
  }

  private finishObservedJob(job: InternalJob, notify: boolean): void {
    if (job.poller) clearInterval(job.poller);
    job.poller = undefined;
    if (this.activeOutputs.get(job.output) === job.jobId) this.activeOutputs.delete(job.output);
    const sessionMatches = !this.activeSessionId || job.originSessionId === this.activeSessionId;
    if (notify && sessionMatches && !job.notificationSent && !this.shuttingDown) {
      const view = snapshot(job);
      if (this.deferNotification?.(view)) {
        this.invokeCompletion(view);
      } else if (this.claimNotification(job)) {
        job.notificationSent = true;
        this.invokeCompletion(view);
      }
    }
    this.pruneCompletedHistory();
  }

  confirmDelivery(jobId: string): boolean {
    const job = this.jobs.get(jobId);
    if (!job || job.status === "running") return false;
    if (job.notificationSent) return true;
    if (!this.claimNotification(job)) return false;
    job.notificationSent = true;
    return true;
  }

  deliverDetached(jobId: string): boolean {
    const job = this.jobs.get(jobId);
    if (!job || job.status === "running" || job.notificationSent || this.shuttingDown) return false;
    const sessionMatches = !this.activeSessionId || job.originSessionId === this.activeSessionId;
    if (!sessionMatches || !this.claimNotification(job)) return false;
    job.notificationSent = true;
    this.invokeCompletion(snapshot(job));
    return true;
  }

  private invokeCompletion(job: JobSnapshot): void {
    try {
      void Promise.resolve(this.onComplete?.(job)).catch(() => {});
    } catch { /* state remains discoverable when the originating Pi runtime is unavailable */ }
  }

  private sessionHasDelivery(job: JobSnapshot): boolean {
    const sessionFile = this.resolveOriginSessionFile(job);
    if (!sessionFile) return false;
    let delivered = this.sessionDeliveryJobIds.get(sessionFile);
    if (!delivered) {
      delivered = new Set<string>();
      for (const line of safeRead(sessionFile).split("\n")) {
        if (!line.includes("claude-review-completion") && !line.includes('\"toolName\":\"claude_review\"')) continue;
        try {
          const row = JSON.parse(line);
          const message = row?.type === "custom_message" ? row : row?.message;
          const customJobId = (row?.type === "custom_message" || message?.role === "custom") && message?.customType === "claude-review-completion"
            ? message?.details?.jobId
            : undefined;
          const toolJobId = message?.role === "toolResult" && message?.toolName === "claude_review" && message?.details?.phase === "completed"
            ? message?.details?.job?.jobId
            : undefined;
          if (typeof customJobId === "string") delivered.add(customJobId);
          if (typeof toolJobId === "string") delivered.add(toolJobId);
        } catch { /* ignore partial or unrelated session rows */ }
      }
      this.sessionDeliveryJobIds.set(sessionFile, delivered);
    }
    return delivered.has(job.jobId);
  }

  private resolveOriginSessionFile(job: JobSnapshot): string | undefined {
    if (job.originSessionFile && existsSync(job.originSessionFile)) return job.originSessionFile;
    if (!job.originSessionId) return undefined;
    const suffix = `_${job.originSessionId}.jsonl`;
    const visit = (dir: string): string | undefined => {
      let names: string[];
      try { names = readdirSync(dir); } catch { return undefined; }
      for (const name of names) {
        const candidate = path.join(dir, name);
        if (name.endsWith(suffix)) return candidate;
        let info;
        try { info = statSync(candidate); } catch { continue; }
        if (info.isDirectory()) {
          const found = visit(candidate);
          if (found) return found;
        }
      }
      return undefined;
    };
    return visit(this.sessionsDir);
  }

  private claimNotification(job: InternalJob): boolean {
    let fd: number | undefined;
    try {
      fd = openSync(job.notificationFile, "wx", 0o600);
      writeFileSync(fd, `${JSON.stringify({ jobId: job.jobId, claimedAt: this.now().toISOString(), claimantPid: process.pid })}\n`, "utf8");
      closeSync(fd);
      return true;
    } catch (error) {
      if (fd !== undefined) try { closeSync(fd); } catch {}
      if ((error as NodeJS.ErrnoException).code === "EEXIST") return false;
      return false;
    }
  }

  private reservationPath(output: string): string {
    const digest = createHash("sha256").update(output).digest("hex");
    return path.join(this.cacheDir, `output-${digest}.lock`);
  }

  private reserveOutput(output: string, jobId: string, stateFile: string, reservationFile: string): void {
    if (this.activeOutputs.has(output)) throw new Error(`output already has an active Claude review job: ${output}`);
    for (let attempt = 0; attempt < 2; attempt += 1) {
      let fd: number | undefined;
      try {
        fd = openSync(reservationFile, "wx", 0o600);
        writeFileSync(fd, `${JSON.stringify({ jobId, output, stateFile, ownerPid: process.pid, createdAt: Date.now() })}\n`, "utf8");
        closeSync(fd);
        return;
      } catch (error) {
        if (fd !== undefined) try { closeSync(fd); } catch {}
        if ((error as NodeJS.ErrnoException).code !== "EEXIST") throw error;
        let existing: { jobId?: string; stateFile?: string; ownerPid?: number; createdAt?: number } = {};
        try { existing = JSON.parse(readFileSync(reservationFile, "utf8")); } catch {}
        let existingState: JobSnapshot | undefined;
        try {
          const parsed = JSON.parse(readFileSync(existing.stateFile ?? "", "utf8"));
          if (isJobSnapshot(parsed)) existingState = parsed;
        } catch {}
        const reservationOwnerIsStarting = processExists(existing.ownerPid)
          && typeof existing.createdAt === "number"
          && Date.now() - existing.createdAt < 30_000
          && (!existingState || (existingState.status === "running" && !existingState.heartbeatAt));
        if (reservationOwnerIsStarting || (existingState?.status === "running" && supervisorIsHealthy(existingState))) {
          throw new Error(`output already has an active Claude review job: ${output}`);
        }
        try { unlinkSync(reservationFile); } catch {}
      }
    }
    throw new Error(`could not reserve Claude review output: ${output}`);
  }

  private releaseReservation(reservationFile: string, jobId: string): void {
    try {
      const reservation = JSON.parse(readFileSync(reservationFile, "utf8"));
      if (reservation.jobId === jobId) unlinkSync(reservationFile);
    } catch { /* already released or replaced */ }
  }

  private pruneCompletedHistory(): void {
    const completed = [...this.jobs.values()]
      .filter((candidate) => candidate.status !== "running")
      .sort((a, b) => (a.completedAt ?? a.startedAt).localeCompare(b.completedAt ?? b.startedAt));
    for (const stale of completed.slice(0, Math.max(0, completed.length - this.maxCompletedJobs))) {
      if (stale.poller) clearInterval(stale.poller);
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
  return spawnRequest?.agent === "claude" && typeof spawnRequest.prompt === "string" && REVIEW_INTENT_RE.test(spawnRequest.prompt);
}

export function defaultLauncherPath(): string {
  return path.join(os.homedir(), ".agents", "skills", "claude-code-review", "scripts", "claude_interactive_review.py");
}

export function defaultCacheDir(): string {
  return path.join(os.homedir(), ".pi", "agent", "cache", "claude-review");
}
