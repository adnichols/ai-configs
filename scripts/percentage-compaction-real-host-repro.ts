import {
	copyFileSync,
	existsSync,
	mkdirSync,
	mkdtempSync,
	realpathSync,
	rmSync,
	symlinkSync,
	writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const repoRoot = resolve(import.meta.dir, "..");
const candidate = process.env.PI_VCC_REPRO_PACKAGE
	? resolve(process.env.PI_VCC_REPRO_PACKAGE)
	: resolve(repoRoot, "_pi/packages/pi-vcc");
const percentageExtension = resolve(
	repoRoot,
	"_pi/extensions/percentage-compaction.ts",
);
const piExecutable = Bun.which("pi");
const runtimeRoot = process.env.PI_VCC_REPRO_PI_RUNTIME
	? realpathSync(resolve(process.env.PI_VCC_REPRO_PI_RUNTIME))
	: piExecutable
		? dirname(dirname(realpathSync(piExecutable)))
		: undefined;
if (!runtimeRoot || !existsSync(join(runtimeRoot, "dist/index.js"))) {
	throw new Error("Unable to resolve the installed Pi runtime package");
}

const dependencyRoot = existsSync(
	join(runtimeRoot, "node_modules", "@earendil-works/pi-ai/dist/providers/faux.js"),
)
	? join(runtimeRoot, "node_modules")
	: resolve(runtimeRoot, "../..", "node_modules");
const runtime = await import(
	pathToFileURL(join(runtimeRoot, "dist/index.js")).href
);
const faux = await import(
	pathToFileURL(
		join(dependencyRoot, "@earendil-works/pi-ai/dist/providers/faux.js"),
	).href
);
const typebox = await import(
	pathToFileURL(join(dependencyRoot, "typebox/build/index.mjs")).href
);

async function runGrokContextCeilingScenario(): Promise<void> {
	const root = mkdtempSync(join(tmpdir(), "grok-context-ceiling-real-host-"));
	let session: any;
	try {
	const sessionDir = join(root, "sessions");
	const agentDir = join(root, "agent");
	mkdirSync(sessionDir, { recursive: true });
	mkdirSync(agentDir, { recursive: true });
	writeFileSync(
		join(agentDir, "settings.json"),
		JSON.stringify({
			packages: [candidate],
			extensions: [percentageExtension],
			compaction: { enabled: true, keepRecentTokens: 1 },
		}),
	);
	process.env.PI_VCC_STANDALONE_CONTINUATION_AUTHORITY = "coordinator";
	process.env.PI_VCC_LOG_PATH = join(root, "pi-vcc.jsonl");

	const core = faux.createFauxCore({
		api: "opencode",
		provider: "opencode",
		models: [
			{
				id: "grok-4.5",
				name: "Grok 4.5 real-host repro",
				reasoning: false,
				input: ["text"],
				cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
				contextWindow: 500_000,
				maxTokens: 8_192,
			},
		],
		tokensPerSecond: 1_000_000,
	});
	const modelRuntime = await runtime.ModelRuntime.create({ modelsPath: null, allowModelNetwork: false });
	void modelRuntime.setRuntimeApiKey(core.provider, "deterministic-no-network-key", { allowNetwork: false });
	modelRuntime.registerProvider(core.provider, {
		api: core.api,
		baseUrl: "http://127.0.0.1:0",
		apiKey: "deterministic-no-network-key",
		streamSimple: core.streamSimple,
		models: core.models,
	});
	const sessionManager = runtime.SessionManager.create(root, sessionDir);
	const now = Date.now();
	const usage = { input: 180_000, output: 0, cacheRead: 0, cacheWrite: 0, totalTokens: 180_000, cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 } };
	for (let index = 0; index < 2; index += 1) {
		sessionManager.appendMessage({ role: "user", content: [{ type: "text", text: `Earlier Grok history ${index}` }], timestamp: now + index * 2 - 1 });
		sessionManager.appendMessage({ ...faux.fauxAssistantMessage(`Earlier Grok history ${index} complete.`), api: core.api, provider: core.provider, model: core.getModel().id, timestamp: now + index * 2 });
	}
	sessionManager.appendMessage({ role: "user", content: [{ type: "text", text: "Large Grok history" }], timestamp: now + 4 });
	sessionManager.appendMessage({ ...faux.fauxAssistantMessage("Large Grok history complete."), api: core.api, provider: core.provider, model: core.getModel().id, usage, timestamp: now + 5 });
	const createdSession = await runtime.createAgentSession({ cwd: root, agentDir, model: core.getModel(), modelRuntime, sessionManager, noTools: "all" });
	session = createdSession.session;
	const providerSamples: number[] = [];
	const policyModulePath = join(root, "grok-context-ceiling-policy.ts");
	const policyDependencyPath = join(root, "node_modules", "@earendil-works");
	mkdirSync(policyDependencyPath, { recursive: true });
	symlinkSync(
		join(dependencyRoot, "@earendil-works", "pi-agent-core"),
		join(policyDependencyPath, "pi-agent-core"),
	);
	copyFileSync(
		join(repoRoot, "_pi", "lib", "grok-context-ceiling-policy.ts"),
		policyModulePath,
	);
	const policy = await import(pathToFileURL(policyModulePath).href);
	const triggerText = "Continue with the Grok request.";
	const triggerMessage = {
		role: "user" as const,
		content: [{ type: "text" as const, text: triggerText }],
		timestamp: Date.now(),
	};
	const estimateTriggerRequest = () =>
		policy.estimateGrokProviderRequestTokens({
			messages: [...session.agent.state.messages, triggerMessage],
			systemPrompt: session.systemPrompt,
			tools: session.agent.state.tools,
		});
	usage.totalTokens += 180_000 - estimateTriggerRequest();
	usage.input = usage.totalTokens;
	const triggerEstimate = estimateTriggerRequest();
	if (triggerEstimate !== 180_000) {
		throw new Error(`Could not seed the exact Grok trigger: ${triggerEstimate}`);
	}
	core.setResponses([
		(context: any) => {
			const tokens = policy.estimateGrokProviderRequestTokens(context);
			providerSamples.push(tokens);
			if (tokens >= 200_000) throw new Error(`Provider ceiling exceeded: ${tokens}`);
			return faux.fauxAssistantMessage("Grok ceiling compaction succeeded.");
		},
	]);

		await session.prompt(triggerText);
		if (!sessionManager.getBranch().some((entry: any) => entry.type === "compaction")) {
			throw new Error("Grok request did not produce a context-ceiling compaction");
		}
		if (providerSamples.length !== 1 || providerSamples.some((tokens) => tokens >= 200_000)) {
			throw new Error(`Grok request reached the provider ceiling: ${JSON.stringify(providerSamples)}`);
		}

		const callsBeforeFailClosedCase = providerSamples.length;
		await session.prompt("s".repeat(800_000));
		if (providerSamples.length !== callsBeforeFailClosedCase) {
			throw new Error("Grok ceiling fallback dispatched an uncompactable provider request");
		}
		if (!session.agent.state.errorMessage?.includes("Grok 4.5 context ceiling")) {
			throw new Error(`Missing actionable Grok ceiling error: ${session.agent.state.errorMessage}`);
		}
		console.log(JSON.stringify({ root, triggerEstimate, providerSamples, failClosed: true }, null, 2));
	} finally {
		session?.dispose();
		if (process.env.KEEP_PERCENTAGE_COMPACTION_REPRO !== "1") rmSync(root, { recursive: true, force: true });
	}
}

