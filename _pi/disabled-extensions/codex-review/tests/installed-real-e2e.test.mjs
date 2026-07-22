import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { realpathSync } from "node:fs";
import { mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { pathToFileURL } from "node:url";

async function loadSdk() {
  const bin = realpathSync(execFileSync("which", ["pi"], { encoding: "utf8" }).trim());
  return import(pathToFileURL(path.join(path.resolve(path.dirname(bin), ".."), "dist", "index.js")));
}

async function terminal(tool, id, ctx) {
  for (let attempt = 0; attempt < 2_100; attempt += 1) {
    const result = await tool.execute("status", { action: "status", jobId: id }, new AbortController().signal, () => {}, ctx);
    if (!["starting", "running"].includes(result.details.job.status)) return result.details.job;
    await new Promise((resolve) => setTimeout(resolve, 2_000));
  }
  throw new Error("real Codex job exceeded controller budget");
}

test("real installed Codex smoke and tiny review use the registered same-process host", { skip: process.env.RUN_REAL_CODEX_TOOL_E2E !== "1", timeout: 4_500_000 }, async (t) => {
  const home = os.homedir();
  const cwd = process.cwd();
  const temporary = await mkdtemp(path.join(os.tmpdir(), "codex-real-tool-"));
  t.after(() => rm(temporary, { recursive: true, force: true }));
  const sdk = await loadSdk();
  const loader = new sdk.DefaultResourceLoader({ cwd, agentDir: path.join(home, ".pi/agent"), settingsManager: sdk.SettingsManager.inMemory({}) });
  await loader.reload();
  const { session } = await sdk.createAgentSession({ cwd, agentDir: path.join(home, ".pi/agent"), resourceLoader: loader, sessionManager: sdk.SessionManager.create(cwd, path.join(home, ".pi/agent/sessions")), noTools: "all" });
  const tool = session.extensionRunner.getToolDefinition("codex_review");
  const ctx = session.extensionRunner.createContext();
  assert.ok(tool);
  const completions = () => session.agent.state.messages.filter((message) => message.role === "custom" && message.customType === "codex-review-completion");

  const smokeOutput = path.join(temporary, "smoke.txt");
  const startedAt = Date.now();
  const smoke = await tool.execute("smoke", { action: "smoke", cwd, output: smokeOutput }, new AbortController().signal, () => {}, ctx);
  assert.equal(smoke.details.job.status, "running");
  assert.ok(Date.now() - startedAt < 300);
  const smokeDone = await terminal(tool, smoke.details.job.jobId, ctx);
  assert.equal(smokeDone.status, "succeeded", smokeDone.summary);
  assert.equal((await readFile(smokeOutput, "utf8")).trim(), "CODEX_REVIEW_SMOKE_READY");
  await new Promise((resolve) => setTimeout(resolve, 100));
  assert.equal(completions().length, 1);

  const prompt = path.join(temporary, "prompt.md");
  const output = path.join(temporary, "review.md");
  await writeFile(prompt, "Review only the repository README title and report whether it is readable. Keep the review tiny and end with exactly VERDICT: CLEAN_FOR_PR unless a real blocking issue exists.\n");
  const review = await tool.execute("review", { action: "start", reviewType: "implementation-review", verdictProfile: "generic-implementation", cwd, promptFile: prompt, output }, new AbortController().signal, () => {}, ctx);
  const done = await terminal(tool, review.details.job.jobId, ctx);
  assert.equal(done.status, "succeeded", done.summary);
  assert.match(await readFile(output, "utf8"), /VERDICT: (CLEAN_FOR_PR|FINDINGS_TO_RESOLVE|BLOCKED_BY_QUESTION|REVIEW_INCOMPLETE_RERUN_NEEDED)\s*$/);
  await new Promise((resolve) => setTimeout(resolve, 100));
  assert.equal(completions().length, 2);
  assert.equal(new Set(completions().map((message) => message.details.jobId)).size, 2);
  await session.extensionRunner.emit({ type: "session_shutdown", reason: "quit" });
  session.dispose();
});
