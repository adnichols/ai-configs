import { access, readFile, stat } from "node:fs/promises";
import { homedir } from "node:os";
import { basename, isAbsolute, relative, resolve } from "node:path";
import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";

const PRD_STATE_TYPE = "prd-mode-state";
const PLAN_STATE_TYPE = "plan-mode-state";
const PLAN_ROOT = "thoughts";
const PRD_PLANS_DIRECTORY = "thoughts/plans";
const PRD_SPECS_DIRECTORY = "thoughts/specs";
const PRD_REVIEW_ARTIFACTS_DIRECTORY = "thoughts/validation/prd-reviews";
const PRD_REVIEW_STATUS_FILENAME = "review-status.json";
const PRD_PROMPTS_DIRECTORIES = ["_pi/prompts", ".pi/prompts"] as const;
const GLOBAL_PROMPTS_DIRECTORY = resolve(homedir(), ".pi/agent/prompts");
const PRD_REVIEW_COMMAND = "review:prd";
const PRD_CLARIFY_COMMAND = "prd:clarify-round";
const DEV_PLAN_FROM_PRD_COMMAND = "dev:plan-from-prd";
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

const DEFAULT_PRD_TOOLS = [
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
	"subagent",
	"Agent",
	"get_subagent_result",
	"steer_subagent",
] as const;

const REVIEW_ORCHESTRATION_TOOLS = [
	"subagent",
	"Agent",
	"get_subagent_result",
	"steer_subagent",
	"interactive_shell",
	"process",
] as const;

interface PrdModeState {
	enabled: boolean;
	currentPrdPath?: string;
	targetSpecPaths?: string[];
	reviewCycles: number;
	reviewInFlight: boolean;
	handoffReady: boolean;
	savedActiveTools?: string[];
	lastReviewCommand?: string;
}

interface PrdReviewStatus {
	schemaVersion?: number;
	prdPath?: string;
	reviewDir?: string;
	status?: string;
	reviewersExpected?: number;
	reviewersCompleted?: number;
	integratedCount?: number;
	pendingCount?: number;
	reviewerFilesRemoved?: boolean;
	generatedAt?: string;
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
		...PRD_PROMPTS_DIRECTORIES.map((directory) => resolve(cwd, directory, `${commandName}.md`)),
		resolve(GLOBAL_PROMPTS_DIRECTORY, `${commandName}.md`),
	];

	for (const candidatePath of candidatePaths) {
		try {
			const template = stripFrontmatter(await readFile(candidatePath, "utf8"));
			return substituteCommandArgs(template, parseCommandArgs(argsString));
		} catch {
			// Ignore missing prompt files and continue searching fallback locations.
		}
	}

	return undefined;
}

function formatCommandArg(arg: string): string {
	return /\s/.test(arg) ? JSON.stringify(arg) : arg;
}

function getPrdSlug(inputPath: string): string {
	const name = basename(stripPathSigil(inputPath));
	return name.endsWith(".md") ? name.slice(0, -3) : name;
}

function getPrdReviewDirectory(cwd: string, inputPath: string): string {
	return resolve(cwd, PRD_REVIEW_ARTIFACTS_DIRECTORY, getPrdSlug(inputPath));
}

function getPrdReviewStatusPath(cwd: string, inputPath: string): string {
	return resolve(getPrdReviewDirectory(cwd, inputPath), PRD_REVIEW_STATUS_FILENAME);
}

function isPrdPlanPath(cwd: string, inputPath: string): boolean {
	const resolved = resolveFromCwd(cwd, inputPath);
	return isWithin(resolve(cwd, PRD_PLANS_DIRECTORY), resolved) && basename(resolved).startsWith("prd-") && resolved.endsWith(".md");
}

function isSpecPath(cwd: string, inputPath: string): boolean {
	const resolved = resolveFromCwd(cwd, inputPath);
	return isWithin(resolve(cwd, PRD_SPECS_DIRECTORY), resolved) && resolved.endsWith(".md") && (basename(resolved).startsWith("spec-") || basename(resolved) === "product_intent.md");
}

function isPrdReviewArtifactPath(cwd: string, inputPath: string): boolean {
	const resolved = resolveFromCwd(cwd, inputPath);
	return isWithin(resolve(cwd, PRD_REVIEW_ARTIFACTS_DIRECTORY), resolved);
}

