import { StringEnum } from "@mariozechner/pi-ai";
import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
import { Text } from "@mariozechner/pi-tui";
import { Type } from "@sinclair/typebox";
import path from "node:path";

import {
  ClaudeReviewJobManager,
  defaultCacheDir,
  defaultLauncherPath,
  isForbiddenDirectReviewToolCall,
  type JobSnapshot,
} from "./runtime.ts";

const Params = Type.Object({
  action: StringEnum(["start", "smoke", "list", "status", "cancel"] as const, {
    description: "Start a review, run a smoke test, list jobs, inspect one job, or cancel one job.",
  }),
  promptFile: Type.Optional(Type.String({
    description: "Review prompt file. Required only for action=start. Relative paths resolve from cwd.",
  })),
  output: Type.Optional(Type.String({
    description: "Launcher output artifact. Required for action=start and action=smoke. Relative paths resolve from cwd.",
  })),
  cwd: Type.Optional(Type.String({
    description: "Repository working directory. Defaults to the current Pi working directory.",
  })),
  jobId: Type.Optional(Type.String({
    description: "Job id. Required for action=status and action=cancel.",
  })),
});

type ToolParams = {
  action: "start" | "smoke" | "list" | "status" | "cancel";
  promptFile?: string;
  output?: string;
  cwd?: string;
  jobId?: string;
};
type AttachedReview = { resolve: (job: JobSnapshot) => void; detached: boolean; completion?: JobSnapshot };

const TERMINAL = new Set(["succeeded", "failed", "timed_out", "cancelled", "interrupted"]);

function normalizePath(value: string, cwd: string): string {
  const clean = value.startsWith("@") ? value.slice(1) : value;
  return path.resolve(cwd, clean);
}

function formatJob(job: JobSnapshot): string {
  const completed = job.completedAt ? ` completed=${job.completedAt}` : "";
  const classification = job.classification ? ` classification=${job.classification}` : "";
  return `${job.jobId} status=${job.status}${classification}${completed}\noutput=${job.output}\nstate=${job.stateFile}\nstdout=${job.stdoutLog}\nstderr=${job.stderrLog}\n${job.summary}`;
}

function runningText(job: JobSnapshot): string {
  const pid = job.supervisorPid ?? job.pid;
  return `Claude reviewer subprocess running.\njobId=${job.jobId}${pid ? ` pid=${pid}` : ""}\noutput=${job.output}\nThe agent is waiting for this reviewer and will continue automatically when it exits.`;
}

function requireString(value: string | undefined, name: string): string {
  if (!value?.trim()) throw new Error(`${name} is required`);
  return value;
}

