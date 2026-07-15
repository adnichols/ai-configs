import { afterEach, describe, expect, test } from "bun:test";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

import {
	configuredThinking,
	enforceAgentThinking,
	installSubagentReasoningGuard,
} from "../_pi/extensions/subagent-reasoning-guard/policy";

const roots: string[] = [];

function fixture(): { cwd: string; home: string } {
	const root = mkdtempSync(join(tmpdir(), "subagent-reasoning-guard-"));
	roots.push(root);
	return { cwd: join(root, "project"), home: join(root, "home") };
}

function writeProfile(
	base: string,
	agent: string,
	frontmatter: string,
	project = false,
): string {
	const directory = project
		? join(base, ".pi", "agents")
		: join(base, ".pi", "agent", "agents");
	mkdirSync(directory, { recursive: true });
	const path = join(directory, `${agent}.md`);
	writeFileSync(path, `---\n${frontmatter}\n---\nAgent instructions.\n`);
	return path;
}

afterEach(() => {
	while (roots.length > 0) rmSync(roots.pop()!, { recursive: true, force: true });
});

describe("subagent reasoning guard", () => {
	test("reads reasoningEffort and thinking frontmatter", () => {
		expect(configuredThinking("---\nreasoningEffort: high\n---\nbody")).toBe(
			"high",
		);
		expect(configuredThinking("---\nthinking: medium\n---\nbody")).toBe(
			"medium",
		);
		expect(configuredThinking("---\nthinking: unlimited\n---\nbody")).toBeUndefined();
	});

	test("pins developer-high to its configured high effort", () => {
		const { cwd, home } = fixture();
		writeProfile(home, "developer-high", "reasoningEffort: high");
		const input = { subagent_type: "developer-high", thinking: "xhigh" };

		const result = enforceAgentThinking(input, cwd, home, ".pi");

		expect(result.action).toBe("pinned");
		expect(result.requested).toBe("xhigh");
		expect(input.thinking).toBe("high");
	});

	test("project agent profile overrides the global profile", () => {
		const { cwd, home } = fixture();
		writeProfile(home, "developer-high", "reasoningEffort: xhigh");
		writeProfile(cwd, "developer-high", "reasoningEffort: high", true);
		const input = { subagent_type: "developer-high", thinking: "xhigh" };

		enforceAgentThinking(input, cwd, home, ".pi");

		expect(input.thinking).toBe("high");
	});

	test("ignores project profiles when the project is not trusted", () => {
		const { cwd, home } = fixture();
		writeProfile(home, "developer-high", "reasoningEffort: high");
		writeProfile(cwd, "developer-high", "reasoningEffort: xhigh", true);
		const input = { subagent_type: "developer-high", thinking: "xhigh" };

		enforceAgentThinking(input, cwd, home, ".pi", false);

		expect(input.thinking).toBe("high");
	});

	test("removes caller override when a profile declares no effort", () => {
		const { cwd, home } = fixture();
		writeProfile(home, "researcher", "model: kimi-k2.5");
		const input: { subagent_type: string; thinking?: string } = {
			subagent_type: "researcher",
			thinking: "xhigh",
		};

		const result = enforceAgentThinking(input, cwd, home, ".pi");

		expect(result.action).toBe("removed");
		expect(input.thinking).toBeUndefined();
	});

	test("leaves unknown built-in agent types unchanged", () => {
		const { cwd, home } = fixture();
		const input = { subagent_type: "general-purpose", thinking: "xhigh" };

		const result = enforceAgentThinking(input, cwd, home, ".pi");

		expect(result.action).toBe("unchanged");
		expect(input.thinking).toBe("xhigh");
	});

	test("mutates Agent tool input and warns when rejecting elevation", () => {
		const { cwd, home } = fixture();
		writeProfile(home, "developer-high", "reasoningEffort: high");
		const handlers: Record<string, (event: any, ctx: any) => void> = {};
		const notifications: Array<{ message: string; level: string }> = [];
		const previousHome = process.env.HOME;
		process.env.HOME = home;
		try {
			installSubagentReasoningGuard({
				on: (name: string, handler: (event: any, ctx: any) => void) => {
					handlers[name] = handler;
				},
			} as any, ".pi");
			const input = { subagent_type: "developer-high", thinking: "xhigh" };
			handlers.tool_call(
				{ toolName: "Agent", input },
				{
					cwd,
					ui: {
						notify: (message: string, level: string) =>
							notifications.push({ message, level }),
					},
				},
			);
			expect(input.thinking).toBe("high");
			expect(notifications[0]?.message).toContain("rejected xhigh");
		} finally {
			if (previousHome === undefined) delete process.env.HOME;
			else process.env.HOME = previousHome;
		}
	});
});
