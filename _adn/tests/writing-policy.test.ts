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

  test("unslop forbids mannered prose", () => {
    const text = readFileSync(join(ROOT, "skills/unslop/SKILL.md"), "utf8");
    expect(text).toContain("Mannered prose");
    expect(text).toContain("a dial worth turning");
    expect(text).toContain("When a literal phrase is available, use it");
  });

  test("adn-mode writing checklist forbids mannered prose", () => {
    const text = readFileSync(join(ROOT, "skills/adn-mode/SKILL.md"), "utf8");
    expect(text).toContain("No mannered prose");
    expect(text).toContain("a dial worth turning");
  });
});
