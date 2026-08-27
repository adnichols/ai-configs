import { existsSync, readFileSync } from "node:fs";
import { ADN_ROOT, atomicWrite, flag, parseArgs } from "./lib.ts";
import { MARKER } from "../extensions/adn-mode.ts";
import { join } from "node:path";

const REQUIRED = ["session_start", "activate", "casual", "compact", "branch", "tree", "off", "new", "resume"];

const { flags } = parseArgs();
const root = flag(flags, "agent-root") ?? ADN_ROOT;
const dest = join(root, "adn", "evaluations", "tui-lifecycle.jsonl");
if (!existsSync(dest)) throw new Error("fail-closed: missing real TUI packet");
const recs = readFileSync(dest, "utf8")
  .split("\n")
  .filter(Boolean)
  .map((line) => JSON.parse(line) as { event: string; surface?: string; casualRouted?: boolean; display?: boolean; marker?: string });
const events = recs.map((r) => r.event);
for (const name of REQUIRED) {
  if (!events.includes(name)) throw new Error(`fail-closed: missing TUI event ${name}`);
}
if (!recs.some((r) => r.surface === "omp-tui")) throw new Error("fail-closed: not a real OMP TUI session");
if (recs.some((r) => r.casualRouted)) throw new Error("fail-closed: casual routed");
if (recs.some((r) => r.display)) throw new Error("fail-closed: reminder leak");
if (recs.some((r) => r.marker && !r.marker.startsWith("ADN_RUNTIME_MARKER:extension-adn-mode"))) {
  throw new Error("fail-closed: marker");
}
atomicWrite(dest, recs.map((r) => JSON.stringify({ ...r, marker: MARKER, display: false, casualRouted: false })).join("\n") + "\n");
console.log(JSON.stringify({ ok: true, count: recs.length, dest, events, surface: "omp-tui" }));
