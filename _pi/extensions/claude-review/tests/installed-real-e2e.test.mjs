import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { mkdtemp, readFile, realpath, rm, writeFile } from "node:fs/promises";
import { realpathSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { pathToFileURL } from "node:url";

async function loadSdk() {
  const piBin = realpathSync(execFileSync("which", ["pi"], { encoding: "utf8" }).trim());
  const packageRoot = path.resolve(path.dirname(piBin), "..");
  return import(pathToFileURL(path.join(packageRoot, "dist", "index.js")));
}

async function loadInstalledTool() {
  const sdk = await loadSdk();
  const extensionPath = path.join(os.homedir(), ".pi/agent/extensions/claude-review/index.ts");
  const loader = new sdk.DefaultResourceLoader({
    cwd: process.cwd(),
    agentDir: path.join(os.homedir(), ".pi/agent"),
    additionalExtensionPaths: [extensionPath],
    settingsManager: sdk.SettingsManager.inMemory({}),
  });
  await loader.reload();
  const loaded = loader.getExtensions();
  assert.deepEqual(loaded.errors, []);
  const resolved = await realpath(extensionPath);
  const extension = loaded.extensions.find((item) => item.resolvedPath === resolved);
  assert.ok(extension, "installed extension should load");
  const tool = extension.tools.get("claude_review")?.definition;
  assert.ok(tool, "installed claude_review tool should register");
  return tool;
}

async function waitForStatus(tool, jobId, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  while (Date.now() < deadline) {
    const result = await tool.execute("status", { action: "status", jobId }, new AbortController().signal, () => {}, { cwd: process.cwd() });
    if (result.details.job.status !== "running") return result.details.job;
    await new Promise((resolve) => setTimeout(resolve, 500));
  }
  throw new Error(`timed out waiting for installed job ${jobId}`);
}

function assertPrivateTmuxGone(artifact) {
  const socket = artifact.match(/^socket=(.+)$/m)?.[1];
  if (!socket) return;
  const probe = spawnSync("tmux", ["-L", socket, "list-sessions"], { encoding: "utf8", timeout: 5_000 });
  assert.notEqual(probe.status, 0, `private tmux socket still has sessions: ${socket}`);
}

test("installed claude_review performs real smoke and tiny review", { timeout: 900_000 }, async (t) => {
  if (process.env.RUN_REAL_CLAUDE_TOOL_E2E !== "1") {
    t.skip("RUN_REAL_CLAUDE_TOOL_E2E not set");
    return;
  }
  const root = await mkdtemp(path.join(os.tmpdir(), "installed-claude-review-e2e-"));
  t.after(() => rm(root, { recursive: true, force: true }));
  const tool = await loadInstalledTool();

  const smokeOutput = path.join(root, "smoke.txt");
  const smokeUpdates = [];
  const smoke = await tool.execute("smoke", { action: "smoke", cwd: process.cwd(), output: smokeOutput }, new AbortController().signal, (update) => smokeUpdates.push(update), { cwd: process.cwd() });
  assert.ok(smokeUpdates.length > 0, "installed smoke must expose its running subprocess state");
  const smokeJob = smoke.details.job;
  if (smokeJob.status !== "succeeded") {
    const evidence = await readFile(smokeOutput, "utf8").catch(() => smokeJob.summary);
    if (/CLAUDE_(?:SESSION_LIMIT_IN_TUI|AUTH_UNAVAILABLE_IN_(?:TUI|TMUX_PREFLIGHT)|REVIEW_MISSING_PREREQUISITE)/.test(evidence)) {
      t.skip(`real Claude prerequisite unavailable: ${smokeJob.classification}`);
      return;
    }
  }
  assert.equal(smokeJob.status, "succeeded", smokeJob.summary);
  const smokeArtifact = await readFile(smokeOutput, "utf8");
  assert.match(smokeArtifact, /CLAUDE_REVIEW_SMOKE_READY/);
  assertPrivateTmuxGone(smokeArtifact);

  const promptFile = path.join(root, "prompt.md");
  const reviewOutput = path.join(root, "review.md");
  await writeFile(promptFile, "Read-only smoke review. Do not edit files. Return exactly `VERDICT: PASS_SCOPED` followed by one short sentence.\n");
  const reviewUpdates = [];
  const review = await tool.execute("review", { action: "start", cwd: process.cwd(), promptFile, output: reviewOutput }, new AbortController().signal, (update) => reviewUpdates.push(update), { cwd: process.cwd() });
  assert.ok(reviewUpdates.length > 0, "installed review must expose its running subprocess state");
  const reviewJob = review.details.job;
  if (reviewJob.status !== "succeeded") {
    const evidence = await readFile(reviewOutput, "utf8").catch(() => reviewJob.summary);
    if (/CLAUDE_(?:SESSION_LIMIT_IN_TUI|AUTH_UNAVAILABLE_IN_(?:TUI|TMUX_PREFLIGHT)|REVIEW_MISSING_PREREQUISITE)/.test(evidence)) {
      t.skip(`real Claude prerequisite unavailable: ${reviewJob.classification}`);
      return;
    }
  }
  assert.equal(reviewJob.status, "succeeded", reviewJob.summary);
  const reviewArtifact = await readFile(reviewOutput, "utf8");
  assert.match(reviewArtifact, /VERDICT: PASS_SCOPED/);
  assert.match(reviewArtifact, /CLAUDE_REVIEW_LAUNCHER_METADATA/);
  assertPrivateTmuxGone(reviewArtifact);
});
