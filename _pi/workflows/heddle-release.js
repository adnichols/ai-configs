/*
 * Heddle release workflow (Herdr-native)
 *
 * Launch from a Herdr pane. Orchestrates via `herdr` CLI only.
 * Workflow bookkeeping lives OUTSIDE the git worktree so signed-release
 * provenance stays clean:
 *   ~/.heddle-release/v{version}/
 *
 * Stages (auto-resume from on-disk progress):
 *   cut → gate (interactive TTY) → build (single flocked shell) → publish
 *
 * args:
 *   parentRepo, developRepo, worktreePath, githubRepo, bump,
 *   publishTarget, slackChannel, slackWorkspace, herdrSession, agentKind,
 *   dryRun, resumeFrom (auto|after-cut|after-gate|build|publish),
 *   releaseVersion
 */

function asNonEmptyString(value) {
  return typeof value === "string" && value.trim() ? value.trim() : null;
}
function asBoolean(value, fallback = false) {
  return typeof value === "boolean" ? value : fallback;
}
function shellQuote(value) {
  const text = String(value);
  if (text === "") return "''";
  if (/^[A-Za-z0-9_@%+=:,./-]+$/.test(text)) return text;
  return `'${text.replace(/'/g, `'\\''`)}'`;
}
function joinCmd(parts) {
  return parts.map(shellQuote).join(" ");
}

async function run(command, options = {}) {
  return shell(command, options);
}
async function runOk(command, options = {}) {
  const result = await run(command, options);
  if (result.exitCode !== 0) {
    throw new Error(
      `Command failed (${result.exitCode}): ${command}\n${result.stderr || result.stdout}`,
    );
  }
  return result;
}
async function writeText(path, text) {
  const code = `from pathlib import Path; p=Path(${JSON.stringify(path)}); p.parent.mkdir(parents=True, exist_ok=True); p.write_text(${JSON.stringify(text)}, encoding="utf-8")`;
  await runOk(`python3 -c ${shellQuote(code)}`);
}
async function readText(path) {
  const code = `from pathlib import Path; p=Path(${JSON.stringify(path)}); print(p.read_text(encoding="utf-8") if p.exists() else "")`;
  return (await runOk(`python3 -c ${shellQuote(code)}`)).stdout;
}
async function readJson(path) {
  const raw = (await readText(path)).trim();
  if (!raw) return null;
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}
async function pathExists(path) {
  const r = await run(joinCmd(["bash", "-lc", `[[ -e ${shellQuote(path)} ]] && echo yes || true`]));
  return (r.stdout || "").includes("yes");
}
async function waitForFile(path, timeoutMs, intervalSec = 5) {
  const code = `
import time, sys
from pathlib import Path
path = Path(${JSON.stringify(path)})
deadline = time.time() + (${Number(timeoutMs)} / 1000.0)
while time.time() < deadline:
    if path.exists() and path.stat().st_size > 0:
        sys.exit(0)
    time.sleep(${Number(intervalSec)})
sys.exit(2)
`;
  const result = await run(`python3 -c ${shellQuote(code)}`, { timeoutMs: timeoutMs + 60_000 });
  return result.exitCode === 0;
}

const argsObject = args && typeof args === "object" && !Array.isArray(args) ? args : {};
const developRepo = asNonEmptyString(argsObject.developRepo) || "/Users/anichols/code/heddle-develop";
const parentRepo = asNonEmptyString(argsObject.parentRepo) || developRepo;
const githubRepo = asNonEmptyString(argsObject.githubRepo) || "Nodaste-Lab/heddle";
const bumpRaw = asNonEmptyString(argsObject.bump) || "patch";
const bump = ["patch", "minor", "major"].includes(bumpRaw) ? bumpRaw : null;
if (!bump) throw new Error('args.bump must be one of "patch", "minor", or "major"');
const publishTargetRaw = asNonEmptyString(argsObject.publishTarget);
const publishTarget = publishTargetRaw
  ? (["none", "github", "github-sparkle"].includes(publishTargetRaw) ? publishTargetRaw : null)
  : null;
if (publishTargetRaw && !publishTarget) {
  throw new Error('args.publishTarget must be one of "none", "github", or "github-sparkle"');
}
const slackChannel = asNonEmptyString(argsObject.slackChannel) || "#heddle-release";
const slackWorkspace = asNonEmptyString(argsObject.slackWorkspace) || "nodaste";
const herdrSession = asNonEmptyString(argsObject.herdrSession);
const agentKind = asNonEmptyString(argsObject.agentKind) || "pi";
const dryRun = asBoolean(argsObject.dryRun, false);
const worktreePathArg = asNonEmptyString(argsObject.worktreePath);
const explicitReleaseVersion = asNonEmptyString(argsObject.releaseVersion);
const resumeFromRaw = asNonEmptyString(argsObject.resumeFrom);
const resumeFrom = resumeFromRaw
  ? (["auto", "after-cut", "after-gate", "build", "publish"].includes(resumeFromRaw) ? resumeFromRaw : null)
  : null;
if (resumeFromRaw && !resumeFrom) {
  throw new Error('args.resumeFrom must be auto|after-cut|after-gate|build|publish');
}
const resumeRequested = resumeFrom !== null;

function herdrArgs(parts) {
  return herdrSession ? ["herdr", "--session", herdrSession, ...parts] : ["herdr", ...parts];
}
async function herdrJson(parts, options = {}) {
  const attempts = parts[0] === "worktree" ? [[...parts, "--json"], parts] : [parts, [...parts, "--json"]];
  let lastError = "";
  for (const attempt of attempts) {
    const result = await run(joinCmd(herdrArgs(attempt)), options);
    const stdout = (result.stdout || "").trim();
    const stderr = (result.stderr || "").trim();
    if (result.exitCode !== 0) {
      lastError = stderr || stdout || `exit ${result.exitCode}`;
      if (/unknown option.*json/i.test(lastError)) continue;
      throw new Error(`herdr failed: ${parts.join(" ")}\n${lastError}`);
    }
    if (!stdout) return {};
    try {
      return JSON.parse(stdout);
    } catch {
      lastError = `non-JSON: ${stdout.slice(0, 500)}`;
    }
  }
  throw new Error(`herdr failed: ${parts.join(" ")}\n${lastError}`);
}
function unwrapHerdr(payload) {
  if (payload && typeof payload === "object" && payload.result && typeof payload.result === "object") {
    return payload.result;
  }
  return payload || {};
}
async function splitPane(fromPaneId, direction, cwd, options = {}) {
  const focus = options.focus === true;
  const payload = unwrapHerdr(
    await herdrJson([
      "pane", "split", fromPaneId,
      "--direction", direction,
      "--cwd", cwd,
      focus ? "--focus" : "--no-focus",
    ]),
  );
  const pane = payload.pane || payload;
  const paneId = pane.pane_id || pane.paneId;
  if (!paneId) throw new Error(`pane split missing pane_id: ${JSON.stringify(payload)}`);
  return String(paneId);
}
/** Run a script file in a pane — never bash -lc with a long inline string (quoting breaks). */
async function paneRunScript(paneId, scriptPath, options = {}) {
  // herdr pane run <pane> bash <script>
  const cmd = joinCmd([...herdrArgs(["pane", "run", paneId, "bash", scriptPath])]);
  return run(cmd, options);
}
async function startAgent(name, paneId) {
  const parts = [
    ...herdrArgs(["agent", "start", name, "--kind", agentKind, "--pane", paneId, "--timeout", "120000"]),
  ];
  if (agentKind === "pi") {
    parts.push("--", "--provider", "openai-codex", "--model", "gpt-5.6-luna", "--thinking", "max");
  }
  const result = await run(joinCmd(parts), { timeoutMs: 180_000 });
  if (result.exitCode !== 0) {
    throw new Error(`herdr agent start ${name} failed:\n${result.stderr || result.stdout}`);
  }
  return true;
}
async function promptAgent(name, text, timeoutMs) {
  return run(
    joinCmd([
      ...herdrArgs([
        "agent", "prompt", name, text,
        "--wait", "--until", "idle", "--until", "done", "--until", "blocked",
        "--timeout", String(timeoutMs),
      ]),
    ]),
    { timeoutMs: timeoutMs + 60_000 },
  );
}
async function readAgentTail(name, lines = 80) {
  const result = await run(
    joinCmd([...herdrArgs(["agent", "read", name, "--source", "recent-unwrapped", "--lines", String(lines)])]),
    { timeoutMs: 60_000 },
  );
  return `${result.stdout || ""}\n${result.stderr || ""}`.trim();
}
async function gcStaleHelpers(stateDir) {
  // Best-effort: drop empty lock if nothing holds it; leave running builds alone.
  const lock = `${stateDir}/build.lock`;
  if (await pathExists(lock)) {
    const held = await run(joinCmd(["bash", "-lc", `lsof ${shellQuote(lock)} >/dev/null 2>&1 && echo held || echo free`]));
    if ((held.stdout || "").includes("free")) {
      await run(joinCmd(["rm", "-f", lock]));
    }
  }
}
/** Exclude .heddle-release/ in linked worktrees via git-dir info/exclude. */
async function ensureWorktreeExclude(worktreeRoot) {
  if (!(await pathExists(worktreeRoot))) return;
  await run(
    joinCmd([
      "bash",
      "-lc",
      `cd ${shellQuote(worktreeRoot)} && EXCL=$(git rev-parse --git-path info/exclude) && mkdir -p $(dirname "$EXCL") && (grep -qx '.heddle-release/' "$EXCL" 2>/dev/null || echo '.heddle-release/' >> "$EXCL")`,
    ]),
  );
}

// ---------------------------------------------------------------------------
phase("preflight-herdr");
log("Checking Herdr parent-pane context.");

const herdrEnv = await run('printf "%s" "${HERDR_PANE_ID:-}|${HERDR_ENV:-}|${HERDR_SOCKET_PATH:-}"');
const [parentPaneId, herdrEnvFlag, herdrSocket] = (herdrEnv.stdout || "").split("|");
if (!parentPaneId || herdrEnvFlag !== "1" || !herdrSocket) {
  throw new Error(
    "heddle-release must run from inside a Herdr pane (HERDR_PANE_ID + HERDR_ENV=1 + HERDR_SOCKET_PATH).",
  );
}
await runOk(joinCmd(["test", "-d", developRepo]));
await runOk(joinCmd(["test", "-d", parentRepo]));

const homeDir = (await runOk('printf "%s" "$HOME"')).stdout;
const launchCwd = (await runOk("pwd -P")).stdout.trim();
const stateName = ".heddle-release"; // legacy in-worktree name (migrated away)

async function loadPkgAndBranch(root) {
  if (!(await pathExists(root))) return { pkgVersion: null, branch: null };
  const meta = await run(
    joinCmd([
      "bash", "-lc",
      `cd ${shellQuote(root)} && node -p "require('./package.json').version" 2>/dev/null; git branch --show-current 2>/dev/null; true`,
    ]),
  );
  const lines = (meta.stdout || "").trim().split("\n").map((s) => s.trim()).filter(Boolean);
  let pkgVersion = null;
  let branch = null;
  for (const line of lines) {
    if (!pkgVersion && /^[0-9]+\.[0-9]+\.[0-9]+/.test(line)) pkgVersion = line.split("+")[0];
    else if (!branch && (line.startsWith("release/") || line === "develop" || line === "main")) branch = line;
  }
  return { pkgVersion, branch };
}

function versionFromBits({ cut, pkgVersion, branch, root }) {
  if (cut && cut.releaseVersion) return String(cut.releaseVersion).split("+")[0];
  if (branch) {
    const m = String(branch).match(/^release\/v?([0-9]+\.[0-9]+\.[0-9]+)/);
    if (m) return m[1];
  }
  if (pkgVersion) return pkgVersion;
  if (root) {
    const m2 = String(root).match(/release-v?([0-9]+\.[0-9]+\.[0-9]+)\/?$/);
    if (m2) return m2[1];
  }
  return null;
}

function looksLikeReleaseWorktree({ cut, branch, root }) {
  if (cut && cut.status === "ready") return true;
  if (branch && /^release\//.test(branch)) return true;
  if (root && /\/release-v?[0-9]+\.[0-9]+\.[0-9]+\/?$/.test(root)) return true;
  if (root && String(root).includes("/.herdr/worktrees/heddle/release")) return true;
  return false;
}

async function loadStateBundle(worktreeRoot, versionHint) {
  const ver = versionHint || versionFromBits(await (async () => {
    const mb = await loadPkgAndBranch(worktreeRoot);
    const legacyCut = worktreeRoot ? await readJson(`${worktreeRoot}/${stateName}/cut.json`) : null;
    return { cut: legacyCut, pkgVersion: mb.pkgVersion, branch: mb.branch, root: worktreeRoot };
  })());
  const external = ver ? `${homeDir}/.heddle-release/v${ver}` : null;
  const legacy = worktreeRoot ? `${worktreeRoot}/${stateName}` : null;

  // Prefer external state; fall back to legacy in-worktree state from earlier runs.
  let stateDir = null;
  if (external && (await pathExists(`${external}/cut.json`) || await pathExists(external))) {
    stateDir = external;
  } else if (legacy && (await pathExists(`${legacy}/cut.json`))) {
    stateDir = legacy;
  } else if (external) {
    stateDir = external;
  } else if (legacy) {
    stateDir = legacy;
  }

  const cut = stateDir ? await readJson(`${stateDir}/cut.json`) : null;
  const gate = stateDir ? await readJson(`${stateDir}/gate.json`) : null;
  const build = stateDir ? await readJson(`${stateDir}/build.json`) : null;
  const publish = stateDir ? await readJson(`${stateDir}/publish.json`) : null;
  const progress = stateDir ? await readJson(`${stateDir}/progress.json`) : null;
  const mb = await loadPkgAndBranch(worktreeRoot);
  return {
    worktreeRoot,
    stateDir,
    external,
    legacy,
    version: versionFromBits({ cut, pkgVersion: mb.pkgVersion, branch: mb.branch, root: worktreeRoot }) || ver,
    cut,
    gate,
    build,
    publish,
    progress,
    branch: mb.branch,
    pkgVersion: mb.pkgVersion,
  };
}

// Resolve worktree + version (resume never trusts develop tip first).
let worktreePath = worktreePathArg;
let releaseVersion = explicitReleaseVersion ? explicitReleaseVersion.split("+")[0] : null;
let bundle = null;

if (worktreePath) {
  bundle = await loadStateBundle(worktreePath, releaseVersion);
  releaseVersion = releaseVersion || bundle.version;
}
if (!releaseVersion && resumeRequested) {
  // try cwd
  const cwdBundle = await loadStateBundle(launchCwd, null);
  if (cwdBundle && looksLikeReleaseWorktree(cwdBundle)) {
    bundle = cwdBundle;
    worktreePath = cwdBundle.worktreeRoot;
    releaseVersion = cwdBundle.version;
    log(`Detected release worktree from cwd: ${worktreePath} (v${releaseVersion || "?"}).`);
  }
}
if (!releaseVersion && !resumeRequested) {
  // Fresh release: version from origin/develop
  const versionRes = await runOk(
    joinCmd([
      "bash", "-lc",
      `git -C ${shellQuote(developRepo)} fetch origin develop --prune && git -C ${shellQuote(developRepo)} show origin/develop:package.json | node -e "let s='';process.stdin.on('data',d=>s+=d);process.stdin.on('end',()=>{const v=JSON.parse(s).version||'';process.stdout.write(String(v).split('+')[0])})"`,
    ]),
    { timeoutMs: 120_000 },
  );
  releaseVersion = (versionRes.stdout || "").trim();
}
// cwd detection for full /heddle:release launched inside a release worktree
if (!bundle) {
  const cwdBundle = await loadStateBundle(launchCwd, releaseVersion);
  if (cwdBundle && looksLikeReleaseWorktree(cwdBundle)) {
    bundle = cwdBundle;
    worktreePath = worktreePath || cwdBundle.worktreeRoot;
    releaseVersion = releaseVersion || cwdBundle.version;
    if (cwdBundle.cut && cwdBundle.cut.status === "ready") {
      log(`Found existing release progress in cwd; will auto-resume (v${releaseVersion}).`);
    }
  }
}
if (!releaseVersion && explicitReleaseVersion) releaseVersion = explicitReleaseVersion.split("+")[0];
if (!/^[0-9]+\.[0-9]+\.[0-9]+/.test(releaseVersion || "")) {
  throw new Error(
    resumeRequested
      ? "Resume could not detect release version. Run from the release worktree or pass releaseVersion=0.x.y."
      : `Could not resolve release version (got ${JSON.stringify(releaseVersion)})`,
  );
}

const releaseBranch = `release/v${releaseVersion}`;
if (!worktreePath) worktreePath = `${homeDir}/.herdr/worktrees/heddle/release-v${releaseVersion}`;
if (!bundle || bundle.worktreeRoot !== worktreePath) {
  bundle = await loadStateBundle(worktreePath, releaseVersion);
}

// Canonical state dir: always external going forward.
const stateDir = `${homeDir}/.heddle-release/v${releaseVersion}`;
await runOk(joinCmd(["mkdir", "-p", `${stateDir}/prompts`, `${stateDir}/scripts`]));

// Migrate legacy in-worktree state into external dir (once).
if (bundle.legacy && bundle.legacy !== stateDir && (await pathExists(bundle.legacy))) {
  log(`Migrating legacy state ${bundle.legacy} → ${stateDir}`);
  await run(
    joinCmd([
      "bash", "-lc",
      `cp -n ${shellQuote(bundle.legacy)}/*.json ${shellQuote(stateDir)}/ 2>/dev/null || true; cp -n ${shellQuote(bundle.legacy)}/prompts/* ${shellQuote(stateDir)}/prompts/ 2>/dev/null || true`,
    ]),
  );
  // Ensure worktree exclude so leftover legacy files don't dirty provenance if present.
  await ensureWorktreeExclude(worktreePath);
}

// Reload after migration
let cut = await readJson(`${stateDir}/cut.json`);
let priorGate = await readJson(`${stateDir}/gate.json`);
let priorBuild = await readJson(`${stateDir}/build.json`);
let priorPublish = await readJson(`${stateDir}/publish.json`);

const cutReady = !!(cut && cut.status === "ready");
const gateAlreadyOpen = !!(priorGate && priorGate.status === "open");
const buildAlreadyDone = !!(priorBuild && priorBuild.status === "built" && priorBuild.pkgPath);
const publishReady = !!(
  priorPublish && ["completed", "built_not_published"].includes(String(priorPublish.status || ""))
);

function computeNext() {
  if (!cutReady) return "cut";
  if (!gateAlreadyOpen) return "gate";
  if (!buildAlreadyDone) return "build";
  if (!publishReady) return "publish";
  return "done";
}
let progressStage = computeNext();

let effectiveResume = resumeFrom;
if (!effectiveResume && cutReady) effectiveResume = "auto";
if (resumeRequested && !effectiveResume) effectiveResume = "auto";

let skipCut = false;
let skipGate = false;
let skipBuild = false;
if (effectiveResume === "auto") {
  skipCut = cutReady;
  skipGate = cutReady && gateAlreadyOpen;
  skipBuild = cutReady && buildAlreadyDone;
} else if (effectiveResume === "after-cut") {
  if (!cutReady) throw new Error(`resumeFrom=after-cut needs ready cut.json in ${stateDir}`);
  skipCut = true;
} else if (effectiveResume === "after-gate" || effectiveResume === "build") {
  if (!cutReady) throw new Error(`resumeFrom=${effectiveResume} needs ready cut.json`);
  skipCut = true;
  skipGate = true;
} else if (effectiveResume === "publish") {
  if (!buildAlreadyDone) throw new Error("resumeFrom=publish needs build.json status=built");
  skipCut = true;
  skipGate = true;
  skipBuild = true;
}

const label = `heddle ${releaseBranch}`;
const config = {
  parentPaneId,
  parentRepo,
  developRepo,
  githubRepo,
  bump,
  publishTarget,
  slackChannel,
  slackWorkspace,
  herdrSession,
  agentKind,
  dryRun,
  resumeFrom: effectiveResume || null,
  progressStage,
  skipCut,
  skipGate,
  skipBuild,
  releaseVersion,
  releaseBranch,
  worktreePath,
  stateDir,
  label,
};

log(
  `Release v${releaseVersion} (${releaseBranch}) dryRun=${dryRun} resume=${effectiveResume || "none"} next=${progressStage} skip[cut=${skipCut},gate=${skipGate},build=${skipBuild}] stateDir=${stateDir}`,
);

async function writeProgress(stage, extra = {}) {
  const c = extra.cut || cut;
  const g = extra.gate || priorGate;
  const b = extra.build || priorBuild;
  const p = extra.publish || priorPublish;
  let next = "cut";
  if (c && c.status === "ready") next = "gate";
  if (c && c.status === "ready" && g && g.status === "open") next = "build";
  if (c && c.status === "ready" && b && b.status === "built" && b.pkgPath) next = "publish";
  if (
    c && c.status === "ready" &&
    b && b.status === "built" && b.pkgPath &&
    p && ["completed", "built_not_published"].includes(String(p.status || ""))
  ) next = "done";
  const payload = {
    releaseVersion,
    releaseBranch,
    worktreePath,
    stateDir,
    stage,
    cut: c && c.status ? c.status : null,
    gate: g && g.status ? g.status : null,
    build: b && b.status ? b.status : null,
    publish: p && p.status ? p.status : null,
    next,
    updatedAt: (await runOk('date -u +"%Y-%m-%dT%H:%M:%SZ"')).stdout.trim(),
  };
  await writeText(`${stateDir}/progress.json`, JSON.stringify(payload, null, 2));
}

await gcStaleHelpers(stateDir);
await writeProgress(effectiveResume ? `resume-${progressStage}` : "start");

if (dryRun) {
  phase("dry-run-plan");
  return {
    ok: true,
    dryRun: true,
    config,
    plan: [
      skipCut ? `Skip cut (reuse ${stateDir}/cut.json)` : `Cut release branch + bump develop`,
      skipGate ? `Skip gate open (verify only)` : `Interactive open-gate + gate-watch`,
      skipBuild ? `Skip build (reuse pkg)` : `Flocked npm ci + one release:signed (state outside worktree)`,
      `Publish pane + optional Slack ${slackChannel}`,
    ],
  };
}

if (progressStage === "done") {
  return {
    ok: true,
    alreadyComplete: true,
    config,
    cut,
    gate: priorGate,
    build: priorBuild,
    publish: priorPublish,
    stateDir,
  };
}

// ---------------------------------------------------------------------------
phase("create-release-worktree");
log(`Ensuring Herdr worktree for ${releaseBranch} at ${worktreePath}`);

let workspaceId = null;
let tabId = null;
let rootPaneId = null;
let worktreeCheckout = worktreePath;

const existing = await run(
  joinCmd(["bash", "-lc", `git -C ${shellQuote(parentRepo)} worktree list --porcelain | rg -F ${shellQuote(worktreePath)} || true`]),
);
if ((existing.stdout || "").includes(worktreePath) || (await pathExists(worktreePath))) {
  log("Opening existing worktree in Herdr.");
  const opened = unwrapHerdr(
    await herdrJson([
      "worktree", "open", "--cwd", parentRepo, "--path", worktreePath,
      "--label", label, "--no-focus",
    ]),
  );
  const rootPane = opened.root_pane || {};
  const workspace = opened.workspace || {};
  const tab = opened.tab || {};
  const worktree = opened.worktree || {};
  rootPaneId = rootPane.pane_id || null;
  tabId = tab.tab_id || rootPane.tab_id || null;
  workspaceId = workspace.workspace_id || rootPane.workspace_id || worktree.open_workspace_id || null;
  worktreeCheckout =
    worktree.path || (workspace.worktree && workspace.worktree.checkout_path) || rootPane.cwd || worktreePath;
} else {
  const created = unwrapHerdr(
    await herdrJson([
      "worktree", "create", "--cwd", parentRepo,
      "--branch", releaseBranch, "--base", "origin/develop",
      "--path", worktreePath, "--label", label, "--no-focus",
    ]),
  );
  const rootPane = created.root_pane || {};
  const workspace = created.workspace || {};
  const tab = created.tab || {};
  const worktree = created.worktree || {};
  rootPaneId = rootPane.pane_id || null;
  tabId = tab.tab_id || rootPane.tab_id || null;
  workspaceId = workspace.workspace_id || rootPane.workspace_id || worktree.open_workspace_id || null;
  worktreeCheckout =
    worktree.path || (workspace.worktree && workspace.worktree.checkout_path) || rootPane.cwd || worktreePath;
}
if (!rootPaneId) throw new Error("Herdr worktree create/open did not return root_pane.pane_id");

// Exclude any leftover in-tree state dir from dirty checks.
await ensureWorktreeExclude(worktreeCheckout);

await writeText(
  `${stateDir}/config.json`,
  JSON.stringify({ ...config, worktreeCheckout, workspaceId, tabId, rootPaneId }, null, 2),
);

// ---------------------------------------------------------------------------
// CUT — deterministic script; agent only runs it (or shell runs on skip path)
// ---------------------------------------------------------------------------
const cutScriptPath = `${stateDir}/scripts/run-cut.sh`;
const cutResultPath = `${stateDir}/cut.json`;

// Build cut script without JS ${ bash expansions
const cutScriptLines = [
  "#!/usr/bin/env bash",
  "set -euo pipefail",
  `WORKTREE=${JSON.stringify(worktreeCheckout)}`,
  `DEVELOP_REPO=${JSON.stringify(developRepo)}`,
  `RELEASE_BRANCH=${JSON.stringify(releaseBranch)}`,
  `RELEASE_VERSION=${JSON.stringify(releaseVersion)}`,
  `BUMP=${JSON.stringify(bump)}`,
  `CUT_JSON=${JSON.stringify(cutResultPath)}`,
  `STATE_DIR=${JSON.stringify(stateDir)}`,
  'GIT_WL="$(command -v git-with-index-lock 2>/dev/null || true)"',
  'if [[ -z "$GIT_WL" && -x "$HOME/.local/bin/git-with-index-lock" ]]; then GIT_WL="$HOME/.local/bin/git-with-index-lock"; fi',
  'if [[ -z "$GIT_WL" ]]; then GIT_WL=git; fi',
  'log() { printf "[cut] %s\\n" "$*"; }',
  'fail_json() {',
  '  local msg="$1"',
  '  python3 - "$CUT_JSON" "$msg" <<\'PY\'',
  "import json,sys",
  "path,msg=sys.argv[1],sys.argv[2]",
  "open(path,'w').write(json.dumps({'status':'failed','blockers':[msg],'evidence':[]},indent=2)+'\\n')",
  "PY",
  "  exit 1",
  "}",
  'cd "$WORKTREE"',
  'log "worktree=$(pwd) branch=$(git branch --show-current)"',
  'git fetch origin develop --prune',
  '# Ensure release branch matches expected version tip',
  'if [[ "$(git branch --show-current)" != "$RELEASE_BRANCH" ]]; then',
  '  git switch -C "$RELEASE_BRANCH" || git switch "$RELEASE_BRANCH"',
  "fi",
  'git push -u origin "$RELEASE_BRANCH"',
  'RELEASE_SHA="$(git rev-parse HEAD)"',
  'log "pushed $RELEASE_BRANCH @$RELEASE_SHA"',
  '# Bump develop on a clean temporary worktree so dirty personal checkouts are untouched',
  'TMP_DEV="$(mktemp -d "${TMPDIR:-/tmp}/heddle-cut-develop.XXXXXX")"',
  'cleanup() { rm -rf "$TMP_DEV"; }',
  "trap cleanup EXIT",
  'git -C "$DEVELOP_REPO" fetch origin develop --prune',
  'git -C "$DEVELOP_REPO" worktree add --detach "$TMP_DEV" origin/develop',
  'cd "$TMP_DEV"',
  'git switch -C develop origin/develop',
  '# Prefer direct script so a bare worktree does not need npm ci',
  'bash scripts/release/cut-release.sh --$BUMP',
  'NEXT_VERSION="$(node -p "require(\'./package.json\').version.split(\'+\')[0]")"',
  'if [[ -z "$(git status --porcelain)" ]]; then fail_json "release:cut made no changes"; fi',
  '"$GIT_WL" add -A',
  '"$GIT_WL" commit -m "chore(release): bump develop after cutting v$RELEASE_VERSION"',
  'git push origin develop',
  'DEVELOP_SHA="$(git rev-parse HEAD)"',
  'log "develop now $NEXT_VERSION @$DEVELOP_SHA"',
  'python3 - "$CUT_JSON" "$RELEASE_VERSION" "$RELEASE_BRANCH" "$NEXT_VERSION" "$RELEASE_SHA" "$DEVELOP_SHA" <<\'PY\'',
  "import json,sys",
  "path,rv,rb,nv,rs,ds=sys.argv[1:7]",
  "open(path,'w').write(json.dumps({",
  "  'status':'ready',",
  "  'releaseVersion':rv,",
  "  'releaseBranch':rb,",
  "  'developNextVersion':nv,",
  "  'releaseHeadSha':rs,",
  "  'developHeadSha':ds,",
  "  'evidence':['deterministic run-cut.sh','pushed release branch','bumped develop in temp worktree','pushed develop'],",
  "  'blockers':[],",
  "}, indent=2)+'\\n')",
  "PY",
  'log "wrote $CUT_JSON"',
];
await writeText(cutScriptPath, cutScriptLines.join("\n") + "\n");
await runOk(joinCmd(["chmod", "+x", cutScriptPath]));

if (skipCut) {
  phase("cut-skipped");
  log(`Skipping cut; reusing ${cutResultPath}`);
  if (!cut || cut.status !== "ready") throw new Error(`skipCut but cut.json not ready at ${cutResultPath}`);
  await writeProgress("cut-skipped", { cut });
} else {
  phase("cut");
  log("Running deterministic cut script in a shell pane (not an exploratory agent).");
  const cutPaneId = rootPaneId;
  const cutRun = await paneRunScript(cutPaneId, cutScriptPath, { timeoutMs: 45 * 60 * 1000 });
  cut = (await readJson(cutResultPath)) || {
    status: "failed",
    blockers: [
      `cut script did not write ${cutResultPath}`,
      `exit=${cutRun.exitCode}`,
      (cutRun.stderr || cutRun.stdout || "").slice(-2000),
    ],
  };
  if (cut.status !== "ready") {
    await writeProgress("cut-failed", { cut });
    return { ok: false, phase: "cut", config: { ...config, worktreeCheckout, rootPaneId }, cut, stateDir };
  }
  await writeProgress("cut-complete", { cut });
}

// ---------------------------------------------------------------------------
// GATE
// ---------------------------------------------------------------------------
let gatePaneId = priorGate && priorGate.gatePaneId ? String(priorGate.gatePaneId) : null;
let gateWatchPaneId = null;
let gate = priorGate;

const gateOpenScript = `${stateDir}/scripts/run-gate-open.sh`;
const gateWatchScript = `${stateDir}/scripts/run-gate-watch.sh`;
const gateResultPath = `${stateDir}/gate.json`;

await writeText(
  gateOpenScript,
  [
    "#!/usr/bin/env bash",
    "set -euo pipefail",
    `cd ${JSON.stringify(worktreeCheckout)}`,
    "echo '=== Heddle release gate (interactive shell) ==='",
    "echo 'Enter your 1Password password when prompted.'",
    "npm run release:op:open-gate",
    "npm run release:op:verify-gate",
    "echo GATE_OPEN_OK",
    "",
  ].join("\n"),
);
await runOk(joinCmd(["chmod", "+x", gateOpenScript]));

// Watch script polls verify-gate and writes gate.json (no agent needed)
await writeText(
  gateWatchScript,
  [
    "#!/usr/bin/env bash",
    "set -euo pipefail",
    `WORKTREE=${JSON.stringify(worktreeCheckout)}`,
    `GATE_JSON=${JSON.stringify(gateResultPath)}`,
    `GATE_PANE=${JSON.stringify(gatePaneId || "")}`,
    "DEADLINE=$((SECONDS + 2700))",
    'while (( SECONDS < DEADLINE )); do',
    '  if [[ -s "$GATE_JSON" ]]; then',
    '    if python3 -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get(\'status\')==\'open\' else 1)" "$GATE_JSON" 2>/dev/null; then',
    '      echo "[gate-watch] gate.json already open"',
    "      exit 0",
    "    fi",
    "  fi",
    '  if (cd "$WORKTREE" && npm run release:op:verify-gate); then',
    '    python3 - "$GATE_JSON" "$GATE_PANE" <<\'PY\'',
    "import json,sys",
    "path,pane=sys.argv[1],sys.argv[2]",
    "open(path,'w').write(json.dumps({'status':'open','gatePaneId':pane or None,'verifiedBy':'gate-watch-script','evidence':['npm run release:op:verify-gate exit 0'],'blockers':[]},indent=2)+'\\n')",
    "PY",
    '    echo "[gate-watch] wrote $GATE_JSON"',
    "    exit 0",
    "  fi",
    "  sleep 5",
    "done",
    'echo "[gate-watch] timeout" >&2',
    "exit 2",
    "",
  ].join("\n"),
);
await runOk(joinCmd(["chmod", "+x", gateWatchScript]));

if (skipGate) {
  phase("open-gate-skipped");
  log("Skipping interactive open-gate; verifying existing gate.");
  const verifyExisting = await run(
    joinCmd(["bash", "-lc", `cd ${shellQuote(worktreeCheckout)} && npm run release:op:verify-gate`]),
    { timeoutMs: 120_000 },
  );
  if (verifyExisting.exitCode !== 0) {
    log("Existing gate verify failed; opening interactive gate.");
    skipGate = false;
  } else {
    gate = gate || {
      status: "open",
      gatePaneId: gatePaneId || "reused",
      verifiedBy: "resume-verify",
      evidence: ["npm run release:op:verify-gate exit 0"],
      blockers: [],
    };
    await writeText(gateResultPath, JSON.stringify(gate, null, 2));
    await writeProgress("gate-skipped", { gate });
  }
}

if (!skipGate) {
  phase("open-gate");
  log("Interactive gate pane + watch script (password TTY required).");
  gatePaneId = await splitPane(rootPaneId, "right", worktreeCheckout, { focus: true });
  gateWatchPaneId = await splitPane(rootPaneId, "down", worktreeCheckout, { focus: false });
  // rewrite watch script with real gate pane id
  await writeText(
    gateWatchScript,
    [
      "#!/usr/bin/env bash",
      "set -euo pipefail",
      `WORKTREE=${JSON.stringify(worktreeCheckout)}`,
      `GATE_JSON=${JSON.stringify(gateResultPath)}`,
      `GATE_PANE=${JSON.stringify(gatePaneId)}`,
      "DEADLINE=$((SECONDS + 2700))",
      "while (( SECONDS < DEADLINE )); do",
      '  if [[ -s "$GATE_JSON" ]] && python3 -c "import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d.get(\'status\')==\'open\' else 1)" "$GATE_JSON" 2>/dev/null; then exit 0; fi',
      '  if (cd "$WORKTREE" && npm run release:op:verify-gate); then',
      '    python3 - "$GATE_JSON" "$GATE_PANE" <<\'PY\'',
      "import json,sys",
      "path,pane=sys.argv[1],sys.argv[2]",
      "open(path,'w').write(json.dumps({'status':'open','gatePaneId':pane,'verifiedBy':'gate-watch-script','evidence':['npm run release:op:verify-gate exit 0'],'blockers':[]},indent=2)+'\\n')",
      "PY",
      "    exit 0",
      "  fi",
      "  sleep 5",
      "done",
      "exit 2",
      "",
    ].join("\n"),
  );
  await runOk(joinCmd(["chmod", "+x", gateWatchScript]));

  const gateTimeoutMs = 45 * 60 * 1000;
  const gateStage = await parallel("open-gate-stage", {
    interactiveOpen: async () => {
      const result = await paneRunScript(gatePaneId, gateOpenScript, { timeoutMs: gateTimeoutMs });
      return { paneId: gatePaneId, exitCode: result.exitCode, stdout: result.stdout, stderr: result.stderr };
    },
    watch: async () => {
      const result = await paneRunScript(gateWatchPaneId, gateWatchScript, { timeoutMs: gateTimeoutMs });
      return { paneId: gateWatchPaneId, exitCode: result.exitCode };
    },
    hostPoll: async () => {
      const ok = await waitForFile(gateResultPath, gateTimeoutMs, 5);
      // also accept verify success even if file race
      if (!ok) {
        const v = await run(
          joinCmd(["bash", "-lc", `cd ${shellQuote(worktreeCheckout)} && npm run release:op:verify-gate`]),
          { timeoutMs: 120_000 },
        );
        if (v.exitCode === 0) {
          gate = {
            status: "open",
            gatePaneId,
            verifiedBy: "host-poll",
            evidence: ["verify-gate exit 0"],
            blockers: [],
          };
          await writeText(gateResultPath, JSON.stringify(gate, null, 2));
          return { ok: true };
        }
        return { ok: false };
      }
      return { ok: true };
    },
  });

  gate = (await readJson(gateResultPath)) || null;
  if (!gate || gate.status !== "open") {
    const v = await run(
      joinCmd(["bash", "-lc", `cd ${shellQuote(worktreeCheckout)} && npm run release:op:verify-gate`]),
      { timeoutMs: 120_000 },
    );
    if (v.exitCode === 0) {
      gate = {
        status: "open",
        gatePaneId,
        verifiedBy: "final-verify",
        evidence: ["verify-gate exit 0"],
        blockers: [],
      };
      await writeText(gateResultPath, JSON.stringify(gate, null, 2));
    } else {
      gate = {
        status: "failed",
        gatePaneId,
        blockers: ["Release gate never verified open"],
        gateStage,
      };
      await writeProgress("gate-failed", { gate });
      return {
        ok: false,
        phase: "open-gate",
        config: { ...config, worktreeCheckout, rootPaneId, gatePaneId, gateWatchPaneId },
        cut,
        gate,
        stateDir,
      };
    }
  }
  await writeProgress("gate-open", { gate });
}

// ---------------------------------------------------------------------------
// BUILD
// ---------------------------------------------------------------------------
let build = priorBuild;
let buildPaneId = null;
let monitorPaneId = null;
const buildResultPath = `${stateDir}/build.json`;
const buildLogPath = `${stateDir}/build.log`;
const buildLockPath = `${stateDir}/build.lock`;
const buildScriptPath = `${stateDir}/scripts/run-signed-build.sh`;
const monitorScriptPath = `${stateDir}/scripts/run-build-monitor.sh`;
const buildTimeoutMs = 4 * 60 * 60 * 1000;

// Signed build script: state OUTSIDE worktree; fail-soft write build.json; clean tree check
const buildScriptBody = [
  "#!/usr/bin/env bash",
  "set -euo pipefail",
  `WORKTREE=${JSON.stringify(worktreeCheckout)}`,
  `STATE_DIR=${JSON.stringify(stateDir)}`,
  `BUILD_JSON=${JSON.stringify(buildResultPath)}`,
  `BUILD_LOG=${JSON.stringify(buildLogPath)}`,
  `BUILD_LOCK=${JSON.stringify(buildLockPath)}`,
  `RELEASE_VERSION=${JSON.stringify(releaseVersion)}`,
  `RELEASE_BRANCH=${JSON.stringify(releaseBranch)}`,
  'mkdir -p "$STATE_DIR"',
  'exec 9>"$BUILD_LOCK"',
  "if ! flock -n 9; then",
  '  echo "release_build_lock_held" | tee -a "$BUILD_LOG"',
  '  python3 - "$BUILD_JSON" "$RELEASE_VERSION" "$RELEASE_BRANCH" <<\'PY\'',
  "import json,sys",
  "path,rv,rb=sys.argv[1:4]",
  "open(path,'w').write(json.dumps({'status':'failed','releaseVersion':rv,'releaseBranch':rb,'pkgPath':'','blockers':['build.lock held']},indent=2)+'\\n')",
  "PY",
  "  exit 75",
  "fi",
  'write_fail() {',
  '  local msg="$1"',
  '  python3 - "$BUILD_JSON" "$RELEASE_VERSION" "$RELEASE_BRANCH" "$msg" "$BUILD_LOG" <<\'PY\'',
  "import json,sys",
  "from pathlib import Path",
  "path,rv,rb,msg,logp=sys.argv[1:6]",
  "tail=''",
  "p=Path(logp)",
  "if p.exists():",
  "  lines=p.read_text(errors='replace').splitlines()",
  "  tail='\\n'.join(lines[-40:])",
  "open(path,'w').write(json.dumps({'status':'failed','releaseVersion':rv,'releaseBranch':rb,'pkgPath':'','blockers':[msg], 'logTail':tail},indent=2)+'\\n')",
  "PY",
  "}",
  "trap 'rc=$?; if [[ $rc -ne 0 ]]; then write_fail \"run-signed-build exited $rc\"; fi; exit $rc' EXIT",
  'tmp_log="$(mktemp)"',
  "(",
  "  set -euo pipefail",
  '  cd "$WORKTREE"',
  '  echo "[build] $(date -u +%Y-%m-%dT%H:%M:%SZ) starting unique signed build"',
  '  echo "[build] branch=$(git branch --show-current) head=$(git rev-parse HEAD)"',
  "  # Ensure workflow state never dirties provenance",
  "  EXCL=$(git rev-parse --git-path info/exclude)",
  "  mkdir -p \"$(dirname \"$EXCL\")\"",
  "  grep -qx '.heddle-release/' \"$EXCL\" 2>/dev/null || echo '.heddle-release/' >> \"$EXCL\"",
  "  # Fail fast if tree still dirty (other than ignored paths)",
  "  if [[ -n \"$(git status --porcelain)\" ]]; then",
  "    echo '[build] worktree dirty:'",
  "    git status --short",
  "    echo 'heddle_source_tree_dirty: clean the release worktree (workflow state must live outside the repo)' >&2",
  "    exit 12",
  "  fi",
  "  npm run release:op:verify-gate",
  "  echo '[build] npm ci'",
  "  if [[ -f package-lock.json ]]; then npm ci; else npm install; fi",
  "  echo '[build] npm run release:signed (exactly once)'",
  "  npm run release:signed",
  "  echo '[build] locating artifacts'",
  '  python3 - "$BUILD_JSON" "$WORKTREE" "$RELEASE_VERSION" "$RELEASE_BRANCH" <<\'PY\'',
  "import json,sys",
  "from pathlib import Path",
  "path,root,version,branch=sys.argv[1:5]",
  "root=Path(root)",
  "release_dir=root/'artifacts'/'releases'/f'v{version}'",
  "pkgs=sorted(release_dir.glob('*.pkg')) if release_dir.exists() else []",
  "if not pkgs:",
  "  pkgs=sorted((root/'artifacts').rglob(f'*{version}*.pkg'))",
  "if not pkgs:",
  "  signed=root/'artifacts'/'signed'",
  "  if signed.exists(): pkgs=sorted(signed.glob('*.pkg'))",
  "pkg=str(pkgs[-1]) if pkgs else ''",
  "checksum=pkg+'.sha256' if pkg and Path(pkg+'.sha256').exists() else ''",
  "status='built' if pkg else 'failed'",
  "blockers=[] if pkg else ['signed build finished but no .pkg found under artifacts/']",
  "open(path,'w').write(json.dumps({'status':status,'releaseVersion':version,'releaseBranch':branch,'pkgPath':pkg,'checksumPath':checksum,'releaseDir':str(release_dir) if release_dir.exists() else '','evidence':['flocked shell build','npm ci','one release:signed',f'pkg={pkg}' if pkg else 'pkg missing'],'blockers':blockers},indent=2)+'\\n')",
  "print(open(path).read())",
  "raise SystemExit(0 if status=='built' else 1)",
  "PY",
  ') >"$tmp_log" 2>&1',
  "rc=$?",
  'tee -a "$BUILD_LOG" <"$tmp_log" >/dev/null || true',
  'cat "$tmp_log" || true',
  'rm -f "$tmp_log"',
  // disable EXIT trap success path double-write
  "trap - EXIT",
  'if [[ $rc -ne 0 && ! -s "$BUILD_JSON" ]]; then write_fail "run-signed-build exited $rc"; fi',
  'exit "$rc"',
  "",
].join("\n");
await writeText(buildScriptPath, buildScriptBody);
await runOk(joinCmd(["chmod", "+x", buildScriptPath]));

await writeText(
  monitorScriptPath,
  [
    "#!/usr/bin/env bash",
    "set -euo pipefail",
    `LOG=${JSON.stringify(buildLogPath)}`,
    `JSON=${JSON.stringify(buildResultPath)}`,
    'mkdir -p "$(dirname "$LOG")"',
    'touch "$LOG"',
    'tail -n 80 -F "$LOG" &',
    "tail_pid=$!",
    'while [[ ! -s "$JSON" ]]; do sleep 5; done',
    "kill $tail_pid 2>/dev/null || true",
    'echo "[monitor] build result present"',
    'sed -n "1,160p" "$JSON"',
    "",
  ].join("\n"),
);
await runOk(joinCmd(["chmod", "+x", monitorScriptPath]));

if (skipBuild) {
  phase("build-skipped");
  log(`Skipping build; pkg=${build && build.pkgPath}`);
  if (!build || build.status !== "built" || !build.pkgPath) {
    throw new Error(`skipBuild but build.json not ready in ${stateDir}`);
  }
  await writeProgress("build-skipped", { build });
} else {
  phase("build");
  log("Single flocked build shell + monitor (state outside git worktree).");
  buildPaneId = await splitPane(rootPaneId, "right", worktreeCheckout, { focus: false });
  monitorPaneId = await splitPane(rootPaneId, "down", worktreeCheckout, { focus: false });

  const buildStage = await parallel("build-stage", {
    buildShell: async () => {
      const result = await paneRunScript(buildPaneId, buildScriptPath, { timeoutMs: buildTimeoutMs });
      return { paneId: buildPaneId, exitCode: result.exitCode };
    },
    monitor: async () => {
      // fire-and-forget style: start monitor; host also waits for JSON
      await paneRunScript(monitorPaneId, monitorScriptPath, { timeoutMs: 15_000 }).catch(() => null);
      return { paneId: monitorPaneId };
    },
    heartbeat: async () => {
      // Poll until build.json exists; write lightweight heartbeat env for operators.
      const hb = `${stateDir}/scripts/run-build-heartbeat.sh`;
      const simpleHb = [
        "#!/usr/bin/env bash",
        "set -euo pipefail",
        `LOG=${JSON.stringify(buildLogPath)}`,
        `JSON=${JSON.stringify(buildResultPath)}`,
        `META=${JSON.stringify(`${stateDir}/build-heartbeat.env`)}`,
        "START=$SECONDS",
        "while true; do",
        '  if [[ -s "$JSON" ]]; then exit 0; fi',
        '  LINE=$(tail -n 1 "$LOG" 2>/dev/null || true)',
        '  {',
        '    echo "elapsedSec=$((SECONDS-START))"',
        '    echo "stage=building"',
        '    echo "lastLogLine=$LINE"',
        '  } > "$META"',
        "  sleep 30",
        "done",
        "",
      ].join("\n");
      await writeText(hb, simpleHb);
      await runOk(joinCmd(["chmod", "+x", hb]));
      const result = await run(joinCmd(["bash", hb]), { timeoutMs: buildTimeoutMs + 60_000 });
      return { exitCode: result.exitCode };
    },
  });

  build = (await readJson(buildResultPath)) || {
    status: "failed",
    blockers: [`build did not write ${buildResultPath}`, `stage=${JSON.stringify(buildStage)}`],
  };
  if (build.status !== "built") {
    await writeProgress("build-failed", { build });
    return {
      ok: false,
      phase: "build",
      config: { ...config, worktreeCheckout, rootPaneId, gatePaneId, buildPaneId, monitorPaneId },
      cut,
      gate,
      build,
      stateDir,
    };
  }
  priorBuild = build;
  await writeProgress("build-complete", { build });
}

// ---------------------------------------------------------------------------
// PUBLISH
// ---------------------------------------------------------------------------
phase("publish");
log("Publish agent pane (operator choice if publishTarget unset).");

const publishResultPath = `${stateDir}/publish.json`;
const publishPromptPath = `${stateDir}/prompts/publish.md`;
const publishTargetLine = publishTarget
  ? `Use publishTarget=${publishTarget} without asking.`
  : "ASK the operator in this pane to choose exactly one: none | github | github-sparkle. Wait for their answer.";

await writeText(
  publishPromptPath,
  `# Heddle publish + Slack

You are the visible publish agent.

## Config
- worktree: ${worktreeCheckout}
- stateDir: ${stateDir}
- releaseVersion: ${releaseVersion}
- releaseBranch: ${releaseBranch}
- githubRepo: ${githubRepo}
- pkgPath: ${build.pkgPath}
- slackChannel: ${slackChannel}
- slackWorkspace: ${slackWorkspace}
- result file: ${publishResultPath}

## Publish decision
${publishTargetLine}

## Execute
1. none: do not create a GitHub release; do not Sparkle-publish.
2. github: publish signed installer + checksum + ccore Homebrew bundle to GitHub Releases tag v${releaseVersion} on ${githubRepo}. Follow docs/V1_DISTRIBUTION_SECURITY.md steps 5-8.
3. github-sparkle: github steps, then staging+prod via npm run release:updates:publish and live smoke (docs step 9).

## Slack
If publishTargetUsed is github or github-sparkle:
- Full changelog for v${releaseVersion}
- agent-slack message send --workspace ${slackWorkspace} "${slackChannel}" "<text>"

## Gate cleanup
When finished: npm run release:op:close-gate -- --confirm (if appropriate)

## Result
Write ${publishResultPath} JSON with status completed|built_not_published|blocked|failed, publishTargetUsed, githubReleaseUrl, sparklePublished, slack, evidence, blockers.
`,
);

const publishPaneId = await splitPane(rootPaneId, "right", worktreeCheckout, { focus: true });
const publishAgentName = `heddle-rel-publish-v${releaseVersion.replace(/\./g, "-")}`;
await startAgent(publishAgentName, publishPaneId);
const publishPromptRes = await promptAgent(
  publishAgentName,
  `Read and execute ${publishPromptPath}. Write ${publishResultPath} when done.`,
  2 * 60 * 60 * 1000,
);
const publish = (await readJson(publishResultPath)) || {
  status: "failed",
  publishTargetUsed: "unknown",
  blockers: [
    `publish agent did not write ${publishResultPath}`,
    `exit=${publishPromptRes.exitCode}`,
    await readAgentTail(publishAgentName, 80),
  ],
};

const ok = publish.status === "completed" || publish.status === "built_not_published";
await writeProgress(ok ? "publish-complete" : "publish-failed", { publish, cut, gate, build });

return {
  ok,
  dryRun: false,
  config: {
    ...config,
    worktreeCheckout,
    workspaceId,
    tabId,
    rootPaneId,
    panes: {
      root: rootPaneId,
      gate: gatePaneId,
      gateWatch: gateWatchPaneId,
      build: buildPaneId,
      monitor: monitorPaneId,
      publish: publishPaneId,
    },
  },
  cut,
  gate,
  build,
  publish,
  stateDir,
};
