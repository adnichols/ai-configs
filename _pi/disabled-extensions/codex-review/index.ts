import { StringEnum } from "@mariozechner/pi-ai";
import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { Text } from "@mariozechner/pi-tui";
import { Type } from "@sinclair/typebox";
import path from "node:path";
import {
  CodexReviewJobManager,
  defaultCacheDir,
  defaultLauncherPath,
  isForbiddenDirectReviewToolCall,
  outcomeGuidance,
  type JobSnapshot,
  type ReviewType,
  type VerdictProfile,
} from "./runtime.ts";

const Params = Type.Object({
  action: StringEnum(["start", "smoke", "list", "status", "cancel"] as const),
  reviewType: Type.Optional(StringEnum(["implementation-review", "adversarial-implementation-review", "plan-review"] as const)),
  verdictProfile: Type.Optional(StringEnum(["pre-pr-implementation", "run-plan-pm", "reviewed-html-plan", "generic-implementation", "generic-plan"] as const)),
  promptFile: Type.Optional(Type.String()),
  output: Type.Optional(Type.String()),
  cwd: Type.Optional(Type.String()),
  jobId: Type.Optional(Type.String()),
});
type ParamsType = {
  action: "start" | "smoke" | "list" | "status" | "cancel";
  reviewType?: ReviewType;
  verdictProfile?: VerdictProfile;
  promptFile?: string;
  output?: string;
  cwd?: string;
  jobId?: string;
};
type AttachedReview = { resolve: (job: JobSnapshot) => void; detached: boolean; completion?: JobSnapshot };

const TERMINAL = new Set(["succeeded", "failed", "timed_out", "cancelled", "interrupted"]);
const required = (value: string | undefined, name: string) => {
  if (!value?.trim()) throw new Error(`${name} is required`);
  return value;
};
const resolve = (value: string, cwd: string) => path.resolve(cwd, value.startsWith("@") ? value.slice(1) : value);
function format(job: JobSnapshot): string {
  return `${job.jobId} status=${job.status}${job.classification ? ` classification=${job.classification}` : ""}${job.verdict ? ` verdict=${job.verdict}` : ""}\n${outcomeGuidance(job)}`;
}
function runningText(job: JobSnapshot): string {
  const pid = job.pid ? ` pid=${job.pid}` : "";
  return `Codex reviewer subprocess running.\njobId=${job.jobId}${pid}\noutput=${job.output}\nThe agent is waiting for this reviewer and will continue automatically when it exits.`;
}

