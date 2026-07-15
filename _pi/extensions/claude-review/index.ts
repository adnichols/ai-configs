import { StringEnum } from "@mariozechner/pi-ai";
import type { ExtensionAPI, ExtensionContext } from "@mariozechner/pi-coding-agent";
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

function normalizePath(value: string, cwd: string): string {
  const clean = value.startsWith("@") ? value.slice(1) : value;
  return path.resolve(cwd, clean);
}

function formatJob(job: JobSnapshot): string {
  const completed = job.completedAt ? ` completed=${job.completedAt}` : "";
  const classification = job.classification ? ` classification=${job.classification}` : "";
  return `${job.jobId} status=${job.status}${classification}${completed}\noutput=${job.output}\nstate=${job.stateFile}\nstdout=${job.stdoutLog}\nstderr=${job.stderrLog}\n${job.summary}`;
}

function requireString(value: string | undefined, name: string): string {
  if (!value?.trim()) throw new Error(`${name} is required`);
  return value;
}

export default function claudeReviewExtension(pi: ExtensionAPI) {
  const manager = new ClaudeReviewJobManager({
    launcherPath: defaultLauncherPath(),
    cacheDir: defaultCacheDir(),
    onComplete: (job) => {
      pi.sendMessage({
        customType: "claude-review-completion",
        content: `Claude review background job completed.\n${formatJob(job)}\nRead and triage the output artifact; do not infer a verdict from process exit alone.`,
        display: true,
        details: job,
      }, { triggerTurn: true, deliverAs: "followUp" });
    },
  });

  pi.on("session_start", () => {
    manager.activate();
  });

  pi.on("tool_call", (event) => {
    if (!isForbiddenDirectReviewToolCall(event.toolName, event.input)) return;
    return {
      block: true,
      reason: "Direct Claude review launch is disabled. Use the claude_review tool so the review always runs through the deterministic background controller.",
    };
  });

  pi.on("session_shutdown", async () => {
    // Stop only this extension instance's observers. Detached supervisors own
    // accepted jobs so reloads, session switches, and Pi exit do not cancel them.
    await manager.shutdown();
  });

  pi.registerTool({
    name: "claude_review",
    label: "Claude Review",
    description:
      "Run required Claude Code reviews through the canonical interactive-tmux launcher under a durable detached supervisor. Jobs survive Pi session/reload lifecycle, persist terminal state, never open an overlay, and are never killed for output silence.",
    promptSnippet:
      "Start, recover, inspect, or explicitly cancel durable background Claude Code review jobs",
    promptGuidelines: [
      "Use claude_review for required Claude Code plan or implementation reviews; do not launch Claude reviews through bash, process, or interactive_shell.",
      "Before claude_review action=start, write a bounded read-only review prompt to a file and provide that promptFile plus an output artifact path.",
      "After completion, read the output artifact: transport success means a non-empty normalized review plus launcher metadata and no classified provider/launcher failure; interpret any workflow verdict separately.",
      "Use claude_review list/status after reload or restart to recover durable jobs whose original completion notification could not be delivered.",
    ],
    parameters: Params,

    async execute(_toolCallId, params: ToolParams, _signal, _onUpdate, ctx: ExtensionContext) {
      manager.activate();
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
      const job = await manager.start({ action: params.action, cwd, promptFile, output });
      return {
        content: [{
          type: "text",
          text: `Claude ${params.action === "smoke" ? "smoke" : "review"} dispatched invisibly under a detached supervisor.\njobId=${job.jobId}\noutput=${job.output}\nThe job survives Pi session/reload lifecycle. This session will be notified on completion when still available; otherwise recover it later with list/status.`,
        }],
        details: { action: params.action, job },
      };
    },
  });
}
