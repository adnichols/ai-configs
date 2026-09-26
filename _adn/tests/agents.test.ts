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
const PIN = "ecc249f1e306fc64ddf83c7bed16cacf7c2239db";
const ROOT = join(homedir(), ".agents", "adn", "agents");

describe.skipIf(!RUN)("adn council agents", () => {
  test("role-backed agents exist with markers and verdicts", () => {
    for (const [id, alias, verdict] of [
      ["arch-one", "@arch-one", "DIVERGE"],
      ["arch-two", "@arch-two", "DIVERGE"],
      ["arch-three", "@arch-three", "DIVERGE"],
      ["reviewer-two", "@reviewer-two", "BLOCK"],
      ["reviewer-three", "@reviewer-three", "BLOCK"],
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
