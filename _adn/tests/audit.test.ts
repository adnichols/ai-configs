import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { describe, expect, test } from "bun:test";

const SCRIPT = join(import.meta.dir, "..", "scripts", "audit-adn.ts");
const RUN = (process.env.ADN_THROUGH ? Number(String(process.env.ADN_THROUGH).replace(/^p/, "")) : 8) >= 5;

describe.skipIf(!RUN)("audit-adn", () => {
  test("sentinels never leak to stdout", () => {
    const root = mkdtempSync(join(tmpdir(), "adn-audit-"));
    try {
      const dir = join(root, "sessions", "x");
      mkdirSync(dir, { recursive: true });
      writeFileSync(
        join(dir, "s.jsonl"),
        JSON.stringify({
          type: "message",
          message: { role: "user", content: [{ type: "text", text: "/adn-mode SECRET sk-ant-123" }] },
        }) + "\nnot json\n",
      );
      const r = spawnSync("bun", [SCRIPT, "--agent-root", root, "--dry-run"], { encoding: "utf8" });
      expect(r.status).toBe(0);
      expect(r.stdout).not.toContain("SECRET");
      expect(r.stdout).not.toContain("sk-ant");
      expect(r.stderr).not.toContain("SECRET");
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });
});
