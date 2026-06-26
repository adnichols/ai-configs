import { access, readFile } from "node:fs/promises";
import { homedir } from "node:os";
import { isAbsolute, relative, resolve } from "node:path";
import type { ExtensionAPI, ExtensionCommandContext, ExtensionContext } from "@mariozechner/pi-coding-agent";

const PLAN_STATE_TYPE = "aplan-mode-state";
const PLAN_ROOT = "thoughts";
const PLAN_DIRECTORY = "thoughts/plans";
const PLAN_COMMANDS_DIRECTORIES = ["_omp/commands", ".omp/commands"] as const;
const GLOBAL_COMMANDS_DIRECTORY = resolve(homedir(), ".omp/agent/commands");
const EXECUTE_PLAN_COMMAND = "cmd:execute-plan";
const STANDARD_PLAN_REVIEW_COMMAND = "review:plan";
const ADVERSARIAL_PLAN_REVIEW_COMMAND = "review:plan-adversarial";
const CHANGE_REVIEW_INTEGRATE_COMMAND = "review:change-integrate";
const MAX_REVIEW_CYCLES = 3;

const DESTRUCTIVE_PATTERNS = [
	/\brm\b/i,
	/\brmdir\b/i,
	/\bmv\b/i,
	/\bcp\b/i,
	/\bmkdir\b/i,
	/\btouch\b/i,
	/\bchmod\b/i,
	/\bchown\b/i,
	/\bchgrp\b/i,
	/\bln\b/i,
	/\btee\b/i,
	/\btruncate\b/i,
	/\bdd\b/i,
	/\bshred\b/i,
	/(^|[^<])>(?!>)/,
	/>>/,
	/\bnpm\s+(install|uninstall|update|ci|link|publish)/i,
	/\byarn\s+(add|remove|install|publish)/i,
	/\bpnpm\s+(add|remove|install|publish)/i,
	/\bpip\s+(install|uninstall)/i,
	/\bapt(-get)?\s+(install|remove|purge|update|upgrade)/i,
	/\bbrew\s+(install|uninstall|upgrade)/i,
	/\bgit\s+(add|commit|push|pull|merge|rebase|reset|checkout|branch\s+-[dD]|stash|cherry-pick|revert|tag|init|clone)/i,
	/\bsudo\b/i,
	/\bsu\b/i,
	/\bkill\b/i,
	/\bpkill\b/i,
	/\bkillall\b/i,
	/\breboot\b/i,
	/\bshutdown\b/i,
	/\bsystemctl\s+(start|stop|restart|enable|disable)/i,
	/\bservice\s+\S+\s+(start|stop|restart)/i,
	/\b(vim?|nano|emacs|code|subl)\b/i,
];

const SAFE_BASH_PATTERNS = [
	/^\s*cat\b/,
	/^\s*head\b/,
	/^\s*tail\b/,
	/^\s*less\b/,
	/^\s*more\b/,
	/^\s*grep\b/,
	/^\s*find\b/,
	/^\s*ls\b/,
	/^\s*pwd\b/,
	/^\s*echo\b/,
	/^\s*printf\b/,
	/^\s*wc\b/,
	/^\s*sort\b/,
	/^\s*uniq\b/,
	/^\s*diff\b/,
	/^\s*file\b/,
	/^\s*stat\b/,
	/^\s*du\b/,
	/^\s*df\b/,
	/^\s*tree\b/,
	/^\s*which\b/,
	/^\s*whereis\b/,
	/^\s*type\b/,
	/^\s*env\b/,
	/^\s*printenv\b/,
	/^\s*uname\b/,
	/^\s*whoami\b/,
	/^\s*id\b/,
	/^\s*date\b/,
	/^\s*cal\b/,
	/^\s*uptime\b/,
	/^\s*ps\b/,
	/^\s*top\b/,
	/^\s*htop\b/,
	/^\s*free\b/,
	/^\s*git\s+(status|log|diff|show|branch|remote|config\s+--get)/i,
	/^\s*git\s+ls-/i,
	/^\s*npm\s+(list|ls|view|info|search|outdated|audit)/i,
	/^\s*yarn\s+(list|info|why|audit)/i,
	/^\s*pnpm\s+(list|why|outdated|audit)/i,
	/^\s*node\s+--version/i,
	/^\s*python\s+--version/i,
	/^\s*python3\s+--version/i,
	/^\s*curl\s/i,
	/^\s*wget\s+-O\s*-/i,
	/^\s*jq\b/,
	/^\s*sed\s+-n/i,
	/^\s*awk\b/,
	/^\s*rg\b/,
	/^\s*fd\b/,
	/^\s*bat\b/,
	/^\s*exa\b/,
];

