#!/usr/bin/env node
// Publishes a built clickable demo to https://<run-name>.demos.keramos.tech on
// the Nodaste Labs account, behind the existing demos Cloudflare Access
// application, and proves it: the certificate serves, an anonymous request is
// refused, and the demos service token (via demo-access.mjs) gets 200.
//
//   publish-demo.mjs <run-name> <built-dir> [--worker <_worker.js>] [--migrations <dir>]
//                    [--static] [--run-dir <dir>] [--timeout <seconds>]
//
// <built-dir> is the Vite build output of the demo template (thoughts/prototypes/web-ui-v1/dist).
// The feedback Worker and D1 migrations default to ../worker next to it. --static
// publishes assets only, with no Worker and no feedback database.
// Re-running with an existing name updates that demo in place.
// Never touches product deployables, the Access policy or the service token.
import { execFileSync, spawnSync } from "node:child_process";
import { Resolver } from "node:dns/promises";
import { cpSync, existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, statSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { parseArgs } from "node:util";
import { demoAccessCookies } from "./demo-access.mjs";

const ACCOUNT_ID = "e6d3e575b97001f8ad1a7e98e497afa5";
const DEMO_DOMAIN = "demos.keramos.tech";
// The one Access application that covers every demo host. Both values are public:
// the team domain is a URL and the audience tag is inside every Access JWT.
const ACCESS_TEAM_DOMAIN = "nodaste-labs.cloudflareaccess.com";
const ACCESS_AUD = "0cdd131e57e771b0767fe6521e96a210b4d013a7e6429a0dac6d3fb5ce7bbf3c";
const RUN_NAME = /^[a-z0-9][a-z0-9-]{2,62}$/;
const COMPATIBILITY_DATE = "2026-10-12";

function fail(message) {
  console.error(`publish-demo: ${message}`);
  process.exit(1);
}

function run(command, args, options = {}) {
  try {
    return execFileSync(command, args, { encoding: "utf8", stdio: ["ignore", "pipe", "pipe"], ...options });
  } catch (error) {
    const detail = `${error.stdout ?? ""}${error.stderr ?? ""}`.trim();
    throw new Error(`${command} ${args.join(" ")} failed:\n${detail || error.message}`);
  }
}

// mbp has wrangler on PATH; dever runs it through npx.
const hasWrangler = spawnSync("wrangler", ["--version"], { stdio: "ignore" }).status === 0;
const wrangler = (args, options = {}) => {
  const [command, ...prefix] = hasWrangler ? ["wrangler"] : ["npx", "--yes", "wrangler@4"];
  return run(command, [...prefix, ...args], { ...options, env: { ...process.env, CLOUDFLARE_ACCOUNT_ID: ACCOUNT_ID, ...options.env } });
};

function parseCli() {
  const { values, positionals } = parseArgs({
    allowPositionals: true,
    options: {
      worker: { type: "string" },
      migrations: { type: "string" },
      static: { type: "boolean", default: false },
      "run-dir": { type: "string" },
      timeout: { type: "string", default: "900" },
    },
  });
  const [runName, builtDir] = positionals;
  if (positionals.length !== 2) {
    fail("usage: publish-demo.mjs <run-name> <built-dir> [--worker <_worker.js>] [--migrations <dir>] [--static] [--run-dir <dir>] [--timeout <seconds>]");
  }
  if (!RUN_NAME.test(runName)) fail(`run name ${JSON.stringify(runName)} must match ${RUN_NAME} (lowercase letters, digits, hyphens).`);
  const built = resolve(builtDir);
  if (!existsSync(join(built, "index.html"))) fail(`${built} has no index.html; pass the built demo directory.`);
  const timeout = Number(values.timeout);
  if (!Number.isFinite(timeout) || timeout <= 0) fail("--timeout must be a positive number of seconds.");

  let worker = null;
  let migrations = null;
  if (!values.static) {
    worker = resolve(values.worker ?? join(built, "..", "worker", "_worker.js"));
    migrations = resolve(values.migrations ?? join(dirname(worker), "migrations"));
    if (!existsSync(worker)) fail(`Worker ${worker} not found. Pass --worker, or --static for an assets-only demo.`);
    if (!existsSync(migrations) || !statSync(migrations).isDirectory()) fail(`Migrations directory ${migrations} not found. Pass --migrations.`);
  }
  return { runName, built, worker, migrations, runDir: resolve(values["run-dir"] ?? join("artifacts", "verified-build", runName)), timeoutMs: timeout * 1000 };
}

function ensureLabsAccount() {
  const output = wrangler(["whoami"]);
  if (!output.includes(ACCOUNT_ID)) fail(`wrangler is not logged in to the Nodaste Labs account ${ACCOUNT_ID}. Run \`wrangler login\` with an account that has it.`);
}

function readManifest(runDir) {
  const path = join(runDir, "demos.json");
  return existsSync(path) ? JSON.parse(readFileSync(path, "utf8")).demos ?? [] : [];
}

function workerExists(name) {
  try {
    wrangler(["deployments", "list", "--name", name]);
    return true;
  } catch (error) {
    if (error.message.includes("10007")) return false;
    throw error;
  }
}

function lookupDatabaseId(name) {
  try {
    return JSON.parse(wrangler(["d1", "info", name, "--json"])).uuid;
  } catch (error) {
    if (error.message.includes("Couldn't find DB")) return null;
    throw error;
  }
}

// A name is ours only if this worktree and branch recorded it. Anything else that already holds the
// Worker or database name belongs to another demo or deployable, so stop before any migration or deploy.
function assertNameIsOurs(runDir, runName, databaseName, owner) {
  const recorded = readManifest(runDir).find((demo) => demo.run === runName && demo.worktree === owner.worktree && demo.branch === owner.branch);
  if (recorded) return;
  const taken = [workerExists(runName) && `Worker ${runName}`, databaseName && lookupDatabaseId(databaseName) && `D1 database ${databaseName}`].filter(Boolean);
  if (taken.length > 0) {
    fail(`${taken.join(" and ")} already exist on the Labs account and this worktree has no demos.json entry for ${runName}. Choose a new run name; reuse a name only from the worktree and branch that published it.`);
  }
}

function ensureDatabase(name) {
  const existing = lookupDatabaseId(name);
  if (existing) return existing;
  wrangler(["d1", "create", name]);
  return lookupDatabaseId(name);
}

function stage({ runName, built, worker, migrations, runDir }, databaseId) {
  const stageDir = join(runDir, "publish");
  rmSync(stageDir, { recursive: true, force: true });
  mkdirSync(stageDir, { recursive: true });
  cpSync(built, join(stageDir, "site"), { recursive: true });
  const host = `${runName}.${DEMO_DOMAIN}`;
  const config = {
    name: runName,
    compatibility_date: COMPATIBILITY_DATE,
    account_id: ACCOUNT_ID,
    workers_dev: false,
    preview_urls: false,
    routes: [{ pattern: host, custom_domain: true }],
  };
  if (worker) {
    cpSync(worker, join(stageDir, "_worker.js"));
    config.main = "_worker.js";
    config.assets = { directory: "site", binding: "ASSETS", run_worker_first: true };
    config.d1_databases = [{ binding: "FEEDBACK_DB", database_name: `${runName}-feedback`, database_id: databaseId, migrations_dir: migrations }];
    config.vars = { DEMO_HOST: host, DEMO_ID: runName, ACCESS_TEAM_DOMAIN, ACCESS_AUD };
  } else {
    config.assets = { directory: "site" };
  }
  const configPath = join(stageDir, "wrangler.jsonc");
  writeFileSync(configPath, `${JSON.stringify(config, null, 2)}\n`);
  return { stageDir, configPath, host };
}

function deploy(configPath, stageDir) {
  const outputDir = mkdtempSync(join(tmpdir(), "publish-demo-"));
  const outputFile = join(outputDir, "wrangler-output.ndjson");
  try {
    wrangler(["deploy", "-c", configPath], { cwd: stageDir, env: { WRANGLER_OUTPUT_FILE_PATH: outputFile } });
    const entries = readFileSync(outputFile, "utf8").split("\n").filter(Boolean).map((line) => JSON.parse(line));
    const version = entries.filter((entry) => entry.type === "deploy").map((entry) => entry.version_id).findLast(Boolean);
    if (!version) throw new Error("wrangler deploy reported no version id.");
    return version;
  } finally {
    rmSync(outputDir, { recursive: true, force: true });
  }
}

const sleep = (ms) => new Promise((done) => setTimeout(done, ms));

// Probing before the record exists makes the system resolver cache NXDOMAIN for a while
// (negative caching). Ask a public resolver until the record shows up, and only then touch the system one.
async function waitForDns(host, deadline) {
  const resolver = new Resolver();
  resolver.setServers(["1.1.1.1", "8.8.8.8"]);
  for (;;) {
    if ((await resolver.resolve4(host).catch(() => [])).length > 0) return;
    if (Date.now() > deadline) throw new Error(`${host} has no DNS record after the deadline.`);
    console.error(`waiting for DNS record of ${host}`);
    await sleep(5000);
  }
}

// Anonymous requests must hit the Access login wall, never the demo itself.
async function anonymousIsRefused(url) {
  const response = await fetch(url, { redirect: "manual" });
  const location = response.headers.get("location") ?? "";
  const refused = response.status === 401 || response.status === 403 || (response.status >= 300 && response.status < 400 && location.includes("cloudflareaccess.com"));
  return { refused, status: response.status };
}

// The custom-domain certificate takes about 5 minutes; until then fetch fails or Access answers non-200.
async function waitUntilServing(url, timeoutMs) {
  const deadline = Date.now() + timeoutMs;
  await waitForDns(new URL(url).hostname, deadline);
  let last = "no response";
  for (;;) {
    try {
      const [cookie] = await demoAccessCookies(url);
      const response = await fetch(url, { redirect: "manual", headers: { Cookie: `${cookie.name}=${cookie.value}` } });
      if (response.status === 200) return;
      last = `HTTP ${response.status}`;
    } catch (error) {
      last = error.cause?.code ?? error.message;
    }
    if (Date.now() > deadline) throw new Error(`${url} did not serve 200 to the service token within ${timeoutMs / 1000}s (last: ${last}).`);
    console.error(`waiting for ${url}: ${last}`);
    await sleep(15000);
  }
}

function recordManifest(runDir, entry) {
  const path = join(runDir, "demos.json");
  const demos = existsSync(path) ? JSON.parse(readFileSync(path, "utf8")).demos ?? [] : [];
  writeFileSync(path, `${JSON.stringify({ demos: [...demos.filter((demo) => demo.run !== entry.run), entry] })}\n`);
}

async function main() {
  const options = parseCli();
  const { runName, runDir } = options;
  ensureLabsAccount();
  mkdirSync(runDir, { recursive: true });

  const git = (...args) => run("git", args).trim();
  const owner = { worktree: git("rev-parse", "--show-toplevel"), branch: git("rev-parse", "--abbrev-ref", "HEAD") };
  const databaseName = options.worker ? `${runName}-feedback` : null;
  assertNameIsOurs(runDir, runName, databaseName, owner);
  const url = `https://${runName}.${DEMO_DOMAIN}`;
  // Recorded before anything is created, so a run that dies midway is still cleaned up and re-runnable.
  recordManifest(runDir, { run: runName, worker: runName, d1: databaseName, account: ACCOUNT_ID, url, ...owner });

  const databaseId = databaseName ? ensureDatabase(databaseName) : null;
  const { stageDir, configPath } = stage(options, databaseId);
  if (databaseName) wrangler(["d1", "migrations", "apply", "FEEDBACK_DB", "--remote", "-c", configPath], { cwd: stageDir });
  const version = deploy(configPath, stageDir);

  await waitUntilServing(url, options.timeoutMs);
  const anonymous = await anonymousIsRefused(url);
  if (!anonymous.refused) throw new Error(`${url} answered an anonymous request with HTTP ${anonymous.status}; the demo is not behind Access. Do not share it.`);

  console.log(`URL: ${url}`);
  console.log(`Deployment version: ${version}`);
  console.log(`Account: ${ACCOUNT_ID}`);
  console.log(`D1 database: ${options.worker ? `${runName}-feedback (${databaseId})` : "none (static)"}`);
  console.log(`Service token check: 200`);
  console.log(`Anonymous request: refused (HTTP ${anonymous.status})`);
  console.log(`Manifest: ${join(runDir, "demos.json")}`);
}

main().catch((error) => fail(error.message));
