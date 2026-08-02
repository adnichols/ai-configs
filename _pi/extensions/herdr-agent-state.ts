// installed by herdr
// managed by ai-configs; this copy supersedes herdr's bundled integration.
// herdr's `herdr integration install pi` overwrites this path with the stock
// herdr asset; re-run `install.sh --pi` to restore this improved version.
// add custom hooks/plugins beside this file instead of editing it.
// HERDR_INTEGRATION_ID=pi
// HERDR_INTEGRATION_VERSION=8
// Pi-vcc continuation entries also count as working until their durable terminal
// outcome is recorded, so compaction/recovery work never appears idle.
// Background processes count as working by default. Set
// HERDR_PI_BACKGROUND_PROCESS_MODE=none|finite|all to override, and use
// HERDR_PI_BACKGROUND_PROCESS_IGNORE for comma/newline-separated literal
// name or command fragments that should remain idle.
// @ts-nocheck

import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { createConnection } from "node:net";

const HERDR_ENV = process.env.HERDR_ENV;
const socketPath = process.env.HERDR_SOCKET_PATH;
const paneId = process.env.HERDR_PANE_ID;
const source = "herdr:pi";

// Pi RPC runs (including explore_subagent) inherit the parent process
// environment by default. They have an extension UI context but do not own the
// terminal pane, so they must never report or release that pane's lifecycle.
function isHeadlessChildRuntime(): boolean {
  if (process.env.PI_EXPLORE_SUBAGENT_CHILD === "1") {
    return true;
  }

  return process.argv.some(
    (arg, index, argv) => arg === "--mode=rpc" || (arg === "--mode" && argv[index + 1] === "rpc"),
  );
}

function enabled() {
  return HERDR_ENV === "1" && !!socketPath && !!paneId && !isHeadlessChildRuntime();
}

type OperatorWaitMarker = {
  paneId: string;
  message: string;
  setAt: string;
  kind: "approval" | "blocker" | "password" | "generic";
  notifyOnSet: boolean;
};

const operatorWaitKinds = new Set(["approval", "blocker", "password", "generic"]);

function operatorWaitMarker(): OperatorWaitMarker | undefined {
  if (!paneId) {
    return undefined;
  }
  const stateRoot = process.env.HERDR_OPERATOR_WAIT_DIR
    || join(process.env.XDG_STATE_HOME || join(homedir(), ".local", "state"), "herdr-operator-wait");
  const filename = `${createHash("sha256").update(paneId, "utf8").digest("hex")}.json`;
  try {
    const value = JSON.parse(readFileSync(join(stateRoot, filename), "utf8"));
    if (
      value?.paneId !== paneId
      || typeof value?.message !== "string"
      || typeof value?.setAt !== "string"
      || !value.setAt.endsWith("Z")
      || !Number.isFinite(Date.parse(value.setAt))
      || !operatorWaitKinds.has(value?.kind)
      || typeof value?.notifyOnSet !== "boolean"
    ) {
      return undefined;
    }
    return value as OperatorWaitMarker;
  } catch {
    // Workflow marker I/O is an attention aid and must never break Pi lifecycle reporting.
    return undefined;
  }
}

// sendRequest resolves with true on a successful round-trip and false on any
// error or timeout. Callers use the result to retry dropped reports so a lost
// final idle never leaves the pane stuck in working.
function sendRequest(request: unknown): Promise<boolean> {
  if (!enabled()) {
    return Promise.resolve(false);
  }

  return new Promise((resolve) => {
    let done = false;
    const finish = (ok: boolean) => {
      if (done) return;
      done = true;
      socket.destroy();
      resolve(ok);
    };

    const socket = createConnection(socketPath!);
    socket.on("error", () => finish(false));
    socket.on("connect", () => socket.write(`${JSON.stringify(request)}\n`));
    socket.on("data", () => finish(true));
    socket.on("end", () => finish(true));
    const timeout = setTimeout(() => finish(false), 500);
    timeout.unref?.();
  });
}

type AgentState = "working" | "blocked" | "idle";

type ProcessStatus = "running" | "terminating" | "terminate_timeout" | "exited" | "killed";

type TrackedProcess = {
  id: string;
  name: string;
  command: string;
  pid?: number;
  status?: ProcessStatus;
  alertOnSuccess?: boolean;
  alertOnFailure?: boolean;
};

