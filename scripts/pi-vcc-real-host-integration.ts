// Candidate contract harness: imports source/installed candidates against the
// installed Pi module surface, then exercises registered callbacks with a
// deterministic synthetic context. It does not claim real Pi lifecycle dispatch.
import { mock } from "bun:test";
import { existsSync, mkdirSync, mkdtempSync, readdirSync, realpathSync, statSync, writeFileSync } from "node:fs";
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
if (!(["source", "installed"] as string[]).includes(candidateName) || cases !== "all" || sessionMode !== "file-backed" || providerName !== "deterministic-fake") {
  throw new Error("Usage: --candidate source|installed --cases all --session-mode file-backed --provider deterministic-fake [--artifacts-dir empty-path]");
}

const requestedArtifactsDir = values.get("--artifacts-dir");
const root = requestedArtifactsDir ? resolve(requestedArtifactsDir) : mkdtempSync(join(tmpdir(), "pi-vcc-candidate-contract-"));
if (existsSync(root)) {
  if (!statSync(root).isDirectory() || readdirSync(root).length !== 0) {
    throw new Error(`--artifacts-dir must be nonexistent or an empty directory: ${root}`);
  }
} else {
  mkdirSync(root, { recursive: true });
}
const artifactRoot = realpathSync(root);
console.log(`pi-vcc candidate-contract artifacts: ${artifactRoot}`);

const candidate = resolve(candidateName === "source"
  ? "_pi/packages/pi-vcc"
  : process.env.PI_VCC_INSTALLED_PACKAGE ?? join(process.env.HOME ?? "", ".pi/agent/local-packages/ai-configs/pi-vcc"));
const extension = resolve(candidateName === "source"
  ? "_pi/extensions/percentage-compaction.ts"
  : process.env.PI_VCC_INSTALLED_EXTENSION ?? join(process.env.HOME ?? "", ".pi/agent/extensions/percentage-compaction.ts"));

if (!existsSync(join(candidate, "package.json")) || !existsSync(join(candidate, "src/hooks/before-compact.ts"))) {
  throw new Error(`candidate package is not an extension-only pi-vcc package: ${candidate}`);
}
if (!existsSync(join(candidate, "src/core/custom-message-classifier.ts"))) {
  throw new Error(`candidate package is missing the legacy classifier: ${candidate}`);
}
if (!existsSync(extension)) {
  throw new Error(`percentage-compaction extension missing for candidate ${candidateName}: ${extension}`);
}
if (candidateName === "installed" && extension.replaceAll("\\", "/").includes("/_pi/extensions/")) {
  throw new Error("installed candidate must not load the source percentage-compaction extension");
}

const piExecutable = Bun.which("pi");
if (!piExecutable) throw new Error("Pi executable is required to resolve the installed extension API module");
const runtimeRoot = dirname(dirname(realpathSync(piExecutable)));
const codingAgentModule = await import(pathToFileURL(join(runtimeRoot, "dist/index.js")).href);
const typeboxModule = await import(pathToFileURL(join(runtimeRoot, "node_modules/typebox/build/index.mjs")).href);
// The candidate package is a peer extension loaded by Pi. Mocking these two
// package names to the actual installed runtime lets Bun import the candidate
// source without mutating the checkout's node_modules tree.
mock.module("@earendil-works/pi-coding-agent", () => codingAgentModule);
mock.module("typebox", () => typeboxModule);

mkdirSync(join(artifactRoot, "sessions"), { recursive: true });
mkdirSync(join(artifactRoot, "logs"), { recursive: true });

const packageModule = await import(pathToFileURL(join(candidate, "index.ts")).href);
const packageHandlers: Record<string, any> = {};
const packageTools: Record<string, any> = {};
packageModule.default({
  on: (event: string, handler: any) => { packageHandlers[event] = handler; },
  registerTool: (tool: any) => { packageTools[tool.name] = tool; },
  registerCommand: () => {},
});
if (!packageHandlers.session_before_compact || !packageTools.vcc_recall) {
  throw new Error("candidate pi-vcc package did not register its compaction hook and recall tool");
}

const extensionModule = await import(pathToFileURL(extension).href);
const percentageCompaction = extensionModule.default as (api: any) => void;
const loadMarker = extensionModule.PI_VCC_LOAD_MARKER as string;
const hardBackstop = extensionModule.HARD_AUTO_COMPACTION_PERCENT as number;
const marker = extensionModule.PI_VCC_MANUAL_BYPASS_MARKER as string;

