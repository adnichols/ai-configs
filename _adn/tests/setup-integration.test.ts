import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { describe, expect, test } from "bun:test";

const SCRIPT = join(import.meta.dir, "..", "scripts", "setup-adn.ts");
const VALIDATE = join(import.meta.dir, "..", "scripts", "validate-adn.ts");

function throughPhase(): number {
  const env = process.env.ADN_THROUGH;
  const i = process.argv.indexOf("--through");
  const raw = i >= 0 ? process.argv[i + 1] : env;
  if (!raw) return 8;
  return Number(String(raw).replace(/^p/, "")) || 8;
}

const RUN = throughPhase() >= 5;

describe.skipIf(!RUN)("setup-adn", () => {
  test("apply check rollback on agent-root", () => {
    const root = mkdtempSync(join(tmpdir(), "adn-setup-"));
    const result = join(root, "result.json");
    try {
      const apply = spawnSync("bun", [SCRIPT, "apply", "--agent-root", root, "--result", result], { encoding: "utf8" });
      expect(apply.status).toBe(0);
      const tx = JSON.parse(readFileSync(result, "utf8")).transactionId;
      expect(tx).toBeTruthy();
      expect(existsSync(join(root, "extensions", "adn-mode.ts"))).toBe(true);
      const check = spawnSync("bun", [SCRIPT, "check", "--agent-root", root], { encoding: "utf8" });
      expect(check.status).toBe(0);
      const rb = spawnSync("bun", [SCRIPT, "rollback", "--agent-root", root, "--transaction", tx], { encoding: "utf8" });
      expect(rb.status).toBe(0);
      const validate = spawnSync("bun", [VALIDATE, "rollback", "--agent-root", root, "--transaction", tx], { encoding: "utf8" });
      expect(validate.status).toBe(0);
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });
});
