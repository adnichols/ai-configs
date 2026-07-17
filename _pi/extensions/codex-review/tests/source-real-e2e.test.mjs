import assert from "node:assert/strict";
import { mkdtemp, readFile, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { CodexReviewJobManager } from "../runtime.ts";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../..");
const launcher = path.join(repo, "skills/codex-review-partner/scripts/run-review.sh");

async function terminal(manager, jobId) {
  for (let attempt = 0; attempt < 2_100; attempt += 1) {
    const job = manager.status(jobId);
    if (job && !["starting", "running"].includes(job.status)) return job;
    await new Promise((resolve) => setTimeout(resolve, 2_000));
  }
  throw new Error("real source Codex smoke exceeded controller budget");
}

test("real source launcher smoke uses the worktree extension runtime without external setsid", { skip: process.env.RUN_REAL_CODEX_SOURCE_E2E !== "1", timeout: 4_500_000 }, async (t) => {
  const temporary = await mkdtemp(path.join(os.tmpdir(), "codex-real-source-"));
  t.after(() => rm(temporary, { recursive: true, force: true }));
  const manager = new CodexReviewJobManager({ launcherPath: launcher, cacheDir: path.join(temporary, "cache") });
  t.after(() => manager.shutdown());
  const output = path.join(temporary, "smoke.txt");
  const started = await manager.start({ action: "smoke", cwd: repo, output });
  assert.equal(started.status, "running");
  const done = await terminal(manager, started.jobId);
  assert.equal(done.status, "succeeded", done.summary);
  assert.equal((await readFile(output, "utf8")).trim(), "CODEX_REVIEW_SMOKE_READY");
  await manager.shutdown();
});