export default function claudeReviewExtension(pi: ExtensionAPI) {
  const attached = new Map<string, AttachedReview>();
  let activeContext: ExtensionContext | undefined;

  const setRunningStatus = (job?: JobSnapshot) => {
    if (!activeContext?.hasUI) return;
    const pid = job?.supervisorPid ?? job?.pid;
    activeContext.ui.setStatus(
      "claude-review",
      job ? activeContext.ui.theme.fg("warning", `◐ Claude reviewer ${job.jobId}${pid ? ` pid:${pid}` : ""}`) : undefined,
    );
  };

  const sendCompletion = (job: JobSnapshot) => {
    pi.sendMessage({
      customType: "claude-review-completion",
      content: `Claude review background job completed.\n${formatJob(job)}\nRead and triage the output artifact; do not infer a verdict from process exit alone.`,
      display: true,
      details: job,
    }, { triggerTurn: true, deliverAs: "followUp" });
  };

  const manager = new ClaudeReviewJobManager({
    launcherPath: defaultLauncherPath(),
    cacheDir: defaultCacheDir(),
    deferNotification: (job) => Boolean(attached.get(job.jobId) && !attached.get(job.jobId)?.detached),
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

  pi.on("session_start", (_event, ctx) => {
    activeContext = ctx;
    manager.activate(ctx.sessionManager.getSessionId());
    const running = manager.list().find((job) => job.status === "running" && job.originSessionId === ctx.sessionManager.getSessionId());
    setRunningStatus(running);
  });

  pi.on("message_start", (event) => {
    const message = event.message as any;
    if (message?.role === "toolResult" && message.toolName === "claude_review" && message.details?.phase === "completed" && typeof message.details?.job?.jobId === "string") {
      manager.confirmDelivery(message.details.job.jobId);
    }
  });

  pi.on("tool_call", (event) => {
    if (!isForbiddenDirectReviewToolCall(event.toolName, event.input)) return;
    return {
      block: true,
      reason: "Direct Claude review launch is disabled. Use the claude_review tool so the review always runs through the deterministic managed controller.",
    };
  });

  pi.on("session_shutdown", async () => {
    activeContext = undefined;
    await manager.shutdown();
  });

  pi.registerTool({
    name: "claude_review",
    label: "Claude Review",
    description:
      "Run required Claude Code reviews as visible managed subprocess tool calls backed by a durable detached supervisor. The tool remains visibly running until completion; accepted jobs still survive Pi session/reload lifecycle.",
    promptSnippet:
      "Start, recover, inspect, or explicitly cancel visible managed Claude Code review subprocesses",
    promptGuidelines: [
      "Use claude_review for required Claude Code plan or implementation reviews; do not launch Claude reviews through bash, process, or interactive_shell.",
      "Before claude_review action=start, write a bounded read-only review prompt to a file and provide that promptFile plus an output artifact path.",
      "Immediately before claude_review action=start, tell the user that the Claude reviewer subprocess is starting and that you will wait for it.",
      "claude_review action=start remains visibly running and does not return until the reviewer exits; then read the output artifact and interpret the workflow verdict separately from transport success.",
      "Use claude_review list/status after reload or restart to recover durable jobs whose original visible tool call was interrupted.",
    ],
    parameters: Params,

    async execute(_toolCallId, params: ToolParams, signal, onUpdate, ctx) {
      activeContext = ctx;
      const originSessionId = ctx.sessionManager?.getSessionId?.();
      const originSessionFile = ctx.sessionManager?.getSessionFile?.();
      manager.activate(originSessionId);
      if (params.action === "list") {
        const jobs = manager.list();
        return {
          content: [{ type: "text", text: jobs.length ? jobs.map(formatJob).join("\n\n") : "No persisted Claude review jobs." }],
          details: { action: "list", jobs },
        };
      }

      if (params.action === "status") {
        const jobId = requireString(params.jobId, "jobId");
        const job = manager.status(jobId);
        if (!job) throw new Error(`Claude review job not found: ${jobId}`);
        return {
          content: [{ type: "text", text: formatJob(job) }],
          details: { action: "status", job },
        };
      }

      if (params.action === "cancel") {
        const jobId = requireString(params.jobId, "jobId");
        const cancelled = await manager.cancel(jobId);
        if (!cancelled) throw new Error(`Claude review job is not running or does not exist: ${jobId}`);
        const job = manager.status(jobId);
        return {
          content: [{ type: "text", text: `Cancellation requested for ${jobId}. Completion will be reported automatically.` }],
          details: { action: "cancel", job },
        };
      }

      const cwd = normalizePath(params.cwd ?? ctx.cwd, ctx.cwd);
      const output = normalizePath(requireString(params.output, "output"), cwd);
      const promptFile = params.action === "start"
        ? normalizePath(requireString(params.promptFile, "promptFile"), cwd)
        : undefined;
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
          cwd,
          promptFile,
          output,
          originSessionId,
          originSessionFile,
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
            if (waiter.completion) manager.deliverDetached(job.jobId);
          }
          rejectAbort(Object.assign(new Error(`Claude reviewer ${job.jobId} continues under the detached supervisor; completion will be reported automatically.`), { name: "AbortError" }));
        };
        if (signal?.aborted) abortHandler();
        else signal?.addEventListener("abort", abortHandler, { once: true });
        const completed = await Promise.race([terminal, aborted]);
        return {
          content: [{ type: "text", text: `Claude reviewer subprocess completed.\n${formatJob(completed)}\nRead and triage the output artifact now; do not infer a verdict from process exit alone.` }],
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
      return new Text(theme.fg("toolTitle", theme.bold("Claude reviewer subprocess ")) + theme.fg("muted", args.action), 0, 0);
    },
    renderResult(result, { isPartial }, theme) {
      const job = result.details?.job as JobSnapshot | undefined;
      const pid = job?.supervisorPid ?? job?.pid;
      if (isPartial && job) return new Text(theme.fg("warning", `◐ running ${job.jobId}${pid ? ` pid=${pid}` : ""} — agent waiting`), 0, 0);
      if (job) {
        const color = job.status === "succeeded" ? "success" : "warning";
        return new Text(theme.fg(color, `✓ ${job.jobId} ${job.status}${job.classification ? ` ${job.classification}` : ""}`), 0, 0);
      }
      return new Text(result.content.map((part: any) => part.type === "text" ? part.text : "").join("\n"), 0, 0);
    },
  });
}
