import { existsSync, mkdirSync, readFileSync, chmodSync, mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { ADN_ROOT, atomicWrite, flag, parseArgs, sha256 } from "./lib.ts";

const { cmd, flags } = parseArgs();
if (cmd !== "run") throw new Error("fail-closed: run required");
const id = flag(flags, "id");
const arm = flag(flags, "arm");
const root = flag(flags, "agent-root") ?? ADN_ROOT;
if (!id || !arm) throw new Error("fail-closed: --id and --arm");
const privateDir = join(root, "adn", "evaluations", "private", id);
const packet = JSON.parse(readFileSync(join(privateDir, "packet.json"), "utf8"));
const diff = readFileSync(join(privateDir, "diff.patch"));
const packet_fingerprint = sha256(JSON.stringify({
  id: packet.id,
  category: packet.category,
  source: packet.source,
  intent: packet.intent,
  scope: packet.scope,
  base: packet.base,
  commit: packet.commit,
  verification: packet.verification,
  planBytesHash: packet.planBytesHash,
}) + sha256(diff));
const context = crypto.randomUUID();
const worktree = mkdtempSync(join(tmpdir(), `adn-${id}-${arm}-`));
writeFileSync(join(worktree, "packet.json"), JSON.stringify(packet));
writeFileSync(join(worktree, "diff.patch"), diff);
const skill = arm === "current" ? "skill://autoreview" : "skill://interrogate";
const diff_fingerprint = sha256(diff);
const prompt = `Read ${skill}.
Review this diff. Not a production merge.
Start with these two lines exactly:
packet_fingerprint=${packet_fingerprint}
diff_fingerprint=${diff_fingerprint}
Then VERDICT: PASS or VERDICT: FINDINGS_TO_RESOLVE and the material reason. Do not choose freely.
Diff:
${diff.toString("utf8").slice(0, 8000)}
`;
let stdout = "";
let fake = false;
if (flags.fake || flags["dry-run"] || process.env.ADN_FAKE_ARMS === "1") {
  fake = true;
  stdout = `FAKE_ARM\n${skill}\npacket_fingerprint=${packet_fingerprint}\ndiff_fingerprint=${diff_fingerprint}\nVERDICT: PASS\n`;
} else {
  let text = "";
  for (let attempt = 1; attempt <= 2; attempt++) {
    const started = Date.now();
    console.error(`arm-start ${id} ${arm} attempt=${attempt} max-time=90s`);
    const launched = spawnSync("omp", ["-p", "--no-session", "--max-time", "90s", prompt], {
      encoding: "utf8",
      cwd: worktree,
      timeout: 120_000,
    });
    stdout = `${launched.stdout ?? ""}${launched.stderr ?? ""}`;
    text = stdout.replace(/Working\.\.\.\n?/g, "").replace(/Deadline exceeded\n?/g, "").trim();
    console.error(`arm-done ${id} ${arm} attempt=${attempt} ms=${Date.now() - started} status=${launched.status} bytes=${text.length}`);
    if (text.includes(packet_fingerprint) && text.includes(diff_fingerprint) && /VERDICT:\s*(PASS|FINDINGS_TO_RESOLVE)/.test(text)) {
      stdout = text;
      break;
    }
    console.error(`arm-body ${id} ${arm} attempt=${attempt}\n${text}`);
    if (attempt === 2) {
      rmSync(worktree, { recursive: true, force: true });
      throw new Error(`fail-closed: omp arm ${id} ${arm}`);
    }
  }
}
const record = {
  arm,
  packet_fingerprint,
  diff_fingerprint: sha256(diff),
  context,
  worktree,
  skill,
  fake,
  body: stdout,
};
const dest = join(privateDir, `${arm}.json`);
atomicWrite(dest, JSON.stringify(record, null, 2) + "\n");
chmodSync(dest, 0o600);
const next = arm === "current" ? "current_complete" : "adn_complete";
spawnSync("bun", [
  join(ADN_ROOT, "scripts/trial-ledger.ts"),
  "advance",
  "--id",
  id,
  "--state",
  next,
  "--hash",
  packet_fingerprint,
  "--context",
  context,
  "--agent-root",
  root,
], { stdio: "inherit" });
console.log(JSON.stringify({ ok: true, id, arm, packet_fingerprint, context, worktree }));
