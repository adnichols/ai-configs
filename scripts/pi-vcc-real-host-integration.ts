import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, realpathSync, rmSync, statSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const args = process.argv.slice(2);
const values = new Map<string, string>();
const allowedOptions = new Set(["--candidate", "--cases", "--session-mode", "--provider", "--artifacts-dir"]);
for (let index = 0; index < args.length; index += 2) {
  const name = args[index];
  const value = args[index + 1];
  if (!name || !allowedOptions.has(name) || !value || value.startsWith("--")) {
    throw new Error("Usage: --candidate source|installed --cases all --session-mode file-backed --provider deterministic-fake [--artifacts-dir empty-path]");
  }
  values.set(name, value);
}
const candidateName = values.get("--candidate") ?? "source";
const cases = values.get("--cases") ?? "all";
const sessionMode = values.get("--session-mode") ?? "file-backed";
const providerName = values.get("--provider") ?? "deterministic-fake";
if (!["source", "installed"].includes(candidateName) || cases !== "all" || sessionMode !== "file-backed" || providerName !== "deterministic-fake") {
  throw new Error("Usage: --candidate source|installed --cases all --session-mode file-backed --provider deterministic-fake [--artifacts-dir empty-path]");
}
const requestedArtifactsDir = values.get("--artifacts-dir");
let root = "";
if (requestedArtifactsDir) {
  root = resolve(requestedArtifactsDir);
  if (existsSync(root)) {
    if (!statSync(root).isDirectory() || readdirSync(root).length !== 0) {
      throw new Error(`--artifacts-dir must be nonexistent or an empty directory: ${root}`);
    }
  } else {
    mkdirSync(root, { recursive: true });
  }
  root = realpathSync(root);
  console.log(`pi-vcc real-host artifacts: ${root}`);
}

const candidate = resolve(candidateName === "source"
  ? "_pi/packages/pi-vcc"
  : process.env.PI_VCC_INSTALLED_PACKAGE ?? join(process.env.HOME ?? "", ".pi/agent/local-packages/ai-configs/pi-vcc"));
const candidateRuntimeRoot = join(candidate, "node_modules/@earendil-works/pi-coding-agent");
const piExecutable = Bun.which("pi");
const installedRuntimeRoot = piExecutable
  ? dirname(dirname(realpathSync(piExecutable)))
  : undefined;
const runtimeRoot = existsSync(join(candidateRuntimeRoot, "dist/index.js"))
  ? candidateRuntimeRoot
  : installedRuntimeRoot && existsSync(join(installedRuntimeRoot, "dist/index.js"))
    ? installedRuntimeRoot
    : undefined;
if (!runtimeRoot) throw new Error("Unable to resolve the installed Pi runtime package");
const dependencyRoot = existsSync(join(candidate, "node_modules/@earendil-works/pi-ai"))
  ? join(candidate, "node_modules")
  : join(runtimeRoot, "node_modules");
const runtime = await import(pathToFileURL(join(runtimeRoot, "dist/index.js")).href);
const faux = await import(pathToFileURL(join(dependencyRoot, "@earendil-works/pi-ai/dist/providers/faux.js")).href);
const typebox = await import(pathToFileURL(join(dependencyRoot, "typebox/build/index.mjs")).href);
const protocol = await import(pathToFileURL(join(candidate, "src/core/continuation-protocol.ts")).href);
const { PI_VCC_LOAD_MARKER } = await import(pathToFileURL(join(candidate, "index.ts")).href);
const actualCompactContextTrigger = resolve(
  "scripts/fixtures/pi-vcc-actual-compact-context-trigger.ts",
);
if (typeof runtime.createAgentSession !== "function" || typeof runtime.SessionManager?.create !== "function" || typeof runtime.ModelRuntime?.create !== "function") {
  throw new Error("Pi runtime does not expose createAgentSession, SessionManager, and ModelRuntime");
}

if (!root) root = mkdtempSync(join(tmpdir(), "pi-vcc-real-host-"));
mkdirSync(join(root, "sessions"), { recursive: true });
mkdirSync(join(root, "logs"), { recursive: true });
process.env.PI_VCC_LOG_PATH = join(root, "logs", "pi-vcc.jsonl");
const originalSetTimeout = globalThis.setTimeout;
const scaledSetTimeout = ((callback: (...args: any[]) => void, delay?: number, ...timerArgs: any[]) => {
  const requested = delay ?? 0;
  // Coordinator timers are scheduled from an absolute deadline, so ordinary
  // clock movement makes the observed delay a few milliseconds smaller than
  // the nominal 15s/60s/900s phase budget.
  const scaled = requested >= 800_000 ? 90 : requested >= 50_000 ? 60 : requested >= 10_000 ? 25 : requested;
  return originalSetTimeout(callback, scaled, ...timerArgs);
}) as typeof setTimeout;
globalThis.setTimeout = scaledSetTimeout;

const sleep = (ms: number) => new Promise<void>((resolveSleep) => originalSetTimeout(resolveSleep, ms));
const waitFor = async (description: string, predicate: () => boolean, timeoutMs = 2_000) => {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    if (predicate()) return;
    await sleep(5);
  }
  throw new Error(`Timed out waiting for ${description}`);
};

interface Host {
  root: string;
  session: any;
  sessionManager: any;
  readonly coordinator: any;
  readonly ctx: any;
  core: any;
  events: Array<{ type: string; transactionId?: string; persistedAtEvent?: boolean }>;
  request(transactionId: string, deadlineMs?: number): any;
  flushArtifacts(): void;
  dispose(): void;
}

