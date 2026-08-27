import { existsSync, readFileSync } from "node:fs";
import { homedir } from "node:os";
import { join } from "node:path";
import { describe, expect, test } from "bun:test";

function throughPhase(): number {
  const i = process.argv.indexOf("--through");
  if (i === -1) return 8;
  return Number(String(process.argv[i + 1] ?? "p8").replace(/^p/, "")) || 8;
}

const RUN = throughPhase() >= 2;
const PIN = "46756f89270d7e7dcb8c28c90fd0f957ade4ce2c";
const ROOT = join(homedir(), ".agents", "adn", "agents");

describe.skipIf(!RUN)("adn council agents", () => {
  test("three role-backed agents exist with markers and verdicts", () => {
    for (const [id, alias, verdict] of [
      ["architect-grok", "@architect-grok", "DIVERGE"],
      ["architect-kimi", "@architect-kimi", "CONVERGE"],
      ["reviewer-kimi", "@reviewer-kimi", "BLOCK"],
    ] as const) {
      const path = join(ROOT, `${id}.md`);
      expect(existsSync(path)).toBe(true);
      const body = readFileSync(path, "utf8");
      expect(body).toContain(`ADN_RUNTIME_MARKER:${id}:${PIN}`);
      expect(body).toContain(alias);
      expect(body).toContain(verdict);
      expect(body).toContain("fail closed");
    }
  });
});
