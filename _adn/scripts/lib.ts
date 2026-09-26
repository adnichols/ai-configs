import { createHash } from "node:crypto";
import { chmodSync, mkdirSync, readFileSync, readdirSync, renameSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { homedir } from "node:os";

export const PIN = "ecc249f1e306fc64ddf83c7bed16cacf7c2239db";
export const ADN_ROOT = process.env.ADN_ROOT ?? join(homedir(), ".agents", "adn");
// Roles ADN agents resolve through `model: "@<role>"` frontmatter. The models behind them live in OMP config.
export function agentRoles(agentsDir = join(ADN_ROOT, "agents")): string[] {
  const roles = new Set<string>();
  for (const name of readdirSync(agentsDir)) {
    const match = readFileSync(join(agentsDir, name), "utf8").match(/^model:\s*"?@([\w-]+)"?\s*$/m);
    if (!match) throw new Error(`fail-closed: ${name} must use model: "@<role>"`);
    roles.add(match[1]);
  }
  return [...roles].sort();
}
export const FORBIDDEN = [
  "prompt",
  "message",
  "transcript",
  "content",
  "arguments",
  "diff",
  "reviewerBody",
  "SECRET",
  "sk-ant",
];

export function sha256(data: string | Buffer): string {
  return createHash("sha256").update(data).digest("hex");
}

export function fileSha(path: string): string {
  return sha256(readFileSync(path));
}

export function atomicWrite(path: string, data: string | Buffer, mode = 0o600): void {
  mkdirSync(dirname(path), { recursive: true, mode: 0o700 });
  const tmp = `${path}.tmp.${process.pid}`;
  writeFileSync(tmp, data, { mode });
  renameSync(tmp, path);
  chmodSync(path, mode);
}

export function parseArgs(argv = process.argv.slice(2)): { cmd: string; flags: Record<string, string | boolean> } {
  let cmd = "";
  let rest = argv;
  if (argv[0] && !argv[0].startsWith("--")) {
    cmd = argv[0];
    rest = argv.slice(1);
  }
  const flags: Record<string, string | boolean> = {};
  for (let i = 0; i < rest.length; i++) {
    const a = rest[i];
    if (!a.startsWith("--")) continue;
    const key = a.slice(2);
    const next = rest[i + 1];
    if (!next || next.startsWith("--")) flags[key] = true;
    else {
      flags[key] = next;
      i++;
    }
  }
  return { cmd, flags };
}

export function flag(flags: Record<string, string | boolean>, name: string): string | undefined {
  const v = flags[name];
  return typeof v === "string" ? v : undefined;
}

export function containsForbidden(value: unknown): string | null {
  const json = JSON.stringify(value);
  for (const key of FORBIDDEN) {
    if (json.includes(key)) return key;
  }
  return null;
}

export function assertAllowlisted(value: unknown, extra: string[] = []): void {
  const hit = containsForbidden(value);
  if (hit && !extra.includes(hit)) throw new Error(`fail-closed: forbidden ${hit}`);
}

export function withDirLock<T>(root: string, fn: () => T): T {
  const lock = join(root, "adn", "locks", "setup.lock");
  mkdirSync(dirname(lock), { recursive: true });
  try {
    mkdirSync(lock);
  } catch {
    throw new Error(`fail-closed: lock held ${lock}`);
  }
  try {
    return fn();
  } finally {
    rmSync(lock, { recursive: true, force: true });
  }
}