const grokContextCeilingScenario =
	process.argv.includes("--scenario=grok-4-5-ceiling") ||
	process.argv[process.argv.indexOf("--scenario") + 1] === "grok-4-5-ceiling";
if (grokContextCeilingScenario) {
	await runGrokContextCeilingScenario();
	process.exit(0);
}

const root = mkdtempSync(join(tmpdir(), "percentage-compaction-real-host-"));
const sessionDir = join(root, "sessions");
const agentDir = join(root, "agent");
mkdirSync(sessionDir, { recursive: true });
mkdirSync(agentDir, { recursive: true });
writeFileSync(
	join(agentDir, "settings.json"),
	JSON.stringify({
		packages: [candidate],
		extensions: [percentageExtension],
	}),
);
process.env.PI_VCC_STANDALONE_CONTINUATION_AUTHORITY = "coordinator";
process.env.PI_VCC_LOG_PATH = join(root, "pi-vcc.jsonl");

const contextWindow = 100_000;
const providerFailurePercent = 96;
const core = faux.createFauxCore({
	api: "percentage-compaction-repro-api",
	provider: "percentage-compaction-repro-provider",
	models: [
		{
			id: "percentage-compaction-repro-model",
			name: "Percentage compaction real-host repro",
			reasoning: false,
			input: ["text"],
			cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
			contextWindow,
			maxTokens: 1_000,
		},
	],
	tokensPerSecond: 1_000_000,
});
const modelRuntime = await runtime.ModelRuntime.create({
	modelsPath: null,
	allowModelNetwork: false,
});
await modelRuntime.setRuntimeApiKey(
	core.provider,
	"deterministic-no-network-key",
);
modelRuntime.registerProvider(core.provider, {
	api: core.api,
	baseUrl: "http://127.0.0.1:0",
	apiKey: "deterministic-no-network-key",
	streamSimple: core.streamSimple,
	models: core.models,
});

