import { readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(import.meta.dir, "..", "skills");
const missing: string[] = [];
for (const name of readdirSync(ROOT)) {
  const dir = join(ROOT, name);
  if (!statSync(dir).isDirectory()) continue;
  const skill = join(dir, "SKILL.md");
  try {
    const text = readFileSync(skill, "utf8");
    if (!text.includes("ADN_RUNTIME_MARKER:")) missing.push(name);
  } catch {
    missing.push(name);
  }
}
if (process.argv.includes("--fail-on-shadow") && missing.length) {
  throw new Error(`fail-closed: ${missing.join(",")}`);
}
console.log(JSON.stringify({ ok: true, missing }));
