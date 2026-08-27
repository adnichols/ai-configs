import { describe, expect, test } from "bun:test";
import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(import.meta.dir, "..", "skills");

function skillDirs(): string[] {
  return readdirSync(ROOT).filter((name) => statSync(join(ROOT, name)).isDirectory());
}

describe("skills", () => {
  test("every skill has SKILL.md with unique ADN marker", () => {
    const dirs = skillDirs();
    expect(dirs.length).toBeGreaterThanOrEqual(48);
    const markers = new Set<string>();
    for (const name of dirs) {
      const text = readFileSync(join(ROOT, name, "SKILL.md"), "utf8");
      expect(text.includes("ADN_RUNTIME_MARKER:")).toBe(true);
      const m = text.match(/ADN_RUNTIME_MARKER:[^\n]+/);
      expect(m).toBeTruthy();
      expect(markers.has(m![0])).toBe(false);
      markers.add(m![0]);
    }
  });
});
