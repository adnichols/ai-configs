import { describe, expect, test } from "bun:test";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { disjointWrite, evaluateAuthority, type AuthorityCase } from "../scripts/authority.ts";

const FIX = join(import.meta.dir, "fixtures/authority.json");

describe("authority", () => {
  test("default pause, exact destructive preauth, third-party needs repo+action", () => {
    const table = JSON.parse(readFileSync(FIX, "utf8"));
    expect(table.default).toBe("pause-exclusion");
    expect(table.destructiveData).toBe("exact-preauth");
    expect(table.thirdParty).toBe("repo-plus-action");
    expect(table.repoPermit.allowed).toBe(true);
    expect(table.repoForbid.allowed).toBe(false);
    for (const c of table.cases as AuthorityCase[]) {
      expect(evaluateAuthority(c)).toBe(c.result);
    }
    expect(disjointWrite([["src/a.ts"], ["src/a.ts"]]).ok).toBe(false);
    expect(disjointWrite([["src/a.ts"], ["src/b.ts"]]).ok).toBe(true);
  });
});
