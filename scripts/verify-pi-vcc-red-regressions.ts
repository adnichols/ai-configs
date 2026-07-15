import { spawnSync } from "node:child_process";
import { resolve } from "node:path";

const args = process.argv.slice(2);
const valueAfter = (flag: string) => {
  const index = args.indexOf(flag);
  return index >= 0 ? args[index + 1] : undefined;
};
const candidate = valueAfter("--candidate") ?? "source";
const expectCurrentFailures = valueAfter("--expect-current-failures");
const expectFixed = valueAfter("--expect-fixed");

if (candidate !== "source") {
  console.error("RED verifier currently supports --candidate source only");
  process.exit(2);
}
if ((expectCurrentFailures === undefined) === (expectFixed === undefined)) {
  console.error("Specify exactly one of --expect-current-failures all or --expect-fixed all");
  process.exit(2);
}
if ((expectCurrentFailures ?? expectFixed) !== "all") {
  console.error("Only the complete named regression set is supported");
  process.exit(2);
}

const packageDir = resolve("_pi/packages/pi-vcc");
const regressionPattern = [
  "persisted top-level custom_message",
  "no-message_start acceptance",
  "reload releases the old package lease",
  "uses host idle readiness",
  "preserves settlement gating while the host remains active",
  "gates acceptance-expiry retries",
  "version 1 active tools",
  "version 2 active-tool correlation",
  "partial parallel-tool batches",
  "persistence failure releases the package lease",
  "releases lifecycle ownership even when replacement outcome persistence fails",
  "unrelated assistant and tool activity before durable acceptance",
  "full 100ms activation budget",
  "paces two retries at exactly 1s then 2s",
  "stalls an outstanding tool",
  "status-only messages neutral",
  "version 1 submitted work",
  "double package load",
  "dual-reads version 1 history",
  "custom-message intent classifier",
].join("|");
const files = [
  "tests/continuation.test.ts",
  "tests/coordinator.test.ts",
  "tests/integration/continuation-runtime.test.ts",
  "tests/custom-message-classifier.test.ts",
];

const run = spawnSync("bun", ["test", ...files, "--test-name-pattern", regressionPattern], {
  cwd: packageDir,
  encoding: "utf8",
  env: {
    ...process.env,
    PI_VCC_LOG_PATH: resolve(".tmp/pi-vcc-red-verifier.jsonl"),
  },
});
const output = `${run.stdout ?? ""}${run.stderr ?? ""}`;
process.stdout.write(output);

if (expectFixed !== undefined) {
  if (run.status !== 0) {
    console.error("RED regression verifier: FAIL (post-fix named regressions are not green)");
    process.exit(1);
  }
  console.log("RED regression verifier: PASS (all named regressions are green in post-fix mode)");
  process.exit(0);
}

if (run.status === 0) {
  console.error(
    "RED regression verifier: FAIL (the P1 baseline mode expected named current-main failures, but the candidate is already fixed; use --expect-fixed all after P2-P5)",
  );
  process.exit(1);
}
const expectedIdentifiers = ["fail", "error", "expected"];
if (!expectedIdentifiers.some((identifier) => output.toLowerCase().includes(identifier))) {
  console.error("RED regression verifier: FAIL (tests failed without an expected assertion identifier)");
  process.exit(1);
}
console.log("RED regression verifier: PASS (named regressions failed as expected on the pre-fix baseline)");