const estimateContextTokens = (context: any) =>
	Math.ceil(
		JSON.stringify({
			systemPrompt: context.systemPrompt,
			messages: context.messages,
			tools: context.tools,
		}).length / 4,
	);

const providerErrors: Array<{
	call: number;
	estimatedTokens: number;
	compactionsAtFailure: number;
}> = [];
const providerContextSamples: Array<{
	call: number;
	estimatedTokens: number;
	compactions: number;
}> = [];
let toolExecutions = 0;
const sessionManager = runtime.SessionManager.create(root, sessionDir);
const primingUsage = {
	input: 90_000,
	output: 10,
	cacheRead: 0,
	cacheWrite: 0,
	totalTokens: 90_010,
	cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
};
sessionManager.appendMessage({
	role: "user",
	content: [{ type: "text", text: "Build a large deterministic tool history." }],
	timestamp: Date.now(),
});
for (let index = 0; index < 25; index += 1) {
	const toolCallId = `prime-tool-${index + 1}`;
	sessionManager.appendMessage({
		...faux.fauxAssistantMessage(
			[
				faux.fauxToolCall(
					"long_horizon_tool",
					{ turn: -(index + 1) },
					{ id: toolCallId },
				),
			],
			{ stopReason: "toolUse" },
		),
		api: core.api,
		provider: core.provider,
		model: core.getModel().id,
		usage: primingUsage,
		timestamp: Date.now() + index * 2 + 1,
	});
	sessionManager.appendMessage({
		role: "toolResult",
		toolCallId,
		toolName: "long_horizon_tool",
		content: [{ type: "text", text: "priming-output:" + "p".repeat(12_000) }],
		isError: false,
		timestamp: Date.now() + index * 2 + 2,
	});
}
sessionManager.appendMessage({
	role: "user",
	content: [{ type: "text", text: "Continue after the controlled baseline." }],
	timestamp: Date.now() + 100,
});
sessionManager.appendMessage({
	...faux.fauxAssistantMessage("Baseline ready."),
	api: core.api,
	provider: core.provider,
	model: core.getModel().id,
	usage: primingUsage,
	timestamp: Date.now() + 101,
});
const { session } = await runtime.createAgentSession({
	cwd: root,
	agentDir,
	model: core.getModel(),
	modelRuntime,
	sessionManager,
	tools: ["long_horizon_tool"],
	customTools: [
		{
			name: "long_horizon_tool",
			label: "long_horizon_tool",
			description: "Adds deterministic context during a long tool-driven run",
			parameters: typebox.Type.Object({ turn: typebox.Type.Number() }),
			execute: async (_id: string, params: { turn: number }) => {
				toolExecutions += 1;
				return {
					content: [
						{
							type: "text",
							text: `tool-turn-${params.turn}:` + "x".repeat(12_000),
						},
					],
					details: {},
				};
			},
		},
	],
});
session.setAutoCompactionEnabled(false);

const compactionCount = () =>
	sessionManager.getBranch().filter((entry: any) => entry.type === "compaction")
		.length;
const assistantErrors = () =>
	sessionManager
		.getBranch()
		.filter(
			(entry: any) =>
				entry.type === "message" &&
				entry.message?.role === "assistant" &&
				entry.message?.stopReason === "error",
		);
const assistantText = (entry: any) =>
	Array.isArray(entry?.message?.content)
		? entry.message.content
				.filter((part: any) => part?.type === "text")
				.map((part: any) => part.text)
				.join("")
		: "";
const longRunCompleted = () =>
	sessionManager
		.getBranch()
		.some(
			(entry: any) =>
				entry.type === "message" &&
				entry.message?.role === "assistant" &&
				entry.message?.stopReason === "stop" &&
				assistantText(entry).includes("long run complete"),
		);
const userText = (entry: any) =>
	Array.isArray(entry?.message?.content)
		? entry.message.content
				.filter((part: any) => part?.type === "text")
				.map((part: any) => part.text)
				.join("")
		: typeof entry?.message?.content === "string"
			? entry.message.content
			: "";
const waitFor = async (description: string, predicate: () => boolean) => {
	const deadline = Date.now() + 3_000;
	while (Date.now() < deadline) {
		if (predicate()) return;
		await Bun.sleep(10);
	}
	throw new Error(`Timed out waiting for ${description}`);
};

