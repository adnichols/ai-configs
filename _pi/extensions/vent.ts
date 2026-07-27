// Vendored from @howaboua/pi-vent so all Pi sessions share one log.
//
// MIT License
// Copyright (c) 2026 Igor Warzocha
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.
import { appendFile, mkdir, readFile, writeFile } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";
import {
	type ExtensionAPI,
	withFileMutationQueue,
} from "@earendil-works/pi-coding-agent";
import { Text } from "@earendil-works/pi-tui";
import { Type } from "typebox";

const VENT_DIRECTORY = join(homedir(), ".pi");
const VENT_PATH = join(VENT_DIRECTORY, "VENT.md");

const ventSchema = Type.Object(
	{
		thought: Type.String({
			description: "Vent entry text.",
		}),
		trigger: Type.Optional(
			Type.String({ description: "Optional short trigger label." }),
		),
	},
	{ additionalProperties: false },
);

function clean(input: string): string {
	return input.trim().replace(/\r\n/g, "\n");
}

async function fileExists(path: string): Promise<boolean> {
	try {
		await readFile(path, "utf8");
		return true;
	} catch (error: unknown) {
		if ((error as NodeJS.ErrnoException).code === "ENOENT") return false;
		throw error;
	}
}

export default function ventExtension(pi: ExtensionAPI) {
	pi.registerTool({
		name: "vent",
		label: "vent",
		description: "Append workflow-friction feedback to ~/.pi/VENT.md.",
		promptSnippet: "Log repeated workflow friction.",
		promptGuidelines: [
			"vent: Use for repeated or systemic workflow friction, especially when the same manual workaround happens more than once.",
			"vent: Use after a second hook/tool failure with the same root cause, or when tool output forces the same retry sequence.",
			"vent: Use when project instructions, docs, or tooling cause avoidable backtracking that should become automation, docs, or workflow fixes.",
			"vent: Do not use for one-off lint/type errors or ordinary coding mistakes.",
			"vent: Call near the end of the turn after completing the task; batch related feedback instead of calling repeatedly.",
			"vent: Include what failed, what workaround was repeated, and what would prevent it next time; never use vent as a substitute for finishing the task.",
		],
		parameters: ventSchema,
		executionMode: "sequential",

		async execute(_toolCallId, params) {
			const thought = clean(params.thought);
			if (!thought) throw new Error("vent.thought must not be empty");

			const trigger = params.trigger ? clean(params.trigger) : undefined;
			const now = new Date();
			const timestamp =
				[
					String(now.getFullYear()).slice(-2),
					String(now.getMonth() + 1).padStart(2, "0"),
					String(now.getDate()).padStart(2, "0"),
				].join("-") +
				" " +
				[
					String(now.getHours()).padStart(2, "0"),
					String(now.getMinutes()).padStart(2, "0"),
				].join(":");
			const heading =
				"# VENT\n\nFeedback log. Repeated/systemic workflow friction that should become future automation, docs, or workflow fixes.\n\n";
			const entry = [
				`## ${timestamp}${trigger ? ` — ${trigger}` : ""}`,
				"",
				thought,
				"",
			].join("\n");

			return withFileMutationQueue(VENT_PATH, async () => {
				await mkdir(VENT_DIRECTORY, { recursive: true });
				if (!(await fileExists(VENT_PATH))) {
					await writeFile(VENT_PATH, heading, "utf8");
				}
				await appendFile(VENT_PATH, entry, "utf8");

				return {
					content: [
						{
							type: "text" as const,
							text: `Appended vent entry to ~/.pi/VENT.md (${timestamp}).`,
						},
					],
					details: { path: VENT_PATH, timestamp, trigger, thought },
				};
			});
		},

		renderCall(args, theme, _context) {
			const trigger =
				typeof args?.trigger === "string" && args.trigger.trim()
					? ` ${args.trigger.trim()}`
					: "";
			return new Text(
				`${theme.fg("toolTitle", theme.bold("vent"))}${theme.fg("muted", trigger)}`,
				0,
				0,
			);
		},

		renderResult(result, { expanded }, theme) {
			const details = result.details as
				| { timestamp?: unknown; thought?: unknown }
				| undefined;
			const timestamp =
				typeof details?.timestamp === "string" ? details.timestamp : "saved";
			let text = `${theme.fg("success", "✓")} wrote ${theme.fg("accent", "~/.pi/VENT.md")} ${theme.fg("dim", timestamp)}`;

			if (expanded && typeof details?.thought === "string") {
				text += `\n\n${details.thought}`;
			}

			return new Text(text, 0, 0);
		},
	});
}