const vccContinuationEntryTypes = new Set([
  "pi-vcc-continuation-request",
  "pi-vcc-continuation-snapshot",
  "pi-vcc-continuation-outcome",
]);
const vccTerminalStates = new Set(["settled", "superseded", "failed_loudly"]);

function vccContinuationSnapshot(entry: any): { transactionId: string; state: string } | undefined {
  if (entry?.type !== "custom" || !vccContinuationEntryTypes.has(entry?.customType)) {
    return undefined;
  }

  const data = entry?.data;
  const snapshot = data?.snapshot;
  if (
    data?.protocol !== "pi-vcc-continuation" ||
    !Number.isInteger(data?.version) ||
    snapshot?.protocol !== "pi-vcc-continuation" ||
    !Number.isInteger(snapshot?.version) ||
    typeof snapshot?.transactionId !== "string" ||
    snapshot.transactionId.length === 0 ||
    typeof snapshot?.state !== "string"
  ) {
    return undefined;
  }

  return { transactionId: snapshot.transactionId, state: snapshot.state };
}

const liveProcessStatuses = new Set<ProcessStatus>(["running", "terminating", "terminate_timeout"]);

type QueuedState = {
  state: AgentState;
  message?: string;
  seq: number;
  generation: number;
};

const idleDebounceMs = parseDurationEnv("HERDR_PI_IDLE_DEBOUNCE_MS", 250);
const retryGraceMs = parseDurationEnv("HERDR_PI_RETRY_GRACE_MS", 2500);
const reconcileIntervalMs = parseDurationEnv("HERDR_PI_RECONCILE_MS", 5000);
const heartbeatIntervalMs = parseDurationEnv("HERDR_PI_HEARTBEAT_MS", 15000);
const maxSendRetries = parseDurationEnv("HERDR_PI_MAX_SEND_RETRIES", 3);
const sendRetryDelayMs = parseDurationEnv("HERDR_PI_SEND_RETRY_DELAY_MS", 400);
const backgroundProcessMode = (() => {
  const explicit = process.env.HERDR_PI_BACKGROUND_PROCESS_MODE;
  if (explicit === "none" || explicit === "finite" || explicit === "all") {
    return explicit;
  }
  if (process.env.HERDR_PI_COUNT_BACKGROUND_PROCESSES === "0") {
    return "none";
  }
  if (process.env.HERDR_PI_COUNT_BACKGROUND_PROCESSES === "1") {
    return "all";
  }
  return "all";
})();
const backgroundProcessIgnoreTerms = parseListEnv("HERDR_PI_BACKGROUND_PROCESS_IGNORE");
const retryableErrorPattern =
  /overloaded|provider.?returned.?error|rate.?limit|too many requests|429|500|502|503|504|service.?unavailable|server.?error|internal.?error|network.?error|connection.?error|connection.?refused|connection.?lost|websocket.?closed|websocket.?error|other side closed|fetch failed|upstream.?connect|reset before headers|socket hang up|ended without|http2 request did not get a response|timed? out|timeout|terminated|retry delay/i;
let reportSeq = Date.now() * 1000;
let currentAgentSessionId: string | undefined;
let currentAgentSessionPath: string | undefined;

function nextReportSeq(): number {
  reportSeq += 1;
  return reportSeq;
}

function parseDurationEnv(name: string, fallback: number): number {
  const raw = process.env[name];
  if (!raw) {
    return fallback;
  }
  const parsed = Number.parseInt(raw, 10);
  if (!Number.isFinite(parsed) || parsed < 0) {
    return fallback;
  }
  return parsed;
}

function parseListEnv(name: string): string[] {
  return String(process.env[name] ?? "")
    .split(/[\n,]/)
    .map((value) => value.trim().toLowerCase())
    .filter((value) => value.length > 0);
}

function updateSessionRef(ctx: any): void {
  try {
    const file = ctx?.sessionManager?.getSessionFile?.();
    currentAgentSessionPath =
      typeof file === "string" && file.startsWith("/") ? file : undefined;
  } catch {
    currentAgentSessionPath = undefined;
  }

  try {
    const id = ctx?.sessionManager?.getSessionId?.();
    currentAgentSessionId = typeof id === "string" && id.length > 0 ? id : undefined;
  } catch {
    currentAgentSessionId = undefined;
  }
}

