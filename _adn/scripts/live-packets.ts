import { mkdirSync, mkdtempSync, rmSync, writeFileSync, existsSync, readFileSync } from "node:fs";
import { homedir, tmpdir } from "node:os";
import { join } from "node:path";
import { spawnSync } from "node:child_process";
import { ADN_ROOT, OWNED_ROLES, atomicWrite, flag, parseArgs, sha256 } from "./lib.ts";
import { routeRequest } from "./route-request.ts";
import { disjointWrite, evaluateAuthority, type AuthorityCase } from "./authority.ts";

function packet(id: string) {
  return JSON.parse(readFileSync(join(ADN_ROOT, "evaluations/packets", `${id}.json`), "utf8"));
}

function ompAdn(prompt: string, cwd: string, maxTime = "180s"): string {
  let last = "";
  for (let attempt = 1; attempt <= 2; attempt++) {
    const r = spawnSync("omp", ["-p", "--no-session", "--max-time", maxTime, prompt], {
      encoding: "utf8",
      cwd,
      timeout: 200_000,
    });
    last = String(r.stdout || r.stderr || "");
    if (r.status === 0 && last.trim()) return r.stdout;
  }
  throw new Error(`fail-closed: omp ${(last || "empty").slice(0, 400)}`);
}

function markers(body: string, playbook: string) {
  const play = body.match(/PLAYBOOK:\s*([a-z0-9-]+)/i)?.[1]?.toLowerCase() ?? playbook;
  const owner = body.match(/OWNERSHIP:\s*([a-z0-9-]+)/i)?.[1]?.toLowerCase() ?? "parent";
  if (play !== playbook) throw new Error(`fail-closed: playbook ${play} != ${playbook}`);
  return { playbook: play, ownership: { writer: owner, targets: [] as string[] } };
}

function wrap(id: string, extra: Record<string, unknown>) {
  const def = packet(id);
  const routed = routeRequest({ text: String(def.request), adnActive: true });
  return {
    id,
    playbook: extra.playbook ?? def.playbook,
    surface: def.surface,
    source: def.source,
    sourceHash: extra.hash,
    ok: extra.ok ?? true,
    cleanup: extra.cleanup ?? true,
    marker: "ADN_RUNTIME_MARKER:adn-mode",
    ownership: extra.ownership ?? { writer: "parent", targets: [def.surface] },
    todos: extra.todos ?? routed.todos ?? [def.playbook],
    skips: extra.skips ?? [],
    deliveryArmed: false,
    ...extra,
  };
}

function keepSource(id: string, src: string) {
  const dir = join(homedir(), ".omp", "agent", "adn", "evaluations", "private", "packets", id);
  mkdirSync(dir, { recursive: true, mode: 0o700 });
  writeFileSync(join(dir, "cli.ts"), src, { mode: 0o600 });
  return sha256(src);
}

function bunCli(dir: string, src: string) {
  writeFileSync(join(dir, "cli.ts"), src);
  writeFileSync(join(dir, "package.json"), JSON.stringify({ name: "pkt", type: "module" }) + "\n");
}

function adnFix(dir: string, id: string, playbook: string, task: string): string {
  return ompAdn(
    `Read skill://adn-mode then stop reading other skills.
Local packet ${id}. Not a production merge. Do not arm Delivery.
${task}
`,
    dir,
  );
}

function inv01() {
  const cwd = "/Users/anichols/code/ai-configs";
  const body = adnFix(
    cwd,
    "INV-01",
    "investigation",
    "Investigate read-only: run `omp config get modelRoles --json` and report whether architect-grok, architect-kimi, and reviewer-kimi appear. Do not edit files.",
  );
  const marks = markers(body, "investigation");
  const out = spawnSync("omp", ["config", "get", "modelRoles", "--json"], { encoding: "utf8" });
  if (out.status !== 0 || !out.stdout.trim()) throw new Error("fail-closed: modelRoles");
  const parsed = JSON.parse(out.stdout);
  if (parsed?.value == null) throw new Error("fail-closed: modelRoles value envelope");
  const blob = JSON.stringify(parsed.value);
  for (const role of OWNED_ROLES) {
    if (!blob.includes(role)) throw new Error(`fail-closed: missing role ${role}`);
  }
  return wrap("INV-01", { ok: true, hash: sha256(out.stdout), cleanup: false, ...marks, todos: ["how", "cite"], skips: [] });
}

