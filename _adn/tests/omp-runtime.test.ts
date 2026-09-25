import { expect, test } from "bun:test";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const source = join(import.meta.dir, "..");

test("fresh and repeated ADN installs provide OMP cleanup gates without plugins", () => {
  const root = mkdtempSync(join(tmpdir(), "adn-omp-runtime-"));
  try {
    for (let install = 0; install < 2; install++) {
      const result = spawnSync("bun", [join(source, "scripts/setup-adn.ts"), "apply", "--agent-root", root], {
        env: { ...process.env, ADN_ROOT: source }, encoding: "utf8",
      });
      expect(result.status, result.stderr).toBe(0);
      for (const name of ["adn-mode", "deslop", "no-comments"]) {
        expect(readFileSync(join(root, "skills", name, "SKILL.md"), "utf8"))
          .toBe(readFileSync(join(source, "skills", name, "SKILL.md"), "utf8"));
      }
      const omp = Bun.which("omp");
      if (omp) {
        for (const uri of ["skill://deslop", "skill://no-comments", "skill://adn-mode/references/omp-runtime.md"]) {
          const discovered = spawnSync(omp, ["read", uri], {
            env: { ...process.env, PI_CODING_AGENT_DIR: root }, encoding: "utf8",
          });
          expect(discovered.status, discovered.stderr).toBe(0);
          expect(discovered.stdout).not.toContain("Unknown skill");
          const relative = uri.slice("skill://".length);
          const path = uri.endsWith(".md") ? relative : join(relative, "SKILL.md");
          expect(discovered.stdout).toContain(readFileSync(join(root, "skills", path), "utf8").trim());
        }
      }
      const comments = readFileSync(join(root, "skills/no-comments/SKILL.md"), "utf8");
      expect(comments).toContain('agent: "comment-sicko"');
      expect(comments).not.toContain('subagent_type: "Comment Sicko"');
      const agent = readFileSync(join(root, "agents/comment-sicko.md"), "utf8");
      expect(agent).toContain('model: "@reviewer"');
      expect(agent).toContain("Stay read-only");
      const mode = readFileSync(join(root, "skills/adn-mode/SKILL.md"), "utf8");
      expect(mode).toContain("references/omp-runtime.md");
      expect(mode).not.toContain('`OMP` plugin');
      const contract = readFileSync(join(root, "skills/adn-mode/references/omp-runtime.md"), "utf8");
      expect(contract).toContain("takes precedence");
      expect(contract).toContain("retired standalone skill is not required");
    }
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});
