/**
 * Prewalk Extension (ai-configs vendored)
 *
 * Ported from oh-my-pi / lukeramsden/pi-prewalk, with named execution profiles.
 *
 * Prewalk lets a strong model plan, then hands mechanical implementation to a
 * configured execution model + reasoning level. One-way switch, armed via
 * `--prewalk` / `--prewalk-into` or `/prewalk`, fires at first edit/write once
 * a todo list exists.
 *
 * Profiles: package profiles.json + optional ~/.pi/agent/prewalk-profiles.json
 *   /prewalk              → default profile
 *   /prewalk profiles     → list
 *   /prewalk terra        → named profile
 *   /prewalk flash:high   → profile + thinking override
 *   /prewalk default sol  → session default
 *   /prewalk provider/id[:level] → ad-hoc model
 */

import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import type { Api, Model } from "@earendil-works/pi-ai";
import type { ExtensionAPI, ExtensionContext } from "@earendil-works/pi-coding-agent";

const PREWALK_PLAN_MESSAGE_TYPE = "prewalk-plan";
const PREWALK_CONTINUE_MESSAGE_TYPE = "prewalk-continue";
const PREWALK_CHECKLIST_MESSAGE_TYPE = "prewalk-checklist";

const PREWALK_ACTION_TOOLS: Record<string, true> = {
	edit: true,
	write: true,
};

/** Fallback when profiles.json is missing or empty. */
const HARDCODED_DEFAULT_TARGET = {
	provider: "deepinfra",
	id: "deepseek-ai/DeepSeek-V4-Flash-0731",
	thinkingLevel: "low" as ThinkingLevel,
};

const PREWALK_PLAN_PROMPT = `Stop and write the complete plan in your NEXT reply — before any further exploration. You have already seen enough to commit to a plan; do not defer this.

First, state the plan itself, explicitly and comprehensively:

- Every remaining step in execution order, with the exact files, symbols, commands, and checks involved.
- Known risks, edge cases, and how you will verify each step actually landed (specific commands, expected outputs). Never modify tests or verification assets to make checks pass.
- What is already done, stated briefly, so no step gets repeated.

Be thorough and concrete — this plan is the reference for the remainder of the run. You may verify details with tools after the plan is written, never before.

Then, only once the plan above is complete, in the SAME reply, capture it as a todo list (the todo tool): 5-9 items, one per MEANINGFUL step, each naming its concrete target and its verification. Only steps that change or verify code belong on the list — no reporting, bookkeeping, cleanup-ceremony, or release-note items. The todo list serves the task, never the reverse: when reality disagrees with an item, fix the actual problem rather than working the checklist.

This is a checkpoint, not a final answer: do not end your turn on the plan alone — after recording the todo list, continue the task; do not stop here.`;

const PREWALK_CONTINUE_PROMPT = `Continue the task now — do not end your turn here.`;

const PREWALK_CHECKLIST_PROMPT = `Before you consider this task finished, verify:

- Consistency: if you changed a pattern, signature, or check in one place, grep for every other call site or duplicate copy that needs the identical change. A fix applied to only some of the matching sites is still a failure.
- Scope: if your diff does more than the minimal change needed to resolve the issue, confirm you have not altered behavior for any case outside the reported issue. Prefer the smallest correct diff over a broader rewrite.
- Verification: run the full test module or file the issue lives in, not just the one test you expect to flip. A change that breaks a sibling test is not a fix.

Do not claim the task is complete until you have done these three checks.`;

type ThinkingLevel = "off" | "minimal" | "low" | "medium" | "high" | "xhigh" | "max";

interface PrewalkProfile {
	label?: string;
	provider: string;
	id: string;
	thinkingLevel?: ThinkingLevel;
}

interface PrewalkConfigFile {
	defaultProfile?: string;
	profiles?: Record<string, Partial<PrewalkProfile> & { provider?: string; id?: string }>;
}

