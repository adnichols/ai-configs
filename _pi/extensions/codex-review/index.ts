import { StringEnum } from "@mariozechner/pi-ai";
import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { Type } from "@sinclair/typebox";
import path from "node:path";
import { CodexReviewJobManager, defaultCacheDir, defaultLauncherPath, isForbiddenDirectReviewToolCall, outcomeGuidance, type JobSnapshot, type ReviewType, type VerdictProfile } from "./runtime.ts";

const Params = Type.Object({
  action: StringEnum(["start", "smoke", "list", "status", "cancel"] as const),
  reviewType: Type.Optional(StringEnum(["implementation-review", "adversarial-implementation-review", "plan-review"] as const)),
  verdictProfile: Type.Optional(StringEnum(["pre-pr-implementation", "run-plan-pm", "reviewed-html-plan", "generic-implementation", "generic-plan"] as const)),
  promptFile: Type.Optional(Type.String()), output: Type.Optional(Type.String()), cwd: Type.Optional(Type.String()), jobId: Type.Optional(Type.String()),
});
type ParamsType = { action: "start" | "smoke" | "list" | "status" | "cancel"; reviewType?: ReviewType; verdictProfile?: VerdictProfile; promptFile?: string; output?: string; cwd?: string; jobId?: string };
const required = (value: string | undefined, name: string) => { if (!value?.trim()) throw new Error(`${name} is required`); return value; };
const resolve = (value: string, cwd: string) => path.resolve(cwd, value.startsWith("@") ? value.slice(1) : value);
function format(job: JobSnapshot): string { return `${job.jobId} status=${job.status}${job.classification ? ` classification=${job.classification}` : ""}${job.verdict ? ` verdict=${job.verdict}` : ""}\n${outcomeGuidance(job)}`; }

export default function codexReviewExtension(pi: ExtensionAPI) {
  const manager = new CodexReviewJobManager({ launcherPath: defaultLauncherPath(), cacheDir: defaultCacheDir(), onComplete: (job) => { pi.sendMessage({ customType: "codex-review-completion", content: `Codex review background job completed.\n${format(job)}\nRead and triage the artifact; infrastructure success is not itself a clean gate verdict.`, display: true, details: job }, { triggerTurn: true, deliverAs: "followUp" }); } });
  pi.on("session_start", () => manager.activate());
  pi.on("message_start", (event) => { const message = event.message as any; if (message?.role === "custom" && message.customType === "codex-review-completion" && typeof message.details?.deliveryId === "string") manager.confirmDelivery(message.details.deliveryId); });
  pi.on("tool_call", (event) => { const result = isForbiddenDirectReviewToolCall(event.toolName, event.input); return result.blocked ? { block: true, reason: result.reason! } : undefined; });
  pi.on("session_shutdown", () => manager.shutdown());
  pi.registerTool({ name: "codex_review", label: "Codex Review", description: "Run deterministic required Codex reviews invisibly in the background with final-message validation and classified completion.", promptSnippet: "Start, inspect, or cancel managed Codex review jobs", promptGuidelines: ["Use codex_review for required Pi Codex reviews.", "Write a bounded prompt file and select the workflow-specific verdictProfile.", "Read the artifact and interpret its verdict separately from infrastructure completion."], parameters: Params,
    async execute(_id, params: ParamsType, _signal, _update, ctx: ExtensionContext) {
      manager.activate(); if (params.action === "list") { const jobs = manager.list(); return { content: [{ type: "text", text: jobs.length ? jobs.map(format).join("\n\n") : "No Codex review jobs." }], details: { action: "list", jobs } }; }
      if (params.action === "status") { const job = manager.status(required(params.jobId, "jobId")); if (!job) throw new Error("Codex review job not found"); return { content: [{ type: "text", text: format(job) }], details: { action: "status", job } }; }
      if (params.action === "cancel") { const id = required(params.jobId, "jobId"); if (!await manager.cancel(id)) throw new Error(`Codex review job is not running: ${id}`); return { content: [{ type: "text", text: `Cancellation requested for ${id}.` }], details: { action: "cancel", job: manager.status(id) } }; }
      const cwd = resolve(params.cwd ?? ctx.cwd, ctx.cwd); const output = resolve(required(params.output, "output"), cwd); const promptFile = params.action === "start" ? resolve(required(params.promptFile, "promptFile"), cwd) : undefined;
      const job = await manager.start({ action: params.action, reviewType: params.reviewType, verdictProfile: params.verdictProfile, cwd, promptFile, output });
      return { content: [{ type: "text", text: `Codex ${params.action === "smoke" ? "smoke" : "review"} dispatched invisibly.\njobId=${job.jobId}\noutput=${job.output}\nCompletion will be delivered automatically.` }], details: { action: params.action, job } };
    } });
}
