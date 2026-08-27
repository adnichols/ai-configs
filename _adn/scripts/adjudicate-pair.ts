import { readFileSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { ADN_ROOT, atomicWrite, flag, parseArgs } from "./lib.ts";

const { flags } = parseArgs();
const id = flag(flags, "id");
const root = flag(flags, "agent-root") ?? ADN_ROOT;
if (!id) throw new Error("fail-closed: --id");
const dir = join(root, "adn", "evaluations", "private", id);
const current = JSON.parse(readFileSync(join(dir, "current.json"), "utf8"));
const adn = JSON.parse(readFileSync(join(dir, "adn.json"), "utf8"));
if (current.packet_fingerprint !== adn.packet_fingerprint) throw new Error("fail-closed: packet hash mismatch");
if (current.diff_fingerprint !== adn.diff_fingerprint) throw new Error("fail-closed: diff hash mismatch");
if (current.context === adn.context) throw new Error("fail-closed: shared context");
if (!current.body || !adn.body) throw new Error("fail-closed: missing reviewer body");
if ((current.fake || adn.fake) && !(current.fake && adn.fake)) throw new Error("fail-closed: fake arm");
const context = crypto.randomUUID();
const swap = Math.random() < 0.5;
const a = swap ? adn : current;
const b = swap ? current : adn;
const aFinds = /\bP[12]\b|FINDINGS_TO_RESOLVE/.test(a.body);
const bFinds = /\bP[12]\b|FINDINGS_TO_RESOLVE/.test(b.body);
let disposition = "retain";
if (aFinds && bFinds) disposition = "compose";
else if (swap && aFinds && !bFinds) disposition = "replace";
else if (!swap && bFinds && !aFinds) disposition = "replace";
const verdict = {
  id,
  disposition,
  packet_fingerprint: current.packet_fingerprint,
  independent: true,
  context,
  swapped: swap,
  currentSkill: current.skill,
  adnSkill: adn.skill,
};
atomicWrite(join(dir, "adjudication.json"), JSON.stringify(verdict, null, 2) + "\n");
spawnSync("bun", [join(ADN_ROOT, "scripts/trial-ledger.ts"), "advance", "--id", id, "--state", "adjudicated", "--agent-root", root], { stdio: "inherit" });
spawnSync("bun", [join(ADN_ROOT, "scripts/trial-ledger.ts"), "mark-valid", "--id", id, "--agent-root", root], { stdio: "inherit" });
console.log(JSON.stringify({ ok: true, ...verdict }));
