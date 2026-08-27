import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { routeRequest } from "../scripts/route-request.ts";

const PLAY = join(import.meta.dir, "..", "skills/adn-mode/playbooks");
const FIX = join(import.meta.dir, "fixtures/playbook-routing.json");
const files = readdirSync(PLAY).filter((n) => n.endsWith(".md")).map((n) => n.replace(/\.md$/, ""));
const fixtures = JSON.parse(readFileSync(FIX, "utf8")) as Array<{
  playbook: string;
  positive: { text: string; adnActive?: boolean; explicitAdn?: boolean; route?: string; handoff?: string; threshold?: string };
  counterexample: { text: string; adnActive?: boolean; explicitAdn?: boolean; reason?: string; overlap?: boolean };
}>;
const names = new Set(fixtures.map((f) => f.playbook));
const missing = files.filter((n) => !names.has(n));
if (process.argv.includes("--require-manifest-coverage") && missing.length) {
  throw new Error(`fail-closed: ${missing.join(",")}`);
}
for (const f of fixtures) {
  const pos = routeRequest({
    text: f.positive.text,
    adnActive: f.positive.adnActive ?? true,
    explicitAdn: f.positive.explicitAdn,
  });
  const expected = f.positive.route ?? f.playbook;
  if (pos.playbook !== expected) throw new Error(`fail-closed: ${f.playbook} positive ${pos.playbook}`);
  if (f.positive.handoff && pos.handoff !== f.positive.handoff) {
    throw new Error(`fail-closed: ${f.playbook} handoff ${pos.handoff}`);
  }
  if (f.positive.threshold && pos.threshold !== f.positive.threshold) {
    throw new Error(`fail-closed: ${f.playbook} threshold ${pos.threshold}`);
  }
  if (pos.deliveryArmed !== false) throw new Error(`fail-closed: ${f.playbook} armed delivery`);
  const neg = routeRequest({
    text: f.counterexample.text,
    adnActive: f.counterexample.adnActive ?? false,
    explicitAdn: f.counterexample.explicitAdn,
  });
  if (f.counterexample.reason === "casual" && neg.reason !== "casual") {
    throw new Error(`fail-closed: ${f.playbook} casual`);
  }
  if (f.counterexample.reason === "outside" && neg.reason !== "outside-adn") {
    throw new Error(`fail-closed: ${f.playbook} outside`);
  }
}
const formal = fixtures.filter((f) => f.positive.threshold);
if (formal.length < 6) throw new Error(`fail-closed: need six formal thresholds, got ${formal.length}`);
console.log(JSON.stringify({ ok: true, count: files.length, fixtures: fixtures.length, formal: formal.length, missing }));