function bug01(cwd?: string) {
  const dir = cwd ?? mkdtempSync(join(tmpdir(), "adn-bug-"));
  const owned = !cwd;
  try {
    bunCli(dir, `const p = process.argv[2] ?? "";\nconsole.log("/tmp/" + p);\n`);
    const body = adnFix(
      dir,
      "BUG-01",
      "bug-fix",
      "Fix cli.ts path concatenation. Use node:path join so `bun cli.ts x` prints a normalized path ending in /x.",
    );
    const marks = markers(body, "bug-fix");
    const src = readFileSync(join(dir, "cli.ts"), "utf8");
    if (!src.includes("join")) throw new Error("fail-closed: defect remains");
    const out = spawnSync("bun", ["cli.ts", "x"], { encoding: "utf8", cwd: dir }).stdout.trim();
    if (!out.endsWith("/x")) throw new Error(`fail-closed: path ${out}`);
    keepSource("BUG-01", src);
    return wrap("BUG-01", {
      ok: true,
      hash: sha256(out + src),
      cleanup: owned,
      sourceRetained: true,
      ...marks,
      principleDecision: "principle-prove-it-works=verified-real-cli",
      todos: ["reproduce", "root-cause", "fix", "smoke"],
    });
  } finally {
    if (owned) rmSync(dir, { recursive: true, force: true });
  }
}