interface LoadedConfig {
	defaultProfile: string;
	profiles: Record<string, PrewalkProfile>;
}

interface ArmedPrewalk {
	target: Model<Api>;
	thinkingLevel?: ThinkingLevel;
	profileName?: string;
}

const THINKING_LEVELS = new Set<ThinkingLevel>(["off", "minimal", "low", "medium", "high", "xhigh", "max"]);

function packageRoot(): string {
	try {
		return join(dirname(fileURLToPath(import.meta.url)), "..");
	} catch {
		return join(homedir(), ".pi", "agent", "local-packages", "ai-configs", "pi-prewalk");
	}
}

function agentDir(): string {
	return process.env.PI_CODING_AGENT_DIR?.trim() || join(homedir(), ".pi", "agent");
}

function readJsonFile(path: string): PrewalkConfigFile | undefined {
	if (!existsSync(path)) return undefined;
	try {
		const raw = JSON.parse(readFileSync(path, "utf8")) as unknown;
		if (!raw || typeof raw !== "object" || Array.isArray(raw)) return undefined;
		return raw as PrewalkConfigFile;
	} catch {
		return undefined;
	}
}

function isThinkingLevel(value: string): value is ThinkingLevel {
	return THINKING_LEVELS.has(value as ThinkingLevel);
}

function normalizeProfile(
	name: string,
	partial: Partial<PrewalkProfile> & { provider?: string; id?: string },
	base?: PrewalkProfile,
): PrewalkProfile | undefined {
	const provider = (partial.provider ?? base?.provider ?? "").trim();
	const id = (partial.id ?? base?.id ?? "").trim();
	if (!provider || !id) return undefined;
	const thinkingRaw = partial.thinkingLevel ?? base?.thinkingLevel;
	const thinkingLevel =
		typeof thinkingRaw === "string" && isThinkingLevel(thinkingRaw.toLowerCase())
			? (thinkingRaw.toLowerCase() as ThinkingLevel)
			: undefined;
	const label = (partial.label ?? base?.label ?? name).trim() || name;
	return { label, provider, id, thinkingLevel };
}

/** Exported for unit tests. */
export function mergePrewalkConfigs(packageCfg: PrewalkConfigFile | undefined, userCfg: PrewalkConfigFile | undefined): LoadedConfig {
	const profiles: Record<string, PrewalkProfile> = {};

	const ingest = (cfg: PrewalkConfigFile | undefined, overlay: boolean) => {
		if (!cfg?.profiles || typeof cfg.profiles !== "object") return;
		for (const [name, partial] of Object.entries(cfg.profiles)) {
			const key = name.trim().toLowerCase();
			if (!key || !partial || typeof partial !== "object") continue;
			const merged = normalizeProfile(key, partial, overlay ? profiles[key] : undefined);
			if (merged) profiles[key] = merged;
		}
	};

	ingest(packageCfg, false);
	ingest(userCfg, true);

	if (Object.keys(profiles).length === 0) {
		profiles.flash = {
			label: "DeepSeek Flash (cheap execution)",
			provider: HARDCODED_DEFAULT_TARGET.provider,
			id: HARDCODED_DEFAULT_TARGET.id,
			thinkingLevel: HARDCODED_DEFAULT_TARGET.thinkingLevel,
		};
	}

	const requested =
		(userCfg?.defaultProfile ?? packageCfg?.defaultProfile ?? "flash").trim().toLowerCase() || "flash";
	const defaultProfile = profiles[requested] ? requested : Object.keys(profiles).sort()[0];

	return { defaultProfile, profiles };
}

export function loadPrewalkConfig(agentDirectory = agentDir(), pkgRoot = packageRoot()): LoadedConfig {
	const packageCfg = readJsonFile(join(pkgRoot, "profiles.json"));
	const userCfg = readJsonFile(join(agentDirectory, "prewalk-profiles.json"));
	return mergePrewalkConfigs(packageCfg, userCfg);
}

