import { createHash } from "node:crypto";
import { existsSync, lstatSync, readFileSync, readlinkSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { describe, expect, test } from "bun:test";

const PIN = "46756f89270d7e7dcb8c28c90fd0f957ade4ce2c";
const ADN_ROOT = join(homedir(), ".agents", "adn");
const SHARED_SKILLS = join(homedir(), ".agents", "skills");
const AI_CONFIGS = "/Users/anichols/code/ai-configs";
const MARKER_PREFIX = "ADN_RUNTIME_MARKER:";

const REQUIRED_FIELDS = [
  "id",
  "kind",
  "phase",
  "sourcePath",
  "sourceSha",
  "triggerClass",
  "requiredRoles",
  "requiredTools",
  "requiredSkills",
  "ompAdapter",
  "retainedBehavior",
  "failureBehavior",
  "runtimeMarker",
  "provingTest",
  "targetPath",
  "checksum",
] as const;

const P1_IDS = [
  "provenance-license",
  "provenance-doc",
  "principle-laziness-protocol",
  "ai-configs-ponytail-cutover",
] as const;

const PRINCIPLE_IDS = [
  "principle-laziness-protocol",
  "principle-foundational-thinking",
  "principle-redesign-from-first-principles",
  "principle-subtract-before-you-add",
  "principle-minimize-reader-load",
  "principle-outcome-oriented-execution",
  "principle-experience-first",
  "principle-exhaust-the-design-space",
  "principle-build-the-lever",
  "principle-model-the-domain",
  "principle-boundary-discipline",
  "principle-type-system-discipline",
  "principle-make-operations-idempotent",
  "principle-migrate-callers-then-delete-legacy-apis",
  "principle-separate-before-serializing-shared-state",
  "principle-prove-it-works",
  "principle-fix-root-causes",
  "principle-sequence-verifiable-units",
  "principle-guard-the-context-window",
  "principle-never-block-on-the-human",
  "principle-encode-lessons-in-structure",
] as const;

const OPERATIONAL_IDS = [
  "adn-mode",
  "setup-adn",
  "adn-audit",
  "adopt-skill",
  "how",
  "why",
  "recall",
  "blast-radius",
  "architect",
  "arena",
  "swarm",
  "interrogate",
  "automate-me",
  "reflect",
  "teach",
  "no-comments",
  "figure-it-out",
  "show-me-your-work",
  "create-verification-skill",
  "maintain-verification-skill",
  "unslop",
  "bro",
  "technical-writing",
  "typescript-best-practices",
  "poteto-mode",
  "setup-pstack",
  "tdd",
] as const;

const PLAYBOOK_IDS = [
  "playbook-investigation",
  "playbook-bug-fix",
  "playbook-perf-issue",
  "playbook-hillclimb",
  "playbook-runtime-forensics",
  "playbook-trace-forensics",
  "playbook-feature",
  "playbook-refactoring",
  "playbook-prototype",
  "playbook-visual-parity",
  "playbook-authoring-a-skill",
  "playbook-eval",
  "playbook-babysit",
  "playbook-shipping",
  "playbook-autonomous-run",
  "playbook-orchestrate",
  "playbook-autopilot-full",
  "playbook-autopilot-stack",
  "playbook-session-pickup",
  "playbook-pause-safely",
  "playbook-multi-phase-plan",
  "playbook-worktree-cleanup",
  "playbook-opening-a-pr",
] as const;

const AGENT_IDS = ["architect-grok", "architect-kimi", "reviewer-kimi"] as const;

type ManifestRow = {
  id: string;
  kind: string;
  phase: number;
  sourcePath: string;
  sourceSha: string;
  triggerClass: string;
  requiredRoles: string[];
  requiredTools: string[];
  requiredSkills: string[];
  ompAdapter: string;
  retainedBehavior: string;
  failureBehavior: string;
  runtimeMarker: string;
  provingTest: string;
  targetPath: string;
  checksum: string;
  excluded?: boolean;
};

type Manifest = {
  schemaVersion: number;
  version: string;
  upstream: {
    url: string;
    pin: string;
    license: string;
    reviewDate: string;
  };
  roles: Record<string, string>;
  assets: ManifestRow[];
};

function gate(): "all" | number {
  const args = process.argv;
  const env = process.env.ADN_THROUGH;
  if (args.includes("--all") || env === "all") return "all";
  const idx = args.indexOf("--through");
  const raw = idx >= 0 ? args[idx + 1] : env;
  if (raw) return Number(String(raw).replace(/^p/i, ""));
  return 1;
}

function sha256(path: string): string {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function loadManifest(): Manifest {
  const path = join(ADN_ROOT, "manifest.json");
  expect(existsSync(path)).toBe(true);
  return JSON.parse(readFileSync(path, "utf8")) as Manifest;
}

describe("ADN manifest", () => {
  const through = gate();

  test("schema, pin, license, and exhaustive inventory", () => {
    const manifest = loadManifest();
    expect(manifest.schemaVersion).toBe(1);
    expect(manifest.upstream.pin).toBe(PIN);
    expect(manifest.upstream.license).toBe("MIT");
    expect(manifest.upstream.url).toContain("cursor/plugins");
    expect(manifest.roles["architect-grok"]).toBe("xai-oauth/grok-4.6:high");
    expect(manifest.roles["architect-kimi"]).toBe("cursor/kimi-k3-max:max");
    expect(manifest.roles["reviewer-kimi"]).toBe("cursor/kimi-k3-max:high");

    const ids = manifest.assets.map((row) => row.id);
    expect(new Set(ids).size).toBe(ids.length);
    for (const id of [...P1_IDS, ...PRINCIPLE_IDS, ...OPERATIONAL_IDS, ...PLAYBOOK_IDS, ...AGENT_IDS]) {
      expect(ids).toContain(id);
    }
    expect(ids).not.toContain("extension-adn-mode");
    expect(ids).toContain("exclusion-benny");
    expect(ids).not.toContain("make-bot-ui");

    const license = readFileSync(join(ADN_ROOT, "LICENSE.pstack"), "utf8");
    expect(license).toContain("MIT License");
    expect(license).toContain("Lauren Tan");
    const provenance = readFileSync(join(ADN_ROOT, "PROVENANCE.md"), "utf8");
    expect(provenance).toContain(PIN);
    expect(provenance).toContain("do not silently refresh");

    for (const row of manifest.assets) {
      for (const field of REQUIRED_FIELDS) {
        expect(row[field], `${row.id} missing ${field}`).toBeDefined();
      }
    }
  });

  test("phase gate requires owned files, checksums, and markers", () => {
    const manifest = loadManifest();
    const required = manifest.assets.filter((row) => {
      if (row.excluded) return false;
      if (through === "all") return true;
      return row.phase <= through;
    });
    expect(required.map((row) => row.id)).toEqual(expect.arrayContaining([...P1_IDS]));

    for (const row of required) {
      const target = row.targetPath.startsWith("~")
        ? join(homedir(), row.targetPath.slice(2))
        : row.targetPath.startsWith("/")
          ? row.targetPath
          : join(ADN_ROOT, row.targetPath);
      expect(existsSync(target), `${row.id} missing ${target}`).toBe(true);
      if (row.checksum !== "link") {
        expect(sha256(target), `${row.id} checksum`).toBe(row.checksum);
      }
      if (row.runtimeMarker.startsWith(MARKER_PREFIX) && !row.id.startsWith("ai-configs-")) {
        const body = readFileSync(target, "utf8");
        expect(body).toContain(row.runtimeMarker);
      }
    }
  });

  test("laziness is linked one-level before Ponytail can return", () => {
    const skill = join(ADN_ROOT, "skills", "principle-laziness-protocol", "SKILL.md");
    const link = join(SHARED_SKILLS, "principle-laziness-protocol");
    expect(existsSync(skill)).toBe(true);
    expect(lstatSync(link).isSymbolicLink()).toBe(true);
    expect(resolve(dirname(link), readlinkSync(link))).toBe(join(ADN_ROOT, "skills", "principle-laziness-protocol"));
    const body = readFileSync(skill, "utf8");
    expect(body).toContain(`${MARKER_PREFIX}principle-laziness-protocol`);
    expect(body).toContain(PIN);
    expect(body).toContain("Prefer deletion");
  });

  test("ai-configs installer cannot reinstall Ponytail", () => {
    const install = readFileSync(join(AI_CONFIGS, "_omp", "install.sh"), "utf8");
    const testFile = readFileSync(join(AI_CONFIGS, "test_omp_config_install.sh"), "utf8");
    expect(install).not.toContain("@dietrichgebert/ponytail");
    expect(install).not.toMatch(/ponytail/i);
    expect(testFile).not.toContain("plugin install @dietrichgebert/ponytail");
    expect(testFile).toContain("ponytail");
  });
});
