import { describe, expect, test } from "bun:test";

function pairDisposition(currentBody: string, adnBody: string) {
  const adnFinds = /\bP[12]\b|FINDINGS_TO_RESOLVE/.test(adnBody);
  const currentFinds = /\bP[12]\b|FINDINGS_TO_RESOLVE/.test(currentBody);
  if (adnFinds && currentFinds) return "compose-or-retain";
  if (adnFinds && !currentFinds) return "replace";
  return "retain";
}

function p8Decide(opts: { valid: number; verificationReproduced: boolean }) {
  if (!opts.verificationReproduced || opts.valid < 10) {
    return "INCONCLUSIVE";
  }
  return "retain";
}

describe("review decision", () => {
  test("retain when both arms are clean", () => {
    expect(pairDisposition("PASS", "PASS")).toBe("retain");
  });
  test("replace when ADN finds a P1 the current arm missed", () => {
    expect(pairDisposition("PASS", "P1 FINDINGS_TO_RESOLVE")).toBe("replace");
  });
  test("INCONCLUSIVE when original verification was not reproduced", () => {
    expect(p8Decide({ valid: 10, verificationReproduced: false })).toBe("INCONCLUSIVE");
  });
});