export function parseTargetSpec(spec: string | undefined): { modelSpec?: string; thinkingLevel?: ThinkingLevel } {
	if (!spec) return {};
	const trimmed = spec.trim();
	const separator = trimmed.lastIndexOf(":");
	if (separator < 0) return { modelSpec: trimmed };
	const suffix = trimmed.slice(separator + 1).toLowerCase() as ThinkingLevel;
	if (!THINKING_LEVELS.has(suffix)) return { modelSpec: trimmed };
	const head = trimmed.slice(0, separator).trim();
	return { modelSpec: head.length > 0 ? head : undefined, thinkingLevel: suffix };
}

function modelLabel(model: Model<Api>): string {
	return `${model.provider}/${model.id}`;
}

function modelsAreEqual(a: Model<Api> | undefined, b: Model<Api>): boolean {
	return a !== undefined && a.provider === b.provider && a.id === b.id;
}

function totalCost(model: Model<Api>): number {
	return (model.cost?.input ?? 0) + (model.cost?.output ?? 0);
}

function profileLabel(name: string, profile: PrewalkProfile): string {
	const thinking = profile.thinkingLevel ? `:${profile.thinkingLevel}` : "";
	const pretty = profile.label ? ` — ${profile.label}` : "";
	return `${name} → ${profile.provider}/${profile.id}${thinking}${pretty}`;
}

async function resolveModelByProviderId(
	ctx: ExtensionContext,
	provider: string,
	id: string,
): Promise<{ model?: Model<Api>; error?: string }> {
	const available = (await ctx.modelRegistry.getAvailable()) as Model<Api>[];
	if (available.length === 0) {
		return { error: "No models with configured API keys are available" };
	}
	const providerLc = provider.toLowerCase();
	const idLc = id.toLowerCase();
	const match =
		available.find((m) => m.provider.toLowerCase() === providerLc && m.id.toLowerCase() === idLc) ??
		available.find((m) => m.id.toLowerCase() === idLc) ??
		available.find((m) => m.id.toLowerCase() === `${providerLc}/${idLc}`);
	if (!match) {
		return { error: `No available model matches ${provider}/${id}` };
	}
	return { model: match };
}

/**
 * Resolve a profile name, ad-hoc model spec, or default profile into a live model.
 */
