import { readdirSync, readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { ADN_ROOT, atomicWrite, flag, parseArgs, sha256 } from "./lib.ts";
import { spawnSync } from "node:child_process";

const { flags } = parseArgs();
const root = flag(flags, "agent-root");
if (!root) throw new Error("fail-closed: --agent-root");
const txDir = join(root, "adn", "transactions");
const times: Array<{ utc: string; transactionId?: string; file: string }> = [];
if (existsSync(txDir)) {
  for (const name of readdirSync(txDir)) {
    if (!name.endsWith(".json") || name.endsWith(".result.json")) continue;
    try {
      const parsed = JSON.parse(readFileSync(join(txDir, name), "utf8"));
      if (typeof parsed.utc === "string") times.push({ utc: parsed.utc, transactionId: parsed.transactionId, file: name });
    } catch {}
  }
}
times.sort((a, b) => a.utc.localeCompare(b.utc));
const now = new Date();
const start = times[0] ? new Date(times[0].utc) : new Date(now.getTime() - 60_000);
const due = new Date(now.getTime() + 30 * 24 * 3600 * 1000);
const durationMs = Math.max(now.getTime() - start.getTime(), 1);
const sessionsDir = join(root, "sessions");
const coverage = spawnSync("bun", [join(ADN_ROOT, "scripts/audit-adn.ts"), "--agent-root", root, "--dry-run"], {
  encoding: "utf8",
});
let sessionCount = 0;
let recordCount = 0;
let skippedCount = 0;
let errorCount = 0;
try {
  const parsed = JSON.parse((coverage.stdout || "{}").trim().split("\n").at(-1) || "{}");
  sessionCount = Number(parsed.sessionCount ?? 0);
  recordCount = Number(parsed.recordCount ?? 0);
  skippedCount = Number(parsed.skippedCount ?? parsed.skipped ?? 0);
  errorCount = Number(parsed.errorCount ?? 0);
} catch {}
if (!existsSync(sessionsDir)) {
  sessionCount = 0;
}
const limitations = [
  "short-window non-use cannot justify deletion",
  "first short window may recommend retain/optional/further-observation only",
];
if (!times[0]) limitations.push("no-install-transaction");
if (durationMs < 21 * 24 * 3600 * 1000) limitations.push("window shorter than 21 days");
const report = {
  owner: "ai-configs maintainer",
  window_start: start.toISOString(),
  window_end: now.toISOString(),
  duration_ms: durationMs,
  duration: `${Math.round(durationMs / 1000)}s`,
  installTransactionId: times[0]?.transactionId ?? null,
  profileRootId: sha256(root).slice(0, 12),
  sinceInstall: Boolean(flags["since-install"]),
  transcript_coverage: { sessionCount, recordCount },
  skipped: skippedCount,
  errors: errorCount,
  nextDueUtc: due.toISOString(),
  command: "bun ~/.agents/adn/scripts/audit-adn.ts --workspace /Users/anichols/code/ai-configs --since-install --window 21d --report adoption",
  outputRoot: join(root, "adn", "evaluations"),
  failureAction: "page ai-configs maintainer and keep evidence",
  observation_limitations: limitations,
  recommend: "further-observation",
  delete: undefined,
};
const dest = join(
  root,
  "adn",
  "operations",
  `monthly-audit-${start.toISOString().slice(0, 10)}-${now.toISOString().slice(0, 10)}.json`,
);
atomicWrite(join(root, "adn", "operations", "monthly-audit.json"), JSON.stringify(report, null, 2) + "\n");
atomicWrite(dest, JSON.stringify(report, null, 2) + "\n");
console.log(JSON.stringify({ ok: true, window_start: report.window_start, window_end: report.window_end, dest }));