let hostOrdinal = 0;
const createHost = async (
  toolExecute?: (...args: any[]) => Promise<any>,
  options: {
    suppressContinuationMessageStartForExtensions?: boolean;
    packagePaths?: string[];
    extensionPaths?: string[];
  } = {},
): Promise<Host> => {
  hostOrdinal += 1;
  const hostRoot = join(root, "hosts", `host-${hostOrdinal}`);
  const sessionDir = join(root, "sessions", `host-${hostOrdinal}`);
  const agentDir = join(root, "agents", `host-${hostOrdinal}`);
  mkdirSync(sessionDir, { recursive: true });
  mkdirSync(agentDir, { recursive: true });
  writeFileSync(
    join(agentDir, "settings.json"),
    JSON.stringify({
      packages: options.packagePaths ?? [candidate],
      extensions: options.extensionPaths ?? [],
    }),
  );

  const core = faux.createFauxCore({
    api: `pi-vcc-faux-api-${hostOrdinal}`,
    provider: `pi-vcc-faux-provider-${hostOrdinal}`,
    models: [{
      id: `pi-vcc-faux-model-${hostOrdinal}`,
      name: "Pi VCC deterministic fake",
      reasoning: false,
      input: ["text"],
      cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
      contextWindow: 100_000,
      maxTokens: 1_000,
    }],
    tokensPerSecond: 100_000,
  });
  const modelRuntime = await runtime.ModelRuntime.create({
    modelsPath: null,
    allowModelNetwork: false,
  });
  await modelRuntime.setRuntimeApiKey(core.provider, "deterministic-no-network-key");
  modelRuntime.registerProvider(core.provider, {
    api: core.api,
    baseUrl: "http://127.0.0.1:0",
    apiKey: "deterministic-no-network-key",
    streamSimple: core.streamSimple,
    models: core.models,
  });

  const sessionManager = runtime.SessionManager.create(hostRoot, sessionDir);
  const customTools = toolExecute ? [{
    name: "host_progress_tool",
    label: "host_progress_tool",
    description: "Deterministic no-network progress tool",
    parameters: typebox.Type.Object({}),
    execute: toolExecute,
  }] : [];
  const result = await runtime.createAgentSession({
    cwd: hostRoot,
    agentDir,
    model: core.getModel(),
    modelRuntime,
    sessionManager,
    tools: customTools.length ? ["host_progress_tool"] : [],
    customTools,
  });
  const session = result.session as any;
  const owner = (globalThis as any)[PI_VCC_LOAD_MARKER];
  const registeredPackageExtensions = session._extensionRunner.extensions.filter((extension: any) =>
    extension.path.includes("pi-vcc") && [...extension.handlers.values()].some((handlers: any[]) => handlers.length > 0));
  if (!result.extensionsResult.extensions?.length || owner?.status !== "active" || !owner.coordinator || registeredPackageExtensions.length !== 1) {
    throw new Error("AgentSession did not discover exactly one registering pi-vcc package coordinator");
  }
  let suppressedContinuationStarts = 0;
  if (options.suppressContinuationMessageStartForExtensions) {
    const runner = session._extensionRunner;
    const originalEmit = runner.emit.bind(runner);
    runner.emit = async (event: any) => {
      if (event?.type === "message_start" && event.message?.customType === protocol.CONTINUATION_MESSAGE_CUSTOM_TYPE) {
        suppressedContinuationStarts += 1;
        return { errors: [] };
      }
      return originalEmit(event);
    };
  }
  const events: Host["events"] = [];
  session.subscribe((event: any) => {
    if (event.type === "message_start" || event.type === "message_end") {
      const details = event.message?.details;
      if (event.message?.customType === protocol.CONTINUATION_MESSAGE_CUSTOM_TYPE) {
        events.push({
          type: event.type,
          transactionId: details?.transactionId,
          persistedAtEvent: sessionManager.getBranch().some((entry: any) =>
            entry.type === "custom_message" && entry.details?.transactionId === details?.transactionId),
        });
      }
    } else if (event.type === "agent_settled") {
      const pending = (globalThis as any)[PI_VCC_LOAD_MARKER]?.coordinator?.getPending();
      events.push({
        type: event.type,
        transactionId: pending?.transactionId,
        persistedAtEvent: sessionManager.getBranch().some((entry: any) =>
          entry.type === "custom_message" && entry.details?.transactionId === pending?.transactionId),
      });
    }
  });

  return {
    root: hostRoot,
    session,
    sessionManager,
    get coordinator() { return (globalThis as any)[PI_VCC_LOAD_MARKER]?.coordinator; },
    get ctx() { return session._extensionRunner.createContext(); },
    core,
    events,
    request(transactionId: string, deadlineMs = 15_000) {
      const activeOwner = (globalThis as any)[PI_VCC_LOAD_MARKER];
      if (!activeOwner?.coordinator) throw new Error("pi-vcc owner is unavailable");
      return activeOwner.coordinator.request({
        initiator: "compact_context",
        outcome: "compacted",
        attemptId: `${transactionId}-attempt`,
        compactionId: `${transactionId}-compaction`,
        requestId: `${transactionId}-request`,
        originatingRequestId: `${transactionId}-originating-request`,
        transactionId,
        deadlineMs,
        retryLimit: 2,
      }, session._extensionRunner.createContext());
    },
    flushArtifacts() {
      const sessionFile = sessionManager.getSessionFile();
      if (sessionFile && !existsSync(sessionFile)) {
        sessionManager.appendMessage(faux.fauxAssistantMessage("real-host validation artifact flush"));
      }
    },
    dispose() {
      this.flushArtifacts();
      (globalThis as any)[PI_VCC_LOAD_MARKER]?.coordinator?.dispose?.();
      session.dispose();
      delete (globalThis as any)[PI_VCC_LOAD_MARKER];
    },
    get suppressedContinuationStarts() { return suppressedContinuationStarts; },
  } as Host & { readonly suppressedContinuationStarts: number };
};

const durableMessages = (host: Host, transactionId: string) => host.sessionManager.getBranch().filter((entry: any) =>
  entry.type === "custom_message" && entry.customType === protocol.CONTINUATION_MESSAGE_CUSTOM_TYPE && entry.details?.transactionId === transactionId);
const outcomes = (host: Host, transactionId: string) => host.sessionManager.getBranch().filter((entry: any) =>
  entry.type === "custom" && entry.customType === protocol.CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE && entry.data?.transactionId === transactionId);
