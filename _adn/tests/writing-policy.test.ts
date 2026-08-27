import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(import.meta.dir, "..");

describe("writing policy", () => {
  test("BUG and FEAT playbooks require principle-to-decision evidence in the final reply", () => {
    for (const name of ["bug-fix.md", "feature.md"]) {
      const text = readFileSync(join(ROOT, "skills/adn-mode/playbooks", name), "utf8");
      expect(text.toLowerCase()).toMatch(/principle/);
      expect(text.toLowerCase()).toMatch(/decision|why|how/);
    }
  });
});
