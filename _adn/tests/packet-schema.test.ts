import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";

const ROOT = join(import.meta.dir, "..", "evaluations", "packets");
const IDS = ["INV-01", "BUG-01", "FEAT-01", "REF-01", "DIRECT-01", "FORMAL-01"] as const;

describe("packet schema", () => {
  test("six P4 packets have required fields and fingerprints", () => {
    for (const id of IDS) {
      const pkt = JSON.parse(readFileSync(join(ROOT, `${id}.json`), "utf8"));
      expect(pkt.id).toBe(id);
      expect(pkt.source).toBe("p4-packet");
      expect(pkt.sourceHash).toBeTruthy();
      expect(pkt.request).toBeTruthy();
      expect(pkt.surface).toBeTruthy();
      expect(pkt.playbook).toBeTruthy();
      expect(pkt.expected).toBeTruthy();
    }
  });
});
