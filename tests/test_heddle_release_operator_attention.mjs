#!/usr/bin/env node

import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";

const source = await readFile("_pi/workflows/heddle-release.js", "utf8");
const start = source.indexOf("async function bestEffortOperatorAttention");
const end = source.indexOf("async function startAgent", start);
assert.ok(start >= 0 && end > start, "operator-attention wrapper must remain testable in workflow source");
const wrapperSource = source.slice(start, end);

function shellQuote(value) {
  const text = String(value);
  if (/^[A-Za-z0-9_@%+=:,./-]+$/.test(text)) return text;
  return `'${text.replace(/'/g, `'\\''`)}'`;
}
function joinCmd(parts) {
  return parts.map(shellQuote).join(" ");
}

function makeWrapper(run) {
  const context = vm.createContext({ run, joinCmd });
  vm.runInContext(`${wrapperSource}\nglobalThis.withOperatorAttentionForTest = withOperatorAttention;`, context);
  return context.withOperatorAttentionForTest;
}

async function scenario(name, operation, verify) {
  const calls = [];
  const wrapper = makeWrapper(async (command) => {
    calls.push(command);
    return { exitCode: command.includes(" set ") ? 7 : 0 }; // nonzero helper is ignored
  });
  let result;
  let error;
  try {
    result = await wrapper({
      paneId: "w1:p2",
      kind: "password",
      message: "Enter password",
      operation: async () => {
        calls.push("operation");
        return operation();
      },
    });
  } catch (caught) {
    error = caught;
  }
  assert.match(calls[0], /^herdr-operator-attention set --pane w1:p2 --kind password --message /);
  assert.equal(calls[1], "operation", `${name}: set must finish before pane operation`);
  assert.equal(calls.at(-1), "herdr-operator-attention clear --pane w1:p2", `${name}: clear must be final`);
  verify({ result, error, calls });
}

await scenario("success", () => ({ exitCode: 0 }), ({ result, error }) => {
  assert.equal(error, undefined);
  assert.equal(result.exitCode, 0);
});
await scenario("failure return", () => ({ exitCode: 1 }), ({ result, error }) => {
  assert.equal(error, undefined);
  assert.equal(result.exitCode, 1);
});
await scenario("timeout return", () => ({ exitCode: 124, timedOut: true }), ({ result }) => {
  assert.equal(result.timedOut, true);
});
await scenario("throw", () => { throw new Error("pane launch failed"); }, ({ error }) => {
  assert.match(error.message, /pane launch failed/);
});

// Even a thrown attention subprocess error is swallowed so the gate operation remains authoritative.
const resilient = makeWrapper(async () => { throw new Error("helper missing"); });
const value = await resilient({
  paneId: "w1:p2",
  kind: "password",
  message: "Enter password",
  operation: async () => "gate-result",
});
assert.equal(value, "gate-result");

assert.match(source, /interactiveOpen: async \(\) => withOperatorAttention\(\{/);
assert.match(source, /kind: "password"/);
assert.match(source, /paneRunScript\(gatePaneId, gateOpenScript/);

console.log("ok - Heddle release gate operator attention");
