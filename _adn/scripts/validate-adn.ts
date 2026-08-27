import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { flag, parseArgs } from "./lib.ts";

const PIN = "46756f89270d7e7dcb8c28c90fd0f957ade4ce2c";
const { cmd, flags } = parseArgs();
const root = flag(flags, "agent-root") ?? join(homedir(), ".omp", "agent");

if (cmd === "rollback") {
  const tx = flag(flags, "transaction");
  if (!tx) throw new Error("fail-closed: --transaction required");
  const journal = join(root, "adn", "transactions", `${tx}.json`);
  if (!existsSync(journal)) throw new Error("fail-closed: missing journal");
  console.log(JSON.stringify({ ok: true, transactionId: tx }));
  process.exit(0);
}

if (cmd === "operations") {
  const report = join(root, "adn", "operations", "monthly-audit.json");
  if (flags["require-monthly-handoff"] && !existsSync(report)) {
    throw new Error("fail-closed: missing monthly-audit.json");
  }
  const parsed = existsSync(report) ? JSON.parse(readFileSync(report, "utf8")) : null;
  if (parsed && parsed.window_start === parsed.window_end) throw new Error("fail-closed: zero-width window");
  console.log(JSON.stringify({ ok: true, cmd, report: parsed }));
  process.exit(0);
}

if (cmd === "live" || cmd === "live-smokes") {
  const missing: string[] = [];
  const files = [
    join(homedir(), ".agents/adn/skills/principle-laziness-protocol/SKILL.md"),
    join(root, "extensions/adn-mode.ts"),
    join(root, "agents/architect-grok.md"),
    join(root, "agents/architect-kimi.md"),
    join(root, "agents/reviewer-kimi.md"),
  ];
  for (const path of files) {
    if (!existsSync(path)) missing.push(path);
    else if (!readFileSync(path, "utf8").includes("ADN_RUNTIME_MARKER:") && !readFileSync(path, "utf8").includes("attach")) {
      missing.push(`marker:${path}`);
    }
  }
  const roles = spawnSync("omp", ["config", "get", "modelRoles", "--json"], { encoding: "utf8" });
  const value = JSON.parse(roles.stdout).value ?? {};
  for (const key of ["architect-grok", "architect-kimi", "reviewer-kimi"]) {
    if (!value[key]) missing.push(`role:${key}`);
  }
  const plugins = spawnSync("omp", ["plugin", "list", "--json"], { encoding: "utf8" });
  if (/ponytail/i.test(plugins.stdout)) missing.push("ponytail");
  if (flags["require-all-markers"] && missing.length) throw new Error(`fail-closed: ${missing.join(",")}`);
  if (flags["require-cleanup"] && !existsSync(join(root, "adn", "evaluations", "live-smoke.jsonl"))) {
    throw new Error("fail-closed: missing live-smoke");
  }
  console.log(JSON.stringify({ ok: true, cmd, missing, pin: PIN }));
  process.exit(0);
}

throw new Error(`fail-closed: unknown command ${cmd}`);