async function resolveTarget(
	ctx: ExtensionContext,
	spec: string | undefined,
	config: LoadedConfig,
	sessionDefaultProfile: string | undefined,
): Promise<{
	model?: Model<Api>;
	thinkingLevel?: ThinkingLevel;
	profileName?: string;
	error?: string;
	warning?: string;
}> {
	const available = (await ctx.modelRegistry.getAvailable()) as Model<Api>[];
	if (available.length === 0) {
		return { error: "No models with configured API keys are available" };
	}

	const parsed = parseTargetSpec(spec);
	const token = parsed.modelSpec?.trim();

	// Named profile (exact, case-insensitive).
	if (token) {
		const profileKey = token.toLowerCase();
		const profile = config.profiles[profileKey];
		if (profile) {
			const resolved = await resolveModelByProviderId(ctx, profile.provider, profile.id);
			if (resolved.error || !resolved.model) {
				return { error: resolved.error ?? `Profile "${profileKey}" model is unavailable` };
			}
			return {
				model: resolved.model,
				thinkingLevel: parsed.thinkingLevel ?? profile.thinkingLevel,
				profileName: profileKey,
			};
		}
	}

	// Ad-hoc model spec.
	if (token) {
		const query = token.toLowerCase();
		let match: Model<Api> | undefined;
		if (query.includes("/")) {
			const slash = query.indexOf("/");
			const provider = query.slice(0, slash);
			const id = query.slice(slash + 1);
			match =
				available.find((m) => m.provider.toLowerCase() === provider && m.id.toLowerCase() === id) ??
				available.find((m) => m.id.toLowerCase() === query);
		} else {
			match =
				available.find((m) => m.id.toLowerCase() === query) ??
				available.find((m) => m.id.toLowerCase().includes(query));
		}
		if (!match) {
			const known = Object.keys(config.profiles).sort().join(", ");
			return {
				error: `No profile or available model matches "${token}". Profiles: ${known || "(none)"}.`,
			};
		}
		return { model: match, thinkingLevel: parsed.thinkingLevel };
	}

	// Default profile path.
	const defaultName = (sessionDefaultProfile ?? config.defaultProfile).toLowerCase();
	const defaultProfile = config.profiles[defaultName];
	if (defaultProfile) {
		const resolved = await resolveModelByProviderId(ctx, defaultProfile.provider, defaultProfile.id);
		if (resolved.model) {
			return {
				model: resolved.model,
				thinkingLevel: parsed.thinkingLevel ?? defaultProfile.thinkingLevel,
				profileName: defaultName,
			};
		}
	}

	// Fallback: hardcoded DeepSeek Flash, then cheapest other model.
	const current = ctx.model as Model<Api> | undefined;
	const candidates = available.filter((m) => !modelsAreEqual(current, m));
	if (candidates.length === 0) {
		return { error: "No available model to prewalk into (only the current model has a configured key)" };
	}

	const isHardcoded = (m: Model<Api>): boolean =>
		m.provider.toLowerCase() === HARDCODED_DEFAULT_TARGET.provider &&
		m.id.toLowerCase() === HARDCODED_DEFAULT_TARGET.id.toLowerCase();
	const preferred = candidates.find(isHardcoded);
	if (preferred) {
		return {
			model: preferred,
			thinkingLevel: parsed.thinkingLevel ?? HARDCODED_DEFAULT_TARGET.thinkingLevel,
			warning: defaultProfile
				? `Profile "${defaultName}" unavailable; using ${HARDCODED_DEFAULT_TARGET.provider}/${HARDCODED_DEFAULT_TARGET.id}.`
				: undefined,
		};
	}

	const byCost = (a: Model<Api>, b: Model<Api>): number =>
		totalCost(a) - totalCost(b) || (a.cost?.output ?? 0) - (b.cost?.output ?? 0);
	const priced = candidates.filter((m) => totalCost(m) > 0).sort(byCost);
	const chosen = priced[0] ?? candidates.slice().sort(byCost)[0];
	const defaultLabel = defaultProfile
		? `${defaultProfile.provider}/${defaultProfile.id}`
		: `${HARDCODED_DEFAULT_TARGET.provider}/${HARDCODED_DEFAULT_TARGET.id}`;
	return {
		model: chosen,
		thinkingLevel: parsed.thinkingLevel,
		warning: `Default ${defaultLabel} unavailable; using ${modelLabel(chosen)} instead.`,
	};
}

