import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import { readFileSync, readdirSync } from "node:fs";
import { chmod, mkdir, mkdtemp, readFile, rm, writeFile } from "node:fs/promises";
import os from "node:os";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";
import { CodexReviewJobManager } from "../runtime.ts";

const launcher = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../../skills/codex-review-partner/scripts/run-review.sh");
function live(pid) { try { const raw = readFileSync(`/proc/${pid}/stat`, "utf8"), tail = raw.slice(raw.lastIndexOf(")") + 2).split(" "); return tail[0] !== "Z"; } catch { return false; } }
function liveGroupMembers(pgid) { const result = []; for (const name of readdirSync("/proc")) { if (!/^\d+$/.test(name)) continue; try { const raw = readFileSync(`/proc/${name}/stat`, "utf8"), tail = raw.slice(raw.lastIndexOf(")") + 2).split(" "); if (tail[0] !== "Z" && Number(tail[2]) === pgid) result.push(Number(name)); } catch {} } return result; }
async function waitGone(pids) { for (let i = 0; i < 120; i += 1) { if (pids.every((pid) => !live(pid))) return; await new Promise((resolve) => setTimeout(resolve, 25)); } throw new Error(`live production descendants: ${pids.filter(live).join(",")}`); }
async function waitGroupGone(pgid) { for (let i = 0; i < 120; i += 1) { if (liveGroupMembers(pgid).length === 0) return; await new Promise((resolve) => setTimeout(resolve, 25)); } throw new Error(`live production launcher-group members: ${liveGroupMembers(pgid).join(",")}`); }

async function fixture(t) {
  const root = await mkdtemp(path.join(os.tmpdir(), "codex-production-tree-")); t.after(() => rm(root, { recursive: true, force: true }));
  const bin = path.join(root, "bin"); await mkdir(bin); const pids = path.join(root, "pids");
  const codex = path.join(bin, "codex");
  await writeFile(codex, `#!/usr/bin/env python3
import os,pathlib,signal,subprocess,sys,time
if sys.argv[1:]==['--version']: print('codex-cli 0.144.4'); raise SystemExit
pathlib.Path(os.environ['TREE_PIDS']).write_text(str(os.getpid())+'\\n')
child=subprocess.Popen([sys.executable,'-c','import signal,time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(60)'])
with pathlib.Path(os.environ['TREE_PIDS']).open('a') as f: f.write(str(child.pid)+'\\n')
signal.signal(signal.SIGTERM, signal.SIG_IGN)
time.sleep(60)
`); await chmod(codex, 0o755);
  await writeFile(path.join(root, ".bash_profile"), `export PATH=${JSON.stringify(`${bin}:/usr/bin:/bin`)}\n`);
  const launcherShim = path.join(root, "run-review.sh");
  await writeFile(launcherShim, `#!/usr/bin/env bash\nexport HOME=${JSON.stringify(root)}\nexport SHELL=/bin/bash\nexport PATH=${JSON.stringify(`${bin}:/usr/bin:/bin`)}\nexport TREE_PIDS=${JSON.stringify(pids)}\nexec ${JSON.stringify(launcher)} "$@"\n`);
  await chmod(launcherShim, 0o755);
  const cwd = path.join(root, "repo"); await mkdir(cwd); const prompt = path.join(root, "prompt"); await writeFile(prompt, "bounded");
  return { root, cwd, prompt, pids, launcher: launcherShim };
}
async function startedPids(file) { for (let i = 0; i < 100; i += 1) { try { const rows = (await readFile(file, "utf8")).trim().split("\n").map(Number); if (rows.length === 2) return rows; } catch {} await new Promise((resolve) => setTimeout(resolve, 20)); } throw new Error("production Codex tree did not start"); }

