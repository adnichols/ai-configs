import { existsSync, readFileSync } from "node:fs";
import { access, readFile } from "node:fs/promises";
import { homedir } from "node:os";
import { basename, isAbsolute, relative, resolve } from "node:path";
import type { ExtensionAPI, ExtensionCommandContext, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { Key } from "@mariozechner/pi-tui";

const PLAN_STATE_TYPE = "plan-mode-state";
const PRD_STATE_TYPE = "prd-mode-state";
const PLAN_ROOT = "thoughts";
const PLAN_DIRECTORY = "thoughts/plans";
const PLAN_REVIEW_SERVICE_URL = "http://mbp.braid-python.ts.net:4317";
const PLAN_PROMPTS_DIRECTORIES = ["_pi/prompts", ".pi/prompts"] as const;
const GLOBAL_PROMPTS_DIRECTORY = resolve(homedir(), ".pi/agent/prompts");
const EXECUTE_PLAN_COMMAND = "cmd:execute-plan";
const STANDARD_PLAN_REVIEW_COMMAND = "review:plan";
const CHANGE_REVIEW_COMMAND = "review:change";
const CLAUDE_CHANGE_REVIEW_COMMAND = "review:change-claude-code";
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
	"process",
] as const;

const REVIEW_ORCHESTRATION_TOOLS = [
	"subagent",
	"Agent",
	"get_subagent_result",
	"steer_subagent",
	"interactive_shell",
	"process",
] as const;

interface PlanModeState {
	enabled: boolean;
	currentPlanPath?: string;
	currentPlanReviewUrl?: string;
	currentPlanId?: string;
	currentPlanListenerProcessId?: string;
	activeCommentId?: string;
	activeClaimId?: string;
	acknowledgedCommentId?: string;
	savedActiveTools?: string[];
	reviewCycles: number;
	lastReviewCommand?: string;
	preferredStandardReviewCommand?: string;
}