try {
	const longRunResponses = Array.from({ length: 100 }, (_, index) =>
		(context: any, _options: any, state: { callCount: number }) => {
			const estimatedTokens = estimateContextTokens(context);
			providerContextSamples.push({
				call: state.callCount,
				estimatedTokens,
				compactions: compactionCount(),
			});
			if (
				estimatedTokens >=
				(contextWindow * providerFailurePercent) / 100
			) {
				providerErrors.push({
					call: state.callCount,
					estimatedTokens,
					compactionsAtFailure: compactionCount(),
				});
				return faux.fauxAssistantMessage([], {
					stopReason: "error",
					errorMessage: "context_too_large: deterministic real-host repro",
				});
			}
			if (index >= 75) return faux.fauxAssistantMessage("long run complete");
			return faux.fauxAssistantMessage(
				[
					faux.fauxToolCall(
						"long_horizon_tool",
						{ turn: index + 1 },
						{ id: `long-tool-${index + 1}` },
					),
				],
				{ stopReason: "toolUse" },
			);
		},
	);
	core.setResponses(longRunResponses);

	const piVccCommand = session._extensionRunner.getCommand("pi-vcc");
	if (!piVccCommand) throw new Error("pi-vcc command was not registered");
	await piVccCommand.handler(
		"Continue the deterministic long tool-driven run.",
		session._extensionRunner.createCommandContext(),
	);
	await waitFor("controlled baseline compaction", () => compactionCount() === 1);
	await waitFor(
		"provider overflow or successful long-run completion",
		() =>
			providerErrors.length > 0 ||
			(longRunCompleted() && !session.isStreaming && !session.isCompacting),
	);
	const finalBranch = sessionManager.getBranch();
	const followUpIndex = finalBranch.findIndex(
		(entry: any) =>
			entry.type === "message" &&
			entry.message?.role === "user" &&
			userText(entry).includes("Continue the deterministic long tool-driven run."),
	);
	const oversizedTurnCompactionIndex = finalBranch.findIndex(
		(entry: any, index: number) =>
			index > followUpIndex && entry.type === "compaction",
	);
	const oversizedTurnCompaction = finalBranch[oversizedTurnCompactionIndex];
	const oversizedTurnFirstKeptIndex = finalBranch.findIndex(
		(entry: any) => entry.id === oversizedTurnCompaction?.firstKeptEntryId,
	);
	const firstPostOversizedCompactionSample = providerContextSamples.find(
		(sample) => sample.compactions >= 2,
	);
	const result = {
		root,
		toolExecutions,
		compactions: compactionCount(),
		oversizedTurnCut: {
			followUpIndex,
			compactionIndex: oversizedTurnCompactionIndex,
			firstKeptIndex: oversizedTurnFirstKeptIndex,
			firstKeptEntryId: oversizedTurnCompaction?.firstKeptEntryId,
		},
		firstPostOversizedCompactionSample,
		providerErrors,
		assistantErrors: assistantErrors().map((entry: any) =>
			entry.message.errorMessage,
		),
		usage: session.getContextUsage(),
	};
	console.log(JSON.stringify(result, null, 2));
	if (providerErrors.length > 0) {
		if (process.env.KEEP_PERCENTAGE_COMPACTION_REPRO !== "1") {
			rmSync(root, { recursive: true, force: true });
		}
		process.exit(1);
	}
	if (!longRunCompleted()) throw new Error("Long run never reached terminal stop");
	if (followUpIndex < 0) throw new Error("Long-run follow-up user turn was not persisted");
	if (oversizedTurnCompactionIndex < 0)
		throw new Error("The oversized user turn was never compacted");
	if (oversizedTurnFirstKeptIndex <= followUpIndex)
		throw new Error(
			"Oversized user turn compaction retained the entire active turn instead of splitting it",
		);
	if (!firstPostOversizedCompactionSample)
		throw new Error("No provider response followed the oversized-turn compaction");
	if (firstPostOversizedCompactionSample.estimatedTokens >= contextWindow * 0.4)
		throw new Error(
			`Oversized-turn compaction retained too much context: ${firstPostOversizedCompactionSample.estimatedTokens}`,
		);
	if (assistantErrors().length > 0)
		throw new Error("Long run persisted an assistant error");
	if (toolExecutions < 70)
		throw new Error(`Long run was too short: ${toolExecutions} tool executions`);
	if (compactionCount() < 3 || compactionCount() > 4)
		throw new Error(
			`Unexpected compaction count for deterministic run: ${compactionCount()}`,
		);
	const finalUsage = session.getContextUsage();
	if (finalUsage?.percent === null || finalUsage?.percent === undefined)
		throw new Error("Final context usage was unavailable");
	if (finalUsage.percent >= 80)
		throw new Error(`Final context usage exceeded hard backstop: ${finalUsage.percent}`);
} finally {
	session.dispose();
	if (process.env.KEEP_PERCENTAGE_COMPACTION_REPRO !== "1") {
		rmSync(root, { recursive: true, force: true });
	}
}
