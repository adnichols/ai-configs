#!/usr/bin/env node
import { spawn, spawnSync } from "node:child_process";
import { closeSync, existsSync, openSync, readFileSync, readdirSync, renameSync, unlinkSync, writeFileSync } from "node:fs";
import os from "node:os";
import path from "node:path";

import { classifyArtifact } from "./artifact-contract.mjs";

const MAX_SUMMARY_CHARS = 5_000;

function bounded(text) {
  if (text.length <= MAX_SUMMARY_CHARS) return text;
  return `${text.slice(0, MAX_SUMMARY_CHARS)}\n[summary truncated; read the artifact/log for full output]`;
}

function safeRead(file) {
  try { return readFileSync(file, "utf8"); } catch { return ""; }
}

function writeState(file, state) {
  const tmp = `${file}.${process.pid}.tmp`;
  writeFileSync(tmp, `${JSON.stringify(state, null, 2)}\n`, { encoding: "utf8", mode: 0o600 });
  renameSync(tmp, file);
}

function processAlive(child) {
  return child && child.exitCode === null && child.signalCode === null;
}

function killTree(child, signal) {
  if (!processAlive(child)) return;
  try {
    if (process.platform !== "win32" && child.pid) process.kill(-child.pid, signal);
    else child.kill(signal);
  } catch {
    try { child.kill(signal); } catch { /* already gone */ }
  }
}

function cleanupPrivateTmuxSockets(reviewName, launcherPid) {
  if (!launcherPid || typeof process.getuid !== "function") return;
  const roots = [process.env.TMUX_TMPDIR, os.tmpdir(), "/tmp", "/private/tmp"].filter(Boolean);
  const bases = [...new Set(roots.map((root) => path.join(root, `tmux-${process.getuid()}`)))];
  const prefix = `claude-review-${reviewName.replace(/[^A-Za-z0-9_.-]+/g, "-").replace(/^-+|-+$/g, "")}-${launcherPid}-`;
  const killed = new Set();
  for (const base of bases) {
    let names;
    try { names = readdirSync(base); } catch { continue; }
    for (const name of names) {
      if (!name.startsWith(prefix) || killed.has(name)) continue;
      killed.add(name);
      try {
        spawnSync("tmux", ["-S", path.join(base, name), "kill-server"], { stdio: "ignore", timeout: 5_000, shell: false });
      } catch { /* socket is already gone or tmux is unavailable */ }
    }
  }
}

const requestFile = process.argv[2];
if (!requestFile) throw new Error("supervisor request file is required");
const request = JSON.parse(readFileSync(requestFile, "utf8"));
let state = JSON.parse(readFileSync(request.stateFile, "utf8"));
state.supervisorPid = process.pid;
state.heartbeatAt = new Date().toISOString();
writeState(request.stateFile, state);

let stdoutFd;
let stderrFd;
let child;
let watchdog;
let heartbeatTimer;
let forceKillTimer;
let requestedTerminalStatus;
let finalized = false;

function releaseReservation() {
  try {
    const reservation = JSON.parse(readFileSync(request.reservationFile, "utf8"));
    if (reservation.jobId === state.jobId) unlinkSync(request.reservationFile);
  } catch { /* already released or replaced */ }
}

function finalize(status, classification, summary, code = null, signal = null) {
  if (finalized) return;
  finalized = true;
  if (watchdog) clearTimeout(watchdog);
  if (heartbeatTimer) clearInterval(heartbeatTimer);
  if (forceKillTimer) clearTimeout(forceKillTimer);
  if (stdoutFd !== undefined) { try { closeSync(stdoutFd); } catch {} stdoutFd = undefined; }
  if (stderrFd !== undefined) { try { closeSync(stderrFd); } catch {} stderrFd = undefined; }
  state = {
    ...state,
    status,
    classification,
    summary: bounded(`${summary}\nstdout=${state.stdoutLog}\nstderr=${state.stderrLog}`),
    completedAt: new Date().toISOString(),
    exitCode: code,
    signal,
  };
  writeState(request.stateFile, state);
  releaseReservation();
  try { unlinkSync(requestFile); } catch { /* already removed */ }
}

