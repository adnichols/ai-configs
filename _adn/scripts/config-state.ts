import { mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join } from "node:path";
import { spawnSync } from "node:child_process";

export const ADN_ROLES = {
  "architect-grok": "cursor/cursor-grok-4.6:high",
  "architect-kimi": "cursor/kimi-k3-max:max",
  "reviewer-kimi": "cursor/kimi-k3-max:high",
} as const;

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

export function mergeRoles(current: Record<string, string>, patch: Record<string, string>): Record<string, string> {
  return { ...current, ...patch };
}

export function withLock<T>(lockDir: string, fn: () => T): T {
  mkdirSync(dirname(lockDir), { recursive: true });
  try {
    mkdirSync(lockDir);
  } catch {
    throw new Error(`lock held: ${lockDir}`);
  }
  try {
    return fn();
  } finally {
    rmSync(lockDir, { recursive: true, force: true });
  }
}

export function applyRoleMerge(opts: { agentRoot?: string } = {}): {
  profile: string;
  roles: Record<string, string>;
} {
  const profile = resolveProfile(opts);
  const lockDir = join(opts.agentRoot ?? join(homedir(), ".agents", "adn"), "locks", "config.lock");
  return withLock(lockDir, () => {
    let current: Record<string, string> = {};
    if (opts.agentRoot) {
      const store = join(profile, "modelRoles.json");
      try {
        current = JSON.parse(readFileSync(store, "utf8"));
      } catch {
        current = {};
      }
      const roles = mergeRoles(current, ADN_ROLES);
      writeFileSync(store, JSON.stringify(roles, null, 2) + "\n");
      return { profile, roles };
    }
    const got = spawnSync("omp", ["config", "get", "modelRoles", "--json"], { encoding: "utf8" });
    if (got.status !== 0) throw new Error(got.stderr || "fail-closed: omp config get failed");
    current = parseRolesEnvelope(got.stdout);
    const roles = mergeRoles(current, ADN_ROLES);
    const set = spawnSync("omp", ["config", "set", "modelRoles", "--json", JSON.stringify(roles)], {
      encoding: "utf8",
    });
    if (set.status !== 0) throw new Error(set.stderr || "fail-closed: omp config set failed");
    return { profile, roles };
  });
}
