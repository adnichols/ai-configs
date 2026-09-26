import { cpSync, existsSync, lstatSync, mkdirSync, readFileSync, readdirSync, rmSync, symlinkSync } from "node:fs";
import { dirname, join } from "node:path";
import { ADN_ROOT, agentRoles, atomicWrite, fileSha, flag, parseArgs, withDirLock } from "./lib.ts";
import { readRoles, resolveProfile } from "./config-state.ts";

const SKILLS = join(ADN_ROOT, "skills");
const AGENTS = join(ADN_ROOT, "agents");
const RETIRED = ["extensions/adn-mode.ts", "extensions/adn-mode.generated.ts", "adn/generation.json"];
const RETIRED_SKILLS = ["adn-audit"];

function skillRootFor(root: string) {
  const live = !process.argv.includes("--agent-root");
  return live ? join(process.env.HOME ?? "", ".agents", "skills") : join(root, "skills");
}

function resultPath(flags: Record<string, string | boolean>, id: string, root: string) {
  return flag(flags, "result") ?? join(root, "adn", "transactions", `${id}.result.json`);
}

function journalPath(root: string, id: string) {
  return join(root, "adn", "transactions", `${id}.json`);
}

function present(path: string) {
  try {
    lstatSync(path);
    return true;
  } catch {
    return false;
  }
}

function ownedTargets(root: string) {
  const skillRoot = skillRootFor(root);
  const skillLinks = existsSync(SKILLS)
    ? readdirSync(SKILLS)
        .filter((name) => existsSync(join(SKILLS, name, "SKILL.md")))
        .map((name) => ({
          kind: "skill",
          src: join(SKILLS, name),
          dest: join(skillRoot, name),
        }))
    : [];
  return [
    ...readdirSync(AGENTS).map((name) => ({
      kind: "agent",
      src: join(AGENTS, name),
      dest: join(root, "agents", name),
    })),
    ...skillLinks,
  ];
}

function fingerprint(path: string): string | null {
  if (!present(path)) return null;
  if (lstatSync(path).isSymbolicLink()) return `link:${path}`;
  return fileSha(path);
}

function retireLeftovers(root: string) {
  const records = [];
  const retired = [...RETIRED.map((rel) => join(root, rel)), ...RETIRED_SKILLS.map((name) => join(skillRootFor(root), name))];
  for (const dest of retired) {
    if (!present(dest)) continue;
    const pre = fingerprint(dest);
    rmSync(dest, { recursive: true, force: true });
    records.push({ kind: "retire", src: dest, dest, pre, post: null });
  }
  return records;
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
    } else {
      cpSync(t.src, t.dest);
    }
    records.push({ ...t, pre, post: fingerprint(t.dest) });
  }
  records.push(...retireLeftovers(root));
  return { targets: records };
}

// ADN agents name OMP roles. Every named role must be defined; ADN never chooses its model.
function undefinedRoles(root: string) {
  const isolated = process.argv.includes("--agent-root");
  const roles = readRoles(isolated ? { agentRoot: root } : {});
  if (roles === null) return [];
  return agentRoles(AGENTS)
    .filter((role) => !roles[role])
    .map((role) => ({ target: `role:${role}`, reason: "undefined-role" }));
}

function checkTargets(root: string) {
  const drift = [];
  for (const t of ownedTargets(root)) {
    if (!existsSync(t.dest) && !("skipped" in t)) drift.push({ target: t.dest, reason: "missing" });
  }
  for (const dest of [...RETIRED.map((rel) => join(root, rel)), ...RETIRED_SKILLS.map((name) => join(skillRootFor(root), name))]) {
    if (present(dest)) drift.push({ target: dest, reason: "retired" });
  }
  drift.push(...undefinedRoles(root));
  return drift;
}

function rollback(root: string, tx: string) {
  const journal = JSON.parse(readFileSync(journalPath(root, tx), "utf8"));
  for (const t of journal.targets) {
    if (t.kind === "retire") continue;
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
    const missingRoles = undefinedRoles(root);
    if (missingRoles.length) throw new Error(`fail-closed: ${JSON.stringify(missingRoles)}`);
    const id = crypto.randomUUID();
    const applied = applyTargets(root);
    const journal = {
      schemaVersion: 1,
      transactionId: id,
      utc: new Date().toISOString(),
      profile: root,
      ...applied,
    };
    atomicWrite(journalPath(root, id), JSON.stringify(journal, null, 2) + "\n");
    const result = { transactionId: id, profile: root, ok: true };
    atomicWrite(resultPath(flags, id, root), JSON.stringify(result) + "\n");
    return result;
  }
  if (cmd === "check") {
    const drift = checkTargets(root);
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
