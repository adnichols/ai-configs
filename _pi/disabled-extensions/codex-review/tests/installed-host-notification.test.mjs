import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { realpathSync } from "node:fs";
import { chmod, copyFile, mkdir, mkdtemp, readFile, rm, symlink, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { pathToFileURL } from "node:url";

async function loadSdk() {
  const bin = realpathSync(execFileSync("which", ["pi"], { encoding: "utf8" }).trim());
  return import(pathToFileURL(path.join(path.resolve(path.dirname(bin), ".."), "dist", "index.js")));
}

async function waitForTerminal(tool, id, cwd, ctx) {
  let result;
  for (let attempt = 0; attempt < 1_500; attempt += 1) {
    result = await tool.execute("status", { action: "status", jobId: id }, new AbortController().signal, () => {}, ctx ?? { cwd });
    if (!["starting", "running"].includes(result.details.job.status)) return result.details.job;
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
  const job = result?.details?.job;
  const state = job?.stateFile ? await readFile(job.stateFile, "utf8").catch(() => "<unreadable>") : "<missing>";
  const stderr = job?.stderrLog ? await readFile(job.stderrLog, "utf8").catch(() => "<unreadable>") : "<missing>";
  throw new Error(`timed out waiting for installed Codex job\nstate=${state}\nstderr=${stderr}`);
}

test("installed same-process host keeps reviews visible, follows up only after detachment, and suppresses shutdown cancellation", async (t) => {
  const installedHome = process.env.PI_REVIEW_STACK_TEST_HOME;
  const temporaryHome = !installedHome;
  const home = await mkdtemp(path.join(os.tmpdir(), "codex-installed-host-"));
  let agentDir = path.join(home, ".pi/agent");
  t.after(() => rm(home, { recursive: true, force: true }));
  if (temporaryHome) {
    const source = path.resolve("_pi/extensions/codex-review");
    await mkdir(path.join(home, ".pi/agent/extensions"), { recursive: true });
    await import("node:fs/promises").then(({ cp }) => cp(source, path.join(home, ".pi/agent/extensions/codex-review"), { recursive: true }));
    const launcher = path.join(home, ".agents/skills/codex-review-partner/scripts/run-review.sh");
    await mkdir(path.dirname(launcher), { recursive: true });
    await copyFile(path.join(source, "tests/fixtures/fake_launcher.py"), launcher);
    await copyFile(path.resolve("skills/codex-review-partner/scripts/process_identity.py"), path.join(path.dirname(launcher), "process_identity.py"));
    await chmod(launcher, 0o755);
  } else {
    agentDir = path.join(installedHome, ".pi/agent");
    const skills = path.join(home, ".agents/skills");
    await mkdir(skills, { recursive: true });
    await symlink(path.join(installedHome, ".agents/skills/codex-review-partner"), path.join(skills, "codex-review-partner"), "dir");
  }
  const oldHome = process.env.HOME;
  process.env.HOME = home;
  t.after(() => { if (oldHome === undefined) delete process.env.HOME; else process.env.HOME = oldHome; });

  const sdk = await loadSdk();
  const cwd = process.cwd();
  const loader = new sdk.DefaultResourceLoader({ cwd, agentDir, settingsManager: sdk.SettingsManager.inMemory({}) });
  await loader.reload();
  const { session } = await sdk.createAgentSession({ cwd, agentDir, resourceLoader: loader, sessionManager: sdk.SessionManager.inMemory(cwd), noTools: "all" });
  const tool = session.extensionRunner.getToolDefinition("codex_review");
  const ctx = session.extensionRunner.createContext();
  assert.ok(tool);

  const testDir = await mkdtemp(path.join(home, ".pi/codex-review-host-test-"));
  t.after(() => rm(testDir, { recursive: true, force: true }));
  const prompt = path.join(testDir, "prompt.md");
  const output = path.join(testDir, "review.md");
  await writeFile(prompt, "MODE=success\nDELAY=0.3\n");
  const updates = [];
  let settled = false;
  const execution = tool.execute("start", { action: "start", reviewType: "implementation-review", verdictProfile: "generic-implementation", cwd, promptFile: prompt, output }, new AbortController().signal, (update) => updates.push(update), ctx).finally(() => { settled = true; });
  await new Promise((resolve) => setTimeout(resolve, 80));
  assert.equal(settled, false);
  assert.ok(updates.length > 0);
  assert.equal(updates[0].details.job.status, "running");
  assert.equal(updates[0].details.job.originSessionId, session.sessionId);
  const completed = await execution;
  assert.equal(completed.details.job.status, "succeeded");
  assert.equal(completed.details.job.deliveryState, "delivering");
  await session.extensionRunner.emit({ type: "message_start", message: { role: "toolResult", toolName: "codex_review", details: completed.details } });
  const delivered = await tool.execute("status", { action: "status", jobId: completed.details.job.jobId }, new AbortController().signal, () => {}, ctx);
  assert.equal(delivered.details.job.deliveryState, "delivered");
  assert.match(await readFile(output, "utf8"), /VERDICT:/);
  await new Promise((resolve) => setTimeout(resolve, 100));
  const completions = () => session.agent.state.messages.filter((message) => message.role === "custom" && message.customType === "codex-review-completion");
  assert.equal(completions().length, 0, "attached visible completion must return through the tool, not queue a duplicate turn");

  const detachedPrompt = path.join(testDir, "detached.md");
  await writeFile(detachedPrompt, "MODE=success\nDELAY=0.3\n");
  const detachedController = new AbortController();
  const detachedUpdates = [];
  const detachedExecution = tool.execute("detached", { action: "start", reviewType: "implementation-review", verdictProfile: "generic-implementation", cwd, promptFile: detachedPrompt, output: path.join(testDir, "detached-output.md") }, detachedController.signal, (update) => detachedUpdates.push(update), ctx);
  while (detachedUpdates.length === 0) await new Promise((resolve) => setTimeout(resolve, 10));
  detachedController.abort();
  await assert.rejects(detachedExecution, /continues under the managed controller/);
  for (let attempt = 0; attempt < 100 && completions().length === 0; attempt += 1) await new Promise((resolve) => setTimeout(resolve, 20));
  assert.equal(completions().length, 1);
  assert.match(String(completions()[0].content), /Read and triage/);

  const delayedPrompt = path.join(testDir, "delayed.md");
  await writeFile(delayedPrompt, "MODE=success\nDELAY=5\n");
  const delayedController = new AbortController();
  const delayedUpdates = [];
  const delayedExecution = tool.execute("delayed", { action: "start", reviewType: "implementation-review", verdictProfile: "generic-implementation", cwd, promptFile: delayedPrompt, output: path.join(testDir, "delayed-output.md") }, delayedController.signal, (update) => delayedUpdates.push(update), ctx);
  while (delayedUpdates.length === 0) await new Promise((resolve) => setTimeout(resolve, 10));
  delayedController.abort();
  await assert.rejects(delayedExecution, /continues under the managed controller/);
  await session.extensionRunner.emit({ type: "session_shutdown", reason: "quit" });
  session.dispose();
  await new Promise((resolve) => setTimeout(resolve, 100));
  assert.equal(completions().length, 1);
});
