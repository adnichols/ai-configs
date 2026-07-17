import { spawn, type ChildProcess } from "node:child_process";
import { createHash, randomUUID } from "node:crypto";
import { chmodSync, closeSync, constants, copyFileSync, existsSync, mkdirSync, openSync, readFileSync, readdirSync, realpathSync, renameSync, statSync, unlinkSync, writeFileSync } from "node:fs";
import { realpath, stat } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

export const REVIEW_TIMEOUT_SECONDS = 3600;
export const SMOKE_TIMEOUT_SECONDS = 180;
export const REVIEW_WATCHDOG_MS = 4_200_000;
export const SMOKE_WATCHDOG_MS = 300_000;
const MAX_SUMMARY = 5_000;
const TERMINAL = new Set(["succeeded", "failed", "timed_out", "cancelled", "interrupted"]);

export type ReviewType = "implementation-review" | "adversarial-implementation-review" | "plan-review";
export type VerdictProfile = "pre-pr-implementation" | "run-plan-pm" | "reviewed-html-plan" | "generic-implementation" | "generic-plan";
export type JobStatus = "starting" | "running" | "succeeded" | "failed" | "timed_out" | "cancelled" | "interrupted";
export type DeliveryState = "pending" | "delivering" | "delivered" | "ineligible";

const PROFILE_TOKENS: Record<VerdictProfile, Set<string>> = {
  "pre-pr-implementation": new Set(["FINDINGS_TO_RESOLVE", "CLEAN_FOR_PR", "BLOCKED_BY_QUESTION", "REVIEW_INCOMPLETE_RERUN_NEEDED"]),
  "generic-implementation": new Set(["FINDINGS_TO_RESOLVE", "CLEAN_FOR_PR", "BLOCKED_BY_QUESTION", "REVIEW_INCOMPLETE_RERUN_NEEDED"]),
  "run-plan-pm": new Set(["PASS_SCOPED", "PASS_WITH_DOCUMENTED_OUT_OF_SCOPE_FOLLOW_UPS", "FIX_IN_SCOPE_FINDINGS", "BLOCKED_BY_SCOPE_QUESTION", "REVIEW_INCOMPLETE_RERUN_NEEDED"]),
  "reviewed-html-plan": new Set(["PLAN_EXECUTION_READY", "PLAN_NEEDS_REVISION", "BLOCKED_BY_PRODUCT_QUESTION", "REVIEW_INCOMPLETE_RERUN_NEEDED"]),
  "generic-plan": new Set(["PLAN_EXECUTION_READY", "PLAN_NEEDS_REVISION", "BLOCKED_BY_QUESTION", "REVIEW_INCOMPLETE_RERUN_NEEDED"]),
};
const COMPATIBLE: Record<ReviewType, VerdictProfile[]> = {
  "implementation-review": ["pre-pr-implementation", "run-plan-pm", "generic-implementation"],
  "adversarial-implementation-review": ["pre-pr-implementation", "generic-implementation"],
  "plan-review": ["reviewed-html-plan", "generic-plan"],
};

export interface StartRequest { action: "start" | "smoke"; reviewType?: ReviewType; verdictProfile?: VerdictProfile; cwd: string; promptFile?: string; output: string }
export interface LaunchRequest extends StartRequest { stagingOutput: string; launcherStatus: string; processIdentityFile: string; jobNonce: string }
export interface JobSnapshot {
  jobId: string; jobNonce: string; action: "start" | "smoke"; reviewType?: ReviewType; verdictProfile?: VerdictProfile; status: JobStatus; classification?: string; verdict?: string;
  summary: string; cwd: string; promptFile?: string; output: string; stdoutLog: string; stderrLog: string; stateFile: string; reservationFile: string;
  stagingOutput: string; launcherStatus: string; processIdentityFile: string; startedAt: string; completedAt?: string; pid?: number; pgid?: number; processStartIdentity?: string; bootId?: string; ownerPid?: number; ownerStartIdentity?: string; ownerBootId?: string; exitCode?: number | null; signal?: NodeJS.Signals | null;
  deliveryId: string; deliveryState: DeliveryState; deliveryAttempts: number; cancellationReason?: "user" | "session_shutdown";
}
interface InternalJob extends JobSnapshot { child?: ChildProcess; watchdog?: ReturnType<typeof setTimeout>; finishing: boolean; finishPromise?: Promise<void> }
interface ProcessIdentity { pid: number; ppid: number; startTime: string; pgid: number; state: string }
interface CodexProcessEvidence { protocolVersion: 1; nonce: string; codexPid: number; codexPgid: number; processStartIdentity: string; bootId: string }
type GroupEvidence = Map<number, Map<number, string>>;
interface Options {
  launcherPath: string; cacheDir: string; onComplete?: (event: JobSnapshot) => void; reviewWatchdogMs?: number; smokeWatchdogMs?: number; killGraceMs?: number;
  writeState?: (file: string, value: JobSnapshot) => void; spawnImpl?: typeof spawn; now?: () => Date; makeId?: () => string; maxCompletedJobs?: number;
  deliveryEvidence?: (deliveryId: string) => boolean | Promise<boolean>; sessionsDir?: string;
}

