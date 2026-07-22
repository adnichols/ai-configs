import assert from "node:assert/strict";
import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

import { ClaudeReviewJobManager } from "../runtime.ts";

const here = path.dirname(fileURLToPath(import.meta.url));
const fakeLauncher = path.join(here, "fixtures", "fake_launcher.py");

async function waitForAll(manager, ids, timeoutMs = 15_000) {
  const pending = new Set(ids);
  const deadline = Date.now() + timeoutMs;
  while (pending.size && Date.now() < deadline) {
    for (const id of pending) {
      if (manager.status(id)?.status !== "running") pending.delete(id);
    }
    if (pending.size) await new Promise((resolve) => setTimeout(resolve, 10));
  }
  assert.equal(pending.size, 0, `jobs did not finish: ${[...pending].join(", ")}`);
}

function processExists(pid) {
  try { process.kill(pid, 0); return true; } catch { return false; }
}

test("75 mixed concurrent jobs complete once without registry leaks", async (t) => {
  const root = await mkdtemp(path.join(os.tmpdir(), "claude-review-stress-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  const cwd = path.join(root, "repo");
  await mkdir(cwd);
  const notifications = [];
  const manager = new ClaudeReviewJobManager({
    launcherPath: fakeLauncher,
    cacheDir: path.join(root, "cache"),
    onComplete: (event) => notifications.push(event),
    reviewWatchdogMs: 10_000,
    maxCompletedJobs: 25,
  });
  t.after(() => manager.shutdown());

  const modes = ["success", "no-verdict", "alternate-verdict", "malformed-success", "provider-error", "tool-only", "classified-failure", "no-artifact", "nonzero-no-artifact"];
  const starts = [];
  for (let i = 0; i < 75; i += 1) {
    const promptFile = path.join(root, `prompt-${i}.md`);
    const output = path.join(root, `output-${i}.md`);
    const mode = modes[i % modes.length];
    const delay = ((i * 37) % 90) / 1000;
    await writeFile(promptFile, `MODE=${mode}\nDELAY=${delay}\n`);
    starts.push(manager.start({ action: "start", cwd, promptFile, output }));
  }
  const jobs = await Promise.all(starts);
  await waitForAll(manager, jobs.map((job) => job.jobId));

  assert.equal(notifications.length, 75);
  assert.equal(new Set(notifications.map((event) => event.jobId)).size, 75, "every job must notify exactly once");
  assert.equal(manager.list().length, 25, "terminal history must remain bounded");
  assert.equal(manager.list().filter((job) => job.status === "running").length, 0);
  const expectedSuccesses = Array.from({ length: 75 }, (_, i) => modes[i % modes.length]).filter((mode) => ["success", "no-verdict", "alternate-verdict"].includes(mode)).length;
  assert.equal(notifications.filter((job) => job.status === "succeeded").length, expectedSuccesses);
  assert.equal(notifications.filter((job) => job.status === "failed").length, 75 - expectedSuccesses);
  assert.equal(manager.status(jobs[0].jobId), undefined, "old terminal jobs should be evicted from memory");
});

test("concurrent explicit cancellation leaves no live supervisor pids", async (t) => {
  const root = await mkdtemp(path.join(os.tmpdir(), "claude-review-reap-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  const cwd = path.join(root, "repo");
  await mkdir(cwd);
  const manager = new ClaudeReviewJobManager({
    launcherPath: fakeLauncher,
    cacheDir: path.join(root, "cache"),
    reviewWatchdogMs: 10_000,
    killGraceMs: 50,
  });

  const starts = [];
  for (let i = 0; i < 12; i += 1) {
    const promptFile = path.join(root, `hang-${i}.md`);
    await writeFile(promptFile, "MODE=hang\n");
    starts.push(manager.start({ action: "start", cwd, promptFile, output: path.join(root, `hang-${i}.out`) }));
  }
  const jobs = await Promise.all(starts);
  await Promise.all(jobs.map((job) => manager.cancel(job.jobId)));
  await waitForAll(manager, jobs.map((job) => job.jobId));
  await manager.shutdown();
  assert.equal(manager.list().filter((job) => job.status !== "cancelled").length, 0);
  await new Promise((resolve) => setTimeout(resolve, 50));
  for (const job of jobs) {
    assert.equal(processExists(job.pid), false, `child pid ${job.pid} survived cancellation/shutdown`);
  }
});
