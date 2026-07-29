import { describe, expect, it } from "vitest";
import {
	applyForcedAgentBackgroundArgs,
	getCursorGrokComposerAgentBackgroundGuidanceText,
	isCursorGrokOrComposerModelId,
	shouldForcePiAgentBackground,
} from "../src/cursor-agent-background-policy.js";

describe("cursor-agent-background-policy", () => {
	it("detects grok and composer Cursor SDK model ids", () => {
		expect(isCursorGrokOrComposerModelId("grok-4.5")).toBe(true);
		expect(isCursorGrokOrComposerModelId("Grok-4.5")).toBe(true);
		expect(isCursorGrokOrComposerModelId("composer-2.5")).toBe(true);
		expect(isCursorGrokOrComposerModelId("composer-2-5")).toBe(true);
		expect(isCursorGrokOrComposerModelId("composer-2")).toBe(true);
		expect(isCursorGrokOrComposerModelId("cursor/grok-4.5")).toBe(true);
		expect(isCursorGrokOrComposerModelId("gpt-5.5")).toBe(false);
		expect(isCursorGrokOrComposerModelId("claude-4.5-sonnet")).toBe(false);
		expect(isCursorGrokOrComposerModelId(undefined)).toBe(false);
	});

	it("forces Agent background only for grok/composer parents", () => {
		expect(shouldForcePiAgentBackground("grok-4.5")).toBe(true);
		expect(shouldForcePiAgentBackground("composer-2.5")).toBe(true);
		expect(shouldForcePiAgentBackground("gpt-5.5")).toBe(false);

		const forced = applyForcedAgentBackgroundArgs(
			"Agent",
			{ subagent_type: "reviewer", prompt: "review" },
			"grok-4.5",
		);
		expect(forced.forced).toBe(true);
		expect(forced.args).toEqual({
			subagent_type: "reviewer",
			prompt: "review",
			run_in_background: true,
		});

		const already = applyForcedAgentBackgroundArgs(
			"Agent",
			{ run_in_background: true, prompt: "review" },
			"composer-2.5",
		);
		expect(already.forced).toBe(false);
		expect(already.args.run_in_background).toBe(true);

		const otherTool = applyForcedAgentBackgroundArgs("bash", { command: "echo hi" }, "grok-4.5");
		expect(otherTool.forced).toBe(false);
		expect(otherTool.args).toEqual({ command: "echo hi" });

		const otherModel = applyForcedAgentBackgroundArgs(
			"Agent",
			{ subagent_type: "reviewer" },
			"gpt-5.5",
		);
		expect(otherModel.forced).toBe(false);
		expect(otherModel.args.run_in_background).toBeUndefined();
	});

	it("exposes join guidance for bootstrap prompts", () => {
		const text = getCursorGrokComposerAgentBackgroundGuidanceText();
		expect(text).toContain("run_in_background: true");
		expect(text).toContain("get_subagent_result");
	});
});
