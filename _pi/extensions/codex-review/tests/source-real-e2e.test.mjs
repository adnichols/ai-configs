import assert from "node:assert/strict";
import { chmod, mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
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

test("real source launcher smoke uses the worktree extension runtime without external setsid", { skip: process.env.RUN_REAL_CODEX_SOURCE_E2E !== "1", timeout: 4_500_000, concurrency: false }, async (t) => {
  const temporary = await mkdtemp(path.join(os.tmpdir(), "codex-real-source-"));
  t.after(() => rm(temporary, { recursive: true, force: true }));
  const sentinelBin = path.join(temporary, "sentinel-bin");
  await mkdir(sentinelBin);
  const setsid = path.join(sentinelBin, "setsid");
  const setsidMarker = path.join(temporary, "external-setsid-invoked");
  await writeFile(setsid, `#!/bin/sh\nprintf invoked >${JSON.stringify(setsidMarker)}\necho 'external setsid must not be invoked' >&2\nexit 97\n`);
  await chmod(setsid, 0o755);
  const originalPath = process.env.PATH;
  process.env.PATH = `${sentinelBin}${path.delimiter}${originalPath ?? ""}`;
  t.after(() => { if (originalPath === undefined) delete process.env.PATH; else process.env.PATH = originalPath; });
  const manager = new CodexReviewJobManager({ launcherPath: launcher, cacheDir: path.join(temporary, "cache") });
  t.after(() => manager.shutdown());
  const output = path.join(temporary, "smoke.txt");
  const started = await manager.start({ action: "smoke", cwd: repo, output });
  assert.equal(started.status, "running");
  const done = await terminal(manager, started.jobId);
  assert.equal(done.status, "succeeded", done.summary);
  assert.equal((await readFile(output, "utf8")).trim(), "CODEX_REVIEW_SMOKE_READY");
  await assert.rejects(readFile(setsidMarker), { code: "ENOENT" });
  await manager.shutdown();
});