export function validateVerdict(profile: VerdictProfile, text: string): { ok: boolean; verdict?: string } {
  const lines = text.replace(/\r\n?/g, "\n").split("\n"); let fenced = false; const candidates: Array<[number, string]> = [];
  lines.forEach((line, index) => { const logical = line.replace(/[\t ]+$/g, ""); if (/^\s*```/.test(logical)) { fenced = !fenced; return; } const match = !fenced && /^VERDICT: ([A-Z0-9_]+)$/.exec(logical); if (match) candidates.push([index, match[1]]); });
  const nonempty = lines.map((line, index) => [line.replace(/[\t ]+$/g, ""), index] as const).filter(([line]) => line.length);
  const candidate = candidates[0]; const ok = candidates.length === 1 && nonempty.length > 0 && candidate[0] === nonempty.at(-1)?.[1] && PROFILE_TOKENS[profile].has(candidate[1]);
  return ok ? { ok: true, verdict: candidate[1] } : { ok: false };
}

export function assertCompatible(reviewType: ReviewType, profile: VerdictProfile): void {
  if (!COMPATIBLE[reviewType]?.includes(profile)) throw new Error(`Incompatible reviewType/verdictProfile; valid pairs: ${Object.entries(COMPATIBLE).map(([type, profiles]) => `${type}=[${profiles.join(",")}]`).join("; ")}`);
}

export function buildLauncherArgs(request: LaunchRequest): string[] {
  const args = ["--mode", request.action === "smoke" ? "smoke" : request.reviewType!];
  if (request.action === "start") args.push("--verdict-profile", request.verdictProfile!, "--input", request.promptFile!);
  args.push("--cwd", request.cwd, "--output", request.stagingOutput, "--status-file", request.launcherStatus, "--process-identity-file", request.processIdentityFile, "--job-nonce", request.jobNonce, "--timeout-seconds", String(request.action === "smoke" ? SMOKE_TIMEOUT_SECONDS : REVIEW_TIMEOUT_SECONDS));
  return args;
}

export function redactSummary(text: string): string {
  const clean = text.replace(/\x1B(?:[@-_][0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1B\\))/g, "")
    .replace(/(authorization\s*:\s*bearer\s+)[^\s]+/gi, "$1[REDACTED]")
    .replace(/\b(api[_-]?key|token|access[_-]?token)\s*[=:]\s*[^\s]+/gi, "$1=[REDACTED]");
  return clean.length <= MAX_SUMMARY ? clean : `${clean.slice(0, MAX_SUMMARY)}\n[summary truncated; inspect evidence paths]`;
}

const CLEAN_VERDICTS = new Set(["CLEAN_FOR_PR", "PASS_SCOPED", "PASS_WITH_DOCUMENTED_OUT_OF_SCOPE_FOLLOW_UPS", "PLAN_EXECUTION_READY"]);
const FINDING_VERDICTS = new Set(["FINDINGS_TO_RESOLVE", "FIX_IN_SCOPE_FINDINGS", "PLAN_NEEDS_REVISION"]);
const BLOCKED_VERDICTS = new Set(["BLOCKED_BY_QUESTION", "BLOCKED_BY_SCOPE_QUESTION", "BLOCKED_BY_PRODUCT_QUESTION"]);
function unusableBudget(profile?: VerdictProfile): string {
  return profile && !profile.startsWith("generic-") ? "the workflow's single narrower unusable-output rerun allowance" : "the caller's documented infrastructure-rerun policy";
}
export function outcomeGuidance(job: JobSnapshot): string {
  const profile = job.verdictProfile ?? "smoke"; const evidence = `Evidence: output=${job.output}; stdout=${job.stdoutLog}; stderr=${job.stderrLog}; launcherStatus=${job.launcherStatus}; state=${job.stateFile}.`;
  if (job.verdict && CLEAN_VERDICTS.has(job.verdict)) return `Profile ${profile}: clean for this review leg. Retry budget: none. Next action: Read and triage the artifact, record its verdict, then continue to the next required workflow gate. ${evidence}`;
  if (job.verdict && FINDING_VERDICTS.has(job.verdict)) return `Profile ${profile}: findings/revision required. Infrastructure retry budget: none; use only the workflow's existing post-fix targeted-rereview budget after fixing or triaging findings. Next action: read ${job.output}, resolve or disposition its findings, then return to the workflow's fix-and-rereview step. ${evidence}`;
  if (job.verdict && BLOCKED_VERDICTS.has(job.verdict)) { const decision = job.verdict === "BLOCKED_BY_SCOPE_QUESTION" ? "scope decision" : job.verdict === "BLOCKED_BY_PRODUCT_QUESTION" ? "product decision" : "required decision"; return `Profile ${profile}: blocked by question. Retry budget: none until the ${decision} is resolved; this consumes no infrastructure-rerun allowance. Next action: surface the exact question from ${job.output}, obtain the ${decision}, then restart the same required gate only if still required. ${evidence}`; }
  if (job.verdict === "REVIEW_INCOMPLETE_RERUN_NEEDED") {
    const budget = profile === "pre-pr-implementation" || profile === "run-plan-pm" ? "one narrowed incomplete-coverage follow-up for this reviewer/cycle" : profile === "reviewed-html-plan" ? "follow each recommended required slice until complete or the reviewed-plan convergence/product/tooling stop condition fires" : "caller-owned; apply the caller's documented coverage-continuation policy";
    return `Profile ${profile}: review coverage is incomplete. Coverage-continuation budget: ${budget}; this is not post-fix rereview. Next action: read ${job.output}, report completed and remaining checks, and run exactly its recommended narrower slice only when that budget permits. ${evidence}`;
  }
  const c = job.classification ?? "CODEX_REVIEW_UNKNOWN";
  if (["CODEX_REVIEW_ARTIFACT_MISSING", "CODEX_REVIEW_ARTIFACT_INVALID", "CODEX_REVIEW_ARTIFACT_POST_PUBLISH_INVALID"].includes(c)) return `Profile ${profile}: reviewer artifact is unusable (${c}). Retry budget: ${unusableBudget(job.verdictProfile)}. Next action: inspect the staging/status/log evidence, repair or narrow the prompt, and use that allowance only if available; never infer a verdict from progress text. ${evidence}`;
  if (["CODEX_REVIEW_OUTPUT_EXISTS", "CODEX_REVIEW_OUTPUT_RACE"].includes(c)) return `Profile ${profile}: output path safety blocked publication (${c}). Retry budget: no automatic retry against this path; path correction consumes no semantic review cycle. Next action: preserve the existing output and restart with a fresh absent output path. ${evidence}`;
  if (c === "CODEX_REVIEW_LAUNCHER_PROTOCOL_INVALID") return `Profile ${profile}: launcher protocol is missing, malformed, or contradictory. Retry budget: ${unusableBudget(job.verdictProfile)}, only after protocol diagnosis/repair. Next action: inspect launcherStatus/stdout/stderr and repair the exact protocol defect before any narrower rerun. ${evidence}`;
  if (c === "CODEX_AUTH_UNAVAILABLE") return `Profile ${profile}: evidence-backed authentication is unavailable. Retry budget: no automatic rerun and no semantic cycle consumed by prerequisite repair. Next action: repair credentials, run codex_review smoke, then resume the same required review. ${evidence}`;
  if (/RATE|PROVIDER|SESSION_UNAVAILABLE/.test(c)) return `Profile ${profile}: evidence-backed provider/session availability blocker (${c}). Retry budget: no automatic fallback, model substitution, or post-fix budget consumption. Next action: wait for the evidence-backed recovery/reset condition, then resume the same required gate. ${evidence}`;
  if (c === "CODEX_REVIEW_CODEX_EXIT_NONZERO" || c === "CODEX_REVIEW_CODEX_SIGNAL" || c === "CODEX_REVIEW_LAUNCH_FAILED") return `Profile ${profile}: generic Codex/launch failure (${c}); no unsupported provider cause is claimed. Retry budget: no automatic rerun; apply only the workflow's documented unusable-transport allowance. Next action: inspect stdout/stderr/status, repair the launch or transport fault, then rerun only if that allowance permits. ${evidence}`;
  if (job.status === "timed_out" || c === "CODEX_REVIEW_INNER_TIMEOUT" || c === "CODEX_REVIEW_OUTER_TIMEOUT") return `Profile ${profile}: timeout (${c}); the controller completed TERM-to-KILL cleanup of the managed process group. Retry budget: at most ${unusableBudget(job.verdictProfile)}, and using it consumes that allowance. Next action: inspect evidence and rerun once with the exact narrower prompt only if the allowance remains; otherwise stop. ${evidence}`;
  if (job.status === "cancelled") return `Profile ${profile}: cancelled by ${job.cancellationReason ?? "controller"}; no reviewer result. Retry budget: no automatic rerun and cancellation is neither findings nor clean. Next action: confirm the gate is still required, then restart that same gate in the active session; graceful session_shutdown remains notification-ineligible. ${evidence}`;
  if (c === "CODEX_REVIEW_STATE_PERSIST_FAILED") return `Profile ${profile}: terminal controller-state persistence failed; the original verdict is not authoritative. Retry budget: no automatic semantic retry. Next action: repair cache storage/permissions, inspect emergency evidence, and restart the required gate with a fresh path because restart recovery is not guaranteed. ${evidence}`;
  if (c === "CODEX_REVIEW_CLEANUP_FAILED") return `Profile ${profile}: identity-safe process cleanup could not be verified; descendants may still be alive and process identity evidence was retained. Retry budget: no reviewer rerun while cleanup is unresolved. Next action: inspect state/process identity evidence and perform identity-safe operator cleanup before restarting the gate. ${evidence}`;
  if (c === "CODEX_REVIEW_INTERRUPTED" || c === "CODEX_REVIEW_ORPHAN_IDENTITY_UNCERTAIN") return `Profile ${profile}: startup reconciliation interrupted a persisted job (${c}). Retry budget: no automatic rerun. Next action: inspect cleanup/identity evidence, confirm the required gate is still needed, then restart it with a fresh path. ${evidence}`;
  return `Profile ${profile}: terminal outcome ${c}. Retry budget: no automatic retry. Next action: inspect the bounded evidence paths and apply the coordinating workflow's documented policy. ${evidence}`;
}

function atomicWrite(file: string, value: unknown): void { const tmp = `${file}.${process.pid}.${randomUUID()}.tmp`; writeFileSync(tmp, `${JSON.stringify(value, null, 2)}\n`, { mode: 0o600 }); renameSync(tmp, file); }
function safeUnlink(file: string): void { try { unlinkSync(file); } catch { /* manager-owned path is absent or retained */ } }
function safeRead(file: string): string { try { return readFileSync(file, "utf8"); } catch { return ""; } }
function hash(text: string): string { return createHash("sha256").update(text).digest("hex"); }
function delay(ms: number): Promise<void> { return new Promise((resolve) => setTimeout(resolve, ms)); }
function processIdentity(pid: number): ProcessIdentity | undefined {
  try {
    const raw = readFileSync(`/proc/${pid}/stat`, "utf8"); const tail = raw.slice(raw.lastIndexOf(")") + 2).split(" ");
    return { pid, ppid: Number(tail[1]), pgid: Number(tail[2]), startTime: tail[19], state: tail[0] };
  } catch { return undefined; }
}
function currentBootId(): string | undefined { try { return readFileSync("/proc/sys/kernel/random/boot_id", "utf8").trim(); } catch { return undefined; } }
function readCodexEvidence(job: JobSnapshot): CodexProcessEvidence | undefined {
  try {
    const value = JSON.parse(readFileSync(job.processIdentityFile, "utf8"));
    if (value?.protocolVersion !== 1 || value.nonce !== job.jobNonce || value.bootId !== currentBootId()
      || !Number.isInteger(value.codexPid) || value.codexPid <= 0 || !Number.isInteger(value.codexPgid) || value.codexPgid <= 0
      || typeof value.processStartIdentity !== "string" || !value.processStartIdentity) return undefined;
    return value;
  } catch { return undefined; }
}
function groupMembers(pgid: number): ProcessIdentity[] {
  const members: ProcessIdentity[] = [];
  let names: string[]; try { names = readdirSync("/proc"); } catch { return members; }
  for (const name of names) { if (!/^\d+$/.test(name)) continue; const identity = processIdentity(Number(name)); if (identity?.pgid === pgid) members.push(identity); }
  return members;
}
function signalGroup(pgid: number, signal: NodeJS.Signals): boolean { try { process.kill(-pgid, signal); return true; } catch (error: any) { return error?.code === "ESRCH"; } }
function groupAlive(pgid: number): boolean { try { process.kill(-pgid, 0); return true; } catch (error: any) { return error?.code !== "ESRCH"; } }
function addGroupEvidence(groups: GroupEvidence, identity: ProcessIdentity): void {
  let members = groups.get(identity.pgid); if (!members) { members = new Map(); groups.set(identity.pgid, members); }
  members.set(identity.pid, identity.startTime);
}
function groupEvidenceMatches(pgid: number, members: Map<number, string>): boolean {
  return [...members].some(([pid, startTime]) => { const identity = processIdentity(pid); return identity?.state !== "Z" && identity?.pgid === pgid && identity.startTime === startTime; });
}
function discoverDescendantGroups(root: ProcessIdentity): { descendants: GroupEvidence; launcher: GroupEvidence } | undefined {
  const currentRoot = processIdentity(root.pid);
  if (!currentRoot || currentRoot.startTime !== root.startTime || currentRoot.pgid !== root.pgid) return undefined;
  const processes = new Map<number, ProcessIdentity>();
  let names: string[]; try { names = readdirSync("/proc"); } catch { return undefined; }
  for (const name of names) { if (!/^\d+$/.test(name)) continue; const identity = processIdentity(Number(name)); if (identity) processes.set(identity.pid, identity); }
  const descendantPids = new Set([root.pid]); let changed = true;
  while (changed) {
    changed = false;
    for (const identity of processes.values()) if (!descendantPids.has(identity.pid) && descendantPids.has(identity.ppid)) { descendantPids.add(identity.pid); changed = true; }
  }
  const descendantPgids = new Set<number>();
  for (const pid of descendantPids) { const identity = processes.get(pid); if (identity && identity.pgid !== root.pgid) descendantPgids.add(identity.pgid); }
  const descendants: GroupEvidence = new Map(); const launcher: GroupEvidence = new Map();
  for (const identity of processes.values()) {
    if (descendantPgids.has(identity.pgid)) addGroupEvidence(descendants, identity);
    else if (identity.pgid === root.pgid) addGroupEvidence(launcher, identity);
  }
  return { descendants, launcher };
}
function reservationMatches(job: JobSnapshot): boolean { return safeRead(job.reservationFile) === `${job.jobId}\n${job.jobNonce}\n${job.output}\n`; }
function stateView(job: InternalJob): JobSnapshot { const { child: _child, watchdog: _watchdog, finishing: _finishing, finishPromise: _finishPromise, ...view } = job; return view; }

async function existingDir(value: string): Promise<string> { const resolved = path.resolve(value); if (!(await stat(resolved)).isDirectory()) throw new Error(`cwd is not a directory: ${resolved}`); return realpath(resolved); }
async function existingFile(value: string): Promise<string> { const resolved = path.resolve(value); if (!(await stat(resolved)).isFile()) throw new Error(`promptFile is not a file: ${resolved}`); return realpath(resolved); }
function canonicalOutput(value: string): string { const absolute = path.resolve(value); mkdirSync(path.dirname(absolute), { recursive: true, mode: 0o700 }); let parent = path.dirname(absolute); try { parent = statSync(parent).isDirectory() ? realpathSync(parent) : parent; } catch { /* created above */ } return path.join(parent, path.basename(absolute)); }

function validLauncherProtocol(protocol: any, outerCode: number | null, outerSignal: NodeJS.Signals | null): boolean {
  if (!protocol || protocol.protocolVersion !== 1 || !["success", "failure"].includes(protocol.outcome) || typeof protocol.classification !== "string") return false;
  const common = (typeof protocol.cliVersion === "string" && protocol.cliVersion.length > 0)
    && (protocol.codexExitCode === null || Number.isInteger(protocol.codexExitCode))
    && (protocol.codexSignal === null || typeof protocol.codexSignal === "string" || Number.isInteger(protocol.codexSignal))
    && typeof protocol.timeout === "boolean" && typeof protocol.finalMessageValidation === "string"
    && (protocol.matchedSource === null || typeof protocol.matchedSource === "string");
  if (!common || outerSignal !== null) return false;
  if (protocol.outcome === "success") return outerCode === 0 && protocol.classification === "CODEX_REVIEW_SUCCEEDED" && protocol.codexExitCode === 0 && protocol.codexSignal === null && protocol.timeout === false && protocol.matchedSource === "final-message" && protocol.finalMessageValidation === "valid";
  if (outerCode === 0 || protocol.classification === "CODEX_REVIEW_SUCCEEDED") return false;
  const expected: Record<string, { source: string; validation: string; timeout: boolean; code: "zero" | "nonzero" | "any"; signal: boolean; outer: "codex" | number[] }> = {
    CODEX_REVIEW_INNER_TIMEOUT: { source: "inner-timeout", validation: "not-checked", timeout: true, code: "any", signal: true, outer: [124] },
    CODEX_REVIEW_LAUNCH_FAILED: { source: "exec", validation: "not-checked", timeout: false, code: "nonzero", signal: false, outer: "codex" },
    CODEX_REVIEW_CODEX_SIGNAL: { source: "signal", validation: "not-checked", timeout: false, code: "nonzero", signal: true, outer: "codex" },
    CODEX_REVIEW_CODEX_EXIT_NONZERO: { source: "generic", validation: "not-checked", timeout: false, code: "nonzero", signal: false, outer: "codex" },
    CODEX_REVIEW_ARTIFACT_MISSING: { source: "final-message", validation: "missing", timeout: false, code: "zero", signal: false, outer: [20] },
    CODEX_REVIEW_ARTIFACT_INVALID: { source: "final-message", validation: "invalid", timeout: false, code: "zero", signal: false, outer: [21] },
    CODEX_REVIEW_OUTPUT_COMMIT_FAILED: { source: "output-commit", validation: "valid", timeout: false, code: "zero", signal: false, outer: [23, 129, 130, 143] },
  };
  const rule = expected[protocol.classification]; if (!rule) return false;
  const codeOk = rule.code === "any" || (rule.code === "zero" ? protocol.codexExitCode === 0 : typeof protocol.codexExitCode === "number" && protocol.codexExitCode !== 0);
  const signalNumber = typeof protocol.codexSignal === "number" ? protocol.codexSignal : typeof protocol.codexSignal === "string"
    ? (/^\d+$/.test(protocol.codexSignal) ? Number(protocol.codexSignal) : ({ HUP: 1, SIGHUP: 1, INT: 2, SIGINT: 2, TERM: 15, SIGTERM: 15, KILL: 9, SIGKILL: 9 } as Record<string, number>)[protocol.codexSignal])
    : undefined;
  const signalAgrees = rule.signal
    ? Number.isInteger(signalNumber) && protocol.codexExitCode === 128 + signalNumber!
    : protocol.codexSignal === null;
  const outerAgrees = rule.outer === "codex" ? outerCode === protocol.codexExitCode : outerCode !== null && rule.outer.includes(outerCode);
  return protocol.matchedSource === rule.source && protocol.finalMessageValidation === rule.validation && protocol.timeout === rule.timeout && codeOk && signalAgrees && outerAgrees;
}

function sessionDeliveryIds(sessionsDir: string): Set<string> {
  const deliveries = new Set<string>();
  const visit = (dir: string): void => {
    let names: string[]; try { names = readdirSync(dir); } catch { return; }
    for (const name of names) {
      const file = path.join(dir, name); let info; try { info = statSync(file); } catch { continue; }
      if (info.isDirectory()) { visit(file); continue; }
      if (!name.endsWith(".jsonl")) continue;
      for (const line of safeRead(file).split("\n")) {
        if (!line.includes("codex-review-completion")) continue;
        try { const row = JSON.parse(line); const message = row?.type === "custom_message" ? row : row?.message; const details = message?.details; if ((row?.type === "custom_message" || message?.role === "custom") && message?.customType === "codex-review-completion") { if (typeof details?.deliveryId === "string") deliveries.add(details.deliveryId); if (typeof details?.jobId === "string") deliveries.add(`legacy:${details.jobId}`); } } catch { /* ignore partial/unrelated session rows */ }
      }
    }
  };
  visit(sessionsDir); return deliveries;
}

export class CodexReviewJobManager {
  private readonly options: Options; private readonly jobs = new Map<string, InternalJob>(); private activation?: Promise<void>; private shuttingDown = false; private readonly starts = new Set<Promise<unknown>>(); private startupDeliveryIds?: Set<string>;
  constructor(options: Options) { this.options = options; mkdirSync(options.cacheDir, { recursive: true, mode: 0o700 }); mkdirSync(this.jobsDir(), { recursive: true, mode: 0o700 }); mkdirSync(this.reservationsDir(), { recursive: true, mode: 0o700 }); }
  private jobsDir() { return path.join(this.options.cacheDir, "jobs"); } private reservationsDir() { return path.join(this.options.cacheDir, "reservations"); }
  private emergencyFile(job: JobSnapshot): string { return `${job.stateFile}.emergency`; }
  private write(job: InternalJob): void { (this.options.writeState ?? atomicWrite)(job.stateFile, stateView(job)); safeUnlink(this.emergencyFile(job)); }
  private writeEmergency(job: InternalJob): boolean { try { atomicWrite(this.emergencyFile(job), stateView(job)); return true; } catch { return false; } }
  private persistDelivery(job: InternalJob): boolean { try { this.write(job); return true; } catch { return this.writeEmergency(job); } }
  activate(): Promise<void> { if (!this.activation) this.activation = this.reconcile().then(() => this.prune()); return this.activation; }
  private readPersisted(file: string): JobSnapshot | undefined {
    let main: JobSnapshot | undefined; let emergency: JobSnapshot | undefined;
    try { main = JSON.parse(readFileSync(file, "utf8")); } catch { /* malformed main evidence */ }
    try { emergency = JSON.parse(readFileSync(`${file}.emergency`, "utf8")); } catch { /* no emergency evidence */ }
    return emergency ?? main;
  }
  private normalizePersisted(raw: JobSnapshot): InternalJob {
    return { ...raw, processIdentityFile: raw.processIdentityFile ?? `${raw.stateFile}.process-identity.json`, jobNonce: raw.jobNonce ?? "legacy", deliveryId: raw.deliveryId ?? `legacy:${raw.jobId}`, deliveryState: raw.deliveryState ?? (raw.cancellationReason === "session_shutdown" ? "ineligible" : TERMINAL.has(raw.status) ? "delivered" : "pending"), deliveryAttempts: raw.deliveryAttempts ?? 0, finishing: false };
  }
  private persistedOwnerIsActive(job: InternalJob): boolean {
    if (job.ownerPid && job.ownerStartIdentity) {
      if (job.ownerBootId && job.ownerBootId !== currentBootId()) return false;
      const owner = processIdentity(job.ownerPid); return owner?.state !== "Z" && owner?.startTime === job.ownerStartIdentity;
    }
    if (job.pid && job.processStartIdentity) {
      const launcher = processIdentity(job.pid); if (!launcher || launcher.state === "Z" || launcher.startTime !== job.processStartIdentity || launcher.ppid <= 1) return false;
      return processIdentity(launcher.ppid)?.state !== "Z";
    }
    return false;
  }
  private async reconcile(): Promise<void> {
    for (const name of readdirSync(this.jobsDir()).filter((entry) => entry.endsWith(".state.json"))) {
      const file = path.join(this.jobsDir(), name); const raw = this.readPersisted(file); if (!raw) continue; const job = this.normalizePersisted(raw);
      if ((raw.status === "starting" || raw.status === "running") && this.persistedOwnerIsActive(job)) continue;
      this.jobs.set(job.jobId, job);
      if (raw.status === "starting" || raw.status === "running") await this.reconcileInterrupted(job);
      else if (TERMINAL.has(raw.status)) await this.deliver(job);
    }
  }
  private async reconcileInterrupted(job: InternalJob): Promise<void> {
    let classification = "CODEX_REVIEW_INTERRUPTED"; let cleanupVerified = job.status !== "running";
    if (job.status === "running" && job.pid && job.pgid && job.processStartIdentity) {
      const identity = processIdentity(job.pid); const bootMatches = !job.bootId || job.bootId === currentBootId();
      if (!bootMatches || (identity && (identity.startTime !== job.processStartIdentity || identity.pgid !== job.pgid)) || !reservationMatches(job)) classification = "CODEX_REVIEW_ORPHAN_IDENTITY_UNCERTAIN";
      else {
        cleanupVerified = await this.terminateVerified(job, false); if (!cleanupVerified) classification = "CODEX_REVIEW_ORPHAN_IDENTITY_UNCERTAIN";
      }
    } else if (job.status === "running") classification = "CODEX_REVIEW_ORPHAN_IDENTITY_UNCERTAIN";
    if (cleanupVerified) { if (reservationMatches(job)) safeUnlink(job.reservationFile); safeUnlink(job.stagingOutput); safeUnlink(job.launcherStatus); safeUnlink(job.processIdentityFile); }
    job.status = "interrupted"; job.classification = classification; job.completedAt = new Date().toISOString(); job.summary = `${classification}; persisted job was not resumed${cleanupVerified ? "." : "; cleanup was not verified and process evidence was retained."}`; job.deliveryState = "pending";
    try { this.write(job); } catch (error) { job.classification = "CODEX_REVIEW_STATE_PERSIST_FAILED"; job.summary = redactSummary(`${job.classification}: reconciliation persistence failed: ${String(error)}`); this.writeEmergency(job); }
    await this.deliver(job);
  }
  async start(request: StartRequest): Promise<JobSnapshot> {
    const operation = this.startInternal(request); this.starts.add(operation); try { return await operation; } finally { this.starts.delete(operation); }
  }
  private async startInternal(request: StartRequest): Promise<JobSnapshot> {
    await this.activate(); if (this.shuttingDown) throw new Error("Codex review manager is shutting down");
    const cwd = await existingDir(request.cwd); const promptFile = request.action === "start" ? await existingFile(request.promptFile ?? "") : undefined;
    if (this.shuttingDown) throw new Error("Codex review manager is shutting down");
    if (request.action === "smoke" && (request.reviewType || request.verdictProfile || request.promptFile)) throw new Error("smoke accepts no reviewType, verdictProfile, or promptFile");
    const reviewType = request.action === "start" ? (request.reviewType ?? "implementation-review") : undefined; const verdictProfile = request.action === "start" ? request.verdictProfile : undefined;
    if (request.action === "start") { if (!verdictProfile) throw new Error("verdictProfile is required"); assertCompatible(reviewType!, verdictProfile); }
    if (this.shuttingDown) throw new Error("Codex review manager is shutting down");
    const output = canonicalOutput(request.output); if (existsSync(output)) throw new Error(`CODEX_REVIEW_OUTPUT_EXISTS: caller-owned output already exists: ${output}`);
    const id = (this.options.makeId ?? randomUUID)(); const nonce = randomUUID(); const reservationFile = path.join(this.reservationsDir(), `${hash(output)}.reserve`);
    let reservationFd: number; try { reservationFd = openSync(reservationFile, constants.O_CREAT | constants.O_EXCL | constants.O_WRONLY, 0o600); writeFileSync(reservationFd, `${id}\n${nonce}\n${output}\n`); closeSync(reservationFd); } catch { throw new Error(`CODEX_REVIEW_OUTPUT_EXISTS: output is already reserved: ${output}`); }
    if (this.shuttingDown) { safeUnlink(reservationFile); throw new Error("Codex review manager is shutting down"); }
    const base = path.join(this.jobsDir(), id); const owner = processIdentity(process.pid); const job: InternalJob = { jobId: id, jobNonce: nonce, action: request.action, reviewType, verdictProfile, status: "starting", summary: "Starting Codex review.", cwd, promptFile, output, stdoutLog: `${base}.stdout.jsonl`, stderrLog: `${base}.stderr.log`, stateFile: `${base}.state.json`, reservationFile, stagingOutput: `${base}.staging`, launcherStatus: `${base}.launcher-status.json`, processIdentityFile: `${base}.process-identity.json`, startedAt: (this.options.now ?? (() => new Date()))().toISOString(), ownerPid: process.pid, ownerStartIdentity: owner?.startTime, ownerBootId: currentBootId(), deliveryId: `codex-review:${id}:${nonce}`, deliveryState: "pending", deliveryAttempts: 0, finishing: false };
    this.jobs.set(id, job);
    try { this.write(job); } catch (error) { safeUnlink(reservationFile); this.jobs.delete(id); throw new Error(`CODEX_REVIEW_INITIAL_STATE_PERSIST_FAILED: starting state: ${String(error)}`); }
    if (this.shuttingDown) { job.deliveryState = "ineligible"; job.cancellationReason = "session_shutdown"; job.status = "cancelled"; job.classification = "CODEX_REVIEW_CANCELLED"; job.completedAt = new Date().toISOString(); job.summary = "CODEX_REVIEW_CANCELLED reason=session_shutdown"; safeUnlink(reservationFile); this.write(job); throw new Error("Codex review manager is shutting down"); }
    const outFd = openSync(job.stdoutLog, "w", 0o600); const errFd = openSync(job.stderrLog, "w", 0o600); let child: ChildProcess;
    try { child = (this.options.spawnImpl ?? spawn)(this.options.launcherPath, buildLauncherArgs({ ...request, cwd, promptFile, reviewType, verdictProfile, stagingOutput: job.stagingOutput, launcherStatus: job.launcherStatus, processIdentityFile: job.processIdentityFile, jobNonce: job.jobNonce }), { cwd, detached: process.platform !== "win32", shell: false, stdio: ["ignore", outFd, errFd] }); }
    catch (error) { closeSync(outFd); closeSync(errFd); safeUnlink(reservationFile); this.jobs.delete(id); throw new Error(`CODEX_REVIEW_LAUNCH_FAILED: ${String(error)}`); }
    closeSync(outFd); closeSync(errFd); job.child = child; job.pid = child.pid; job.pgid = child.pid; job.bootId = currentBootId(); if (child.pid) job.processStartIdentity = processIdentity(child.pid)?.startTime; job.status = "running"; job.summary = "Codex review is running.";
    try { this.write(job); } catch (error) { job.deliveryState = "ineligible"; job.finishing = true; if (job.watchdog) clearTimeout(job.watchdog); const cleaned = await this.terminateVerified(job, true); safeUnlink(reservationFile); safeUnlink(job.stagingOutput); safeUnlink(job.launcherStatus); safeUnlink(job.processIdentityFile); this.jobs.delete(id); try { atomicWrite(`${base}.emergency.json`, { classification: "CODEX_REVIEW_INITIAL_STATE_PERSIST_FAILED", pid: job.pid, pgid: job.pgid, processStartIdentity: job.processStartIdentity, cleaned, error: String(error) }); } catch { /* best effort evidence */ } throw new Error(`CODEX_REVIEW_INITIAL_STATE_PERSIST_FAILED: running state: ${String(error)}; cleaned=${cleaned}`); }
    this.attach(job);
    if (this.shuttingDown) { await this.cancel(job.jobId, "session_shutdown"); throw new Error("Codex review manager is shutting down"); }
    return stateView(job);
  }
  private attach(job: InternalJob): void {
    const watchdogMs = job.action === "smoke" ? (this.options.smokeWatchdogMs ?? SMOKE_WATCHDOG_MS) : (this.options.reviewWatchdogMs ?? REVIEW_WATCHDOG_MS);
    job.watchdog = setTimeout(() => void this.timeout(job), watchdogMs);
    job.child!.once("error", () => void this.finish(job, null, null, "CODEX_REVIEW_LAUNCH_FAILED", false, true));
    job.child!.once("close", (code, signal) => void this.finish(job, code, signal as NodeJS.Signals | null, undefined, false, true));
  }
  private async timeout(job: InternalJob): Promise<void> { if (job.status !== "running") return; await this.finish(job, job.child?.exitCode ?? null, job.child?.signalCode as NodeJS.Signals | null, undefined, true, true); }
  private async finish(job: InternalJob, code: number | null, signal: NodeJS.Signals | null, forced?: string, outerTimeout = false, cleanupDescendants = false): Promise<void> {
    if (job.finishPromise) return job.finishPromise;
    if (TERMINAL.has(job.status)) return;
    job.finishPromise = this.finishOnce(job, code, signal, forced, outerTimeout, cleanupDescendants);
    return job.finishPromise;
  }
  private async finishOnce(job: InternalJob, code: number | null, signal: NodeJS.Signals | null, forced?: string, outerTimeout = false, cleanupDescendants = false): Promise<void> {
    job.finishing = true; if (job.watchdog) clearTimeout(job.watchdog);
    const cleanupSucceeded = !cleanupDescendants || await this.terminateVerified(job, false);
    if (!cleanupSucceeded) forced = "CODEX_REVIEW_CLEANUP_FAILED";
    job.exitCode = code; job.signal = signal; job.completedAt = new Date().toISOString();
    let classification = forced; let verdict: string | undefined; let success = false;
    if (outerTimeout && cleanupSucceeded) { job.status = "timed_out"; classification = "CODEX_REVIEW_OUTER_TIMEOUT"; }
    else if (!classification) {
      let protocol: any; try { protocol = JSON.parse(readFileSync(job.launcherStatus, "utf8")); } catch { classification = "CODEX_REVIEW_LAUNCHER_PROTOCOL_INVALID"; }
      if (!classification && !validLauncherProtocol(protocol, code, signal)) classification = "CODEX_REVIEW_LAUNCHER_PROTOCOL_INVALID";
      if (!classification && protocol.outcome === "failure") classification = protocol.classification;
      if (!classification) {
        try { if (existsSync(job.stagingOutput)) chmodSync(job.stagingOutput, 0o600); chmodSync(job.launcherStatus, 0o600); } catch { classification = "CODEX_REVIEW_ARTIFACT_INVALID"; }
        const text = safeRead(job.stagingOutput); if (!classification && !text) classification = "CODEX_REVIEW_ARTIFACT_MISSING";
        else if (!classification && job.action === "smoke") { if (text.trim() !== "CODEX_REVIEW_SMOKE_READY") classification = "CODEX_REVIEW_ARTIFACT_INVALID"; else success = true; }
        else if (!classification) { const checked = validateVerdict(job.verdictProfile!, text); if (!checked.ok) classification = "CODEX_REVIEW_ARTIFACT_INVALID"; else { verdict = checked.verdict; success = true; } }
        if (success) {
          try { copyFileSync(job.stagingOutput, job.output, constants.COPYFILE_EXCL); chmodSync(job.output, 0o600); const published = readFileSync(job.output, "utf8"); if (hash(published) !== hash(text) || (job.action === "smoke" ? published.trim() !== "CODEX_REVIEW_SMOKE_READY" : !validateVerdict(job.verdictProfile!, published).ok)) throw new Error("post-publish mismatch"); }
          catch (error: any) { success = false; classification = existsSync(job.output) && error?.code === "EEXIST" ? "CODEX_REVIEW_OUTPUT_RACE" : "CODEX_REVIEW_ARTIFACT_POST_PUBLISH_INVALID"; }
        }
      }
    }
    if (job.status !== "timed_out") job.status = success ? "succeeded" : "failed"; job.classification = success ? "CODEX_REVIEW_SUCCEEDED" : classification; job.verdict = verdict;
    job.summary = redactSummary(`${job.classification}${verdict ? ` verdict=${verdict}` : ""}. output=${job.output} stdout=${job.stdoutLog} stderr=${job.stderrLog} launcherStatus=${job.launcherStatus} state=${job.stateFile}`);
    if (cleanupSucceeded) { safeUnlink(job.reservationFile); safeUnlink(job.processIdentityFile); }
    if (success) safeUnlink(job.stagingOutput); job.deliveryState = "pending";
    try { this.write(job); } catch (error) { job.status = "failed"; job.classification = "CODEX_REVIEW_STATE_PERSIST_FAILED"; job.summary = redactSummary(`${job.classification}: ${String(error)}; emergency evidence attempted at ${this.emergencyFile(job)}`); this.writeEmergency(job); }
    await this.deliver(job); this.prune();
  }
  private async deliveryWasRecorded(deliveryId: string): Promise<boolean> { if (this.options.deliveryEvidence) return Boolean(await this.options.deliveryEvidence(deliveryId)); this.startupDeliveryIds ??= sessionDeliveryIds(this.options.sessionsDir ?? path.join(os.homedir(), ".pi", "agent", "sessions")); return this.startupDeliveryIds.has(deliveryId); }
  private async deliver(job: InternalJob): Promise<void> {
    if (job.deliveryState === "ineligible" || job.deliveryState === "delivered" || !TERMINAL.has(job.status)) return;
    if (job.deliveryState === "delivering") {
      if (await this.deliveryWasRecorded(job.deliveryId)) { job.deliveryState = "delivered"; this.persistDelivery(job); return; }
      job.deliveryState = "pending"; if (!this.persistDelivery(job)) return;
    }
    job.deliveryState = "delivering"; job.deliveryAttempts += 1; if (!this.persistDelivery(job)) return;
    try { this.options.onComplete?.(stateView(job)); }
    catch (error) { job.deliveryState = "pending"; job.summary = redactSummary(`${job.summary}; completion delivery failed: ${String(error)}`); this.persistDelivery(job); }
  }
  confirmDelivery(deliveryId: string): boolean { const job = [...this.jobs.values()].find((candidate) => candidate.deliveryId === deliveryId); if (!job || job.deliveryState !== "delivering") return false; job.deliveryState = "delivered"; return this.persistDelivery(job); }
  private async waitForChildClose(child: ChildProcess, timeoutMs: number): Promise<boolean> {
    if (child.exitCode !== null || child.signalCode !== null) return true;
    return new Promise((resolve) => { const timer = setTimeout(() => { child.off("close", closed); resolve(false); }, timeoutMs); const closed = () => { clearTimeout(timer); resolve(true); }; child.once("close", closed); });
  }
  private async terminateVerified(job: InternalJob, requireChildClose: boolean): Promise<boolean> {
    const grace = this.options.killGraceMs ?? 500;
    const waitGroupsGone = async (pgids: number[]): Promise<boolean> => { const settle = Math.max(grace, 250); for (let elapsed = 0; elapsed < settle && pgids.some(groupAlive); elapsed += 25) await delay(25); return pgids.every((pgid) => !groupAlive(pgid)); };
    const terminateEvidence = async (evidence: CodexProcessEvidence): Promise<boolean> => {
      const identity = processIdentity(evidence.codexPid);
      if (!identity) return groupMembers(evidence.codexPgid).filter((member) => member.state !== "Z").length === 0;
      if (identity.startTime !== evidence.processStartIdentity || identity.pgid !== evidence.codexPgid) return false;
      const members = new Map(groupMembers(evidence.codexPgid).map((member) => [member.pid, member.startTime]));
      if (members.get(evidence.codexPid) !== evidence.processStartIdentity) return false;
      if (!signalGroup(evidence.codexPgid, "SIGTERM")) return false;
      for (let elapsed = 0; elapsed < grace && groupEvidenceMatches(evidence.codexPgid, members); elapsed += 25) await delay(25);
      if (groupEvidenceMatches(evidence.codexPgid, members) && !signalGroup(evidence.codexPgid, "SIGKILL")) return false;
      for (let elapsed = 0; elapsed < grace && groupEvidenceMatches(evidence.codexPgid, members); elapsed += 25) await delay(25);
      return !groupEvidenceMatches(evidence.codexPgid, members);
    };
    const codexEvidence = readCodexEvidence(job);
    if (!job.pid || !job.pgid || !job.processStartIdentity || (!job.child && !reservationMatches(job))) return codexEvidence ? terminateEvidence(codexEvidence) : (!job.pid || !processIdentity(job.pid));
    if (job.bootId && job.bootId !== currentBootId()) return false;
    const identity = processIdentity(job.pid);
    if (!identity) {
      if (!codexEvidence) return existsSync(job.processIdentityFile) ? false : waitGroupsGone([job.pgid]);
      if (await terminateEvidence(codexEvidence)) return waitGroupsGone([job.pgid, codexEvidence.codexPgid]);
      return waitGroupsGone([job.pgid, codexEvidence.codexPgid]);
    }
    if (identity.startTime !== job.processStartIdentity || identity.pgid !== job.pgid) return false;
    const rootEvidence = new Map<number, string>([[identity.pid, identity.startTime]]);
    if (!groupEvidenceMatches(job.pgid, rootEvidence) || !signalGroup(job.pgid, "SIGSTOP")) return false;
    await delay(10);
    const discovered = discoverDescendantGroups(identity);
    if (!discovered) { if (groupEvidenceMatches(job.pgid, rootEvidence)) signalGroup(job.pgid, "SIGCONT"); return false; }
    const terminateGroups = async (groups: GroupEvidence, resume = false): Promise<boolean> => {
      for (const [pgid, members] of groups) {
        if (!groupEvidenceMatches(pgid, members)) continue;
        if (!signalGroup(pgid, "SIGTERM")) return false;
        if (resume) signalGroup(pgid, "SIGCONT");
      }
      for (let elapsed = 0; elapsed < grace && [...groups].some(([pgid, members]) => groupEvidenceMatches(pgid, members)); elapsed += 25) await delay(25);
      for (const [pgid, members] of groups) {
        if (!groupEvidenceMatches(pgid, members)) continue;
        if (!signalGroup(pgid, "SIGKILL")) return false;
      }
      for (let elapsed = 0; elapsed < grace && [...groups].some(([pgid, members]) => groupEvidenceMatches(pgid, members)); elapsed += 25) await delay(25);
      return [...groups].every(([pgid, members]) => !groupEvidenceMatches(pgid, members));
    };
    if (!await terminateGroups(discovered.descendants)) return false;
    if (codexEvidence && !await terminateEvidence(codexEvidence)) return false;
    if (!await terminateGroups(discovered.launcher, true)) return false;
    if (job.child && requireChildClose) await this.waitForChildClose(job.child, grace);
    return (!requireChildClose || !job.child || job.child.exitCode !== null || job.child.signalCode !== null);
  }
  status(id: string): JobSnapshot | undefined { const job = this.jobs.get(id); return job ? stateView(job) : undefined; }
  list(): JobSnapshot[] { return [...this.jobs.values()].map(stateView).sort((a, b) => b.startedAt.localeCompare(a.startedAt)); }
  async cancel(id: string, reason: "user" | "session_shutdown" = "user"): Promise<boolean> {
    const job = this.jobs.get(id); if (!job || !["starting", "running"].includes(job.status) || job.finishPromise) return false;
    job.finishPromise = this.cancelOnce(job, reason);
    await job.finishPromise; return true;
  }
  private async cancelOnce(job: InternalJob, reason: "user" | "session_shutdown"): Promise<void> {
    job.finishing = true; if (job.watchdog) clearTimeout(job.watchdog); job.cancellationReason = reason; job.deliveryState = reason === "session_shutdown" ? "ineligible" : "pending";
    const cleanupSucceeded = !job.child || await this.terminateVerified(job, true); job.status = cleanupSucceeded ? "cancelled" : "interrupted"; job.classification = cleanupSucceeded ? "CODEX_REVIEW_CANCELLED" : "CODEX_REVIEW_CLEANUP_FAILED"; job.completedAt = new Date().toISOString(); job.summary = cleanupSucceeded ? `CODEX_REVIEW_CANCELLED reason=${reason}` : `CODEX_REVIEW_CLEANUP_FAILED reason=${reason}; process identity evidence retained`;
    if (cleanupSucceeded) { safeUnlink(job.reservationFile); safeUnlink(job.stagingOutput); safeUnlink(job.launcherStatus); safeUnlink(job.processIdentityFile); }
    try { this.write(job); } catch (error) { job.classification = "CODEX_REVIEW_STATE_PERSIST_FAILED"; job.summary = redactSummary(`${job.classification}: cancellation persistence failed: ${String(error)}`); this.writeEmergency(job); }
    await this.deliver(job);
  }
  async shutdown(): Promise<void> {
    this.shuttingDown = true; await Promise.allSettled([...this.starts]);
    await Promise.all([...this.jobs.values()].filter((job) => ["starting", "running"].includes(job.status)).map((job) => this.cancel(job.jobId, "session_shutdown")));
  }
  private prune(): void { const cutoff = Date.now() - 7 * 86400_000; const terminal = this.list().filter((job) => TERMINAL.has(job.status) && (job.deliveryState === "delivered" || job.deliveryState === "ineligible")); const expired = terminal.filter((job) => Date.parse(job.completedAt ?? job.startedAt) < cutoff); const fresh = terminal.filter((job) => !expired.includes(job)); const remove = [...expired, ...fresh.slice(this.options.maxCompletedJobs ?? 100)]; for (const job of remove) { for (const file of [job.stateFile, `${job.stateFile}.emergency`, job.stdoutLog, job.stderrLog, job.launcherStatus, job.stagingOutput, job.processIdentityFile]) safeUnlink(file); this.jobs.delete(job.jobId); } }
}

export function defaultLauncherPath(): string { return path.join(os.homedir(), ".agents", "skills", "codex-review-partner", "scripts", "run-review.sh"); }
export function defaultCacheDir(): string { return path.join(os.homedir(), ".pi", "agent", "cache", "codex-review"); }

export function isForbiddenDirectReviewToolCall(toolName: string, input: unknown): { blocked: boolean; reason?: string } {
  if (!["bash", "process", "interactive_shell", "exec_command"].includes(toolName) || !input || typeof input !== "object") return { blocked: false };
  const command = String((input as any).command ?? (input as any).cmd ?? "");
  const wrapper = /run-review\.sh\b[\s\S]*--mode\s+(implementation-review|adversarial-implementation-review|plan-review)\b/.exec(command); const native = /\bcodex\s+exec\s+review\b/.test(command);
  if (!wrapper && !native) return { blocked: false };
  const mode = wrapper?.[1] ?? "implementation-review"; const profile = mode === "plan-review" ? "generic-plan" : "generic-implementation";
  return { blocked: true, reason: `Direct required Codex review launch is disabled. Use codex_review({action:"start",reviewType:"${mode}",verdictProfile:"${profile}",promptFile:"/path/prompt.md",output:"/path/review.md",cwd:"/path/repo"}). Maintained workflows must use their specific profile.` };
}