const snapshots = (host: Host, transactionId: string) => host.sessionManager.getBranch().filter((entry: any) =>
  entry.type === "custom" && entry.customType === protocol.CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE && entry.data?.snapshot?.transactionId === transactionId);
const transactionLogRecords = (transactionId: string) => {
  try {
    return readFileSync(process.env.PI_VCC_LOG_PATH!, "utf8")
      .trim()
      .split("\n")
      .filter(Boolean)
      .map((line) => JSON.parse(line))
      .filter((record) => record.transactionId === transactionId);
  } catch {
    return [];
  }
};

const REQUIRED_REAL_HOST_CASES = [
  "duplicate-package-discovery-singleton",
  "session-replacement-singleton",
  "idle-async-rejection",
  "streaming-steer-without-message-start",
  "preaccept-unrelated-tool-activity",
  "missing-tool-completion-stall-recovery",
  "durable-top-level-custom-message",
  "postaccept-tool-activity-over-60s",
  "active-inference-over-progress-deadline",
  "high-frequency-tool-checkpoint-reload",
  "queued-activation-full-budget",
  "status-neutral-model-driving-supersession",
  "abort-backoff-persisted-acceptance",
  "v1-reload-adaptation",
  "active-compact-context-plan-builder-resume",
  "actual-compact-context-turn-end-resume",
] as const;
type RealHostCaseName = (typeof REQUIRED_REAL_HOST_CASES)[number];
const caseRegistry = new Map<RealHostCaseName, () => Promise<void>>();
const registerCase = (name: RealHostCaseName, run: () => Promise<void>) => {
  if (caseRegistry.has(name)) throw new Error(`Duplicate real-host case registration: ${name}`);
  caseRegistry.set(name, run);
};

