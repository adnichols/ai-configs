import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { describe, expect, test } from "bun:test";

const RUN = (process.env.ADN_THROUGH ? Number(String(process.env.ADN_THROUGH).replace(/^p/, "")) : 8) >= 5;
const FIXTURE = join(import.meta.dir, "fixtures", "locked-candidates.json");
const BUNDLE = join(import.meta.dir, "..", "scripts", "candidate-bundle.ts");
const LEDGER = join(import.meta.dir, "..", "scripts", "trial-ledger.ts");
const ARM = join(import.meta.dir, "..", "scripts", "run-review-arm.ts");
const ADJ = join(import.meta.dir, "..", "scripts", "adjudicate-pair.ts");

describe.skipIf(!RUN)("review trial", () => {
  test("ten candidates 3/3/2/2 reach valid with matching hashes", () => {
    const root = mkdtempSync(join(tmpdir(), "adn-trial-"));
    try {
      const reg = spawnSync("bun", [BUNDLE, "register", "--manifest", FIXTURE, "--all", "--agent-root", root], {
        encoding: "utf8",
      });
      expect(reg.status).toBe(0);
      const val = spawnSync("bun", [LEDGER, "validate", "--agent-root", root, "--require-state", "registered", "--count", "10", "--distribution", "bug=3,feature=3,refactor=2,plan=2"], { encoding: "utf8" });
      expect(val.status).toBe(0);
      const ids = ["B01","B02","B03","F01","F02","F03","R01","R02","P01","P02"];
      for (const id of ids) {
        const a = spawnSync("bun", [ARM, "run", "--id", id, "--arm", "current", "--agent-root", root, "--fake"], { encoding: "utf8" });
        expect(a.status).toBe(0);
        const b = spawnSync("bun", [ARM, "run", "--id", id, "--arm", "adn", "--agent-root", root, "--fake"], { encoding: "utf8" });
        expect(b.status).toBe(0);
        const adj = spawnSync("bun", [ADJ, "--id", id, "--agent-root", root], { encoding: "utf8" });
        expect(adj.status).toBe(0);
        expect(adj.stdout).not.toContain("diff --git");
      }
      const done = spawnSync("bun", [LEDGER, "validate", "--agent-root", root, "--require-state", "valid", "--count", "10"], { encoding: "utf8" });
      expect(done.status).toBe(0);
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });
});
