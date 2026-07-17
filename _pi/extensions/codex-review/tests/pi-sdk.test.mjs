import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import { chmod, copyFile, mkdir, mkdtemp, readFile, realpath, rm, writeFile } from "node:fs/promises";
import { realpathSync } from "node:fs";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath, pathToFileURL } from "node:url";
import { isForbiddenDirectReviewToolCall } from "../runtime.ts";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../..");
const extensionPath = path.join(repo, "_pi/extensions/codex-review/index.ts");
const fake = path.join(repo, "_pi/extensions/codex-review/tests/fixtures/fake_launcher.py");

async function sdk() {
  const bin = realpathSync(execFileSync("which", ["pi"], { encoding: "utf8" }).trim());
  return import(pathToFileURL(path.join(path.resolve(path.dirname(bin), ".."), "dist", "index.js")));
}

test("real Pi loader registers restricted codex_review schema, guard, and visible subprocess lifecycle", async (t) => {
  const home = await mkdtemp(path.join(os.tmpdir(), "pi-codex-sdk-"));
  t.after(() => rm(home, { recursive: true, force: true }));
  const launcher = path.join(home, ".agents/skills/codex-review-partner/scripts/run-review.sh");
  await mkdir(path.dirname(launcher), { recursive: true });
  await copyFile(fake, launcher);
  await chmod(launcher, 0o755);
  const old = process.env.HOME;
  process.env.HOME = home;
  t.after(() => old === undefined ? delete process.env.HOME : process.env.HOME = old);

  const s = await sdk();
  const loader = new s.DefaultResourceLoader({
    cwd: repo,
    agentDir: path.join(home, ".pi/agent"),
    additionalExtensionPaths: [extensionPath],
    settingsManager: s.SettingsManager.inMemory({}),
  });
  await loader.reload();
  const loaded = loader.getExtensions();
  assert.deepEqual(loaded.errors, []);
  const resolved = await realpath(extensionPath);
  const ext = loaded.extensions.find((item) => item.resolvedPath === resolved);
  const tool = ext.tools.get("codex_review").definition;
  assert.ok(tool);
  assert.deepEqual(Object.keys(tool.parameters.properties).sort(), ["action", "cwd", "jobId", "output", "promptFile", "reviewType", "verdictProfile"].sort());
  const guard = ext.handlers.get("tool_call")[0];
  assert.equal((await guard({ toolName: "process", input: { command: "run-review.sh --mode plan-review --input p" } })).block, true);
  assert.equal(await guard({ toolName: "bash", input: { command: "codex --version" } }), undefined);

  const promptFile = path.join(home, "visible-prompt.md");
  const output = path.join(home, "visible-review.md");
  await writeFile(promptFile, "MODE=success\nDELAY=0.3\n");
  const updates = [];
  let settled = false;
  const execution = tool.execute(
    "visible-review",
    {
      action: "start",
      reviewType: "implementation-review",
      verdictProfile: "generic-implementation",
      cwd: repo,
      promptFile,
      output,
    },
    new AbortController().signal,
    (update) => updates.push(update),
    { cwd: repo },
  ).finally(() => { settled = true; });
  await new Promise((resolvePromise) => setTimeout(resolvePromise, 80));
  assert.equal(settled, false, "visible Codex review tool call must stay active while its subprocess runs");
  assert.ok(updates.length > 0, "visible Codex review tool call must publish a running update");
  assert.equal(updates[0].details.phase, "running");
  assert.match(updates[0].content[0].text, /reviewer subprocess running/);
  const result = await execution;
  assert.equal(result.details.phase, "completed");
  assert.equal(result.details.job.status, "succeeded");
  assert.equal(result.details.job.deliveryState, "delivering");
  await ext.handlers.get("message_start")[0]({ message: { role: "toolResult", toolName: "codex_review", details: result.details } });
  const delivered = await tool.execute("status-call", { action: "status", jobId: result.details.job.jobId }, new AbortController().signal, () => {}, { cwd: repo });
  assert.equal(delivered.details.job.deliveryState, "delivered");
  assert.match(result.content[0].text, /reviewer subprocess completed/);
  assert.match(await readFile(output, "utf8"), /VERDICT: CLEAN_FOR_PR/);

  await ext.handlers.get("session_shutdown")[0]();
});

test("positive guard signatures block while pair/version/free-form remain allowed", () => {
  assert.equal(isForbiddenDirectReviewToolCall("bash", { command: "run-review.sh --mode plan-review --input p" }).blocked, true);
  assert.equal(isForbiddenDirectReviewToolCall("interactive_shell", { command: "codex exec review --base main" }).blocked, true);
  for (const command of ["run-review.sh --mode pair --input p", "codex --version", "codex exec \"implement review parser\""]) {
    assert.equal(isForbiddenDirectReviewToolCall("bash", { command }).blocked, false);
  }
});
