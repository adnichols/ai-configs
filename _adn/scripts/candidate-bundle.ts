import { mkdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { ADN_ROOT, atomicWrite, flag, parseArgs, sha256 } from "./lib.ts";
import { resolveProfile } from "./config-state.ts";

type Candidate = {
  id: string;
  category: string;
  source: string;
  commit: string;
  parent: string;
  intent: string;
  plan?: string;
};

const { cmd, flags } = parseArgs();
if (cmd !== "register") throw new Error("fail-closed: register required");
const manifestPath = flag(flags, "manifest");
if (!manifestPath) throw new Error("fail-closed: --manifest required");
const agentRoot = flag(flags, "agent-root") ?? resolveProfile();
const repo = "/Users/anichols/code/ai-configs";
const manifest = JSON.parse(readFileSync(manifestPath, "utf8")) as { candidates: Candidate[] };
const ledger: unknown[] = [];

for (const c of manifest.candidates) {
  const diff = spawnSync("git", ["diff", "--binary", "--full-index", c.parent, c.commit], {
    cwd: repo,
    encoding: "utf8",
    maxBuffer: 20_000_000,
  });
  if (diff.status !== 0) throw new Error(`fail-closed: diff ${c.id} ${diff.stderr}`);
  const planBytes = c.plan ? spawnSync("git", ["show", `${c.commit}:${c.plan}`], { cwd: repo, encoding: "utf8" }).stdout ?? "" : "";
  const packet = {
    id: c.id,
    category: c.category,
    source: c.source,
    intent: c.intent,
    scope: c.plan ?? "diff",
    base: c.parent,
    commit: c.commit,
    verification: "git diff replay",
    planBytesHash: planBytes ? sha256(planBytes) : null,
  };
  const diff_fingerprint = sha256(diff.stdout);
  const packet_fingerprint = sha256(JSON.stringify(packet) + diff_fingerprint);
  const privateDir = join(agentRoot, "adn", "evaluations", "private", c.id);
  mkdirSync(privateDir, { recursive: true, mode: 0o700 });
  atomicWrite(join(privateDir, "diff.patch"), diff.stdout);
  atomicWrite(join(privateDir, "packet.json"), JSON.stringify(packet, null, 2) + "\n");
  ledger.push({
    id: c.id,
    category: c.category,
    source: c.source,
    state: "registered",
    diff_fingerprint,
    packet_fingerprint,
  });
}

const ledgerPath = join(agentRoot, "adn", "evaluations", "ledger.json");
atomicWrite(ledgerPath, JSON.stringify({ schemaVersion: 1, entries: ledger }, null, 2) + "\n");
console.log(JSON.stringify({ ok: true, count: ledger.length, ledger: ledgerPath }));
