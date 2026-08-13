// Pi tool mirror of `delivery reflect` — logs end-of-run process reflections
// outside the worktree to ~/.pi (same destinations as the delivery CLI).
import { spawn } from "node:child_process";
import { access } from "node:fs/promises";
import { homedir } from "node:os";
import { join } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";
import { Text } from "@earendil-works/pi-tui";
import { Type } from "typebox";

const reflectSchema = Type.Object(
	{
		friction: Type.Optional(
			Type.Array(Type.String(), {
				description: "Observed process friction items.",
			}),
		),
		rework: Type.Optional(
			Type.Array(Type.String(), {
				description: "Rework challenges encountered.",
			}),
		),
		improvements: Type.Optional(
			Type.Array(Type.String(), {
				description: "Improvement opportunities for later processing.",
			}),
		),
		notes: Type.Optional(
			Type.Array(Type.String(), {
				description: "Additional freeform notes.",
			}),
		),
		outcome: Type.Optional(
			Type.String({
				description: "Short outcome label, e.g. done, pr-opened, blocked.",
			}),
		),
		trigger: Type.Optional(
			Type.String({
				description: "Short trigger label, e.g. end-of-run.",
			}),
		),
		markDone: Type.Optional(
			Type.Boolean({
				description: "If true, set delivery ledger stage to DONE after logging.",
			}),
		),
		allowUntracked: Type.Optional(
			Type.Boolean({
				description: "Allow logging when no worktree ledger exists.",
			}),
		),
		cwd: Type.Optional(
			Type.String({
				description: "Worktree cwd override (defaults to session cwd).",
			}),
		),
	},
	{ additionalProperties: false },
);

async function resolveDeliveryBin(): Promise<string | null> {
	const candidates = [
		join(homedir(), ".local", "bin", "delivery"),
		join(homedir(), ".agents", "scripts", "delivery"),
		join(homedir(), ".agents", "skills", "delivery-run", "scripts", "delivery"),
	];
	for (const candidate of candidates) {
		try {
			await access(candidate);
			return candidate;
		} catch {
			// try next
		}
	}
	return null;
}

function runDelivery(
	bin: string,
	args: string[],
	cwd: string | undefined,
	signal: AbortSignal | undefined,
): Promise<{ code: number; stdout: string; stderr: string }> {
	return new Promise((resolve) => {
		const child = spawn(bin, args, {
			cwd: cwd || process.cwd(),
			env: {
				...process.env,
				DELIVERY_SKIP_HERDR: process.env.DELIVERY_SKIP_HERDR || "1",
			},
			stdio: ["ignore", "pipe", "pipe"],
		});
		let stdout = "";
		let stderr = "";
		const onAbort = () => {
			try {
				child.kill("SIGTERM");
			} catch {
				// ignore
			}
		};
		if (signal) {
			if (signal.aborted) onAbort();
			else signal.addEventListener("abort", onAbort, { once: true });
		}
		child.stdout.on("data", (chunk) => {
			stdout += String(chunk);
		});
		child.stderr.on("data", (chunk) => {
			stderr += String(chunk);
		});
		child.on("error", (err) => {
			resolve({ code: 1, stdout, stderr: `${stderr}\n${err}`.trim() });
		});
		child.on("close", (code) => {
			resolve({ code: code ?? 1, stdout, stderr });
		});
	});
}