export default function prewalkExtension(pi: ExtensionAPI) {
	let armed: ArmedPrewalk | undefined;
	let planInjected = false;
	let continuePending = false;
	let todoSeen = false;
	let sessionDefaultProfile: string | undefined;
	let config = loadPrewalkConfig();

	pi.registerFlag("prewalk", {
		description: "Arm prewalk: switch to the default execution profile at the first edit/write (todo-gated)",
		type: "boolean",
		default: false,
	});
	pi.registerFlag("prewalk-into", {
		description: "Arm prewalk into a profile name or provider/id[:thinking]",
		type: "string",
	});

	function reloadConfig(): LoadedConfig {
		config = loadPrewalkConfig();
		return config;
	}

	function resetState(): void {
		armed = undefined;
		planInjected = false;
		continuePending = false;
		todoSeen = false;
	}

	function steerPlanNudge(): void {
		pi.sendMessage(
			{
				customType: PREWALK_PLAN_MESSAGE_TYPE,
				content: PREWALK_PLAN_PROMPT,
				display: false,
			},
			{ deliverAs: "steer" },
		);
	}

	function arm(target: Model<Api>, thinkingLevel: ThinkingLevel | undefined, profileName: string | undefined, ctx: ExtensionContext): void {
		if (armed) {
			ctx.ui.notify(
				`Prewalk: already armed for ${modelLabel(armed.target)}, waiting for the first edit/write.`,
				"info",
			);
			return;
		}
		armed = { target, thinkingLevel, profileName };
		planInjected = true;
		continuePending = true;
		steerPlanNudge();
		const profileSuffix = profileName ? ` (profile ${profileName})` : "";
		const thinkingSuffix = thinkingLevel ? ` with ${thinkingLevel} thinking` : "";
		ctx.ui.notify(
			`Prewalk: armed for ${modelLabel(target)}${thinkingSuffix}${profileSuffix} — will switch at the first edit/write once the todo list exists.`,
			"info",
		);
	}

	async function armFromSpec(spec: string | undefined, ctx: ExtensionContext): Promise<void> {
		reloadConfig();
		const resolved = await resolveTarget(ctx, spec, config, sessionDefaultProfile);
		if (resolved.error || !resolved.model) {
			ctx.ui.notify(`Prewalk: ${resolved.error ?? "could not resolve target model"}`, "error");
			return;
		}
		if (resolved.warning) {
			ctx.ui.notify(`Prewalk: ${resolved.warning}`, "warning");
		}
		arm(resolved.model, resolved.thinkingLevel, resolved.profileName, ctx);
	}

	pi.on("session_start", async (_event, ctx) => {
		resetState();
		sessionDefaultProfile = undefined;
		reloadConfig();
		const into = pi.getFlag("prewalk-into");
		const enabled = pi.getFlag("prewalk") === true || (typeof into === "string" && into.length > 0);
		if (!enabled) return;
		const spec = typeof into === "string" && into.length > 0 ? into : undefined;
		await armFromSpec(spec, ctx);
	});

	pi.registerCommand("prewalk", {
		description:
			"Switch to a configured execution profile (or ad-hoc model) at the first edit/write (todo-gated). Try: /prewalk profiles",
		handler: async (args, ctx) => {
			const arg = args?.trim() ?? "";
			const lower = arg.toLowerCase();

			if (lower === "off" || lower === "disable") {
				if (!armed) {
					ctx.ui.notify("Prewalk: not armed.", "info");
					return;
				}
				armed = undefined;
				continuePending = false;
				planInjected = false;
				ctx.ui.notify("Prewalk: disarmed.", "info");
				return;
			}

			if (lower === "status") {
				reloadConfig();
				const activeDefault = sessionDefaultProfile ?? config.defaultProfile;
				const armedText = armed
					? `armed for ${modelLabel(armed.target)}${armed.thinkingLevel ? ` with ${armed.thinkingLevel} thinking` : ""}${armed.profileName ? ` (profile ${armed.profileName})` : ""} (todo seen: ${todoSeen})`
					: "not armed";
				ctx.ui.notify(
					`Prewalk: ${armedText}. Default profile: ${activeDefault}. Profiles: ${Object.keys(config.profiles).sort().join(", ") || "(none)"}.`,
					"info",
				);
				return;
			}

			if (lower === "profiles" || lower === "list") {
				reloadConfig();
				const activeDefault = sessionDefaultProfile ?? config.defaultProfile;
				const lines = Object.entries(config.profiles)
					.sort(([a], [b]) => a.localeCompare(b))
					.map(([name, profile]) => {
						const mark = name === activeDefault ? "*" : " ";
						return `${mark} ${profileLabel(name, profile)}`;
					});
				const userPath = join(agentDir(), "prewalk-profiles.json");
				ctx.ui.notify(
					[
						"Prewalk profiles (* = default for /prewalk):",
						...lines,
						`User overrides: ${userPath}`,
						"Switch: /prewalk <profile> | /prewalk default <profile> | /prewalk <provider/model>[:level]",
					].join("\n"),
					"info",
				);
				return;
			}

			if (lower === "default" || lower.startsWith("default ")) {
				reloadConfig();
				const rest = arg.slice("default".length).trim();
				if (!rest) {
					const activeDefault = sessionDefaultProfile ?? config.defaultProfile;
					ctx.ui.notify(
						`Prewalk: default profile is ${activeDefault}. Set with /prewalk default <name>. Persist in ${join(agentDir(), "prewalk-profiles.json")}.`,
						"info",
					);
					return;
				}
				const name = rest.toLowerCase();
				if (!config.profiles[name]) {
					ctx.ui.notify(
						`Prewalk: unknown profile "${rest}". Known: ${Object.keys(config.profiles).sort().join(", ")}`,
						"error",
					);
					return;
				}
				sessionDefaultProfile = name;
				ctx.ui.notify(
					`Prewalk: session default profile is now ${name} (${profileLabel(name, config.profiles[name])}).`,
					"info",
				);
				return;
			}

			await armFromSpec(arg.length > 0 ? arg : undefined, ctx);
		},
	});

	pi.on("turn_end", async (event, ctx) => {
		if (!armed) return;
		const message = event.message;
		if (!message || message.role !== "assistant") return;

		const toolResults = event.toolResults ?? [];
		if (toolResults.some((result) => !result.isError && result.toolName === "todo")) {
			todoSeen = true;
		}

		const hasToolResults = toolResults.length > 0;
		if (planInjected && hasToolResults) {
			continuePending = true;
		} else if (continuePending) {
			continuePending = false;
			pi.sendMessage(
				{
					customType: PREWALK_CONTINUE_MESSAGE_TYPE,
					content: PREWALK_CONTINUE_PROMPT,
					display: false,
				},
				{ deliverAs: "steer" },
			);
		}

		const todoGateOpen = todoSeen || !pi.getActiveTools().includes("todo");
		const action = todoGateOpen
			? toolResults.find((result) => !result.isError && PREWALK_ACTION_TOOLS[result.toolName])
			: undefined;

		if (!action) {
			if (!planInjected) {
				planInjected = true;
				continuePending = true;
				steerPlanNudge();
				ctx.ui.notify("Prewalk: injected deep-plan nudge.", "info");
			}
			return;
		}

		const target = armed.target;
		const targetThinkingLevel = armed.thinkingLevel;
		const profileName = armed.profileName;
		if (modelsAreEqual(ctx.model as Model<Api> | undefined, target)) {
			armed = undefined;
			continuePending = false;
			return;
		}

		const switched = await pi.setModel(target);
		if (!switched) {
			ctx.ui.notify(`Prewalk: no API key for ${modelLabel(target)}; staying on current model.`, "warning");
			armed = undefined;
			continuePending = false;
			return;
		}
		if (targetThinkingLevel) {
			pi.setThinkingLevel(targetThinkingLevel);
		}
		armed = undefined;
		const profileSuffix = profileName ? ` (profile ${profileName})` : "";
		ctx.ui.notify(
			`Prewalk: switched to ${modelLabel(target)}${targetThinkingLevel ? ` with ${targetThinkingLevel} thinking` : ""}${profileSuffix} after first ${action.toolName} call.`,
			"info",
		);
		pi.sendMessage(
			{
				customType: PREWALK_CHECKLIST_MESSAGE_TYPE,
				content: PREWALK_CHECKLIST_PROMPT,
				display: false,
			},
			{ deliverAs: "steer" },
		);
	});

	pi.on("context", async (event) => {
		if (armed) return;
		const messages = event.messages.filter(
			(m) =>
				!(
					m.role === "custom" &&
					(m.customType === PREWALK_PLAN_MESSAGE_TYPE || m.customType === PREWALK_CONTINUE_MESSAGE_TYPE)
				),
		);
		if (messages.length === event.messages.length) return;
		return { messages };
	});
}
