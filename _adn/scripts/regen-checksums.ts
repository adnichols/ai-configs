import { createHash } from "node:crypto";
import { existsSync, readFileSync, writeFileSync } from "node:fs";
import { homedir } from "node:os";
import { isAbsolute, join } from "node:path";

const ADN_ROOT = process.env.ADN_ROOT ?? join(homedir(), ".agents", "adn");
const MANIFEST = join(ADN_ROOT, "manifest.json");

function sha256(path: string): string {
  return createHash("sha256").update(readFileSync(path)).digest("hex");
}

function resolveTarget(target: string): string {
  if (target.startsWith("~")) return join(homedir(), target.slice(2));
  if (isAbsolute(target)) return target;
  return join(ADN_ROOT, target);
}

const manifest = JSON.parse(readFileSync(MANIFEST, "utf8"));
for (const row of manifest.assets) {
  if (row.excluded) continue;
  if (row.checksum === "excluded" || row.checksum === "link") continue;
  const target = resolveTarget(row.targetPath);
  if (!existsSync(target)) {
    console.error("missing", target);
    continue;
  }
  row.checksum = sha256(target);
}

writeFileSync(MANIFEST, JSON.stringify(manifest, null, 2) + "\n");
console.log(JSON.stringify({ ok: true, path: MANIFEST }));