const runExtensionCase = async (name: string) => {
  const handlers: Record<string, any> = {};
  const tools: Record<string, any> = {};
  const compactions: any[] = [];
  const notifications: any[] = [];
  const customMessages: any[] = [];
  const controller = new AbortController();
  let idle = false;
  const ctx: any = {
    mode: "rpc",
    hasUI: false,
    cwd: process.cwd(),
    model: undefined,
    signal: controller.signal,
    isIdle: () => idle,
    ui: { notify: (message: string, level: string) => notifications.push({ message, level }) },
    getContextUsage: () => ({ percent: hardBackstop, contextWindow: 200_000, tokens: 160_000 }),
    compact: (request: any) => compactions.push(request ?? {}),
  };
  (globalThis as any)[loadMarker] = { status: "active" };
  percentageCompaction({
    on: (event: string, handler: any) => { handlers[event] = handler; },
    registerTool: (tool: any) => { tools[tool.name] = tool; },
    registerCommand: () => {},
    sendMessage: (message: any, options: any) => customMessages.push({ message, options }),
  });

  if (name === "settled-run") {
    const result = await tools.compact_context.execute(
      "case",
      { reason: "integration", boundary: "after_test_loop", preserve: "keep integration evidence" },
      controller.signal,
      undefined,
      ctx,
    );
    if (!result.details.accepted || compactions.length !== 0) throw new Error("compact_context did not record idle maintenance safely");
    await handlers.turn_end({ message: { role: "assistant", stopReason: "stop" } }, ctx);
    if (compactions.length !== 0) throw new Error("semantic maintenance compacted before settlement");
    idle = true;
    await handlers.agent_settled({}, ctx);
    if (compactions.length !== 1 || !compactions[0].customInstructions.includes(marker)) {
      throw new Error("settled semantic maintenance did not compact exactly once");
    }
  } else if (name === "escape-terminal") {
    await tools.compact_context.execute("case", { reason: "integration", boundary: "after_test_loop" }, controller.signal, undefined, ctx);
    await handlers.turn_end({ message: { role: "assistant", stopReason: "aborted" } }, ctx);
    idle = true;
    await handlers.agent_settled({}, ctx);
    if (compactions.length !== 0) throw new Error("aborted runtime retained compaction work");
  } else if (name === "native-satisfies-pending") {
    await tools.compact_context.execute("case", { reason: "integration", boundary: "after_test_loop" }, controller.signal, undefined, ctx);
    await handlers.session_compact({ compactionEntry: { details: {} } }, ctx);
    idle = true;
    await handlers.agent_settled({}, ctx);
    if (compactions.length !== 0) throw new Error("native compaction did not satisfy pending semantic maintenance");
  } else if (name === "native-threshold") {
    await handlers.turn_end({ message: { role: "assistant", stopReason: "toolUse" } }, ctx);
    if (compactions.length !== 0 || !notifications.some((item) => item.level === "warning" && item.message === `Context is at ${hardBackstop}%.`)) {
      throw new Error("threshold path did not remain a concise warning without compaction work");
    }
  } else {
    throw new Error(`unknown extension case: ${name}`);
  }

  if (customMessages.length !== 0) throw new Error(`${name} emitted a synthetic continuation message`);
  return { name, compactions: compactions.length, customMessages: customMessages.length, notifications };
};

const extensionResults = [
  await runExtensionCase("settled-run"),
  await runExtensionCase("escape-terminal"),
  await runExtensionCase("native-satisfies-pending"),
  await runExtensionCase("native-threshold"),
];

