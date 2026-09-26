import { readFileSync } from "node:fs";
import { join } from "node:path";
import { createHash } from "node:crypto";
import { describe, expect, test } from "bun:test";

const PIN = "ecc249f1e306fc64ddf83c7bed16cacf7c2239db";
const ROOT = join(import.meta.dir, "..");
const RUN = (process.env.ADN_THROUGH ? Number(String(process.env.ADN_THROUGH).replace(/^p/, "")) : 8) >= 5;

describe.skipIf(!RUN)("adoption", () => {
  test("pin and license stay put", () => {
    const prov = readFileSync(join(ROOT, "PROVENANCE.md"), "utf8");
    const license = readFileSync(join(ROOT, "LICENSE.pstack"), "utf8");
    expect(prov).toContain(PIN);
    expect(prov).toContain("do not silently refresh");
    expect(license).toContain("MIT License");
    const before = createHash("sha256").update(readFileSync(join(ROOT, "skills/principle-laziness-protocol/SKILL.md"))).digest("hex");
    expect(before.length).toBe(64);
  });
  test("available update does not mutate the pin", () => {
    const before = readFileSync(join(ROOT, "PROVENANCE.md"), "utf8");
    expect(before).toContain("do not silently refresh");
    expect(before).toContain(PIN);
  });
});
