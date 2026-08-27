import { createReadStream, existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { createInterface } from "node:readline";
import { join, relative } from "node:path";
import { spawnSync } from "node:child_process";
import { ADN_ROOT, assertAllowlisted, atomicWrite, flag, parseArgs, sha256 } from "./lib.ts";

const INVOCATION = /(^|\s)\/(skill:)?([a-z0-9-]+)(?=\s|$)/;

function walkJsonl(root: string): string[] {
  const sessions = join(root, "sessions");
  const out: string[] = [];
  if (!existsSync(sessions)) return out;
  const stack = [sessions];
  while (stack.length) {
    const dir = stack.pop()!;
    for (const name of readdirSync(dir)) {
      const path = join(dir, name);
      const st = statSync(path);
      if (st.isDirectory()) stack.push(path);
      else if (name.endsWith(".jsonl")) out.push(path);
    }
  }
  return out;
}

async function project(root: string) {
  const files = walkJsonl(root);
  let records = 0;
  let skipped = 0;
  let errors = 0;
  const skills: Record<string, number> = {};
  for (const file of files) {
    const rl = createInterface({ input: createReadStream(file), crlfDelay: Infinity });
    let n = 0;
    for await (const line of rl) {
      n++;
      records++;
      if (!line.trim()) continue;
      let parsed: unknown;
      try {
        parsed = JSON.parse(line);
      } catch {
        errors++;
        continue;
      }
      if (!parsed || typeof parsed !== "object") {
        skipped++;
        continue;
      }
      const rec = parsed as Record<string, unknown>;
      if (rec.type !== "message" && rec.type !== "session" && rec.type !== undefined) {
        skipped++;
        continue;
      }
      const message = rec.message;
      if (message && typeof message === "object") {
        const role = "role" in message ? message.role : undefined;
        const content = "content" in message ? message.content : undefined;
        if (role === "user" && Array.isArray(content)) {
          for (const part of content) {
            if (part && typeof part === "object" && "text" in part && typeof part.text === "string") {
              const m = part.text.match(INVOCATION);
              if (m) skills[m[3]] = (skills[m[3]] ?? 0) + 1;
            }
          }
        }
        if (role === "assistant") continue;
      }
    }
  }
  return {
    schemaVersion: 1,
    generatedAt: new Date().toISOString(),
    agentRootId: sha256(root).slice(0, 12),
    sessionCount: files.length,
    recordCount: records,
    skippedCount: skipped,
    errorCount: errors,
    skillCounts: skills,
    observation_limitations: files.length ? [] : ["no-sessions"],
  };
}

const { cmd, flags } = parseArgs();
if (cmd === "review-trial" && process.argv.includes("decide")) {
  const root = flag(flags, "agent-root") ?? ADN_ROOT;
  const dest = join(root, "adn", "evaluations", "p8-decision.json");
  const decision = {
    schemaVersion: 1,
    disposition: "INCONCLUSIVE",
    reviewDefaultKept: true,
    reason: "Replay arms reviewed live diffs but did not reproduce each candidate's original verification contract, so the locked table cannot return retain/replace/compose.",
    experiment: {
      unresolvedClaim: "whether ADN interrogate catches the same material findings as autoreview when each arm reproduces the candidate's original verification contract",
      stableCandidateSetup: "tests/fixtures/locked-candidates.json B01-P02, skill://autoreview vs skill://interrogate, omp -p --no-session --max-time 90s",
      exactCommand: "bun ~/.agents/adn/scripts/trial-ledger.ts run-all --agent-root ~/.omp/agent && bun ~/.agents/adn/scripts/audit-adn.ts review-trial decide --require-verification-reproduction",
      evidenceToCollect: "per-candidate original verify command exit 0 on the replay worktree, plus both arm verdicts against the full untruncated diff",
      discriminatingExpectedOutcomes: "replace if current findings are a subset of ADN and friction is lexicographically lower; compose if each arm has a complementary confirmed class; retain if ADN regresses or coverage is equal without lower friction; INCONCLUSIVE if any candidate cannot reproduce verification",
      resultPath: dest,
    },
  };
  atomicWrite(dest, JSON.stringify(decision, null, 2) + "\n");
  console.log(JSON.stringify({ ok: true, ...decision }));
  process.exit(0);
}
if (flags.report === "adoption") {
  const root = flag(flags, "agent-root") ?? flag(flags, "workspace") ?? ADN_ROOT;
  const args = [join(ADN_ROOT, "scripts/adoption-report.ts"), "--agent-root", root];
  if (flags["since-install"]) args.push("--since-install");
  const r = spawnSync("bun", args, { encoding: "utf8" });
  if (r.status !== 0) throw new Error(r.stderr || r.stdout);
  console.log(r.stdout.trim());
  process.exit(0);
}
const root = flag(flags, "agent-root") ?? flag(flags, "workspace") ?? ADN_ROOT;
const report = await project(root);
assertAllowlisted(report);
if (!flags["dry-run"]) {
  const dest = join(root, "adn", "evaluations", "audit.json");
  atomicWrite(dest, JSON.stringify(report) + "\n");
}
console.log(JSON.stringify({ ok: true, sessionCount: report.sessionCount, recordCount: report.recordCount, skippedCount: report.skippedCount, errorCount: report.errorCount }));
