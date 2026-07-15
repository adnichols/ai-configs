import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";

type AgentToolInput = {
	subagent_type?: unknown;
	thinking?: unknown;
};

export type GuardResult = {
	action: "unchanged" | "pinned" | "removed";
	agent?: string;
	requested?: string;
	configured?: string;
	profilePath?: string;
};

const SAFE_AGENT_NAME = /^[A-Za-z0-9._-]+$/;
const FRONTMATTER_END = /^---\s*$/m;
const EFFORT_LINE = /^(?:reasoningEffort|thinking):\s*["']?([^\s"']+)["']?\s*$/m;
const VALID_EFFORTS = new Set([
	"off",
	"minimal",
	"low",
	"medium",
	"high",
	"xhigh",
	"max",
]);

export function configuredThinking(markdown: string): string | undefined {
	if (!markdown.startsWith("---")) return undefined;
	const remainder = markdown.slice(3).replace(/^\r?\n/, "");
	const end = FRONTMATTER_END.exec(remainder);
	if (!end) return undefined;
	const effort = remainder.slice(0, end.index).match(EFFORT_LINE)?.[1];
	return effort && VALID_EFFORTS.has(effort) ? effort : undefined;
}

export function findAgentProfile(
	agent: string,
	cwd: string,
	home = homedir(),
	configDirName = ".pi",
	allowProjectProfile = true,
): string | undefined {
	if (!SAFE_AGENT_NAME.test(agent)) return undefined;
	const candidates = allowProjectProfile
		? [
				join(cwd, configDirName, "agents", `${agent}.md`),
				join(home, configDirName, "agent", "agents", `${agent}.md`),
			]
		: [join(home, configDirName, "agent", "agents", `${agent}.md`)];
	return candidates.find((candidate) => existsSync(candidate));
}

export function enforceAgentThinking(
	input: AgentToolInput,
	cwd: string,
	home = homedir(),
	configDirName = ".pi",
	allowProjectProfile = true,
): GuardResult {
	const agent =
		typeof input.subagent_type === "string" ? input.subagent_type : undefined;
	if (!agent) return { action: "unchanged" };

	const profilePath = findAgentProfile(
		agent,
		cwd,
		home,
		configDirName,
		allowProjectProfile,
	);
	if (!profilePath) return { action: "unchanged", agent };

	const requested =
		typeof input.thinking === "string" ? input.thinking : undefined;
	const configured = configuredThinking(readFileSync(profilePath, "utf8"));

	if (configured) {
		if (requested === configured) {
			return {
				action: "unchanged",
				agent,
				requested,
				configured,
				profilePath,
			};
		}
		input.thinking = configured;
		return {
			action: "pinned",
			agent,
			requested,
			configured,
			profilePath,
		};
	}

	if ("thinking" in input) {
		delete input.thinking;
		return { action: "removed", agent, requested, profilePath };
	}

	return { action: "unchanged", agent, profilePath };
}

export function installSubagentReasoningGuard(
	pi: { on: (event: string, handler: (event: any, ctx: any) => void) => void },
	configDirName = ".pi",
): void {
	pi.on("tool_call", (event, ctx) => {
		if (event.toolName !== "Agent") return;

		const result = enforceAgentThinking(
			event.input as AgentToolInput,
			ctx.cwd,
			homedir(),
			configDirName,
			ctx.isProjectTrusted?.() ?? false,
		);
		if (result.action === "pinned") {
			ctx.ui.notify(
				`Pinned ${result.agent} reasoning to ${result.configured}` +
					(result.requested ? ` (rejected ${result.requested})` : ""),
				"warning",
			);
		} else if (result.action === "removed") {
			ctx.ui.notify(
				`Removed unauthorized reasoning override for ${result.agent}`,
				"warning",
			);
		}
	});
}
