import assert from "node:assert/strict";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import {
  ClaudeReviewJobManager,
  REVIEW_WATCHDOG_MS,
  SMOKE_WATCHDOG_MS,
  buildLauncherArgs,
  classifyArtifact,
  cleanupPrivateTmuxSockets,
  isForbiddenDirectReviewToolCall,
} from "../runtime.ts";

const here = path.dirname(fileURLToPath(import.meta.url));
const fakeLauncher = path.join(here, "fixtures", "fake_launcher.py");

async function fixture(t) {
  const root = await mkdtemp(path.join(os.tmpdir(), "claude-review-ext-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  const cwd = path.join(root, "repo");
  const promptFile = path.join(root, "prompt.md");
  const output = path.join(root, "review.md");
  await import("node:fs/promises").then(({ mkdir }) => mkdir(cwd));
  await writeFile(promptFile, "MODE=success\nRead-only review.\n");
  return { root, cwd, promptFile, output };
}

function managerFor(root, notifications, overrides = {}) {
  return new ClaudeReviewJobManager({
    launcherPath: fakeLauncher,
    cacheDir: path.join(root, "cache"),
    onComplete: (event) => notifications.push(event),
    reviewWatchdogMs: 5_000,
    smokeWatchdogMs: 5_000,
    ...overrides,
  });
}

async function waitForTerminal(manager, jobId, timeoutMs = 5_000) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const job = manager.status(jobId);
    if (job && job.status !== "running") return job;
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
  throw new Error(`timed out waiting for ${jobId}`);
}

test("outer watchdogs cover the launcher's full valid lifecycle", () => {
  assert.equal(REVIEW_WATCHDOG_MS, 4_200_000);
  assert.equal(SMOKE_WATCHDOG_MS, 300_000);
});

test("buildLauncherArgs fixes launcher policy and uses argument arrays", () => {
  const args = buildLauncherArgs({
    action: "start",
    cwd: "/repo with spaces",
    promptFile: "/tmp/review prompt.md",
    output: "/tmp/review output.md",
    reviewName: "claude-review-fixed",
  });
  assert.deepEqual(args, [
    "--cwd", "/repo with spaces",
    "--prompt-file", "/tmp/review prompt.md",
    "--output", "/tmp/review output.md",
    "--review-name", "claude-review-fixed",
    "--timeout-seconds", "3600",
  ]);
  assert.deepEqual(buildLauncherArgs({
    action: "smoke",
    cwd: "/repo",
    output: "/tmp/smoke.txt",
    reviewName: "claude-review-smoke",
  }), [
    "--smoke",
    "--cwd", "/repo",
    "--output", "/tmp/smoke.txt",
    "--review-name", "claude-review-smoke",
    "--timeout-seconds", "120",
  ]);
});

test("argument-array launch preserves paths with spaces", async (t) => {
  const f = await fixture(t);
  const spacedCwd = path.join(f.root, "repo with spaces");
  const spacedPrompt = path.join(f.root, "prompt with spaces.md");
  const spacedOutput = path.join(f.root, "output with spaces.md");
  await import("node:fs/promises").then(({ mkdir }) => mkdir(spacedCwd));
  await writeFile(spacedPrompt, "MODE=success\n");
  const manager = managerFor(f.root, []);
  t.after(() => manager.shutdown());
  const started = await manager.start({ action: "start", cwd: spacedCwd, promptFile: spacedPrompt, output: spacedOutput });
  const completed = await waitForTerminal(manager, started.jobId);
  assert.equal(completed.status, "succeeded");
  assert.match(await readFile(spacedOutput, "utf8"), /CLAUDE_REVIEW_LAUNCHER_METADATA/);
});

test("start returns immediately, survives silence beyond the old 8s overlay threshold, and notifies exactly once", async (t) => {
  const f = await fixture(t);
  await writeFile(f.promptFile, "MODE=success\nDELAY=8.5\n");
  const notifications = [];
  const manager = managerFor(f.root, notifications, { reviewWatchdogMs: 15_000 });
  t.after(() => manager.shutdown());

  const startedAt = Date.now();
  const started = await manager.start({ action: "start", cwd: f.cwd, promptFile: f.promptFile, output: f.output });
  assert.equal(started.status, "running");
  assert.ok(Date.now() - startedAt < 200, "start should return before the silent child completes");
  await new Promise((resolve) => setTimeout(resolve, 8_200));
  assert.equal(manager.status(started.jobId)?.status, "running", "silence beyond the former 8s threshold must not kill a review");

  const completed = await waitForTerminal(manager, started.jobId, 5_000);
  assert.equal(completed.status, "succeeded");
  assert.equal(notifications.length, 1);
  assert.equal(notifications[0].jobId, started.jobId);
  assert.match(await readFile(f.output, "utf8"), /CLAUDE_REVIEW_LAUNCHER_METADATA/);
  await new Promise((resolve) => setTimeout(resolve, 50));
  assert.equal(notifications.length, 1, "completion must be emitted exactly once");
});

test("stale prior output cannot turn a zero-exit no-op into false success", async (t) => {
  const f = await fixture(t);
  await writeFile(f.output, "VERDICT: CLEAN_FOR_PR\n---\nCLAUDE_REVIEW_LAUNCHER_METADATA\nsocket=stale\n");
  await writeFile(f.promptFile, "MODE=no-artifact\n");
  const manager = managerFor(f.root, []);
  t.after(() => manager.shutdown());
  const started = await manager.start({ action: "start", cwd: f.cwd, promptFile: f.promptFile, output: f.output });
  const completed = await waitForTerminal(manager, started.jobId);
  assert.equal(completed.status, "failed");
  assert.equal(completed.classification, "CLAUDE_REVIEW_ARTIFACT_MISSING");
});

test("zero exit without valid artifact is infrastructure failure", async (t) => {
  const f = await fixture(t);
  await writeFile(f.promptFile, "MODE=no-artifact\n");
  const notifications = [];
  const manager = managerFor(f.root, notifications);
  t.after(() => manager.shutdown());
  const started = await manager.start({ action: "start", cwd: f.cwd, promptFile: f.promptFile, output: f.output });
  const completed = await waitForTerminal(manager, started.jobId);
  assert.equal(completed.status, "failed");
  assert.equal(completed.classification, "CLAUDE_REVIEW_ARTIFACT_MISSING");
  assert.equal(notifications.length, 1);
});

test("zero exit with malformed artifact is infrastructure failure", async (t) => {
  const f = await fixture(t);
  await writeFile(f.promptFile, "MODE=malformed-success\n");
  const manager = managerFor(f.root, []);
  t.after(() => manager.shutdown());
  const started = await manager.start({ action: "start", cwd: f.cwd, promptFile: f.promptFile, output: f.output });
  const completed = await waitForTerminal(manager, started.jobId);
  assert.equal(completed.status, "failed");
  assert.equal(completed.classification, "CLAUDE_REVIEW_ARTIFACT_INVALID");
});

test("classified launcher failures preserve classification and evidence", async (t) => {
  const f = await fixture(t);
  await writeFile(f.promptFile, "MODE=classified-failure\n");
  const manager = managerFor(f.root, []);
  t.after(() => manager.shutdown());
  const started = await manager.start({ action: "start", cwd: f.cwd, promptFile: f.promptFile, output: f.output });
  const completed = await waitForTerminal(manager, started.jobId);
  assert.equal(completed.status, "failed");
  assert.equal(completed.classification, "CLAUDE_AUTH_UNAVAILABLE_IN_TUI");
  assert.match(completed.summary, /inspect=tmux/);
});

test("simultaneous starts reserve the same output atomically", async (t) => {
  const f = await fixture(t);
  await writeFile(f.promptFile, "MODE=success\nDELAY=0.2\n");
  const manager = managerFor(f.root, []);
  t.after(() => manager.shutdown());
  const results = await Promise.allSettled([
    manager.start({ action: "start", cwd: f.cwd, promptFile: f.promptFile, output: f.output }),
    manager.start({ action: "start", cwd: f.cwd, promptFile: f.promptFile, output: f.output }),
  ]);
  assert.equal(results.filter((result) => result.status === "fulfilled").length, 1);
  assert.equal(results.filter((result) => result.status === "rejected").length, 1);
  const started = results.find((result) => result.status === "fulfilled").value;
  await waitForTerminal(manager, started.jobId);
});

test("symlinked parent aliases share one atomic output reservation", async (t) => {
  const f = await fixture(t);
  const actualDir = path.join(f.root, "actual-output");
  const aliasDir = path.join(f.root, "alias-output");
  await import("node:fs/promises").then(async ({ mkdir, symlink }) => {
    await mkdir(actualDir);
    await symlink(actualDir, aliasDir, "dir");
  });
  await writeFile(f.promptFile, "MODE=success\nDELAY=0.2\n");
  const manager = managerFor(f.root, []);
  t.after(() => manager.shutdown());
  const results = await Promise.allSettled([
    manager.start({ action: "start", cwd: f.cwd, promptFile: f.promptFile, output: path.join(actualDir, "review.md") }),
    manager.start({ action: "start", cwd: f.cwd, promptFile: f.promptFile, output: path.join(aliasDir, "review.md") }),
  ]);
  assert.equal(results.filter((result) => result.status === "fulfilled").length, 1);
  assert.equal(results.filter((result) => result.status === "rejected").length, 1);
  const started = results.find((result) => result.status === "fulfilled").value;
  await waitForTerminal(manager, started.jobId);
});

test("duplicate active output paths are rejected while distinct jobs run concurrently", async (t) => {
  const f = await fixture(t);
  await writeFile(f.promptFile, "MODE=success\nDELAY=0.25\n");
  const secondPrompt = path.join(f.root, "second.md");
  const secondOutput = path.join(f.root, "second-output.md");
  await writeFile(secondPrompt, "MODE=success\nDELAY=0.1\n");
  const notifications = [];
  const manager = managerFor(f.root, notifications);
  t.after(() => manager.shutdown());

  const first = await manager.start({ action: "start", cwd: f.cwd, promptFile: f.promptFile, output: f.output });
  await assert.rejects(
    manager.start({ action: "start", cwd: f.cwd, promptFile: f.promptFile, output: f.output }),
    /already has an active Claude review job/,
  );
  const second = await manager.start({ action: "start", cwd: f.cwd, promptFile: secondPrompt, output: secondOutput });
  await Promise.all([waitForTerminal(manager, first.jobId), waitForTerminal(manager, second.jobId)]);
  assert.equal(notifications.length, 2);
  assert.equal(new Set(notifications.map((event) => event.jobId)).size, 2);
  assert.equal(manager.list().filter((job) => job.status === "running").length, 0);
});

test("watchdog timeout and explicit cancellation reap children and private tmux", async (t) => {
  const f = await fixture(t);
  await writeFile(f.promptFile, "MODE=hang\n");
  const cleanupCalls = [];
  const manager = managerFor(f.root, [], {
    reviewWatchdogMs: 120,
    killGraceMs: 40,
    cleanupTmuxImpl: (reviewName, pid) => cleanupCalls.push({ reviewName, pid }),
  });
  t.after(() => manager.shutdown());
  const timed = await manager.start({ action: "start", cwd: f.cwd, promptFile: f.promptFile, output: f.output });
  const timedResult = await waitForTerminal(manager, timed.jobId);
  assert.equal(timedResult.status, "timed_out");

  const cancelOutput = path.join(f.root, "cancel.md");
  const cancelled = await manager.start({ action: "start", cwd: f.cwd, promptFile: f.promptFile, output: cancelOutput });
  assert.equal(await manager.cancel(cancelled.jobId), true);
  const cancelledResult = await waitForTerminal(manager, cancelled.jobId);
  assert.equal(cancelledResult.status, "cancelled");
  assert.equal(cleanupCalls.length, 2);
  assert.deepEqual(cleanupCalls.map((call) => call.reviewName), [timed.jobId, cancelled.jobId]);
  assert.ok(cleanupCalls.every((call) => Number.isInteger(call.pid)));
});

test("force kill reaps a child that ignores SIGTERM", async (t) => {
  const f = await fixture(t);
  await writeFile(f.promptFile, "MODE=ignore-term\n");
  const manager = managerFor(f.root, [], { reviewWatchdogMs: 100, killGraceMs: 50 });
  t.after(() => manager.shutdown());
  const started = await manager.start({ action: "start", cwd: f.cwd, promptFile: f.promptFile, output: f.output });
  const completed = await waitForTerminal(manager, started.jobId, 2_000);
  assert.equal(completed.status, "timed_out");
  await new Promise((resolve) => setTimeout(resolve, 30));
  assert.throws(() => process.kill(started.pid, 0));
});

test("cancellation cleanup targets only the job's private tmux sockets", async (t) => {
  const f = await fixture(t);
  const socketDir = path.join(f.root, "tmux-1000");
  await import("node:fs/promises").then(({ mkdir }) => mkdir(socketDir));
  const matching = "claude-review-claude-review-abc123-4242-nonce";
  const otherJob = "claude-review-claude-review-other-4242-nonce";
  const otherPid = "claude-review-claude-review-abc123-9999-nonce";
  await Promise.all([matching, otherJob, otherPid].map((name) => writeFile(path.join(socketDir, name), "")));
  const calls = [];
  cleanupPrivateTmuxSockets("claude-review-abc123", 4242, {
    socketDir,
    tmuxExecutable: "/fake/tmux",
    spawnSyncImpl: (command, args, options) => {
      calls.push({ command, args, options });
      return {};
    },
  });
  assert.equal(calls.length, 1);
  assert.equal(calls[0].command, "/fake/tmux");
  assert.deepEqual(calls[0].args, ["-L", matching, "kill-server"]);
  assert.equal(calls[0].options.shell, false);
});

test("shutdown cancels jobs without triggering a new completion turn and persists state", async (t) => {
  const f = await fixture(t);
  await writeFile(f.promptFile, "MODE=hang\n");
  const notifications = [];
  const manager = managerFor(f.root, notifications, { killGraceMs: 40 });
  const started = await manager.start({ action: "start", cwd: f.cwd, promptFile: f.promptFile, output: f.output });
  await manager.shutdown();
  const completed = manager.status(started.jobId);
  assert.equal(completed?.status, "cancelled");
  assert.equal(notifications.length, 0, "session shutdown must not trigger a fresh LLM turn");
  assert.deepEqual(JSON.parse(await readFile(completed.stateFile, "utf8")), completed);
});

test("artifact classifier distinguishes review, smoke, and launcher failures", () => {
  assert.deepEqual(classifyArtifact("start", "VERDICT: CLEAN_FOR_PR\n---\nCLAUDE_REVIEW_LAUNCHER_METADATA\n"), { ok: true, classification: "CLAUDE_REVIEW_SUCCEEDED" });
  assert.deepEqual(classifyArtifact("start", "Provider error: no final review was produced.\n---\nCLAUDE_REVIEW_LAUNCHER_METADATA\n"), { ok: false, classification: "CLAUDE_REVIEW_ARTIFACT_INVALID" });
  assert.deepEqual(classifyArtifact("smoke", "CLAUDE_REVIEW_SMOKE_READY\nsocket=x\nsession=y\n"), { ok: true, classification: "CLAUDE_REVIEW_SMOKE_READY" });
  assert.deepEqual(classifyArtifact("start", "CLAUDE_SESSION_LIMIT_IN_TUI\nwait for reset\n"), { ok: false, classification: "CLAUDE_SESSION_LIMIT_IN_TUI" });
});

test("runtime policy blocks known direct review routes without blocking unrelated Claude delegation", () => {
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "python3 ~/.agents/skills/claude-code-review/scripts/claude_interactive_review.py --smoke" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("process", { action: "start", command: "python3 /tmp/claude_interactive_review.py" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "bash -lc 'python3 /tmp/claude_interactive_review.py --smoke'" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "bash -lc '/tmp/claude_interactive_review.py --smoke'" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("process", { action: "start", command: "/tmp/claude_interactive_review.py --smoke" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "bash -lc 'exec /tmp/claude_interactive_review.py --smoke'" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "command /tmp/claude_interactive_review.py --smoke" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "env FOO=bar /tmp/claude_interactive_review.py --smoke" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "timeout 200 /tmp/claude_interactive_review.py --smoke" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("process", { action: "start", command: "nohup /tmp/claude_interactive_review.py --smoke" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "zsh -ilc 'claude audit the current diff'" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("process", { action: "start", command: "claude 'Find bugs in this change'" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("interactive_shell", { command: "claude 'Review this diff and return CLEAN_FOR_PR'" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("interactive_shell", { spawn: { agent: "claude", prompt: "Read-only implementation review of the current diff" } }), true);
  assert.equal(isForbiddenDirectReviewToolCall("interactive_shell", { spawn: { agent: "claude", prompt: "Explain how this module works" } }), false);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "rg claude_interactive_review.py skills" }), false);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "cat skills/claude-code-review/scripts/claude_interactive_review.py" }), false);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "git diff -- skills/claude-code-review/scripts/claude_interactive_review.py" }), false);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "cmp skills/claude-code-review/scripts/claude_interactive_review.py ~/.agents/skills/claude-code-review/scripts/claude_interactive_review.py" }), false);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "sed -n '1,100p' skills/claude-code-review/scripts/claude_interactive_review.py" }), false);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "cat /tmp/claude_interactive_review.py >/dev/null; /tmp/claude_interactive_review.py --smoke" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "rg claude_interactive_review.py /tmp && python3 /tmp/claude_interactive_review.py --smoke" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "git diff -- /tmp/claude_interactive_review.py; bash -lc '/tmp/claude_interactive_review.py --smoke'" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "sed -n '1p' /tmp/claude_interactive_review.py | /tmp/claude_interactive_review.py --smoke" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "cat /tmp/claude_interactive_review.py >/dev/null & /tmp/claude_interactive_review.py --smoke" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "cat /tmp/claude_interactive_review.py > >(/tmp/claude_interactive_review.py --smoke)" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "cat /tmp/claude_interactive_review.py < <(/tmp/claude_interactive_review.py --smoke)" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "find /tmp -name claude_interactive_review.py -exec {} --smoke \\;" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "rg --pre cat claude_interactive_review.py /tmp" }), true);
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "claude --version" }), false);
  assert.equal(isForbiddenDirectReviewToolCall("process", { action: "start", command: "claude 'Explain this module'" }), false);
});
