import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, test } from "bun:test";
import { parseRolesEnvelope, readRoles, resolveProfile } from "../scripts/config-state.ts";

function throughPhase(): number {
  const i = process.argv.indexOf("--through");
  if (i === -1) return 8;
  return Number(String(process.argv[i + 1] ?? "p8").replace(/^p/, "")) || 8;
}

const RUN = throughPhase() >= 2;

describe.skipIf(!RUN)("config-state", () => {
  test("parses omp JSON envelope .value", () => {
    const roles = parseRolesEnvelope(
      JSON.stringify({ key: "modelRoles", value: { reviewer: "x" }, type: "record" }),
    );
    expect(roles).toEqual({ reviewer: "x" });
  });

  test("fail-closed on missing modelRoles", () => {
    expect(() => parseRolesEnvelope(JSON.stringify({ key: "modelRoles", type: "record" }))).toThrow(/fail-closed/);
  });

  test("neutral cwd profile matches omp config path", () => {
    const profile = resolveProfile({ cwd: "/tmp", env: { ...process.env, PI_CONFIG_FILES: "should-not-win" } });
    expect(profile).toBe("/Users/anichols/.omp/agent");
  });

  test("agent root reads modelRoles from its config.yml and fails closed without the key", () => {
    const root = mkdtempSync(join(tmpdir(), "adn-roles-"));
    try {
      expect(readRoles({ agentRoot: root })).toBeNull();
      writeFileSync(join(root, "config.yml"), "modelRoles:\n  reviewer: devin/swe-2:high\n");
      expect(readRoles({ agentRoot: root })).toEqual({ reviewer: "devin/swe-2:high" });
      writeFileSync(join(root, "config.yml"), "theme: dark\n");
      expect(() => readRoles({ agentRoot: root })).toThrow(/fail-closed/);
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });
});