function isAllowedReviewCleanupCommand(cwd: string, command: string): boolean {
	const trimmed = command.trim();
	const match = trimmed.match(/^rm\s+-f\s+(.+)$/);
	if (!match) return false;

	const targets = parseCommandArgs(match[1]);
	return targets.length > 0 && targets.every((target) => target.endsWith(".md") && isPrdReviewArtifactPath(cwd, target));
}

function isAllowedPrdWritePath(cwd: string, inputPath: string): boolean {
	return isPrdPlanPath(cwd, inputPath) || isSpecPath(cwd, inputPath) || isPrdReviewArtifactPath(cwd, inputPath);
}

function extractTargetSpecPaths(content: string): string[] {
	const lines = content.split(/\r?\n/);
	const headingIndex = lines.findIndex((line) => /^##\s+\[REQUIRED\]\s+Selected functional spec path\(s\)\s*$/i.test(line.trim()));
	if (headingIndex === -1) return [];

	const collected = new Set<string>();
	for (let i = headingIndex + 1; i < lines.length; i += 1) {
		const line = lines[i].trim();
		if (line.startsWith("## ")) break;
		const matches = line.match(/thoughts\/specs\/[A-Za-z0-9._/-]+\.md/g);
		if (matches) {
			for (const match of matches) collected.add(match);
		}
	}

	return [...collected];
}

function isPlanStateEnabled(
	entries: Array<{ type: string; customType?: string; data?: { enabled?: boolean } }>,
	planFlagEnabled = false,
): boolean {
	const stateEntry = entries
		.filter((entry) => entry.type === "custom" && entry.customType === PLAN_STATE_TYPE)
		.pop();
	return Boolean(stateEntry?.data?.enabled) || planFlagEnabled;
}

function derivePrdTools(allTools: string[], normalTools: string[] | undefined): string[] {
	const desired = new Set<string>(DEFAULT_PRD_TOOLS);
	for (const toolName of REVIEW_ORCHESTRATION_TOOLS) {
		desired.add(toolName);
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

export default function prdModeExtension(pi: ExtensionAPI): void {
	let prdModeEnabled = false;
	let currentPrdPath: string | undefined;
	let targetSpecPaths: string[] = [];
	let savedActiveTools: string[] | undefined;
	let reviewCycles = 0;
	let reviewInFlight = false;
	let pendingAutoReviewCommand = false;
	let handoffReady = false;
	let lastReviewCommand: string | undefined;
	let turnTouchedPrdArtifact = false;

	function getAllToolNames(): string[] {
		return pi.getAllTools().map((tool) => tool.name);
	}

	function persistState(): void {
		pi.appendEntry(PRD_STATE_TYPE, {
			enabled: prdModeEnabled,
			currentPrdPath,
			targetSpecPaths,
			reviewCycles,
			reviewInFlight,
			handoffReady,
			savedActiveTools,
			lastReviewCommand,
		} satisfies PrdModeState);
	}

	function updateUi(ctx: ExtensionContext): void {
		if (!prdModeEnabled) {
			ctx.ui.setStatus("prd-mode", undefined);
			ctx.ui.setWidget("prd-mode", undefined);
			return;
		}

		const prdLabel = currentPrdPath ?? "no PRD file yet";
		const targetLabel = targetSpecPaths.length > 0 ? targetSpecPaths.join(", ") : "no baseline spec selected yet";
		const displayedCycles = Math.min(reviewCycles, MAX_REVIEW_CYCLES);
		const cycleLabel = reviewCycles > 0 ? ` • review ${displayedCycles}/${MAX_REVIEW_CYCLES}` : "";
		const status = reviewInFlight ? `🧪 prd review${cycleLabel}` : `🧭 prd${cycleLabel}`;
		const handoffLabel = handoffReady ? "/dev:plan-from-prd ready" : `approved ${PRD_REVIEW_STATUS_FILENAME} required before handoff`;
		ctx.ui.setStatus("prd-mode", ctx.ui.theme.fg("accent", status));
		ctx.ui.setWidget("prd-mode", [
			ctx.ui.theme.fg("accent", "PRD mode active"),
			ctx.ui.theme.fg("muted", `Current PRD: ${prdLabel}`),
			ctx.ui.theme.fg("muted", `Target specs: ${targetLabel}`),
			ctx.ui.theme.fg("muted", `Writes allowed under thoughts/plans/prd-*.md, thoughts/specs/spec-*.md, and ${PRD_REVIEW_ARTIFACTS_DIRECTORY}/<prd-slug>/`),
			ctx.ui.theme.fg("muted", `Clarification: use /${PRD_CLARIFY_COMMAND} before asking the next question`),
			ctx.ui.theme.fg("muted", `Handoff: ${handoffLabel}`),
		]);
	}

	function applyPrdTools(): void {
		const allTools = getAllToolNames();
		pi.setActiveTools(derivePrdTools(allTools, savedActiveTools));
	}

	function otherModeActive(ctx: ExtensionContext): boolean {
		const entries = ctx.sessionManager.getEntries() as Array<{ type: string; customType?: string; data?: { enabled?: boolean } }>;
		return isPlanStateEnabled(entries, pi.getFlag("plan") === true);
	}

	function currentStateEntry(ctx: ExtensionContext): PrdModeState | undefined {
		const stateEntry = ctx.sessionManager
			.getEntries()
			.filter((entry: { type: string; customType?: string }) => entry.type === "custom" && entry.customType === PRD_STATE_TYPE)
			.pop() as { data?: PrdModeState } | undefined;
		return stateEntry?.data;
	}

	function enablePrdMode(ctx: ExtensionContext): void {
		if (prdModeEnabled) return;
		if (otherModeActive(ctx)) {
			ctx.ui.notify(`Cannot enable /prd while /plan mode is active. Disable /plan first, then retry /prd.`, "warning");
			return;
		}

		if (!savedActiveTools || savedActiveTools.length === 0) {
			savedActiveTools = pi.getActiveTools();
		}
		prdModeEnabled = true;
		reviewInFlight = false;
		pendingAutoReviewCommand = false;
		lastReviewCommand = undefined;
		handoffReady = false;
		applyPrdTools();
		updateUi(ctx);
		persistState();
		ctx.ui.notify(`PRD mode enabled.${currentPrdPath ? ` Current PRD: ${currentPrdPath}` : ""}`, "info");
	}

	function disablePrdMode(ctx: ExtensionContext): void {
		prdModeEnabled = false;
		reviewInFlight = false;
		pendingAutoReviewCommand = false;
		handoffReady = false;
		lastReviewCommand = undefined;
		if (savedActiveTools && savedActiveTools.length > 0) {
			pi.setActiveTools(savedActiveTools);
		}
		updateUi(ctx);
		persistState();
		ctx.ui.notify(`PRD mode disabled.${currentPrdPath ? ` Current PRD preserved: ${currentPrdPath}` : ""}`, "info");
	}

	async function maybePromptForReviewBeforeExit(
		ctx: ExtensionContext,
		reason: "toggle-off" | "handoff",
	): Promise<"review" | "exit" | "cancel"> {
		if (!prdModeEnabled || reviewInFlight) return reason === "handoff" ? "cancel" : "exit";
		if (currentPrdPath) {
			await refreshHandoffReady(ctx);
		}
		if (handoffReady) return "exit";

		if (!currentPrdPath) {
			if (reason === "handoff") {
				ctx.ui.notify(`/${DEV_PLAN_FROM_PRD_COMMAND} requires a PRD file and an approved /${PRD_REVIEW_COMMAND} result.`, "warning");
				return "cancel";
			}
			return "exit";
		}

		if (!ctx.hasUI) {
			if (reason === "handoff") {
				ctx.ui.notify(
					`/${DEV_PLAN_FROM_PRD_COMMAND} requires an approved ${PRD_REVIEW_STATUS_FILENAME} under ${PRD_REVIEW_ARTIFACTS_DIRECTORY}/${getPrdSlug(currentPrdPath)}/. Run /${PRD_REVIEW_COMMAND} first.`,
					"warning",
				);
				return "cancel";
			}
			return "exit";
		}

		const reviewLabel = reviewCycles === 0
			? `/${PRD_REVIEW_COMMAND} has not produced an approved result for ${currentPrdPath}.`
			: `The latest /${PRD_REVIEW_COMMAND} result for ${currentPrdPath} is missing, stale, or not approved.`;
		const actionLabel = reason === "handoff" ? `continue to /${DEV_PLAN_FROM_PRD_COMMAND}` : "exit PRD mode";
		const choices = reason === "handoff"
			? ["Run /review:prd now", "Keep editing in PRD mode"]
			: ["Run /review:prd now", "Exit PRD mode anyway", "Keep editing in PRD mode"];
		const choice = await ctx.ui.select(`${reviewLabel} Run the five-reviewer gate before you ${actionLabel}?`, choices);

		if (choice === "Run /review:prd now") return "review";
		if (choice === "Exit PRD mode anyway") return "exit";
		return "cancel";
	}

	async function togglePrdMode(ctx: ExtensionContext): Promise<void> {
		if (prdModeEnabled) {
			const decision = await maybePromptForReviewBeforeExit(ctx, "toggle-off");
			if (decision === "review") {
				await startReviewCycle(ctx, PRD_REVIEW_COMMAND);
				return;
			}
			if (decision === "cancel") {
				return;
			}
			disablePrdMode(ctx);
		} else {
			enablePrdMode(ctx);
		}
	}

	async function dispatchSlashCommandPrompt(ctx: ExtensionContext, commandText: string): Promise<void> {
		const expandedPrompt = await expandSlashCommandPrompt(ctx.cwd, commandText);
		pi.sendUserMessage(expandedPrompt ?? commandText);
	}

	function prepareFreshExecutionCommand(ctx: ExtensionContext): void {
		if (!currentPrdPath) return;
		const command = `/${DEV_PLAN_FROM_PRD_COMMAND} ${formatCommandArg(currentPrdPath)}`;
		ctx.ui.setEditorText(command);
		ctx.ui.notify(`Prepared ${command}. Press Enter to start a fresh execution session.`, "info");
	}

	function refreshPrdStateFromFile(ctx: ExtensionContext): void {
		if (!currentPrdPath) {
			targetSpecPaths = [];
			return;
		}

		const resolved = resolve(ctx.cwd, currentPrdPath);
		void readFile(resolved, "utf8")
			.then((content) => {
				targetSpecPaths = extractTargetSpecPaths(content);
				updateUi(ctx);
				persistState();
			})
			.catch(() => {
				targetSpecPaths = [];
				updateUi(ctx);
				persistState();
			});
	}

	async function hasUnresolvedReviewComments(ctx: ExtensionContext): Promise<boolean> {
		if (!currentPrdPath) return false;
		try {
			const content = await readFile(resolve(ctx.cwd, currentPrdPath), "utf8");
			return content.includes("[REVIEW:");
		} catch {
			return false;
		}
	}

	async function readCurrentReviewStatus(ctx: ExtensionContext): Promise<PrdReviewStatus | undefined> {
		if (!currentPrdPath) return undefined;
		try {
			const content = await readFile(getPrdReviewStatusPath(ctx.cwd, currentPrdPath), "utf8");
			const parsed = JSON.parse(content) as unknown;
			if (!parsed || typeof parsed !== "object") return undefined;
			return parsed as PrdReviewStatus;
		} catch {
			return undefined;
		}
	}

	async function hasApprovedReviewStatus(ctx: ExtensionContext): Promise<boolean> {
		if (!currentPrdPath) return false;

		try {
			const prdPath = resolve(ctx.cwd, currentPrdPath);
			const statusPath = getPrdReviewStatusPath(ctx.cwd, currentPrdPath);
			const expectedReviewDir = relativeToCwd(ctx.cwd, getPrdReviewDirectory(ctx.cwd, currentPrdPath));
			const [prdStats, statusStats, status] = await Promise.all([
				stat(prdPath),
				stat(statusPath),
				readCurrentReviewStatus(ctx),
			]);
			if (!status) return false;

			return status.schemaVersion === 1
				&& status.prdPath === currentPrdPath
				&& status.reviewDir === expectedReviewDir
				&& status.status === "approved"
				&& status.reviewersExpected === 5
				&& status.reviewersCompleted === 5
				&& typeof status.integratedCount === "number"
				&& status.integratedCount >= 0
				&& status.integratedCount <= 5
				&& status.pendingCount === 0
				&& status.reviewerFilesRemoved === true
				&& statusStats.mtimeMs >= prdStats.mtimeMs;
		} catch {
			return false;
		}
	}

	async function refreshHandoffReady(ctx: ExtensionContext): Promise<void> {
		handoffReady = Boolean(currentPrdPath)
			&& !(await hasUnresolvedReviewComments(ctx))
			&& (await hasApprovedReviewStatus(ctx));
		updateUi(ctx);
		persistState();
	}

	async function startReviewCycle(ctx: ExtensionContext, command: string = PRD_REVIEW_COMMAND): Promise<void> {
		if (!currentPrdPath) {
			ctx.ui.notify(`Create or select a PRD file under ${PRD_PLANS_DIRECTORY}/ before running /${PRD_REVIEW_COMMAND}.`, "warning");
			return;
		}

		reviewInFlight = true;
		pendingAutoReviewCommand = true;
		lastReviewCommand = command;
		reviewCycles += 1;
		handoffReady = false;
		applyPrdTools();
		updateUi(ctx);
		persistState();
		await dispatchSlashCommandPrompt(ctx, `/${command} ${formatCommandArg(currentPrdPath)}`);
	}


	async function offerPostReviewAction(ctx: ExtensionContext, reason: string): Promise<void> {
		if (!prdModeEnabled || !ctx.hasUI || !currentPrdPath) return;

		const choices = ["Keep editing in PRD mode"];
		if (reviewCycles < MAX_REVIEW_CYCLES) {
			choices.unshift("Run another PRD review cycle");
		}
		if (handoffReady) {
			choices.unshift("Start fresh /dev:plan-from-prd session");
		}

		const choice = await ctx.ui.select(`PRD review complete (${reason}). Choose an exit path for ${currentPrdPath}.`, choices);

		if (choice === "Start fresh /dev:plan-from-prd session") {
			disablePrdMode(ctx);
			prepareFreshExecutionCommand(ctx);
			return;
		}

		if (choice === "Run another PRD review cycle") {
			await startReviewCycle(ctx, PRD_REVIEW_COMMAND);
		}
	}

	async function hydrateState(ctx: ExtensionContext): Promise<void> {
		prdModeEnabled = false;
		reviewInFlight = false;
		pendingAutoReviewCommand = false;
		handoffReady = false;
		currentPrdPath = undefined;
		targetSpecPaths = [];
		savedActiveTools = undefined;
		reviewCycles = 0;
		lastReviewCommand = undefined;
		turnTouchedPrdArtifact = false;

		const state = currentStateEntry(ctx);
		if (state) {
			prdModeEnabled = Boolean(state.enabled);
			currentPrdPath = state.currentPrdPath;
			targetSpecPaths = state.targetSpecPaths ?? [];
			reviewCycles = state.reviewCycles ?? 0;
			reviewInFlight = Boolean(state.reviewInFlight);
			handoffReady = Boolean(state.handoffReady);
			savedActiveTools = state.savedActiveTools;
			lastReviewCommand = state.lastReviewCommand;
		}

		if (pi.getFlag("prd") === true) {
			prdModeEnabled = true;
		}

		if (currentPrdPath) {
			try {
				await access(resolve(ctx.cwd, currentPrdPath));
				refreshPrdStateFromFile(ctx);
			} catch {
				currentPrdPath = undefined;
				targetSpecPaths = [];
				reviewCycles = 0;
				handoffReady = false;
				lastReviewCommand = undefined;
			}
		}

		if (prdModeEnabled) {
			if (otherModeActive(ctx)) {
				prdModeEnabled = false;
				updateUi(ctx);
				persistState();
				ctx.ui.notify(`PRD mode state conflicted with /plan mode on restore. Disable /plan, then re-enable /prd.`, "warning");
				return;
			}

			if (!savedActiveTools || savedActiveTools.length === 0) {
				savedActiveTools = pi.getActiveTools();
			}
			applyPrdTools();
		} else if (savedActiveTools && savedActiveTools.length > 0) {
			pi.setActiveTools(savedActiveTools);
		}

		if (currentPrdPath && !reviewInFlight) {
			await refreshHandoffReady(ctx);
			return;
		}

		updateUi(ctx);
	}

	pi.registerFlag("prd", {
		description: "Start in PRD mode",
		type: "boolean",
		default: false,
	});

	pi.registerCommand("prd", {
		description: "Toggle PRD mode for thoughts/specs and PRD delta workflows",
		handler: async (_args, ctx) => await togglePrdMode(ctx),
	});

	pi.on("session_start", async (_event, ctx) => {
		await hydrateState(ctx);
	});

	pi.on("session_tree", async (_event, ctx) => {
		await hydrateState(ctx);
	});

	pi.on("input", async (event, ctx) => {
		turnTouchedPrdArtifact = false;
		const text = event.text.trim();
		if (!prdModeEnabled) return { action: "continue" };

		if (text.startsWith(`/${DEV_PLAN_FROM_PRD_COMMAND}`)) {
			const decision = await maybePromptForReviewBeforeExit(ctx, "handoff");
			if (decision === "review") {
				await startReviewCycle(ctx, PRD_REVIEW_COMMAND);
				return { action: "block" };
			}
			if (decision === "cancel") {
				return { action: "block" };
			}
			disablePrdMode(ctx);
			return { action: "continue" };
		}

		if (text.startsWith(`/${PRD_CLARIFY_COMMAND}`)) {
			handoffReady = false;
			updateUi(ctx);
			persistState();
			return { action: "continue" };
		}

		if (text.startsWith(`/${PRD_REVIEW_COMMAND}`)) {
			reviewInFlight = true;
			lastReviewCommand = PRD_REVIEW_COMMAND;
			if (pendingAutoReviewCommand) {
				pendingAutoReviewCommand = false;
			} else {
				reviewCycles += 1;
			}
			handoffReady = false;
			if (!savedActiveTools || savedActiveTools.length === 0) {
				savedActiveTools = pi.getActiveTools();
			}
			applyPrdTools();
			updateUi(ctx);
			persistState();
		}

		return { action: "continue" };
	});

	pi.on("before_agent_start", async (_event, ctx) => {
		if (!prdModeEnabled) return;

		const prdInstruction = currentPrdPath
			? `Current PRD file: ${currentPrdPath}. Continue evolving that file unless the user explicitly asks for a different one.`
			: `If you create a new PRD, write it to ${PRD_PLANS_DIRECTORY}/prd-<slug>.md.`;
		const specInstruction = targetSpecPaths.length > 0
			? `Baseline functional spec(s): ${targetSpecPaths.join(", ")}.`
			: `Discover candidate functional specs under ${PRD_SPECS_DIRECTORY}/ and ask the user to choose if multiple plausible specs match. If ${PRD_SPECS_DIRECTORY}/product_intent.md is absent, use the user request plus repo guidance as the documented fallback baseline.`;

		return {
			message: {
				customType: "prd-mode-context",
				content: `[PRD MODE ACTIVE]
You are in PRD mode for this repository.

Purpose:
- Turn the user's change request into a reviewed PRD delta.
- Keep the PRD delta in ${PRD_PLANS_DIRECTORY}/prd-<slug>.md.
- Compare each answer round against the current intent and spec baseline.
- Ask up to 10 targeted clarification questions when needed to clarify product intent and decisions.
- After a substantive PRD update, run /${PRD_CLARIFY_COMMAND} first so the clarification-gap reviewer runs before optional scout research and before the next question is asked.
- When clarification is still needed, ask the clarification-gap reviewer's prioritized questions directly in the conversation.
- Make each question include a recommended choice and why it is recommended.
- Do not run /${PRD_REVIEW_COMMAND} automatically after edits; use it only when you and the user have clarified the intent and agree a wider review is valuable.
- Treat /${PRD_REVIEW_COMMAND} as the explicit review gate before handoff.
- Once the PRD review is approved, hand off through /${DEV_PLAN_FROM_PRD_COMMAND} <prd-path> in a fresh session.

Artifact model:
- Optional repo-level intent baseline: ${PRD_SPECS_DIRECTORY}/product_intent.md
- Canonical functional spec(s): ${PRD_SPECS_DIRECTORY}/spec-<area>.md
- Working PRD delta: ${PRD_PLANS_DIRECTORY}/prd-<slug>.md
- Review artifacts: ${PRD_REVIEW_ARTIFACTS_DIRECTORY}/<prd-slug>/
- Execution plan: ${PLAN_ROOT}/plans/<slug>.md

PRD delta schema:
- [REQUIRED] Request summary
- [REQUIRED] Selected functional spec path(s)
- [REQUIRED] Current behavior baseline
- [REQUIRED] Proposed behavior changes
- [REQUIRED] Unchanged constraints
- [REQUIRED] Explicit user/operator/agent flows
- [REQUIRED] Error/recovery/default behavior
- [REQUIRED] Readiness decision for dev:plan
- [OPTIONAL] Privacy/security/reliability notes
- [OPTIONAL] Build-vs-buy notes
- [OPTIONAL] Research notes
- [OPTIONAL] Implementation hints

Rules:
- If ${PRD_SPECS_DIRECTORY}/product_intent.md is absent, explicitly say the baseline is the request plus repo guidance.
- If multiple functional specs plausibly match, stop and ask the user to choose.
- If no functional spec exists, say so explicitly and ask for the closest area or exemplar.
- Write only under ${PRD_PLANS_DIRECTORY}/, ${PRD_SPECS_DIRECTORY}/, and ${PRD_REVIEW_ARTIFACTS_DIRECTORY}/ while PRD mode is active.
- Keep /${PRD_REVIEW_COMMAND} artifacts in ${PRD_REVIEW_ARTIFACTS_DIRECTORY}/<prd-slug>/, including ${PRD_REVIEW_STATUS_FILENAME}.
- Do not make implementation changes outside the PRD/spec/review artifact surface.
- Preserve truthful recovery status after errors or interruptions.
- Keep clarification questions high-signal and limited to the set that materially improves intent clarity or decision quality (up to 10 at a time).
- The required clarification order is: clarification-gap reviewer → optional scout → direct user questions.

${prdInstruction}
${specInstruction}`,
				display: false,
			},
		};
	});

	pi.on("tool_call", async (event, ctx) => {
		if (!prdModeEnabled) return;

		if (event.toolName === "bash") {
			const command = String(event.input.command ?? "");
			if (!isSafeCommand(command) && !isAllowedReviewCleanupCommand(ctx.cwd, command)) {
				return {
					block: true,
					reason: `PRD mode only allows read-only bash commands, plus explicit rm -f cleanup of reviewer files under ${PRD_REVIEW_ARTIFACTS_DIRECTORY}/<prd-slug>/.`,
				};
			}
		}

		if (event.toolName === "edit" || event.toolName === "write") {
			const inputPath = typeof event.input.path === "string" ? event.input.path : "";
			if (!inputPath || !isAllowedPrdWritePath(ctx.cwd, inputPath)) {
				return {
					block: true,
					reason: `PRD mode only allows edit/write under ${PRD_PLANS_DIRECTORY}/prd-*.md, ${PRD_SPECS_DIRECTORY}/spec-*.md, and ${PRD_REVIEW_ARTIFACTS_DIRECTORY}/<prd-slug>/.`,
				};
			}
		}
	});

	pi.on("tool_result", async (event, ctx) => {
		if (!prdModeEnabled || event.isError) return;
		if (event.toolName !== "edit" && event.toolName !== "write") return;

		const inputPath = typeof event.input.path === "string" ? event.input.path : undefined;
		if (!inputPath || !isAllowedPrdWritePath(ctx.cwd, inputPath)) return;

		turnTouchedPrdArtifact = true;

		if (isPrdPlanPath(ctx.cwd, inputPath)) {
			currentPrdPath = relativeToCwd(ctx.cwd, inputPath);
			refreshPrdStateFromFile(ctx);
		}

		if (!reviewInFlight) {
			handoffReady = false;
		}
		updateUi(ctx);
		persistState();
	});

	pi.on("agent_end", async (_event, ctx) => {
		if (!prdModeEnabled) return;

		if (reviewInFlight) {
			reviewInFlight = false;
			pendingAutoReviewCommand = false;
			applyPrdTools();
			await refreshHandoffReady(ctx);
			await offerPostReviewAction(
				ctx,
				handoffReady
					? `review cycle ${reviewCycles} approved`
					: `review cycle ${reviewCycles} found issues to resolve`,
			);
			turnTouchedPrdArtifact = false;
			return;
		}

		turnTouchedPrdArtifact = false;
	});
}