function requestStop(status) {
  if (finalized || requestedTerminalStatus) return;
  requestedTerminalStatus = status;
  killTree(child, "SIGTERM");
  forceKillTimer = setTimeout(() => killTree(child, "SIGKILL"), request.killGraceMs);
  forceKillTimer.unref?.();
}

process.on("SIGTERM", () => requestStop("cancelled"));
process.on("SIGINT", () => requestStop("cancelled"));
process.on("uncaughtException", (error) => {
  if (child?.pid) {
    killTree(child, "SIGKILL");
    cleanupPrivateTmuxSockets(request.reviewName, child.pid);
  }
  finalize("interrupted", "CLAUDE_REVIEW_SUPERVISOR_FAILED", String(error));
  process.exitCode = 1;
});

try {
  stdoutFd = openSync(state.stdoutLog, "a", 0o600);
  stderrFd = openSync(state.stderrLog, "a", 0o600);
  child = spawn(request.pythonExecutable, [request.launcherPath, ...request.launcherArgs], {
    cwd: state.cwd,
    detached: process.platform !== "win32",
    shell: false,
    stdio: ["ignore", stdoutFd, stderrFd],
  });
  state.launcherPid = child.pid;
  state.heartbeatAt = new Date().toISOString();
  writeState(request.stateFile, state);
  heartbeatTimer = setInterval(() => {
    if (finalized) return;
    state.heartbeatAt = new Date().toISOString();
    writeState(request.stateFile, state);
  }, 2_000);
  if (requestedTerminalStatus) killTree(child, "SIGTERM");

  child.once("error", (error) => {
    finalize("failed", "CLAUDE_REVIEW_SPAWN_FAILED", String(error));
  });
  child.once("exit", (code, signal) => {
    if (finalized) return;
    if (requestedTerminalStatus === "timed_out") {
      cleanupPrivateTmuxSockets(request.reviewName, child.pid);
      finalize("timed_out", "CLAUDE_REVIEW_OUTER_TIMEOUT", `Outer watchdog timed out; private tmux cleanup attempted; output=${state.output}`, code, signal);
      return;
    }
    if (requestedTerminalStatus === "cancelled") {
      cleanupPrivateTmuxSockets(request.reviewName, child.pid);
      finalize("cancelled", "CLAUDE_REVIEW_CANCELLED", `Claude review job was explicitly cancelled and private tmux cleanup was attempted; output=${state.output}`, code, signal);
      return;
    }

    const artifactExists = existsSync(state.output);
    const artifact = artifactExists ? safeRead(state.output) : "";
    if (code === 0) {
      if (!artifactExists) {
        finalize("failed", "CLAUDE_REVIEW_ARTIFACT_MISSING", `Launcher exited zero but did not create output=${state.output}`, code, signal);
        return;
      }
      const result = classifyArtifact(state.action, artifact);
      if (!result.ok) {
        finalize("failed", result.classification, bounded(artifact || `Invalid output=${state.output}`), code, signal);
        return;
      }
      finalize("succeeded", result.classification, `Claude ${state.action === "smoke" ? "smoke" : "review"} transport succeeded; output=${state.output}`, code, signal);
      return;
    }

    if (artifactExists) {
      const result = classifyArtifact(state.action, artifact);
      finalize("failed", result.ok ? "CLAUDE_REVIEW_PROCESS_FAILED" : result.classification, bounded(artifact), code, signal);
      return;
    }
    const stderr = safeRead(state.stderrLog);
    const stdout = safeRead(state.stdoutLog);
    finalize(
      "failed",
      "CLAUDE_REVIEW_PROCESS_FAILED",
      bounded(`Launcher exited ${code ?? "without code"} and produced no artifact.\nstdout=${state.stdoutLog}\nstderr=${state.stderrLog}\n${stderr || stdout}`),
      code,
      signal,
    );
  });

  watchdog = setTimeout(() => requestStop("timed_out"), request.watchdogMs);
  watchdog.unref?.();
} catch (error) {
  finalize("failed", "CLAUDE_REVIEW_SPAWN_FAILED", String(error));
  process.exitCode = 1;
}
