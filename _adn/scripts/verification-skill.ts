import { mkdirSync, writeFileSync, readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { flag, parseArgs } from "./lib.ts";

export type VerifyDecision =
  | { action: "reuse"; reason: "existing-command" }
  | { action: "no-skill"; reason: "one-off-smoke" }
  | { action: "create"; reason: "repeated-gap" }
  | { action: "maintain"; reason: "covered-drift" }
  | { action: "untouched"; reason: "uncovered-surface" };

export function decideVerification(kind: string): VerifyDecision {
  if (kind === "existing-command") return { action: "reuse", reason: "existing-command" };
  if (kind === "one-off-smoke") return { action: "no-skill", reason: "one-off-smoke" };
  if (kind === "repeated-gap") return { action: "create", reason: "repeated-gap" };
  if (kind === "covered-drift") return { action: "maintain", reason: "covered-drift" };
  if (kind === "uncovered-surface") return { action: "untouched", reason: "uncovered-surface" };
  throw new Error(`fail-closed: unknown decision ${kind}`);
}


if (import.meta.main) {
  const { cmd, flags } = parseArgs();

  if (cmd === "decide") {
    const kind = flag(flags, "case") ?? "";
    console.log(JSON.stringify({ ok: true, ...decideVerification(kind) }));
    process.exit(0);
  }

  const repo = flag(flags, "repo");
  const slug = flag(flags, "slug");
  if (!repo || !slug) throw new Error("fail-closed: --repo and --slug");
  const dir = join(repo, ".agents", "skills", `verify-${slug}`);

  if (cmd === "create") {
    const decision = decideVerification("repeated-gap");
    const surface = flag(flags, "surface");
    if (!surface) throw new Error("fail-closed: --surface required for create");
    const args = String(flag(flags, "args") ?? "").split(" ").filter(Boolean);
    mkdirSync(dir, { recursive: true });
    writeFileSync(
      join(dir, "SKILL.md"),
      `---\nname: verify-${slug}\ndescription: Generated verification driver\n---\n\nRun driver.ts against the real surface.\n`,
    );
    writeFileSync(
      join(dir, "feature-map.json"),
      JSON.stringify({ slug, surfaces: [surface], program: surface, args, decision }) + "\n",
    );
    writeFileSync(
      join(dir, "driver.ts"),
      `import { spawnSync } from "node:child_process";
const surface = ${JSON.stringify(surface)};
const args = ${JSON.stringify(args)};
const r = spawnSync("bun", [surface, ...args], { encoding: "utf8", cwd: ${JSON.stringify(repo)}, timeout: 4000 });
if (r.status !== 0) throw new Error("fail-closed: surface " + (r.stderr || r.stdout));
if (!r.stdout.trim()) throw new Error("fail-closed: empty surface output");
console.log(r.stdout.trim());
`,
    );
    console.log(JSON.stringify({ ok: true, dir, action: decision.action }));
    process.exit(0);
  }

  if (cmd === "run") {
    const r = spawnSync("bun", [join(dir, "driver.ts")], { encoding: "utf8", cwd: repo, timeout: 5000 });
    if (r.status !== 0) throw new Error(`fail-closed: driver ${r.stderr || r.stdout}`);
    console.log(JSON.stringify({ ok: true, output: r.stdout.trim() }));
    process.exit(0);
  }

  if (cmd === "maintain") {
    if (!existsSync(join(dir, "feature-map.json"))) throw new Error("fail-closed: missing feature-map");
    const map = JSON.parse(readFileSync(join(dir, "feature-map.json"), "utf8"));
    if (flags["no-change"]) {
      if (map.slug !== slug) throw new Error("fail-closed: feature-map changed");
      console.log(JSON.stringify({ ok: true, changed: false, slug: map.slug, action: "untouched" }));
      process.exit(0);
    }
    const decision = decideVerification("covered-drift");
    map.decision = decision;
    writeFileSync(join(dir, "feature-map.json"), JSON.stringify(map) + "\n");
    console.log(JSON.stringify({ ok: true, changed: true, slug: map.slug, action: decision.action }));
    process.exit(0);
  }

  throw new Error(`fail-closed: unknown ${cmd}`);
}