export default function codexReviewExtension(pi: ExtensionAPI) {
  const attached = new Map<string, AttachedReview>();
  let activeContext: ExtensionContext | undefined;

  const setRunningStatus = (job?: JobSnapshot) => {
    if (!activeContext?.hasUI) return;
    activeContext.ui.setStatus(
      "codex-review",
      job ? activeContext.ui.theme.fg("warning", `◐ Codex reviewer ${job.jobId}${job.pid ? ` pid:${job.pid}` : ""}`) : undefined,
    );
  };

  const sendCompletion = (job: JobSnapshot) => {
    pi.sendMessage({
      customType: "codex-review-completion",
      content: `Codex review background job completed.\n${format(job)}\nRead and triage the artifact; infrastructure success is not itself a clean gate verdict.`,
      display: true,
      details: job,
    }, { triggerTurn: true, deliverAs: "followUp" });
  };

  const manager = new CodexReviewJobManager({
    launcherPath: defaultLauncherPath(),
    cacheDir: defaultCacheDir(),
    onComplete: (job) => {
      const waiter = attached.get(job.jobId);
      if (waiter) {
        waiter.completion = job;
        if (waiter.detached) {
          attached.delete(job.jobId);
          sendCompletion(job);
        } else {
          waiter.resolve(job);
        }
      } else {
        sendCompletion(job);
      }
      setRunningStatus(manager.list().find((candidate) => candidate.status === "running" && candidate.originSessionId === activeContext?.sessionManager.getSessionId()));
    },
  });

  pi.on("session_start", async (_event, ctx) => {
    activeContext = ctx;
    await manager.activate(ctx.sessionManager.getSessionId());
  });
  pi.on("message_start", (event) => {
    const message = event.message as any;
    const customDelivery = message?.role === "custom" && message.customType === "codex-review-completion"
      ? message.details?.deliveryId
      : undefined;
    const toolDelivery = message?.role === "toolResult" && message.toolName === "codex_review" && message.details?.phase === "completed"
      ? message.details?.job?.deliveryId
      : undefined;
    const deliveryId = customDelivery ?? toolDelivery;
    if (typeof deliveryId === "string") manager.confirmDelivery(deliveryId);
  });
  pi.on("tool_call", (event) => {
    const result = isForbiddenDirectReviewToolCall(event.toolName, event.input);
    return result.blocked ? { block: true, reason: result.reason! } : undefined;
  });
  pi.on("session_shutdown", () => manager.shutdown());

  pi.registerTool({
    name: "codex_review",
    label: "Codex Review",
    description: "Run deterministic required Codex reviews as visible managed subprocess tool calls with final-message validation and classified completion.",
    promptSnippet: "Start, inspect, or cancel visible managed Codex review subprocesses",
    promptGuidelines: [
      "Use codex_review for required Pi Codex reviews.",
      "Write a bounded prompt file and select the workflow-specific verdictProfile.",
      "Immediately before codex_review action=start, tell the user that the Codex reviewer subprocess is starting and that you will wait for it.",
      "codex_review action=start remains visibly running and does not return until the reviewer exits; then read the artifact and interpret its verdict separately from infrastructure completion.",
    ],
    parameters: Params,
    async execute(_id, params: ParamsType, signal, onUpdate, ctx: ExtensionContext) {
      activeContext = ctx;
      const originSessionId = ctx.sessionManager?.getSessionId?.();
      await manager.activate(originSessionId);
      if (params.action === "list") {
        const jobs = manager.list();
        return { content: [{ type: "text", text: jobs.length ? jobs.map(format).join("\n\n") : "No Codex review jobs." }], details: { action: "list", jobs } };
      }
      if (params.action === "status") {
        const job = manager.status(required(params.jobId, "jobId"));
        if (!job) throw new Error("Codex review job not found");
        return { content: [{ type: "text", text: format(job) }], details: { action: "status", job } };
      }
      if (params.action === "cancel") {
        const id = required(params.jobId, "jobId");
        if (!await manager.cancel(id)) throw new Error(`Codex review job is not running: ${id}`);
        return { content: [{ type: "text", text: `Cancellation requested for ${id}.` }], details: { action: "cancel", job: manager.status(id) } };
      }

      const cwd = resolve(params.cwd ?? ctx.cwd, ctx.cwd);
      const output = resolve(required(params.output, "output"), cwd);
      const promptFile = params.action === "start" ? resolve(required(params.promptFile, "promptFile"), cwd) : undefined;
      let accepted: JobSnapshot | undefined;
      let resolveTerminal!: (job: JobSnapshot) => void;
      let rejectAbort!: (error: Error) => void;
      const terminal = new Promise<JobSnapshot>((resolvePromise) => { resolveTerminal = resolvePromise; });
      const aborted = new Promise<never>((_resolve, reject) => { rejectAbort = reject; });
      let interval: ReturnType<typeof setInterval> | undefined;
      let abortHandler: (() => void) | undefined;
      try {
        const job = await manager.start({
          action: params.action,
          reviewType: params.reviewType,
          verdictProfile: params.verdictProfile,
          cwd,
          promptFile,
          output,
          originSessionId,
          onAccepted: (candidate) => {
            accepted = candidate;
            attached.set(candidate.jobId, { resolve: resolveTerminal, detached: false });
          },
        });
        accepted ??= job;
        if (TERMINAL.has(job.status)) resolveTerminal(job);
        setRunningStatus(job);
        const emitUpdate = () => {
          const current = manager.status(job.jobId) ?? job;
          onUpdate?.({ content: [{ type: "text", text: runningText(current) }], details: { action: params.action, phase: "running", job: current } });
        };
        emitUpdate();
        interval = setInterval(emitUpdate, 1_000);
        abortHandler = () => {
          const waiter = attached.get(job.jobId);
          if (waiter) {
            waiter.detached = true;
            if (waiter.completion) {
              attached.delete(job.jobId);
              sendCompletion(waiter.completion);
            }
          }
          rejectAbort(Object.assign(new Error(`Codex reviewer ${job.jobId} continues under the managed controller; completion will be reported automatically.`), { name: "AbortError" }));
        };
        if (signal?.aborted) abortHandler();
        else signal?.addEventListener("abort", abortHandler, { once: true });
        const completed = await Promise.race([terminal, aborted]);
        return {
          content: [{ type: "text", text: `Codex reviewer subprocess completed.\n${format(completed)}\nRead and triage the artifact now; infrastructure success is not itself a clean gate verdict.` }],
          details: { action: params.action, phase: "completed", job: completed },
        };
      } finally {
        if (interval) clearInterval(interval);
        if (abortHandler) signal?.removeEventListener("abort", abortHandler);
        if (accepted) {
          const waiter = attached.get(accepted.jobId);
          if (waiter && !waiter.detached) attached.delete(accepted.jobId);
        }
        setRunningStatus(manager.list().find((candidate) => candidate.status === "running" && candidate.originSessionId === originSessionId));
      }
    },
    renderCall(args, theme) {
      return new Text(theme.fg("toolTitle", theme.bold("Codex reviewer subprocess ")) + theme.fg("muted", args.action), 0, 0);
    },
    renderResult(result, { isPartial }, theme) {
      const job = result.details?.job as JobSnapshot | undefined;
      if (isPartial && job) return new Text(theme.fg("warning", `◐ running ${job.jobId}${job.pid ? ` pid=${job.pid}` : ""} — agent waiting`), 0, 0);
      if (job) {
        const color = job.status === "succeeded" ? "success" : "warning";
        return new Text(theme.fg(color, `✓ ${job.jobId} ${job.status}${job.verdict ? ` verdict=${job.verdict}` : ""}`), 0, 0);
      }
      return new Text(result.content.map((part: any) => part.type === "text" ? part.text : "").join("\n"), 0, 0);
    },
  });
}
