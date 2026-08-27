import { spawnSync } from "node:child_process";
import { join } from "node:path";
import { ADN_ROOT } from "./lib.ts";

const r = spawnSync("bun", [join(ADN_ROOT, "scripts/audit-adn.ts"), ...process.argv.slice(2)], { stdio: "inherit" });
process.exit(r.status ?? 1);
