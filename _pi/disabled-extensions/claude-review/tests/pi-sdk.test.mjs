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
      reason: "Direct Claude review launch is disabled. Use the claude_review tool so the review always runs through the deterministic managed controller.",
    },
  );
  assert.equal(
    await toolCallGuard({ toolName: "interactive_shell", input: { spawn: { agent: "claude", prompt: "Explain this module" } } }),
    undefined,
  );

  const output = path.join(home, "visible-output.md");
  const visiblePrompt = path.join(home, "visible-prompt.md");
  await writeFile(visiblePrompt, "MODE=no-verdict\nDELAY=0.3\n");
  const updates = [];
  let settled = false;
  const execution = tool.execute(
    "start-call",
    { action: "start", cwd: repo, promptFile: visiblePrompt, output },
    new AbortController().signal,
    (update) => updates.push(update),
    { cwd: repo },
  ).finally(() => { settled = true; });
  await new Promise((resolve) => setTimeout(resolve, 80));
  assert.equal(settled, false, "visible review tool call must remain active while the subprocess runs");
  assert.ok(updates.length > 0, "visible review tool call must publish a running update");
  assert.equal(updates[0].details.phase, "running");
  assert.match(updates[0].content[0].text, /reviewer subprocess running/);
  const result = await execution;
  assert.equal(result.details.phase, "completed");
  assert.equal(result.details.job.status, "succeeded");
  const messageStartHandler = extension.handlers.get("message_start")?.[0];
  assert.ok(messageStartHandler, "terminal tool results should acknowledge durable completion delivery");
  await messageStartHandler({ message: { role: "toolResult", toolName: "claude_review", details: result.details } });
  assert.match(await readFile(output, "utf8"), /No blocking issues were found/);
  assert.match(result.content[0].text, /reviewer subprocess completed/);

  const lifecyclePrompt = path.join(home, "lifecycle-prompt.md");
  await writeFile(lifecyclePrompt, "MODE=no-verdict\nDELAY=0.5\n");
  const lifecycleUpdates = [];
  const lifecycleController = new AbortController();
  const lifecycleExecution = tool.execute(
    "lifecycle-call",
    { action: "start", cwd: repo, promptFile: lifecyclePrompt, output: path.join(home, "lifecycle-output.md") },
    lifecycleController.signal,
    (update) => lifecycleUpdates.push(update),
    { cwd: repo },
  );
  while (lifecycleUpdates.length === 0) await new Promise((resolve) => setTimeout(resolve, 10));
  const lifecycleJob = lifecycleUpdates[0].details.job;
  const supervisorPid = lifecycleJob.supervisorPid ?? lifecycleJob.pid;
  assert.ok(supervisorPid && process.kill(supervisorPid, 0) === true);
  lifecycleController.abort();
  await assert.rejects(lifecycleExecution, /continues under the detached supervisor/);
  const shutdownHandler = extension.handlers.get("session_shutdown")?.[0];
  assert.ok(shutdownHandler, "session shutdown cleanup should be registered");
  await shutdownHandler();
  assert.doesNotThrow(() => process.kill(supervisorPid, 0), "session shutdown must not cancel accepted work");

  const replacementLoader = new sdk.DefaultResourceLoader({
    cwd: repo,
    agentDir: path.join(home, ".pi/agent"),
    additionalExtensionPaths: [extensionPath],
    settingsManager: sdk.SettingsManager.inMemory({}),
  });
  await replacementLoader.reload();
  const replacementLoaded = replacementLoader.getExtensions();
  assert.deepEqual(replacementLoaded.errors, []);
  const replacementExtension = replacementLoaded.extensions.find((item) => item.resolvedPath === resolvedExtensionPath);
  const replacementTool = replacementExtension?.tools.get("claude_review")?.definition;
  assert.ok(replacementTool, "replacement extension should recover the review tool");
  const recovered = await waitForStatus(replacementTool, lifecycleJob.jobId, repo);
  assert.equal(recovered.status, "succeeded");
  assert.match(await readFile(recovered.output, "utf8"), /No blocking issues were found/);
  await replacementExtension.handlers.get("session_shutdown")?.[0]?.();
});