function isPrdModeActive(
	entries: Array<{ type: string; customType?: string; data?: { enabled?: boolean } }>,
	prdFlagEnabled = false,
): boolean {
	const stateEntry = entries
		.filter((entry) => entry.type === "custom" && entry.customType === PRD_STATE_TYPE)
		.pop();
	return Boolean(stateEntry?.data?.enabled) || prdFlagEnabled;
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
		...PLAN_PROMPTS_DIRECTORIES.map((directory) => resolve(cwd, directory, `${commandName}.md`)),
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

function normalizeExecuteTarget(target: string | undefined): "dev:run" | "run-plan" | undefined {
	if (!target) return undefined;
	const normalized = target.trim().replace(/^\//, "");
	if (normalized === "dev:run") return normalized;
	if (normalized === "run-plan" || normalized === "skill:run-plan") return "run-plan";
	return undefined;
}

function formatCommandArg(arg: string): string {
	return /\s/.test(arg) ? JSON.stringify(arg) : arg;
}

function formatNextSteps(commands: readonly string[]): string {
	return commands.join("\n");
}

function isStandardReviewCommand(command: string | undefined): command is typeof STANDARD_PLAN_REVIEW_COMMAND | typeof CHANGE_REVIEW_COMMAND {
	return command === STANDARD_PLAN_REVIEW_COMMAND || command === CHANGE_REVIEW_COMMAND;
}

function getExecutePlanUsage(): string {
	return `Usage: /${EXECUTE_PLAN_COMMAND} <plan slug | thoughts/plans/<slug>.html | path/to/plan.html | legacy path/to/plan.md> [--target dev:run|run-plan]`;
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
	const isExplicitPlanPath = /\.(html|md)$/i.test(planDispatchArgument);
	if (!isExplicitPlanPath && !/^[A-Za-z0-9][A-Za-z0-9._-]*$/.test(planDispatchArgument)) {
		return {
			error: `Invalid plan slug "${planDispatchArgument}". Slugs may only contain letters, numbers, dots, underscores, and hyphens, and must start with a letter or number.`,
		};
	}
	const planPath = isExplicitPlanPath
		? resolveFromCwd(cwd, planDispatchArgument)
		: resolve(cwd, PLAN_DIRECTORY, `${planDispatchArgument}.html`);

	try {
		await access(planPath);
	} catch {
		return {
			error: `Reviewed plan not found: ${planPath}. /${EXECUTE_PLAN_COMMAND} requires an explicit existing reviewed plan file or slug.`,
		};
	}

	return { planDispatchArgument, planPath, targetOverride };
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
	return isWithin(getPlansRoot(cwd), resolved) && /\.(html|md)$/i.test(resolved);
}

function isHtmlPlanFilePath(cwd: string, inputPath: string): boolean {
	const resolved = resolveFromCwd(cwd, inputPath);
	return isWithin(getPlansRoot(cwd), resolved) && /\.html$/i.test(resolved);
}

function isClaudeReviewTempPath(inputPath: string, extension: ".txt" | ".md"): boolean {
	const resolved = resolve(inputPath);
	const name = basename(resolved);
	return resolved === `/tmp/${name}` && new RegExp(`^pi-claude-review-[A-Za-z0-9._-]+\\${extension}$`).test(name);
}

function hasShellHazards(command: string): boolean {
	return /[\r\n;&|`<>]/.test(command) || /\$\(/.test(command) || />>/.test(command);
}

function getOptionValues(tokens: string[], option: string): string[] {
	const values: string[] = [];
	const equalsPrefix = `${option}=`;
	for (let i = 0; i < tokens.length; i += 1) {
		if (tokens[i] === option && i < tokens.length - 1) values.push(tokens[i + 1]);
		else if (tokens[i].startsWith(equalsPrefix)) values.push(tokens[i].slice(equalsPrefix.length));
	}
	return values;
}

function getOptionValue(tokens: string[], option: string): string | undefined {
	return getOptionValues(tokens, option)[0];
}

function hasFlag(tokens: string[], flag: string): boolean {
	return tokens.includes(flag);
}

function validateRemainingTokens(tokens: string[], startIndex: number, options: { valueFlags?: Set<string>; booleanFlags?: Set<string>; positional?: (token: string) => boolean } = {}): boolean {
	const valueFlags = options.valueFlags ?? new Set<string>();
	const booleanFlags = options.booleanFlags ?? new Set<string>();
	const positional = options.positional ?? (() => false);
	for (let i = startIndex; i < tokens.length; i += 1) {
		const token = tokens[i];
		const equalsIndex = token.indexOf("=");
		if (equalsIndex > 0) {
			const flag = token.slice(0, equalsIndex);
			if (!valueFlags.has(flag)) return false;
			if (token.slice(equalsIndex + 1).length === 0) return false;
			continue;
		}
		if (valueFlags.has(token)) {
			if (i === tokens.length - 1 || tokens[i + 1].startsWith("-")) return false;
			i += 1;
			continue;
		}
		if (booleanFlags.has(token)) continue;
		if (token.startsWith("-")) return false;
		if (!positional(token)) return false;
	}
	return true;
}

function serviceUrlAllowed(rawUrl: string | undefined, path?: string): boolean {
	if (typeof rawUrl !== "string") return false;
	try {
		const url = new URL(rawUrl);
		const hostOk = (url.hostname === "mbp.braid-python.ts.net" || url.hostname === "127.0.0.1" || url.hostname === "localhost") && url.port === "4317";
		return hostOk && (path === undefined || url.pathname === path);
	} catch {
		return false;
	}
}

function allPlanReviewUrlsAllowed(tokens: string[]): boolean {
	return getOptionValues(tokens, "--url").every((url) => serviceUrlAllowed(url));
}

function changedFilesAreThoughts(cwd: string, tokens: string[]): boolean {
	return getOptionValues(tokens, "--changed-files")
		.flatMap((value) => value.split(",").map((file) => file.trim()).filter(Boolean))
		.every((file) => isThoughtsPath(cwd, file));
}

function commandPlanId(tokens: string[]): string | undefined {
	if (tokens[0] === "plan-review" && tokens[1] === "agent" && tokens[2] === "next" && tokens[3] && !tokens[3].startsWith("-")) return tokens[3];
	if (tokens[0] === "plan-review" && tokens[1] === "queue" && tokens[2] === "list") return getOptionValue(tokens, "--plan-id");
	if (tokens[0] === "plan-review" && tokens[1] === "queue" && tokens[2] === "claim") return tokens[3] && !tokens[3].startsWith("-") ? tokens[3] : undefined;
	return undefined;
}

function planIdMatches(tokens: string[], state: Partial<PlanModeState> = {}): boolean {
	if (!state.currentPlanId) return Boolean(commandPlanId(tokens));
	return commandPlanId(tokens) === state.currentPlanId;
}

function isAllowedHealthCommand(tokens: string[]): boolean {
	if (tokens[0] !== "curl") return false;
	const urls = tokens.filter((token) => /^https?:\/\//i.test(token));
	if (urls.length !== 1 || !serviceUrlAllowed(urls[0], "/health")) return false;
	const harmlessFlags = new Set(["-f", "-s", "-S", "-L", "-i", "--fail", "--silent", "--show-error", "--location", "--include"]);
	return tokens.every((token) => token === "curl" || token === urls[0] || /^-[fsSLi]+$/.test(token) || harmlessFlags.has(token));
}

function hasPackageScript(cwd: string, scriptName: string): boolean {
	try {
		const packageJson = JSON.parse(readFileSync(resolve(cwd, "package.json"), "utf8")) as { scripts?: Record<string, unknown> };
		return typeof packageJson.scripts?.[scriptName] === "string";
	} catch {
		return false;
	}
}

function isAllowedPlanNodeCommand(cwd: string, tokens: string[]): boolean {
	if (tokens[0] !== "node" || tokens.length < 3) return false;
	const resolvedScript = resolveFromCwd(cwd, tokens[1]);
	if (!existsSync(resolvedScript)) return false;
	if (!isWithin(resolve(cwd, "scripts/plans"), resolvedScript)) return false;
	const scriptName = basename(resolvedScript);
	if (scriptName !== "validate-html-plan.mjs" && scriptName !== "check-plan-authority.mjs" && !/^(validate|check)-[A-Za-z0-9._-]+\.mjs$/.test(scriptName)) return false;
	let sawPlan = false;
	for (const token of tokens.slice(2)) {
		if (token.startsWith("-")) return false;
		sawPlan = true;
		if (!isHtmlPlanFilePath(cwd, token)) return false;
	}
	return sawPlan;
}

function isAllowedPlanServerCommand(cwd: string, tokens: string[]): boolean {
	if (tokens[0] !== "npm" || tokens[1] !== "run" || tokens[2] !== "plans:serve") return false;
	if (!hasPackageScript(cwd, "plans:serve")) return false;
	if (!hasFlag(tokens, "--check")) return false;
	const planValues = getOptionValues(tokens, "--plan");
	return planValues.length > 0
		&& planValues.every((planPath) => isHtmlPlanFilePath(cwd, planPath))
		&& validateRemainingTokens(tokens, 3, { valueFlags: new Set(["--plan"]), booleanFlags: new Set(["--", "--check"]) });
}

function isAllowedServiceStartupOrOpen(tokens: string[]): boolean {
	if (tokens[0] === "brew") return tokens[1] === "services" && tokens[2] === "start" && tokens[3] === "plan-reviewer" && tokens.length === 4;
	if (tokens[0] === "open") return tokens.length === 2 && /^http:\/\/mbp\.braid-python\.ts\.net:4317(?:\/\S*)?$/i.test(tokens[1]);
	return false;
}

function isAllowedRegister(cwd: string, tokens: string[]): boolean {
	if (tokens[1] !== "register") return false;
	const executionReadyValues = getOptionValues(tokens, "--execution-ready");
	if (executionReadyValues.length !== 1 || !["true", "false"].includes(executionReadyValues[0])) return false;
	const flagsWithValues = new Set(["--repo", "--branch", "--commit", "--execution-ready", "--url"]);
	const booleanFlags = new Set(["--json", "--snapshot", "--new-thread"]);
	const planFiles: string[] = [];
	for (let i = 2; i < tokens.length; i += 1) {
		const token = tokens[i];
		if (token.includes("=")) {
			const flag = token.slice(0, token.indexOf("="));
			if (flagsWithValues.has(flag)) continue;
		}
		if (flagsWithValues.has(token)) {
			i += 1;
			continue;
		}
		if (booleanFlags.has(token)) continue;
		if (token.startsWith("-")) return false;
		planFiles.push(token);
	}
	return planFiles.length === 1 && isHtmlPlanFilePath(cwd, planFiles[0]) && allPlanReviewUrlsAllowed(tokens);
}

function isAgentNextDrain(tokens: string[], state: Partial<PlanModeState> = {}): boolean {
	return tokens[1] === "agent"
		&& tokens[2] === "next"
		&& Boolean(commandPlanId(tokens))
		&& planIdMatches(tokens, state)
		&& hasFlag(tokens, "--no-wait")
		&& hasFlag(tokens, "--json")
		&& !hasFlag(tokens, "--wait")
		&& allPlanReviewUrlsAllowed(tokens)
		&& validateRemainingTokens(tokens, 4, { valueFlags: new Set(["--url", "--timeout", "--lease-seconds"]), booleanFlags: new Set(["--no-wait", "--json"]) });
}

function isAllowedPlanReviewListenerCommand(command: string, state: Partial<PlanModeState> = {}): boolean {
	const tokens = parseCommandArgs(command.trim());
	return tokens[0] === "plan-review"
		&& tokens[1] === "agent"
		&& tokens[2] === "next"
		&& Boolean(commandPlanId(tokens))
		&& planIdMatches(tokens, state)
		&& hasFlag(tokens, "--wait")
		&& hasFlag(tokens, "--json")
		&& !hasFlag(tokens, "--no-wait")
		&& allPlanReviewUrlsAllowed(tokens)
		&& validateRemainingTokens(tokens, 4, { valueFlags: new Set(["--url", "--timeout", "--lease-seconds"]), booleanFlags: new Set(["--wait", "--json"]) });
}

function isAllowedQueueLifecycle(cwd: string, tokens: string[], state: Partial<PlanModeState> = {}): boolean {
	const subcommand = tokens[1];
	if (subcommand === "queue") {
		if (tokens[2] !== "list" && tokens[2] !== "claim") return false;
		if (!commandPlanId(tokens)) return false;
		const startIndex = tokens[2] === "claim" ? 4 : 3;
		return planIdMatches(tokens, state)
			&& changedFilesAreThoughts(cwd, tokens)
			&& allPlanReviewUrlsAllowed(tokens)
			&& validateRemainingTokens(tokens, startIndex, { valueFlags: new Set(["--url", "--plan-id", "--ids", "--limit", "--lease-seconds", "--changed-files"]), booleanFlags: new Set(["--json", "--all", "--one"]) });
	}
	const commentId = tokens[2];
	if (!commentId || !changedFilesAreThoughts(cwd, tokens) || !allPlanReviewUrlsAllowed(tokens)) return false;
	if (!validateRemainingTokens(tokens, 3, { valueFlags: new Set(["--url", "--claim", "--note", "--summary", "--changed-files", "--reason"]), booleanFlags: new Set(["--json"]) })) return false;
	if (subcommand === "ack") return commentId === state.activeCommentId && getOptionValue(tokens, "--claim") === state.activeClaimId;
	if (subcommand === "release") {
		const claim = getOptionValue(tokens, "--claim");
		return commentId === state.activeCommentId && (claim === undefined || claim === state.activeClaimId);
	}
	if (subcommand === "resolve") return commentId === state.acknowledgedCommentId;
	return false;
}

function isAllowedPlanReviewCommand(cwd: string, tokens: string[], state: Partial<PlanModeState> = {}): boolean {
	if (tokens[0] !== "plan-review") return false;
	if (tokens[1] === "watch") return false;
	if (tokens[1] === "index") return tokens.length === 2;
	if (tokens[1] === "register") return isAllowedRegister(cwd, tokens);
	if (tokens[1] === "agent" && tokens[2] === "next") return isAgentNextDrain(tokens, state);
	if (tokens[1] === "queue" || tokens[1] === "ack" || tokens[1] === "resolve" || tokens[1] === "release") return isAllowedQueueLifecycle(cwd, tokens, state);
	return false;
}

function isAllowedClaudeReviewLauncherCommand(cwd: string, tokens: string[]): boolean {
	if (tokens[0] !== "python3") return false;
	const launcherPaths = new Set([
		"$HOME/.agents/skills/claude-code-review/scripts/claude_interactive_review.py",
		resolve(homedir(), ".agents/skills/claude-code-review/scripts/claude_interactive_review.py"),
	]);
	if (!launcherPaths.has(tokens[1])) return false;
	if (tokens[2] === "--smoke") {
		if (tokens.length !== 9) return false;
		if (tokens[3] !== "--cwd" || (tokens[4] !== "$PWD" && tokens[4] !== cwd)) return false;
		if (tokens[5] !== "--review-name" || !/^[A-Za-z0-9._-]+$/.test(tokens[6])) return false;
		return tokens[7] === "--output" && isClaudeReviewTempPath(tokens[8], ".txt");
	}
	if (tokens.length !== 12) return false;
	const expectedFlags = ["--cwd", "--prompt-file", "--output", "--review-name", "--timeout-seconds"];
	for (let index = 2; index < tokens.length; index += 2) {
		if (tokens[index] !== expectedFlags[(index - 2) / 2]) return false;
	}
	if (tokens[3] !== "$PWD" && tokens[3] !== cwd) return false;
	if (!isClaudeReviewTempPath(tokens[5], ".txt")) return false;
	if (!isClaudeReviewTempPath(tokens[7], ".md")) return false;
	if (!/^[A-Za-z0-9._-]+$/.test(tokens[9])) return false;
	return /^\d+$/.test(tokens[11]);
}

function isSafeCommand(cwd: string, command: string, state: Partial<PlanModeState> = {}): boolean {
	const normalized = command.trim();
	if (hasShellHazards(normalized)) return false;
	const tokens = parseCommandArgs(normalized);
	if (tokens.length === 0) return false;
	if (isAllowedPlanReviewCommand(cwd, tokens, state)) return true;
	if (isAllowedClaudeReviewLauncherCommand(cwd, tokens)) return true;
	if (isAllowedHealthCommand(tokens)) return true;
	if (tokens[0] === "curl") return false;
	if (isAllowedPlanNodeCommand(cwd, tokens)) return true;
	if (isAllowedPlanServerCommand(cwd, tokens)) return true;
	if (isAllowedServiceStartupOrOpen(tokens)) return true;
	const destructive = DESTRUCTIVE_PATTERNS.some((pattern) => pattern.test(normalized));
	const safe = SAFE_BASH_PATTERNS.some((pattern) => pattern.test(normalized));
	return !destructive && safe;
}

function noteClaimFromText(previousState: Partial<PlanModeState>, text: string): Partial<PlanModeState> {
	let payload: Record<string, unknown> | undefined;
	try {
		payload = JSON.parse(text) as Record<string, unknown>;
	} catch {
		const match = text.match(/\{[\s\S]*\}/);
		if (!match) return {};
		try {
			payload = JSON.parse(match[0]) as Record<string, unknown>;
		} catch {
			return {};
		}
	}
	const directClaim = payload?.status === "claimed" ? payload : undefined;
	const listedClaim = Array.isArray(payload?.claimed) ? payload.claimed[0] as Record<string, unknown> | undefined : undefined;
	const listedNestedClaim = listedClaim?.claim as Record<string, unknown> | undefined;
	const directNestedClaim = directClaim?.claim as Record<string, unknown> | undefined;
	const commentId = directClaim?.commentId ?? directClaim?.id ?? listedClaim?.commentId ?? listedClaim?.id;
	const claimId = directClaim?.claimId ?? directNestedClaim?.id ?? listedClaim?.claimId ?? listedNestedClaim?.id;
	if (typeof commentId !== "string" || typeof claimId !== "string") return {};
	return { ...previousState, activeCommentId: commentId, activeClaimId: claimId, acknowledgedCommentId: undefined };
}

function transitionClaimLifecycle(state: Partial<PlanModeState>, command: string): Partial<PlanModeState> {
	const tokens = parseCommandArgs(command.trim());
	if (tokens[0] !== "plan-review") return state;
	const subcommand = tokens[1];
	const commentId = tokens[2];
	if (subcommand === "ack" && commentId === state.activeCommentId && getOptionValue(tokens, "--claim") === state.activeClaimId) {
		return { ...state, acknowledgedCommentId: commentId };
	}
	if (subcommand === "resolve" && commentId === state.acknowledgedCommentId) {
		return { ...state, activeCommentId: undefined, activeClaimId: undefined, acknowledgedCommentId: undefined };
	}
	if (subcommand === "release" && commentId === state.activeCommentId) {
		const claim = getOptionValue(tokens, "--claim");
		if (claim === undefined || claim === state.activeClaimId) {
			return { ...state, activeCommentId: undefined, activeClaimId: undefined, acknowledgedCommentId: undefined };
		}
	}
	return state;
}

function isFinishedProcessOutput(text: string): boolean {
	return /\[(?:exit\(\d+\)|killed|failed|crashed)\]/i.test(text) || /\b(exit|completed|terminated)\b/i.test(text);
}

function toolResultToText(content: unknown): string {
	if (typeof content === "string") return content;
	if (Array.isArray(content)) {
		return content.map((item) => {
			if (typeof item === "string") return item;
			if (item && typeof item === "object" && "text" in item) {
				return String((item as { text?: unknown }).text ?? "");
			}
			return JSON.stringify(item);
		}).join("\n");
	}
	return content === undefined ? "" : JSON.stringify(content);
}

function parseJsonObject(text: string): Record<string, unknown> | undefined {
	try {
		return JSON.parse(text) as Record<string, unknown>;
	} catch {
		const match = text.match(/\{[\s\S]*\}/);
		if (!match) return undefined;
		try {
			return JSON.parse(match[0]) as Record<string, unknown>;
		} catch {
			return undefined;
		}
	}
}

function canonicalPlanReviewUrl(rawUrl: unknown): string | undefined {
	if (typeof rawUrl !== "string" || rawUrl.length === 0) return undefined;
	if (/^https?:\/\//i.test(rawUrl)) {
		try {
			const url = new URL(rawUrl);
			if (["localhost", "127.0.0.1", "::1", "[::1]"].includes(url.hostname) && url.port === "4317") {
				return `${PLAN_REVIEW_SERVICE_URL}${url.pathname}${url.search}${url.hash}`;
			}
		} catch {
			return undefined;
		}
		return rawUrl;
	}
	return rawUrl.startsWith("/") ? `${PLAN_REVIEW_SERVICE_URL}${rawUrl}` : `${PLAN_REVIEW_SERVICE_URL}/${rawUrl}`;
}

function parsePlanReviewRegistrationOutput(text: string): { planId?: string; reviewUrl?: string; sourcePath?: string } {
	const payload = parseJsonObject(text);
	if (payload) {
		const sourceSync = payload.sourceSync as { sourcePath?: unknown } | undefined;
		return {
			planId: typeof payload.planId === "string" ? payload.planId : undefined,
			reviewUrl: canonicalPlanReviewUrl(payload.reviewUrl),
			sourcePath: typeof sourceSync?.sourcePath === "string" ? sourceSync.sourcePath : undefined,
		};
	}

	const reviewUrl = text.match(/^\s*Review URL\s*:?\s*(\S+)\s*$/im)?.[1];
	const planId = text.match(/^\s*Plan ID\s*:?\s*(\S+)\s*$/im)?.[1];
	return {
		planId,
		reviewUrl: canonicalPlanReviewUrl(reviewUrl),
	};
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

export default function planModeExtension(pi: ExtensionAPI): void {
	let planModeEnabled = false;
	let currentPlanPath: string | undefined;
	let currentPlanReviewUrl: string | undefined;
	let currentPlanId: string | undefined;
	let currentPlanListenerProcessId: string | undefined;
	let activeCommentId: string | undefined;
	let activeClaimId: string | undefined;
	let acknowledgedCommentId: string | undefined;
	let savedActiveTools: string[] | undefined;
	let reviewCycles = 0;
	let reviewInFlight = false;
	let pendingAutoReviewCommand = false;
	let lastReviewCommand: string | undefined;
	let preferredStandardReviewCommand: typeof STANDARD_PLAN_REVIEW_COMMAND | typeof CHANGE_REVIEW_COMMAND | undefined;
	let turnTouchedPlan = false;

	function getPreferredStandardReviewCommand(): typeof STANDARD_PLAN_REVIEW_COMMAND | typeof CHANGE_REVIEW_COMMAND {
		return preferredStandardReviewCommand ?? STANDARD_PLAN_REVIEW_COMMAND;
	}

	function getAllToolNames(): string[] {
		return pi.getAllTools().map((tool) => tool.name);
	}

	function getCommandState(): PlanModeState {
		return {
			enabled: planModeEnabled,
			currentPlanPath,
			currentPlanReviewUrl,
			currentPlanId,
			currentPlanListenerProcessId,
			activeCommentId,
			activeClaimId,
			acknowledgedCommentId,
			savedActiveTools,
			reviewCycles,
			lastReviewCommand,
			preferredStandardReviewCommand,
		};
	}

	function persistState(): void {
		pi.appendEntry(PLAN_STATE_TYPE, {
			enabled: planModeEnabled,
			currentPlanPath,
			currentPlanReviewUrl,
			currentPlanId,
			currentPlanListenerProcessId,
			activeCommentId,
			activeClaimId,
			acknowledgedCommentId,
			savedActiveTools,
			reviewCycles,
			lastReviewCommand,
			preferredStandardReviewCommand,
		} satisfies PlanModeState);
	}

	function updateUi(ctx: ExtensionContext): void {
		if (!planModeEnabled) {
			ctx.ui.setStatus("plan-mode", undefined);
			ctx.ui.setWidget("plan-mode", undefined);
			return;
		}

		const planLabel = currentPlanPath ?? "no plan file yet";
		const urlLabel = currentPlanReviewUrl ?? "not registered yet";
		const listenerLabel = currentPlanListenerProcessId ?? "not running/unknown";
		const claimLabel = activeCommentId && activeClaimId
			? acknowledgedCommentId === activeCommentId
				? `acknowledged ${activeCommentId} (${activeClaimId})`
				: `active ${activeCommentId} (${activeClaimId})`
			: "none";
		const displayedCycles = Math.min(reviewCycles, MAX_REVIEW_CYCLES);
		const cycleLabel = reviewCycles > 0 ? ` • review ${displayedCycles}/${MAX_REVIEW_CYCLES}` : "";
		const status = reviewInFlight ? `🧪 plan review${cycleLabel}` : `📝 plan${cycleLabel}`;
		ctx.ui.setStatus("plan-mode", ctx.ui.theme.fg("accent", status));
		ctx.ui.setWidget("plan-mode", [
			ctx.ui.theme.fg("accent", "Plan mode active"),
			ctx.ui.theme.fg("muted", `Current plan: ${planLabel}`),
			ctx.ui.theme.fg("muted", `Plan URL: ${urlLabel}`),
			ctx.ui.theme.fg("muted", `Comment listener: ${listenerLabel}`),
			ctx.ui.theme.fg("muted", `Active claim: ${claimLabel}`),
			ctx.ui.theme.fg("muted", `Writes allowed only under ${PLAN_ROOT}/`),
		]);
	}

	function applyPlanTools(includeReviewTools = false): void {
		const allTools = getAllToolNames();
		pi.setActiveTools(derivePlanTools(allTools, savedActiveTools, includeReviewTools));
	}

	function enablePlanMode(ctx: ExtensionContext): void {
		if (!planModeEnabled) {
			const entries = ctx.sessionManager.getEntries() as Array<{ type: string; customType?: string; data?: { enabled?: boolean } }>;
			if (isPrdModeActive(entries, pi.getFlag("prd") === true)) {
				ctx.ui.notify(`Cannot enable /plan while /prd mode is active. Disable /prd first, then retry /plan.`, "warning");
				return;
			}
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
		ctx.ui.notify(`Plan mode enabled.${planNote}`, "info");
	}

	function getExecutionBlockReason(): string | undefined {
		const blockers: string[] = [];
		if (currentPlanListenerProcessId) {
			blockers.push(`Stop the active plan-review comment listener before execution: process kill ${currentPlanListenerProcessId}.`);
		}
		if (activeCommentId && activeClaimId) {
			const claimState = acknowledgedCommentId === activeCommentId ? "acknowledged" : "active";
			blockers.push(`Resolve or release the ${claimState} browser comment claim before execution: ${activeCommentId} (${activeClaimId}).`);
		}
		return blockers.length > 0 ? blockers.join(" ") : undefined;
	}

	function getListenerCleanupMessage(): string | undefined {
		return getExecutionBlockReason();
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
		const listenerNote = getListenerCleanupMessage();
		ctx.ui.notify(`Plan mode disabled.${planNote}${listenerNote ? ` ${listenerNote}` : ""}`, "info");
	}

	function togglePlanMode(ctx: ExtensionContext): void {
		if (planModeEnabled) {
			disablePlanMode(ctx);
		} else {
			enablePlanMode(ctx);
		}
	}

	async function dispatchSlashCommandPrompt(ctx: ExtensionContext, commandText: string): Promise<void> {
		// pi.sendUserMessage() bypasses slash-command expansion, so expand prompt-backed
		// slash commands before dispatching them from plan-mode automation.
		const expandedPrompt = await expandSlashCommandPrompt(ctx.cwd, commandText);
		pi.sendUserMessage(expandedPrompt ?? commandText);
	}

	async function handleExecutePlanCommand(args: string, ctx: ExtensionCommandContext): Promise<void> {
		const listenerCleanupMessage = getListenerCleanupMessage();
		if (listenerCleanupMessage) {
			ctx.ui.notify(listenerCleanupMessage, "warning");
			return;
		}

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

		const commandText = `/${target} ${formatCommandArg(request.planDispatchArgument)}`;
		const executionPrompt = target.startsWith("skill:")
			? commandText
			: await expandSlashCommandPrompt(ctx.cwd, commandText);
		if (!executionPrompt) {
			ctx.ui.notify(`Could not expand /${target}. Ensure the corresponding prompt template exists.`, "error");
			return;
		}

		disablePlanMode(ctx);
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
		if (isStandardReviewCommand(command)) {
			preferredStandardReviewCommand = command;
		}
		reviewCycles += 1;
		applyPlanTools(true);
		updateUi(ctx);
		persistState();
		await dispatchSlashCommandPrompt(ctx, `/${command} ${currentPlanPath}`);
	}

	async function hydrateState(ctx: ExtensionContext): Promise<void> {
		planModeEnabled = false;
		reviewInFlight = false;
		pendingAutoReviewCommand = false;
		currentPlanPath = undefined;
		currentPlanReviewUrl = undefined;
		currentPlanId = undefined;
		currentPlanListenerProcessId = undefined;
		activeCommentId = undefined;
		activeClaimId = undefined;
		acknowledgedCommentId = undefined;
		savedActiveTools = undefined;
		reviewCycles = 0;
		lastReviewCommand = undefined;
		preferredStandardReviewCommand = undefined;
		turnTouchedPlan = false;

		const stateEntry = ctx.sessionManager
			.getEntries()
			.filter((entry: { type: string; customType?: string }) => entry.type === "custom" && entry.customType === PLAN_STATE_TYPE)
			.pop() as { data?: PlanModeState } | undefined;

		if (stateEntry?.data) {
			planModeEnabled = stateEntry.data.enabled;
			currentPlanPath = stateEntry.data.currentPlanPath;
			currentPlanReviewUrl = stateEntry.data.currentPlanReviewUrl;
			currentPlanId = stateEntry.data.currentPlanId;
			currentPlanListenerProcessId = stateEntry.data.currentPlanListenerProcessId;
			activeCommentId = stateEntry.data.activeCommentId;
			activeClaimId = stateEntry.data.activeClaimId;
			acknowledgedCommentId = stateEntry.data.acknowledgedCommentId;
			savedActiveTools = stateEntry.data.savedActiveTools;
			reviewCycles = stateEntry.data.reviewCycles ?? 0;
			lastReviewCommand = stateEntry.data.lastReviewCommand;
			preferredStandardReviewCommand = isStandardReviewCommand(stateEntry.data.preferredStandardReviewCommand)
				? stateEntry.data.preferredStandardReviewCommand
				: undefined;
		}

		if (pi.getFlag("plan") === true) {
			planModeEnabled = true;
		}

		if (currentPlanPath) {
			try {
				await access(resolve(ctx.cwd, currentPlanPath));
			} catch {
				currentPlanPath = undefined;
				currentPlanReviewUrl = undefined;
				currentPlanId = undefined;
				currentPlanListenerProcessId = undefined;
				activeCommentId = undefined;
				activeClaimId = undefined;
				acknowledgedCommentId = undefined;
				reviewCycles = 0;
				lastReviewCommand = undefined;
				preferredStandardReviewCommand = undefined;
			}
		}

		const entries = ctx.sessionManager.getEntries() as Array<{ type: string; customType?: string; data?: { enabled?: boolean } }>;
		if (planModeEnabled && isPrdModeActive(entries, pi.getFlag("prd") === true)) {
			planModeEnabled = false;
			updateUi(ctx);
			persistState();
			ctx.ui.notify(`Plan mode state conflicted with /prd mode on restore. Disable /prd, then re-enable /plan.`, "warning");
			return;
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

		const standardReviewCommand = getPreferredStandardReviewCommand();
		if (/\.html$/i.test(currentPlanPath)) {
			ctx.ui.notify(
				`HTML plan updated (${reason}). Run /dev:reviewed-html-plan ${formatCommandArg(currentPlanPath)} to register/iterate browser feedback; /${standardReviewCommand} ${formatCommandArg(currentPlanPath)} remains available for explicit inline review.`,
				"info",
			);
			return;
		}

		ctx.ui.notify(
			`Plan updated (${reason}). Run /${standardReviewCommand} ${formatCommandArg(currentPlanPath)} when ready.`,
			"info",
		);
	}

	async function startReviewIntegration(ctx: ExtensionContext, options?: { automatic?: boolean }): Promise<void> {
		if (!currentPlanPath) return;
		const completedReviewCommand = isStandardReviewCommand(lastReviewCommand)
			? lastReviewCommand
			: getPreferredStandardReviewCommand();
		reviewInFlight = true;
		pendingAutoReviewCommand = false;
		lastReviewCommand = CHANGE_REVIEW_INTEGRATE_COMMAND;
		applyPlanTools(false);
		updateUi(ctx);
		persistState();
		if (options?.automatic) {
			ctx.ui.notify(
				`/${completedReviewCommand} completed for ${currentPlanPath}. Automatically running /${CHANGE_REVIEW_INTEGRATE_COMMAND}.`,
				"info",
			);
		}
		await dispatchSlashCommandPrompt(ctx, `/${CHANGE_REVIEW_INTEGRATE_COMMAND} ${formatCommandArg(currentPlanPath)}`);
	}

	async function offerPostReviewAction(ctx: ExtensionContext, reason: string): Promise<void> {
		if (!planModeEnabled || !ctx.hasUI || !currentPlanPath) return;

		const standardReviewCommand = getPreferredStandardReviewCommand();
		const nextSteps = [] as string[];

		if (isStandardReviewCommand(lastReviewCommand)) {
			nextSteps.push(`/${CHANGE_REVIEW_INTEGRATE_COMMAND} ${formatCommandArg(currentPlanPath)}`);
		} else if (lastReviewCommand === CHANGE_REVIEW_INTEGRATE_COMMAND && reviewCycles < MAX_REVIEW_CYCLES) {
			nextSteps.push(`/${standardReviewCommand} ${formatCommandArg(currentPlanPath)}`);
		}

		if (isStandardReviewCommand(lastReviewCommand) || lastReviewCommand === CHANGE_REVIEW_INTEGRATE_COMMAND) {
			nextSteps.push(`/${ADVERSARIAL_PLAN_REVIEW_COMMAND} ${formatCommandArg(currentPlanPath)}`);
		}

		nextSteps.push(
			`/${EXECUTE_PLAN_COMMAND} ${formatCommandArg(currentPlanPath)} --target dev:run`,
			`/${EXECUTE_PLAN_COMMAND} ${formatCommandArg(currentPlanPath)} --target run-plan`,
		);

		ctx.ui.notify(`Plan review complete (${reason}). Available next steps:\n${formatNextSteps(nextSteps)}`, "info");
	}

	pi.registerFlag("plan", {
		description: "Start in plan mode",
		type: "boolean",
		default: false,
	});

	pi.registerCommand("plan", {
		description: "Toggle plan mode for thoughts/ planning workflows",
		handler: async (_args, ctx) => togglePlanMode(ctx),
	});

	pi.registerCommand(EXECUTE_PLAN_COMMAND, {
		description: "Start /run-plan or /dev:run in a fresh session from a reviewed plan",
		handler: async (args, ctx) => handleExecutePlanCommand(args, ctx),
	});

	pi.registerShortcut(Key.ctrlAlt("p"), {
		description: "Toggle plan mode",
		handler: async (ctx) => togglePlanMode(ctx),
	});

	pi.on("session_start", async (_event, ctx) => {
		await hydrateState(ctx);
	});

	pi.on("session_tree", async (_event, ctx) => {
		await hydrateState(ctx);
	});

	pi.on("input", async (event, ctx) => {
		turnTouchedPlan = false;
		const text = event.text.trim();
		if (!planModeEnabled) return { action: "continue" };

		if (text.startsWith(`/${EXECUTE_PLAN_COMMAND}`) || text.startsWith("/dev:run") || text.startsWith("/run-plan") || text.startsWith("/skill:run-plan")) {
			const executionBlockReason = getExecutionBlockReason();
			if (executionBlockReason) {
				ctx.ui.notify(executionBlockReason, "warning");
				return { action: "block" };
			}
			disablePlanMode(ctx);
			return { action: "continue" };
		}

		if (text.startsWith(`/${CHANGE_REVIEW_INTEGRATE_COMMAND}`)) {
			reviewInFlight = true;
			lastReviewCommand = CHANGE_REVIEW_INTEGRATE_COMMAND;
			if (!savedActiveTools || savedActiveTools.length === 0) {
				savedActiveTools = pi.getActiveTools();
			}
			applyPlanTools(true);
			updateUi(ctx);
			persistState();
			return { action: "continue" };
		}

		if (
			text.startsWith(`/${ADVERSARIAL_PLAN_REVIEW_COMMAND}`)
			|| text.startsWith(`/${STANDARD_PLAN_REVIEW_COMMAND}`)
			|| text.startsWith(`/${CHANGE_REVIEW_COMMAND}`)
			|| text.startsWith(`/${CLAUDE_CHANGE_REVIEW_COMMAND}`)
		) {
			reviewInFlight = true;
			if (text.startsWith(`/${ADVERSARIAL_PLAN_REVIEW_COMMAND}`)) {
				lastReviewCommand = ADVERSARIAL_PLAN_REVIEW_COMMAND;
			} else if (text.startsWith(`/${CLAUDE_CHANGE_REVIEW_COMMAND}`)) {
				lastReviewCommand = CLAUDE_CHANGE_REVIEW_COMMAND;
			} else {
				const standardReviewCommand = text.startsWith(`/${CHANGE_REVIEW_COMMAND}`)
					? CHANGE_REVIEW_COMMAND
					: STANDARD_PLAN_REVIEW_COMMAND;
				lastReviewCommand = standardReviewCommand;
				preferredStandardReviewCommand = standardReviewCommand;
			}
			if (pendingAutoReviewCommand) {
				pendingAutoReviewCommand = false;
			} else {
				reviewCycles += 1;
			}
			if (!savedActiveTools || savedActiveTools.length === 0) {
				savedActiveTools = pi.getActiveTools();
			}
			applyPlanTools(true);
			updateUi(ctx);
			persistState();
		}

		return { action: "continue" };
	});

	pi.on("before_agent_start", async (_event) => {
		if (!planModeEnabled) return;

		const activeClaimInstruction = activeCommentId && activeClaimId
			? ` Active browser comment claim: ${activeCommentId} (${activeClaimId})${acknowledgedCommentId === activeCommentId ? " is acknowledged; resolve it before restarting the listener." : " is unacknowledged; ack, release, or resolve it before execution."}`
			: " No active browser comment claim.";
		const currentPlanInstruction = currentPlanPath
			? `Current plan file: ${currentPlanPath}. Continue evolving that file unless the user explicitly asks for a different one. Current browser review URL: ${currentPlanReviewUrl ?? "not registered yet"}.${activeClaimInstruction}`
			: `If you create a new plan, write it to ${PLAN_DIRECTORY}/<slug>.html.${activeClaimInstruction}`;

		return {
			message: {
				customType: "plan-mode-context",
				content: `[PLAN MODE ACTIVE]
You are in planning mode for this repository.

Constraints:
- Read the codebase freely.
- You may write only under ${PLAN_ROOT}/ using edit/write tools, except transient Claude review prompt files matching /tmp/pi-claude-review-*.txt during review commands.
- Keep plan files in ${PLAN_DIRECTORY}/.
- Do not make implementation changes outside ${PLAN_ROOT}/.
- Use read-only bash commands for exploration; file mutations must go through edit/write inside ${PLAN_ROOT}/, except the transient Claude review prompt file exception above.
- Load and follow the planning skills needed for deterministic HTML planning: planning-workflow, doct-document-ops, reviewed-html-plan, product-principles for workflow-impacting plans, plus relevant domain skills.
- Plans should align with thoughts/specs/product_intent.md and thoughts/plans/AGENTS.md when relevant.
- New active plans should be semantic HTML under ${PLAN_DIRECTORY}/<slug>.html unless the user explicitly supplies an existing legacy Markdown plan.
- Register HTML plans with plan-review using truthful --execution-ready metadata; preserve and display the canonical browser review URL.
- Use the Doct durable plan comment listener for browser comments: drain with agent next --no-wait, start listenerInstructions.listenerCommand (doct-agent plans listen ... --jsonl) via the process tool, process each emitted claim, then ack/resolve it. Do not use agent next --wait as the default listener, and do not use or recommend the watch subcommand in /plan mode.
- After creating or materially updating an HTML plan, /dev:reviewed-html-plan <path> is the deterministic registration, browser-feedback, PM-review, and Claude/Codex plan-review path. /review:plan <path> remains available only as an explicit inline review.
- After a standard inline review completes with comments, /review:change-integrate <path> runs automatically so review feedback is resolved back into the same plan file before any manual execution handoff.
- After standard inline review integration, you may optionally run /review:plan-adversarial <path> for a second-pass challenge review.
- Before execution, stop any active plan-review comment listener, then run /cmd:execute-plan <path> --target dev:run or --target run-plan to start a fresh execution session.
- Review feedback should be integrated back into the same plan file.
- Automatic inline review looping is capped at ${MAX_REVIEW_CYCLES} cycles before stopping.

${currentPlanInstruction}`,
				display: false,
			},
		};
	});

	pi.on("tool_call", async (event, ctx) => {
		if (!planModeEnabled) return;

		if (event.toolName === "bash") {
			const command = String(event.input.command ?? "");
			if (!isSafeCommand(ctx.cwd, command, getCommandState())) {
				return {
					block: true,
					reason: `Plan mode only allows read-only bash commands. Use edit/write within ${PLAN_ROOT}/ for plan files.`,
				};
			}
		}

		if (event.toolName === "process") {
			const action = String(event.input.action ?? "");
			const command = String(event.input.command ?? "");
			const id = typeof event.input.id === "string" ? event.input.id : undefined;
			const readOnlyActions = new Set(["list", "output", "logs"]);
			const allowedStart = action === "start" && isAllowedPlanReviewListenerCommand(command, getCommandState());
			const allowedKill = action === "kill" && id !== undefined && id === currentPlanListenerProcessId;

			if (!readOnlyActions.has(action) && !allowedStart && !allowedKill) {
				return {
					block: true,
					reason: "Plan mode only allows process list/output/logs, starting the plan-review agent next listener, or killing the tracked listener.",
				};
			}
		}

		if (event.toolName === "edit" || event.toolName === "write") {
			const inputPath = typeof event.input.path === "string" ? event.input.path : "";
			const allowedClaudeReviewPrompt = reviewInFlight && isClaudeReviewTempPath(inputPath, ".txt");
			if (!inputPath || (!isThoughtsPath(ctx.cwd, inputPath) && !allowedClaudeReviewPrompt)) {
				return {
					block: true,
					reason: `Plan mode only allows edit/write under ${PLAN_ROOT}/, except transient Claude review prompt files under /tmp.`,
				};
			}
		}
	});

	pi.on("tool_result", async (event, ctx) => {
		if (!planModeEnabled) return;

		if (event.toolName === "process") {
			const action = String(event.input.action ?? "");
			const command = String(event.input.command ?? "");
			if (action === "kill" && event.input.id === currentPlanListenerProcessId) {
				currentPlanListenerProcessId = undefined;
				updateUi(ctx);
				persistState();
				return;
			}
			if (event.isError) return;
			const text = toolResultToText(event.content);
			if (action === "start" && isAllowedPlanReviewListenerCommand(command, getCommandState())) {
				const details = (event as unknown as { details?: { id?: string; processId?: string } }).details;
				const match = text.match(/\b(proc_\w+)/);
				currentPlanListenerProcessId = details?.id ?? details?.processId ?? match?.[1] ?? currentPlanListenerProcessId;
				const claimState = noteClaimFromText(getCommandState(), text);
				const capturedClaim = Boolean(claimState.activeCommentId && claimState.activeClaimId);
				activeCommentId = claimState.activeCommentId ?? activeCommentId;
				activeClaimId = claimState.activeClaimId ?? activeClaimId;
				acknowledgedCommentId = claimState.acknowledgedCommentId;
				if (capturedClaim || isFinishedProcessOutput(text)) {
					currentPlanListenerProcessId = undefined;
				}
				updateUi(ctx);
				persistState();
				return;
			}
			if ((action === "output" || action === "logs") && event.input.id === currentPlanListenerProcessId) {
				const claimState = noteClaimFromText(getCommandState(), text);
				const capturedClaim = Boolean(claimState.activeCommentId && claimState.activeClaimId);
				activeCommentId = claimState.activeCommentId ?? activeCommentId;
				activeClaimId = claimState.activeClaimId ?? activeClaimId;
				acknowledgedCommentId = claimState.acknowledgedCommentId ?? acknowledgedCommentId;
				if (capturedClaim || isFinishedProcessOutput(text)) {
					currentPlanListenerProcessId = undefined;
				}
				updateUi(ctx);
				persistState();
			}
			return;
		}

		if (event.isError) return;

		if (event.toolName === "bash") {
			const command = String(event.input.command ?? "");
			const text = toolResultToText(event.content);
			if (/^\s*plan-review\s+register\b/i.test(command)) {
				const registration = parsePlanReviewRegistrationOutput(text);
				if (registration.reviewUrl) {
					currentPlanReviewUrl = registration.reviewUrl;
					currentPlanId = registration.planId ?? currentPlanId;
					if (registration.sourcePath) {
						currentPlanPath = relativeToCwd(ctx.cwd, registration.sourcePath);
					}
					updateUi(ctx);
					persistState();
				}
			} else if (/^\s*plan-review\s+agent\s+next\b/i.test(command)) {
				const claimState = noteClaimFromText(getCommandState(), text);
				activeCommentId = claimState.activeCommentId ?? activeCommentId;
				activeClaimId = claimState.activeClaimId ?? activeClaimId;
				acknowledgedCommentId = claimState.acknowledgedCommentId;
				updateUi(ctx);
				persistState();
			} else if (/^\s*plan-review\s+(ack|resolve|release)\b/i.test(command)) {
				const nextState = transitionClaimLifecycle(getCommandState(), command);
				activeCommentId = nextState.activeCommentId;
				activeClaimId = nextState.activeClaimId;
				acknowledgedCommentId = nextState.acknowledgedCommentId;
				updateUi(ctx);
				persistState();
			}
			return;
		}


		if (event.toolName !== "edit" && event.toolName !== "write") return;

		const inputPath = typeof event.input.path === "string" ? event.input.path : undefined;
		if (!inputPath || !isPlanFilePath(ctx.cwd, inputPath)) return;

		turnTouchedPlan = true;
		const nextPlanPath = relativeToCwd(ctx.cwd, inputPath);
		if (nextPlanPath !== currentPlanPath) {
			currentPlanReviewUrl = undefined;
			currentPlanId = undefined;
			currentPlanListenerProcessId = undefined;
			activeCommentId = undefined;
			activeClaimId = undefined;
			acknowledgedCommentId = undefined;
		}
		currentPlanPath = nextPlanPath;
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
			if (isStandardReviewCommand(lastReviewCommand) && turnTouchedPlan) {
				await startReviewIntegration(ctx, { automatic: true });
				turnTouchedPlan = false;
				return;
			}

			const reviewReason = lastReviewCommand === CHANGE_REVIEW_INTEGRATE_COMMAND
				? turnTouchedPlan
					? `review cycle ${reviewCycles} integrated`
					: `review cycle ${reviewCycles} integration completed`
				: isStandardReviewCommand(lastReviewCommand)
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
