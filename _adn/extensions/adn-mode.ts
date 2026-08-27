import { readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { spawnSync } from "node:child_process";

export const PIN = "46756f89270d7e7dcb8c28c90fd0f957ade4ce2c";
export const STATE_TYPE = "dev.adn.mode.state.v1";
export const REMINDER_TYPE = "dev.adn.mode.reminder.v1";
export const MARKER = "ADN_RUNTIME_MARKER:extension-adn-mode:46756f89270d7e7dcb8c28c90fd0f957ade4ce2c";

export type AdnState = {
  schemaVersion: 1;
  sessionId: string;
  generation: number;
  enabled: boolean;
};

export type BranchEntry = { customType?: string; details?: unknown };
export type AdnEvent =
  | { type: "session_start"; sessionId: string; generation: number; branch?: BranchEntry[] }
  | { type: "session_switch"; reason: "new" | "resume"; sessionId: string; generation: number; branch?: BranchEntry[] }
  | { type: "branch" | "tree" | "compact"; sessionId: string; generation: number; branch?: BranchEntry[] }
  | { type: "command"; enabled: boolean; sessionId: string; generation: number };

export type GenerationOpts = { generation: number; root?: string; pin?: string };

export const empty = (sessionId = "", generation = 0): AdnState => ({
  schemaVersion: 1,
  sessionId,
  generation,
  enabled: false,
});

export function parseState(details: unknown): AdnState | null {
  if (!details || typeof details !== "object") return null;
  const d = details as Record<string, unknown>;
  if (d.schemaVersion !== 1) return null;
  if (typeof d.sessionId !== "string" || typeof d.generation !== "number" || typeof d.enabled !== "boolean") return null;
  return { schemaVersion: 1, sessionId: d.sessionId, generation: d.generation, enabled: d.enabled };
}

export function latestMatchingEntry(
  branch: BranchEntry[] | undefined,
  customType: string,
  sessionId: string,
  generation: number,
): BranchEntry | undefined {
  if (!branch) return undefined;
  for (let i = branch.length - 1; i >= 0; i--) {
    const entry = branch[i];
    if (entry?.customType !== customType) continue;
    const parsed = parseState(entry.details);
    if (parsed && parsed.sessionId === sessionId && parsed.generation === generation) return entry;
  }
  return undefined;
}

export function reminderPayload(state: AdnState) {
  return {
    customType: REMINDER_TYPE,
    display: false as const,
    content: "",
    details: { ...state, marker: MARKER },
  };
}

export const RECOVERY_APPLY = "bun ~/.agents/adn/scripts/setup-adn.ts apply";

export function repairOwnedDrift(home = process.env.HOME ?? ""): { ok: boolean; recovery?: string } {
  if (process.env.ADN_SKIP_REPAIR === "1") return { ok: true };
  const setup = join(home, ".agents/adn/scripts/setup-adn.ts");
  const check = spawnSync("bun", [setup, "check"], { encoding: "utf8" });
  if (check.status === 0) return { ok: true };
  const apply = spawnSync("bun", [setup, "apply"], { encoding: "utf8" });
  const recheck = spawnSync("bun", [setup, "check"], { encoding: "utf8" });
  if (apply.status === 0 && recheck.status === 0) return { ok: true };
  return { ok: false, recovery: RECOVERY_APPLY };
}

function restore(event: Extract<AdnEvent, { sessionId: string; generation: number; branch?: BranchEntry[] }>): AdnState {
  const hit = parseState(latestMatchingEntry(event.branch, STATE_TYPE, event.sessionId, event.generation)?.details);
  return hit ?? empty(event.sessionId, event.generation);
}

export function reduceEvent(_prev: Partial<AdnState>, event: AdnEvent): AdnState {
  if (event.type === "command") {
    return { schemaVersion: 1, sessionId: event.sessionId, generation: event.generation, enabled: event.enabled };
  }
  if (event.type === "session_switch" && event.reason === "new") {
    return empty(event.sessionId, event.generation);
  }
  return restore(event);
}

function branchFrom(ctx: unknown): BranchEntry[] {
  if (!ctx || typeof ctx !== "object" || !("sessionManager" in ctx)) return [];
  const sm = ctx.sessionManager;
  if (!sm || typeof sm !== "object" || !("getBranch" in sm) || typeof sm.getBranch !== "function") return [];
  const branch = sm.getBranch();
  return Array.isArray(branch) ? branch : [];
}

export function scanCollisions(dirs: string[], selfName = "adn-mode.ts"): string[] {
  const hits: string[] = [];
  for (const dir of dirs) {
    let names: string[] = [];
    try {
      names = readdirSync(dir);
    } catch {
      continue;
    }
    for (const name of names) {
      if (name === selfName) continue;
      const path = join(dir, name);
      try {
        if (!statSync(path).isFile()) continue;
      } catch {
        continue;
      }
      if (/adn|poteto/i.test(name)) hits.push(path);
    }
  }
  return hits;
}

export function attach(
  pi: {
    on: (event: string, fn: (event: unknown, ctx: unknown) => void) => void;
    registerCommand: (name: string, spec: unknown) => void;
    appendEntry: (type: string, details: unknown) => void;
    sendMessage: (payload: unknown) => void;
    notify: (msg: string, kind?: string) => void;
  },
  opts: GenerationOpts,
) {
  const generation = opts.generation;
  let sessionId = "";
  let state: AdnState = empty("", generation);
  const persist = () => {
    pi.appendEntry(STATE_TYPE, state);
    pi.appendEntry(REMINDER_TYPE, reminderPayload(state));
  };
  pi.on("session_start", (event: unknown, ctx: unknown) => {
    sessionId = event && typeof event === "object" && "sessionId" in event && typeof event.sessionId === "string"
      ? event.sessionId
      : crypto.randomUUID();
    state = reduceEvent(state, { type: "session_start", sessionId, generation, branch: branchFrom(ctx) });
    persist();
  });
  pi.on("before_agent_start", () => persist());
  pi.on("session_switch", (event: unknown, ctx: unknown) => {
    const reason = event && typeof event === "object" && "reason" in event && event.reason === "new" ? "new" : "resume";
    if (reason === "new") sessionId = crypto.randomUUID();
    state = reduceEvent(state, { type: "session_switch", reason, sessionId, generation, branch: branchFrom(ctx) });
    persist();
  });
  for (const type of ["branch", "tree", "compact"] as const) {
    pi.on(type, (_event, ctx: unknown) => {
      state = reduceEvent(state, { type, sessionId, generation, branch: branchFrom(ctx) });
      persist();
    });
  }
  pi.registerCommand("adn-mode", {
    description: "Activate ADN mode or forward a request into skill://adn-mode",
    handler: (args: string) => {
      const trimmed = String(args ?? "").trim();
      if (/^off\b/i.test(trimmed)) {
        state = reduceEvent(state, { type: "command", enabled: false, sessionId, generation });
        persist();
        return;
      }
      const repaired = repairOwnedDrift();
      if (!repaired.ok) {
        pi.notify(`${repaired.recovery}`, "error");
        return;
      }
      const request = trimmed.replace(/^(on|repair)\b/i, "").trim();
      state = reduceEvent(state, { type: "command", enabled: true, sessionId, generation });
      persist();
      if (request) {
        pi.sendMessage({ role: "user", content: `Load skill://adn-mode\n${request}` });
      }
    },
  });
}

export default function (pi: Parameters<typeof attach>[0]) {
  attach(pi, { generation: 1 });
}
