import { describe, expect, test } from "bun:test";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(import.meta.dir, "..");
const ADN_MODE = join(ROOT, "skills", "adn-mode");
const SKILL = join(ADN_MODE, "SKILL.md");
const PLAY = join(ADN_MODE, "playbooks");
const REFERENCES = join(ADN_MODE, "references");

const skill = readFileSync(SKILL, "utf8");

function markdownFiles(dir: string): string[] {
  return readdirSync(dir)
    .filter((n) => n.endsWith(".md"))
    .map((n) => join(dir, n));
}

describe("adn-mode contract", () => {
  test("adn-mode does not prescribe an impossible subagent type", () => {
    expect(skill).not.toContain('subagent_type: "adn"');
    expect(skill).not.toContain('subagent_type: "poteto-agent"');
    expect(skill).toContain("architect-grok");
    expect(skill).toContain("architect-kimi");
    expect(skill).toContain("reviewer-kimi");
  });

  test("adn-mode points to the right setup skill", () => {
    expect(skill).not.toContain("/setup-pstack");
    expect(skill).toContain("/setup-adn");
  });

  test("adn-mode files contain no em-dashes or en-dashes", () => {
    const files = [SKILL, ...markdownFiles(PLAY), ...markdownFiles(REFERENCES)];
    for (const path of files) {
      const text = readFileSync(path, "utf8");
      expect(text).not.toMatch(/[\u2014\u2013]/);
    }
  });

  test("every playbook has an explicit final handoff step", () => {
    for (const name of readdirSync(PLAY).filter((n) => n.endsWith(".md"))) {
      if (name === "opening-a-pr.md") continue;
      const text = readFileSync(join(PLAY, name), "utf8");
      const hasHandoff =
        text.includes("Run **Opening a PR**") || text.includes("No PR. End cleanly.");
      expect(hasHandoff).toBe(true);
    }
  });
});
