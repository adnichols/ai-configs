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
  for (let attempt = 0; attempt < 600; attempt += 1) {
    const result = await tool.execute("status", { action: "status", jobId: id }, new AbortController().signal, () => {}, ctx ?? { cwd });
    if (!["starting", "running"].includes(result.details.job.status)) return result.details.job;
    await new Promise((resolve) => setTimeout(resolve, 20));
  }
  throw new Error("timed out waiting for installed Codex job");
}

test("installed same-process host queues one completion follow-up and none for shutdown cancellation", async (t) => {
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
  await writeFile(prompt, "MODE=success\n");
  const startTime = Date.now();
  const started = await tool.execute("start", { action: "start", reviewType: "implementation-review", verdictProfile: "generic-implementation", cwd, promptFile: prompt, output }, new AbortController().signal, () => {}, ctx);
  assert.equal(started.details.job.status, "running");
  assert.ok(Date.now() - startTime < 1_000);
  assert.equal((await waitForTerminal(tool, started.details.job.jobId, cwd, ctx)).status, "succeeded");
  assert.match(await readFile(output, "utf8"), /VERDICT:/);
  await new Promise((resolve) => setTimeout(resolve, 100));
  const completions = () => session.agent.state.messages.filter((message) => message.role === "custom" && message.customType === "codex-review-completion");
  assert.equal(completions().length, 1);
  assert.match(String(completions()[0].content), /Read and triage/);

  const delayedPrompt = path.join(testDir, "delayed.md");
  await writeFile(delayedPrompt, "MODE=success\nDELAY=5\n");
  await tool.execute("delayed", { action: "start", reviewType: "implementation-review", verdictProfile: "generic-implementation", cwd, promptFile: delayedPrompt, output: path.join(testDir, "delayed-output.md") }, new AbortController().signal, () => {}, ctx);
  await session.extensionRunner.emit({ type: "session_shutdown", reason: "quit" });
  session.dispose();
  await new Promise((resolve) => setTimeout(resolve, 100));
  assert.equal(completions().length, 1);
});