const DEFAULT_PLAN_TOOLS = [
	"read",
	"bash",
	"grep",
	"find",
	"ls",
	"edit",
	"write",
	"todo",
	"lsp",
	"web_search",
	"fetch_content",
	"get_search_content",
	"question",
	"questionnaire",
] as const;

const REVIEW_ORCHESTRATION_TOOLS = [
	"subagent",
	"Agent",
	"get_subagent_result",
	"steer_subagent",
	"process",
] as const;

interface PlanModeState {
	enabled: boolean;
	currentPlanPath?: string;
	savedActiveTools?: string[];
	reviewCycles: number;
	lastReviewCommand?: string;
}

function stripPathSigil(inputPath: string): string {
	return inputPath.startsWith("@") ? inputPath.slice(1) : inputPath;
}

function resolveFromCwd(cwd: string, inputPath: string): string {
	const normalized = stripPathSigil(inputPath);
	return isAbsolute(normalized) ? normalized : resolve(cwd, normalized);
}

function isWithin(parent: string, child: string): boolean {
	const rel = relative(parent, child);
	return rel === "" || (!rel.startsWith("..") && !isAbsolute(rel));
}

function relativeToCwd(cwd: string, inputPath: string): string {
	return relative(cwd, resolveFromCwd(cwd, inputPath));
}

function isSafeCommand(command: string): boolean {
	const destructive = DESTRUCTIVE_PATTERNS.some((pattern) => pattern.test(command));
	const safe = SAFE_BASH_PATTERNS.some((pattern) => pattern.test(command));
	return !destructive && safe;
}

function stripFrontmatter(content: string): string {
	if (!content.startsWith("---\n")) return content;
	const end = content.indexOf("\n---\n", 4);
	return end === -1 ? content : content.slice(end + 5);
}

function parseCommandArgs(argsString: string): string[] {
	const args: string[] = [];
	let current = "";
	let inQuote: string | null = null;

	for (let i = 0; i < argsString.length; i += 1) {
		const char = argsString[i];

		if (inQuote) {
			if (char === inQuote) {
				inQuote = null;
			} else {
				current += char;
			}
		} else if (char === '"' || char === "'") {
			inQuote = char;
		} else if (char === " " || char === "\t") {
			if (current) {
				args.push(current);
				current = "";
			}
		} else {
			current += char;
		}
	}

	if (current) {
		args.push(current);
	}

	return args;
}

function substituteCommandArgs(content: string, args: string[]): string {
	let result = content.replace(/\$(\d+)/g, (_, num: string) => {
		const index = Number.parseInt(num, 10) - 1;
		return args[index] ?? "";
	});

	result = result.replace(/\$@\[(\d+)(?::(\d*)?)?\]/g, (_, startRaw: string, lengthRaw?: string) => {
		const start = Number.parseInt(startRaw, 10);
		if (!Number.isFinite(start) || start < 1) return "";

		const startIndex = start - 1;
		if (startIndex >= args.length) return "";
		if (lengthRaw === undefined || lengthRaw === "") {
			return args.slice(startIndex).join(" ");
		}

		const length = Number.parseInt(lengthRaw, 10);
		if (!Number.isFinite(length) || length <= 0) return "";
		return args.slice(startIndex, startIndex + length).join(" ");
	});

	const allArgs = args.join(" ");
	result = result.replaceAll("$ARGUMENTS", allArgs);
	result = result.replaceAll("$@", allArgs);
	return result;
}