test("controller cancellation reaps launcher login shell Codex and descendants in production topology", { concurrency: false }, async (t) => {
  const f = await fixture(t), notes = [], manager = new CodexReviewJobManager({ launcherPath: f.launcher, cacheDir: path.join(f.root, "cache"), onComplete: (event) => notes.push(event), killGraceMs: 50 });
  const job = await manager.start({ action: "start", reviewType: "implementation-review", verdictProfile: "generic-implementation", cwd: f.cwd, promptFile: f.prompt, output: path.join(f.root, "review") });
  const descendants = await startedPids(f.pids); assert.equal(await manager.cancel(job.jobId), true); await waitGone([job.pid, ...descendants]); assert.equal(notes.length, 1); await manager.shutdown();
});

test("unexpected real launcher death reaps Codex and its parent-bound watchdog before notification", { concurrency: false }, async (t) => {
  const f = await fixture(t), notes = [], manager = new CodexReviewJobManager({ launcherPath: f.launcher, cacheDir: path.join(f.root, "cache"), onComplete: (event) => notes.push({ event, launcherGroup: liveGroupMembers(job.pgid) }), killGraceMs: 50 });
  const job = await manager.start({ action: "start", reviewType: "implementation-review", verdictProfile: "generic-implementation", cwd: f.cwd, promptFile: f.prompt, output: path.join(f.root, "review") });
  const descendants = await startedPids(f.pids); process.kill(job.pid, "SIGKILL");
  for (let i = 0; i < 150 && manager.status(job.jobId)?.status === "running"; i += 1) await new Promise((resolve) => setTimeout(resolve, 20));
  await waitGone(descendants); await waitGroupGone(job.pgid);
  assert.equal(manager.status(job.jobId)?.classification, "CODEX_REVIEW_LAUNCHER_PROTOCOL_INVALID"); assert.equal(notes.length, 1); assert.deepEqual(notes[0].launcherGroup, []); await manager.shutdown();
});

test("outer timeout reaps the complete production topology before terminal delivery", { concurrency: false }, async (t) => {
  const f = await fixture(t), notes = [], manager = new CodexReviewJobManager({ launcherPath: f.launcher, cacheDir: path.join(f.root, "cache"), onComplete: (event) => notes.push(event), reviewWatchdogMs: 1000, killGraceMs: 50 });
  const job = await manager.start({ action: "start", reviewType: "implementation-review", verdictProfile: "generic-implementation", cwd: f.cwd, promptFile: f.prompt, output: path.join(f.root, "review") });
  const descendants = await startedPids(f.pids); for (let i = 0; i < 100 && manager.status(job.jobId)?.status === "running"; i += 1) await new Promise((resolve) => setTimeout(resolve, 20));
  assert.equal(manager.status(job.jobId)?.status, "timed_out"); await waitGone([job.pid, ...descendants]); assert.equal(notes.length, 1); await manager.shutdown();
});

test("managed inner timeout publishes valid timeout status and reaps Codex descendants", { concurrency: false }, async (t) => {
  const f = await fixture(t), statusFile = path.join(f.root, "status.json"), output = path.join(f.root, "review");
  const child = spawn(f.launcher, ["--mode", "implementation-review", "--verdict-profile", "generic-implementation", "--input", f.prompt, "--cwd", f.cwd, "--output", output, "--status-file", statusFile, "--timeout-seconds", "1"], { cwd: f.cwd, detached: true, shell: false, stdio: "ignore" });
  t.after(() => { try { process.kill(-child.pid, "SIGKILL"); } catch {} });
  const descendants = await startedPids(f.pids);
  const result = await new Promise((resolve, reject) => { child.once("error", reject); child.once("close", (code, signal) => resolve({ code, signal })); });
  assert.deepEqual(result, { code: 124, signal: null });
  const protocol = JSON.parse(await readFile(statusFile, "utf8"));
  assert.equal(protocol.classification, "CODEX_REVIEW_INNER_TIMEOUT"); assert.equal(protocol.matchedSource, "inner-timeout"); assert.equal(protocol.timeout, true); assert.equal(protocol.finalMessageValidation, "not-checked");
  await waitGone([child.pid, ...descendants]);
});