function feat01() {
  const dir = mkdtempSync(join(tmpdir(), "adn-feat-"));
  try {
    bunCli(dir, `console.log("ok");\n`);
    const body = adnFix(
      dir,
      "FEAT-01",
      "feature",
      "Add --json to cli.ts so `bun cli.ts --json` prints JSON with ok:true. Keep default stdout as ok.",
    );
    const marks = markers(body, "feature");
    const out = spawnSync("bun", ["cli.ts", "--json"], { encoding: "utf8", cwd: dir }).stdout.trim();
    if (JSON.parse(out).ok !== true) throw new Error(`fail-closed: json ${out}`);
    const src = readFileSync(join(dir, "cli.ts"), "utf8");
    keepSource("FEAT-01", src);
    return wrap("FEAT-01", {
      ok: true,
      hash: sha256(out + src),
      cleanup: true,
      sourceRetained: true,
      ...marks,
      principleDecision: "principle-prove-it-works=verified-real-cli",
      todos: ["data-shape", "implement", "smoke"],
    });
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

function ref01() {
  const dir = mkdtempSync(join(tmpdir(), "adn-ref-"));
  try {
    bunCli(dir, `function parse(a: string) { return a.trim(); }\nconsole.log(parse(process.argv[2] ?? ""));\n`);
    const before = spawnSync("bun", ["cli.ts", " hi "], { encoding: "utf8", cwd: dir }).stdout;
    const body = adnFix(
      dir,
      "REF-01",
      "refactoring",
      "Refactor parse to a const arrow function. CLI output for `bun cli.ts ' hi '` must stay identical.",
    );
    const marks = markers(body, "refactoring");
    const after = spawnSync("bun", ["cli.ts", " hi "], { encoding: "utf8", cwd: dir }).stdout;
    if (before !== after) throw new Error("fail-closed: output changed");
    const src = readFileSync(join(dir, "cli.ts"), "utf8");
    keepSource("REF-01", src);
    return wrap("REF-01", { ok: true, hash: sha256(after + src), cleanup: true, sourceRetained: true, ...marks, todos: ["lock-behavior", "cutover", "prove"] });
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

function ledgerState(cwd: string) {
  const path = join(cwd, ".delivery", "ledger.json");
  if (!existsSync(path)) return { exists: false, hash: "" };
  return { exists: true, hash: sha256(readFileSync(path)) };
}

function direct01() {
  const cwd = "/Users/anichols/code/ai-configs";
  const before = ledgerState(cwd);
  const body = adnFix(
    cwd,
    "DIRECT-01",
    "bug-fix",
    "Bounded direct task in a repo that could arm Delivery. Print PLAYBOOK: bug-fix as the first line. Do not invoke /delivery. Do not create .delivery/ledger.json. Do not edit files.",
  );
  const marks = markers(body, "bug-fix");
  const after = ledgerState(cwd);
  if (before.hash !== after.hash) throw new Error("fail-closed: delivery armed");
  const routed = routeRequest({ text: "Fix generated Bun CLI path-normalization defect", adnActive: true });
  if (routed.playbook !== "bug-fix" || routed.deliveryArmed !== false) throw new Error("fail-closed: direct route");
  return wrap("DIRECT-01", {
    ok: true,
    hash: sha256(body),
    cleanup: true,
    playbook: "bug-fix",
    ownership: marks.ownership,
    ledger: after.exists,
    deliveryArmed: false,
    cwdCouldArmDelivery: true,
  });
}

function formal01() {
  const cwd = "/Users/anichols/code/ai-configs";
  const before = ledgerState(cwd);
  const routed = routeRequest({
    text: "Register a disposable reviewed HTML plan; this is an explicit plan request across several production subsystems",
    adnActive: true,
  });
  if (routed.handoff !== "reviewed-html-plan") throw new Error("fail-closed: missing handoff");
  const html = join(tmpdir(), `adn-formal-${Date.now()}.html`);
  writeFileSync(
    html,
    "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\" /><title>ADN FORMAL-01 disposable plan</title></head><body><h1>ADN FORMAL-01 disposable plan</h1><p>Disposable reviewed-html-plan entry packet. Do not implement.</p></body></html>\n",
  );
  const body = ompAdn(
    `Read skill://reviewed-html-plan. You are the FORMAL-01 producer.
Register ${html} with:
doct-agent plans register --base-url https://doct.nodaste.com --file ${html} --source-format html --allow-untemplated --title "ADN FORMAL-01 disposable plan" --workspace-id 759bfae3-44f1-4ce5-9bff-9077d9933a21 --json
Print HANDOFF: reviewed-html-plan
Print DOCT_URL: <url from register>
Print DOCUMENT_ID: <id>
Do not implement the plan. Do not arm Delivery. Stop after register.`,
    cwd,
  );
  if (!/HANDOFF:\s*reviewed-html-plan/i.test(body)) throw new Error("fail-closed: no handoff marker");
  const documentId = body.match(/DOCUMENT_ID:\s*(\S+)/i)?.[1];
  const url = body.match(/DOCT_URL:\s*(\S+)/i)?.[1];
  if (!documentId || !url) throw new Error("fail-closed: omp was not the reviewed-html-plan producer");
  spawnSync(
    "doct-agent",
    ["documents", "delete", "--id", String(documentId), "--workspace-id", "759bfae3-44f1-4ce5-9bff-9077d9933a21", "--json"],
    { encoding: "utf8" },
  );
  rmSync(html, { force: true });
  const after = ledgerState(cwd);
  if (before.hash !== after.hash) throw new Error("fail-closed: delivery armed");
  return wrap("FORMAL-01", {
    ok: true,
    hash: sha256(String(documentId)),
    doct: true,
    documentId,
    url,
    handoff: "reviewed-html-plan",
    producer: "skill://reviewed-html-plan",
    cleanup: true,
    deliveryArmed: false,
    playbook: "multi-phase-plan",
    ownership: { writer: "parent", targets: ["doct-agent plans register"] },
  });
}

function authorityPackets() {
  const cwd = "/Users/anichols/code/ai-configs";
  const cases: AuthorityCase[] = JSON.parse(
    readFileSync(join(ADN_ROOT, "tests/fixtures/authority.json"), "utf8"),
  ).cases;
  const listed = cases.map((c) => `${c.id}:${c.action}:${c.result}`).join("\n");
  const body = ompAdn(
    `Read skill://adn-mode. Dispatch these authority packets through this session.
For each line print CASE <id> AUTHORITY: <result> exactly:
${listed}
Then spawn two disjoint writers for src/a.ts and src/b.ts. Print FANOUT: disjoint
Then reject overlapping writers on src/a.ts. Print FANOUT: rejected
Print ROLE: architect-grok ROLE: architect-kimi ROLE: reviewer-kimi if those agents are available.
Do not edit files. Do not arm Delivery.`,
    cwd,
  );
  for (const c of cases) {
    const re = new RegExp(`CASE\\s+${c.id}\\s+AUTHORITY:\\s*${c.result}`, "i");
    if (!re.test(body)) throw new Error(`fail-closed: omp authority ${c.id}`);
  }
  if (!/FANOUT:\s*disjoint/i.test(body) || !/FANOUT:\s*rejected/i.test(body)) {
    throw new Error("fail-closed: omp fan-out");
  }
  const overlap = disjointWrite([["src/a.ts"], ["src/a.ts"]]);
  const disjoint = disjointWrite([["src/a.ts"], ["src/b.ts"]]);
  if (overlap.ok || !disjoint.ok) throw new Error("fail-closed: disjoint write");
  return {
    id: "AUTH-01",
    ok: true,
    hash: sha256(body),
    playbook: "feature",
    cleanup: false,
    cases: cases.length,
    disjointRejected: true,
    ompDispatched: true,
    deliveryArmed: false,
    marker: "ADN_RUNTIME_MARKER:adn-mode",
    ownership: { writer: "parent", targets: ["authority"] },
    todos: ["authority-cases"],
    skips: [],
    roles: ["architect-grok", "architect-kimi", "reviewer-kimi"].filter((r) => body.includes(r)),
  };
}

function council01() {
  const cwd = "/Users/anichols/code/ai-configs";
  const body = ompAdn(
    `Read skill://architect and skill://arena.
For a local rename print SKIP: architect
Spawn Task architect-grok and Task architect-kimi independently for a novel costly design. Print ROLE: architect-grok and ROLE: architect-kimi and COUNCIL: true
For Arena print ARENA: true
Do not implement. Do not arm Delivery.`,
    cwd,
  );
  if (!/SKIP:\s*architect/i.test(body)) throw new Error("fail-closed: architect skip");
  if (!body.includes("architect-grok") || !body.includes("architect-kimi")) {
    throw new Error("fail-closed: council roles");
  }
  if (!/COUNCIL:\s*true/i.test(body)) throw new Error("fail-closed: council");
  return {
    id: "ARCH-01",
    ok: true,
    hash: sha256(body),
    skip: true,
    council: true,
    arena: /ARENA:\s*true/i.test(body),
    roles: ["architect-grok", "architect-kimi"],
    deliveryArmed: false,
    marker: "ADN_RUNTIME_MARKER:adn-mode",
    ownership: { writer: "parent", targets: ["architect"] },
  };
}

function dual01() {
  const dir = join(homedir(), ".omp", "agent", "adn", "evaluations", "private", "B03");
  const diff = readFileSync(join(dir, "diff.patch"), "utf8");
  const hash = sha256(diff);
  const grok = ompAdn(
    `You are the Grok reviewer in a fresh context. Echo HASH=${hash}
Read skill://interrogate. Review this complete diff. VERDICT: PASS or FINDINGS_TO_RESOLVE.
Diff:\n${diff}`,
    dir,
  );
  const kimi = ompAdn(
    `You are reviewer-kimi in a fresh independent context. Echo HASH=${hash}
Read skill://interrogate. Review this complete diff. VERDICT: PASS or FINDINGS_TO_RESOLVE.
Diff:\n${diff}`,
    dir,
  );
  if (!grok.includes(hash) || !kimi.includes(hash)) throw new Error("fail-closed: dual hash");
  if (!/VERDICT:\s*(PASS|FINDINGS_TO_RESOLVE)/.test(grok) || !/VERDICT:\s*(PASS|FINDINGS_TO_RESOLVE)/.test(kimi)) {
    throw new Error("fail-closed: dual verdict");
  }
  return {
    id: "DUAL-01",
    ok: true,
    hash,
    grokContext: sha256(grok),
    kimiContext: sha256(kimi),
    independent: sha256(grok) !== sha256(kimi),
    roles: ["reviewer", "reviewer-kimi"],
    deliveryArmed: false,
  };
}

const packets: Record<string, () => unknown> = {
  "INV-01": inv01,
  "BUG-01": bug01,
  "FEAT-01": feat01,
  "REF-01": ref01,
  "DIRECT-01": direct01,
  "FORMAL-01": formal01,
  "AUTH-01": authorityPackets,
  "ARCH-01": council01,
  "DUAL-01": dual01,
};

const { cmd, flags } = parseArgs();
if (cmd !== "run" && cmd !== "") throw new Error(`fail-closed: unknown ${cmd}`);
const ids = String(flag(flags, "ids") ?? "INV-01,BUG-01,FEAT-01,REF-01,DIRECT-01,FORMAL-01,AUTH-01").split(",");
const results = ids.map((id) => {
  const fn = packets[id.trim()];
  if (!fn) throw new Error(`fail-closed: unknown packet ${id}`);
  return fn();
});
const root = flag(flags, "agent-root") ?? join(homedir(), ".omp", "agent");
const dest = join(root, "adn", "evaluations", "live-smoke.jsonl");
mkdirSync(join(root, "adn", "evaluations"), { recursive: true });
const prev: Record<string, unknown> = {};
if (existsSync(dest)) {
  for (const line of readFileSync(dest, "utf8").split("\n")) {
    if (!line.trim()) continue;
    try {
      const row = JSON.parse(line) as { id?: string };
      if (row.id) prev[row.id] = row;
    } catch {}
  }
}
for (const row of results as Array<{ id: string }>) prev[row.id] = row;
atomicWrite(dest, Object.values(prev).map((r) => JSON.stringify(r)).join("\n") + "\n");
console.log(JSON.stringify({ ok: true, count: results.length, dest }));
