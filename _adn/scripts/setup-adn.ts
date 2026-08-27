import { spawnSync } from "node:child_process";
import { cpSync, existsSync, lstatSync, mkdirSync, readFileSync, readdirSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { ADN_ROOT, OWNED_ROLES, atomicWrite, fileSha, flag, parseArgs, sha256, withDirLock } from "./lib.ts";
import { ADN_ROLES, applyRoleMerge, resolveProfile } from "./config-state.ts";

const SKILLS = join(ADN_ROOT, "skills");
const AGENTS = join(ADN_ROOT, "agents");
const EXT = join(ADN_ROOT, "extensions", "adn-mode.ts");

function resultPath(flags: Record<string, string | boolean>, id: string, root: string) {
  return flag(flags, "result") ?? join(root, "adn", "transactions", `${id}.result.json`);
}

function journalPath(root: string, id: string) {
  return join(root, "adn", "transactions", `${id}.json`);
}

function ownedTargets(root: string) {
  const live = !process.argv.includes("--agent-root");
  const skillRoot = live ? join(process.env.HOME ?? "", ".agents", "skills") : join(root, "skills");
  const skillLinks = existsSync(SKILLS)
    ? readdirSync(SKILLS).map((name) => ({
        kind: "skill",
        src: join(SKILLS, name),
        dest: join(skillRoot, name),
      }))
    : [];
  return [
    { kind: "generation", src: EXT, dest: join(root, "adn", "generation.json") },
    { kind: "wrapper", src: EXT, dest: join(root, "extensions", "adn-mode.ts") },
    { kind: "wrapper", src: EXT, dest: join(root, "extensions", "adn-mode.generated.ts") },
    ...readdirSync(AGENTS).map((name) => ({
      kind: "agent",
      src: join(AGENTS, name),
      dest: join(root, "agents", name),
    })),
    ...skillLinks,
  ];
}

function fingerprint(path: string): string | null {
  if (!existsSync(path)) return null;
  if (lstatSync(path).isSymbolicLink()) return `link:${path}`;
  return fileSha(path);
}

function applyTargets(root: string) {
  const targets = ownedTargets(root);
  const records = [];
  for (const t of targets) {
    const pre = fingerprint(t.dest);
    mkdirSync(dirname(t.dest), { recursive: true });
    if (t.kind === "skill") {
      if (existsSync(t.dest)) {
        records.push({ ...t, pre, post: pre, skipped: "exists" });
        continue;
      }
      symlinkSync(t.src, t.dest);
    } else if (t.kind === "generation") {
      atomicWrite(t.dest, JSON.stringify({ generation: 1, root, pin: "46756f89270d7e7dcb8c28c90fd0f957ade4ce2c" }, null, 2) + "\n");
    } else if (t.kind === "wrapper") {
      atomicWrite(
        t.dest,
        `import { attach } from ${JSON.stringify(EXT)};\nimport generation from "../adn/generation.json" with { type: "json" };\nexport default function (pi) { attach(pi, generation); }\nexport * from ${JSON.stringify(EXT)};\n`,
      );
    } else {
      cpSync(t.src, t.dest);
    }
    records.push({ ...t, pre, post: fingerprint(t.dest) });
  }
  const isolated = process.argv.includes("--agent-root");
  const roles = applyRoleMerge(isolated ? { agentRoot: root } : {});
  return { targets: records, roles: roles.roles };
}

function checkTargets(root: string) {
  const drift = [];
  for (const t of ownedTargets(root)) {
    if (!existsSync(t.dest) && !("skipped" in t)) drift.push({ target: t.dest, reason: "missing" });
  }
  const isolated = process.argv.includes("--agent-root");
  const store = join(root, "modelRoles.json");
  let roles: Record<string, string> = {};
  if (isolated && existsSync(store)) {
    roles = JSON.parse(readFileSync(store, "utf8"));
  } else if (!isolated) {
    const got = spawnSync("omp", ["config", "get", "modelRoles", "--json"], { encoding: "utf8" });
    if (got.status !== 0) {
      drift.push({ target: "modelRoles", reason: "missing" });
      return drift;
    }
    roles = JSON.parse(got.stdout).value ?? {};
  } else if (!flagProcessExpect()) {
    drift.push({ target: "modelRoles.json", reason: "missing" });
    return drift;
  }
  for (const key of OWNED_ROLES) {
    if (roles[key] !== ADN_ROLES[key]) drift.push({ target: `role:${key}`, reason: "owned-role-drift" });
  }
  return drift;
}

function flagProcessExpect() {
  return process.argv.includes("--expect-owned-role-drift");
}

function rollback(root: string, tx: string) {
  const journal = JSON.parse(readFileSync(journalPath(root, tx), "utf8"));
  for (const t of journal.targets) {
    const now = fingerprint(t.dest);
    if (now !== t.post) throw new Error(`fail-closed: drift ${t.dest}`);
    if (t.pre == null) rmSync(t.dest, { recursive: true, force: true });
    else if (String(t.pre).startsWith("link:")) {
      rmSync(t.dest, { recursive: true, force: true });
      symlinkSync(t.src, t.dest);
    } else {
      cpSync(t.src, t.dest);
    }
  }
  if (journal.priorRoles) {
    atomicWrite(join(root, "modelRoles.json"), JSON.stringify(journal.priorRoles, null, 2) + "\n");
  }
}

const { cmd, flags } = parseArgs();
const agentRoot = flag(flags, "agent-root");
const profile = flag(flags, "profile") ?? process.env.OMP_PROFILE;
if (agentRoot && profile && process.env.OMP_PROFILE && cmd === "apply") {
  // --agent-root wins for tests and clears profile env by contract
  delete process.env.OMP_PROFILE;
  delete process.env.PI_PROFILE;
  process.env.PI_CODING_AGENT_DIR = agentRoot;
}
const root = agentRoot ?? resolveProfile({ env: { ...process.env, PI_CONFIG_FILES: undefined } });
if (agentRoot) process.env.PI_CODING_AGENT_DIR = agentRoot;

const out = withDirLock(root, () => {
  if (cmd === "apply") {
    const id = crypto.randomUUID();
    const priorRoles = existsSync(join(root, "modelRoles.json"))
      ? JSON.parse(readFileSync(join(root, "modelRoles.json"), "utf8"))
      : {};
    const applied = applyTargets(root);
    const journal = {
      schemaVersion: 1,
      transactionId: id,
      utc: new Date().toISOString(),
      profile: root,
      priorRoles,
      ...applied,
    };
    atomicWrite(journalPath(root, id), JSON.stringify(journal, null, 2) + "\n");
    const result = { transactionId: id, profile: root, ok: true };
    atomicWrite(resultPath(flags, id, root), JSON.stringify(result) + "\n");
    return result;
  }
  if (cmd === "check") {
    const drift = checkTargets(root);
    if (process.argv.includes("--expect-owned-role-drift")) {
      if (!drift.some((d) => d.reason === "owned-role-drift")) throw new Error("expected owned-role-drift");
      return { ok: true, drift };
    }
    if (drift.length) throw new Error(`fail-closed: ${JSON.stringify(drift)}`);
    return { ok: true, drift: [] };
  }
  if (cmd === "rollback") {
    const tx = flag(flags, "transaction");
    if (!tx) throw new Error("fail-closed: --transaction required");
    const journal = JSON.parse(readFileSync(journalPath(root, tx), "utf8"));
    const comparisons = (journal.targets ?? []).map((t: { dest: string; post: string | null }) => ({
      dest: t.dest,
      recordedPost: t.post,
      current: fingerprint(t.dest),
      matches: fingerprint(t.dest) === t.post,
    }));
    if (flags["dry-run"]) return { ok: true, dryRun: true, transactionId: tx, comparisons };
    rollback(root, tx);
    return { ok: true, transactionId: tx, comparisons };
  }
  throw new Error(`fail-closed: unknown command ${cmd}`);
});
console.log(JSON.stringify(out));