export default function deliveryReflectExtension(pi: ExtensionAPI) {
	pi.registerTool({
		name: "delivery_reflect",
		label: "delivery_reflect",
		description:
			"Append an end-of-run delivery reflection to ~/.pi/DELIVERY_REFLECTIONS.md and ~/.pi/delivery-reflections.jsonl (outside the worktree).",
		promptSnippet: "Log delivery-run friction/rework/improvements at end of workflow.",
		promptGuidelines: [
			"delivery_reflect: Call only when a delivery ledger already exists, near the end of that delivery run before DONE.",
			"delivery_reflect: Skip when there is no .delivery/ledger.json. Do not bootstrap, init, or arm delivery to satisfy this tool.",
			"delivery_reflect: Capture process friction, rework challenges, and improvement opportunities — not ordinary code bugs.",
			"delivery_reflect: Prefer structured friction/rework/improvements arrays; keep notes short.",
			"delivery_reflect: Logs live outside the worktree under ~/.pi for later processing (like vent).",
			"delivery_reflect: Guidance not gates — missing reflection must not hard-block shipping.",
			"delivery_reflect: Do not use this as a substitute for finishing the task.",
		],
		parameters: reflectSchema,
		executionMode: "sequential",

		async execute(_toolCallId, params, signal, _onUpdate, ctx) {
			const bin = await resolveDeliveryBin();
			if (!bin) {
				throw new Error(
					"delivery CLI not found. Install ai-configs shared skills (delivery-run) or ensure ~/.local/bin/delivery exists.",
				);
			}

			const cwd =
				(typeof params.cwd === "string" && params.cwd.trim()) ||
				(typeof (ctx as { cwd?: unknown })?.cwd === "string"
					? String((ctx as { cwd?: string }).cwd)
					: process.cwd());

			const args: string[] = [
				"--cwd",
				cwd,
				"reflect",
				"--trigger",
				params.trigger?.trim() || "end-of-run",
			];
			if (params.outcome?.trim()) {
				args.push("--outcome", params.outcome.trim());
			}
			for (const item of params.friction || []) {
				if (item.trim()) args.push("--friction", item.trim());
			}
			for (const item of params.rework || []) {
				if (item.trim()) args.push("--rework", item.trim());
			}
			for (const item of params.improvements || []) {
				if (item.trim()) args.push("--improvement", item.trim());
			}
			for (const item of params.notes || []) {
				if (item.trim()) args.push("--note", item.trim());
			}
			if (params.markDone) args.push("--mark-done");
			if (params.allowUntracked) args.push("--allow-untracked");
			args.push("--json");

			const hasBody =
				(params.friction && params.friction.length) ||
				(params.rework && params.rework.length) ||
				(params.improvements && params.improvements.length) ||
				(params.notes && params.notes.length) ||
				params.outcome;
			if (!hasBody) {
				throw new Error(
					"delivery_reflect requires at least one of friction, rework, improvements, notes, or outcome",
				);
			}

			const result = await runDelivery(bin, args, cwd, signal);
			if (result.code !== 0) {
				throw new Error(
					result.stderr || result.stdout || `delivery reflect failed (${result.code})`,
				);
			}

			let details: Record<string, unknown> = {};
			try {
				details = JSON.parse(result.stdout) as Record<string, unknown>;
			} catch {
				details = { raw: result.stdout.trim() };
			}

			const ts =
				typeof details.timestamp === "string" ? details.timestamp : "saved";
			const md =
				typeof details.markdownPath === "string"
					? details.markdownPath
					: join(homedir(), ".pi", "DELIVERY_REFLECTIONS.md");

			return {
				content: [
					{
						type: "text" as const,
						text: `Appended delivery reflection to ${md} (${ts}).`,
					},
				],
				details,
			};
		},

		renderCall(args, theme) {
			const outcome =
				typeof args?.outcome === "string" && args.outcome.trim()
					? ` ${args.outcome.trim()}`
					: "";
			return new Text(
				`${theme.fg("toolTitle", theme.bold("delivery_reflect"))}${theme.fg("muted", outcome)}`,
				0,
				0,
			);
		},

		renderResult(result, { expanded }, theme) {
			const details = result.details as
				| { timestamp?: unknown; markdownPath?: unknown; record?: unknown }
				| undefined;
			const timestamp =
				typeof details?.timestamp === "string" ? details.timestamp : "saved";
			let text = `${theme.fg("success", "✓")} wrote ${theme.fg("accent", "~/.pi/DELIVERY_REFLECTIONS.md")} ${theme.fg("dim", timestamp)}`;
			if (expanded && details?.record) {
				text += `\n\n${JSON.stringify(details.record, null, 2)}`;
			}
			return new Text(text, 0, 0);
		},
	});
}
