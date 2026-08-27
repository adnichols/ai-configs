import { mkdtempSync, mkdirSync, rmSync, writeFileSync, existsSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { describe, expect, test } from "bun:test";
import { decideVerification } from "../scripts/verification-skill.ts";

const RUN = (process.env.ADN_THROUGH ? Number(String(process.env.ADN_THROUGH).replace(/^p/, "")) : 8) >= 5;
const SCRIPT = join(import.meta.dir, "..", "scripts", "verification-skill.ts");

describe.skipIf(!RUN)("verification-skill", () => {
  test("five locked decisions", () => {
    expect(decideVerification("existing-command")).toEqual({ action: "reuse", reason: "existing-command" });
    expect(decideVerification("one-off-smoke")).toEqual({ action: "no-skill", reason: "one-off-smoke" });
    expect(decideVerification("repeated-gap")).toEqual({ action: "create", reason: "repeated-gap" });
    expect(decideVerification("covered-drift")).toEqual({ action: "maintain", reason: "covered-drift" });
    expect(decideVerification("uncovered-surface")).toEqual({ action: "untouched", reason: "uncovered-surface" });
  });

  test("creates a driver that launches the real surface then no-change maintain", { timeout: 15000 }, () => {
    const repo = mkdtempSync(join(tmpdir(), "adn-verify-"));
    try {
      mkdirSync(join(repo, ".agents", "skills"), { recursive: true });
      const surface = join(repo, "cli.ts");
      writeFileSync(surface, `console.log("surface-ok");\n`);
      const r = spawnSync("bun", [SCRIPT, "create", "--repo", repo, "--slug", "demo", "--surface", surface], {
        encoding: "utf8",
      });
      expect(r.status).toBe(0);
      expect(existsSync(join(repo, ".agents/skills/verify-demo/SKILL.md"))).toBe(true);
      const run = spawnSync("bun", [SCRIPT, "run", "--repo", repo, "--slug", "demo"], { encoding: "utf8" });
      expect(run.status).toBe(0);
      expect(run.stdout).toContain("surface-ok");
      const neg = spawnSync("bun", [SCRIPT, "maintain", "--repo", repo, "--slug", "demo", "--no-change"], {
        encoding: "utf8",
      });
      expect(neg.status).toBe(0);
      expect(JSON.parse(neg.stdout).changed).toBe(false);
    } finally {
      rmSync(repo, { recursive: true, force: true });
    }
  });
});