function withSessionRef(params: Record<string, unknown>): Record<string, unknown> {
  if (currentAgentSessionPath) {
    return { ...params, agent_session_path: currentAgentSessionPath };
  }
  if (currentAgentSessionId) {
    return { ...params, agent_session_id: currentAgentSessionId };
  }
  return params;
}

function currentSessionRef(): Record<string, unknown> | undefined {
  if (currentAgentSessionPath) {
    return { agent_session_path: currentAgentSessionPath };
  }
  if (currentAgentSessionId) {
    return { agent_session_id: currentAgentSessionId };
  }
  return undefined;
}

function reportSession(): Promise<boolean> {
  const sessionRef = currentSessionRef();
  if (!sessionRef) {
    return Promise.resolve(false);
  }

  return sendRequest({
    id: `${source}:session:${Date.now()}:${Math.random().toString(36).slice(2)}`,
    method: "pane.report_agent_session",
    params: {
      pane_id: paneId,
      source,
      agent: "pi",
      seq: nextReportSeq(),
      ...sessionRef,
    },
  });
}

function sendState(state: AgentState, message?: string, seq = nextReportSeq()): Promise<boolean> {
  return sendRequest({
    id: `${source}:${Date.now()}:${Math.random().toString(36).slice(2)}`,
    method: "pane.report_agent",
    params: withSessionRef({
      pane_id: paneId,
      source,
      agent: "pi",
      state,
      message,
      seq,
    }),
  });
}

function releaseAgent(): Promise<boolean> {
  return sendRequest({
    id: `${source}:release:${Date.now()}:${Math.random().toString(36).slice(2)}`,
    method: "pane.release_agent",
    params: {
      pane_id: paneId,
      source,
      agent: "pi",
      seq: nextReportSeq(),
    },
  });
}

let sendInFlight = false;
let queuedState: QueuedState | undefined;
let lastPublishAt = 0;
let lastSuccessfulStateReportAt = 0;
let lastQueuedState: AgentState | undefined;
let lastQueuedMessage: string | undefined;
let stateReportsEnabled = true;
let stateReportGeneration = 0;

function queueState(state: AgentState, message?: string): void {
  if (!stateReportsEnabled) {
    return;
  }
  lastPublishAt = Date.now();
  lastQueuedState = state;
  lastQueuedMessage = message;
  queuedState = { state, message, seq: nextReportSeq(), generation: stateReportGeneration };
  if (!sendInFlight) {
    void drainStateQueue();
  }
}

async function drainStateQueue(): Promise<void> {
  if (sendInFlight) {
    return;
  }

  sendInFlight = true;
  try {
    let attempts = 0;
    while (queuedState) {
      const next = queuedState;
      queuedState = undefined;
      const ok = await sendState(next.state, next.message, next.seq);
      if (ok) {
        lastSuccessfulStateReportAt = Date.now();
      }

      if (!stateReportsEnabled || next.generation !== stateReportGeneration) {
        break;
      }

      if (!ok && queuedState === undefined) {
        // The report was dropped (socket error/timeout) and no newer state
        // has superseded it. Retry the same state a few times so a lost final
        // idle does not strand the pane in working. If a newer state was
        // queued while we were sending, drop the retry and let it win.
        attempts += 1;
        if (attempts < maxSendRetries) {
          queuedState = next;
          await sleepUnref(sendRetryDelayMs);
        }
      } else {
        attempts = 0;
      }
    }
  } finally {
    sendInFlight = false;
    if (queuedState && stateReportsEnabled && queuedState.generation === stateReportGeneration) {
      void drainStateQueue();
    }
  }
}

async function waitForStateQueueIdle(): Promise<void> {
  while (sendInFlight) {
    await sleepUnref(25);
  }
}

function sleepUnref(ms: number): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, ms);
    timer.unref?.();
  });
}

function lastAssistantMessage(messages: unknown[]): any | undefined {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const message = messages[i] as any;
    if (message?.role === "assistant") {
      return message;
    }
  }
  return undefined;
}

function processToolDetails(event: any): any | undefined {
  return event?.details ?? event?.result?.details;
}

