import { existsSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

export function resolveProfile(opts: { cwd?: string; env?: NodeJS.ProcessEnv; agentRoot?: string } = {}): string {
  if (opts.agentRoot) return opts.agentRoot;
  const env = { ...process.env, ...(opts.env ?? {}) };
  delete env.PI_CONFIG_FILES;
  const r = spawnSync("omp", ["config", "path"], {
    cwd: opts.cwd ?? "/tmp",
    env,
    encoding: "utf8",
  });
  if (r.status !== 0) throw new Error(r.stderr || "fail-closed: omp config path failed");
  return r.stdout.trim();
}

export function parseRolesEnvelope(raw: string): Record<string, string> {
  const parsed = JSON.parse(raw);
  const value = parsed?.value;
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    throw new Error("fail-closed: modelRoles missing");
  }
  return { ...value };
}

// OMP owns role-to-model mapping (`modelRoles`, installed from `_omp/config.yml`).
// ADN only reads it. Returns null for an isolated agent root with no config.yml.
export function readRoles(opts: { agentRoot?: string } = {}): Record<string, string> | null {
  if (opts.agentRoot) {
    const config = join(opts.agentRoot, "config.yml");
    if (!existsSync(config)) return null;
    const roles = Bun.YAML.parse(readFileSync(config, "utf8"))?.modelRoles;
    if (!roles || typeof roles !== "object") throw new Error("fail-closed: modelRoles missing");
    return { ...roles };
  }
  const got = spawnSync("omp", ["config", "get", "modelRoles", "--json"], { encoding: "utf8" });
  if (got.status !== 0) throw new Error(got.stderr || "fail-closed: omp config get failed");
  return parseRolesEnvelope(got.stdout);
}
