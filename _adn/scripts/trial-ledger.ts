import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { ADN_ROOT, atomicWrite, flag, parseArgs } from "./lib.ts";
import { resolveProfile } from "./config-state.ts";

type Entry = {
  id: string;
  category: string;
  source: string;
  state: string;
  diff_fingerprint: string;
  packet_fingerprint: string;
  currentHash?: string;
  adnHash?: string;
  contextCurrent?: string;
  contextAdn?: string;
};

function load(root: string) {
  const path = join(root, "adn", "evaluations", "ledger.json");
  if (!existsSync(path)) throw new Error("fail-closed: missing ledger");
  return { path, data: JSON.parse(readFileSync(path, "utf8")) as { entries: Entry[] } };
}

function nextStage(e: Entry): string | null {
  if (e.state === "registered") return "current";
  if (e.state === "current_complete") return "adn";
  if (e.state === "adn_complete") return "adjudicate";
  if (e.state === "adjudicated") return "valid";
  return null;
}

const { cmd, flags } = parseArgs();
const root = flag(flags, "agent-root") ?? resolveProfile();
const { path, data } = load(root);

if (cmd === "validate") {
  const requireState = flag(flags, "require-state");
  const count = Number(flag(flags, "count") ?? data.entries.length);
  if (data.entries.length !== count) throw new Error(`fail-closed: count ${data.entries.length}`);
  const dist = Object.fromEntries(
    String(flag(flags, "distribution") ?? "")
      .split(",")
      .filter(Boolean)
      .map((p) => p.split("=")),
  );
  if (Object.keys(dist).length) {
    const got: Record<string, number> = {};
    for (const e of data.entries) got[e.category] = (got[e.category] ?? 0) + 1;
    for (const [k, v] of Object.entries(dist)) {
      if (String(got[k] ?? 0) !== v) throw new Error(`fail-closed: distribution ${k}`);
    }
  }
  if (requireState && data.entries.some((e) => e.state !== requireState)) {
    throw new Error("fail-closed: state");
  }
  console.log(JSON.stringify({ ok: true, count: data.entries.length }));
  process.exit(0);
}

if (cmd === "next") {
  const e = data.entries.find((row) => row.state !== "valid");
  if (!e) {
    console.log("true");
    process.exit(0);
  }
  const stage = nextStage(e);
  if (!stage) throw new Error(`fail-closed: stuck ${e.id}`);
  if (stage === "adjudicate") {
    console.log(`bun ${join(ADN_ROOT, "scripts/adjudicate-pair.ts")} --id ${e.id} --agent-root ${root}`);
  } else if (stage === "valid") {
    console.log(`bun ${join(ADN_ROOT, "scripts/trial-ledger.ts")} mark-valid --id ${e.id} --agent-root ${root}`);
  } else {
    console.log(`bun ${join(ADN_ROOT, "scripts/run-review-arm.ts")} run --id ${e.id} --arm ${stage} --agent-root ${root}`);
  }
  process.exit(0);
}

if (cmd === "advance") {
  const id = flag(flags, "id");
  const state = flag(flags, "state");
  const entry = data.entries.find((e) => e.id === id);
  if (!entry || !state) throw new Error("fail-closed: advance");
  entry.state = state;
  if (flag(flags, "hash")) {
    if (state === "current_complete") entry.currentHash = flag(flags, "hash");
    if (state === "adn_complete") entry.adnHash = flag(flags, "hash");
  }
  if (flag(flags, "context")) {
    if (entry.currentHash && !entry.adnHash) entry.contextCurrent = flag(flags, "context");
    else entry.contextAdn = flag(flags, "context");
  }
  atomicWrite(path, JSON.stringify(data, null, 2) + "\n");
  console.log(JSON.stringify({ ok: true, id, state }));
  process.exit(0);
}

if (cmd === "mark-valid") {
  const id = flag(flags, "id");
  const entry = data.entries.find((e) => e.id === id);
  if (!entry) throw new Error("fail-closed: missing");
  entry.state = "valid";
  atomicWrite(path, JSON.stringify(data, null, 2) + "\n");
  console.log(JSON.stringify({ ok: true, id, state: "valid" }));
  process.exit(0);
}

if (cmd === "run-all") {
  for (;;) {
    const current = load(root);
    if (current.data.entries.every((e) => e.state === "valid")) {
      console.log(JSON.stringify({ ok: true, count: current.data.entries.length }));
      process.exit(0);
    }
    const e = current.data.entries.find((row) => row.state !== "valid");
    if (!e) throw new Error("fail-closed: no next");
    const stage = nextStage(e);
    if (!stage) throw new Error(`fail-closed: stuck ${e.id} ${e.state}`);
    const args =
      stage === "adjudicate"
        ? [join(ADN_ROOT, "scripts/adjudicate-pair.ts"), "--id", e.id, "--agent-root", root]
        : stage === "valid"
          ? [join(ADN_ROOT, "scripts/trial-ledger.ts"), "mark-valid", "--id", e.id, "--agent-root", root]
          : [join(ADN_ROOT, "scripts/run-review-arm.ts"), "run", "--id", e.id, "--arm", stage, "--agent-root", root];
    const r = spawnSync("bun", args, { encoding: "utf8", stdio: "inherit" });
    if (r.status !== 0) throw new Error(`fail-closed: ${e.id} ${stage}`);
  }
}

throw new Error(`fail-closed: unknown ${cmd}`);
