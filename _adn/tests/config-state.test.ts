import { mkdirSync, mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { describe, expect, test } from "bun:test";
import {
  ADN_ROLES,
  mergeRoles,
  parseRolesEnvelope,
  resolveProfile,
  withLock,
  applyRoleMerge,
} from "../scripts/config-state.ts";

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

  test("merge preserves unrelated keys", () => {
    const next = mergeRoles({ reviewer: "keep", default: "xai" }, ADN_ROLES);
    expect(next.reviewer).toBe("keep");
    expect(next.default).toBe("xai");
    expect(next["architect-grok"]).toBe("cursor/cursor-grok-4.6:high");
    expect(next["architect-kimi"]).toBe("cursor/kimi-k3-max:max");
    expect(next["reviewer-kimi"]).toBe("cursor/kimi-k3-max:high");
  });

  test("neutral cwd profile matches omp config path", () => {
    const profile = resolveProfile({ cwd: "/tmp", env: { ...process.env, PI_CONFIG_FILES: "should-not-win" } });
    expect(profile).toBe("/Users/anichols/.omp/agent");
  });

  test("agent-root never writes live settings", () => {
    const root = mkdtempSync(join(tmpdir(), "adn-agent-"));
    try {
      const result = applyRoleMerge({ agentRoot: root });
      expect(result.profile).toBe(root);
      expect(result.roles["architect-grok"]).toBe(ADN_ROLES["architect-grok"]);
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  });

  test("lock is exclusive", () => {
    const dir = mkdtempSync(join(tmpdir(), "adn-lock-"));
    const lock = join(dir, "config.lock");
    mkdirSync(lock);
    try {
      expect(() => withLock(lock, () => 1)).toThrow(/lock held/);
    } finally {
      rmSync(dir, { recursive: true, force: true });
    }
  });
});
