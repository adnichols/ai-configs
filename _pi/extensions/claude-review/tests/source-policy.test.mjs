import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import path from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const repo = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../../../..");

async function text(file) {
  return readFile(path.join(repo, file), "utf8");
}

test("public tool schema exposes review intent but no transport controls", async () => {
  const source = await text("_pi/extensions/claude-review/index.ts");
  assert.match(source, /name:\s*"claude_review"/);
  for (const forbidden of ["mode", "background", "timeout", "model", "effort", "command", "spawn", "overlay", "quietThreshold"]) {
    assert.doesNotMatch(source, new RegExp(`\\b${forbidden}\\s*:\\s*Type\\.`), `schema must not expose ${forbidden}`);
  }
  assert.doesNotMatch(source, /from\s+["'][^"']*pi-interactive-shell|interactive_shell\s*\(\s*\{/);
  assert.doesNotMatch(source, /autoExitOnQuiet/);
  assert.match(source, /pi\.on\("tool_call"/);
  assert.match(source, /pi\.on\("session_shutdown"/);
});

test("Pi review prompts route Claude through claude_review", async () => {
  const prompt = await text("_pi/prompts/review:change-claude-code.md");
  assert.match(prompt, /claude_review\(\{/);
  assert.doesNotMatch(prompt, /python3[^\n]*claude_interactive_review\.py/);
  assert.doesNotMatch(prompt, /Opus 4\.7|Opus 4\.8|claude-opus-4-/);

  const adversarial = await text("_pi/prompts/review:plan-adversarial.md");
  assert.match(adversarial, /deterministic `claude_review` tool/);
});

test("shared Pi-capable review workflows describe the deterministic tool", async () => {
  for (const file of [
    "skills/reviewed-html-plan/SKILL.md",
    "skills/run-plan/SKILL.md",
    "skills/pre-pr-implementation-review/SKILL.md",
  ]) {
    const source = await text(file);
    assert.match(source, /claude_review\(\{/, `${file} must show the Pi tool route`);
    assert.doesNotMatch(source, /Opus 4\.7|claude-opus-4-7/, `${file} must leave model ownership to the launcher`);
  }
});
