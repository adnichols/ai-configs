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
  assert.match(source, /detached supervisor/);
  assert.match(source, /reviewer subprocess running/);
  assert.match(source, /phase: "running"/);
  assert.match(source, /renderResult/);
  assert.doesNotMatch(source, /dispatched invisibly/);
});

test("completion delivery is bound to the originating Pi session", async () => {
  const index = await text("_pi/extensions/claude-review/index.ts");
  const runtime = await text("_pi/extensions/claude-review/runtime.ts");
  assert.match(index, /sessionManager\.getSessionId\(\)/);
  assert.match(index, /originSessionId/);
  assert.match(runtime, /job\.originSessionId === this\.activeSessionId/);
  assert.match(runtime, /sessionMatches/);
});

test("restart recovery indexes session delivery evidence once", async () => {
  const runtime = await text("_pi/extensions/claude-review/runtime.ts");
  assert.match(runtime, /private startupDeliveredJobIds\?: Set<string>/);
  assert.match(runtime, /if \(this\.startupDeliveredJobIds\) return this\.startupDeliveredJobIds/);
  assert.match(runtime, /this\.deliveredSessionJobIds\(\)\.has\(persisted\.jobId\)/);
  assert.doesNotMatch(runtime, /sessionHasDelivery\(jobId/);
});

test("Pi review prompts route Claude through claude_review", async () => {
  const prompt = await text("_pi/prompts/review:change-claude-code.md");
  assert.match(prompt, /claude_review\(\{/);
  assert.doesNotMatch(prompt, /python3[^\n]*claude_interactive_review\.py/);
  assert.doesNotMatch(prompt, /Opus 4\.7|Opus 4\.8|claude-opus-4-/);

  const adversarial = await text("_pi/prompts/review:plan-adversarial.md");
  assert.match(adversarial, /deterministic `claude_review` tool/);
});

test("artifact contract documentation separates transport success from workflow verdict", async () => {
  for (const file of ["_pi/README.md", "skills/claude-code-review/SKILL.md", "_pi/prompts/review:change-claude-code.md"]) {
    const source = await text(file);
    assert.match(source, /transport validity|transport success/i, `${file} must describe transport validity`);
    assert.match(source, /VERDICT:/, `${file} must explain workflow verdict handling`);
    assert.match(source, /reload|restart/, `${file} must describe lifecycle recovery`);
    if (file !== "_pi/prompts/review:change-claude-code.md") assert.match(source, /session JSONL/i, `${file} must describe long-review recovery`);
  }
  const runtime = await text("_pi/extensions/claude-review/runtime.ts");
  assert.doesNotMatch(runtime, /\^VERDICT:/, "runtime transport validation must not require an exact verdict line");
});

test("shared Pi-capable review workflows describe the deterministic tool", async () => {
  for (const file of [
    "skills/reviewed-html-plan/SKILL.md",
    "skills/run-plan/SKILL.md",
    "skills/autoreview/SKILL.md",
  ]) {
    const source = await text(file);
    assert.match(source, /claude_review\(\{/, `${file} must show the Pi tool route`);
    assert.doesNotMatch(source, /Opus 4\.7|claude-opus-4-7/, `${file} must leave model ownership to the launcher`);
  }
});

test("pre-pr implementation review remains a thin autoreview alias", async () => {
  const source = await text("skills/pre-pr-implementation-review/SKILL.md");
  assert.match(source, /indefinite compatibility alias/i);
  assert.match(source, /\/skill:autoreview <same arguments, unchanged>/);
  assert.match(source, /OPEN_PR_READY/);
  assert.doesNotMatch(source, /claude_review\(\{/);
  assert.doesNotMatch(source, /Severity:\s*P1/);
  assert.doesNotMatch(source, /targeted rereview/);
});
