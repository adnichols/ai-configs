import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { chmod, copyFile, mkdir, mkdtemp, readFile, realpath, rm, writeFile } from "node:fs/promises";
import { realpathSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../..");
const extensionPath = path.join(repo, "_pi/extensions/claude-review/index.ts");
const fakeLauncher = path.join(repo, "_pi/extensions/claude-review/tests/fixtures/fake_launcher.py");

async function loadSdk() {
  const piBin = realpathSync(execFileSync("which", ["pi"], { encoding: "utf8" }).trim());
  const packageRoot = path.resolve(path.dirname(piBin), "..");
  return import(pathToFileURL(path.join(packageRoot, "dist", "index.js")));
}

async function waitForStatus(tool, jobId, cwd) {
  const deadline = Date.now() + 5_000;
  while (Date.now() < deadline) {
    const result = await tool.execute("status-call", { action: "status", jobId }, new AbortController().signal, () => {}, { cwd });
    if (result.details.job.status !== "running") return result.details.job;
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
  throw new Error(`timed out waiting for ${jobId}`);
}

test("real Pi ResourceLoader registers and runs claude_review without an LLM", async (t) => {
  const home = await mkdtemp(path.join(os.tmpdir(), "pi-claude-review-sdk-"));
  t.after(() => rm(home, { recursive: true, force: true }));
  const installedLauncher = path.join(home, ".agents/skills/claude-code-review/scripts/claude_interactive_review.py");
  await mkdir(path.dirname(installedLauncher), { recursive: true });
  await copyFile(fakeLauncher, installedLauncher);
  await chmod(installedLauncher, 0o755);

  const originalHome = process.env.HOME;
  process.env.HOME = home;
  t.after(() => {
    if (originalHome === undefined) delete process.env.HOME;
    else process.env.HOME = originalHome;
  });

  const sdk = await loadSdk();
  const loader = new sdk.DefaultResourceLoader({
    cwd: repo,
    agentDir: path.join(home, ".pi/agent"),
    additionalExtensionPaths: [extensionPath],
    settingsManager: sdk.SettingsManager.inMemory({}),
  });
  await loader.reload();
  const loaded = loader.getExtensions();
  assert.deepEqual(loaded.errors, []);
  const resolvedExtensionPath = await realpath(extensionPath);
  const extension = loaded.extensions.find((item) => item.resolvedPath === resolvedExtensionPath);
  assert.ok(extension, "extension should load through the real Pi ResourceLoader");
  const registeredTool = extension.tools.get("claude_review");
  assert.ok(registeredTool, "claude_review should be registered");
  const tool = registeredTool.definition;
  const toolCallGuard = extension.handlers.get("tool_call")?.[0];
  assert.ok(toolCallGuard, "direct-review tool-call guard should be registered");
  assert.deepEqual(
    await toolCallGuard({ toolName: "process", input: { action: "start", command: "python3 /tmp/claude_interactive_review.py" } }),
    {
      block: true,
      reason: "Direct Claude review launch is disabled. Use the claude_review tool so the review always runs through the deterministic background controller.",
    },
  );
  assert.equal(
    await toolCallGuard({ toolName: "interactive_shell", input: { spawn: { agent: "claude", prompt: "Explain this module" } } }),
    undefined,
  );

  const output = path.join(home, "smoke.txt");
  const startedAt = Date.now();
  const result = await tool.execute(
    "start-call",
    { action: "smoke", cwd: repo, output },
    new AbortController().signal,
    () => {},
    { cwd: repo },
  );
  assert.ok(Date.now() - startedAt < 200, "real tool execute should return immediately");
  assert.equal(result.details.job.status, "running");
  const completed = await waitForStatus(tool, result.details.job.jobId, repo);
  assert.equal(completed.status, "succeeded");
  assert.match(await readFile(output, "utf8"), /CLAUDE_REVIEW_SMOKE_READY/);
  assert.match(result.content[0].text, /dispatched invisibly in the background/);

  const hangPrompt = path.join(home, "hang-prompt.md");
  await writeFile(hangPrompt, "MODE=hang\n");
  const hanging = await tool.execute(
    "hang-call",
    { action: "start", cwd: repo, promptFile: hangPrompt, output: path.join(home, "hang-output.md") },
    new AbortController().signal,
    () => {},
    { cwd: repo },
  );
  const childPid = hanging.details.job.pid;
  assert.ok(childPid && process.kill(childPid, 0) === true);
  const shutdownHandler = extension.handlers.get("session_shutdown")?.[0];
  assert.ok(shutdownHandler, "session shutdown cleanup should be registered");
  await shutdownHandler();
  const afterShutdown = await tool.execute(
    "shutdown-status",
    { action: "status", jobId: hanging.details.job.jobId },
    new AbortController().signal,
    () => {},
    { cwd: repo },
  );
  assert.equal(afterShutdown.details.job.status, "cancelled");
  assert.throws(() => process.kill(childPid, 0));
});
