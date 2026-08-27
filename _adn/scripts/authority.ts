export type AuthorityCase = {
  id: string;
  action: string;
  preauth?: boolean;
  scope?: string;
  exact?: string;
  repo?: string;
  exactAction?: string;
  repoPermit?: boolean;
  repoForbid?: boolean;
  result: "proceed" | "pause" | "default-excluded" | "stop";
};

export function evaluateAuthority(c: AuthorityCase): AuthorityCase["result"] {
  if (c.repoForbid) return "stop";
  if (c.repoPermit) return "proceed";
  if (c.action === "delete-data" || c.action === "delete-unproven-work" || c.action === "credential-change") {
    return c.preauth && c.scope ? "proceed" : "pause";
  }
  if (c.action === "customer-message" || c.action === "deploy") {
    return c.exact ? "proceed" : "default-excluded";
  }
  if (c.action === "create-pr" && c.repo) {
    return c.exactAction ? "proceed" : "pause";
  }
  if (c.action === "create-pr") return "default-excluded";
  return c.preauth ? "proceed" : "pause";
}

export function disjointWrite(targets: string[][]): { ok: boolean; reason?: string } {
  const seen = new Set<string>();
  for (const group of targets) {
    for (const t of group) {
      if (seen.has(t)) return { ok: false, reason: "shared-write" };
      seen.add(t);
    }
  }
  return { ok: true };
}
