import { describe, expect, test } from "bun:test";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const PLAY = join(import.meta.dir, "..", "skills/adn-mode/playbooks");
const FIX = join(import.meta.dir, "fixtures/playbook-routing.json");

describe("playbook contract", () => {
  test("23 playbooks have source-step IDs", () => {
    const files = readdirSync(PLAY).filter((n) => n.endsWith(".md"));
    expect(files.length).toBe(23);
    for (const name of files) {
      const text = readFileSync(join(PLAY, name), "utf8");
      expect(text).toContain("<!-- source-step:");
    }
  });

  test("routing fixture covers every playbook with a positive and counterexample", () => {
    const files = readdirSync(PLAY).filter((n) => n.endsWith(".md")).map((n) => n.replace(/\.md$/, ""));
    const fixtures = JSON.parse(readFileSync(FIX, "utf8")) as Array<{ playbook: string; positive: unknown; counterexample: unknown }>;
    const names = new Set(fixtures.map((f) => f.playbook));
    for (const name of files) expect(names.has(name)).toBe(true);
    for (const row of fixtures) {
      expect(row.positive).toBeTruthy();
      expect(row.counterexample).toBeTruthy();
    }
  });
});