function isProcessLive(processInfo: TrackedProcess): boolean {
  if (processInfo.status && !liveProcessStatuses.has(processInfo.status)) {
    return false;
  }

  const pid = processInfo.pid;
  if (!Number.isFinite(pid) || !pid || pid <= 0) {
    return liveProcessStatuses.has(processInfo.status as ProcessStatus);
  }

  try {
    process.kill(pid, 0);
    return true;
  } catch (error) {
    const code = (error as NodeJS.ErrnoException)?.code;
    return code === "EPERM";
  }
}

function hasCommandFlag(command: string, flag: string): boolean {
  const escaped = flag.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(^|\\s)${escaped}(\\s|$)`).test(command);
}

function normalizedCommand(command: unknown): string {
  return typeof command === "string" ? command.trim().replace(/\s+/g, " ") : "";
}

function isPassivePlanListener(processInfo: TrackedProcess): boolean {
  const command = normalizedCommand(processInfo.command);
  return /^plan-review\s+agent\s+next\b/.test(command)
    && hasCommandFlag(command, "--wait")
    && hasCommandFlag(command, "--json")
    && !hasCommandFlag(command, "--no-wait");
}

function isPassivePrListener(processInfo: TrackedProcess): boolean {
  const name = String(processInfo.name ?? "").toLowerCase();
  const command = normalizedCommand(processInfo.command);
  return /^pr-\d+-monitor$/.test(name)
    || name.includes("pr-monitor")
    || /(^|\s)(bash\s+)?\/tmp\/monitor-pr-\d+\.sh(\s|$)/.test(command);
}

function isPassivePlanServer(processInfo: TrackedProcess): boolean {
  const name = String(processInfo.name ?? "").toLowerCase();
  const command = normalizedCommand(processInfo.command);
  return name.includes("plan-server")
    || /(^|\s)npm\s+run\s+plans:serve\b/.test(command)
    || /(^|\s)(pnpm|yarn|bun)\s+(run\s+)?plans:serve\b/.test(command)
    || /(^|\s)plan-review\s+serve\b/.test(command)
    || /scripts\/plans\/serve-html-plans\.mjs\b/.test(command);
}

function isPassiveDoctListener(processInfo: TrackedProcess): boolean {
  const command = normalizedCommand(processInfo.command).toLowerCase();
  return /(^|\s)doct-agent\s+plans\s+listen\b/.test(command)
    || (/(^|\s)doct-agent\s+plans\s+agent\s+next\b/.test(command)
      && hasCommandFlag(command, "--wait")
      && !hasCommandFlag(command, "--no-wait"));
}

function isConfiguredIgnoredProcess(processInfo: TrackedProcess): boolean {
  if (backgroundProcessIgnoreTerms.length === 0) {
    return false;
  }
  const name = String(processInfo.name ?? "").toLowerCase();
  const command = normalizedCommand(processInfo.command).toLowerCase();
  const searchable = `${name}\n${command}`;
  return backgroundProcessIgnoreTerms.some((term) => searchable.includes(term));
}

function isPassiveListenerProcess(processInfo: TrackedProcess): boolean {
  return isPassivePlanListener(processInfo)
    || isPassivePrListener(processInfo)
    || isPassiveDoctListener(processInfo);
}

function isLongLivedServiceProcess(processInfo: TrackedProcess): boolean {
  const name = String(processInfo.name ?? "").toLowerCase();
  const command = normalizedCommand(processInfo.command).toLowerCase();
  return isConfiguredIgnoredProcess(processInfo)
    || isPassiveListenerProcess(processInfo)
    || isPassivePlanServer(processInfo)
    || name.includes("listener")
    || name.includes("dev-server")
    || name.includes("watcher")
    || /(^|\s)(npm|pnpm|yarn|bun)\s+(run\s+)?(dev|serve|start)\b/.test(command)
    || /(^|\s)(next|vite|astro|nuxt)\s+dev\b/.test(command)
    || /(^|\s)(cargo\s+watch|watchexec|nodemon|webpack-dev-server)\b/.test(command)
    || /(^|\s)(tail\s+-f|log\s+stream)\b/.test(command);
}

function isFiniteVerificationProcess(processInfo: TrackedProcess): boolean {
  const command = normalizedCommand(processInfo.command).toLowerCase();
  if (/\b(--watch|--watchall|watch|dev|serve)\b/.test(command)) {
    return false;
  }
  return /(^|\s)(npm|pnpm|yarn|bun)\s+(ci|install|test)\b/.test(command)
    || /(^|\s)(npm|pnpm|yarn|bun)\s+run\s+[^\s]*(test|spec|check|lint|typecheck|build)[^\s]*\b/.test(command)
    || /(^|\s)(npx\s+)?tsc\b/.test(command)
    || /(^|\s)(pytest|ruff|mypy)\b/.test(command)
    || /(^|\s)cargo\s+(test|check|build|clippy)\b/.test(command)
    || /(^|\s)go\s+test\b/.test(command)
    || /(^|\s)swift\s+test\b/.test(command)
    || /(^|\s)xcodebuild\b/.test(command)
    || /(^|\s)(gradle|gradlew|\.\/gradlew|mvn|make)\s+[^\s]*(test|check|build|verify)[^\s]*\b/.test(command);
}

function isBlockingProcessWork(processInfo: TrackedProcess): boolean {
  if (backgroundProcessMode === "none") {
    return false;
  }
  if (isLongLivedServiceProcess(processInfo)) {
    return false;
  }
  if (backgroundProcessMode === "all") {
    return true;
  }
  return processInfo.alertOnSuccess === true || isFiniteVerificationProcess(processInfo);
}

function toTrackedProcess(raw: any, fallback?: Partial<TrackedProcess>): TrackedProcess | undefined {
  const id = typeof raw?.id === "string" && raw.id.length > 0
    ? raw.id
    : typeof fallback?.id === "string" && fallback.id.length > 0
      ? fallback.id
      : undefined;
  if (!id) {
    return undefined;
  }

  return {
    id,
    name: typeof raw?.name === "string" ? raw.name : fallback?.name ?? "",
    command: typeof raw?.command === "string" ? raw.command : fallback?.command ?? "",
    pid: Number.isFinite(raw?.pid) ? raw.pid : fallback?.pid,
    status: typeof raw?.status === "string" ? raw.status : fallback?.status,
    alertOnSuccess: typeof raw?.alertOnSuccess === "boolean" ? raw.alertOnSuccess : fallback?.alertOnSuccess,
    alertOnFailure: typeof raw?.alertOnFailure === "boolean" ? raw.alertOnFailure : fallback?.alertOnFailure,
  };
}

function retryableErrorMessage(event: any): string | undefined {
  const messages = Array.isArray(event?.messages) ? event.messages : [];
  const assistant = lastAssistantMessage(messages);
  if (assistant?.stopReason !== "error") {
    return undefined;
  }

  const errorMessage = String(assistant.errorMessage ?? "");
  if (!retryableErrorPattern.test(errorMessage)) {
    return undefined;
  }
  return errorMessage || "retryable provider error";
}

export default function (pi) {
  if (!enabled()) {
    return;
  }

  let agentActive = false;
  let retryHoldActive = false;
  let failureBlocked = false;
  let failureMessage: string | undefined;
  let blockedCount = 0;
  let blockedMessage: string | undefined;
  let lastState: AgentState | undefined;
  let lastMessage: string | undefined;
  let idleTimer: ReturnType<typeof setTimeout> | undefined;
  let retryTimer: ReturnType<typeof setTimeout> | undefined;
  let rootSession = false;
  // Most recent ExtensionContext, refreshed on every event that carries one.
  // The reconciliation watchdog uses it to ask pi whether the agent is truly
  // idle, independent of our own event-edge bookkeeping.
  let currentCtx: any | undefined;
  let reconcileTimer: ReturnType<typeof setInterval> | undefined;
  let heartbeatTimer: ReturnType<typeof setInterval> | undefined;
  const subagentIds = new Set<string>();
  const processIds = new Map<string, TrackedProcess>();
  const vccContinuationIds = new Set<string>();
  const wrappedUis = new WeakSet<object>();
  const blockingUiMethods = ["select", "confirm", "input", "editor", "custom"];

  function wrapBlockingUi(ctx: any): void {
    const ui = ctx?.ui;
    if (!rootSession || !ui || typeof ui !== "object" || wrappedUis.has(ui)) {
      return;
    }
    wrappedUis.add(ui);

    for (const method of blockingUiMethods) {
      const original = ui[method];
      if (typeof original !== "function") {
        continue;
      }
      ui[method] = async function (...args: any[]) {
        pi.events.emit("herdr:blocked", { active: true, label: `Pi UI: ${method}` });
        try {
          return await original.apply(this, args);
        } finally {
          pi.events.emit("herdr:blocked", { active: false, label: `Pi UI: ${method}` });
        }
      };
    }
  }

  function clearTimer(timer: ReturnType<typeof setTimeout> | undefined) {
    if (timer) {
      clearTimeout(timer);
    }
  }

  function clearIdleTimer() {
    clearTimer(idleTimer);
    idleTimer = undefined;
  }

  function clearPendingTimers() {
    clearIdleTimer();
    clearTimer(retryTimer);
    retryTimer = undefined;
  }

  function clearFailureState() {
    retryHoldActive = false;
    failureBlocked = false;
    failureMessage = undefined;
  }

  function clearSessionState() {
    agentActive = false;
    blockedCount = 0;
    blockedMessage = undefined;
    clearFailureState();
    vccContinuationIds.clear();
    lastState = undefined;
    lastMessage = undefined;
  }

  function observeVccContinuationEntry(entry: any): void {
    const snapshot = vccContinuationSnapshot(entry);
    if (!snapshot) {
      return;
    }
    if (vccTerminalStates.has(snapshot.state)) {
      vccContinuationIds.delete(snapshot.transactionId);
      return;
    }
    vccContinuationIds.add(snapshot.transactionId);
  }

  function restoreVccContinuations(ctx: any): void {
    vccContinuationIds.clear();
    try {
      const entries = ctx?.sessionManager?.getBranch?.();
      if (!Array.isArray(entries)) {
        return;
      }
      for (const entry of entries) {
        observeVccContinuationEntry(entry);
      }
    } catch {
      // Session-entry reconstruction is a reporting aid. A future entry_appended
      // event will restore VCC ownership if the branch is unavailable here.
    }
  }

  function managerBlockingSubagentsRunning(): boolean | undefined {
    const manager = (globalThis as any)[Symbol.for("pi-subagents:manager")];
    if (typeof manager?.hasRunning !== "function") {
      return undefined;
    }
    return manager.hasRunning() === true;
  }

  function subagentWorkActive(): boolean {
    const managerRunning = managerBlockingSubagentsRunning();
    if (managerRunning === false) {
      subagentIds.clear();
      return false;
    }
    if (managerRunning === true) {
      return true;
    }
    return subagentIds.size > 0;
  }

  function processWorkActive(): boolean {
    let hasBlockingProcess = false;
    for (const [id, processInfo] of processIds) {
      if (!isProcessLive(processInfo)) {
        processIds.delete(id);
        continue;
      }
      if (isBlockingProcessWork(processInfo)) {
        hasBlockingProcess = true;
      }
    }
    return hasBlockingProcess;
  }

  function desiredState() {
    if (blockedCount > 0) {
      return { state: "blocked" as const, message: blockedMessage };
    }
    if (failureBlocked) {
      return { state: "blocked" as const, message: failureMessage };
    }
    const operatorWait = operatorWaitMarker();
    if (operatorWait) {
      return { state: "blocked" as const, message: operatorWait.message };
    }
    if (agentActive || retryHoldActive || vccContinuationIds.size > 0) {
      return { state: "working" as const, message: undefined };
    }
    if (subagentWorkActive()) {
      return { state: "working" as const, message: undefined };
    }
    if (processWorkActive()) {
      return { state: "working" as const, message: undefined };
    }
    return { state: "idle" as const, message: undefined };
  }

  function publishState(force = false) {
    if (!rootSession) {
      return;
    }
    const next = desiredState();
    if (!force && next.state === lastState && next.message === lastMessage) {
      return;
    }
    lastState = next.state;
    lastMessage = next.message;
    queueState(next.state, next.message);
  }

  function scheduleIdle() {
    clearPendingTimers();
    clearFailureState();
    idleTimer = setTimeout(() => {
      idleTimer = undefined;
      publishState();
    }, idleDebounceMs);
    idleTimer.unref?.();
  }

  function holdForRetry(message: string) {
    clearPendingTimers();
    retryHoldActive = true;
    failureBlocked = false;
    failureMessage = message;
    publishState();

    const retryGeneration = stateReportGeneration;
    retryTimer = setTimeout(() => {
      if (retryGeneration !== stateReportGeneration) {
        return;
      }
      retryTimer = undefined;
      retryHoldActive = false;
      failureBlocked = true;
      publishState();
    }, retryGraceMs);
    retryTimer.unref?.();
  }

  function startReconcile() {
    if (reconcileTimer || reconcileIntervalMs <= 0) {
      return;
    }
    reconcileTimer = setInterval(reconcile, reconcileIntervalMs);
    reconcileTimer.unref?.();
  }

  function stopReconcile() {
    if (reconcileTimer) {
      clearInterval(reconcileTimer);
      reconcileTimer = undefined;
    }
  }

  function startHeartbeat() {
    if (heartbeatTimer || heartbeatIntervalMs <= 0) {
      return;
    }
    heartbeatTimer = setInterval(heartbeat, heartbeatIntervalMs);
    heartbeatTimer.unref?.();
  }

  function stopHeartbeat() {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer);
      heartbeatTimer = undefined;
    }
  }

  // Reconcile independently tracked work such as subagents and background
  // processes. `ctx.isIdle()` is not a safe replacement for agent_settled:
  // Pi can report idle between tool-loop callbacks while the foreground agent
  // still owns work. Only the full lifecycle settlement edge may clear
  // agentActive.
  function reconcile() {
    if (!rootSession) {
      return;
    }
    publishState();
  }

  function heartbeat() {
    if (!rootSession) {
      return;
    }

    const now = Date.now();
    const hasQueuedState = lastQueuedState !== undefined || lastQueuedMessage !== undefined;
    const shouldRepublish =
      hasQueuedState &&
      (lastSuccessfulStateReportAt < lastPublishAt ||
        (lastSuccessfulStateReportAt > 0 && now - lastSuccessfulStateReportAt >= heartbeatIntervalMs));

    if (shouldRepublish) {
      publishState(true);
    }
  }

  pi.events.on("herdr:blocked", (data) => {
    if (!rootSession) {
      return;
    }
    if (!data?.active) {
      blockedCount = Math.max(0, blockedCount - 1);
      if (blockedCount === 0) {
        blockedMessage = undefined;
      }
      publishState();
      return;
    }

    clearPendingTimers();
    blockedCount += 1;
    blockedMessage = data.label;
    publishState();
  });

  function addSubagent(id: unknown) {
    if (!rootSession || typeof id !== "string" || id.length === 0) {
      return;
    }
    subagentIds.add(id);
    clearIdleTimer();
    publishState();
  }

  function removeSubagent(id: unknown) {
    if (!rootSession || typeof id !== "string" || id.length === 0) {
      return;
    }
    subagentIds.delete(id);
    publishState();
  }

  pi.events.on("subagents:created", (data) => addSubagent(data?.id));
  pi.events.on("subagents:started", (data) => addSubagent(data?.id));
  pi.events.on("subagents:completed", (data) => removeSubagent(data?.id));
  pi.events.on("subagents:failed", (data) => removeSubagent(data?.id));

  pi.on("session_start", (_event, ctx) => {
    if (ctx?.hasUI !== true) {
      return;
    }
    stateReportGeneration += 1;
    stateReportsEnabled = true;
    queuedState = undefined;
    clearPendingTimers();
    clearSessionState();
    subagentIds.clear();
    processIds.clear();
    rootSession = true;
    currentCtx = ctx;
    restoreVccContinuations(ctx);
    wrapBlockingUi(ctx);
    updateSessionRef(ctx);
    void reportSession();
    publishState(true);
    startReconcile();
    startHeartbeat();
  });

  pi.on("agent_start", (_event, ctx) => {
    if (!rootSession) {
      return;
    }
    if (ctx) {
      currentCtx = ctx;
      wrapBlockingUi(ctx);
    }
    clearPendingTimers();
    clearFailureState();
    agentActive = true;
    publishState();
  });

  pi.on("agent_end", (event, ctx) => {
    if (!rootSession) {
      return;
    }
    if (ctx) {
      currentCtx = ctx;
      wrapBlockingUi(ctx);
    }
    if (!agentActive) {
      // Ignore duplicate or late low-level end events after the full run has
      // already settled. agent_end is not itself an idle boundary.
      return;
    }

    const retryableMessage = retryableErrorMessage(event);
    if (retryableMessage) {
      holdForRetry(retryableMessage);
    }
  });

  pi.on("agent_settled", (_event, ctx) => {
    if (!rootSession) {
      return;
    }
    if (ctx) {
      currentCtx = ctx;
      wrapBlockingUi(ctx);
    }

    agentActive = false;
    if (retryHoldActive || failureBlocked) {
      clearIdleTimer();
      publishState();
      return;
    }

    scheduleIdle();
  });

  pi.on("before_agent_start", (_event, ctx) => {
    if (rootSession && ctx) {
      currentCtx = ctx;
      wrapBlockingUi(ctx);
    }
  });

  pi.on("tool_call", (_event, ctx) => {
    if (!rootSession) {
      return;
    }
    if (ctx) {
      currentCtx = ctx;
      wrapBlockingUi(ctx);
    }
    // A tool call is foreground work even if a previous lifecycle edge was
    // missed. Pi does not emit a new agent_start for every tool-loop step.
    clearPendingTimers();
    clearFailureState();
    agentActive = true;
    publishState();
  });

  pi.on("tool_result", async (event, ctx) => {
    if (ctx) {
      currentCtx = ctx;
      wrapBlockingUi(ctx);
    }
    if (!rootSession || event?.toolName !== "process") {
      return;
    }

    const action = String(event?.input?.action ?? "");
    const details = processToolDetails(event);
    if (action === "clear") {
      processIds.clear();
      publishState();
      return;
    }

    if (action === "kill" && typeof event?.input?.id === "string") {
      processIds.delete(event.input.id);
      publishState();
      return;
    }

    if (event?.isError) {
      return;
    }

    if (Array.isArray(details?.processes)) {
      for (const rawProcess of details.processes) {
        const tracked = toTrackedProcess(rawProcess);
        if (!tracked) continue;
        if (isProcessLive(tracked)) {
          processIds.set(tracked.id, tracked);
        } else {
          processIds.delete(tracked.id);
        }
      }
    }

    const fallback = action === "start"
      ? {
          id: typeof details?.id === "string" ? details.id : undefined,
          name: typeof event?.input?.name === "string" ? event.input.name : "",
          command: typeof event?.input?.command === "string" ? event.input.command : "",
          status: "running" as ProcessStatus,
          alertOnSuccess: typeof event?.input?.alertOnSuccess === "boolean" ? event.input.alertOnSuccess : undefined,
          alertOnFailure: typeof event?.input?.alertOnFailure === "boolean" ? event.input.alertOnFailure : undefined,
        }
      : undefined;
    const tracked = toTrackedProcess(details?.process, fallback);
    if (tracked) {
      if (isProcessLive(tracked)) {
        processIds.set(tracked.id, tracked);
      } else {
        processIds.delete(tracked.id);
      }
    }

    publishState();
  });

  pi.on("entry_appended", (event, ctx) => {
    if (!rootSession) {
      return;
    }
    if (ctx) {
      currentCtx = ctx;
      wrapBlockingUi(ctx);
    }
    observeVccContinuationEntry(event?.entry);
    publishState();
  });

  pi.on("session_shutdown", async (event) => {
    if (!rootSession) {
      return;
    }
    const shutdownGeneration = stateReportGeneration;
    const shouldReleaseAgent = event?.reason !== "reload";
    stopReconcile();
    stopHeartbeat();
    clearPendingTimers();
    clearSessionState();
    subagentIds.clear();
    processIds.clear();
    stateReportsEnabled = false;
    queuedState = undefined;
    rootSession = false;
    currentCtx = undefined;
    await waitForStateQueueIdle();
    // Pi reloads extensions in-place and keeps the same session reference.
    // Releasing here makes Herdr suppress subsequent full-lifecycle reports
    // for that same session, so preserve authority until the new extension
    // instance republishes state from reload-time session_start.
    if (shouldReleaseAgent && shutdownGeneration === stateReportGeneration && !rootSession) {
      await releaseAgent();
    }
  });
}