const messageEntry = (id: string, message: any) => ({ type: "message", id, parentId: null, timestamp: new Date().toISOString(), message });
const user = (text: string) => ({ role: "user", content: text, timestamp: Date.now() });
const assistant = (text: string) => ({
  role: "assistant",
  content: [{ type: "text", text }],
  stopReason: "stop",
  provider: "faux",
  model: "faux-1",
  api: "faux",
  usage: { input: 1, output: 1, cacheRead: 0, cacheWrite: 0, totalTokens: 2 },
  timestamp: Date.now(),
});
const toolCall = (id: string) => ({
  role: "assistant",
  content: [{ type: "toolCall", id, name: "bash", arguments: { command: "echo ok" } }],
  stopReason: "toolUse",
  provider: "faux",
  model: "faux-1",
  api: "faux",
  usage: { input: 1, output: 1, cacheRead: 0, cacheWrite: 0, totalTokens: 2 },
  timestamp: Date.now(),
});
const toolResult = (id: string) => ({
  role: "toolResult",
  toolCallId: id,
  toolName: "bash",
  content: [{ type: "text", text: "ok" }],
  isError: false,
  timestamp: Date.now(),
});
const preparation = (overrides: Record<string, unknown> = {}) => ({
  firstKeptEntryId: "kept-user",
  messagesToSummarize: [user("old request"), assistant("old answer")],
  turnPrefixMessages: [],
  isSplitTurn: false,
  tokensBefore: 500,
  previousSummary: undefined,
  fileOps: { read: new Set<string>(), written: new Set<string>(), edited: new Set<string>() },
  settings: { enabled: true, reserveTokens: 100, keepRecentTokens: 200 },
  ...overrides,
});

const nativeResult = await packageHandlers.session_before_compact({
  preparation: preparation(),
  branchEntries: [
    messageEntry("old-user", user("old request")),
    messageEntry("old-assistant", assistant("old answer")),
    messageEntry("kept-user", user("new request")),
    messageEntry("kept-assistant", assistant("new answer")),
  ],
  reason: "threshold",
  willRetry: false,
});
if (nativeResult?.compaction?.firstKeptEntryId !== "kept-user" || !nativeResult.compaction.summary.includes("old request")) {
  throw new Error("candidate package did not preserve the host native retained entry");
}

const splitResult = await packageHandlers.session_before_compact({
  preparation: preparation({ messagesToSummarize: [user("old request")], turnPrefixMessages: [toolCall("tc-1")], firstKeptEntryId: "kept-result", isSplitTurn: true }),
  branchEntries: [messageEntry("old-user", user("old request")), messageEntry("prefix-call", toolCall("tc-1")), messageEntry("kept-result", toolResult("tc-1"))],
  reason: "overflow",
  willRetry: true,
});
if (splitResult?.compaction?.firstKeptEntryId !== "kept-result" || splitResult.compaction.details.sourceMessageCount !== 2) {
  throw new Error("candidate package did not preserve the native split-turn prefix and tool pairing");
}

const explicitKeepResult = await packageHandlers.session_before_compact({
  preparation: preparation({ messagesToSummarize: [user("host native prefix")] }),
  branchEntries: [
    messageEntry("u1", user("first")), messageEntry("a1", assistant("first answer")),
    messageEntry("u2", user("second")), messageEntry("a2", assistant("second answer")),
    messageEntry("u3", user("third")), messageEntry("a3", assistant("third answer")),
  ],
  customInstructions: "__PI_VCC_MANUAL_BYPASS__\nkeep:1",
  reason: "manual",
});
if (explicitKeepResult?.compaction?.firstKeptEntryId !== "u3" || !explicitKeepResult.compaction.summary.includes("second answer")) {
  throw new Error("candidate package did not honor explicit keep:1");
}
if (!packageModule.isLegacyContinuationMessage({ customType: "pi-vcc-continuation" }) || packageModule.isLegacyContinuationMessage({ customType: "other" })) {
  throw new Error("candidate package legacy continuation classifier is incorrect");
}

const packageResults = [
  { name: "package-native-retention", firstKeptEntryId: nativeResult.compaction.firstKeptEntryId },
  { name: "package-split-turn", firstKeptEntryId: splitResult.compaction.firstKeptEntryId },
  { name: "package-explicit-keep", firstKeptEntryId: explicitKeepResult.compaction.firstKeptEntryId },
];
const results = [...extensionResults, ...packageResults];
writeFileSync(join(artifactRoot, "sessions", "settled-run.jsonl"), `${JSON.stringify({ type: "integration", results })}\n`);
writeFileSync(join(artifactRoot, "logs", "pi-vcc.jsonl"), `${JSON.stringify({ event: "settled_run_integration", candidate: candidateName, results })}\n`);
console.log(`pi-vcc candidate-contract integration: PASS candidate=${candidateName} cases=${results.length}`);
