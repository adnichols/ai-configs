import { mkdtempSync, mkdirSync, rmSync, writeFileSync, readFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { describe, expect, test } from "bun:test";

const RUN = (process.env.ADN_THROUGH ? Number(String(process.env.ADN_THROUGH).replace(/^p/, "")) : 8) >= 5;
const SCRIPT = join(import.meta.dir, "..", "scripts", "audit-adn.ts");

describe.skipIf(!RUN)("adoption report", () => {
  test("monthly handoff names owner due command", () => {
    const root = mkdtempSync(join(tmpdir(), "adn-report-"));
    try {
      mkdirSync(join(root, "adn", "operations"), { recursive: true, mode: 0o700 });
      const r = spawnSync("bun", [join(import.meta.dir, "..", "scripts", "adoption-report.ts"), "--agent-root", root], { encoding: "utf8" });
      expect(r.status).toBe(0);
      const handoff = JSON.parse(readFileSync(join(root, "adn/operations/monthly-audit.json"), "utf8"));
      expect(handoff.owner).toBe("ai-configs maintainer");
      expect(handoff.command).toContain("audit-adn.ts");
      expect(handoff.failureAction).toBeTruthy();
      expect(handoff.delete).toBeUndefined();
      expect(handoff.duration_ms).toBeGreaterThan(0);
      expect(handoff.observation_limitations.join(" ")).toContain("cannot justify deletion");
      expect(handoff.window_start).toBeTruthy();
      expect(handoff.window_end).toBeTruthy();
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });
});