async function expandSlashCommandPrompt(cwd: string, commandText: string): Promise<string | undefined> {
	if (!commandText.startsWith("/")) return undefined;

	const spaceIndex = commandText.indexOf(" ");
	const commandName = spaceIndex === -1 ? commandText.slice(1) : commandText.slice(1, spaceIndex);
	const argsString = spaceIndex === -1 ? "" : commandText.slice(spaceIndex + 1);
	const candidatePaths = [
		...PLAN_COMMANDS_DIRECTORIES.map((directory) => resolve(cwd, directory, `${commandName}.md`)),
		resolve(GLOBAL_COMMANDS_DIRECTORY, `${commandName}.md`),
	];

	for (const candidatePath of candidatePaths) {
		try {
			const template = stripFrontmatter(await readFile(candidatePath, "utf8"));
			return substituteCommandArgs(template, parseCommandArgs(argsString));
		} catch {
			// Ignore missing command files and continue searching fallback locations.
		}
	}

	return undefined;
}

function normalizeExecuteTarget(target: string | undefined): "dev:run" | "run-plan" | undefined {
	if (!target) return undefined;
	const normalized = target.trim().replace(/^\//, "");
	if (normalized === "dev:run") return normalized;
	if (normalized === "run-plan" || normalized === "skill:run-plan") return "run-plan";
	return undefined;
}

function getExecutePlanUsage(): string {
	return `Usage: /${EXECUTE_PLAN_COMMAND} <plan slug | thoughts/plans/<slug>.md | path/to/plan.md> [--target dev:run|run-plan]`;
}

async function resolveExecutePlanRequest(
	cwd: string,
	rawArgs: string,
): Promise<
	| { planDispatchArgument: string; planPath: string; targetOverride?: "dev:run" | "run-plan" }
	| { error: string }
> {
	const tokens = parseCommandArgs(rawArgs.trim());
	if (tokens.length === 0) {
		return { error: getExecutePlanUsage() };
	}

	const targetFlagIndex = tokens.lastIndexOf("--target");
	let planTokens = tokens;
	let targetOverride: "dev:run" | "run-plan" | undefined;

	if (targetFlagIndex !== -1) {
		if (targetFlagIndex === tokens.length - 1) {
			return { error: "Missing value after --target. Valid targets: /dev:run or /run-plan." };
		}
		if (targetFlagIndex < tokens.length - 2) {
			return { error: "Unexpected extra arguments after --target. Use exactly one target value." };
		}

		targetOverride = normalizeExecuteTarget(tokens[targetFlagIndex + 1]);
		if (!targetOverride) {
			return { error: "Invalid --target value. Valid targets: /dev:run or /run-plan." };
		}
		planTokens = tokens.slice(0, targetFlagIndex);
	}

	const planArgument = planTokens.join(" ").trim();
	if (!planArgument) {
		return { error: getExecutePlanUsage() };
	}

	const planDispatchArgument = stripPathSigil(planArgument);
	const planPath = planDispatchArgument.endsWith(".md")
		? resolveFromCwd(cwd, planDispatchArgument)
		: resolve(cwd, PLAN_DIRECTORY, `${planDispatchArgument}.md`);

	try {
		await access(planPath);
	} catch {
		return {
			error: `Reviewed plan not found: ${planPath}. /${EXECUTE_PLAN_COMMAND} requires an explicit existing reviewed plan file or slug.`,
		};
	}

	return { planDispatchArgument, planPath, targetOverride };
}

function formatCommandArg(arg: string): string {
	return /\s/.test(arg) ? JSON.stringify(arg) : arg;
}

function formatNextSteps(commands: readonly string[]): string {
	return commands.join("\n");
}

function getThoughtsRoot(cwd: string): string {
	return resolve(cwd, PLAN_ROOT);
}

function getPlansRoot(cwd: string): string {
	return resolve(cwd, PLAN_DIRECTORY);
}

function isThoughtsPath(cwd: string, inputPath: string): boolean {
	return isWithin(getThoughtsRoot(cwd), resolveFromCwd(cwd, inputPath));
}

function isPlanFilePath(cwd: string, inputPath: string): boolean {
	const resolved = resolveFromCwd(cwd, inputPath);
	return isWithin(getPlansRoot(cwd), resolved) && resolved.endsWith(".md");
}

function derivePlanTools(allTools: string[], normalTools: string[] | undefined, includeReviewTools: boolean): string[] {
	const desired = new Set<string>(DEFAULT_PLAN_TOOLS);
	if (includeReviewTools) {
		for (const toolName of REVIEW_ORCHESTRATION_TOOLS) {
			desired.add(toolName);
		}
	}

	const orderedSource = normalTools && normalTools.length > 0 ? normalTools : allTools;
	const selected = orderedSource.filter((tool) => desired.has(tool));

	for (const required of desired) {
		if (allTools.includes(required) && !selected.includes(required)) {
			selected.push(required);
		}
	}

	return selected;
}

function buildAplanBootstrapPrompt(userArgs: string): string {
	const workflow = [
		"Use the repo-managed OMP planning workflow for this repository.",
		`Keep plan files under ${PLAN_DIRECTORY}/ as single markdown plan documents.`,
		`After materially updating a plan, run /${STANDARD_PLAN_REVIEW_COMMAND} on that file, integrate any inline review comments back into the same plan with /${CHANGE_REVIEW_INTEGRATE_COMMAND}, and optionally run /${ADVERSARIAL_PLAN_REVIEW_COMMAND} for a challenge pass.`,
		`When the reviewed plan is ready for implementation, hand execution off through /${EXECUTE_PLAN_COMMAND} to /run-plan or /dev:run.`,
	].join(" ");

	if (!userArgs) {
		return workflow;
	}

	return `${workflow}\n\nUser request: ${userArgs}`;
}

export default function aplanModeExtension(pi: ExtensionAPI): void {
	let planModeEnabled = false;
	let currentPlanPath: string | undefined;
	let savedActiveTools: string[] | undefined;
	let reviewCycles = 0;
	let reviewInFlight = false;
	let pendingAutoReviewCommand = false;
	let lastReviewCommand: string | undefined;
	let turnTouchedPlan = false;

	function getAllToolNames(): string[] {
		return pi.getAllTools().map((tool) => tool.name);
	}

	function persistState(): void {
		pi.appendEntry(PLAN_STATE_TYPE, {
			enabled: planModeEnabled,
			currentPlanPath,
			savedActiveTools,
			reviewCycles,
			lastReviewCommand,
		} satisfies PlanModeState);
	}

	function updateUi(ctx: ExtensionContext): void {
		if (!planModeEnabled) {
			ctx.ui.setStatus("aplan-mode", undefined);
			ctx.ui.setWidget("aplan-mode", undefined);
			return;
		}

		const planLabel = currentPlanPath ?? "no plan file yet";
		const displayedCycles = Math.min(reviewCycles, MAX_REVIEW_CYCLES);
		const cycleLabel = reviewCycles > 0 ? ` • review ${displayedCycles}/${MAX_REVIEW_CYCLES}` : "";
		const status = reviewInFlight ? `🧪 /aplan${cycleLabel}` : `📝 /aplan${cycleLabel}`;
		ctx.ui.setStatus("aplan-mode", ctx.ui.theme.fg("accent", status));
		ctx.ui.setWidget("aplan-mode", [
			ctx.ui.theme.fg("accent", "/aplan active"),
			ctx.ui.theme.fg("muted", `Current plan: ${planLabel}`),
			ctx.ui.theme.fg("muted", `Writes allowed only under ${PLAN_ROOT}/`),
		]);
	}

	function applyPlanTools(includeReviewTools = false): void {
		const allTools = getAllToolNames();
		pi.setActiveTools(derivePlanTools(allTools, savedActiveTools, includeReviewTools));
	}

	function enablePlanMode(ctx: ExtensionContext): void {
		if (!planModeEnabled) {
			savedActiveTools = pi.getActiveTools();
		}
		planModeEnabled = true;
		reviewInFlight = false;
		pendingAutoReviewCommand = false;
		lastReviewCommand = undefined;
		turnTouchedPlan = false;
		applyPlanTools(false);
		updateUi(ctx);
		persistState();

		const planNote = currentPlanPath ? ` Current plan: ${currentPlanPath}` : "";
		ctx.ui.notify(`/aplan enabled.${planNote}`, "info");
	}

	function disablePlanMode(ctx: ExtensionContext): void {
		planModeEnabled = false;
		reviewInFlight = false;
		pendingAutoReviewCommand = false;
		lastReviewCommand = undefined;
		turnTouchedPlan = false;
		if (savedActiveTools && savedActiveTools.length > 0) {
			pi.setActiveTools(savedActiveTools);
		}
		updateUi(ctx);
		persistState();
		const planNote = currentPlanPath ? ` Current plan preserved: ${currentPlanPath}` : "";
		ctx.ui.notify(`/aplan disabled.${planNote}`, "info");
	}

	function togglePlanMode(ctx: ExtensionContext): void {
		if (planModeEnabled) {
			disablePlanMode(ctx);
		} else {
			enablePlanMode(ctx);
		}
	}

	async function dispatchSlashCommandPrompt(ctx: ExtensionContext, commandText: string): Promise<void> {
		const expandedPrompt = await expandSlashCommandPrompt(ctx.cwd, commandText);
		pi.sendUserMessage(expandedPrompt ?? commandText);
	}

	async function handleExecutePlanCommand(args: string, ctx: ExtensionCommandContext): Promise<void> {
		const request = await resolveExecutePlanRequest(ctx.cwd, args);
		if ("error" in request) {
			ctx.ui.notify(request.error, "warning");
			return;
		}

		let target = request.targetOverride;
		if (!target) {
			if (!ctx.hasUI) {
				ctx.ui.notify("No UI available. Re-run with --target dev:run or --target run-plan.", "warning");
				return;
			}

			const choice = await ctx.ui.select(`Choose execution path for ${request.planDispatchArgument}.`, [
				`/run-plan ${request.planDispatchArgument}`,
				`/dev:run ${request.planDispatchArgument}`,
			]);
			if (!choice) {
				return;
			}
			target = choice.startsWith("/run-plan") ? "run-plan" : "dev:run";
		}

		const executionPrompt = await expandSlashCommandPrompt(ctx.cwd, `/${target} ${request.planDispatchArgument}`);
		if (!executionPrompt) {
			ctx.ui.notify(`Could not expand /${target}. Ensure the corresponding command template exists.`, "error");
			return;
		}

		if (planModeEnabled) {
			disablePlanMode(ctx);
		}

		await ctx.waitForIdle();
		const result = await ctx.newSession({ parentSession: ctx.sessionManager.getSessionFile() });
		if (result.cancelled) {
			return;
		}

		pi.sendUserMessage(executionPrompt);
	}

	async function startReviewCycle(
		ctx: ExtensionContext,
		command: string = STANDARD_PLAN_REVIEW_COMMAND,
	): Promise<void> {
		reviewInFlight = true;
		pendingAutoReviewCommand = true;
		lastReviewCommand = command;
		reviewCycles += 1;
		applyPlanTools(true);
		updateUi(ctx);
		persistState();
		await dispatchSlashCommandPrompt(ctx, `/${command} ${currentPlanPath}`);
	}

	async function startReviewIntegration(ctx: ExtensionContext, options?: { automatic?: boolean }): Promise<void> {
		if (!currentPlanPath) return;
		reviewInFlight = true;
		pendingAutoReviewCommand = false;
		lastReviewCommand = CHANGE_REVIEW_INTEGRATE_COMMAND;
		applyPlanTools(false);
		updateUi(ctx);
		persistState();
		if (options?.automatic) {
			ctx.ui.notify(
				`/${STANDARD_PLAN_REVIEW_COMMAND} completed for ${currentPlanPath}. Automatically running /${CHANGE_REVIEW_INTEGRATE_COMMAND}.`,
				"info",
			);
		}
		await dispatchSlashCommandPrompt(ctx, `/${CHANGE_REVIEW_INTEGRATE_COMMAND} ${formatCommandArg(currentPlanPath)}`);
	}

	async function planHasInlineReviewComments(planPath: string, ctx: ExtensionContext): Promise<boolean> {
		try {
			const content = await readFile(resolveFromCwd(ctx.cwd, planPath), "utf8");
			return /\[REVIEW(?::[^\]]+)?\][\s\S]*?\[\/REVIEW\]/.test(content);
		} catch {
			return false;
		}
	}

	async function hydrateState(ctx: ExtensionContext): Promise<void> {
		planModeEnabled = false;
		reviewInFlight = false;
		pendingAutoReviewCommand = false;
		currentPlanPath = undefined;
		savedActiveTools = undefined;
		reviewCycles = 0;
		lastReviewCommand = undefined;
		turnTouchedPlan = false;

		const stateEntry = ctx.sessionManager
			.getEntries()
			.filter((entry: { type: string; customType?: string }) => entry.type === "custom" && entry.customType === PLAN_STATE_TYPE)
			.pop() as { data?: PlanModeState } | undefined;

		if (stateEntry?.data) {
			planModeEnabled = stateEntry.data.enabled;
			currentPlanPath = stateEntry.data.currentPlanPath;
			savedActiveTools = stateEntry.data.savedActiveTools;
			reviewCycles = stateEntry.data.reviewCycles ?? 0;
			lastReviewCommand = stateEntry.data.lastReviewCommand;
		}

		if (currentPlanPath) {
			try {
				await access(resolve(ctx.cwd, currentPlanPath));
			} catch {
				currentPlanPath = undefined;
				reviewCycles = 0;
				lastReviewCommand = undefined;
			}
		}

		if (planModeEnabled) {
			if (!savedActiveTools || savedActiveTools.length === 0) {
				savedActiveTools = pi.getActiveTools();
			}
			applyPlanTools(false);
		} else if (savedActiveTools && savedActiveTools.length > 0) {
			pi.setActiveTools(savedActiveTools);
		}

		updateUi(ctx);
	}

	async function offerReview(ctx: ExtensionContext, reason: string): Promise<void> {
		if (!planModeEnabled || !ctx.hasUI || !currentPlanPath) return;

		if (reviewCycles >= MAX_REVIEW_CYCLES) {
			ctx.ui.notify(
				`Plan review auto-loop stopped after ${MAX_REVIEW_CYCLES} cycles for ${currentPlanPath}.`,
				"warning",
			);
			updateUi(ctx);
			persistState();
			return;
		}

		ctx.ui.notify(
			`Plan updated (${reason}). Run /${STANDARD_PLAN_REVIEW_COMMAND} ${formatCommandArg(currentPlanPath)} when ready.`,
			"info",
		);
	}

	async function offerPostReviewAction(ctx: ExtensionContext, reason: string): Promise<void> {
		if (!planModeEnabled || !ctx.hasUI || !currentPlanPath) return;

		const nextSteps = [] as string[];
		if (reviewCycles < MAX_REVIEW_CYCLES) {
			nextSteps.push(`/${STANDARD_PLAN_REVIEW_COMMAND} ${formatCommandArg(currentPlanPath)}`);
		}
		if (lastReviewCommand === STANDARD_PLAN_REVIEW_COMMAND || lastReviewCommand === CHANGE_REVIEW_INTEGRATE_COMMAND) {
			nextSteps.push(`/${ADVERSARIAL_PLAN_REVIEW_COMMAND} ${formatCommandArg(currentPlanPath)}`);
		}
		nextSteps.push(
			`/${EXECUTE_PLAN_COMMAND} ${formatCommandArg(currentPlanPath)} --target dev:run`,
			`/${EXECUTE_PLAN_COMMAND} ${formatCommandArg(currentPlanPath)} --target run-plan`,
		);

		ctx.ui.notify(`Plan review complete (${reason}). Available next steps:\n${formatNextSteps(nextSteps)}`, "info");
	}

	pi.registerCommand("aplan", {
		description: "Enter built-in /plan mode and queue the repo-managed OMP planning workflow for the next planning turn",
		handler: async (_args, ctx) => {
			if (!ctx.hasUI) return;
			ctx.ui.setEditorText("/plan");
			ctx.ui.notify("/aplan enters native /plan mode. Your next planning message will get the repo-managed workflow guidance.", "info");
		},
	});

	pi.registerCommand(EXECUTE_PLAN_COMMAND, {
		description: "Start /run-plan or /dev:run in a fresh session from a reviewed plan",
		handler: async (args, ctx) => handleExecutePlanCommand(args, ctx),
	});

	pi.on("session_start", async (_event, ctx) => {
		await hydrateState(ctx);
	});

	pi.on("session_switch", async (_event, ctx) => {
		await hydrateState(ctx);
	});

	pi.on("session_fork", async (_event, ctx) => {
		await hydrateState(ctx);
	});

	pi.on("session_tree", async (_event, ctx) => {
		await hydrateState(ctx);
	});

	pi.on("input", async (event, ctx) => {
		turnTouchedPlan = false;
		const text = event.text.trim();

		if (text === "/aplan" || text.startsWith("/aplan ")) {
			const args = text.slice("/aplan".length).trim();
			pi.sendMessage(
				{
					customType: "aplan-bootstrap",
					content: buildAplanBootstrapPrompt(args),
					display: false,
					attribution: "agent",
				},
				{ deliverAs: "nextTurn" },
			);
			return { text: "/plan" };
		}

		if (!planModeEnabled) {
			return {};
		}

		if (text.startsWith("/dev:run") || text.startsWith("/run-plan")) {
			disablePlanMode(ctx);
			return {};
		}

		if (
			text.startsWith(`/${ADVERSARIAL_PLAN_REVIEW_COMMAND}`) ||
			text.startsWith(`/${STANDARD_PLAN_REVIEW_COMMAND}`) ||
			text.startsWith(`/${CHANGE_REVIEW_INTEGRATE_COMMAND}`)
		) {
			reviewInFlight = true;
			lastReviewCommand = text.startsWith(`/${ADVERSARIAL_PLAN_REVIEW_COMMAND}`)
				? ADVERSARIAL_PLAN_REVIEW_COMMAND
				: text.startsWith(`/${CHANGE_REVIEW_INTEGRATE_COMMAND}`)
					? CHANGE_REVIEW_INTEGRATE_COMMAND
					: STANDARD_PLAN_REVIEW_COMMAND;
			if (pendingAutoReviewCommand) {
				pendingAutoReviewCommand = false;
			} else if (lastReviewCommand !== CHANGE_REVIEW_INTEGRATE_COMMAND) {
				reviewCycles += 1;
			}
			if (!savedActiveTools || savedActiveTools.length === 0) {
				savedActiveTools = pi.getActiveTools();
			}
			applyPlanTools(lastReviewCommand !== CHANGE_REVIEW_INTEGRATE_COMMAND);
			updateUi(ctx);
			persistState();
		}

		return {};
	});

	pi.on("before_agent_start", async (_event) => {
		if (!planModeEnabled) return;

		const currentPlanInstruction = currentPlanPath
			? `Current plan file: ${currentPlanPath}. Continue evolving that file unless the user explicitly asks for a different one.`
			: `If you create a new plan, write it to ${PLAN_DIRECTORY}/<slug>.md.`;

		return {
			message: {
				customType: "aplan-mode-context",
				content: `[/APLAN ACTIVE]
You are in /aplan mode for this repository.

Constraints:
- Read the codebase freely.
- You may write only under ${PLAN_ROOT}/ using edit/write tools.
- Keep plan files in ${PLAN_DIRECTORY}/.
- Do not make implementation changes outside ${PLAN_ROOT}/.
- Use read-only bash commands for exploration; file mutations must go through edit/write inside ${PLAN_ROOT}/.
- Plans should align with thoughts/specs/product_intent.md and thoughts/plans/AGENTS.md when relevant.
- After creating or materially updating a plan, /review:plan <path> is available when you want review.
- After a standard review writes inline review comments into the plan, /review:change-integrate <path> runs automatically so feedback is resolved back into the same plan before any manual execution handoff.
- After standard review integration, you may optionally run /review:plan-adversarial <path> for a second-pass challenge review.
- After an integrated review completes, you may manually run /cmd:execute-plan <path> --target dev:run or --target run-plan to start a fresh execution session outside /aplan mode.
- Review feedback should be integrated back into the same plan file.
- Automatic review looping is capped at ${MAX_REVIEW_CYCLES} cycles before stopping.

${currentPlanInstruction}`,
				display: false,
			},
		};
	});

	pi.on("tool_call", async (event, ctx) => {
		if (!planModeEnabled) return;

		if (event.toolName === "bash") {
			const command = String(event.input.command ?? "");
			if (!isSafeCommand(command)) {
				return {
					block: true,
					reason: `Plan mode only allows read-only bash commands. Use edit/write within ${PLAN_ROOT}/ for plan files.`,
				};
			}
		}

		if (event.toolName === "edit" || event.toolName === "write") {
			const inputPath = typeof event.input.path === "string" ? event.input.path : "";
			if (!inputPath || !isThoughtsPath(ctx.cwd, inputPath)) {
				return {
					block: true,
					reason: `Plan mode only allows edit/write under ${PLAN_ROOT}/.`,
				};
			}
		}
	});

	pi.on("tool_result", async (event, ctx) => {
		if (!planModeEnabled || event.isError) return;
		if (event.toolName !== "edit" && event.toolName !== "write") return;

		const inputPath = typeof event.input.path === "string" ? event.input.path : undefined;
		if (!inputPath || !isPlanFilePath(ctx.cwd, inputPath)) return;

		turnTouchedPlan = true;
		currentPlanPath = relativeToCwd(ctx.cwd, inputPath);
		if (!reviewInFlight) {
			reviewCycles = 0;
			lastReviewCommand = undefined;
		}
		updateUi(ctx);
		persistState();
	});

	pi.on("agent_end", async (_event, ctx) => {
		if (!planModeEnabled) return;

		if (reviewInFlight) {
			reviewInFlight = false;
			pendingAutoReviewCommand = false;
			applyPlanTools(false);
			updateUi(ctx);
			persistState();
			if (
				lastReviewCommand === STANDARD_PLAN_REVIEW_COMMAND &&
				turnTouchedPlan &&
				currentPlanPath &&
				(await planHasInlineReviewComments(currentPlanPath, ctx))
			) {
				await startReviewIntegration(ctx, { automatic: true });
				turnTouchedPlan = false;
				return;
			}

			const reviewReason = lastReviewCommand === CHANGE_REVIEW_INTEGRATE_COMMAND
				? turnTouchedPlan
					? `review cycle ${reviewCycles} integrated`
					: `review cycle ${reviewCycles} integration completed`
				: lastReviewCommand === STANDARD_PLAN_REVIEW_COMMAND
					? `review cycle ${reviewCycles} completed`
					: turnTouchedPlan
						? `review cycle ${reviewCycles} updated the plan`
						: `review cycle ${reviewCycles} completed`;
			await offerPostReviewAction(ctx, reviewReason);
			turnTouchedPlan = false;
			return;
		}

		if (turnTouchedPlan) {
			await offerReview(ctx, "plan file updated");
		}

		turnTouchedPlan = false;
	});
}