try {
  // AgentSession.reload() emits shutdown to the old runner before constructing
  // the replacement runner. The package must release ownership through that
  // real lifecycle, without harness mutation of the singleton marker.
  registerCase("duplicate-package-discovery-singleton", async () => {
    const host = await createHost();
    const firstOwner = (globalThis as any)[PI_VCC_LOAD_MARKER];
    const firstRunner = host.session._extensionRunner;
    await host.session.reload();
    const replacementOwner = (globalThis as any)[PI_VCC_LOAD_MARKER];
    const replacementRunner = host.session._extensionRunner;
    if (!replacementOwner?.coordinator || replacementOwner === firstOwner || replacementRunner === firstRunner) {
      throw new Error("AgentSession.reload() did not replace the pi-vcc owner and extension runner");
    }
    const packageExtensions = replacementRunner.extensions.filter((extension: any) => extension.path.includes("pi-vcc"));
    if (packageExtensions.length !== 1 || packageExtensions[0].handlers.get("agent_settled")?.length !== 1 || packageExtensions[0].handlers.get("session_shutdown")?.length !== 1) {
      throw new Error("reload did not retain exactly one pi-vcc lifecycle handler set");
    }
    host.coordinator.request({
      initiator: "compact_context", outcome: "compacted", attemptId: "reload-singleton-attempt",
      transactionId: "reload-singleton", pendingToolCount: 1,
    }, host.ctx);
    const reloadRequests = host.sessionManager.getBranch().filter((entry: any) =>
      entry.type === "custom" && entry.customType === protocol.CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE && entry.data?.snapshot?.transactionId === "reload-singleton");
    if (reloadRequests.length !== 1 || durableMessages(host, "reload-singleton").length !== 0) {
      throw new Error("reload singleton path duplicated request publication or submitted while tool-unsafe");
    }
    await host.session._extensionRunner.emit({ type: "session_shutdown", reason: "new" });
    if (outcomes(host, "reload-singleton").length !== 1) {
      throw new Error("reload singleton validation transaction did not terminalize for artifact audit");
    }
    host.dispose();

    const duplicateAlias = join(root, "pi-vcc-duplicate-alias");
    symlinkSync(candidate, duplicateAlias, "dir");
    const duplicateHost = await createHost(undefined, { packagePaths: [candidate, duplicateAlias] });
    const duplicateExtensions = duplicateHost.session._extensionRunner.extensions.filter((extension: any) => extension.path.includes("pi-vcc"));
    if (duplicateExtensions.length !== 1) throw new Error(`duplicate package discovery did not collapse to one extension: ${duplicateExtensions.length}`);
    duplicateHost.dispose();
  });

  // Exercise a non-reload replacement boundary through the actual AgentSession
  // extension runner. Old work must terminalize before a newly loaded session can
  // acquire the singleton and deliver through its replacement coordinator.
  registerCase("session-replacement-singleton", async () => {
    const oldHost = await createHost();
    oldHost.coordinator.request({
      initiator: "compact_context",
      outcome: "compacted",
      attemptId: "new-replacement-old-attempt",
      transactionId: "new-replacement-old",
      pendingToolCount: 1,
    }, oldHost.ctx);
    await oldHost.session._extensionRunner.emit({ type: "session_shutdown", reason: "new" });
    if ((globalThis as any)[PI_VCC_LOAD_MARKER] !== undefined || outcomes(oldHost, "new-replacement-old").length !== 1) {
      throw new Error("actual new-session shutdown did not terminalize old work and release singleton ownership");
    }
    oldHost.flushArtifacts();
    oldHost.session.dispose();

    const replacement = await createHost();
    const replacementRunner = replacement.session._extensionRunner;
    const packageExtensions = replacementRunner.extensions.filter((extension: any) => extension.path.includes("pi-vcc"));
    if (packageExtensions.length !== 1 || packageExtensions[0].handlers.get("agent_settled")?.length !== 1 || packageExtensions[0].handlers.get("session_shutdown")?.length !== 1) {
      throw new Error("new-session replacement did not register exactly one pi-vcc lifecycle handler set");
    }
    replacement.core.setResponses([faux.fauxAssistantMessage("post-new replacement continuation complete")]);
    replacement.request("new-replacement-active");
    await waitFor("post-new replacement settlement", () => outcomes(replacement, "new-replacement-active").length === 1);
    if (durableMessages(replacement, "new-replacement-active").length !== 1 || outcomes(replacement, "new-replacement-active").length !== 1) {
      throw new Error("new-session replacement coordinator was not functional exactly once");
    }
    replacement.dispose();
  });

  // Actual extension sendMessage is void while AgentSession catches its rejected
  // Promise. Reject the first real host submission while idle, then restore
  // delivery and prove the readiness-gated 1s retry reaches one durable outcome.
  registerCase("idle-async-rejection", async () => {
    const host = await createHost();
    const originalSendCustomMessage = host.session.sendCustomMessage.bind(host.session);
    let submissionAttempts = 0;
    host.session.sendCustomMessage = async (...sendArgs: any[]) => {
      submissionAttempts += 1;
      if (submissionAttempts === 1) throw new Error("deterministic async host rejection");
      return originalSendCustomMessage(...sendArgs);
    };
    host.core.setResponses([faux.fauxAssistantMessage("async rejection retry completed")]);
    host.request("async-rejection", 25);
    await waitFor("async rejection retry", () => host.coordinator.getPending()?.state === "retrying");
    if (durableMessages(host, "async-rejection").length !== 0) throw new Error("async rejection unexpectedly persisted acceptance");
    await waitFor("second async rejection submission", () => submissionAttempts === 2);
    await waitFor("async rejection durable outcome", () => outcomes(host, "async-rejection").length === 1);
    if (submissionAttempts !== 2 || durableMessages(host, "async-rejection").length !== 1 || outcomes(host, "async-rejection").length !== 1) {
      throw new Error(`async rejection recovery violated exact-once delivery: attempts=${submissionAttempts}`);
    }
    host.session.sendCustomMessage = originalSendCustomMessage;
    host.dispose();
  });

  // Real streaming steer with source-faithful runner interception: AgentSession
  // still performs the real sendMessage/sendCustomMessage path, emits the
  // external lifecycle, and persists only after custom message_end. We suppress
  // only delivery of that custom message_start to extension handlers, proving
  // the next assistant lifecycle reconciles durable acceptance before progress.
  registerCase("streaming-steer-without-message-start", async () => {
    const host = await createHost(undefined, { suppressContinuationMessageStartForExtensions: true });
    let release!: () => void;
    let providerStarted = false;
    const held = new Promise<void>((resolveHeld) => { release = resolveHeld; });
    host.core.setResponses([
      async () => {
        providerStarted = true;
        await held;
        return faux.fauxAssistantMessage("initial streaming turn complete");
      },
      faux.fauxAssistantMessage("continuation made progress"),
    ]);
    const initialPrompt = host.session.prompt("start deterministic streaming turn");
    await waitFor("provider streaming start", () => providerStarted);
    host.request("streaming-steer");
    if (host.coordinator.getPending()?.acceptedAt !== undefined) throw new Error("streaming steer was accepted before host delivery");
    release();
    await initialPrompt;
    await waitFor("streaming steer settlement", () => outcomes(host, "streaming-steer").length === 1);
    const customEnd = host.events.find((event) => event.type === "message_end" && event.transactionId === "streaming-steer");
    const settled = host.events.find((event) => event.type === "agent_settled" && event.transactionId === "streaming-steer");
    if (!customEnd || customEnd.persistedAtEvent !== false || !settled || settled.persistedAtEvent !== true) {
      throw new Error(`host ordering changed: ${JSON.stringify(host.events)}`);
    }
    if (durableMessages(host, "streaming-steer").length !== 1 || outcomes(host, "streaming-steer").length !== 1) {
      throw new Error("streaming steer did not produce exactly one durable acceptance and outcome");
    }
    const starts = host.events.filter((event) => event.type === "message_start" && event.transactionId === "streaming-steer");
    const suppressedStarts = (host as Host & { readonly suppressedContinuationStarts: number }).suppressedContinuationStarts;
    if (starts.length !== 1 || suppressedStarts !== 1 || host.coordinator.getPending()?.state !== "settled") {
      throw new Error(`no-message_start interception did not reach exactly one successful outcome: starts=${starts.length} suppressed=${suppressedStarts}`);
    }
    host.dispose();
  });

  // Pre-acceptance activity comes from a real provider-driven tool belonging to
  // the already-running turn. It must not be credited to the queued continuation.
  registerCase("preaccept-unrelated-tool-activity", async () => {
    let toolStarted = false;
    let releaseTool!: () => void;
    const toolHeld = new Promise<void>((resolveTool) => { releaseTool = resolveTool; });
    const host = await createHost(async (_id, _params, _signal, onUpdate) => {
      toolStarted = true;
      onUpdate?.({ content: [{ type: "text", text: "unrelated progress" }], details: {} });
      await toolHeld;
      return { content: [{ type: "text", text: "unrelated done" }], details: {} };
    });
    host.core.setResponses([
      faux.fauxAssistantMessage([faux.fauxToolCall("host_progress_tool", {}, { id: "preaccept-tool" })], { stopReason: "toolUse" }),
      faux.fauxAssistantMessage("initial tool turn complete"),
      faux.fauxAssistantMessage("continuation complete"),
    ]);
    const initialPrompt = host.session.prompt("run unrelated tool first");
    await waitFor("unrelated tool start", () => toolStarted);
    host.request("preaccept-activity");
    await sleep(20);
    if (host.coordinator.getPending()?.acceptedAt !== undefined || host.coordinator.getPending()?.lastProgressAt !== undefined) {
      throw new Error("provider/tool activity before continuation delivery was attributed as acceptance or progress");
    }
    releaseTool();
    await initialPrompt;
    await waitFor("preaccept continuation settlement", () => outcomes(host, "preaccept-activity").length === 1);
    host.dispose();
  });

  // A real provider tool call emits updates, then goes silent past the scaled
  // representation of the 900s ceiling, then emits correlated progress and
  // finishes. Ownership stalls fail-closed, resumes, and settles exactly once.
  registerCase("missing-tool-completion-stall-recovery", async () => {
    let pauseReached = false;
    let releasePause!: () => void;
    const paused = new Promise<void>((resolvePause) => { releasePause = resolvePause; });
    const host = await createHost(async (_id, _params, _signal, onUpdate) => {
      onUpdate?.({ content: [{ type: "text", text: "update-1" }], details: {} });
      await sleep(30);
      onUpdate?.({ content: [{ type: "text", text: "update-2" }], details: {} });
      pauseReached = true;
      await paused;
      onUpdate?.({ content: [{ type: "text", text: "recovery-update" }], details: {} });
      return { content: [{ type: "text", text: "tool complete" }], details: {} };
    });
    host.core.setResponses([
      faux.fauxAssistantMessage([faux.fauxToolCall("host_progress_tool", {}, { id: "stall-tool" })], { stopReason: "toolUse" }),
      faux.fauxAssistantMessage("continuation completed after tool recovery"),
    ]);
    host.request("stall-recovery");
    await waitFor("tool silence window", () => pauseReached);
    await waitFor("fail-closed stalled state", () => host.coordinator.getPending()?.state === "stalled");
    if (outcomes(host, "stall-recovery").length !== 0) throw new Error("stalled transaction released ownership prematurely");
    releasePause();
    await waitFor("correlated update recovery", () => host.coordinator.getPending()?.state !== "stalled");
    await waitFor("stall recovery settlement", () => outcomes(host, "stall-recovery").length === 1);
    if (durableMessages(host, "stall-recovery").length !== 1 || outcomes(host, "stall-recovery").length !== 1) {
      throw new Error("stall/recovery path violated exactly-once durable outcome");
    }
    host.dispose();
  });

  registerCase("durable-top-level-custom-message", async () => {
    const host = await createHost(undefined, { suppressContinuationMessageStartForExtensions: true });
    host.core.setResponses([faux.fauxAssistantMessage("durable acceptance completed")]);
    host.request("durable-top-level");
    await waitFor("durable top-level settlement", () => outcomes(host, "durable-top-level").length === 1);
    if (durableMessages(host, "durable-top-level").length !== 1 || (host as Host & { readonly suppressedContinuationStarts: number }).suppressedContinuationStarts !== 1) {
      throw new Error("top-level custom_message was not the sole durable acceptance boundary");
    }
    host.dispose();
  });

  registerCase("postaccept-tool-activity-over-60s", async () => {
    let releaseTool!: () => void;
    let toolStarted = false;
    const held = new Promise<void>((resolveHeld) => { releaseTool = resolveHeld; });
    const host = await createHost(async () => {
      toolStarted = true;
      await held;
      return { content: [{ type: "text", text: "long tool complete" }], details: {} };
    });
    host.core.setResponses([
      faux.fauxAssistantMessage([faux.fauxToolCall("host_progress_tool", {}, { id: "over-60-tool" })], { stopReason: "toolUse" }),
      faux.fauxAssistantMessage("long tool continuation complete"),
    ]);
    host.request("postaccept-over-60");
    await waitFor("post-acceptance long tool start", () => toolStarted);
    await sleep(70);
    if (outcomes(host, "postaccept-over-60").length !== 0 || host.coordinator.getPending()?.state === "failed_loudly") {
      throw new Error("post-acceptance tool work was failed by the 60-second inactivity watchdog");
    }
    releaseTool();
    await waitFor("post-acceptance long tool settlement", () => outcomes(host, "postaccept-over-60").length === 1);
    host.dispose();
  });

  registerCase("active-inference-over-progress-deadline", async () => {
    let inferenceStarted = false;
    let releaseInference!: () => void;
    const heldInference = new Promise<void>((resolveInference) => { releaseInference = resolveInference; });
    const host = await createHost(async () => ({
      content: [{ type: "text", text: "tool completed before slow inference" }],
      details: {},
    }));
    host.core.setResponses([
      faux.fauxAssistantMessage([faux.fauxToolCall("host_progress_tool", {}, { id: "active-inference-tool" })], { stopReason: "toolUse" }),
      async () => {
        inferenceStarted = true;
        await heldInference;
        return faux.fauxAssistantMessage("slow post-tool inference completed");
      },
    ]);
    host.request("active-inference");
    await waitFor("slow post-tool provider inference", () => inferenceStarted);
    if (host.ctx.isIdle()) throw new Error("real host reported idle during active provider inference");
    const snapshotsBeforeDeadline = snapshots(host, "active-inference").length;
    const logsBeforeDeadline = transactionLogRecords("active-inference").length;
    await sleep(75);
    const active = host.coordinator.getPending();
    if (active?.state !== "progressed" || active.pendingToolCount !== 0 || outcomes(host, "active-inference").length !== 0) {
      throw new Error(`active inference lost continuation ownership: ${JSON.stringify(active)}`);
    }
    if (snapshots(host, "active-inference").length !== snapshotsBeforeDeadline + 1 || transactionLogRecords("active-inference").length !== logsBeforeDeadline + 1) {
      throw new Error("active inference deadline did not produce exactly one durable deferral checkpoint");
    }
    releaseInference();
    await waitFor("active inference settlement", () => outcomes(host, "active-inference").length === 1);
    if (outcomes(host, "active-inference")[0]?.data?.terminalState !== "settled") {
      throw new Error("active inference did not settle successfully after provider completion");
    }
    host.dispose();
  });

  registerCase("high-frequency-tool-checkpoint-reload", async () => {
    let updatesEmitted = 0;
    let releaseTool!: () => void;
    const heldTool = new Promise<void>((resolveTool) => { releaseTool = resolveTool; });
    const host = await createHost(async (_id, _params, _signal, onUpdate) => {
      for (let index = 0; index < 200; index += 1) {
        updatesEmitted += 1;
        onUpdate?.({ content: [{ type: "text", text: `stream-${index}` }], details: {} });
      }
      await heldTool;
      return { content: [{ type: "text", text: "high-frequency tool complete" }], details: {} };
    });
    host.core.setResponses([
      faux.fauxAssistantMessage([faux.fauxToolCall("host_progress_tool", {}, { id: "high-frequency-tool" })], { stopReason: "toolUse" }),
      faux.fauxAssistantMessage("high-frequency continuation complete"),
    ]);
    host.request("high-frequency-reload");
    await waitFor("high-frequency tool updates", () => updatesEmitted === 200);
    await sleep(20);
    const snapshotsBeforeReload = snapshots(host, "high-frequency-reload").length;
    const logsBeforeReload = transactionLogRecords("high-frequency-reload").length;
    if (snapshotsBeforeReload > 8 || logsBeforeReload !== snapshotsBeforeReload + 1) {
      throw new Error(`high-frequency writes were not bounded before reload: snapshots=${snapshotsBeforeReload} logs=${logsBeforeReload}`);
    }

    const reloadAt = Date.now();
    await host.session.reload();
    await waitFor("active-tool replacement coordinator", () => Boolean(host.coordinator));
    host.coordinator.reconcile(host.ctx);
    const restored = host.coordinator.getPending();
    if (
      restored?.transactionId !== "high-frequency-reload" ||
      restored.state !== "progressed" ||
      restored.pendingToolCount !== 1 ||
      (restored.toolStallDeadlineAt ?? 0) < reloadAt + 899_000
    ) {
      throw new Error(`active-tool reload did not grant a fresh stall interval: restored=${JSON.stringify(restored)} outcomes=${JSON.stringify(outcomes(host, "high-frequency-reload").map((entry: any) => entry.data))} snapshots=${JSON.stringify(snapshots(host, "high-frequency-reload").map((entry: any) => entry.data?.snapshot))}`);
    }
    if (snapshots(host, "high-frequency-reload").length !== snapshotsBeforeReload || transactionLogRecords("high-frequency-reload").length !== logsBeforeReload) {
      throw new Error("active-tool reload persisted synthetic liveness instead of retaining bounded durable evidence");
    }
    releaseTool();
    await waitFor("high-frequency reload settlement", () => outcomes(host, "high-frequency-reload").length === 1);
    const finalSnapshots = snapshots(host, "high-frequency-reload").length;
    const finalLogs = transactionLogRecords("high-frequency-reload").length;
    if (finalSnapshots > snapshotsBeforeReload + 4 || finalLogs !== finalSnapshots + 1) {
      throw new Error(`high-frequency terminal writes exceeded material-transition bound: snapshots=${finalSnapshots} logs=${finalLogs}`);
    }
    host.dispose();
  });

  registerCase("queued-activation-full-budget", async () => {
    const host = await createHost();
    host.core.setResponses([
      faux.fauxAssistantMessage("first queued-owner continuation complete"),
      faux.fauxAssistantMessage("second queued continuation complete"),
    ]);
    host.coordinator.request({
      initiator: "compact_context", outcome: "compacted", attemptId: "queue-first-attempt",
      transactionId: "queue-first", pendingToolCount: 1,
    }, host.ctx);
    host.request("queue-second", 15_000);
    await sleep(40);
    await host.session._extensionRunner.emit({ type: "message_end", message: { role: "assistant", stopReason: "stop" } });
    await waitFor("both queued continuations", () => outcomes(host, "queue-first").length === 1 && outcomes(host, "queue-second").length === 1);
    const secondSubmitted = host.sessionManager.getBranch().find((entry: any) =>
      entry.type === "custom" && entry.customType === protocol.CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE &&
      entry.data?.snapshot?.transactionId === "queue-second" && entry.data.snapshot.state === "submitted");
    const secondSnapshot = secondSubmitted?.data?.snapshot;
    if (!secondSnapshot || secondSnapshot.acceptanceDeadlineAt - secondSnapshot.submittedAt !== 15_000) {
      throw new Error("queued activation did not receive its full acceptance budget");
    }
    host.dispose();
  });

  registerCase("status-neutral-model-driving-supersession", async () => {
    const host = await createHost();
    host.coordinator.request({
      initiator: "compact_context", outcome: "compacted", attemptId: "custom-intent-attempt",
      transactionId: "custom-intent", pendingToolCount: 1,
    }, host.ctx);
    const statusMessage = { role: "custom", customType: "ad-process:update", content: "status", display: false, details: {} };
    await host.session.sendCustomMessage(statusMessage, { triggerTurn: false });
    await host.session._extensionRunner.emit({ type: "message_start", message: statusMessage });
    if (host.coordinator.getPending()?.state !== "waiting_tools" || outcomes(host, "custom-intent").length !== 0) {
      throw new Error("status-only custom message superseded continuation ownership");
    }
    const modelDrivingMessage = { role: "custom", customType: "vcc-recall", content: "model input", display: false, details: {} };
    await host.session.sendCustomMessage(modelDrivingMessage, { triggerTurn: false });
    await host.session._extensionRunner.emit({ type: "message_start", message: modelDrivingMessage });
    await waitFor("model-driving supersession", () => outcomes(host, "custom-intent").length === 1);
    if (outcomes(host, "custom-intent")[0]?.data?.terminalReason !== "independent_input") {
      throw new Error("model-driving custom message did not supersede fail-closed");
    }
    host.dispose();
  });

  registerCase("abort-backoff-persisted-acceptance", async () => {
    const host = await createHost();
    const originalSendCustomMessage = host.session.sendCustomMessage.bind(host.session);
    const sentAt: number[] = [];
    host.session.sendCustomMessage = async (...sendArgs: any[]) => {
      if (sendArgs[0]?.customType === protocol.CONTINUATION_MESSAGE_CUSTOM_TYPE) sentAt.push(Date.now());
      return originalSendCustomMessage(...sendArgs);
    };
    host.core.setResponses([
      faux.fauxAssistantMessage("aborted continuation", { stopReason: "aborted" }),
      faux.fauxAssistantMessage("retry continuation succeeded"),
    ]);
    host.request("abort-persisted-retry");
    await waitFor("persisted aborted first acceptance", () => durableMessages(host, "abort-persisted-retry").length === 1);
    await waitFor("abort retry settlement", () => outcomes(host, "abort-persisted-retry").length === 1, 3_000);
    const messages = durableMessages(host, "abort-persisted-retry");
    if (sentAt.length !== 2 || messages.length !== 2 || sentAt[1] - sentAt[0] < 900 || messages.map((entry: any) => entry.details.submissionCount).join(",") !== "1,2") {
      throw new Error(`abort retry did not preserve ordinal-scoped 1s backoff: sends=${sentAt.length} durable=${messages.length} gap=${sentAt[1] - sentAt[0]}`);
    }
    host.session.sendCustomMessage = originalSendCustomMessage;
    host.dispose();
  });

  registerCase("active-compact-context-plan-builder-resume", async () => {
    const host = await createHost();
    host.core.setResponses([
      faux.fauxAssistantMessage("Resumed the active hub activity observability plan from its next concrete phase."),
    ]);
    const packageExtension = host.session._extensionRunner.extensions.find((extension: any) =>
      extension.path.includes("pi-vcc"));
    const beforeCompact = packageExtension?.handlers.get("session_before_compact")?.[0];
    const sessionCompact = packageExtension?.handlers.get("session_compact")?.[0];
    if (!beforeCompact || !sessionCompact) {
      throw new Error("real host did not register pi-vcc compaction lifecycle handlers");
    }

    const result = await beforeCompact({
      type: "session_before_compact",
      reason: "manual",
      willRetry: false,
      preparation: {
        previousSummary: undefined,
        tokensBefore: 5_000,
        fileOps: { read: [], written: [], edited: [] },
      },
      branchEntries: [
        { id: "plan-user", type: "message", message: { role: "user", content: "Execute thoughts/plans/hub-activity-observability.html from P0 through P3." } },
        { id: "plan-progress", type: "message", message: { role: "assistant", content: "P0 is complete; the next concrete phase is P1.", stopReason: "stop" } },
        { id: "plan-user-followup", type: "message", message: { role: "user", content: "Continue the implementation without stopping." } },
        { id: "plan-boundary", type: "message", message: { role: "assistant", content: "The P0 test loop is interpreted; compact before P1.", stopReason: "stop" } },
      ],
      customInstructions: '__PI_VCC_MANUAL_BYPASS__\n{"source":"compact_context","boundary":"after_test_loop","reason":"P0 verified; continue plan P1","resumePolicy":"active","attemptId":"plan-builder-attempt","requestId":"plan-builder-request"}',
    }, host.ctx);
    if (result?.compaction?.details?.compactionIntent?.resumePolicy !== "active" || result.compaction.details.interruptedInFlightTurn !== false) {
      throw new Error(`plan-builder fixture did not reproduce a completed active compact_context boundary: ${JSON.stringify(result?.compaction?.details)}`);
    }

    await sessionCompact({
      type: "session_compact",
      compactionEntry: { id: "plan-builder-compaction", details: result.compaction.details },
      reason: "manual",
      willRetry: false,
    }, host.ctx);
    await waitFor("active compact_context plan-builder request", () =>
      host.sessionManager.getBranch().some((entry: any) =>
        entry.type === "custom" &&
        entry.customType === protocol.CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE &&
        entry.data?.snapshot?.attemptId === "plan-builder-attempt"));
    const request = host.sessionManager.getBranch().find((entry: any) =>
      entry.type === "custom" &&
      entry.customType === protocol.CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE &&
      entry.data?.snapshot?.attemptId === "plan-builder-attempt")?.data?.snapshot;
    const transactionId = request?.transactionId;
    if (typeof transactionId !== "string") throw new Error("plan-builder continuation request omitted a transaction ID");
    if (request.resumePolicy !== "active" || request.compactionId !== "plan-builder-compaction") {
      throw new Error(`plan-builder continuation request lost active policy or compaction identity: ${JSON.stringify(request)}`);
    }
    await waitFor("active compact_context plan-builder continuation", () => outcomes(host, transactionId).length === 1);
    const delivered = durableMessages(host, transactionId);
    if (delivered.length !== 1) {
      throw new Error(`active compact_context did not deliver exactly one plan continuation: ${JSON.stringify(delivered)}`);
    }
    if (outcomes(host, transactionId)[0]?.data?.terminalState !== "settled") {
      throw new Error(`plan-builder continuation did not settle after delivery: ${JSON.stringify(outcomes(host, transactionId)[0]?.data)}`);
    }
    host.dispose();
  });

  registerCase("actual-compact-context-turn-end-resume", async () => {
    const host = await createHost(undefined, {
      extensionPaths: [actualCompactContextTrigger],
    });
    const runtimeErrors: Array<{ error?: string; extensionPath?: string }> = [];
    const removeErrorListener = host.session._extensionRunner.onError((error: any) => {
      runtimeErrors.push(error);
    });
    host.core.setResponses([
      faux.fauxAssistantMessage("Semantic boundary reached."),
      faux.fauxAssistantMessage("Continuation completed after actual compaction."),
    ]);
    const seed = (role: "user" | "assistant", text: string) =>
      host.sessionManager.appendMessage(
        role === "user"
          ? { role, content: [{ type: "text", text }], timestamp: Date.now() }
          : faux.fauxAssistantMessage(text),
      );
    seed("user", "Complete the previous phase.");
    seed("assistant", "The previous phase is complete.");
    seed("user", "Proceed to the next phase.");
    seed("assistant", "Preparing the next phase.");

    await host.session.prompt("Reach the next semantic boundary.");
    await waitFor("actual compact_context compaction", () =>
      host.sessionManager.getBranch().some((entry: any) => entry.type === "compaction"),
    );
    await waitFor("actual compact_context continuation", () =>
      host.sessionManager.getBranch().some(
        (entry: any) =>
          entry.type === "custom" &&
          entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE &&
          entry.data?.origin === "compact_context" &&
          entry.data?.terminalState === "settled",
      ),
    );
    const continuationMessages = host.sessionManager.getBranch().filter(
      (entry: any) =>
        entry.type === "custom_message" &&
        entry.customType === CONTINUATION_MESSAGE_CUSTOM_TYPE &&
        entry.details?.attemptId === "actual-compact-context-attempt",
    );
    const failures = host.sessionManager.getBranch().filter(
      (entry: any) =>
        entry.type === "custom" &&
        entry.customType === CONTINUATION_OUTCOME_ENTRY_CUSTOM_TYPE &&
        entry.data?.attemptId === "actual-compact-context-attempt" &&
        entry.data?.terminalState === "failed_loudly",
    );
    const activeRunErrors = runtimeErrors.filter((error) =>
      /Agent is already processing a prompt/.test(error.error ?? ""),
    );
    removeErrorListener();
    if (continuationMessages.length !== 1 || failures.length !== 0 || activeRunErrors.length !== 0) {
      throw new Error(
        `actual compact_context continuation did not complete cleanly: messages=${continuationMessages.length}, failures=${JSON.stringify(failures.map((entry: any) => entry.data))}, activeRunErrors=${JSON.stringify(activeRunErrors)}`,
      );
    }
    host.dispose();
  });

  registerCase("v1-reload-adaptation", async () => {
    const host = await createHost();
    const epochs = { session: 0, input: 0, agent: 0, turn: 0, message: 0, settlement: 0 };
    const created = {
      protocol: protocol.CONTINUATION_PROTOCOL_NAME, version: 1, transactionId: "v1-reload", origin: "compact_context", reason: "compacted",
      attemptId: "v1-reload-attempt", requestId: "v1-reload-request", originatingRequestId: "v1-reload-origin", resumePolicy: "active",
      state: "created", createdAt: Date.now(), deadlineAt: Date.now() + 15_000, pendingToolCount: 0, submissionCount: 0, retryCount: 0, retryLimit: 2, epochs,
    };
    const submitted = { ...created, state: "submitted", submissionCount: 1, submittedAt: created.createdAt + 1 };
    const progressed = { ...submitted, state: "progressed", acceptedAt: created.createdAt + 2, lastProgressAt: created.createdAt + 3, lastAssistantResult: "progress" };
    host.sessionManager.appendCustomEntry(protocol.CONTINUATION_REQUEST_ENTRY_CUSTOM_TYPE, { protocol: protocol.CONTINUATION_PROTOCOL_NAME, version: 1, kind: "request", snapshot: created });
    host.sessionManager.appendCustomEntry(protocol.CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE, { protocol: protocol.CONTINUATION_PROTOCOL_NAME, version: 1, kind: "snapshot", snapshot: submitted });
    host.sessionManager.appendCustomEntry(protocol.CONTINUATION_SNAPSHOT_ENTRY_CUSTOM_TYPE, { protocol: protocol.CONTINUATION_PROTOCOL_NAME, version: 1, kind: "snapshot", snapshot: progressed });
    host.sessionManager.appendCustomMessageEntry(protocol.CONTINUATION_MESSAGE_CUSTOM_TYPE, "legacy continuation", false, {
      protocol: protocol.CONTINUATION_PROTOCOL_NAME, version: 1, transactionId: "v1-reload", attemptId: "v1-reload-attempt", submissionCount: 1,
      requestId: "v1-reload-request", originatingRequestId: "v1-reload-origin",
    });
    await host.session.reload();
    host.coordinator.reconcile(host.ctx);
    const adapted = host.coordinator.getPending();
    if (adapted?.transactionId !== "v1-reload" || adapted.version !== 2 || adapted.state !== "progressed") {
      throw new Error(`V1 reload did not adapt active work without resubmission: ${JSON.stringify(adapted)}`);
    }
    await host.session._extensionRunner.emit({ type: "agent_settled" });
    await waitFor("V1 adapted settlement", () => outcomes(host, "v1-reload").length === 1);
    if (durableMessages(host, "v1-reload").length !== 1) throw new Error("V1 reload duplicated durable delivery");
    host.dispose();
  });

  const registeredNames = [...caseRegistry.keys()].sort();
  const requiredNames = [...REQUIRED_REAL_HOST_CASES].sort();
  if (registeredNames.length !== requiredNames.length || registeredNames.some((name, index) => name !== requiredNames[index])) {
    throw new Error(`Real-host case registry is incomplete or renamed: required=${requiredNames.join(",")} registered=${registeredNames.join(",")}`);
  }
  for (const name of REQUIRED_REAL_HOST_CASES) {
    const run = caseRegistry.get(name);
    if (!run) throw new Error(`Required real-host case omitted: ${name}`);
    await run();
  }

  const sessionFiles = Array.from({ length: hostOrdinal }, (_, index) => join(root, "sessions", `host-${index + 1}`));
  const persistedText = sessionFiles.flatMap((directory) => {
    try {
      return Array.from(new Bun.Glob("**/*.jsonl").scanSync({ cwd: directory, absolute: true })).map((path) => readFileSync(path, "utf8"));
    } catch {
      return [];
    }
  }).join("\n");
  if (!persistedText.includes('"type":"custom_message"') || !persistedText.includes("streaming-steer")) {
    throw new Error("file-backed AgentSession persistence did not contain the required continuation custom_message");
  }
  console.log(`pi-vcc real-host integration: PASS candidate=${candidateName} hosts=${hostOrdinal}`);
} finally {
  globalThis.setTimeout = originalSetTimeout;
  const owner = (globalThis as any)[PI_VCC_LOAD_MARKER];
  owner?.coordinator?.dispose?.();
  delete (globalThis as any)[PI_VCC_LOAD_MARKER];
  if (!requestedArtifactsDir && process.env.PI_VCC_KEEP_REAL_HOST_ARTIFACTS !== "1") rmSync(root, { recursive: true, force: true });
  else if (!requestedArtifactsDir) console.log(`pi-vcc real-host artifacts: ${root}`);
}
